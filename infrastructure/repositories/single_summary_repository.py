import logging

from psycopg.rows import dict_row

from infrastructure.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class SingleSummaryRepository:
    """負責 single_news_summary 表的讀寫。"""

    def __init__(self, pool):
        self.pool = pool

    async def insert_news_summary(self, news_summary_list):
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                insert_query = '''
                    INSERT INTO single_news_summary (news_id, news_summary, category)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (news_id) DO NOTHING
                    '''
                try:
                    await cursor.executemany(insert_query, news_summary_list)
                    await connection.commit()
                    print(f"成功處理 {len(news_summary_list)} 筆新聞摘要")
                except Exception as e:
                    logger.exception("寫入 single_news_summary 失敗")
                    raise DatabaseError("寫入 single_news_summary 失敗") from e

    async def fetch_specific_summary(self, news_id: str | None = None, category: str | None = None, batch: bool | None = None):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                if news_id:
                    select_query = '''
                        SELECT s.news_id, s.news_summary, s.category, n.title
                        FROM single_news_summary s
                        INNER JOIN news n ON s.news_id = n.news_id
                        WHERE s.news_id = %s
                        '''
                    try:
                        await cursor.execute(select_query, (news_id,))
                        return await cursor.fetchall()
                    except Exception as e:
                        logger.exception("讀取單篇摘要（依 news_id）失敗")
                        raise DatabaseError("讀取單篇摘要（依 news_id）失敗") from e

                if category:
                    select_query = '''
                        SELECT news_id, news_summary
                        FROM single_news_summary
                        WHERE category = %s
                        '''
                    try:
                        await cursor.execute(select_query, (category,))
                        return await cursor.fetchall()
                    except Exception as e:
                        logger.exception("讀取單篇摘要（依分類）失敗")
                        raise DatabaseError("讀取單篇摘要（依分類）失敗") from e

    async def fetch_news_summary(self, category: str):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                    SELECT n.news_id, n.title, s.category, s.news_summary
                    FROM single_news_summary s
                    INNER JOIN news n ON s.news_id = n.news_id
                    WHERE s.category = %s
                    '''
                try:
                    await cursor.execute(select_query, (category,))
                    return await cursor.fetchall()
                except Exception as e:
                    logger.exception("讀取單篇摘要清單（依分類）失敗")
                    raise DatabaseError("讀取單篇摘要清單（依分類）失敗") from e

    async def sandbox_fetch_specific_summary(self, news_id: str):
        """給 /api/sandbox（不耗用 Gemini 配額的示範端點）用的單篇摘要查詢。"""
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                        SELECT s.news_id, s.news_summary, s.category, n.title
                        FROM single_news_summary s
                        INNER JOIN news n ON s.news_id = n.news_id
                        WHERE s.news_id = %s
                            '''
                try:
                    await cursor.execute(select_query, (news_id,))
                    return await cursor.fetchall()
                except Exception as e:
                    logger.exception("讀取 sandbox 單篇摘要失敗")
                    raise DatabaseError("讀取 sandbox 單篇摘要失敗") from e
