import asyncio

import os
import sys
import json
from dotenv import load_dotenv

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)

from infrastructure import db
from gemini import gemini_service

load_dotenv()
DB = db.NewsDB()
ai = gemini_service()



async def generate_cate_summary(category: str):
    news_list = []
    try:
        query_result = await DB.fetch_news_summary(category=category) # [{news_id, title, category, content}]
        if not query_result:
            print(f"類別 {category} 找不到任何新聞內容")
            return None
        else:
            news_json = json.dumps(query_result, ensure_ascii=False)
            try:
                response = await ai.generate_summary(instruction_type="cate", contents=news_json)
                if response:
                    print("生成成功")
                    print(response)
                    """print("--- 原始內容偵錯 ---")
                    print(repr(response)) """
                    print(f"字串長度: {len(response)}")
                else:
                    print("生成失敗")
            except Exception as e:
                print(f"gemini error: {e}")

    except Exception as e:
        print(f"db error: {e}")
    finally:
            await ai.close()


async def main(category:str):
    await DB.pool_init()
    try:
        print("generating vategory summary...")
        await generate_cate_summary(category=category)
    except Exception as e:
        print(f"error: {e}")
    finally:
        await DB.pool_close()

if __name__ == "__main__":
    asyncio.run(main("要聞"))
