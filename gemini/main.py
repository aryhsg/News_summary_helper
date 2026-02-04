import os
import json 
import asyncio
import textwrap
from google import genai
from google.genai import types
from dotenv import load_dotenv
#from json_schema import *
#from gemini.json_schema import *
from json_schema import NewsSummarySchema
from x import contents
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

class gemini_client:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")).aio

        self.sg_system_instruction = """
            你是一位專業的新聞編輯。
            請閱讀新聞文章，並提取核心重點（最少 1 點，最多 5 點）。
            內容必須準確反映文章資訊，包含關鍵事件與影響。
            請將結果依照指定的 JSON 格式回傳。
            以繁體中文回答。
            """
        
        self.batch_system_instruction="""
            你是一位專業的資料分析師和新聞編輯。你的任務是分析用戶提供的多篇新聞 JSON，並將其歸納為高品質的主題摘要，以繁體中文回答。

            輸入格式： [{'news_id': int, 'title': str, 'content': str}]。

            執行規範：
            
            精鍊原則： 每個 point 的內容請控制在 50-80 個中文字內，直接切入核心重點，避免冗贅的過渡句（如：根據報導指出...）。

            數據導向： 摘要中若有具體的數據（如股價、百分比、日期），必須保留，這對金融用戶至關重要。

            結構化： 嚴格遵守提供的 JSON Schema 輸出，確保 topic 具有概括性，且 points 數量介於 2 到 4 點。
            """

        self.cate_system_instruction="""
            你是一位專業的資料分析師和新聞編輯。你的任務是分析用戶提供的多篇新聞 JSON，並將其歸納為高品質的主題摘要，以繁體中文回答。

            執行規範：
            
            精鍊原則： 每個 point 的內容請控制在 50-80 個中文字內，直接切入核心重點，避免冗贅的過渡句（如：根據報導指出...）。

            數據導向： 摘要中若有具體的數據（如股價、百分比、日期），必須保留，這對金融用戶至關重要。

            結構化： 嚴格遵守提供的 JSON Schema 輸出，確保 topic 具有概括性，且 points 數量介於 2 到 4 點。

            字數節流： 總體輸出的文字量需精簡，以利於在行動裝置上閱讀。
            """

    def _format_data(self, data: list):
        response = []
        # 設定內容縮進的寬度（例如 4 個半形空格，剛好對齊 "1. " 之後的文字）
        width = 60  # 每行最大字數
        indent_space = "    " 
        
        for i, content in enumerate(data):
            point_text = content.get("point", "")
            prefix = f"{i+1}. "
            
            # 使用 wrap 處理換行，這會回傳一個文字列表
            # initial_indent: 第一行的縮進 (即標號)
            # subsequent_indent: 之後每一行的縮進 (即空白)
            wrapped_text = textwrap.fill(
                point_text, 
                width=width, 
                initial_indent=prefix, 
                subsequent_indent=" " * len(prefix)
            )
            
            response.append(wrapped_text)
        
        # 用兩個換行符號分隔每一點，閱讀起來更舒適
        return "\n".join(response)

    async def generate_summary(self, instruction_type, contents):
        if instruction_type == "sg":
            system_instruction = self.sg_system_instruction
            max_output_tokens = 2048
            # 建議：sg 模式通常是為了閱讀，建議用 text/plain
            mime_type = "application/json" 
            response_schema=NewsSummarySchema.model_json_schema()
        elif instruction_type == "batch":
            system_instruction = self.cate_system_instruction
            max_output_tokens = 10000
            mime_type = "application/json" 
            response_schema=NewsSummarySchema.model_json_schema()
        elif instruction_type == "cate":
            system_instruction = self.cate_system_instruction
            max_output_tokens = 10000
            mime_type = "text/plain" 
            #response_schema=Cate_NewsSummarySchema
        else:
            raise ValueError("Invalid instruction_type")

        config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=0.9,
            max_output_tokens=max_output_tokens,
            response_mime_type=mime_type, 
            system_instruction=system_instruction
        )

        response = await self.client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=contents, 
            config=config
        )
        #data = json.loads(response.text)
        #data = self._format_data(data)

        #return data
        return response.text

    async def close(self):
        """手動關閉連線池，避免資源洩漏"""
        await self.client.aclose()



    
        
            



# 測試用範例
async def main(contents: list):
    client = gemini_client()
    result = await client.generate_summary("batch", contents)
    #result = client._format_data(result)
    print(type(result))
    print(result)

if __name__ == "__main__":
    news_json_str = json.dumps(contents, ensure_ascii=False)
    asyncio.run(main(contents=news_json_str))