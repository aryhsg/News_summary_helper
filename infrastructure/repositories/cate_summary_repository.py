import logging

from psycopg.rows import dict_row

from infrastructure.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class CateSummaryRepository:
    """負責 cate_news_summary 表的讀寫。"""

    def __init__(self, pool):
        self.pool = pool

    async def insert_cate_summary(self, category, cate_summary_tuple):
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                insert_query = '''
                    INSERT INTO cate_news_summary (category, news_summary)
                    VALUES (%s, %s)
                    ON CONFLICT (category) DO UPDATE SET news_summary = EXCLUDED.news_summary
                    '''
                try:
                    await cursor.execute(insert_query, cate_summary_tuple)
                    await connection.commit()
                    print(f"成功寫入 {category} 類摘要")
                except Exception as e:
                    logger.exception("寫入 cate_news_summary 失敗")
                    raise DatabaseError("寫入 cate_news_summary 失敗") from e

    async def fetch_cate_summary(self, category: str):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                    SELECT category, news_summary
                    FROM cate_news_summary
                    WHERE category = %s
                    '''
                try:
                    await cursor.execute(select_query, (category,))
                    return await cursor.fetchall()
                except Exception as e:
                    logger.exception("讀取類別摘要失敗")
                    raise DatabaseError("讀取類別摘要失敗") from e
