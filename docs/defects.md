# 缺陷紀錄

由 `tests/e2e/` 的 Playwright 與 API 測試在固定測試資料上發現。每筆缺陷在測試裡都有對應的
`xfail(strict=True)`：現況下測試標為預期失敗；缺陷修好之後測試會變成 XPASS 並讓整次執行失敗，
提醒你把 `xfail` 標記拿掉。

重現環境：`docker compose -f tests/e2e/docker-compose.e2e.yml up -d --build`，頁面
`http://localhost:8080`。以下「根因」指出問題所在的程式位置（前端為 `News_summary_helper_frontend/`）。

| ID | 嚴重度 | 摘要 | 測試 |
|---|---|---|---|
| DEF-01 | 高 | 新聞內文以 `innerHTML` 插入，內文含 `<img onerror>` 時腳本會執行 | `test_security.py::test_malicious_content_does_not_execute_script` |
| DEF-02 | 高 | 後端回傳的摘要未跳脫 HTML，前端又以 `innerHTML` 插入 | `test_summary.py::test_summary_with_html_special_chars_is_not_interpreted` |
| DEF-05 | 中 | 對不存在的新聞要求摘要回 500，應為 404 | `test_api.py::test_summary_for_nonexistent_news_is_404_not_500` |
| DEF-04 | 中 | 搜尋框寫「標題或關鍵字」，但關鍵字只能完全相等才找得到 | `test_search.py::test_search_matches_partial_keyword` |
| DEF-03 | 低 | 搜尋 `%`、`_` 被當成萬用字元，`%` 會列出全部新聞 | `test_search.py::test_percent_sign_is_searched_literally` |
| DEF-06 | 低 | 超長無空白標題超出卡片寬度 | `test_article_panel.py::test_very_long_unbroken_title_does_not_overflow_page` |
| DEF-07 | 低 | 「該類別尚無摘要」被快取，後端之後產生了也要重新整理才看得到 | `test_errors.py::test_category_summary_note_is_not_cached_forever` |
| DEF-08 | 低 | 403 的使用者訊息提到 `config.js`、`API_KEY` | `test_errors.py::test_403_message_does_not_leak_developer_details` |
| DEF-09 | 低 | 連線失敗的使用者訊息提到 CORS、`API_BASE` | `test_errors.py::test_network_failure_message_does_not_leak_developer_details` |

---

## DEF-01　內文含惡意 HTML 時會執行腳本（儲存型 XSS 風險）
- **嚴重度**：高
- **重現**：開啟新聞 `9900001`（固定資料裡構造的新聞，內文含 `<img src=x onerror=alert(1)>`）。
- **預期**：腳本不執行，內文被清理或以文字顯示。
- **實際**：跳出 `alert(1)`，腳本被執行。
- **根因**：`app.js` 的 `renderArticlePanel` 以 `${content}` 把 `article.content` 直接放進 `innerHTML`。程式註解說明這是為了渲染爬蟲留下的 `<p>`、`<!--N-->`，但同時也讓內文成為腳本注入的入口：只要上游新聞來源或爬蟲被竄改，每個開啟該篇的使用者都會執行。
- **影響範圍**：所有新聞詳情面板；內文來自外部網站，不受本專案控制。
- **建議**：渲染前用白名單清理（例如 DOMPurify，只允許 `p`、`br`、`strong` 等），不要原樣插入。

## DEF-02　摘要未跳脫，前後端各漏一層
- **嚴重度**：高
- **重現**：開啟新聞 `9900002`（已存摘要含 `<b>`、`<script>`），點「生成 AI 摘要」。
- **預期**：特殊字元以文字顯示。
- **實際**：`<b>粗體標籤</b>` 被渲染成粗體；API 回傳的摘要裡 `<script>` 與 `&`、`<` 原樣存在。
- **根因**：後端 `gemini/formatting.py` 沒有任何跳脫；前端 `app.js` 的 `generateArticleSummary` 以 `${result.summary}` 插入 `innerHTML`。摘要由 LLM 依外部新聞內容產生，等於把外部內容經過 LLM 後再原樣渲染。
- **補充**：`innerHTML` 不會執行 `<script>` 標籤本身，但 `<img onerror>` 這類寫法可以，風險與 DEF-01 同類。
- **建議**：後端產生 HTML 前先對文字跳脫；前端同樣經過清理。

