import redis.asyncio as redis  # 務必使用 .asyncio 版本
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()  # 從 .env 檔案載入環境變數


class RedisManager:
    def __init__(self):
        # 從環境變數讀取連線資訊，增加彈性
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        self.pool = None

    async def init_pool(self):
        """初始化連線池"""
        if not self.pool:
            self.pool = redis.from_url(
                self.redis_url, 
                decode_responses=True, 
                encoding="utf-8"
            )
            print("🚀 Redis 分散式鎖連線池已建立")

    async def close(self):
        """關閉連線"""
        if self.pool:
            await self.pool.close()
            print("💤 Redis 連線已優雅關閉")

    @asynccontextmanager
    async def get_lock(self, news_id: str, timeout: int = 60):
        """
        封裝鎖的邏輯，讓外部調用時只需要：
        async with redis_manager.get_lock("news_123"):
            ...
        """
        lock_name = f"lock:news:{news_id}"
        # 使用 redis-py 內建的 lock
        async with self.pool.lock(lock_name, timeout=timeout) as lock:
            yield lock

# 建立單例物件供全專案引用
redis_manager = RedisManager()
