"""E. 單篇摘要、F. 類別摘要。使用真實後端 + 固定測試資料（第 2 層）。

測試環境的 Gemini 是假金鑰：已預先灌入摘要的新聞直接讀資料庫；沒有摘要的新聞
點擊生成會失敗，正好用來測錯誤畫面，也不會花到真實額度。
"""
import re

import pytest

from playwright.sync_api import expect

from conftest import click_category, open_article, open_home

HAS_SUMMARY = "9838157"       # 已有真實摘要
NO_SUMMARY = "9837670"        # 沒有摘要，生成會失敗
SUMMARY_SPECIAL_CHARS = "9900002"  # 摘要內含 HTML 特殊字元


def generate(page):
    page.locator("#btnGenerateSummary").click()


def test_existing_summary_is_shown_without_calling_gemini(page):
    """E1：已有摘要的新聞，點生成直接看到摘要，按鈕文字改變。"""
    open_article(page, HAS_SUMMARY)
    generate(page)
    box = page.locator("#summaryContainer .summary-box")
    expect(box).to_be_visible()
    expect(box).to_contain_text("味全龍")
    expect(page.locator("#btnGenerateSummary")).to_have_text("重新查看 AI 摘要")
    expect(page.locator("#summaryColumn")).to_be_visible()


def test_generation_failure_shows_error_and_allows_retry(page):
    """E3：沒有摘要的新聞生成失敗時，顯示錯誤、不殘留載入動畫，按鈕恢復可再按。"""
    open_article(page, NO_SUMMARY)
    generate(page)
    state = page.locator("#summaryContainer .state-box")
    expect(state).to_contain_text("伺服器發生錯誤")
    expect(page.locator("#summaryContainer .spinner")).to_have_count(0)
    expect(page.locator("#btnGenerateSummary")).to_be_enabled()


def test_reopening_article_resets_summary_column(page):
    """E4：關掉再開同一篇，摘要欄回到收起狀態，按鈕文字也恢復。"""
    open_article(page, HAS_SUMMARY)
    generate(page)
    expect(page.locator("#summaryContainer .summary-box")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#articlePanel")).to_be_hidden()

    page.locator(f'.news-card[data-id="{HAS_SUMMARY}"]').click()
    page.wait_for_selector("#articleBody .article-title")
    expect(page.locator("#summaryColumn")).to_be_hidden()
    expect(page.locator("#btnGenerateSummary")).to_have_text("生成 AI 摘要")


@pytest.mark.xfail(strict=True, reason="DEF-02：後端回傳的摘要沒有跳脫 HTML、前端又以 innerHTML 插入，<b> 等標籤會被渲染")
def test_summary_with_html_special_chars_is_not_interpreted(page):
    """E6：摘要裡的 <script>、<b> 應該以文字顯示，不能被當成標籤執行或渲染。"""
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    open_article(page, SUMMARY_SPECIAL_CHARS)
    generate(page)
    box = page.locator("#summaryContainer .summary-box")
    expect(box).to_be_visible()
    assert not dialogs, f"摘要觸發了對話框：{dialogs}"
    assert box.locator("b").count() == 0, "<b> 被渲染成粗體標籤，而不是顯示成文字"
    assert "<b>" in box.inner_text()


# --- F. 類別摘要 ---------------------------------------------------------------

def open_category_summary(page, category):
    open_home(page)
    click_category(page, category)
    page.locator("#categorySummaryBtn").click()
    expect(page.locator("#categoryModal")).to_be_visible()


def test_category_summary_requires_a_category(page):
    """F1：沒選分類就按「生成分類摘要」，出現提示且不開視窗。"""
    open_home(page)
    page.locator("#categorySummaryBtn").click()
    expect(page.locator("#toast")).to_have_class(re.compile(r"\bshow\b"))
    expect(page.locator("#toast")).to_have_text("請先從左側選擇一個分類")
    expect(page.locator("#categoryModal")).to_be_hidden()


def test_category_summary_with_content(page):
    """F2：期貨有類別摘要，顯示標題與內容。"""
    open_category_summary(page, "期貨")
    expect(page.locator("#categoryModalTitle")).to_have_text("期貨的趨勢摘要")
    expect(page.locator("#categoryModalBody")).to_contain_text("台指期受國際震盪")


def test_category_summary_missing_shows_note(page):
    """F3：兩岸沒有類別摘要，顯示說明文字，不是空白。"""
    open_category_summary(page, "兩岸")
    expect(page.locator("#categoryModalBody")).to_contain_text("還沒有針對「兩岸」生成趨勢摘要")


def test_category_summary_with_no_insights_is_readable(page):
    """F4：要聞的類別摘要是「無洞察、不值得關注」，畫面不能是空白，也不能露出原始 JSON。"""
    open_category_summary(page, "要聞")
    body = page.locator("#categoryModalBody")
    expect(body).not_to_be_empty()
    text = body.inner_text()
    assert text.strip(), "類別摘要視窗是空的"
    assert '"insights"' not in text and "is_noteworthy" not in text


def test_category_summary_modal_closes_with_escape(page):
    """類別摘要視窗可以用 Esc 關閉。"""
    open_category_summary(page, "期貨")
    page.keyboard.press("Escape")
    expect(page.locator("#categoryModal")).to_be_hidden()
