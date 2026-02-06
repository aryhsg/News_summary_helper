import json

async def generate_summary_with_lock(news_id:int, db_instance, redis_instance, gemini_instance):
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