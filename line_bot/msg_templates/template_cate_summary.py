import json
import copy
from pprint import pprint

# 假設這是 n8n 的特殊語法，用於獲取輸入數據。
# 在純 Python 環境中，您需要將這些替換為實際的數據結構。
# 這裡暫時用佔位符代替，讓結構更清晰。
# ------------------------------------------------------------
# 假設的輸入數據結構（在實際 n8n 執行時會被替換）
# 為了讓代碼可運行，我們將 n8n 的特殊語法替換為字串佔位符或模擬數據。

# ------------------------------------------------------------

# 基礎的 Flex Message 容器
msg_body = {
    "replyToken": f"{_('Webhook').first().json.body.events[0].replyToken}",
    "messages": [
        {
            "type": "flex",
            "altText": f"您選擇的【{_('If3').first().json.body.events[0].postback.data}】已經整理好囉",
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

# 單個新聞項目的 Flex Message 模板
msg_temp = {
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

msg_temp["contents"][0]["text"] = _input.first().json.summary
msg_body["messages"][0]["contents"]["header"]["contents"][0]["text"] = f"📰 以下為今日的【{_('If3').first().json.body.events[0].postback.data}】"
msg_body["messages"][0]["contents"]["body"]["contents"].append(msg_temp)

