"""Gemini 回應無法使用時的處理：輸出被截斷、JSON 格式錯誤、思考設定。

背景：單篇摘要的 max_output_tokens 原本是 2048，而思考 token 也算在這個上限裡，
長文章思考就能用掉 1700 多，輸出被攔腰截斷，json.loads 失敗，使用者看到 500。
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv
from google.genai import types

load_dotenv()
from gemini import generation, locking
from gemini.client import SG_THINKING_LEVEL, gemini_service
from infrastructure.exceptions import GeminiResponseError
from line_bot import line_forward_rules

GOOD_JSON = json.dumps({"news_id": "1", "title": "t", "points": [{"point_id": 1, "content": "第一點"}]}, ensure_ascii=False)


def fake_response(text=GOOD_JSON, finish=types.FinishReason.STOP):
    return SimpleNamespace(text=text, candidates=[SimpleNamespace(finish_reason=finish)], usage_metadata=None)


def service_returning(response):
    ai = gemini_service()
    ai._do_generate_content = AsyncMock(return_value=response)
    return ai


# --- client：思考設定與回應檢查 -------------------------------------------------

@pytest.mark.asyncio
async def test_single_summary_uses_low_thinking_and_a_large_output_budget():
    ai = service_returning(fake_response())
    await ai.generate_summary("sg", "內容")
    config = ai._do_generate_content.call_args.kwargs["config"]
    assert config.thinking_config.thinking_level == SG_THINKING_LEVEL == types.ThinkingLevel.LOW
    assert config.max_output_tokens >= 8192


@pytest.mark.asyncio
async def test_category_summary_keeps_the_models_default_thinking():
    """類別摘要要跨多篇找趨勢，需要推理，不套用低思考。"""
    ai = service_returning(fake_response())
    await ai.generate_summary("cate", "內容")
    config = ai._do_generate_content.call_args.kwargs["config"]
    assert config.thinking_config is None


@pytest.mark.asyncio
@pytest.mark.parametrize("finish", [types.FinishReason.MAX_TOKENS, types.FinishReason.SAFETY])
async def test_response_that_did_not_finish_normally_raises(finish):
    ai = service_returning(fake_response(text='{"news_id": "1", "po', finish=finish))
    with pytest.raises(GeminiResponseError):
        await ai.generate_summary("sg", "內容")


@pytest.mark.asyncio
async def test_empty_response_raises():
    ai = service_returning(fake_response(text=""))
    with pytest.raises(GeminiResponseError):
        await ai.generate_summary("sg", "內容")


@pytest.mark.asyncio
async def test_normal_response_is_returned_unchanged():
    ai = service_returning(fake_response())
    assert await ai.generate_summary("sg", "內容") == GOOD_JSON


# --- generation：解析失敗與重試 ----------------------------------------------------

@pytest.mark.asyncio
async def test_single_summary_retries_once_when_json_is_malformed():
    gemini = AsyncMock()
    gemini.generate_summary.side_effect = ['{"news_id": "1", "po', GOOD_JSON]
    news_id, summary = await generation.generate_single_summary(gemini, "{}")
    assert gemini.generate_summary.call_count == 2
    assert news_id == "1" and "第一點" in summary


@pytest.mark.asyncio
async def test_single_summary_retries_when_client_reports_truncation():
    gemini = AsyncMock()
    gemini.generate_summary.side_effect = [GeminiResponseError("MAX_TOKENS"), GOOD_JSON]
    news_id, _ = await generation.generate_single_summary(gemini, "{}")
    assert gemini.generate_summary.call_count == 2
    assert news_id == "1"


@pytest.mark.asyncio
async def test_single_summary_gives_up_after_two_failures():
    gemini = AsyncMock()
    gemini.generate_summary.return_value = '{"broken'
    with pytest.raises(GeminiResponseError):
        await generation.generate_single_summary(gemini, "{}")
    assert gemini.generate_summary.call_count == 2


@pytest.mark.asyncio
async def test_batch_summary_wraps_malformed_json():
    gemini = AsyncMock()
    gemini.generate_summary.return_value = "[{"
    with pytest.raises(GeminiResponseError):
        await generation.generate_batch_summaries(gemini, "[]")


# --- Web API 與 LINE：使用者看到的結果 -----------------------------------------------

def test_web_api_returns_502_with_a_friendly_message(monkeypatch):
    from tests.test_main import client, headers

    monkeypatch.setattr(locking, "generate_summary_with_lock", AsyncMock(side_effect=GeminiResponseError("x")))
    response = client.post("/api/news/1/summary", headers=headers)
    assert response.status_code == 502
    assert "稍後再試" in response.json()["detail"]


@pytest.mark.asyncio
async def test_line_replies_when_summary_generation_fails(monkeypatch):
    forwarder = line_forward_rules(AsyncMock(), AsyncMock(), AsyncMock())
    monkeypatch.setattr(locking, "generate_summary_with_lock", AsyncMock(side_effect=GeminiResponseError("x")))
    payload = {"events": [{
        "type": "postback",
        "postback": {"data": "https://money.udn.com/money/story/5612/1"},
        "replyToken": "test_token",
    }]}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        await forwarder.forward_rule(payload)
    assert "稍後再試" in mock_post.call_args.kwargs["json"]["messages"][0]["text"]
