import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from dotenv import load_dotenv

load_dotenv()
from web import fastapi_service
from tests.mockdata import *
from infrastructure import NewsDB
from gemini import gemini_service, gen_summary_lock, get_str_summary, get_formatted_summary
from infrastructure import RedisManager
from web.fastapi_service import create_web_app

db_instance = NewsDB()
gemini_instance = gemini_service()
redis_instance = RedisManager()

web_app = create_web_app(db_instance=db_instance, gemini_instance=gemini_instance, redis_instance=redis_instance)

client = TestClient(web_app)

@pytest.mark.asyncio
async def test_get_news_success(monkeypatch):
    """測試正常抓取新聞列表的情境"""

    # 1. 建立一個非同步的模擬函數，模擬從資料庫抓取新聞列表的行為
    mock_fetch = AsyncMock(return_value=mock_news_data)

    # 2. 核心：將原本的 db_instance.web_fetch_news 替換成我們的模擬函數
    # 這樣測試執行時就不會真的去連 PostgreSQL   
    monkeypatch.setattr(db_instance, "web_fetch_news", mock_fetch)

    # 3. 使用 TestClient 發送 GET 請求到 /api/news 路徑
    response = client.get("/api/news")

    # 4. 驗證回應的狀態碼是 200，表示成功
    assert response.status_code == 200

    # 5. 驗證回應的 JSON 資料與我們模擬的新聞列表相同
    assert response.json()[0]["title"] == "測試要聞新聞標題"


@pytest.mark.asyncio
async def test_get_news_empty(monkeypatch):
    """測試抓取新聞列表但資料庫沒有新聞的情境"""

    # 1. 建立一個非同步的模擬函數，模擬從資料庫抓取新聞列表但回傳空列表
    mock_fetch = AsyncMock(return_value=mock_empty_news_data)

    # 2. 替換原本的 db_instance.web_fetch_news 成我們的模擬函數
    monkeypatch.setattr(db_instance, "web_fetch_news", mock_fetch)

    # 3. 發送 GET 請求到 /api/news 路徑
    response = client.get("/api/news")

    # 4. 驗證回應的狀態碼是 200，表示成功
    assert response.status_code == 200

    # 5. 驗證回應的 JSON 資料是一個空列表
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_news_content_success(monkeypatch):
    """測試正常抓取新聞內容的情境"""

    # 1. 建立一個非同步的模擬函數，模擬從資料庫抓取特定新聞內容的行為
    mock_fetch = AsyncMock(return_value=mock_news_data)  

    # 2. 替換原本的 db_instance.web_fetch_news_contents 成我們的模擬函數
    monkeypatch.setattr(db_instance, "web_fetch_news_contents", mock_fetch)

    # 3. 發送 GET 請求到 /api/news/12345 路徑，這裡的 12345 是我們模擬資料中的新聞 ID
    response = client.get("/api/news/12345")

    # 4. 驗證回應的狀態碼是 200，表示成功
    assert response.status_code == 200

    # 5. 驗證回應的 JSON 資料中的 content 欄位與我們模擬的新聞內容相同
    assert response.json()["content"] == "這是一則要聞測試新聞的內容。"


@pytest.mark.asyncio
async def test_get_news_content_not_found(monkeypatch):
    """測試抓取新聞內容但指定的新聞 ID 不存在的情境"""

    # 1. 建立一個非同步的模擬函數，模擬從資料庫抓取特定新聞內容但回傳空列表
    mock_fetch = AsyncMock(return_value=mock_empty_news_data)  

    # 2. 替換原本的 db_instance.web_fetch_news_contents 成我們的模擬函數
    monkeypatch.setattr(db_instance, "web_fetch_news_contents", mock_fetch)

    # 3. 發送 GET 請求到 /api/news/99999 路徑，這裡的 99999 是一個不存在的新聞 ID
    response = client.get("/api/news/99999")

    # 4. 驗證回應的狀態碼是 404，表示找不到資源
    assert response.status_code == 404

    # 5. 驗證回應的 JSON 資料中的 detail 欄位是 "News not found"
    assert response.json()["detail"] == "News not found"


