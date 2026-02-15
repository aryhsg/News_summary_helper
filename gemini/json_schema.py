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

"""class InsightPoint(BaseModel):
    topic: str = Field(..., description="核心主題或趨勢名稱（如：中東局勢升溫、季報獲利預警）。")
    description: str = Field(..., description="詳細的分析邏輯，需整合具體事實與數據。")
    source_ids: List[int] = Field(..., description="對應的新聞 ID 列表。")

class CategorySummary(BaseModel):
    digest_title: str = Field(..., description="為此彙總報告取一個具有專業新聞感的標題。")
    brief_overview: str = Field(..., description="一句話總覽該類別目前的整體態勢（30-50字內）。")
    insight_points: List[InsightPoint] = Field(..., description="分類的主題洞察清單。")
    future_watch: str = Field(..., description="後續值得關注的關鍵節點、日期或潛在風險預測。")"""

class NewsInsight(BaseModel):
    """代表從新聞群組中提取的單一核心趨勢洞察"""
    topic: str = Field(..., description="核心趨勢名稱，需簡潔且具備高度資訊密度")
    analysis: str = Field(..., description="深度分析。說明趨勢背景、多篇新聞間的關聯性以及對未來的潛在影響")

class CategorySummary(BaseModel):
    """類別彙總的最終輸出結構"""
    insights: List[NewsInsight] = Field(
        ..., 
        description="趨勢洞察列表。若今日新聞皆為氣象、瑣事等雜訊且無重大分析價值，請回傳空列表 []"
    )
    is_noteworthy: bool = Field(
        ..., 
        description="布林值旗標。若有產出重大趨勢為 True；若皆為雜訊則為 False"
    )