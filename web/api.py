import os
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from gemini import gen_summary_lock
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List

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

def create_web_app(db_instance, gemini_instance, redis_instance):

    @asynccontextmanager
    async def web_app_lifespan(app: FastAPI):
        newsdb = db_instance
        redis = redis_instance
        ai = gemini_instance
        await newsdb.pool_init()
        await redis.init_pool()
        #app.state.newsdb = newsdb
        yield {"newsdb": newsdb, "redis": redis, "gemini": ai}

        await newsdb.pool_close()
        await redis.close()
        await ai.close()

    app = FastAPI(lifespan=web_app_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/news", response_model=List[NewsListItem])
    async def get_news_list(request: Request):
        newsdb = request.state.newsdb
        news = await newsdb.web_fetch_news()
        return news


    @app.get("/api/news/{news_id}", response_model=NewsDetail)
    async def get_news_content(news_id: str, request: Request):
        newsdb = request.state.newsdb
        contents = await newsdb.web_fetch_news_contents(news_id=news_id)
        if not contents:
            raise HTTPException(status_code=404, detail="News not found")
        return contents[0]

    @app.post("/api/news/{news_id}/summary", response_model=NewsSummary)
    async def get_news_summary(news_id: str, request: Request):
        newsdb = request.state.newsdb
        redis = request.state.redis
        gemini = request.state.gemini
        summary = await gen_summary_lock.generate_summary_with_lock(news_id=news_id, redis_instance=redis, gemini_instance=gemini, db_instance=newsdb)
        html_summary = gen_summary_lock.advanced_format_summary(summary)
        return {"id": news_id, "summary": html_summary}

    @app.get("/api/news/search?q={keyword}", response_model=List[NewsListItem])
    async def search_news(keyword: str, request: Request):
        newsdb = request.state.newsdb
        results = await newsdb.web_search_news(keyword=keyword)
        return results
    
    return app
