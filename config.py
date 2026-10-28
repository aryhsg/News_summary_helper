"""資料庫連線設定的單一入口（Stage 1）。

原本 infrastructure/db.py 直接用 os.getenv('USERNAME')/os.getenv('PASSWORD')
讀取資料庫帳密。USERNAME 是 Windows 內建的系統環境變數，python-dotenv 的
load_dotenv() 預設不會覆蓋已經存在的環境變數，導致在 Windows 開發機上，
程式悄悄讀到的是系統登入帳號，而不是 .env 裡設定的資料庫帳號。改名為
DB_USERNAME/DB_PASSWORD 根除這個撞名問題。

HOST/PORT/DB_NAME 本身沒有撞名問題，一起收進這裡純粹是讓資料庫連線設定
只有一個讀取入口，方便之後維護。

部署這個改動前，VPS 上的 .env 需要把 USERNAME/PASSWORD 改名成
DB_USERNAME/DB_PASSWORD，否則服務會因為讀不到環境變數而啟動失敗。
"""
import os


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"環境變數 {name} 未設定")
    return value


DB_USERNAME = _require_env("DB_USERNAME")
DB_PASSWORD = _require_env("DB_PASSWORD")
DB_HOST = _require_env("HOST")
DB_PORT = _require_env("PORT")
DB_NAME = _require_env("DB_NAME")