@pytest.mark.asyncio
async def test_get_news_summary_success(monkeypatch):
    """測試正常抓取新聞摘要的情境"""

    # 1. 建立一個非同步的模擬函數，模擬從資料庫抓取特定新聞摘要的行為
    mock_fetch = AsyncMock(return_value=("測試要聞新聞標題", "測試要聞新聞摘要"))  

    # 2. 替換原本的 db_instance.web_fetch_news_contents 成我們的模擬函數
    monkeypatch.setattr(gen_summary_lock, "generate_summary_with_lock", mock_fetch)

    # 3. 發送 POST 請求到 /api/news/12345/summary 路徑，這裡的 12345 是我們模擬資料中的新聞 ID
    response = client.post("/api/news/12345/summary")

    # 4. 驗證回應的狀態碼是 200，表示成功
    assert response.status_code == 200

    # 5. 驗證回應的 JSON 資料中的 summary 存在
    assert "summary" in response.json()


@pytest.mark.asyncio
async def test_get_news_summary_not_found(monkeypatch):
    """測試抓取新聞摘要但指定的新聞 ID 不存在的情境"""

    # 1. 建立一個非同步的模擬函數，模擬從資料庫抓取特定新聞摘要但回傳 None
    mock_fetch = AsyncMock(return_value=(None, None))  

    def mock_format(text):
        if text is None:
            return ""
        return f"{text}"
    # 2. 替換原本的 gen_summary_lock.generate_summary_with_lock 成我們的模擬函數
    monkeypatch.setattr(gen_summary_lock, "generate_summary_with_lock", mock_fetch)
    monkeypatch.setattr(gen_summary_lock, "advanced_format_summary", mock_format)
    # 3. 發送 POST 請求到 /api/news/99999/summary 路徑，這裡的 99999 是一個不存在的新聞 ID
    response = client.post("/api/news/99999/summary")

    # 4. 驗證回應的狀態碼是 200，表示成功（即使沒有摘要也不會報錯）
    assert response.status_code == 200

    # 5. 驗證回應的 JSON 資料中的 summary 是 None 或者是一個空字符串
    assert response.json()["summary"] in (None, "")


@pytest.mark.asyncio
async def test_get_category_summary_success(monkeypatch):
    """測試正常抓取類別摘要的情境"""

    # 1. 建立一個非同步的模擬函數，模擬從資料庫抓取特定類別摘要的行為
    mock_fetch = AsyncMock(return_value=mock_cate_summary_data)  
    def mock_format(raw_summary: dict):
        if raw_summary is None:
            return ""
        return f"{raw_summary.get('news_summary', '{}')}"
    # 2. 替換原本的 db_instance.fetch_cate_summary 成我們的模擬函數
    monkeypatch.setattr(db_instance, "fetch_cate_summary", mock_fetch)
    monkeypatch.setattr(target=fastapi_service, name="get_formatted_summary", value=mock_format)
    # 3. 發送 POST 請求到 /api/news/summary/要聞 路徑，這裡的 "要聞" 是我們模擬資料中的類別
    response = client.post("/api/news/summary/要聞")

    # 4. 驗證回應的狀態碼是 200，表示成功
    assert response.status_code == 200

    # 5. 驗證回應的 JSON 資料中的 summary 存在
    assert "summary" in response.json()


@pytest.mark.asyncio
async def test_get_category_summary_not_found(monkeypatch):
    """測試抓取類別摘要但指定的類別上無摘要的情境"""

    # 1. 建立一個非同步的模擬函數，模擬從資料庫抓取特定類別摘要但回傳 None
    mock_fetch = AsyncMock(return_value=mock_empty_cate_summary_data)  

    def mock_format(raw_summary: dict):
        if raw_summary is None:
            return ""
        return f"{raw_summary.get('news_summary', '{}')}"
    # 2. 替換原本的 db_instance.fetch_cate_summary 成我們的模擬函數
    monkeypatch.setattr(db_instance, "fetch_cate_summary", mock_fetch)
    monkeypatch.setattr(target=fastapi_service, name="get_formatted_summary", value=mock_format)
    # 3. 發送 POST 請求到 /api/news/summary/不存在 路徑，這裡的 "不存在" 是一個不存在的類別
    response = client.post("/api/news/summary/不存在")

    # 4. 驗證回應的狀態碼是 200，表示成功（即使沒有摘要也不會報錯）
    assert response.status_code == 200

    # 5. 驗證回應的 JSON 資料中的 summary 是 "該類別尚無摘要"
    assert response.json()["summary"] == "該類別尚無摘要"