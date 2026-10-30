"""
每小時定時執行爬蟲，將爬取的新聞存入資料庫
"""
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

from news_crawler import scrape_news
import infrastructure.db as db
import infrastructure.redis_manager as redis_manager
import gemini.client as gemini_client
import gemini.generation as generation
from contextlib import asynccontextmanager


@asynccontextmanager # 非同步上下文管理器 
async def db_lifespan():
    news_db = db.NewsDB()
    redis = redis_manager.RedisManager()
    ai = gemini_client.gemini_service()
    try:
        await news_db.pool_init()
        await redis.init_pool()
        print("資料庫連線池已開啟")

        yield (news_db, redis, ai)

    finally:
        await news_db.pool_close()
        await redis.close()
        await ai.close()
        print("資料庫連線池已關閉")

async def scrape_n_store(db):
    print("開始爬蟲")
    news = await scrape_news()
    try:
        await db.insert_news(news)
        print("新聞成功存入資料庫")
    except Exception as e:
        print(f"db error: {e}")

async def main(scrape_only: bool = False):
        try:
            async with db_lifespan() as (db, redis, gemini):
                await scrape_n_store(db=db)

            print("finish scraping")

            # cron 的每小時排程只需要爬蟲、不需要每次都打 Gemini 生成批次摘要
            # （那個比較適合獨立排程，之後要開再開），--scrape-only 讓這支
            # 腳本可以單獨只做爬蟲這一半。
            if scrape_only:
                return

            await asyncio.sleep(300)

            async with db_lifespan() as (db, redis, gemini):
                await generation.batch_gen_all_sum_n_store(db=db, gemini=gemini, redis=redis)
        except Exception as e:
                print(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main(scrape_only="--scrape-only" in sys.argv))