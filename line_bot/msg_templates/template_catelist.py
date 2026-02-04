import json
import copy
from pprint import pprint



def generate_flex_messages(msg):
    """
    根據新聞數據和分類，生成完整的 Flex Message JSON 結構。
    """

    cate_list = ["要聞","國際","證券","期貨","理財","房市","兩岸","金融","專欄","專題","商情","產業"]
    # 基礎的 Flex Message 容器
    msg_body = {
        "replyToken": f"{msg['events'][0]['replyToken']}",
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
    # 3. 創建並填充 msg_body
    # 由於 msg_body 是全域變數，我們先複製一份以確保每次調用都是新的結構
    final_msg_body = copy.deepcopy(msg_body)

    # 4. 迴圈填充 Body 內容
    body_contents_list = final_msg_body["messages"][0]["contents"]["body"]["contents"]
    
    for cate in cate_list:
        # a. 複製模板
        new_msg_temp = copy.deepcopy(msg_temp)
        
        # b. 填充標題 (contents[0].text)
        new_msg_temp["contents"][0]["text"] = cate
        
        # c. 填充 URL (action.data)
        if msg['events'][0]["message"]["text"] == "查詢類別新聞":
          new_msg_temp["action"]["data"] = cate #####
          new_msg_temp["action"]["displayText"] = f"正在載入【{cate}】新聞列表..."
        else:
          new_msg_temp["action"]["data"] = f"{cate}_摘要"
          new_msg_temp["action"]["label"] = f"{cate}類新聞" 
          new_msg_temp["action"]["displayText"] = f"正在生成【{cate}】新聞摘要..."
        
        # d. 添加到 Body 內容列表
        body_contents_list.append(new_msg_temp)
        
    return final_msg_body

