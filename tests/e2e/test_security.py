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


@pytest.mark.xfail(strict=True, reason="DEF-01：renderArticlePanel 以 innerHTML 直接插入 article.content，內文含 <img onerror> 時腳本會執行（儲存型 XSS 風險）")
def test_malicious_content_does_not_execute_script(page):
    """H1：新聞內文含 <img src=x onerror=alert(1)> 時，開啟詳情不應該執行腳本。
    前端把內文用 innerHTML 直接插入（程式註解說明是為了渲染爬蟲留下的 HTML），
    所以內文若被竄改就能執行腳本（儲存型 XSS 風險）。"""
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    open_article(page, XSS_NEWS)
    page.wait_for_timeout(1000)  # 給 onerror 觸發的時間
    assert not dialogs, f"內文中的腳本被執行了：{dialogs}"
