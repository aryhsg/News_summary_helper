import requests
import db
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()
DB = db.NewsDB()

async def scrape_and_process_news():
    try:
        response = await asyncio.to_thread(requests.get, "https://aryhsgsnewsapi.onrender.com/api/scrape-all-news/")
        if response.status_code == 200:
            news_data = response.json() # 直接把回傳的 JSON 轉成 Python 字典
            processed_news = []
            for item in news_data["data"]:
                category  = item.get("category", "N/A")
                link_list = item.get("url", [])
                title_list = item.get("title", [])
                content_list = item.get("content", [])
                image_list = item.get("image", [])
                keywords_list = item.get("keyword", [])
                for link, title, content, image, keywords in zip(link_list, title_list, content_list, image_list, keywords_list):
                    news_id = link.split("/")[-1].split("?")[0]  # 從 URL 中提取新聞 ID
                    single_news = (
                        news_id,
                        category,
                        title,
                        content,
                        link,
                        image,
                        keywords
                    )
                    processed_news.append(single_news)
            # 現在 processed_news 包含了所有新聞的清單，每個新聞都是一個字典
            print(processed_news[0:5])  # 印出前五筆新聞資料作為範例
            await DB.pool_init()
            await DB.insert_news(processed_news)
            await debug_check_db(DB)
            print("新聞資料已成功寫入資料庫。")
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await DB.pool_close()



async def debug_check_db(db_client):
    """專門用來檢查資料庫到底有沒有東西的函數"""
    print("\n--- 正在進行資料庫即時驗證 ---")
    async with db_client.pool.connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT news_id, title FROM news LIMIT 5")
            rows = await cursor.fetchall()
            if rows:
                print(f"✅ 驗證成功！資料庫內目前有 {len(rows)} 筆最新資料：")
                for row in rows:
                    print(f"ID: {row[0]} | 標題: {row[1][:20]}...")
            else:
                print("❌ 驗證失敗：資料庫內仍然空空如也。")


if __name__ == "__main__":
    asyncio.run(scrape_and_process_news())