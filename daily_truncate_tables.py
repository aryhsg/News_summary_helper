from infrastructure.db import NewsDB
import asyncio
from dotenv import load_dotenv
load_dotenv()

db = NewsDB()

async def main():
    await db.pool_init()
        # 在此處可以呼叫其他方法進行測試
    await db.truncate_table('news')
    await db.pool_close()

if __name__ == "__main__":
    asyncio.run(main())