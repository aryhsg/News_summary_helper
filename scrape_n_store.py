from news_crawler import scrapers
import infrastructure.db as db
from contextlib import asynccontextmanager
import asyncio


@asynccontextmanager # 非同步上下文管理器 
async def db_lifespan():
    news_db = db.NewsDB()
    await news_db.pool_init()
    print("資料庫連線池已開啟")

    yield news_db

    await news_db.pool_close()
    print("資料庫連線池已關閉")

async def scrape_n_store():
    async with db_lifespan() as DB:
        print("開始爬蟲")
        news = await scrapers.scrape_news()
        try:
            await DB.insert_news(news)
            print("新聞成功存入資料庫")
        except Exception as e:
            print(f"db error: {e}")




if __name__ == "__main__":
    asyncio.run(scrape_n_store())