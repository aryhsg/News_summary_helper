import time
import random
from locust import HttpUser, task, between

class TestUser(HttpUser):
    wait_time = between(1, 5)

    """def on_start(self):
        # 建議加上 name="/api/news"，保持報表整潔
        with self.client.get("/api/test/news", name="/api/test/news", catch_response=True) as response:
            if response.status_code == 200:
                news_data = response.json()
                self.news_ids = [news['id'] for news in news_data]
            else:
                print("Failed to fetch news list")
                self.news_ids = []"""
            
    """@task(4)
    def read_news(self):
        if self.news_ids:
            news_id = random.choice(self.news_ids)
            # 修正：改成一個底線，對應下方的函式名稱
            self._user_journey(news_id)"""

    def _user_journey(self, news_id):
        # 優化：加上 name="/api/news/[id]" 讓報表合併統計
        with self.client.get(f"/api/news/{news_id}", name="/api/news/[id]", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"failed to read news: {response.status_code}")
                return # 如果內文失敗，直接中斷，不往下執行
            
        time.sleep(5)

        # 優化：加上 name="/api/news/[id]/summary" 讓報表合併統計
        with self.client.post(f"/api/news/{news_id}/summary", name="/api/news/[id]/summary", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"failed to get summary: {response.status_code}")


    @task
    def test_summary_generation(self):
        with self.client.post("/api/test/news/9338960/summary", name="/api/test/news/[id]/summary", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"failed to get test summary: {response.status_code}")
