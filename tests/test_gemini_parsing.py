"""
回歸測試：針對 gemini/ 底下「schema 跟消費端解析對不上」的幾個 bug，
全部用假資料模擬 Gemini 的回應字串，不呼叫真實 Gemini API。
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from gemini import gen_summary_lock, gen_sig_summary


def _news_summary_json(news_id="123", title="測試標題", contents=("重點一", "重點二")):
    """組一個符合 NewsSummarySchema 形狀的假 Gemini 回應。"""
    return json.dumps(
        {
            "news_id": news_id,
            "title": title,
            "points": [
                {"point_id": i + 1, "content": c} for i, c in enumerate(contents)
            ],
        },
        ensure_ascii=False,
    )


@pytest.mark.asyncio
async def test_generate_summary_with_lock_parses_single_object_not_list():
    """
    NewsSummarySchema 是單一物件（不是 list），"sg" 模式的消費端
    不應該再用 result[0] 去索引，且要從 SinglePoint 取出 content，
    不是把整個 {point_id, content} 字典直接印出來。
    """
    mock_db = AsyncMock()
    mock_db.fetch_specific_summary.return_value = []  # 代表資料庫尚無摘要
    mock_db.fetch_news_content.return_value = [
        {"news_id": "123", "title": "測試標題", "content": "內容", "category": "要聞"}
    ]

    class _FakeLockCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    # RedisManager.get_lock 是用 @asynccontextmanager 包的，呼叫時「直接」回傳
    # context manager（不是 coroutine），所以這裡要用 MagicMock 而不是 AsyncMock，
    # 否則 get_lock(...) 呼叫出來的會是一個 coroutine，用不了 async with / __aenter__。
    mock_redis = MagicMock()
    mock_redis.get_lock = MagicMock(return_value=_FakeLockCtx())

    mock_gemini = AsyncMock()
    mock_gemini.generate_summary.return_value = _news_summary_json(
        news_id="123", contents=("第一個重點內容", "第二個重點內容")
    )

    title, summary_str = await gen_summary_lock.generate_summary_with_lock(
        news_id=123, db_instance=mock_db, redis_instance=mock_redis, gemini_instance=mock_gemini
    )

    assert title == "測試標題"
    assert summary_str == "1. 第一個重點內容\n2. 第二個重點內容\n"

    # 存回資料庫時也要用正確解析出來的 news_id/摘要文字，而不是索引出錯造成的壞資料。
    mock_db.insert_news_summary.assert_awaited_once_with(
        [("123", "1. 第一個重點內容\n2. 第二個重點內容\n", "要聞")]
    )


@pytest.mark.asyncio
async def test_batch_gen_sum_n_store_extracts_point_content(monkeypatch):
    """
    batch 模式的回應是一個 list（每個元素是 NewsSummarySchema 形狀），
    每個 point 要取出 content 欄位，不是把整個 SinglePoint 字典印出來。
    """
    # 跳過真實的冷卻 sleep(5)，測試只關心解析邏輯對不對。
    monkeypatch.setattr(gen_sig_summary.asyncio, "sleep", AsyncMock())

    mock_db = AsyncMock()
    mock_db.fetch_news_content.return_value = [
        {"news_id": "111", "title": "新聞一", "content": "內容一"},
    ]
    mock_db.fetch_specific_summary.return_value = []  # 尚未有摘要，需要生成

    class _FakeLockCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    mock_redis = MagicMock()
    mock_redis.get_lock = MagicMock(return_value=_FakeLockCtx())

    mock_gemini = AsyncMock()
    mock_gemini.generate_summary.return_value = json.dumps(
        [
            {
                "news_id": "111",
                "title": "新聞一",
                "points": [
                    {"point_id": 1, "content": "批次重點A"},
                    {"point_id": 2, "content": "批次重點B"},
                ],
            }
        ],
        ensure_ascii=False,
    )

    await gen_sig_summary.batch_gen_sum_n_store(
        category="要聞",
        DB_instance=mock_db,
        gemini_instance=mock_gemini,
        redis_manager_instance=mock_redis,
    )

    mock_db.insert_news_summary.assert_awaited_once_with(
        news_summary_list=[("111", "1. 批次重點A\n2. 批次重點B", "要聞")]
    )
