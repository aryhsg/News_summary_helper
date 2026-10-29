class DatabaseError(Exception):
    """包裝底層 psycopg 例外。

    用來跟「DB 呼叫成功、但查到 0 筆」的正常空結果區分開——後者由
    repository 方法直接回傳空 list/None，不會丟這個例外。
    """
