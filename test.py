import os
import sys
import json
import asyncio
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

import gemini
import news_crawler
import infrastructure.redis_manager


async def main(category: str):
    # 1. 建立實例
    DB = news_crawler.NewsDB()
    gemini_client = gemini.gemini_client()
    redis_mgr = infrastructure.redis_manager.RedisManager()

    try:
        # 2. 開啟所有連線池 (確保這些方法內部有使用 await)
        await DB.pool_init()
        await redis_mgr.init_pool()
        print("🚀 所有連線池初始化成功")

        # 3. 執行批次任務
        # 這裡不需要 asyncio.run，因為我們已經在 main() 裡面了
        raw_summaries = await news_crawler.batch_generate_sg_summaries(
            category=category, 
            DB_instance=DB, 
            gemini_instance=gemini_client, 
            redis_manager_instance=redis_mgr
        )
        
        
        if raw_summaries:
            all_summaries = []
            print("✅ 成功生成摘要")
            print(f"範例結果: {raw_summaries[0]}")
            print("\n----------------------------------------\n")
            for item in raw_summaries:
                summaries = json.loads(item)
                all_summaries.extend(summaries)
            print(type(all_summaries))

        news_summary_list = []
        for news in all_summaries:
            points = news.get("points", "")
            points_str = ""
            for i, point in enumerate(points):
                points_str += f"{i+1}. {point}\n"

            news_tuple = (news.get("news_id", ""), points_str, category)
            news_summary_list.append(news_tuple)
        await DB.insert_news_summary(news_summary_list=news_summary_list)
        print("摘要成功存入資料庫")




    except Exception as e:
        print(f"❌ 執行過程中發生錯誤: {e}")

    finally:
        # 4. 無論成功或失敗，都優雅關閉連線 (這就是專業的清理)
        print("💤 正在關閉連線...")
        await DB.pool_close()
        await redis_mgr.close()
        # 如果 gemini 也有 close 方法請加上
        if hasattr(gemini_client, 'close'):
            await gemini_client.close()


if __name__ == "__main__":
    asyncio.run(main("兩岸"))

"""
{'news_id': '9306002', 
'title': '新興市場上周持續吸引資金流入 台股最吸金', 
'points': ['新興市場ETF連續15週吸引資金，累計流入428億美元；上週（截至1月30日）再吸金65億美元，無國家資金流出。', 
            '台灣資產上週吸金13.93億美元稱冠新興市場，全數流入台股ETF，南韓與中港分居二、三名。', 
            '今年來新興市場已吸金249億美元，反映AI類股暴漲、美國政策不確定性及美元疲軟，促使投資人調整地理曝險。', 
            '瑞銀預期2026年投資主軸為分散投資，將提振新興市場表現，特別是過去配置比率偏低的地區。']
            }
"""