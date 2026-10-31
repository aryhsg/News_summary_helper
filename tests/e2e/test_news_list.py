"""A. 載入與列表、B. 分類篩選。使用真實後端 + 固定測試資料（第 2 層）。"""
import re
from collections import Counter

from playwright.sync_api import expect

from conftest import CATEGORIES, click_category, open_home


def test_home_lists_all_fixture_news(page, sample):
    """A1：首頁顯示固定資料裡的全部新聞，標題一字不差。"""
    open_home(page)
    titles = page.locator(".news-card .card-title").all_inner_texts()
    assert sorted(titles) == sorted(n["title"] for n in sample["news"])


def test_sidebar_counts_match_fixture(page, sample):
    """A2：側邊欄的總數與各分類數字與固定資料一致。"""
    open_home(page)
    expected = Counter(n["category"] for n in sample["news"])
    expect(page.locator("#nav-count-all")).to_have_text(str(len(sample["news"])))
    for cat in CATEGORIES:
        expect(page.locator(f"#nav-count-{cat}")).to_have_text(str(expected.get(cat, 0)))


def test_broken_thumbnail_is_removed_but_card_stays(page):
    """A3：圖片載入失敗（測試資料的 img.test 本來就連不到）時，破圖會被移除，卡片仍完整。"""
    open_home(page)
    first_card = page.locator(".news-card").first
    expect(first_card.locator(".card-thumb img")).to_have_count(0)
    expect(first_card.locator(".card-title")).not_to_be_empty()


def test_category_filter_shows_only_that_category(page, sample):
    """B1：點分類後，標題改變、該項反白、只剩該類新聞。"""
    open_home(page)
    click_category(page, "要聞")
    expected = sum(1 for n in sample["news"] if n["category"] == "要聞")

    expect(page.locator("#pageTitle")).to_have_text("要聞")
    expect(page.locator('.nav-item[data-category="要聞"]')).to_have_class(re.compile(r"\bactive\b"))
    expect(page.locator(".news-card")).to_have_count(expected)
    assert set(page.locator(".news-card .card-tag").all_inner_texts()) == {"要聞"}


def test_empty_category_shows_empty_state(page):
    """B2：沒有新聞的分類（房市）顯示空狀態，沒有任何卡片。"""
    open_home(page)
    click_category(page, "房市")
    expect(page.locator(".news-card")).to_have_count(0)
    expect(page.locator(".state-box")).to_contain_text("這個分類目前沒有新聞")


def test_back_to_all_restores_full_list(page, sample):
    """B3：切到分類後回到「所有新聞」，恢復全部。"""
    open_home(page)
    click_category(page, "期貨")
    click_category(page, "")
    expect(page.locator("#pageTitle")).to_have_text("所有新聞")
    expect(page.locator(".news-card")).to_have_count(len(sample["news"]))


def test_single_article_categories_render_one_card(page):
    """B4：只有 1 篇的分類（專題、理財）正常顯示恰好 1 張卡片。"""
    open_home(page)
    for cat in ("專題", "理財"):
        click_category(page, cat)
        expect(page.locator(".news-card")).to_have_count(1)
