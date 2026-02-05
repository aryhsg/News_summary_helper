sys.path.append(os.path.dirname(os.path.abspath(__file__)))
print("目前的搜尋路徑有：", sys.path)
import os
import sys
import json
import httpx
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.responses import PlainTextResponse


load_dotenv()
from infrastructure import db
from gemini import gemini_client
from infrastructure.redis_manager import redis_manager
from line_bot.msg_templates import templates
cate_news_list = templates.Cate_News_list_Template()
catelist = templates.CateList_Template()
sing_news = templates.Single_News_Template()
# -------------------------------------------------------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global gemini
    print(f"DEBUG: DB_HOST is {os.environ.get('DB_HOST')}")
    # --- App 啟動時執行 ---
    await DB.pool_init() 
    await redis_manager.init_pool()
    print("資料庫連線池與 Redis 連線池已開啟")
    gemini = gemini_client()
    print("Gemini API Client 已就緒")
    yield
    # --- App 關閉時執行 ---
    await gemini.close()
    print("Gemini API Client 已斷線")
    await DB.pool_close()
    await redis_manager.close()
    print("資料庫連線池與 Redis 連線池已關閉")


# 應用程式實例命名為 app
app = FastAPI(lifespan=lifespan)
DB = db.NewsDB()
gemini = None
CATE_LIST = ["要聞","國際","證券","期貨","理財","房市","兩岸","金融","專欄","專題","商情","產業"]
API_URL = "https://api.line.me/v2/bot/message/reply"
# --- 從環境變數中讀取設定 ---
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
# ----------------------------
if not WEBHOOK_URL:
    raise ValueError("FATAL: WEBHOOK_URL environment variable is not set!")

# -------------------------------------------------------------------------------------------------------------------------------
# 註冊 POST 路由，用於接收 LINE Webhook
@app.post("/callback")
# 使用 async 關鍵字，並從 Request 物件中讀取數據
async def line_webhook_forwarder(request: Request):
    
    print("--- 收到新的請求 ---")
    print(f"訪問域名 (Host): {request.headers.get('Host')}")
    print(f"真實 IP (X-Real-IP): {request.headers.get('X-Real-IP')}")
    print(f"轉發鏈條 (X-Forwarded-For): {request.headers.get('X-Forwarded-For')}")
    print(f"通訊協定 (X-Forwarded-Proto): {request.headers.get('X-Forwarded-Proto')}")
    print("--------------------")
    # 取得 LINE 傳來的原始請求內容 (Body)
    # 必須使用 await request.body() 來處理非同步數據流
    body = await request.body()

    decoded_body = json.loads(body.decode('utf-8')) # 將 bytes 轉為字串

    print(f"收到來自 LINE 的訊息內容: {decoded_body}")

    # 檢查是否有事件發生
    if decoded_body.get("events"):
        if decoded_body['events'][0]['type'] == 'message' and decoded_body['events'][0]['message']['text'] == '查詢類別新聞':
            # 直接把資料傳給你的回覆函式
            # 這裡會等待回覆完成才回傳 OK 給 LINE
            
            await return_catelist(d_body=decoded_body)

        if decoded_body['events'][0]['type'] == 'postback' and decoded_body['events'][0]['postback']['data'] in CATE_LIST:
            cate = decoded_body['events'][0]['postback']['data']

            print(f"確認類別成功， 類別為： {cate}")

            result = await DB.fetch_cate_news(category=cate)
            await return_newslist(d_body=decoded_body, query_result=result)

        if decoded_body['events'][0]['type'] == 'postback' and decoded_body['events'][0]['postback']['data'].startswith("http") :
            url = decoded_body['events'][0]['postback']['data']
            news_id = url.split("/")[-1].split("?")[0]
            summary = await generate_summary_with_lock(news_id=news_id)
            await return_news_summary(d_body=decoded_body, news_summary=summary)
                
    # 立即回覆給 LINE 伺服器 (必須是 200 OK，使用 PlainTextResponse 確保回應乾淨)
    return PlainTextResponse("OK", status_code=200)

