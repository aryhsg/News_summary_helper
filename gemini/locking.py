"""
用 Redis 分散式鎖協調「同一篇新聞的摘要只生成一次」，避免同時有多個請求
打進來時重複呼叫 Gemini。實際呼叫 Gemini、解析回應的邏輯交給
gemini.generation，這裡只負責：查快取 -> 上鎖 -> 再查一次快取（double
check）-> 真的沒有才生成 -> 寫回資料庫。
"""
import json
import asyncio

from gemini import generation


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
        query_result = await db_instance.fetch_news_content(news_id)  # [(news_id, title, content, category)]
        contents = json.dumps(query_result)  # GEMINI不收list，所以要轉成json字串
        title = query_result[0].get("title")
        category = query_result[0].get("category")

        resolved_news_id, summary_str = await generation.generate_single_summary(gemini_instance, contents)

        await db_instance.insert_news_summary([(resolved_news_id, summary_str, category)])
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
