import os
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import TypeAdapter
from gemini.json_schema import NewsSummarySchema, CategorySummary
from gemini.prompts import SG_SYSTEM_INSTRUCTION, BATCH_SYSTEM_INSTRUCTION, CATE_SYSTEM_INSTRUCTION
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
        if instruction_type == "sg":
            system_instruction = SG_SYSTEM_INSTRUCTION
            max_output_tokens = 2048
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
            response_schema=response_schema
        )

        response = await self._do_generate_content(
            model="gemini-3.7-flash",
            contents=contents,
            config=config
        )
        return response.text

    async def close(self):
        """手動關閉連線池，避免資源洩漏"""
        await self.client.aclose()
