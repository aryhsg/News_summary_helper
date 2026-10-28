import asyncio

import os
import sys
import json
from dotenv import load_dotenv

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)

# psycopg 的 async 模式在 Windows 預設的 ProactorEventLoop 下無法運作，
# 本機（Windows）直接跑這支腳本時需要換成 SelectorEventLoop。
# 另外 Windows 終端機預設編碼（如 cp950）無法印出專案裡的 emoji log，
# 會直接 crash，且跟其他背景執行緒的 log 同時發生時會卡死整個程式，
# 改成強制用 UTF-8 輸出。Linux 部署（VPS）不受影響，不會進到這個分支。
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from constants import CATE_SUMMARY_CATEGORIES
from infrastructure import db
from gemini import gemini_service

load_dotenv()
DB = db.NewsDB()
ai = gemini_service()

def get_str_summary(raw_summary: dict):
    """
    給LINE排版用
    """
    # 從傳入的字典中取出 JSON 字串並解析
    # CategorySummary schema 只有 insights（[{topic, analysis}]）跟 is_noteworthy，
    # 沒有 report_title 欄位。
    raw_data = json.loads(raw_summary.get("news_summary", "{}"))

    content = ""
    try:
        insights = raw_data.get("insights", [])

        for item in insights:
            topic = item.get("topic", "").strip()
            analysis = item.get("analysis", "").strip()

            # 使用項目符號與分隔線增加視覺區隔
            content += f"● 【{topic}】\n\n"
            content += f"   {analysis}\n\n"
            #content += f"{'-' * 40}\n" # 加入短分隔線

        if not insights:
            content = "今日無重大新聞價值事件。\n\n"

        formatted_summary = f"=== 今日新聞趨勢彙總 ===\n\n{content}"

        return formatted_summary

    except Exception as e:
        print(f"解析摘要時發生錯誤: {e}")
        return None

def get_formatted_summary(raw_summary: dict):
    """
    給網頁排版用
    """
    # CategorySummary schema 只有 insights（[{topic, analysis}]）跟 is_noteworthy，
    # 沒有 report_title 欄位。
    raw_data = json.loads(raw_summary.get("news_summary", "{}"))
    # 1. 處理所有趨勢內容，將 topic 與 analysis 組合
    insights = raw_data.get("insights", [])
    trend_sections = []
    for item in insights:
        topic = item.get("topic", "")
        analysis = item.get("analysis", "")
        # 使用 <h3> 和 <p> 進行簡單網頁排版
        section = f"<br><h3>{topic}</h3>\n<br>\n<p style='text-align: justify;'>{analysis}</p>"
        trend_sections.append(section)

    if not insights:
        trend_sections.append("<br><p>今日無重大新聞價值事件。</p>")

    # 2. 標題用 <h2> 包起來（schema 沒有 report_title，固定用通用標題）
    title_html = "<h2>今日新聞摘要</h2>\n<hr>"

    # 3. 將所有區塊組合成一個大字串，中間用換行隔開
    all_content_html = "\n".join(trend_sections)

    # 最終輸出的 HTML 字串
    final_html = f"{title_html}\n{all_content_html}"

    return final_html

async def generate_summary_n_store(category: str):
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


async def main():
    cate_list = CATE_SUMMARY_CATEGORIES
    await DB.pool_init()
    try:
        print("generating vategory summary...")
        for category in cate_list:
            print(f"正在生成 {category} 類別摘要...")
            await generate_summary_n_store(category=category)
            print(f"{category} 類別摘要生成完成，暫停60秒後繼續下一類別...")
            await asyncio.sleep(60) # 每生成一個類別摘要後暫停60秒，避免過度頻繁請求AI服務
        print("所有類別摘要生成完成！")
    except Exception as e:
        print(f"gen cate summary error: {e}")
    finally:
        await DB.pool_close()


if __name__ == "__main__":
    asyncio.run(main())
