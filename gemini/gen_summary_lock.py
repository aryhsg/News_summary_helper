import re
import json
import asyncio
    
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
        title = result[0].get("title")
        print("資料庫存在該新聞摘要")
        return title, summary

    async with redis_instance.get_lock(str(news_id), timeout=60):        
        result = await db_instance.fetch_specific_summary(news_id)
        
        if result and result[0].get("news_summary"):
            summary = result[0].get("news_summary")
            title = result[0].get("title")
            return title, summary

        print("該新聞目前無摘要，正在生成中...")
        query_result = await db_instance.fetch_news_content(news_id) # [(news_id, title, content, category)]
        contents = json.dumps(query_result) # GEMINI不收list，所以要轉成json字串
        title = query_result[0].get("title")
        category = query_result[0].get("category")
    
        result = await gemini_instance.generate_summary(instruction_type = "sg", contents = contents) # 預計會follow NewsSummarySchema
        result = json.loads(result)
        print(result)
        # NewsSummarySchema 本身就是單篇文章的單一物件（不是 list），
        # 不需要（也不能）用 [0] 去索引；points 裡每個元素是 SinglePoint
        # ({point_id, content})，要取 content 欄位，不是整個物件直接印出來。
        summary = result.get("points", [])
        summary_str = ""
        for i, p in enumerate(summary):
            summary_str += f"{i+1}. {p.get('content', '')}\n"

        await db_instance.insert_news_summary([(result.get("news_id", ""), summary_str, category)])
        print("摘要成功存入資料庫")
        return title, summary_str



async def sandbox_generate_summary_with_lock(news_id: int, db_instance, redis_instance):
    """給 /api/sandbox（不耗用 Gemini 配額的示範端點）用，模擬生成摘要的流程。"""
    result = await db_instance.sandbox_fetch_specific_summary(news_id)

    if result and result[0].get("news_summary"):
        summary = result[0].get("news_summary")
        title = result[0].get("title")
        print("資料庫存在該新聞摘要")
        return title, summary

    async with redis_instance.get_lock(str(news_id), timeout=60):
        result = await db_instance.sandbox_fetch_specific_summary(news_id)
        
        if result and result[0].get("news_summary"):
            summary = result[0].get("news_summary")
            title = result[0].get("title")
            return title, summary

        print("該新聞目前無摘要，正在生成中...")
        await asyncio.sleep(10)
        category = "測試類別"
    
        summary_str = "測試中，這是一個模擬的摘要內容。"
        title = "測試新聞標題"

        await db_instance.insert_news_summary([(9338960, summary_str, category)])
        print("摘要成功存入資料庫")
        return title, summary_str