import json
import copy
from pprint import pprint


# 基礎的 Flex Message 容器
msg_body = {
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
                    # 最終的內容會被填充到這裡
                    "contents": [],
                    "backgroundColor": "#10002b"
                }
            }
        }
    ]
}

# 單個新聞項目的 Flex Message 模板
msg_temp = {
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

BASE_BUBBLE = {
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

def chunk_list(data, size):
    """將列表分割成固定大小的子列表 (Chunks)"""
    for i in range(0, len(data), size):
        yield data[i:i + size]

def generate_flex_messages(msg, news_dict: list):
    """
    根據新聞數據和分類，生成完整的 Flex Message JSON 結構。
    """
    # 1. 初始化用於存放結果的列表
    # 3. 創建並填充 msg_body
    # 由於 msg_body 是全域變數，我們先複製一份以確保每次調用都是新的結構
    final_msg_body = copy.deepcopy(msg_body)

  # ----------------------------------------------------
    # 2. 核心邏輯：分批處理並創建多個 Bubble (Carousel 模式)
    # ----------------------------------------------------
    
    # 設定每個 Bubble 中要包含的最大新聞項目數
    # 12 個項目在大多數情況下是安全的
    ITEMS_PER_BUBBLE = 10

    news_chunks = list(chunk_list(news_dict, ITEMS_PER_BUBBLE))
    bubble_contents = [] # 用來存放所有 Bubble 的列表

    for index, chunk in enumerate(news_chunks):
        # 複製基礎 Bubble 模板
        current_bubble = copy.deepcopy(BASE_BUBBLE)
    # 更新 Header 標題
        header_text_path = current_bubble["header"]["contents"][0]
        header_text_path["text"] = f"📰以下是【{news_dict[0].get('category', '未知')}】類新聞列表"

    # 4. 迴圈填充 Body 內容
        body_contents_list = current_bubble["body"]["contents"]
    
        for news_item in chunk:
            new_msg_temp = copy.deepcopy(msg_temp)
            
            # 填充標題
            new_msg_temp["contents"][0]["text"] = news_item.get("title")
            
            # 填充 URL
            #new_msg_temp["action"]["uri"] = news_item.get("url")
            new_msg_temp["action"]["data"] = news_item.get("url")
            
            body_contents_list.append(new_msg_temp)
            
        bubble_contents.append(current_bubble)

# ----------------------------------------------------
    # 3. 創建最終的 LINE Message API 結構
    # ----------------------------------------------------
    
    # 創建一個包含所有 Bubble 的 Carousel 容器
    carousel_message = {
        "type": "flex",
        "altText": f"您的新聞列表出來囉",
        "contents": {
            "type": "carousel", # 關鍵：使用 carousel
            "contents": bubble_contents # 放入所有 Bubble
        }
    }


# 最終的訊息 API Body (你需要根據 n8n 的 Webhook 數據填寫 replyToken)
    final_msg_body = {
        "replyToken": f"{msg['events'][0]['replyToken']}", # 必須從 Webhook 取得
        "messages": [
            carousel_message
        ]
    }
    
    return final_msg_body
