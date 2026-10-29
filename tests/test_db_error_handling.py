"""
Stage 3 回歸測試：確認「DB 呼叫真的失敗」跟「DB 呼叫成功但查到 0 筆」
現在是兩種不同結果，不會都變成同一種空值。
"""
import pytest
from unittest.mock import AsyncMock

from infrastructure.exceptions import DatabaseError
from infrastructure.repositories import NewsRepository


class _FakeCursor:
    def __init__(self, raises=None, rows=None):
        self._raises = raises
        self._rows = rows or []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, *args, **kwargs):
        if self._raises:
            raise self._raises

    async def fetchall(self):
        return self._rows


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def cursor(self, *args, **kwargs):
        return self._cursor


class _FakePool:
    def __init__(self, cursor):
        self._cursor = cursor

    def connection(self):
        return _FakeConnection(self._cursor)


@pytest.mark.asyncio
async def test_repository_raises_database_error_when_query_fails():
    """真的連不上/查詢出錯 -> 要丟 DatabaseError，不能悄悄回傳 []。"""
    repo = NewsRepository(_FakePool(_FakeCursor(raises=RuntimeError("connection lost"))))
    with pytest.raises(DatabaseError):
        await repo.web_fetch_news()


@pytest.mark.asyncio
async def test_repository_returns_empty_list_when_query_succeeds_with_zero_rows():
    """查詢成功、只是沒有符合的資料 -> 回傳空 list，不是例外。"""
    repo = NewsRepository(_FakePool(_FakeCursor(rows=[])))
    result = await repo.web_fetch_news()
    assert result == []


@pytest.mark.asyncio
async def test_web_api_returns_503_when_db_raises_database_error(monkeypatch):
    """Web API 層要把 DatabaseError 轉成 503，不是讓它變成未處理的 500，
    也不能跟「查無資料」混在一起回 200 空陣列。"""
    from tests.test_main import client, db_instance, headers

    monkeypatch.setattr(db_instance, "web_fetch_news", AsyncMock(side_effect=DatabaseError("boom")))
    response = client.get("/api/news", headers=headers)
    assert response.status_code == 503