## DEF-05　不存在的新聞要求摘要回 500
- **嚴重度**：中
- **重現**：`POST /api/news/0000000/summary`（帶正確金鑰）。
- **預期**：404，與詳情端點一致。
- **實際**：500。
- **根因**：`gemini/locking.py` 的 `generate_summary_with_lock` 查不到新聞時仍執行 `query_result[0]`，空結果造成例外。
- **影響**：使用者傳入無效 ID 會看到「伺服器發生錯誤」，且過程中已取得 Redis 鎖與呼叫流程。
- **建議**：查詢結果為空時直接回 404，不要進入生成流程。

## DEF-04　搜尋關鍵字只能完全相等
- **嚴重度**：中
- **重現**：搜尋「寧德」（新聞 `9836834` 的關鍵字是「寧德時代」，標題不含「寧德」）。
- **預期**：找到該新聞，搜尋框提示是「搜尋標題或關鍵字」。
- **實際**：找不到；搜尋完整的「寧德時代」才找得到（有正向測試）。
- **根因**：`infrastructure/repositories/news_repository.py` 的 `web_search_news` 用 `%s = ANY(keywords)`，是完全相等比對。
- **建議**：要支援部分比對，可改用 `EXISTS (SELECT 1 FROM unnest(keywords) k WHERE k ILIKE ...)`；或把提示文字改成「搜尋標題」。

## DEF-03　搜尋 `%`、`_` 被當成萬用字元
- **嚴重度**：低
- **重現**：搜尋 `%`。
- **預期**：只列出標題真的含 `%` 的新聞（固定資料有 1 篇）。
- **實際**：列出全部 14 篇。
- **根因**：`web_search_news` 把使用者輸入包成 `f"%{keyword}%"`，沒有跳脫 `%` 與 `_`。不是 SQL 注入（參數化查詢，另有測試確認），但搜尋結果不正確。
- **建議**：先把使用者輸入中的 `\`、`%`、`_` 跳脫，再包 `%`。

## DEF-06　超長無空白標題超出卡片
- **嚴重度**：低
- **重現**：列表中新聞 `9900003`（標題是一長串無空白英文）。
- **預期**：標題在卡片內換行或截斷，版面不被撐開。
- **實際**：標題的內容寬度大於卡片寬度。
- **根因**：`styles.css` 的 `.card-title` 只設定 `-webkit-line-clamp`，沒有 `overflow-wrap`／`word-break`，無空白的字串不會換行。
- **建議**：加上 `overflow-wrap: anywhere`。

## DEF-07　「尚無摘要」被快取
- **嚴重度**：低
- **重現**：選「兩岸」→ 按「生成分類摘要」看到「尚無摘要」→ 關閉；之後後端產生該類別摘要 → 同一頁面再按一次。
- **預期**：看到新的摘要。
- **實際**：仍是「尚無摘要」，要重新整理頁面。
- **根因**：`app.js` 的 `openCategoryModal` 把任何成功回應（包含「該類別尚無摘要」）存進 `categorySummaryCache`。
- **建議**：不要快取「尚無摘要」，或給快取加過期時間。失敗的請求有確實不快取（有測試）。

## DEF-08　403 訊息洩漏開發細節
- **嚴重度**：低
- **重現**：金鑰錯誤時載入頁面。
- **實際**：橫幅寫「請確認 config.js 裡的 API_KEY 是否填寫正確」，對一般使用者沒有意義，也透露前端的設定檔名稱。
- **根因**：`app.js` 的 `apiRequest` 對 403 拋出的訊息。
- **建議**：對使用者顯示通用訊息，細節寫進 `console.error`。

## DEF-09　連線失敗訊息提到 CORS 與 API_BASE
- **嚴重度**：低
- **重現**：後端無法連線時載入頁面。
- **實際**：橫幅提到 `API_BASE` 與 CORS。
- **根因**：`app.js` 的 `apiRequest` 對網路錯誤拋出的訊息。
- **建議**：同 DEF-08。

---

## 已確認「沒有問題」的項目（有測試保護）
- 沒帶或帶錯金鑰一律 403；列表、詳情、搜尋的回應格式與型別正確。
- 搜尋字串含 SQL 片段（`'; DROP TABLE news; --`）不出錯，資料不受影響。
- 用錯 HTTP 方法回 405；類別摘要收到陌生類別字串回「尚無摘要」。
- 標題的特殊字元在卡片與詳情標題都以文字顯示（前端對標題有做跳脫）。
- 內文的 `<p>`、`<!--N-->` 被渲染成段落，不會以字面顯示；長內文可在面板內捲動。
- 分類篩選、搜尋、空狀態、關閉面板（✕／Esc／點遮罩）、摘要生成失敗後可重試、403／503／連線中斷時的橫幅。
