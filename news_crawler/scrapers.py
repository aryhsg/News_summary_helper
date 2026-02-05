import requests
import infrastructure.db as db
import asyncio
from dotenv import load_dotenv

load_dotenv()
DB = db.NewsDB()

async def scrape_news():
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
            #print(processed_news[0:5])  # 印出前五筆新聞資料作為範例
            print(f"成功爬取 {len(processed_news)} 則新聞")
            return processed_news
        
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")
        return






if __name__ == "__main__":
    asyncio.run(scrape_news())