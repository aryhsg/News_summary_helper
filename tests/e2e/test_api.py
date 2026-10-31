"""J. API 層。不經瀏覽器，直接用 HTTP 打測試環境的 API（真實後端 + 固定資料）。"""
import pytest

from conftest import BASE_URL


def url(path):
    return f"{BASE_URL}{path}"


@pytest.mark.parametrize("path", ["/api/news", "/api/news/search?q=a", "/api/news/9838157"])
def test_missing_or_wrong_key_is_rejected(path):
    """J1：沒帶或帶錯 X-API-KEY 一律 403，且回傳 JSON 的 detail。"""
    import requests

    for headers in ({}, {"X-API-KEY": "wrong-key"}):
        r = requests.get(url(path), headers=headers, timeout=10)
        assert r.status_code == 403
        assert "detail" in r.json()


def test_news_list_shape(api, sample):
    """J2：列表回傳全部新聞，欄位與型別正確。"""
    r = api.get(url("/api/news"), timeout=10)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == len(sample["news"])
    for item in items:
        assert set(item) == {"id", "title", "category", "img"}
        assert isinstance(item["id"], int)


def test_news_detail_found_and_not_found(api):
    """J2：詳情存在回 200 並含內文；不存在回 404。"""
    ok = api.get(url("/api/news/9838157"), timeout=10)
    assert ok.status_code == 200
    assert ok.json()["content"]
    missing = api.get(url("/api/news/0000000"), timeout=10)
    assert missing.status_code == 404


def test_summary_for_nonexistent_news_is_404_not_500(api):
    """J3：對不存在的新聞要求摘要，應該回 404，不是 500。
    後端沒找到新聞時仍取 `query_result[0]`，會因為空結果而拋出例外。"""
    r = api.post(url("/api/news/0000000/summary"), timeout=30)
    assert r.status_code == 404


def test_search_requires_query_parameter(api):
    """J4：搜尋沒帶 q 回 422。"""
    assert api.get(url("/api/news/search"), timeout=10).status_code == 422


def test_search_with_sql_metacharacters_is_safe(api, sample):
    """J4：搜尋字串含單引號與 SQL 片段時不出錯、不影響資料。"""
    r = api.get(url("/api/news/search"), params={"q": "'; DROP TABLE news; --"}, timeout=10)
    assert r.status_code == 200
    assert r.json() == []
    assert len(api.get(url("/api/news"), timeout=10).json()) == len(sample["news"])


def test_wrong_http_method_is_rejected(api):
    """J5：用 GET 打只接受 POST 的摘要端點，回 405。"""
    assert api.get(url("/api/news/9838157/summary"), timeout=10).status_code == 405


def test_category_summary_accepts_unusual_category_strings(api):
    """J6：類別摘要端點收到沒看過的類別或特殊字元時，回「尚無摘要」，不是錯誤。"""
    for category in ("不存在的類別", "%27", "%3Cscript%3E"):
        r = api.post(url(f"/api/news/summary/{category}"), timeout=10)
        assert r.status_code == 200
        assert r.json()["summary"] == "該類別尚無摘要"
