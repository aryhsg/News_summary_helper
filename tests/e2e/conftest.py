"""Playwright 前端 E2E 測試的共用設定。

跑之前要先起測試環境（獨立於正式環境，資料庫只有固定測試資料）：
    docker compose -f tests/e2e/docker-compose.e2e.yml up -d --build
執行：
    pytest tests/e2e
不要跟 tests/ 底下其他 pytest-asyncio 的測試放在同一次執行（見 pytest.ini）。
"""
import json
import os
from pathlib import Path

import pytest
import requests

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8080")
API_KEY = "e2e-test-key-not-a-secret"  # 與 docker-compose.e2e.yml 的 INTERNAL_API_KEY 一致
DATA_FILE = Path(__file__).parent / "data" / "sample_news.json"

CATEGORIES = [
    "要聞", "國際", "證券", "期貨", "理財", "房市",
    "兩岸", "金融", "專欄", "專題", "商情", "產業",
]


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session", autouse=True)
def _stack_is_up():
    try:
        requests.get(f"{BASE_URL}/", timeout=5).raise_for_status()
    except Exception as exc:
        pytest.exit(
            f"連不到測試環境 {BASE_URL}（{exc}）。請先執行：\n"
            "  docker compose -f tests/e2e/docker-compose.e2e.yml up -d --build",
            returncode=2,
        )


@pytest.fixture(scope="session")
def sample():
    """tests/e2e/data/sample_news.json：灌進測試資料庫的固定資料。"""
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def news_by_id(sample):
    return {n["news_id"]: n for n in sample["news"]}


@pytest.fixture
def api():
    """直接打 API 的 requests session（帶正確金鑰）。"""
    s = requests.Session()
    s.headers.update({"X-API-KEY": API_KEY})
    s.base_url = BASE_URL
    return s


@pytest.fixture(autouse=True)
def _block_external_requests(page):
    """只允許連測試環境本身：擋掉 Google Fonts 與 img.test 等外部請求，
    讓測試不受外網影響，也不會因為等外部資源而變慢。"""
    page.route(lambda url: not url.startswith(BASE_URL), lambda route: route.abort())


def open_home(page):
    """開首頁並等列表載入完成。"""
    page.goto("/")
    page.wait_for_selector(".news-card")


def open_article(page, news_id):
    """開首頁並打開指定新聞的詳情面板。"""
    open_home(page)
    page.locator(f'.news-card[data-id="{news_id}"]').click()
    page.wait_for_selector("#articleBody .article-title")


def click_category(page, name):
    page.locator(f'.nav-item[data-category="{name}"]').click()
