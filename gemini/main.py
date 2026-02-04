import os
import json 
import asyncio
import textwrap
from google import genai
from google.genai import types
from dotenv import load_dotenv
#from json_schema import *
from gemini.json_schema import *

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
async def main(contents:str):
    client = gemini_client()
    result = await client.generate_summary("sg", contents)
    result = client.format_data(result)
    print(type(result))
    print(result)

if __name__ == "__main__":
    contents = """
記憶體市場近期受長江存儲擴產腳步提前、長鑫存儲低價倒貨等流言干擾，惟全球最大電子產品批發零售市場深圳華強北昨（3）日公布最新每周記憶體報價不但沒跌，與台廠最相關的LPDDR4更全面勁揚，全數衝上歷史天價，最高漲幅逾一成，粉碎陸企動搖市場謠言，南亞科（2408）、華邦等台廠「安啦！」。
業界指出，華強北有「中國電子第一街」之譽，是全球最大電子產品批發與零售市場，地位比日本秋葉原、台北光華商場還高，當地商家與業內採購人士「消息比靈通的」，對價格更是「超級敏感」，若真有風吹草動，華強北的報價一定會第一時間反映，極具參考指標，如今當地報價出爐，顯示市場供需並未因傳言而鬆動，反而持續升溫。
LPDDR系列為工控、消費性電子、智慧裝置與邊緣運算的關鍵記憶體規格，價格走勢最能反映DRAM的真實供需狀況，此次報價全面刷寫新高，凸顯結構性缺貨仍在擴大，南亞科（2408）、華邦（2344）等台廠仍將大咬漲價紅利。
南亞科昨日公告，元月營收達153.1億元，創新高，月增27.4%，年增逾六倍。南亞科預期，AI應用爆發使得HBM與DDR5等高階記憶體大量排擠成熟製程產能，使得DDR與LPDDR市場供需火熱，2026年整體需求「滿熱的」，全年展望樂觀。
上周末傳出長江存儲武漢三期新廠量產時程由原訂2027年提前於今年下半年，本周又傳出長鑫存儲低價「倒貨」，雖然兩大陸企都未證實，仍造成市場人心惶惶。由於華強北採購人士相關記憶體報價每周二才更新一次，兩大陸企傳出大動作干擾市場的狀況，無法在相關消息傳出第一時間獲得報價走勢。
根據華強北採購專業報價網站「CFM閃存市場」昨天近午時分開出的最新每周報價，不僅沒跌，與台廠最相關的LPDDR4系列更是全面勁揚，全數衝上歷史天價，顯示市況依舊處於供給吃緊狀態。
觀察最新報價細節，LPDDR4X 16GB至96GB等容量當中，以主流規格64Gb單周漲10.29%，漲幅最高，最新報價為75美元；漲幅第二大的是16Gb漲9.09%，報24美元；另外96Gb漲8.24%，報92美元；32Gb與48Gb分別漲7.14%、5.17%，報價各為45美元、61美元。
其餘包括Flash Wafer、DDR4，固態硬碟（SSD）、各類DRAM模組等最新報價都開至少持平至10%左右漲幅。昨天華強北新盤價開出後，粉碎陸企相關負面傳聞。業界分析，若大陸兩大記憶體廠大動作干擾市況，「價格不跌就算幸運，更不可能還大漲」。
        """
    asyncio.run(main(contents))