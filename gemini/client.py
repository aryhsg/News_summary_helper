import logging
import os
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import TypeAdapter
from gemini.json_schema import NewsSummarySchema, CategorySummary
from gemini.prompts import SG_SYSTEM_INSTRUCTION, BATCH_SYSTEM_INSTRUCTION, CATE_SYSTEM_INSTRUCTION
from infrastructure.exceptions import GeminiResponseError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# 單篇摘要（sg）的思考程度。批次（batch）與類別摘要（cate）維持模型預設：
# 類別摘要要跨多篇找趨勢，需要較多推理；批次這次沒有另外測試過。
SG_THINKING_LEVEL = types.ThinkingLevel.LOW

class gemini_service:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")).aio

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((
            ServerError,     # 對應 500, 503, 504 等伺服器端錯誤
            # ClientError 包含 429 (配額滿) 和 408 (超時)
            # 但要注意 ClientError 也包含 400 (語法錯)，語法錯通常不需要重試
        )),
        reraise=True
    )
    async def _do_generate_content(self, model, contents, config):
        response = await self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )
        return response

    async def generate_summary(self, instruction_type, contents):
        thinking_config = None

        if instruction_type == "sg":
            system_instruction = SG_SYSTEM_INSTRUCTION
            # max_output_tokens 同時涵蓋「思考 token」與「實際輸出 token」。原本 2048 太緊：
            # 長文章的思考就能用掉 1700 多，剩下的空間不夠寫完 JSON，輸出被攔腰截斷、
            # json.loads 失敗，使用者看到 500。摘要的實際輸出只有約 200~350 token。
            max_output_tokens = 8192
            # 單篇摘要不需要深度推理，降低思考程度可以同時減少截斷機率與費用
            # （思考 token 按輸出價計費，而且常常是實際輸出的 2~6 倍）。
            thinking_config = types.ThinkingConfig(thinking_level=SG_THINKING_LEVEL)
            # 建議：sg 模式通常是為了閱讀，建議用 text/plain
            mime_type = "application/json"
            response_schema=NewsSummarySchema.model_json_schema()

        elif instruction_type == "batch":
            system_instruction = BATCH_SYSTEM_INSTRUCTION
            max_output_tokens = 10000
            mime_type = "application/json"
            # batch 模式一次處理多篇新聞，消費端（gemini/generation.py）預期拿到
            # 一個 list，所以 schema 要用陣列包起來，不能直接沿用 "sg" 的單物件 schema。
            # 用 TypeAdapter 讓 Pydantic 把巢狀的 SinglePoint 正確疊到頂層 $defs，
            # 直接手動包 {"type":"array","items": NewsSummarySchema.model_json_schema()}
            # 會讓 $defs 卡在 items 裡面那一層，SDK 解析 $ref 時會找不到定義而噴錯。
            response_schema=TypeAdapter(list[NewsSummarySchema]).json_schema()

        elif instruction_type == "cate":
            system_instruction = CATE_SYSTEM_INSTRUCTION
            max_output_tokens = 10000
            mime_type = "application/json"
            response_schema=CategorySummary.model_json_schema()

        else:
            raise ValueError("Invalid instruction_type")

        config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=0.9,
            max_output_tokens=max_output_tokens,
            response_mime_type=mime_type,
            system_instruction=system_instruction,
            response_schema=response_schema,
            thinking_config=thinking_config,
        )

        response = await self._do_generate_content(
            model="gemini-3.7-flash",
            contents=contents,
            config=config
        )

        # 模型沒有正常結束（例如 MAX_TOKENS：輸出被截斷）時，內容不能信任，
        # 直接報明確的錯誤並記下原因，不要把截斷的 JSON 交給下游去解析失敗。
        candidate = response.candidates[0] if response.candidates else None
        finish_reason = candidate.finish_reason if candidate else None
        if finish_reason != types.FinishReason.STOP or not response.text:
            logger.error(
                "Gemini 回應未正常結束：mode=%s finish_reason=%s usage=%s",
                instruction_type, finish_reason, response.usage_metadata,
            )
            raise GeminiResponseError(f"Gemini 回應未正常結束（finish_reason={finish_reason}）")
        return response.text

    async def close(self):
        """手動關閉連線池，避免資源洩漏"""
        await self.client.aclose()
