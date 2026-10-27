import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

# psycopg 的 async 模式在 Windows 預設的 ProactorEventLoop 下無法運作，
# 本機（Windows）直接跑這支腳本時需要換成 SelectorEventLoop。
# 另外 Windows 終端機預設編碼（如 cp950）無法印出專案裡的 emoji log，
# 會直接 crash，且跟其他背景執行緒的 log 同時發生時會卡死整個程式，
# 改成強制用 UTF-8 輸出。Linux 部署（VPS）不受影響，不會進到這個分支。
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from infrastructure.db import NewsDB

db = NewsDB()

async def main():
    await db.pool_init()
        # 在此處可以呼叫其他方法進行測試
    await db.truncate_table('news')
    await db.truncate_table('cate_news_summary')
    await db.pool_close()

if __name__ == "__main__":
    asyncio.run(main())