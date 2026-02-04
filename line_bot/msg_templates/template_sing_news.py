import json
import copy
from pprint import pprint


def generate_flex_messages(msg, news_summary: str):
    """
    根據新聞數據和分類，生成完整的 Flex Message JSON 結構。
    """
# 基礎的 Flex Message 容器
    msg_body = {
        "replyToken": f"{msg['events'][0]['replyToken']}",
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

    msg_temp["contents"][0]["text"] = news_summary
    msg_body["messages"][0]["contents"]["header"]["contents"][0]["text"] = f"📣"
    msg_body["messages"][0]["contents"]["footer"]["contents"][0]["action"]["uri"] = msg["events"][0]["postback"]["data"]
    msg_body["messages"][0]["contents"]["body"]["contents"].append(msg_temp)

    return msg_body

