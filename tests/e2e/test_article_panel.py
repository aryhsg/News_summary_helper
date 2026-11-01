"""D. 詳情面板。使用真實後端 + 固定測試資料（第 2 層）。"""
import pytest

from playwright.sync_api import expect

from conftest import open_article, open_home

ARTICLE = "9838157"       # 要聞、內文帶 <p> 與 <!--N--> 註解、已有摘要
LONG_BODY = "9838308"     # 內文約 7,900 字
LONG_TITLE = "9900003"    # 標題為超長無空白英文字串


def test_open_article_shows_title_category_and_content(page, news_by_id):
    """D1：點卡片開啟面板，顯示標題、類別、內文。"""
    open_article(page, ARTICLE)
    expect(page.locator("#articlePanel")).to_be_visible()
    expect(page.locator(".article-title")).to_have_text(news_by_id[ARTICLE]["title"])
    expect(page.locator("#articleCat")).to_have_text("要聞")
    expect(page.locator(".article-content")).not_to_be_empty()


def test_html_in_content_is_rendered_not_shown_as_text(page):
    """D2：爬蟲留下的 <p>、<!--N--> 要被渲染成段落，畫面上不能出現字面的標籤。"""
    open_article(page, ARTICLE)
    assert page.locator(".article-content p").count() >= 1
    text = page.locator(".article-content").inner_text()
    assert "<p>" not in text
    assert "<!--" not in text


def test_long_content_scrolls_inside_panel(page):
    """D3：內文極長時，面板內可捲動，且不產生橫向捲動。"""
    open_article(page, LONG_BODY)
    body = page.locator("#articlePanel .panel-body")
    sizes = body.evaluate(
        "el => ({sh: el.scrollHeight, ch: el.clientHeight, sw: el.scrollWidth, cw: el.clientWidth})"
    )
    assert sizes["sh"] > sizes["ch"], "長內文應該超出可視高度"
    assert sizes["sw"] <= sizes["cw"] + 1, "不應有橫向捲動"
    body.evaluate("el => el.scrollTo(0, el.scrollHeight)")
    assert body.evaluate("el => el.scrollTop") > 0


def test_close_with_button(page):
    """D4：按 ✕ 關閉。"""
    open_article(page, ARTICLE)
    page.locator("#articleClose").click()
    expect(page.locator("#articlePanel")).to_be_hidden()
    expect(page.locator("#articleOverlay")).to_be_hidden()


def test_close_with_escape(page):
    """D4：按 Esc 關閉。"""
    open_article(page, ARTICLE)
    page.keyboard.press("Escape")
    expect(page.locator("#articlePanel")).to_be_hidden()


def test_close_by_clicking_overlay(page):
    """D4：點遮罩關閉。"""
    open_article(page, ARTICLE)
    page.locator("#articleOverlay").click(position={"x": 5, "y": 5})
    expect(page.locator("#articlePanel")).to_be_hidden()


def test_very_long_unbroken_title_does_not_overflow_page(page):
    """D6：標題是一長串沒有空白的英文時，不應該撐破版面造成頁面橫向捲動。"""
    open_home(page)
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 1, f"頁面橫向溢出 {overflow}px"
    card = page.locator(f'.news-card[data-id="{LONG_TITLE}"] .card-title')
    fits = card.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    assert fits, "超長標題超出卡片寬度"
