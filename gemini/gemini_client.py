import os
import json 
import asyncio
import textwrap
from google import genai
from google.genai import types
from gemini.json_schema import NewsSummarySchema, CategorySummary
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

class gemini_service:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")).aio

        self.sg_system_instruction = """
            你是一位專業的資料分析師和新聞編輯。你的任務是分析用戶提供的一篇新聞 JSON，並將其歸納為高品質的主題摘要，以繁體中文回答。

            輸入格式： [{'news_id': int, 'title': str, 'content': str, 'category': str}]。

            執行規範：
            
            精鍊原則： 每個 point 的內容請控制在 50-80 個中文字內，直接切入核心重點，避免冗贅的過渡句（如：根據報導指出...）。

            數據導向： 摘要中若有具體的數據（如股價、百分比、日期），必須保留，這對金融用戶至關重要。

            結構化： 嚴格遵守提供的 JSON Schema 輸出， news_id 必須為原始輸入資料之 news_id ， title 必須為原始輸入資料之標題，且 points 數量介於 2 到 4 點。
            """
        
        self.batch_system_instruction="""
            你是一位專業的資料分析師和新聞編輯。你的任務是分析用戶提供的多篇新聞 JSON，並將其歸納為高品質的主題摘要，以繁體中文回答。

            執行規範：
            
            精鍊原則： 每個 point 的內容請控制在 50-80 個中文字內，直接切入核心重點，避免冗贅的過渡句（如：根據報導指出...）。

            數據導向： 摘要中若有具體的數據（如股價、百分比、日期），必須保留，這對金融用戶至關重要。

            結構化： 嚴格遵守提供的 JSON Schema 輸出， news_id 必須為原始輸入資料之 news_id ， title 必須為原始輸入資料之標題，且 points 數量介於 2 到 4 點。

            字數節流： 總體輸出的文字量需精簡，以利於在行動裝置上閱讀。
            """

        self.cate_system_instruction="""
            # Role
            你是一位資深政經編輯與情報分析專家，擅長從碎片化的新聞中提取具備「高資訊密度」的趨勢洞察。

            # Goal
            請針對提供的多篇新聞，產出今日該類別的核心趨勢彙總。你的目標是產出具備「決策參考價值」的報告，而非簡單的條列摘要。

            # Noise Filtering Logic (極為重要)
            在處理新聞時，請嚴格執行以下過濾標準：
            1. **保留**：涉及公共政策、外交關係、重大經濟變動、社會結構轉型、具備全國性影響力的事件。
            2. **捨棄**：
            - 區域性氣象預報或局部天氣。
            - 小規模交通事故、突發零星火警。
            - 單一地區性的鄰里活動或瑣事。
            - 娛樂圈八卦或缺乏社會價值的趣聞。
            **若該類別下所有新聞均屬於雜訊，請直接回覆：「今日無重大新聞價值事件。」不要強行彙總。**
            
            # Restriction
            嚴格遵守提供的 JSON Schema 輸出。

            # Example
            {
                "report_title": "金融市場動態與政策影響分析",
                "core_trends": [
                    {
                    "topic": "金融機構獲利穩健，但面臨匯率與政策變動挑戰",
                    "analysis": "多數金控公司在2026年1月繳出亮眼財報，顯示銀行、證券等業務動能強勁，獲利表現亮眼。然而，壽險業將面臨匯率會計新制，雖預計可省下大量避險成本，但需滿足嚴格的資本門檻，短期內可能增加增資壓力。新台幣匯率波動劇烈，雖在蛇年封關時強升，但近期呈現貶值趨勢，顯示國際美元走勢及台股表現仍是影響匯率的重要因素。",
                    "related_news_ids": [
                        "9327476",
                        "9328556",
                        "9328004",
                        "9327568",
                        "9329445",
                        "9329157",
                        "9329214",
                        "9329132",
                        "9329300",
                        "9329289",
                        "9329554",
                        "9327550"
                    ]
                    },
                    {
                    "topic": "政府調控房市與稅制改革影響深遠",
                    "analysis": "央行選擇性信用管制措施已見成效，不動產放款集中度下降，資金導向首購族與都更危老重建貸款，有助於抑制投機並改善信用資源結構。另一方面，「囤房稅2.0」預計於2025年開徵，已促使夫妻間贈與房產棟數創下歷史新高，顯示多屋族為規避高稅率而積極規劃節稅。此外，企業捐贈運動產業的稅務優惠雖提高，但也新增防弊條款，顯示政策在鼓勵特定產業發展的同時，也注重風險控管。",
                    "related_news_ids": [
                        "9327471",
                        "9328934",
                        "9329485",
                        "9327234"
                    ]
                    }
            }
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
            system_instruction = self.batch_system_instruction
            max_output_tokens = 10000
            mime_type = "application/json" 
            response_schema=NewsSummarySchema.model_json_schema()

        elif instruction_type == "cate":
            system_instruction = self.cate_system_instruction
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
            system_instruction=system_instruction
        )

        response = await self.client.models.generate_content(
            model="gemini-2.5-flash-lite", 
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