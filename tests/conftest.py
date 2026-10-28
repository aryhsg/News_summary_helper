"""確保所有測試檔案在被 collect（import）之前，.env 已經載入。

test_main.py/test_line.py 原本各自呼叫 load_dotenv()，但這只保證自己
檔案內的 import 之前有載入；pytest 的 collection 順序不保證哪個測試檔
先被 import，config.py 現在會在 import 時 fail-fast 檢查必填環境變數，
所以載入 .env 這件事要在這裡統一做一次，不能分散在各測試檔案裡賭順序。
"""
from dotenv import load_dotenv

load_dotenv()
