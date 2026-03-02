import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from dotenv import load_dotenv

load_dotenv()
from line_bot import line_forward_rules, line_service
from gemini import gen_summary_lock





@pytest.mark.asyncio
async def test_line_postback_summary_flow(monkeypatch):
    # 1. 初始化 class
    mock_db = AsyncMock()
    forwarder = line_forward_rules(mock_db, AsyncMock(), AsyncMock())

    # 2. 準備假資料
    mock_db.fetch_cate_summary.return_value = [{"original": "data_from_db"}]
    
    # 3. 掉包 get_str_summary
    # 注意：這個函式是從 gemini 匯入到你的 forward_rules 檔案中的
    # 假設你的檔案路徑是 line_bot/forward_rules.py    
    def mock_get_str(raw_summary):
        return "這是被 Monkeypatch 蓋掉的假摘要"
    
    monkeypatch.setattr(line_service, "get_str_summary", mock_get_str)

    # 4. 攔截 HTTP 請求 (httpx)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        PAYLOAD_CATE_SUMMARY = {
            "events": [{
                "type": "postback",
                "postback": {"data": "金融_摘要"},
                "replyToken": "test_token"
            }]
        }
        
        # 執行
        await forwarder.forward_rule(PAYLOAD_CATE_SUMMARY)
        
        # 5. 驗證
        # 檢查發送給 LINE 的 JSON 裡面，text 欄位是否等於我們設定的假摘要
        args, kwargs = mock_post.call_args
        sent_json = kwargs["json"]
        # 這裡要根據你 Flex Message 的結構去層層抓取，或是用 str() 暴力檢查
        assert "這是被 Monkeypatch 蓋掉的假摘要" in str(sent_json)


@pytest.mark.asyncio
async def test_line_no_data_scenario(monkeypatch):
    # 初始化
    mock_db = AsyncMock(return_value=[]) # 模擬資料庫回傳空列表
    mock_db.fetch_news_content.return_value = []
    forwarder = line_forward_rules(mock_db, AsyncMock(), AsyncMock())

    PAYLOAD_KEYWORD_SEARCH = {
    "events": [{
        "type": "message",
        "replyToken": "token_keyword",
        "message": {
            "type": "text",
            "text": "台積電"
        },
        "source": {"userId": "user_123"}
        }]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # 測試「關鍵字查無新聞」
        await forwarder.forward_rule(PAYLOAD_KEYWORD_SEARCH)
        
        # 驗證是否呼叫了 text_message 分支發送「此關鍵字尚無新聞」
        args, kwargs = mock_post.call_args
        assert "此關鍵字尚無新聞" in str(kwargs["json"])


@pytest.mark.asyncio
async def test_line_single_news_summary_flow(monkeypatch):
    """測試使用者點擊單則新聞 URL 時，是否能正確觸發 AI 摘要並回覆"""
    
    # 2. 初始化 Mock 對象
    mock_db = AsyncMock()
    mock_gemini = AsyncMock()
    mock_redis = AsyncMock()
    
    forwarder = line_forward_rules(mock_db, mock_gemini, mock_redis)

    # 3. Mock 關鍵函式：generate_summary_with_lock
    # 這是你在 line_forward_rules 檔案開頭匯入的
    
    # 模擬回傳標題與摘要內容
    mock_gen_summary = AsyncMock(return_value=("測試新聞標題", "這是 AI 生成的新聞摘要內容"))
    monkeypatch.setattr(gen_summary_lock, "generate_summary_with_lock", mock_gen_summary)

    PAYLOAD_SINGLE_NEWS_SUMMARY = {
    "events": [{
        "type": "postback",
        "replyToken": "token_single_news",
        "postback": {
            "data": "https://news.example.com/20260302_12345"
        },
        "source": {"userId": "user_123"}
        }]
    }

    # 4. 攔截 HTTP 請求 (httpx)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 5. 執行被測試的函式
        await forwarder.forward_rule(PAYLOAD_SINGLE_NEWS_SUMMARY)

        # 6. 驗證邏輯
        # A. 檢查是否正確提取了 news_id (從 URL 最後一段)
        mock_gen_summary.assert_called_once()
        args, kwargs = mock_gen_summary.call_args
        assert kwargs["news_id"] == "20260302_12345"

        # B. 檢查發送給 LINE 的 JSON 內容
        call_args, call_kwargs = mock_post.call_args
        sent_json = call_kwargs["json"]
        
        # 驗證回傳的 Flex Message 是否包含我們 Mock 的標題與摘要
        assert "測試新聞標題" in str(sent_json)
        assert "這是 AI 生成的新聞摘要內容" in str(sent_json)