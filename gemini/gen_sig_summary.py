import asyncio
import json

"""root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)"""




async def batch_generate_sg_summaries(category: str, DB_instance, gemini_instance, redis_manager_instance): 
    """
    news_list: [{"news_id": 1, "title": "...", "content": "..."}, {"news_id": 2, ...}]
    """

    summary_list = []
    try:
        news_list = await DB_instance.fetch_news_content(batch=True, category=category)
        if not news_list:
            print("該類別目前暫無新聞")
        else:
            print(f"取得{category}類所有新聞，共{(len(news_list))}筆")
    except Exception as e:
        print(f"db error: {e}")
        return 
    batch_size = 5
    # 這裡的 news_batches 已經是分好組的了 (例如 [[1,2,3,4,5], [6,7,8,9,10]])
    news_batches = [news_list[i:i + batch_size] for i in range(0, len(news_list), batch_size)]

    for batch in news_batches:
        to_generate_this_round = []
        locks_this_round = []

        # 1. 篩選與上鎖 (針對這一組 5 篇)
        for news in batch:
            news_id = str(news['news_id'])
            lock = redis_manager_instance.get_lock(news_id)
            await lock.__aenter__() 
            
            res = await DB_instance.fetch_specific_summary(news['news_id'])
            if res and res[0].get("news_summary"):
                await lock.__aexit__(None, None, None)
                continue
            
            to_generate_this_round.append(news)
            locks_this_round.append(lock)

        if not to_generate_this_round:
            continue # 這組都生過了，換下一組

        # 2. 執行這一組的生成 (這才是真正的「每批次」)
        try:
            # 記得把 list 轉成 JSON 字串，避免之前那個 Pydantic 94 errors
            print(f"準備生成摘要，本批次共有{len(to_generate_this_round)}筆新聞")
            json_contents = json.dumps(to_generate_this_round, ensure_ascii=False)
            
            summaries = await gemini_instance.generate_summary(instruction_type="batch", contents=json_contents)
            print(f"本批次摘要生成完成")
            summary_list.append(summaries)
               
        except Exception as e:
            print(f"處理批次時發生錯誤: {e}")
        finally:
            # 4. 批次解鎖 (不論成功失敗都要解鎖這組)
            for lock in locks_this_round:
                await lock.__aexit__(None, None, None)

        # 5. 【關鍵】在這裡休息 5 秒，確保下一個 Batch 不會太快發出
        await asyncio.sleep(5)

    return summary_list







