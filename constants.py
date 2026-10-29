"""新聞類別清單的單一來源（Stage 2）。

取代原本在 line_bot/line_service.py、line_bot/msg_templates/templates.py、
gemini/gen_cate_summary.py、gemini/gen_sig_summary.py、infrastructure/db.py
各自硬編碼、彼此不一致的類別清單。

以下四份清單語意不同，刻意分開維護，不要為了「看起來應該一樣」而合併：
- ALL_CATEGORIES：全部可爬取、LINE 選單上會列出的類別。
- CATE_SUMMARY_CATEGORIES：會產生「類別彙總摘要」的類別子集，刻意只開放
  較少類別以控制 Gemini token 成本，不是漏改。
- BATCH_SUMMARY_CATEGORIES：排程批次生成單篇新聞摘要時掃描的類別子集，
  跟 CATE_SUMMARY_CATEGORIES 成員不同也是刻意的，同樣是成本考量。
- SANDBOX_CATEGORIES：/api/sandbox（不耗用 Gemini 配額的示範端點）用的
  類別子集。
"""

ALL_CATEGORIES = [
    "要聞", "國際", "證券", "期貨", "理財", "房市",
    "兩岸", "金融", "專欄", "專題", "商情", "產業",
]

CATE_SUMMARY_CATEGORIES = ["要聞", "國際", "證券", "期貨", "產業", "金融"]

BATCH_SUMMARY_CATEGORIES = ["要聞", "國際", "證券", "期貨", "理財", "兩岸", "金融", "產業"]

SANDBOX_CATEGORIES = ["要聞", "國際", "證券", "期貨", "產業", "金融", "理財"]
