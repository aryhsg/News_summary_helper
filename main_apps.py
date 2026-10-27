import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 找到當前檔案所在的目錄，並指名尋找 .env
root_path = Path(__file__).resolve().parent
sys.path.append(str(root_path / "line_bot"))
load_dotenv()

# psycopg 的 async 模式在 Windows 預設的 ProactorEventLoop 下無法運作，
# 本機（Windows）直接用 uvicorn 跑這個 app 時需要換成 SelectorEventLoop。
# 另外 Windows 終端機預設編碼（如 cp950）無法印出專案裡的 emoji log，
# 會直接 crash，且跟其他背景執行緒的 log 同時發生時會卡死整個程式，
# 改成強制用 UTF-8 輸出。Linux 部署（VPS）不受影響，不會進到這個分支。
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


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




        


