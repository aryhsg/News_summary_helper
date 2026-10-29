"""純字串/資料轉換，不碰 DB、Redis、Gemini API，不需要 mock 就能單元測試。"""
import re

from gemini.json_schema import CategorySummary


def points_to_numbered_string(points: list) -> str:
    """把 NewsSummarySchema 的 points（[{point_id, content}, ...]）轉成編號
    清單字串。sg/batch 兩種模式共用，避免 schema 改一次卻只改到一邊
    （Stage 3.5 的 bug 就是這樣來的）。"""
    return "\n".join(f"{i+1}. {p.get('content', '')}" for i, p in enumerate(points))


def _parse_category_summary(raw_summary: dict) -> CategorySummary:
    return CategorySummary.model_validate_json(raw_summary.get("news_summary", "{}"))


def get_str_summary(raw_summary: dict):
    """給 LINE 排版用"""
    try:
        parsed = _parse_category_summary(raw_summary)

        content = ""
        for item in parsed.insights:
            topic = item.topic.strip()
            analysis = item.analysis.strip()

            # 使用項目符號與分隔線增加視覺區隔
            content += f"● 【{topic}】\n\n"
            content += f"   {analysis}\n\n"

        if not parsed.insights:
            content = "今日無重大新聞價值事件。\n\n"

        return f"=== 今日新聞趨勢彙總 ===\n\n{content}"

    except Exception as e:
        print(f"解析摘要時發生錯誤: {e}")
        return None


def get_formatted_summary(raw_summary: dict):
    """給網頁排版用"""
    parsed = _parse_category_summary(raw_summary)

    # 1. 處理所有趨勢內容，將 topic 與 analysis 組合
    trend_sections = [
        f"<br><h3>{item.topic}</h3>\n<br>\n<p style='text-align: justify;'>{item.analysis}</p>"
        for item in parsed.insights
    ]

    if not parsed.insights:
        trend_sections.append("<br><p>今日無重大新聞價值事件。</p>")

    # 2. 標題用 <h2> 包起來（schema 沒有 report_title，固定用通用標題）
    title_html = "<h2>今日新聞摘要</h2>\n<hr>"

    # 3. 將所有區塊組合成一個大字串，中間用換行隔開
    all_content_html = "\n".join(trend_sections)

    return f"{title_html}\n{all_content_html}"


def advanced_format_summary(text):
    """把 sg/batch 模式輸出的編號清單字串，轉成 <ol><li>...</li></ol> 的 HTML。"""
    # 1. 預處理：先把 \r\n 轉為標準換行，方便判斷行首
    text = text.replace('\r', '').replace('\n', '\n')

    # 2. 優化後的正則表達式：
    # (?m) -> 多行模式
    # ^\d+ -> 行首的數字
    # [\.、] -> 接點號或頓號
    # (?!\d) -> 負向先行斷言：後面「不能」直接接著數字（這能避開 38.72）
    # \s* -> 後面可以接零或多個空白
    pattern = r'(?m)^\d+[\.、](?!\d)\s*'

    # 3. 使用 re.split 進行切割，並移除空項目
    items = re.split(pattern, text)
    items = [item.strip() for item in items if item.strip()]

    # 4. 封裝成 HTML
    html_output = '<ol class="modern-list">\n'
    for item in items:
        # 清理掉內容中可能殘留的換行
        clean_item = item.replace('\n', '')
        html_output += f'    <li>{clean_item}</li>\n'
    html_output += '</ol>'

    return html_output
