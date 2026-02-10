import uvicorn
import os
import sys
from dotenv import load_dotenv

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)
load_dotenv()
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from gemini import gen_summary_lock, gemini_client
from infrastructure import redis_manager
from infrastructure import db
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    newsdb = db.NewsDB()
    redis = redis_manager.RedisManager()
    ai = gemini_client.gemini_service()
    await newsdb.pool_init()
    await redis.init_pool()
    #app.state.newsdb = newsdb
    yield {"newsdb": newsdb, "redis": redis, "gemini": ai}

    await newsdb.pool_close()
    await redis.close()
    await ai.close()

app = FastAPI(lifespan=lifespan)

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

    return {"id": news_id, "summary": summary}

@app.get("/api/news/search?q={keyword}", response_model=List[NewsListItem])
async def search_news(keyword: str, request: Request):
    newsdb = request.state.newsdb
    results = await newsdb.web_search_news(keyword=keyword)
    return results

if __name__ == "__main__":


    uvicorn.run(app, host="0.0.0.0", port=8000)