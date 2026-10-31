"""時序相關的行為：防抖、亂序回應、載入中狀態、請求進行中的畫面切換。

用 hold_requests 把請求扣住，再依測試需要的順序放行（第 1 層：攔截請求）。
列表等其他資料仍然來自真實後端。
"""
import re
from urllib.parse import unquote

from playwright.sync_api import expect

from conftest import hold_requests, json_body, open_article, open_home, wait_until

SUMMARY_OK = {"id": 9838157, "summary": "<ol><li>第一點</li><li>第二點</li></ol>"}


def item(news_id, title):
    return {"id": news_id, "title": title, "category": "要聞", "img": ""}


# --- 搜尋防抖與亂序回應 -------------------------------------------------------------

def test_search_is_debounced_into_a_single_request(page):
    """C1：快速連續輸入只在停下來之後送出一次請求，且帶的是完整字串。
    用英文字母輸入：Playwright 輸入中文時會一次插入整串字、只觸發一次輸入事件，
    測不到「逐字輸入」，這個測試會變成永遠通過。"""
    requests_seen = []
    page.on("request", lambda r: requests_seen.append(r.url) if "/api/news/search" in r.url else None)
    open_home(page)

    page.locator("#searchInput").press_sequentially("etf", delay=60)  # 每字間隔遠小於防抖時間（500ms）
    page.wait_for_timeout(1200)

    assert len(requests_seen) == 1, f"預期防抖後只有 1 次搜尋請求，實際 {len(requests_seen)} 次：{requests_seen}"
    assert requests_seen[0].endswith("q=etf"), requests_seen[0]  # 完整字串，不是中途的片段


def test_search_sends_a_new_request_after_a_pause(page):
    """C1：停頓超過防抖時間再輸入，視為新一輪搜尋，會再送一次請求。"""
    requests_seen = []
    page.on("request", lambda r: requests_seen.append(r.url) if "/api/news/search" in r.url else None)
    open_home(page)

    page.locator("#searchInput").press_sequentially("et", delay=60)
    page.wait_for_timeout(1000)
    page.locator("#searchInput").press_sequentially("f", delay=60)
    page.wait_for_timeout(1000)

    assert len(requests_seen) == 2, requests_seen
    assert requests_seen[0].endswith("q=et") and requests_seen[1].endswith("q=etf")
    # 搜尋範圍含內文，所以不只標題含 ETF 的那篇會符合；這裡只確認它有出現
    expect(page.locator(".news-card", has_text="ETF")).to_have_count(1)


def test_stale_search_response_is_ignored(page):
    """C4：先送出的搜尋比後送出的晚回來時，畫面要以最新一次搜尋為準，不能被舊結果蓋掉。"""
    open_home(page)
    pending = hold_requests(page, "**/api/news/search**")

    page.locator("#searchInput").fill("台指期")          # 請求 A
    wait_until(page, lambda: len(pending) == 1)
    page.locator("#searchInput").fill("全聯")            # 請求 B（使用者改搜別的）
    wait_until(page, lambda: len(pending) == 2)

    pending[1].fulfill(status=200, content_type="application/json", body=json_body([item(111, "新結果")]))
    expect(page.locator(".news-card")).to_have_count(1)
    expect(page.locator(".news-card .card-title")).to_have_text("新結果")

    # 舊請求 A 現在才回來
    pending[0].fulfill(
        status=200, content_type="application/json",
        body=json_body([item(222, "舊結果甲"), item(223, "舊結果乙")]),
    )
    page.wait_for_timeout(700)
    expect(page.locator(".news-card")).to_have_count(1)
    expect(page.locator(".news-card .card-title")).to_have_text("新結果")


def test_search_shows_loading_state_until_response_arrives(page):
    """搜尋請求還沒回來時顯示載入動畫，回來之後換成結果。"""
    open_home(page)
    pending = hold_requests(page, "**/api/news/search**")

    page.locator("#searchInput").fill("台指期")
    wait_until(page, lambda: len(pending) == 1)
    expect(page.locator("#newsGrid .spinner")).to_be_visible()
    expect(page.locator(".news-card")).to_have_count(0)

    pending[0].fulfill(status=200, content_type="application/json", body=json_body([item(1, "有結果")]))
    expect(page.locator("#newsGrid .spinner")).to_have_count(0)
    expect(page.locator(".news-card")).to_have_count(1)


# --- 詳情 API 失敗與載入中 -------------------------------------------------------------

def test_article_panel_shows_loading_then_not_found(page):
    """D5：詳情請求還沒回來時顯示「載入中…」；回 404 後顯示「讀取失敗」與說明，且面板仍可關閉。"""
    open_home(page)
    pending = hold_requests(page, "**/api/news/9838157")

    page.locator('.news-card[data-id="9838157"]').click()
    wait_until(page, lambda: len(pending) == 1)
    expect(page.locator("#articleCat")).to_have_text("載入中…")
    expect(page.locator("#articleBody .spinner")).to_be_visible()

    pending[0].fulfill(status=404, content_type="application/json", body=json_body({"detail": "News not found"}))
    expect(page.locator("#articleCat")).to_have_text("讀取失敗")
    expect(page.locator("#articleBody .state-box")).to_contain_text("News not found")
    expect(page.locator("#articleBody .spinner")).to_have_count(0)

    page.keyboard.press("Escape")
    expect(page.locator("#articlePanel")).to_be_hidden()


