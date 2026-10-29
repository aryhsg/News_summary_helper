"""
每日排程進入點：為 CATE_SUMMARY_CATEGORIES 裡的每個類別各生成一次彙總
摘要。這個檔案維持原本的路徑/檔名，是因為目前呼叫它的 crontab/systemd
timer 設定本身不在版本控制內（見重構計畫 Finding 13），不確定外部是用
什麼指令呼叫到這支檔案，Stage 4 只把內部生成/格式化邏輯搬到
gemini/generation.py、gemini/formatting.py，保留這個進入點路徑不變。
"""
import asyncio

import os
import sys
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
from gemini.generation import generate_cate_summary_and_store

load_dotenv()


async def main():
    news_db = db.NewsDB()
    ai = gemini_service()
    await news_db.pool_init()
    try:
        print("generating category summary...")
        for category in CATE_SUMMARY_CATEGORIES:
            print(f"正在生成 {category} 類別摘要...")
            await generate_cate_summary_and_store(category=category, db_instance=news_db, gemini_instance=ai)
            print(f"{category} 類別摘要生成完成，暫停60秒後繼續下一類別...")
            await asyncio.sleep(60)  # 每生成一個類別摘要後暫停60秒，避免過度頻繁請求AI服務
        print("所有類別摘要生成完成！")
    except Exception as e:
        print(f"gen cate summary error: {e}")
    finally:
        await news_db.pool_close()
        # 只在所有類別都處理完後才關閉一次。原本的寫法把 ai.close() 放在
        # 每個類別各自的 generate_summary_n_store() 的 finally 裡，導致處理
        # 完第一個類別後 Gemini client 就被關閉，CATE_SUMMARY_CATEGORIES
        # 清單裡後面的類別全部因為用已關閉的 client 呼叫而失敗（被內層
        # except Exception 吃掉，只印一行 log，不會讓整個排程中斷）——是一個
        # 原本就存在、沒被注意到的 bug，這次順手修掉。
        await ai.close()


if __name__ == "__main__":
    asyncio.run(main())
