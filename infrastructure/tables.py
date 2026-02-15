from db import NewsDB
import asyncio

single_query = """
CREATE TABLE IF NOT EXISTS single_news_summary (
    id INT PRIMARY KEY ,
    news_id VARCHAR(50) REFERENCES news(news_id) ON DELETE CASCADE,
    news_summary VARCHAR(500)
    )
"""

cate_query = """
CREATE TABLE IF NOT EXISTS cate_news_summary (
    id INT PRIMARY KEY ,
    category VARCHAR(50) UNIQUE,
    news_summary VARCHAR(5000)
    )
"""


async def main():
    news_db = NewsDB()
    # 初始化資料庫
    await news_db.pool_init()
    
    # 建立表格
    await news_db.create_table(single_query)
    await news_db.create_table(cate_query)
  
    
    await news_db.pool_close()

# 這是啟動整個非同步程式的入口
if __name__ == "__main__":
    asyncio.run(main())