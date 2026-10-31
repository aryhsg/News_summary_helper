"""G. 錯誤處理、F5 快取。用攔截請求模擬後端狀況（第 1 層）：
真實後端很難製造 403、503、網路中斷、前後兩次回應不同這些情況。"""
import json
import re

import pytest

from playwright.sync_api import expect

from conftest import click_category, open_home


def fulfill_json(route, status, body):
    route.fulfill(status=status, content_type="application/json", body=json.dumps(body, ensure_ascii=False))


def test_empty_list_shows_empty_state(page):
    """A4：列表 API 回空陣列時顯示空狀態，側邊欄數字為 0。"""
    page.route("**/api/news", lambda r: fulfill_json(r, 200, []))
    page.goto("/")
    expect(page.locator(".state-box")).to_be_visible()
    expect(page.locator(".news-card")).to_have_count(0)
    expect(page.locator("#nav-count-all")).to_have_text("0")


def test_403_shows_banner_and_empty_state(page):
    """G1：金鑰驗證失敗時顯示橫幅與無法載入的說明，側邊欄數字歸零。"""
    page.route("**/api/news", lambda r: fulfill_json(r, 403, {"detail": "Access Denied"}))
    page.goto("/")
    expect(page.locator("#statusBanner")).to_be_visible()
    expect(page.locator("#statusBanner")).to_contain_text("API 金鑰驗證失敗")
    expect(page.locator(".state-box")).to_contain_text("目前無法載入新聞列表")
    expect(page.locator("#nav-count-all")).to_have_text("0")


@pytest.mark.xfail(strict=True, reason="DEF-08：403 的使用者訊息提到 config.js 與 API_KEY（app.js 的 ApiError）")
def test_403_message_does_not_leak_developer_details(page):
    """G1：給一般使用者看的錯誤訊息不該出現 config.js 這類開發用語。"""
    page.route("**/api/news", lambda r: fulfill_json(r, 403, {"detail": "Access Denied"}))
    page.goto("/")
    expect(page.locator("#statusBanner")).to_be_visible()
    assert "config.js" not in page.locator("#statusBanner").inner_text()


def test_503_shows_database_unavailable(page):
    """G2：資料庫暫時無法使用（503）時，橫幅顯示後端回傳的說明。"""
    page.route("**/api/news", lambda r: fulfill_json(r, 503, {"detail": "資料庫暫時無法使用，請稍後再試"}))
    page.goto("/")
    expect(page.locator("#statusBanner")).to_contain_text("資料庫暫時無法使用")


def test_network_failure_shows_banner(page):
    """G3：連不上後端時顯示橫幅。"""
    page.route("**/api/news", lambda r: r.abort())
    page.goto("/")
    expect(page.locator("#statusBanner")).to_contain_text("無法連線到後端伺服器")


@pytest.mark.xfail(strict=True, reason="DEF-09：連線失敗的使用者訊息提到 CORS、API_BASE（app.js 的 ApiError）")
def test_network_failure_message_does_not_leak_developer_details(page):
    """G3：連線失敗訊息不該提到 CORS、API_BASE 這類開發用語。"""
    page.route("**/api/news", lambda r: r.abort())
    page.goto("/")
    expect(page.locator("#statusBanner")).to_be_visible()
    text = page.locator("#statusBanner").inner_text()
    assert "CORS" not in text and "API_BASE" not in text


def test_search_error_shows_message_and_recovers(page):
    """G4：搜尋途中出錯顯示錯誤；後端恢復後，再搜尋能正常顯示結果。"""
    open_home(page)
    page.route("**/api/news/search**", lambda r: fulfill_json(r, 503, {"detail": "資料庫暫時無法使用，請稍後再試"}))
    page.locator("#searchInput").fill("台指期")
    expect(page.locator(".state-box")).to_contain_text("搜尋時發生錯誤")

    page.unroute("**/api/news/search**")
    page.locator("#searchInput").fill("台指期順勢")
    expect(page.locator(".state-box")).to_contain_text("找不到符合搜尋條件的新聞")
    page.locator("#searchInput").fill("台指期")
    expect(page.locator(".news-card")).to_have_count(2)


@pytest.mark.xfail(strict=True, reason="DEF-07：前端把「該類別尚無摘要」也存進 categorySummaryCache，之後後端產生了也要重新整理頁面才看得到")
def test_category_summary_note_is_not_cached_forever(page):
    """F5：類別摘要一開始「尚無摘要」，之後後端產生了，同一個頁面再開應該看到新內容。
    前端把「尚無摘要」也存進快取，所以要重新整理頁面才會更新。"""
    answers = iter([
        {"category": "兩岸", "summary": "該類別尚無摘要"},
        {"category": "兩岸", "summary": "<p>新的兩岸趨勢摘要</p>"},
    ])
    page.route("**/api/news/summary/**", lambda r: fulfill_json(r, 200, next(answers)))
    open_home(page)
    click_category(page, "兩岸")

    page.locator("#categorySummaryBtn").click()
    expect(page.locator("#categoryModalBody")).to_contain_text("還沒有針對")
    page.keyboard.press("Escape")

    page.locator("#categorySummaryBtn").click()
    expect(page.locator("#categoryModalBody")).to_contain_text("新的兩岸趨勢摘要")


def test_failed_category_summary_is_not_cached(page):
    """F6：類別摘要請求失敗時不快取，再按一次會重新請求並成功。"""
    answers = iter([
        (503, {"detail": "資料庫暫時無法使用，請稍後再試"}),
        (200, {"category": "期貨", "summary": "<p>期貨趨勢</p>"}),
    ])
    page.route("**/api/news/summary/**", lambda r: fulfill_json(r, *next(answers)))
    open_home(page)
    click_category(page, "期貨")

    page.locator("#categorySummaryBtn").click()
    expect(page.locator("#categoryModalBody")).to_contain_text("資料庫暫時無法使用")
    page.keyboard.press("Escape")

    page.locator("#categorySummaryBtn").click()
    expect(page.locator("#categoryModalBody")).to_contain_text("期貨趨勢")
