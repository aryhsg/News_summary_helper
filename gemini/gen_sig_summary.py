import json
import asyncio

async def batch_gen_sum_n_store(category: str, DB_instance, gemini_instance, redis_manager_instance): 
    # 這裡只取清單，不存摘要結果
    try:
        news_list = await DB_instance.fetch_news_content(batch=True, category=category)
        if not news_list:
            print(f"{category} 類別目前暫無新聞"); return 
        print(f"取得 {category} 類所有新聞，共 {len(news_list)} 筆")
    except Exception as e:
        print(f"db error: {e}"); return 

    batch_size = 5
    news_batches = [news_list[i:i + batch_size] for i in range(0, len(news_list), batch_size)]

    for batch in news_batches:
        to_generate_this_round = []
        locks_this_round = []

        # 1. 篩選與上鎖
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
            continue 

        # 2. 生成與存入 (確保每一批次都是獨立的)
        try:
            print(f"準備生成摘要，本批次共有 {len(to_generate_this_round)} 筆新聞")
            json_contents = json.dumps(to_generate_this_round, ensure_ascii=False)
            
            # 取得 Gemini 回傳的字串
            raw_summaries = await gemini_instance.generate_summary(instruction_type="batch", contents=json_contents)
            
            # 解析 JSON (假設 Gemini 回傳的是 JSON 字串)
            current_batch_summaries = json.loads(raw_summaries) 

            news_summary_list = []
            for news in current_batch_summaries:
                points = news.get("points", [])
                # 使用 join 處理 list 比 += 效能更好
                points_str = "\n".join([f"{i+1}. {p}" for i, p in enumerate(points)])

                news_tuple = (news.get("news_id", ""), points_str, category)
                news_summary_list.append(news_tuple)

            # 3. 寫入資料庫
            if news_summary_list:
                await DB_instance.insert_news_summary(news_summary_list=news_summary_list)
                print(f"✅ {category} 類本批次 {len(news_summary_list)} 筆成功存入")
               
        except Exception as e:
            print(f"❌ 處理批次時發生錯誤: {e}")
        finally:
            # 4. 批次解鎖
            for lock in locks_this_round:
                await lock.__aexit__(None, None, None)

        # 5. 冷卻時間 (RPM 保護)
        await asyncio.sleep(5)


async def batch_gen_all_sum_n_store(db, gemini, redis):
    catelist = ["要聞","國際","證券","期貨","理財","兩岸","金融","產業"]
    all_results = []
    try:
        for cate in catelist:
            # 記得傳入實例
            await batch_gen_sum_n_store(cate, db, gemini, redis)
    
            
            # 類別間隔 (RPM 防護第二層，預防短時間大量請求)
            print(f"✅ {cate} 處理完成，冷卻 20 秒...")
            await asyncio.sleep(20) 
        
        print(f"✅ 所有類別均處理完成，並存入資料庫")
    except Exception as e:
        print(f"error: {e}")