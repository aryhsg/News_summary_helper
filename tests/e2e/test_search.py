"""C. 搜尋。使用真實後端 + 固定測試資料（第 2 層）。"""
import pytest

from playwright.sync_api import expect

from conftest import click_category, open_home


def search(page, text):
    page.locator("#searchInput").fill(text)


def test_search_with_no_match_shows_message(page):
    """C3：搜尋不到時顯示說明文字。"""
    open_home(page)
    search(page, "完全不存在的關鍵字xyz")
    expect(page.locator(".news-card")).to_have_count(0)
    expect(page.locator(".state-box")).to_contain_text("找不到符合搜尋條件的新聞")


def test_search_combines_with_category_filter(page):
    """C2：搜尋結果可以再用分類篩選；切到沒有符合結果的分類時顯示無結果。"""
    open_home(page)
    search(page, "台指期")
    expect(page.locator(".news-card")).to_have_count(2)

    click_category(page, "要聞")
    expect(page.locator(".news-card")).to_have_count(0)
    expect(page.locator(".state-box")).to_contain_text("找不到符合搜尋條件的新聞")


def test_clearing_search_restores_full_list(page, sample):
    """C5：清空搜尋框後恢復完整列表。"""
    open_home(page)
    search(page, "台指期")
    expect(page.locator(".news-card")).to_have_count(2)
    search(page, "")
    expect(page.locator(".news-card")).to_have_count(len(sample["news"]))


def test_search_matches_exact_keyword(page):
    """C7（正向）：輸入完整的關鍵字「寧德時代」（不在標題裡），能找到對應新聞。"""
    open_home(page)
    search(page, "寧德時代")
    expect(page.locator(".news-card")).to_have_count(1)
    expect(page.locator(".news-card .card-title")).to_contain_text("陸重卡銷量")


@pytest.mark.xfail(strict=True, reason="DEF-04：後端以 `= ANY(keywords)` 完全相等比對關鍵字，部分字串找不到，與搜尋框「搜尋標題或關鍵字」的提示不符")
def test_search_matches_partial_keyword(page):
    """C7：搜尋框寫「搜尋標題或關鍵字」，輸入關鍵字的一部分「寧德」也應該找得到。
    後端關鍵字比對是 `= ANY(keywords)` 完全相等，所以目前找不到。"""
    open_home(page)
    search(page, "寧德")
    expect(page.locator(".news-card")).to_have_count(1)


@pytest.mark.xfail(strict=True, reason="DEF-03：後端用 ILIKE '%關鍵字%' 且未跳脫 % 與 _，輸入 % 會變成匹配全部")
def test_percent_sign_is_searched_literally(page):
    """C6：輸入 % 應該只找標題真的含 % 的新聞（固定資料裡剛好 1 篇「成長率上看12%」）。
    後端用 ILIKE '%關鍵字%'，沒有跳脫萬用字元，% 會變成「匹配全部」。"""
    open_home(page)
    search(page, "%")
    expect(page.locator(".news-card")).to_have_count(1)
    expect(page.locator(".news-card .card-title")).to_contain_text("經濟成長率上看12%")
