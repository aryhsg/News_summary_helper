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
