
import uvicorn
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
from line_bot.fastapi_service import lifespan, create_app
from gemini import gemini_client
from infrastructure import db
from infrastructure import redis_manager


async def start_all():
    gemini = gemini_client.gemini_service()
    news_db = db.NewsDB()
    redis = redis_manager.RedisManager()
    async with lifespan(db_instance=news_db, gemini_instance=gemini, redis_instance= redis) as (DB, Gemini, Redis):

        app = create_app(db= DB, gemini= Gemini, redis= Redis)

        # 啟動 Web 服務
        config = uvicorn.Config(app, host="0.0.0.0", port=5000)
        server = uvicorn.Server(config)
        await server.serve()

    await asyncio.sleep(0.3)

        


if __name__ == "__main__":
    asyncio.run(start_all())