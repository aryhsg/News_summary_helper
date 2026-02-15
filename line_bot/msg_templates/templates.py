import copy

class Templates:
    def __init__(self):
        self.msg_body = ""
        self.msg_temp= ""


class Single_News_Template(Templates): # 單篇新聞摘要模板
    def __init__(self):
        super().__init__()
        self.msg_body = {
        "replyToken": f"",
        "messages": [
            {
                "type": "flex",
                "altText": "您選擇的新聞摘要已經整理好囉",
                "contents": {
                    "type": "bubble",
                    "size": "giga",
                    "header": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                # 替換成實際的分類
                                "text": f"以下是類新聞列表",
                                "size": "lg",
                                "weight": "bold",
                                "wrap": True,
                                "margin": "none",
                                "color": "#f2f7ff"
                            }
                        ],
                        "background": {
                            "type": "linearGradient",
                            "angle": "120deg",
                            "endColor": "#10002b",
                            "startColor": "#3c096c",
                            "centerColor": "#10002b",
                            "centerPosition": "40%"
                        }
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        # 最終的內容會被填充到這裡
                        "contents": [],
                        "backgroundColor": "#10002b"
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "uri",
                                    "label": "📃 看全文",
                                    "uri": "http://linecorp.com/"
                                },
                                "color": "#FFFFFF"
                            }
                        ],
                        "backgroundColor": "#ffba08",
                        "cornerRadius": "none",
                        "flex": 1,
                        "paddingAll": "none",
                        "offsetStart": "none",
                        "background": {
                            "type": "linearGradient",
                            "angle": "90deg",
                            "startColor": "#ff9100",
                            "endColor": "#ff9e00",
                            "centerColor": "#ff8500"
                        }
                    }
                }
            }
        ]
    }
        self.msg_temp = {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "", # 👈 這裡將填入標題 (title)
                "position": "relative",
                "wrap": True,
                "align": "start",
                "weight": "bold",
                "margin": "md",
                "color": "#e7ecef",
                "offsetBottom": "sm",
                "lineSpacing": "8px",
                "size": "lg"
            }
        ],
        "borderColor": "#023e7d",
        "borderWidth": "0.7px",
        "cornerRadius": "sm",
        "margin": "md",
        "offsetBottom": "md",
        "paddingStart": "lg",
        "paddingEnd": "md",
        "background": {
            "type": "linearGradient",
            "angle": "180deg",
            "startColor": "#3d05dd",
            "endColor": "#240046",
            "centerColor": "#4f04a3",
            "centerPosition": "50%"
            }
    }
    def generate_flex_messages(self, msg, news_summary: str):
        """
        根據新聞數據和分類，生成完整的 Flex Message JSON 結構。
        """
        current_body = copy.deepcopy(self.msg_body)
        current_temp = copy.deepcopy(self.msg_temp)

        current_body["replyToken"] = f"{msg['events'][0]['replyToken']}"
        current_temp["contents"][0]["text"] = news_summary
        current_body["messages"][0]["contents"]["header"]["contents"][0]["text"] = f"📣"
        current_body["messages"][0]["contents"]["footer"]["contents"][0]["action"]["uri"] = msg["events"][0]["postback"]["data"]
        current_body["messages"][0]["contents"]["body"]["contents"].append(current_temp)

        return current_body


