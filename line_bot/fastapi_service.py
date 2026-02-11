import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.responses import PlainTextResponse
from line_service import line_forward_rules


# -------------------------------------------------------------------------------------------------------------------------------
@asynccontextmanager
async def global_lifespan(db_instance, gemini_instance, redis_instance):

    print(f"DEBUG: DB_HOST is {os.environ.get('HOST')}")
    try:
        # --- App 啟動時執行 ---
        await db_instance.pool_init() 
        await redis_instance.init_pool()
        print("資料庫連線池與 Redis 連線池已開啟")
        gemini = gemini_instance
        print("Gemini API Client 已就緒")
        yield (db_instance, gemini, redis_instance)
    finally:
        # --- App 關閉時執行 ---
        await gemini_instance.close()
        print("Gemini API Client 已斷線")
        await db_instance.pool_close()
        await redis_instance.close()
        print("資料庫連線池與 Redis 連線池已關閉")
        await asyncio.sleep(0.1)


def create_line_app(db_instance, gemini_instance, redis_instance):
    app = FastAPI()
    line_forward = line_forward_rules(
        db_instance=db_instance, 
        gemini_instance=gemini_instance, 
        redis_instance=redis_instance
        )

    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
    if not WEBHOOK_URL:
        raise ValueError("FATAL: WEBHOOK_URL environment variable is not set!")

    @app.post("/callback")
    async def line_webhook_forwarder(request: Request):
        
        print("--- 收到新的請求 ---")
        print(f"訪問域名 (Host): {request.headers.get('Host')}")
        print(f"真實 IP (X-Real-IP): {request.headers.get('X-Real-IP')}")
        print(f"轉發鏈條 (X-Forwarded-For): {request.headers.get('X-Forwarded-For')}")
        print(f"通訊協定 (X-Forwarded-Proto): {request.headers.get('X-Forwarded-Proto')}")
        print("--------------------")

        try:
            body = await request.body()
            decoded_body = json.loads(body.decode('utf-8')) # 將 bytes 轉為字串
            print(f"收到來自 LINE 的訊息內容: {decoded_body}")
            await line_forward.forward_rule(d_body=decoded_body)

        except Exception as e:
            print(f"error: {e}")
                    
        # 立即回覆給 LINE 伺服器 (必須是 200 OK，使用 PlainTextResponse 確保回應乾淨)
        return PlainTextResponse("OK", status_code=200)
    
    @app.get("/callback")
    def read_root():
        return {"status": "OK"}
    
    return app

# -------------------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    """asyncio.run(return_catelist(d_body=decoded_body))
    asyncio.run(return_newslist(d_body=decoded_body, query_result=result))"""
    """   import uvicorn
        # 本地測試時，使用 uvicorn 啟動
        uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)"""

