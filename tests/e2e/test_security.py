"""H. 安全性。使用真實後端 + 固定測試資料裡構造的資料（第 2 層）。"""
import pytest

from playwright.sync_api import expect

from conftest import open_article, open_home

XSS_NEWS = "9900001"  # 標題與內文含 <script>、<img onerror>、特殊字元


def test_special_chars_in_title_are_shown_as_text(page, news_by_id):
    """H2：標題含 <script>、& 等字元時，卡片以文字顯示，不被當成標籤。"""
    open_home(page)
    card_title = page.locator(f'.news-card[data-id="{XSS_NEWS}"] .card-title')
    expect(card_title).to_have_text(news_by_id[XSS_NEWS]["title"])
    assert card_title.locator("script").count() == 0


def test_special_chars_in_detail_title_are_shown_as_text(page, news_by_id):
    """H2：詳情面板的標題同樣以文字顯示。"""
    open_article(page, XSS_NEWS)
    expect(page.locator(".article-title")).to_have_text(news_by_id[XSS_NEWS]["title"])
    assert page.locator(".article-title script").count() == 0


def test_malicious_content_does_not_execute_script(page):
    """H1：新聞內文含 <img src=x onerror=alert(1)> 時，開啟詳情不應該執行腳本。
    前端把內文用 innerHTML 直接插入（程式註解說明是為了渲染爬蟲留下的 HTML），
    所以內文若被竄改就能執行腳本（儲存型 XSS 風險）。"""
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    open_article(page, XSS_NEWS)
    page.wait_for_timeout(1000)  # 給 onerror 觸發的時間
    assert not dialogs, f"內文中的腳本被執行了：{dialogs}"


# --- 摘要的兩個寫入點（用攔截請求塞入含攻擊字串的回應，第 1 層）---------------------
# 摘要是 LLM 依外部新聞內容生成的，後端又沒有跳脫，所以前端必須自己擋。

PAYLOAD = "<img src=x onerror=alert('xss')>"


def _json(route, body):
    import json

    route.fulfill(status=200, content_type="application/json", body=json.dumps(body, ensure_ascii=False))


def test_single_summary_with_onerror_does_not_execute_script(page):
    """H3：單篇摘要含 <img onerror> 時不應執行腳本。"""
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.route("**/api/news/9838157/summary", lambda r: _json(r, {"id": 9838157, "summary": f"<ol><li>內容{PAYLOAD}</li></ol>"}))
    open_article(page, "9838157")
    page.locator("#btnGenerateSummary").click()
    expect(page.locator("#summaryContainer .summary-box")).to_be_visible()
    page.wait_for_timeout(800)
    assert not dialogs, f"單篇摘要中的腳本被執行了：{dialogs}"


def test_category_summary_with_onerror_does_not_execute_script(page):
    """H4：類別摘要含 <img onerror> 時不應執行腳本。"""
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.route("**/api/news/summary/**", lambda r: _json(r, {"category": "期貨", "summary": f"<h3>主題{PAYLOAD}</h3>"}))
    open_home(page)
    page.locator('.nav-item[data-category="期貨"]').click()
    page.locator("#categorySummaryBtn").click()
    expect(page.locator("#categoryModalBody h3")).to_be_visible()
    page.wait_for_timeout(800)
    assert not dialogs, f"類別摘要中的腳本被執行了：{dialogs}"


def test_sanitizing_keeps_legitimate_summary_formatting(page):
    """H5（回歸）：清理不能破壞正常的摘要排版：單篇是編號清單，類別摘要有標題與段落。"""
    open_article(page, "9838157")
    page.locator("#btnGenerateSummary").click()
    expect(page.locator("#summaryContainer .summary-box ol li")).to_have_count(3)

    page.keyboard.press("Escape")
    page.locator('.nav-item[data-category="期貨"]').click()
    page.locator("#categorySummaryBtn").click()
    body = page.locator("#categoryModalBody")
    expect(body.locator("h3").first).to_be_visible()
    expect(body.locator("p").first).to_be_visible()


def test_sanitizing_keeps_real_article_formatting(page):
    """H5（回歸）：清理不能破壞真實新聞內文的段落與連結。"""
    open_article(page, "9838157")
    content = page.locator(".article-content")
    assert content.locator("p").count() >= 1
    assert "<p>" not in content.inner_text()
