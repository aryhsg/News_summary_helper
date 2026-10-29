"""
合併原本 gen_sig_summary.py（批次模式）跟 gen_summary_lock.py 內嵌的單篇
生成邏輯（sg 模式），以及 gen_cate_summary.py 的類別彙總生成邏輯。三種
模式呼叫 Gemini 的方式不同（sg 一次一篇、batch 一次多篇、cate 整類別
彙總），但「拿到 Gemini 回應後怎麼把 points 轉成編號清單字串」是同一段
邏輯，透過 gemini.formatting.points_to_numbered_string 共用，不再各自
重寫一份——Stage 3.5 的 bug 就是因為這段邏輯重複寫了兩份，改一邊忘了改
另一邊。
"""
import json
import asyncio

from constants import BATCH_SUMMARY_CATEGORIES
from gemini.formatting import points_to_numbered_string


async def generate_single_summary(gemini_instance, contents_json: str):
    """呼叫 sg 模式，回傳 (news_id, summary_str)。"""
    raw = await gemini_instance.generate_summary(instruction_type="sg", contents=contents_json)
    result = json.loads(raw)
    summary_str = points_to_numbered_string(result.get("points", []))
    return result.get("news_id", ""), summary_str


async def generate_batch_summaries(gemini_instance, contents_json: str):
    """呼叫 batch 模式，回傳 [(news_id, summary_str), ...]。"""
    raw = await gemini_instance.generate_summary(instruction_type="batch", contents=contents_json)
    results = json.loads(raw)
    return [
        (news.get("news_id", ""), points_to_numbered_string(news.get("points", [])))
        for news in results
    ]


async def generate_cate_summary(gemini_instance, contents_json: str) -> str:
    """呼叫 cate 模式，回傳原始 JSON 字串（CateSummaryRepository 直接存整個字串）。"""
    return await gemini_instance.generate_summary(instruction_type="cate", contents=contents_json)


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

            batch_results = await generate_batch_summaries(gemini_instance, json_contents)
            news_summary_list = [(news_id, summary_str, category) for news_id, summary_str in batch_results]

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
    try:
        for cate in BATCH_SUMMARY_CATEGORIES:
            # 記得傳入實例
            await batch_gen_sum_n_store(cate, db, gemini, redis)

            # 類別間隔 (RPM 防護第二層，預防短時間大量請求)
            print(f"✅ {cate} 處理完成，冷卻 20 秒...")
            await asyncio.sleep(20)

        print(f"✅ 所有類別均處理完成，並存入資料庫")
    except Exception as e:
        print(f"error: {e}")


async def generate_cate_summary_and_store(category: str, db_instance, gemini_instance):
    """原 gen_cate_summary.py 的 generate_summary_n_store，改成吃 db_instance/
    gemini_instance 參數，不再依賴模組載入時就建立好的全域 DB/ai 物件（那樣
    寫法會讓單純 import 這個模組就產生真的連線池跟 Gemini client）。也移除了
    原本放在這個函式 finally 裡的 ai.close()：原寫法會在處理完第一個類別後
    就把 Gemini client 關掉，導致迴圈裡後面的類別全部因為用已關閉的 client
    而靜默失敗（被外層 except Exception 吃掉，只印一行 log）。client 的關閉
    改成交給呼叫端（cron 進入點 gen_cate_summary.main()）在所有類別都跑完後
    才做一次。"""
    try:
        query_result = await db_instance.fetch_news_summary(category=category)  # [{news_id, title, category, content}]
        if not query_result:
            print(f"類別 {category} 找不到任何新聞內容")
            return None

        news_json = json.dumps(query_result, ensure_ascii=False)
        try:
            response = await generate_cate_summary(gemini_instance, news_json)
            if response:
                print("生成成功")
                print(response)
                print(f"字串長度: {len(response)}")
                await db_instance.insert_cate_summary(category=category, cate_summary_tuple=(category, response))
            else:
                print("生成失敗")
        except Exception as e:
            print(f"gemini error: {e}")

    except Exception as e:
        print(f"db error: {e}")
