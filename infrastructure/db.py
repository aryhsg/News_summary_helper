import logging

from psycopg_pool import AsyncConnectionPool

import config
from infrastructure.exceptions import DatabaseError
from infrastructure.repositories import (
    NewsRepository,
    SingleSummaryRepository,
    CateSummaryRepository,
)

logger = logging.getLogger(__name__)

# truncate_table 只允許清空這幾張已知的表，避免 f-string 直接接使用者輸入的資料表名稱。
_TRUNCATABLE_TABLES = {"news", "single_news_summary", "cate_news_summary"}


class NewsDB:
    """資料庫存取的 facade：持有連線池生命週期，並把實際的讀寫委派給
    三個依資料表拆分的 repository（NewsRepository/SingleSummaryRepository/
    CateSummaryRepository）。對外的方法名稱、簽名都維持跟拆分前一致，
    main_apps.py、line_service.py、web/fastapi_service.py、gen_*.py、
    scrape_n_store.py、daily_truncate_tables.py 不需要跟著改。"""

    def __init__(self):
        self.username = config.DB_USERNAME
        self.password = config.DB_PASSWORD
        self.host = config.DB_HOST
        self.port = config.DB_PORT
        self.db_name = config.DB_NAME
        self.conninfo = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        self.pool = AsyncConnectionPool(conninfo=self.conninfo, min_size=2, max_size=10, open=False)

        self._news = NewsRepository(self.pool)
        self._single_summaries = SingleSummaryRepository(self.pool)
        self._cate_summaries = CateSummaryRepository(self.pool)

    async def pool_init(self):
        await self.pool.open()

    async def pool_close(self):
        await self.pool.close()

    async def create_table(self, query: str):
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                try:
                    await cursor.execute(query)
                    await connection.commit()
                    print("Table created successfully!")
                except Exception as e:
                    logger.exception("建立表格失敗")
                    raise DatabaseError("建立表格失敗") from e

    async def truncate_table(self, table: str):
        if table not in _TRUNCATABLE_TABLES:
            print(f"Refused to truncate unknown table: {table}")
            return
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                query = f"""
                    TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;
                """
                try:
                    await cursor.execute(query)
                    await connection.commit()
                    print(f"Table {table} deleted successfully!")
                except Exception as e:
                    logger.exception(f"清空表格 {table} 失敗")
                    raise DatabaseError(f"清空表格 {table} 失敗") from e

    # --- news ---
    async def insert_news(self, news_list):
        return await self._news.insert_news(news_list)

    async def fetch_cate_news(self, category: str):
        return await self._news.fetch_cate_news(category)

    async def fetch_news_content(self, news_id: str | None = None, category: str | None = None, batch: bool | None = None, keyword: str | None = None):
        return await self._news.fetch_news_content(news_id=news_id, category=category, batch=batch, keyword=keyword)

    async def web_fetch_news(self):
        return await self._news.web_fetch_news()

    async def web_fetch_news_contents(self, news_id: str):
        return await self._news.web_fetch_news_contents(news_id)

    async def web_search_news(self, keyword: str):
        return await self._news.web_search_news(keyword)

    async def test_web_fetch_news(self):
        return await self._news.test_web_fetch_news()

    # --- single_news_summary ---
    async def insert_news_summary(self, news_summary_list):
        return await self._single_summaries.insert_news_summary(news_summary_list)

    async def fetch_specific_summary(self, news_id: str | None = None, category: str | None = None, batch: bool | None = None):
        return await self._single_summaries.fetch_specific_summary(news_id=news_id, category=category, batch=batch)

    async def fetch_news_summary(self, category: str):
        return await self._single_summaries.fetch_news_summary(category)

    async def test_web_fetch_specific_summary(self, news_id: str):
        return await self._single_summaries.test_web_fetch_specific_summary(news_id)

    # --- cate_news_summary ---
    async def insert_cate_summary(self, category, cate_summary_tuple):
        return await self._cate_summaries.insert_cate_summary(category, cate_summary_tuple)

    async def fetch_cate_summary(self, category: str):
        return await self._cate_summaries.fetch_cate_summary(category)
