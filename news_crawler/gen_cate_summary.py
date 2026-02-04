import asyncio
import db
import os
import sys
import json
from dotenv import load_dotenv

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)


from gemini import gemini_client

load_dotenv()
DB = db.NewsDB()
gemini = gemini_client()



async def generate_cate_summary(category: str):
    news_list = []
    try:
        query_result = await DB.fetch_news_content(category=category) # [{category, news_id, title, content}]
        if not query_result:
            print(f"類別 {category} 找不到任何新聞內容")
            return None
        else:
            for item in query_result[:2]:
                input_template = {
                    "news_id": item.get("news_id", ""),
                    "title": item.get("title", ""),
                    "content": item.get("content", "")
                }
                news_list.append(input_template)
            print(news_list)
            news_json = json.dumps(news_list, ensure_ascii=False)
            try:
                response = await gemini.generate_summary(instruction_type="cate", contents=news_json)
                if response:
                    print("生成成功")
                    print(response)
                    print("--- 原始內容偵錯 ---")
                    print(repr(response)) 
                    print(f"字串長度: {len(response)}")
                else:
                    print("生成失敗")
            except Exception as e:
                print(f"gemini error: {e}")

    except Exception as e:
        print(f"db error: {e}")
    finally:
            await gemini.close()


async def main(category:str):
    await DB.pool_init()
    await generate_cate_summary(category=category)
    await DB.pool_close()

if __name__ == "__main__":
    asyncio.run(main("國際"))
