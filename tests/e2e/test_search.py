"""C. 搜尋。使用真實後端 + 固定測試資料（第 2 層）。"""
import re

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


def test_search_matches_partial_keyword(page):
    """C7：輸入關鍵字的一部分「寧德」也找得到（標題、內文、關鍵字都是部分比對）。"""
    open_home(page)
    search(page, "寧德")
    expect(page.locator(".news-card")).to_have_count(1)


def test_percent_sign_is_searched_literally(page, sample):
    """C6：輸入 % 只找標題、內文、關鍵字裡真的含 % 的新聞，不是匹配全部。
    預期結果依固定資料算出（目前是 3 篇：1 篇標題與內文含 %，2 篇內文含 %）。"""
    def contains_percent(n):
        text = re.sub(r"<[^>]*>", "", n["content"])
        return "%" in n["title"] or "%" in text or any("%" in k for k in n["keywords"])

    expected = sorted(n["title"] for n in sample["news"] if contains_percent(n))
    assert 0 < len(expected) < len(sample["news"]), "固定資料要同時有含與不含 % 的新聞，這個測試才有意義"

    open_home(page)
    search(page, "%")
    expect(page.locator(".news-card")).to_have_count(len(expected))
    assert sorted(page.locator(".news-card .card-title").all_inner_texts()) == expected


def test_underscore_is_searched_literally(page):
    """C6：_ 也是 LIKE 的萬用字元（代表任一個字）。固定資料沒有任何標題或內文含底線，應該 0 筆。"""
    open_home(page)
    search(page, "_")
    expect(page.locator(".news-card")).to_have_count(0)
    expect(page.locator(".state-box")).to_contain_text("找不到符合搜尋條件的新聞")


def test_search_matches_words_that_only_appear_in_article_body(page):
    """C8：搜尋只出現在內文、不在標題與關鍵字的詞（「康達盛通」只在 9838157 的內文），也找得到。"""
    open_home(page)
    search(page, "康達盛通")
    expect(page.locator(".news-card")).to_have_count(1)
    expect(page.locator(".news-card .card-title")).to_contain_text("味全龍封王")


def test_search_does_not_match_html_markup_in_article_body(page):
    """C8：內文存的是 HTML，搜尋不應該比對到標籤與註解（像 `!--` 這種只出現在 <!--0--> 的字串）。"""
    open_home(page)
    search(page, "!--")
    expect(page.locator(".news-card")).to_have_count(0)
