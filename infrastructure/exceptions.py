class DatabaseError(Exception):
    """包裝底層 psycopg 例外。

    用來跟「DB 呼叫成功、但查到 0 筆」的正常空結果區分開——後者由
    repository 方法直接回傳空 list/None，不會丟這個例外。
    """


class NewsNotFoundError(Exception):
    """要求的新聞在資料庫裡不存在（例如每日清空資料後，舊的網頁或 LINE 按鈕
    還指著已經被清掉的新聞）。跟 DatabaseError 不同：資料庫本身運作正常。
    Web API 轉成 404，LINE 回覆「新聞已過期」。
    """


class GeminiResponseError(Exception):
    """Gemini 有回應，但內容不能用：沒有正常結束（例如輸出被截斷）、或回傳的不是
    有效的 JSON。跟 API 連線失敗、配額用完（google.genai 的 ClientError/ServerError）
    是不同的情況。Web API 轉成 502，LINE 回覆「摘要暫時產生失敗」。
    """
