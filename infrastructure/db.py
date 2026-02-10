import os
from unicodedata import category
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

class NewsDB:
    def __init__(self):
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.host = os.getenv('HOST')
        self.port = os.getenv('PORT')
        self.db_name = os.getenv('DB_NAME')
        self.conninfo = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        self.pool = AsyncConnectionPool(conninfo=self.conninfo, min_size=2, max_size=10, open=False)

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
                    print(f"Error creating table: {e}")

        

    async def insert_news(self,news_list):
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
                    print(f"寫入失敗: {e}")

    async def insert_cate_summary(self,cate_list):
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                insert_query = '''
                    INSERT INTO cate_summary (category, summary)
                    VALUES (%s, %s)
                    '''
                try:
                    await cursor.executemany(insert_query, cate_list)
                    await connection.commit()
                    print(f"成功處理 {len(cate_list)} 筆摘要")
                except Exception as e:
                    print(f"寫入失敗: {e}")       

    async def insert_news_summary(self,news_summary_list):
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
                    print(f"寫入失敗: {e}") 

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
                    result = await cursor.fetchall()
                    return result
                except Exception as e:
                    print(f"讀取失敗: {e}") 
                    return []
    
    async def fetch_specific_summary(self, news_id: int | None = None, category: str | None = None, batch: bool | None = None):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                if news_id:
                    select_query = '''
                        SELECT news_id, news_summary, category
                        FROM single_news_summary
                        WHERE news_id = %s
                        '''
                    
                    try:
                        await cursor.execute(select_query, (news_id,))
                        result = await cursor.fetchall()
                        return result
                    except Exception as e:
                            print(f"讀取失敗: {e}") 
                            return []

                if category:
                    select_query = '''
                        SELECT news_id, news_summary
                        FROM single_news_summary
                        WHERE category = %s
                        '''
                    try:
                        await cursor.execute(select_query, (category,))
                        result = await cursor.fetchall()
                        return result
                    except Exception as e:
                        print(f"讀取失敗: {e}") 
                        return []

    async def fetch_news_content(self, news_id: int | None = None, category: str | None = None, batch: bool | None = None, keyword: str | None = None):
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
                            result = await cursor.fetchall()
                            return result
                        except Exception as e:
                            print(f"讀取失敗: {e}") 
                            return []

                if batch:
                    select_query = '''
                        SELECT news_id, title, content
                        FROM news
                        WHERE category = %s
                        '''
                    try:
                        await cursor.execute(select_query, (category,))
                        result = await cursor.fetchall()
                        return result
                    except Exception as e:
                        print(f"讀取失敗: {e}") 
                        return []

                if news_id:
                    select_query = '''
                        SELECT news_id, title, content, category
                        FROM news
                        WHERE news_id = %s
                        '''
                    try:
                        await cursor.execute(select_query, (news_id,))
                        result = await cursor.fetchall()
                        return result
                    except Exception as e:
                        print(f"讀取失敗: {e}") 
                        return []
                    
                if keyword:
                    select_query = '''
                        SELECT category, url , news_id, title
                        FROM news
                        WHERE %s = ANY(keywords)
                        '''
                    try:
                        await cursor.execute(select_query, (keyword,))
                        result = await cursor.fetchall()
                        if result:
                            return result
                        else: 
                            return None
                    except Exception as e:
                        print(f"讀取失敗: {e}") 
                        return None

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
                    result = await cursor.fetchall()
                    return result
                except Exception as e:
                    print(f"讀取失敗: {e}") 
                    return []

    async def web_fetch_news(self):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                            SELECT news_id AS id, title AS title, category AS category, article_image AS img
                            FROM news
                            '''
                try:
                    await cursor.execute(select_query)
                    result = await cursor.fetchall()
                    return result
                except Exception as e:
                    print(f"讀取失敗: {e}") 
                    return []
                
    async def web_fetch_news_contents(self, news_id: int):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                            SELECT news_id AS id, title AS title, category AS category, article_image AS img,content AS content
                            FROM news
                            WHERE news_id = %s
                            '''
                try:
                    await cursor.execute(select_query, (news_id,))
                    result = await cursor.fetchall()
                    return result
                except Exception as e:
                    print(f"讀取失敗: {e}") 
                    return []

    async def web_search_news(self, keyword: str):
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                select_query = '''
                            SELECT news_id AS id, title AS title, category AS category, article_image AS img
                            FROM news
                            WHERE %s = ANY(keywords)
                            '''
                try:
                    await cursor.execute(select_query, (keyword,))
                    result = await cursor.fetchall()
                    return result
                except Exception as e:
                    print(f"讀取失敗: {e}") 
                    return []

    async def truncate_table(self, table: str):
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
                    print(f"Error deleting table {table}: {e}")