# -------------------------------------------------------------------------------------------------------------------------------
async def return_catelist(d_body: dict):
    Cate_list = catelist.generate_flex_messages(d_body)
    header = {  
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('ChannelAccessToken')}"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, headers=header, json=Cate_list)
        except httpx.RequestError as e:
            print(f"請求錯誤: {e}")
            return
    print(f"回覆訊息狀態碼: {response.status_code}")
    print(f"回覆訊息內容: {response.text}")

# -------------------------------------------------------------------------------------------------------------------------------
async def return_newslist(d_body: dict, query_result: list):
    newslist = cate_news_list.generate_flex_messages(d_body, query_result)
    header = {  
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('ChannelAccessToken')}"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, headers=header, json=newslist)
        except httpx.RequestError as e:
            print(f"請求錯誤: {e}")
            return
    print(f"回覆訊息狀態碼1: {response.status_code}")
    print(f"回覆訊息內容1: {response.text}")

# -------------------------------------------------------------------------------------------------------------------------------
async def return_news_summary(d_body: dict, news_summary: str):  
    news = sing_news.generate_flex_messages(msg= d_body, news_summary= news_summary)
    header = {  
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('ChannelAccessToken')}"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, headers=header, json=news)
        except httpx.RequestError as e:
            print(f"請求錯誤: {e}")
            return
    print(f"回覆訊息狀態碼1: {response.status_code}")
    print(f"回覆訊息內容1: {response.text}")
# -------------------------------------------------------------------------------------------------------------------------------
async def generate_summary_with_lock(news_id:int):
    result = await DB.fetch_specific_summary(news_id)

    if result and result[0].get("news_summary"):
        summary = result[0].get("news_summary")
        print("資料庫存在該新聞摘要")
        return summary

    async with redis_manager.get_lock(str(news_id), timeout=60):        
        result = await DB.fetch_specific_summary(news_id)
        
        if result and result[0].get("news_summary"):
            summary = result[0].get("news_summary")
            return summary

        print("該新聞目前無摘要，正在生成中...")
        query_result = await DB.fetch_news_content(news_id) # [(news_id, title, content, category)]
        contents = json.dumps(query_result) # GEMINI不收list，所以要轉成json字串
        category = query_result[0]["category"]
    
        result = await gemini.generate_summary(instruction_type = "sg", contents = contents) # 預計會follow NewsSummarySchema
        result = json.loads(result)
        print(result)
        summary = result[0].get("points", [])
        summary_str = ""
        for i, p in enumerate(summary):
            summary_str += f"{i+1}. {p}\n"
        await DB.insert_news_summary([(result[0].get("news_id", ""), summary_str, category)])
        print("摘要成功存入資料庫")
        return summary_str


# -------------------------------------------------------------------------------------------------------------------------------
@app.get("/callback")
def read_root():
    return {"status": "OK"}

# -------------------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    """asyncio.run(return_catelist(d_body=decoded_body))
    asyncio.run(return_newslist(d_body=decoded_body, query_result=result))"""
    """   import uvicorn
        # 本地測試時，使用 uvicorn 啟動
        uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)"""


"""
收到來自 LINE 的訊息內容: {'destination': 'U8def8fa29b2adf0976af7a18038a2a7c', 
'events': [
{'type': 'postback', 
'postback': {'data': '9304589'}, 
'webhookEventId': '01KGGPGZP78GT523RJGE6XRTG5', 
'deliveryContext': {'isRedelivery': False}, 
'timestamp': 1770087022068, 
'source': {'type': 'user', 'userId': 'U4c195fa646faf930e6cae1e38b8c0153'}, 
'replyToken': '4ff289a4b0e44c98bbafe5e087ab8dc9', 
'mode': 'active'}]}
"""