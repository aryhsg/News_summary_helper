import asyncio


"""root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)"""




async def batch_generate_sg_summaries(category: str,news_list: list[dict], DB_instance, gemini_instance, redis_manager_instance): 
    """
    news_list: [{"news_id": 1, "title": "...", "content": "..."}, {"news_id": 2, ...}]
    """
    news_list = DB_instance.fetch_news_content(batch=True, category=category)
    batch_size = 5
    news_batches = [news_list[i:i + batch_size] for i in range(0, len(news_list), batch_size)]

    to_generate = []
    locks = []
    # 1. 篩選與上鎖
    for batch in news_batches:  
        for news in batch:
            news_id = str(news['news_id'])
        # 嘗試拿鎖，這裡建議用 non-blocking 或是嘗試拿鎖，避免爬蟲卡死
        # 但簡單做法是直接用 get_lock
            lock = redis_manager_instance.get_lock(news_id)
            await lock.__aenter__() # 手動進入鎖
        
        # 拿到鎖後 Double Check
            res = await DB_instance.fetch_specific_summary(news['news_id'])
            if res and res[0].get("news_summary"):
                await lock.__aexit__(None, None, None) # 已有摘要，直接解鎖放行
                continue
        
        # 確定要生的才放進清單
            to_generate.append(news)
            locks.append(lock)

        if not to_generate:
            return

    # 2. 執行批次生成 (這是你最核心的 batch 方法)
    summaries = await gemini_instance.generate_summary(instruction_type= "batch", contents=to_generate)

    # 3. 存入資料庫並批次解鎖
    try:
        await DB_instance.insert_news_summary(summaries)
    finally:
        for lock in locks:
            await lock.__aexit__(None, None, None) # 確保最後一定會解鎖