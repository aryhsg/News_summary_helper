import logging

from psycopg.rows import dict_row

from constants import SANDBOX_CATEGORIES
from infrastructure.exceptions import DatabaseError

logger = logging.getLogger(__name__)


def escape_like(keyword: str) -> str:
    """跳脫 LIKE/ILIKE 的萬用字元。PostgreSQL 預設以反斜線當跳脫字元，所以把
    使用者輸入裡的 \\、% 與 _ 各加一個反斜線，搜尋 % 時就只找真的含 % 的標題，
    不會變成「匹配全部」。"""
    return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class NewsRepository:
    """負責 news 表的讀寫。"""

    def __init__(self, pool):
        self.pool = pool

    async def insert_news(self, news_list):
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                insert_query = '''
                    INSERT INTO news (news_id, category, title, content, url, article_image, keywords)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (news_id) DO NOTHING
                    '''
                try:
                    await cursor.executemany(insert_query, news_list)
                    await connection.commit()
                    print(f"成功處理 {len(news_list)} 筆新聞")
                except Exception as e:
                    logger.exception("寫入 news 失敗")
                    raise DatabaseError("寫入 news 失敗") from e

    async def fetch_cate_news(self, category: str):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                    SELECT category, url , news_id, title
                    FROM news
                    WHERE category = %s
                    '''
                try:
                    await cursor.execute(select_query, (category,))
                    return await cursor.fetchall()
                except Exception as e:
                    logger.exception("讀取 news（依分類）失敗")
                    raise DatabaseError("讀取 news（依分類）失敗") from e

    async def fetch_news_content(self, news_id: str | None = None, category: str | None = None, batch: bool | None = None, keyword: str | None = None):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                if category:
                    if not batch:
                        select_query = '''
                            SELECT category, news_id, title, content
                            FROM news
                            WHERE category = %s
                            '''
                        try:
                            await cursor.execute(select_query, (category,))
                            return await cursor.fetchall()
                        except Exception as e:
                            logger.exception("讀取 news 內容（依分類）失敗")
                            raise DatabaseError("讀取 news 內容（依分類）失敗") from e

                if batch:
                    select_query = '''
                        SELECT news_id, title, content
                        FROM news
                        WHERE category = %s
                        '''
                    try:
                        await cursor.execute(select_query, (category,))
                        return await cursor.fetchall()
                    except Exception as e:
                        logger.exception("讀取 news 內容（batch）失敗")
                        raise DatabaseError("讀取 news 內容（batch）失敗") from e

                if news_id:
                    select_query = '''
                        SELECT news_id, title, content, category
                        FROM news
                        WHERE news_id = %s
                        '''
                    try:
                        await cursor.execute(select_query, (news_id,))
                        return await cursor.fetchall()
                    except Exception as e:
                        logger.exception("讀取 news 內容（依 news_id）失敗")
                        raise DatabaseError("讀取 news 內容（依 news_id）失敗") from e

                if keyword:
                    select_query = '''
                        SELECT category, url , news_id, title
                        FROM news
                        WHERE title ILIKE %s
                        OR %s = ANY(keywords)
                        '''
                    try:
                        await cursor.execute(select_query, (f"%{escape_like(keyword)}%", keyword))
                        result = await cursor.fetchall()
                        return result if result else None
                    except Exception as e:
                        logger.exception("讀取 news 內容（依關鍵字）失敗")
                        raise DatabaseError("讀取 news 內容（依關鍵字）失敗") from e

    async def web_fetch_news(self):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                            SELECT news_id AS id, title AS title, category AS category, article_image AS img
                            FROM news
                            '''
                try:
                    await cursor.execute(select_query)
                    return await cursor.fetchall()
                except Exception as e:
                    logger.exception("讀取新聞列表失敗")
                    raise DatabaseError("讀取新聞列表失敗") from e

    async def web_fetch_news_contents(self, news_id: str):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                            SELECT news_id AS id, title AS title, category AS category, article_image AS img,content AS content
                            FROM news
                            WHERE news_id = %s
                            '''
                try:
                    await cursor.execute(select_query, (news_id,))
                    return await cursor.fetchall()
                except Exception as e:
                    logger.exception("讀取新聞內容失敗")
                    raise DatabaseError("讀取新聞內容失敗") from e

    async def web_search_news(self, keyword: str):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                # 標題、內文、關鍵字任一個含有搜尋字串（不分大小寫、部分比對）就算符合。
                # 內文是爬蟲留下的 HTML，比對前先用 regexp_replace 去掉標籤與註解，
                # 否則搜尋 "p"、"img"、"href" 會因為比對到標籤而列出一堆不相關的新聞。
                select_query = '''
                            SELECT news_id AS id, title AS title, category AS category, article_image AS img
                            FROM news
                            WHERE title ILIKE %s
                            OR regexp_replace(content, '<[^>]*>', '', 'g') ILIKE %s
                            OR EXISTS (SELECT 1 FROM unnest(keywords) AS k WHERE k ILIKE %s)
                            '''
                pattern = f"%{escape_like(keyword)}%"
                try:
                    await cursor.execute(select_query, (pattern, pattern, pattern))
                    return await cursor.fetchall()
                except Exception as e:
                    logger.exception("搜尋新聞失敗")
                    raise DatabaseError("搜尋新聞失敗") from e

    async def sandbox_fetch_news(self):
        """給 /api/sandbox（不耗用 Gemini 配額的示範端點）用的新聞列表，
        只開放 SANDBOX_CATEGORIES 這個子集。"""
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                            SELECT news_id AS id, title AS title, category AS category, article_image AS img
                            FROM news
                            WHERE category = ANY(%s)
                            '''
                try:
                    await cursor.execute(select_query, (SANDBOX_CATEGORIES,))
                    return await cursor.fetchall()
                except Exception as e:
                    logger.exception("讀取 sandbox 新聞列表失敗")
                    raise DatabaseError("讀取 sandbox 新聞列表失敗") from e
