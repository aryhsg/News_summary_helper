import sys
from pathlib import Path
from dotenv import load_dotenv

# 找到當前檔案所在的目錄，並指名尋找 .env
root_path = Path(__file__).resolve().parent
sys.path.append(str(root_path / "line_bot"))
load_dotenv()


from line_bot import create_line_app
from web import create_web_app
from gemini import gemini_client
from infrastructure import db
from infrastructure import redis_manager



gemini = gemini_client.gemini_service()
news_db = db.NewsDB()
redis = redis_manager.RedisManager()

line_app = create_line_app(db_instance= news_db, gemini_instance= gemini, redis_instance= redis)
web_app = create_web_app(db_instance= news_db, gemini_instance= gemini, redis_instance= redis)




        


