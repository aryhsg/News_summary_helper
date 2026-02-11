"""
每小時定時執行爬蟲，將爬取的新聞存入資料庫
"""

from news_crawler import scrapers
import infrastructure.db as db
import infrastructure.redis_manager as redis_manager
import gemini.gemini_client as gemini_client
import gemini.gen_sig_summary as gen_sig_summary
from contextlib import asynccontextmanager
import asyncio


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
    news = await scrapers.scrape_news()
    try:
        await db.insert_news(news)
        print("新聞成功存入資料庫")
    except Exception as e:
        print(f"db error: {e}")

async def main():
    async with db_lifespan() as (db, redis, gemini):
        try:
            await scrape_n_store(db=db)
            await gen_sig_summary.batch_gen_all_sum_n_store(db=db, gemini=gemini, redis=redis)
        except Exception as e:
            print(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())