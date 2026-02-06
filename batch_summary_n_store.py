import os
import sys
import json
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

import gemini
import infrastructure.redis_manager
from infrastructure import db
from gemini import gemini_client


@asynccontextmanager
async def lifespan():
    news_db = db.NewsDB()
    gemini = gemini_client.gemini_service()
    redis_mgr = infrastructure.redis_manager.RedisManager() # 建立三個服務的實例
    try:
        await news_db.pool_init()
        await redis_mgr.init_pool()
        print("🚀 所有連線池初始化成功")

        yield (news_db, gemini, redis_mgr)
    finally:
        await news_db.pool_close()
        await redis_mgr.close()
        print("💤 所有連線池成功離線")


async def main(category: str):
    async with lifespan() as (DB, gemini_client, redis_mgr): # 等於 yield(讓出) 後的實例傳進函式中使用

        try:
            await gemini.batch_gen_sum_n_store(
                category=category, 
                DB_instance=DB, 
                gemini_instance=gemini_client, 
                redis_manager_instance=redis_mgr
            )

        except Exception as e:
            print(f"error: {e}")


if __name__ == "__main__":
    asyncio.run(main("要聞"))

"""
{'news_id': '9306002', 
'title': '新興市場上周持續吸引資金流入 台股最吸金', 
'points': ['新興市場ETF連續15週吸引資金，累計流入428億美元；上週（截至1月30日）再吸金65億美元，無國家資金流出。', 
            '台灣資產上週吸金13.93億美元稱冠新興市場，全數流入台股ETF，南韓與中港分居二、三名。', 
            '今年來新興市場已吸金249億美元，反映AI類股暴漲、美國政策不確定性及美元疲軟，促使投資人調整地理曝險。', 
            '瑞銀預期2026年投資主軸為分散投資，將提振新興市場表現，特別是過去配置比率偏低的地區。']
            }
"""