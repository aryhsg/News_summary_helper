import sys
from pathlib import Path
from dotenv import load_dotenv

# 找到當前檔案所在的目錄，並指名尋找 .env
root_path = Path(__file__).resolve().parent
sys.path.append(str(root_path / "line_bot"))
load_dotenv()

import uvicorn
import asyncio
from line_bot import create_line_app, global_lifespan
from web import create_web_app
from gemini import gemini_client
from infrastructure import db
from infrastructure import redis_manager


async def start_all():
    gemini = gemini_client.gemini_service()
    news_db = db.NewsDB()
    redis = redis_manager.RedisManager()
    async with global_lifespan(db_instance=news_db, gemini_instance=gemini, redis_instance= redis) as (DB, Gemini, Redis):

        line_app = create_line_app(db_instance= DB, gemini_instance= Gemini, redis_instance= Redis)
        web_app = create_web_app(db_instance= DB, gemini_instance= Gemini, redis_instance= Redis)
        # 啟動 line_bot 服務
        line_config = uvicorn.Config(line_app, host="0.0.0.0", port=5000)
        line_server = uvicorn.Server(line_config)
        web_config = uvicorn.Config(web_app, host="0.0.0.0", port=8000, lifespan="on")
        web_server = uvicorn.Server(web_config)

        print("📡 系統啟動中：LINE Bot (5000) & Web API (8000)")
        await asyncio.gather(
            line_server.serve(),
            web_server.serve()
        )

    await asyncio.sleep(0.3)

        


if __name__ == "__main__":
    asyncio.run(start_all())