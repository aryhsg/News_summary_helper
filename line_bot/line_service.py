import httpx
import os
import json

from gemini import gen_summary_lock, get_str_summary
from line_bot.msg_templates import templates
cate_news_list = templates.Cate_News_list_Template()
catelist = templates.CateList_Template()
sing_news = templates.Single_News_Template()
cate_news = templates.Cate_News_Summary_Template()



class line_forward_rules:
    def __init__(self, db_instance, gemini_instance, redis_instance):

        self.db = db_instance
        self.gemini = gemini_instance
        self.redis = redis_instance
        self.CATE_LIST = ["要聞","國際","證券","期貨","理財","房市","兩岸","金融","專欄","專題","商情","產業"]
        self.API_URL = "https://api.line.me/v2/bot/message/reply"

    async def forward_rule(self, d_body):
    # 檢查是否有事件發生
        if d_body.get("events"):
            if d_body['events'][0]['type'] == 'message' and d_body['events'][0]['message']['text'] == '請選擇感興趣類別':
                # 直接把資料傳給你的回覆函式
                # 這裡會等待回覆完成才回傳 OK 給 LINE
                
                await self.__return_catelist(d_body)

            
            if d_body['events'][0]['type'] == 'message' and d_body['events'][0]['message']['text'] == '選擇欲生成摘要的類別':
                # 類別摘要
                
                await self.__return_catelist(d_body)   

            if d_body['events'][0]['type'] == 'message' and d_body['events'][0]['message']['text'] != '請選擇感興趣類別':
                # 關鍵字查詢

                k_word = d_body['events'][0]['message']['text']

                result = await self.db.fetch_news_content(keyword= k_word)
                if result:
                    await self.__return_newslist(d_body=d_body, query_result=result)
                else: 
                    await self.text_message(d_body=d_body)

            if d_body['events'][0]['type'] == 'postback' and d_body['events'][0]['postback']['data'] in self.CATE_LIST:
                cate = d_body['events'][0]['postback']['data']

                print(f"確認類別成功， 類別為： {cate}")

                result = await self.db.fetch_cate_news(category=cate)
                if result:
                    await self.__return_newslist(d_body=d_body, query_result=result)
                else: 
                    await self.text_message(d_body=d_body, has_news=False)


            if d_body['events'][0]['type'] == 'postback' and "_摘要" in d_body['events'][0]['postback']['data']:
                cate = d_body['events'][0]['postback']['data'].split("_")[0]

                print(f"確認類別成功， 類別為： {cate}")

                result = await self.db.fetch_cate_summary(category= cate)
                summary = get_str_summary(raw_summary=result[0])

                await self.__return_cate_summary(d_body=d_body, cate_summary=summary)

            if d_body['events'][0]['type'] == 'postback' and d_body['events'][0]['postback']['data'].startswith("http") :
                url = d_body['events'][0]['postback']['data']
                news_id = url.split("/")[-1].split("?")[0]
                summary = await gen_summary_lock.generate_summary_with_lock(news_id=news_id, db_instance=self.db, redis_instance=self.redis, gemini_instance=self.gemini)
                await self.__return_news_summary(d_body=d_body, news_summary=summary)


    async def __return_catelist(self, d_body):
        Cate_list = catelist.generate_flex_messages(d_body)
        header = {  
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('ChannelAccessToken')}"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.API_URL, headers=header, json=Cate_list)
            except httpx.RequestError as e:
                print(f"請求錯誤: {e}")
                return
        print(f"回覆訊息狀態碼: {response.status_code}")
        print(f"回覆訊息內容: {response.text}")

    # -------------------------------------------------------------------------------------------------------------------------------
    async def __return_newslist(self, d_body, query_result: list):
        newslist = cate_news_list.generate_flex_messages(d_body, query_result)
        header = {  
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('ChannelAccessToken')}"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.API_URL, headers=header, json=newslist)
            except httpx.RequestError as e:
                print(f"請求錯誤: {e}")
                return
        print(f"回覆訊息狀態碼: {response.status_code}")
        print(f"回覆訊息內容: {response.text}")

    # -------------------------------------------------------------------------------------------------------------------------------
    async def __return_news_summary(self, d_body, news_summary: str):  
        news = sing_news.generate_flex_messages(msg= d_body, news_summary= news_summary)
        header = {  
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('ChannelAccessToken')}"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.API_URL, headers=header, json=news)
            except httpx.RequestError as e:
                print(f"請求錯誤: {e}")
                return
        print(f"回覆訊息狀態碼: {response.status_code}")
        print(f"回覆訊息內容: {response.text}")


    # -------------------------------------------------------------------------------------------------------------------------------
    async def __return_cate_summary(self, d_body, cate_summary: str):  
        news = cate_news.generate_flex_messages(msg= d_body, cate_summary= cate_summary)
        header = {  
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('ChannelAccessToken')}"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.API_URL, headers=header, json=news)
            except httpx.RequestError as e:
                print(f"請求錯誤: {e}")
                return
        print(f"回覆訊息狀態碼: {response.status_code}")
        print(f"回覆訊息內容: {response.text}")

    # -------------------------------------------------------------------------------------------------------------------------------
    async def text_message(self, d_body, has_news: bool | None = None):

        header = {  
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('ChannelAccessToken')}"
        }
        json_msg = {"replyToken": f"{d_body['events'][0]['replyToken']}",
                    "messages":[
                                {
                                    "type": "text",
                                    "text": "此關鍵字尚無新聞",
                                    "color": "#d1cee0",
                                    "weight": "bold",
                                    "size": "md"
                                }
                   ]}
        if not has_news:
            json_msg["messages"][0]["text"] = "此類別尚無新聞"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.API_URL, headers=header, json=json_msg)
            except httpx.RequestError as e:
                print(f"請求錯誤: {e}")
                return
        print(f"回覆訊息狀態碼: {response.status_code}")
        print(f"回覆訊息內容: {response.text}")

