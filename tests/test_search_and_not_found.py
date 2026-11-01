"""搜尋的 LIKE 跳脫（DEF-03）與「新聞不存在」的處理（DEF-05）。"""
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from dotenv import load_dotenv

load_dotenv()
from gemini import locking
from infrastructure.exceptions import NewsNotFoundError
from infrastructure.repositories.news_repository import escape_like
from line_bot import line_forward_rules


# --- DEF-03：LIKE 萬用字元跳脫 -------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("台指期", "台指期"),                # 一般字串不變
    ("50%", "50\\%"),                    # % 變成字面的 %
    ("a_b", "a\\_b"),                    # _ 變成字面的 _
    ("a\\b", "a\\\\b"),                  # 反斜線本身也要跳脫，否則使用者能自己「逃出」
    ("%_\\", "\\%\\_\\\\"),
    ("", ""),
])
def test_escape_like(raw, expected):
    assert escape_like(raw) == expected


# --- DEF-05：新聞不存在 -------------------------------------------------------

class _FakeRedis:
    @asynccontextmanager
    async def get_lock(self, news_id, timeout=60):
        yield


@pytest.mark.asyncio
async def test_generate_summary_raises_when_news_does_not_exist():
    """查不到新聞時要丟 NewsNotFoundError，而且不能呼叫 Gemini。"""
    db = AsyncMock()
    db.fetch_specific_summary.return_value = []   # 沒有現成摘要
    db.fetch_news_content.return_value = []       # 新聞本身也不存在
    gemini = AsyncMock()

    with pytest.raises(NewsNotFoundError):
        await locking.generate_summary_with_lock(
            news_id="0000000", db_instance=db, redis_instance=_FakeRedis(), gemini_instance=gemini
        )
    gemini.generate_summary.assert_not_called()


def test_web_api_returns_404_when_news_does_not_exist(monkeypatch):
    """Web API 把 NewsNotFoundError 轉成 404（原本是 500）。"""
    from tests.test_main import client, headers

    monkeypatch.setattr(locking, "generate_summary_with_lock", AsyncMock(side_effect=NewsNotFoundError("0")))
    response = client.post("/api/news/0/summary", headers=headers)
    assert response.status_code == 404
    assert "找不到" in response.json()["detail"]


@pytest.mark.asyncio
async def test_line_replies_expired_message_when_news_does_not_exist(monkeypatch):
    """LINE 舊按鈕指到已被清掉的新聞時，要回覆「已過期」，不是靜默沒有回應。"""
    forwarder = line_forward_rules(AsyncMock(), AsyncMock(), AsyncMock())
    monkeypatch.setattr(locking, "generate_summary_with_lock", AsyncMock(side_effect=NewsNotFoundError("1")))

    payload = {"events": [{
        "type": "postback",
        "postback": {"data": "https://money.udn.com/money/story/5612/1"},
        "replyToken": "test_token",
    }]}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        await forwarder.forward_rule(payload)

    sent = mock_post.call_args.kwargs["json"]
    assert "已過期" in sent["messages"][0]["text"]
