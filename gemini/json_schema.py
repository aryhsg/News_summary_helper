from pydantic import BaseModel, Field
from typing import List

class SinglePoint(BaseModel):
    point_id: int = Field(description="摘要的編號，由1開始遞增")
    content: str = Field(description="新聞重點的具體描述內容")


class NewsSummarySchema(BaseModel):
    news_id: str = Field(description="原始新聞id (news_id)")
    title: str = Field(description="原始新聞標題")
    points: List[SinglePoint] = Field(description="新聞摘要的條列式重點，最多5點")
    
# ----------------------------------------------------------------------------------------

class SinglePoint(BaseModel):
    point: str = Field(description="單條摘要重點內容，需簡潔有力")
    source_ids: List[int] = Field(
        description="這條重點所引用的新聞 ID 列表（對應輸入 JSON 中的 ID）",
        default=[]
    )

class Cate_NewsSummarySchema(BaseModel):
    topic: str = Field(description="這組新聞的綜合主題大標題（例如：半導體產業動態）")
    summary_analysis: str = Field(description="針對這類別新聞的一句總結評論")
    points: List[SinglePoint] = Field(
        description="新聞摘要的條列式重點，最少2點，最多4點"
    )
