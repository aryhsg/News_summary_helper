import asyncio

import os
import sys
import json
from dotenv import load_dotenv

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)

from infrastructure import db
from gemini import gemini_service

load_dotenv()
DB = db.NewsDB()
ai = gemini_service()

def get_str_summary(raw_summary: dict):
    # 從傳入的字典中取出 JSON 字串並解析
    raw_data = json.loads(raw_summary.get("news_summary", "{}"))
    
    content = ""
    try:
        core_trends = raw_data.get("core_trends", [])
        
        for item in core_trends:
            topic = item.get("topic", "").strip()
            analysis = item.get("analysis", "").strip()
            
            # 使用項目符號與分隔線增加視覺區隔
            content += f"● 【{topic}】\n\n"
            content += f"   {analysis}\n\n"
            #content += f"{'-' * 40}\n" # 加入短分隔線

        # 組合最終結果，主標題置中或加強顯示
        report_title = raw_data.get('report_title', '今日新聞趨勢彙總')
        formatted_summary = f"=== {report_title} ===\n\n{content}" 

        return formatted_summary 

    except Exception as e:
        print(f"解析摘要時發生錯誤: {e}")
        return None

def get_formatted_summary(raw_summary: dict):
    raw_data = json.loads(raw_summary.get("news_summary", "{}"))
    # 1. 處理所有趨勢內容，將 topic 與 analysis 組合
    trend_sections = []
    for item in raw_data.get("core_trends", []):
        topic = item.get("topic", "")
        analysis = item.get("analysis", "")
        # 使用 <h3> 和 <p> 進行簡單網頁排版
        section = f"<br><h3>{topic}</h3>\n<br>\n<p style='text-align: justify;'>{analysis}</p>"
        trend_sections.append(section)
    
    # 2. 取得主標題並用 <h2> 包起來
    report_title = raw_data.get("report_title", "今日新聞摘要")
    title_html = f"<h2>{report_title}</h2>\n<hr>"
    
    # 3. 將所有區塊組合成一個大字串，中間用換行隔開
    all_content_html = "\n".join(trend_sections)
    
    # 最終輸出的 HTML 字串
    final_html = f"{title_html}\n{all_content_html}"
    
    return final_html   

async def generate_cate_summary(category: str):
    news_list = []
    try:
        query_result = await DB.fetch_news_summary(category=category) # [{news_id, title, category, content}]
        if not query_result:
            print(f"類別 {category} 找不到任何新聞內容")
            return None
        else:
            news_json = json.dumps(query_result, ensure_ascii=False)
            try:
                response = await ai.generate_summary(instruction_type="cate", contents=news_json)
                if response:
                    print("生成成功")
                    print(response)
                    """print("--- 原始內容偵錯 ---")
                    print(repr(response)) """
                    print(f"字串長度: {len(response)}")
                    cate_summary_tuple = (category, response)

                    await DB.insert_cate_summary(category= category, cate_summary_tuple= cate_summary_tuple)
                else:
                    print("生成失敗")
            except Exception as e:
                print(f"gemini error: {e}")

    except Exception as e:
        print(f"db error: {e}")
    finally:
            await ai.close()


async def main(category:str):
    await DB.pool_init()
    try:
        print("generating vategory summary...")
        await generate_cate_summary(category=category)
    except Exception as e:
        print(f"error: {e}")
    finally:
        await DB.pool_close()

async def test(cate: str):
    await DB.pool_init()
    try:
        raw_summary = await DB.fetch_cate_summary(category= "兩岸")
        print(type(raw_summary[0]['news_summary']))
        get_str_summary(raw_summary=raw_summary[0])
    except Exception as e:
        print(f"error: {e}")
    finally:
        await DB.pool_close()

if __name__ == "__main__":
    #asyncio.run(main("兩岸"))
    asyncio.run(test("兩岸"))