class Cate_News_Summary_Template(Templates): # 類別新聞摘要模板
    def __init__(self):
        super().__init__()
        self.msg_body = {
    "replyToken": f"",
    "messages": [
        {
            "type": "flex",
            "altText": f"123",
            "contents": {
                "type": "bubble",
                "size": "giga",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            # 替換成實際的分類
                            "text": f"以下是類新聞列表", 
                            "size": "lg",
                            "weight": "bold",
                            "margin": "none",
                            "color": "#e7ecef"
                        }
                    ],
                     "background": {
                        "type": "linearGradient",
                        "angle": "120deg",
                        "startColor": "#3c096c",
                        "endColor": "#10002b",
                        "centerColor": "#10002b",
                        "centerPosition": "40%"
                      }
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    # 最終的內容會被填充到這裡
                    "contents": [],
                    "backgroundColor": "#10002b"
                }
            }
        }
    ]
}

        self.msg_temp = {
    "type": "box",
    "layout": "vertical",
    "contents": [
        {
            "type": "text",
            "text": "", # 👈 這裡將填入標題 (title)
            "position": "relative",
            "wrap": True,
            "align": "start",
            "weight": "bold",
            "margin": "md",
            "color": "#f2f7ff",
            "offsetBottom": "sm",
             "size": "md"
        }
    ],
    "borderColor": "#D5C67A",
    "borderWidth": "none",
    "cornerRadius": "sm",
    "flex": 1,
    "margin": "md",
    "paddingAll": "md",
    "spacing": "xs",
    "background": {
          "type": "linearGradient",
          "angle": "135deg",
          "startColor": "#3d05dd",
          "endColor": "#240046",
          "centerColor": "#4f04a3",
          "centerPosition": "50%"
        },
    "paddingStart": "lg",
    "paddingEnd": "md"
}

    def generate_flex_messages(self, msg, cate_summary: str):
        current_body = copy.deepcopy(self.msg_body)
        current_temp = copy.deepcopy(self.msg_temp)

        current_body["replyToken"] = f"{msg['events'][0]['replyToken']}"
        current_temp["contents"][0]["text"] = cate_summary
        current_body["messages"][0]["contents"]["header"]["contents"][0]["text"] = f"📣"
        current_body["messages"][0]["contents"]["body"]["contents"].append(current_temp)

        return current_body        



class Cate_News_list_Template(Templates): # 新聞列表模板
    def __init__(self):
        super().__init__()
        self.msg_body = {
    "replyToken": f"",
    "messages": [
        {
            "type": "flex",
            "altText": f"",
            "contents": {
                "type": "bubble",
                "size": "giga",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            # 替換成實際的分類
                            "text": f"🗂️ 以下是類新聞列表", 
                            "size": "sm",
                            "weight": "bold",
                            "margin": "none",
                            "color": "#e7ecef"
                        }
                    ],
                    "backgroundColor": "#ffba08",
                     "background": {
                        "type": "linearGradient",
                        "angle": "120deg",
                        "startColor": "#3c096c",
                        "endColor": "#10002b",
                        "centerColor": "#10002b",
                        "centerPosition": "40%"
                      }
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    # 最終的內容會被填充到這裡
                    "contents": [],
                    "backgroundColor": "#10002b"
                }
            }
        }
    ]
}
        self.msg_temp = {
    "type": "box",
    "layout": "vertical",
    "contents": [
        {
            "type": "text",
            "text": "這是新聞的實際標題", 
            "position": "relative",
            "wrap": True,
            "align": "start",
            "weight": "bold",
            "margin": "md",
            "color": "#f2f7ff",
            "offsetBottom": "sm",
            "size": "lg",
            
        }
    ],
    "background": {
        "type": "linearGradient",
        "angle": "135deg",
        "startColor": "#3d05dd",
        "endColor": "#240046",
        "centerColor": "#4f04a3",
        "centerPosition": "25%"
    },
    "paddingStart": "lg",
    "paddingEnd": "md",
    "paddingBottom": "sm",
    "height": "60px", 
    "cornerRadius": "sm",
    "margin": "md",
    "action": {
              "type": "postback",
              "label": "action",
              "data": "",
              "displayText": "請稍後，生成摘要中..."
            }
}
        
        self.base_bubble = {
    "type": "bubble",
    "size": "giga",
    "header": {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "🗂️ 以下是分類新聞列表", 
                "size": "lg",
                "weight": "bold",
                "margin": "none",
                "color": "#e7ecef"
            }
        ],
        "backgroundColor": "#ffba08",
        "background": {
            "type": "linearGradient",
            "angle": "120deg",
            "startColor": "#3c096c",
            "endColor": "#10002b",
            "centerColor": "#10002b",
            "centerPosition": "40%"
        }
    },
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [], # 新聞項目將會填充到這裡
        "backgroundColor": "#10002b"
    }
}
        
    def __chunk_list(self, data, size):
        """將列表分割成固定大小的子列表 (Chunks)"""
        for i in range(0, len(data), size):
            yield data[i:i + size]

    def generate_flex_messages(self, msg, news_dict: list):
        # 1. 設定每個 Bubble 項目數
        ITEMS_PER_BUBBLE = 10
        news_chunks = list(self.__chunk_list(news_dict, ITEMS_PER_BUBBLE))
        bubble_contents = [] 

        # 取得分類名稱 (預設值處理)
        category_name = news_dict[0].get('category', '未知') if news_dict else "未知"

        for chunk in news_chunks:
            # --- 關鍵修正 1：每次迴圈都產生一個「全新的 Bubble」副本 ---
            new_bubble = copy.deepcopy(self.base_bubble)
            
            # 更新 Header 標題
            new_bubble["header"]["contents"][0]["text"] = f"📰 以下是【{category_name}】類新聞"

            # 取得該副本的 body 列表
            body_contents_list = new_bubble["body"]["contents"]
        
            for news_item in chunk:
                # --- 關鍵修正 2：每次迴圈都產生一個「全新新聞項目」副本 ---
                new_item = copy.deepcopy(self.msg_temp)
                
                # 填充內容
                new_item["contents"][0]["text"] = news_item.get("title", "無標題")
                new_item["action"]["data"] = news_item.get("url", "")
                
                # 將「項目副本」放入「Bubble 副本」中
                body_contents_list.append(new_item)
            
            # 將「填滿新聞的 Bubble 副本」放入輪播列表
            bubble_contents.append(new_bubble)

        # 2. 建立 Carousel 結構
        carousel_message = {
            "type": "flex",
            "altText": "您的新聞列表出來囉",
            "contents": {
                "type": "carousel",
                "contents": bubble_contents 
            }
        }

        # 3. 封裝回傳
        self.msg_body = {
            "replyToken": f"{msg['events'][0]['replyToken']}",
            "messages": [carousel_message]
        }
        
        return self.msg_body


