import re
import json

    
def advanced_format_summary(text):
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

async def generate_summary_with_lock(news_id: int, db_instance, redis_instance, gemini_instance):
    result = await db_instance.fetch_specific_summary(news_id)

    if result and result[0].get("news_summary"):
        summary = result[0].get("news_summary")
        print("資料庫存在該新聞摘要")
        return summary

    async with redis_instance.get_lock(str(news_id), timeout=60):        
        result = await db_instance.fetch_specific_summary(news_id)
        
        if result and result[0].get("news_summary"):
            summary = result[0].get("news_summary")
            return summary

        print("該新聞目前無摘要，正在生成中...")
        query_result = await db_instance.fetch_news_content(news_id) # [(news_id, title, content, category)]
        contents = json.dumps(query_result) # GEMINI不收list，所以要轉成json字串
        category = query_result[0]["category"]
    
        result = await gemini_instance.generate_summary(instruction_type = "sg", contents = contents) # 預計會follow NewsSummarySchema
        result = json.loads(result)
        print(result)
        summary = result[0].get("points", [])
        summary_str = ""
        for i, p in enumerate(summary):
            summary_str += f"{i+1}. {p}\n"

        await db_instance.insert_news_summary([(result[0].get("news_id", ""), summary_str, category)])
        print("摘要成功存入資料庫")
        return summary_str