import os
import asyncio
from typing import List
from pydantic import BaseModel
from gemini import locking, get_formatted_summary, advanced_format_summary
from fastapi import FastAPI, HTTPException, Security, Depends, status, Query
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from contextlib import asynccontextmanager

from infrastructure.exceptions import DatabaseError, GeminiResponseError, NewsNotFoundError



class NewsListItem(BaseModel):
    id: int
    title: str
    category: str
    img: str

class NewsDetail(NewsListItem):
    content: str

class NewsSummary(BaseModel):
    id: int
    summary: str

class CateSummary(BaseModel):
    category: str
    summary: str


def create_web_app(db_instance, gemini_instance, redis_instance):

    API_KEY = os.getenv("INTERNAL_API_KEY")
    if not API_KEY:
        raise RuntimeError("INTERNAL_API_KEY environment variable is not set")
    API_KEY_NAME = "X-API-KEY"
    api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

    async def get_api_key(header_key: str = Security(api_key_header)):
        if header_key == API_KEY:
            return header_key

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Invalid Security Token"
        )
    
    @asynccontextmanager
    async def global_lifespan(app: FastAPI):

        print(f"DEBUG: DB_HOST is {os.environ.get('HOST')}")
        try:
            # --- App 啟動時執行 ---
            await db_instance.pool_init() 
            await redis_instance.init_pool()
            print("資料庫連線池與 Redis 連線池已開啟")
            gemini = gemini_instance
            print("Gemini API Client 已就緒")
            yield 
        finally:
            # --- App 關閉時執行 ---
            await gemini_instance.close()
            print("Gemini API Client 已斷線")
            await db_instance.pool_close()
            await redis_instance.close()
            print("資料庫連線池與 Redis 連線池已關閉")
            await asyncio.sleep(0.1)


    app = FastAPI(lifespan=global_lifespan)

    @app.exception_handler(DatabaseError)
    async def database_error_handler(request: Request, exc: DatabaseError):
        # DatabaseError 代表 DB 呼叫本身失敗（連線中斷、查詢出錯等），
        # 跟「查詢成功但查到 0 筆」（repository 回傳空 list）是兩種狀況，
        # 不應該都變成 200 空陣列或 404，這裡統一回 503。
        return JSONResponse(status_code=503, content={"detail": "資料庫暫時無法使用，請稍後再試"})

    @app.exception_handler(NewsNotFoundError)
    async def news_not_found_handler(request: Request, exc: NewsNotFoundError):
        # 要求摘要的新聞不存在（常見原因：每日清空資料後，舊頁面還開著）。
        # 回 404，跟 GET /api/news/{id} 找不到時一致，不是 500。
        return JSONResponse(status_code=404, content={"detail": "找不到這則新聞，可能已過期，請重新整理頁面"})

    @app.exception_handler(GeminiResponseError)
    async def gemini_response_error_handler(request: Request, exc: GeminiResponseError):
        # Gemini 有回應但內容不能用（輸出被截斷、JSON 格式錯誤），重試後仍然失敗。
        # 這是上游服務的問題，回 502（不是我們程式的 500），並給使用者能看懂的說明。
        return JSONResponse(status_code=502, content={"detail": "摘要暫時產生失敗，請稍後再試"})

    # 給容器 healthcheck 用：只確認服務能回應，不查資料庫，也不需要金鑰。
    # 路徑放在 /api/ 外面，nginx 不會轉發，外部連不到。
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/news", response_model=List[NewsListItem])
    async def get_news_list(_ = Depends(get_api_key)):
        news = await db_instance.web_fetch_news()
        return news

    # 這條必須定義在 /api/news/{news_id} 之前，否則 "search" 會先被
    # {news_id} 這個萬用路徑參數吃掉，永遠進不到這條路由。
    @app.get("/api/news/search", response_model=List[NewsListItem])
    async def search_news(q: str = Query(...), _ = Depends(get_api_key)):
        newsdb = db_instance
        results = await newsdb.web_search_news(keyword=q)
        return results

    @app.get("/api/news/{news_id}", response_model=NewsDetail)
    async def get_news_content(news_id: str, _ = Depends(get_api_key)):
        contents = await db_instance.web_fetch_news_contents(news_id=news_id)
        if not contents:
            raise HTTPException(status_code=404, detail="News not found")
        return contents[0]

    @app.post("/api/news/{news_id}/summary", response_model=NewsSummary)
    async def get_news_summary(news_id: str, _ = Depends(get_api_key)):
        newsdb = db_instance
        redis = redis_instance
        gemini = gemini_instance
        title, summary = await locking.generate_summary_with_lock(news_id=news_id, redis_instance=redis, gemini_instance=gemini, db_instance=newsdb)
        html_summary = advanced_format_summary(summary)
        return {"id": news_id, "summary": html_summary}

    @app.post("/api/news/summary/{category}", response_model=CateSummary)
    async def get_cate_summary(category: str, _ = Depends(get_api_key)):
        newsdb = db_instance
        raw_summary = await newsdb.fetch_cate_summary(category= category)
        if raw_summary: 

            summary = get_formatted_summary(raw_summary=raw_summary[0])
            return {"category": category, "summary": summary}
        else:
            return {"category": category, "summary": "該類別尚無摘要"}
    

    # /api/sandbox/... 是不耗用 Gemini 配額的示範端點，跟 pytest 單元測試
    # 是兩件事，命名/路徑避免再用「test」避免混淆（Stage 5）。
    @app.get("/api/sandbox/news", response_model=List[NewsListItem])
    async def get_sandbox_news_list(_ = Depends(get_api_key)):
        news = await db_instance.sandbox_fetch_news()
        return news

    @app.post("/api/sandbox/news/{news_id}/summary", response_model=NewsSummary)
    async def get_sandbox_news_summary(news_id: str, _ = Depends(get_api_key)):
        newsdb = db_instance
        redis = redis_instance
        title, summary = await locking.sandbox_generate_summary_with_lock(news_id=news_id, redis_instance=redis, db_instance=newsdb)
        return {"id": news_id, "summary": summary}

    return app