class CateList_Template(Templates): # 類別列表模板
    def __init__(self):
        super().__init__()
        self.cate_list = ["要聞","國際","證券","期貨","理財","房市","兩岸","金融","專欄","專題","商情","產業"]

        self.msg_body = {
        "replyToken": f"",
        "messages": [
            {
                "type": "flex",
                "altText": "您的新聞類別列表出來囉",
                "contents": {
                    "type": "bubble",
                    "size": "kilo",
                    "header": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                # 替換成實際的分類
                                "text": f"🗂️ 選擇您關心的類別新聞", 
                                "size": "md",
                                "weight": "bold",
                                "margin": "none",
                                "color": "#e7ecef"
                            }
                        ],
                        "backgroundColor": "#ffba08",
                        "background": {
                            "type": "linearGradient",
                            "angle": "120deg",
                            "startColor": "#3c096c",
                            "endColor": "#10002b",
                            "centerColor": "#10002b",
                            "centerPosition": "40%"
                        }
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        # 最終的內容會被填充到這裡
                        "contents": [],
                        "backgroundColor": "#10002b"
                    }
                }
            }
        ]
    }
        self.msg_temp = {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "這是新聞的實際標題", 
                "position": "relative",
                "wrap": True,
                "align": "start",
                "weight": "bold",
                "margin": "md",
                "color": "#f2f7ff",
                "size": "md"
                
            }
        ],
        "background": {
            "type": "linearGradient",
            "angle": "135deg",
            "startColor": "#3d05dd",
            "endColor": "#240046",
            "centerColor": "#4f04a3",
            "centerPosition": "25%"
        },
        "paddingStart": "md",
        "paddingBottom": "sm",
        "cornerRadius": "sm",
        "margin": "md",
        "action": {
                "type": "postback",
                "label": "action",
                "data": "",
                "displayText": "請稍後，加載內容中..."
                }
    }
        
    def generate_flex_messages(self, msg):
        self.msg_body["replyToken"] = f"{msg['events'][0]['replyToken']}"   

        # 清空之前的內容，避免重複呼叫時累積
        self.msg_body["messages"][0]["contents"]["body"]["contents"] = []
        body_contents_list = self.msg_body["messages"][0]["contents"]["body"]["contents"]
        
        for cate in self.cate_list:
            # 2. 使用 deepcopy 複製一個獨立的模板副本
            temp_item = copy.deepcopy(self.msg_temp)
            
            # 3. 修改這個「副本」的內容
            temp_item["contents"][0]["text"] = cate
            
            if msg['events'][0]["message"]["text"] == "請選擇感興趣類別":
                temp_item["action"]["data"] = cate
                temp_item["action"]["displayText"] = f"正在載入【{cate}】新聞列表..."
            else:
                temp_item["action"]["data"] = f"{cate}_摘要"
                temp_item["action"]["label"] = f"{cate}類新聞" 
                temp_item["action"]["displayText"] = f"正在生成【{cate}】新聞摘要..."
            
            # 4. 將副本添加到列表
            body_contents_list.append(temp_item)
        
        return self.msg_body