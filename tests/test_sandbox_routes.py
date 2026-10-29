"""
Stage 5 回歸測試：確認 /api/test/... 已經改名成 /api/sandbox/...，
新路徑可用、舊路徑不再存在。
"""
import pytest
from unittest.mock import AsyncMock

from tests.mockdata import mock_news_data


@pytest.mark.asyncio
async def test_sandbox_news_list_success(monkeypatch):
    from tests.test_main import client, db_instance, headers

    monkeypatch.setattr(db_instance, "sandbox_fetch_news", AsyncMock(return_value=mock_news_data))
    response = client.get("/api/sandbox/news", headers=headers)
    assert response.status_code == 200
    assert response.json()[0]["title"] == "測試要聞新聞標題"


@pytest.mark.asyncio
async def test_old_test_prefixed_route_no_longer_exists():
    from tests.test_main import client, headers

    response = client.get("/api/test/news", headers=headers)
    assert response.status_code == 404