def test_article_panel_shows_error_on_server_error(page):
    """D5：詳情請求回 500（非 JSON）時，顯示通用的伺服器錯誤說明。"""
    open_home(page)
    page.route("**/api/news/9838157", lambda r: r.fulfill(status=500, body="Internal Server Error"))
    page.locator('.news-card[data-id="9838157"]').click()
    expect(page.locator("#articleCat")).to_have_text("讀取失敗")
    expect(page.locator("#articleBody .state-box")).to_contain_text("伺服器發生錯誤")


# --- 摘要載入中狀態與請求進行中的畫面切換 ---------------------------------------------------

def test_summary_loading_state_then_result(page):
    """E2：按下生成後，摘要欄立刻展開並顯示載入動畫、按鈕停用；回應到了才換成摘要並恢復按鈕。"""
    open_article(page, "9838157")
    pending = hold_requests(page, "**/api/news/9838157/summary")

    page.locator("#btnGenerateSummary").click()
    wait_until(page, lambda: len(pending) == 1)
    expect(page.locator("#summaryColumn")).to_be_visible()
    expect(page.locator("#articlePanel")).to_have_class(re.compile(r"\bis-split\b"))
    expect(page.locator("#summaryContainer .spinner")).to_be_visible()
    expect(page.locator("#btnGenerateSummary")).to_be_disabled()

    pending[0].fulfill(status=200, content_type="application/json", body=json_body(SUMMARY_OK))
    expect(page.locator("#summaryContainer .summary-box li")).to_have_count(2)
    expect(page.locator("#summaryContainer .spinner")).to_have_count(0)
    expect(page.locator("#btnGenerateSummary")).to_be_enabled()
    expect(page.locator("#btnGenerateSummary")).to_have_text("重新查看 AI 摘要")


def test_late_summary_does_not_leak_into_another_article(page):
    """E5：A 的摘要還在生成時關掉面板、改開 B，A 之後才回來的摘要不能出現在 B 的面板裡。"""
    open_article(page, "9838157")                       # A
    pending = hold_requests(page, "**/api/news/9838157/summary")
    page.locator("#btnGenerateSummary").click()
    wait_until(page, lambda: len(pending) == 1)

    page.keyboard.press("Escape")                       # 生成中關掉面板
    expect(page.locator("#articlePanel")).to_be_hidden()
    page.locator('.news-card[data-id="9837670"]').click()   # 改開 B
    page.wait_for_selector("#articleBody .article-title")
    expect(page.locator(".article-title")).to_contain_text("經濟成長率")

    pending[0].fulfill(status=200, content_type="application/json", body=json_body(SUMMARY_OK))
    page.wait_for_timeout(700)

    expect(page.locator("#summaryColumn")).to_be_hidden()
    expect(page.locator("#summaryContainer")).to_be_empty()
    expect(page.locator("#btnGenerateSummary")).to_have_text("生成 AI 摘要")
    expect(page.locator("#btnGenerateSummary")).to_be_enabled()


# --- 輸入法（IME）組字 ----------------------------------------------------------------

def test_search_ignores_ime_composition_and_searches_once_per_committed_text(page):
    """C9：用注音輸入法打中文時，組字中的注音符號不該被拿去搜尋；選字確認之後才搜尋。
    模擬「味全」：每個字都先組字（ㄨㄟˋ）、停頓超過防抖時間、再選字確認。
    （只有英文字母的測試測不到這個：真實的中文輸入會觸發輸入法組字事件。）"""
    queries = []
    page.on("request", lambda r: queries.append(unquote(r.url.split("q=")[-1])) if "/api/news/search" in r.url else None)
    open_home(page)
    cdp = page.context.new_cdp_session(page)
    page.locator("#searchInput").focus()

    def compose(zhuyin):
        cdp.send("Input.imeSetComposition", {"text": zhuyin, "selectionStart": len(zhuyin), "selectionEnd": len(zhuyin)})

    def commit(char):
        cdp.send("Input.insertText", {"text": char})

    compose("ㄨㄟˋ")
    page.wait_for_timeout(900)                      # 停頓超過防抖時間，組字中仍不該搜尋
    assert queries == [], f"組字中就送出了搜尋：{queries}"

    commit("味")
    page.wait_for_timeout(900)
    assert queries == ["味"], queries

    compose("ㄑㄩㄢˊ")
    page.wait_for_timeout(900)
    assert queries == ["味"], f"第二個字組字中又送出了搜尋：{queries}"

    commit("全")
    page.wait_for_timeout(900)
    assert queries == ["味", "味全"], queries
    expect(page.locator("#searchInput")).to_have_value("味全")
