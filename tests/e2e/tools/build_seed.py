"""把 tests/e2e/data/sample_news.json 轉成 PostgreSQL 初始化用的 seed.sql。

seed.sql 會被掛載到測試資料庫容器的 /docker-entrypoint-initdb.d/，接在
infrastructure/schema.sql（01）之後執行（02）。資料有變動時重新執行本腳本：

    python tests/e2e/tools/build_seed.py

字串一律用 dollar-quoting（$q$...$q$）包起來，這樣標題裡的單引號、HTML 特殊
字元（構造的 XSS 測試資料）都不需要逐一跳脫。
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SRC = DATA_DIR / "sample_news.json"
OUT = DATA_DIR / "seed.sql"


def q(value: str) -> str:
    assert "$q$" not in value, f"資料含有 dollar-quote 分隔字串：{value[:30]}"
    return f"$q${value}$q$"


def text_array(items) -> str:
    if not items:
        return "ARRAY[]::text[]"
    return "ARRAY[" + ", ".join(q(i) for i in items) + "]::text[]"


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    lines = [
        "-- 由 tests/e2e/tools/build_seed.py 從 sample_news.json 產生，請勿手動修改。",
        "",
    ]

    for n in data["news"]:
        lines.append(
            "INSERT INTO news (news_id, category, title, content, url, article_image, keywords) VALUES ("
            f"{q(n['news_id'])}, {q(n['category'])}, {q(n['title'])}, {q(n['content'])}, "
            f"{q(n['url'])}, {q(n['article_image'])}, {text_array(n['keywords'])});"
        )
    lines.append("")

    for s in data["single_news_summary"]:
        lines.append(
            "INSERT INTO single_news_summary (news_id, news_summary, category) VALUES ("
            f"{q(s['news_id'])}, {q(s['news_summary'])}, {q(s['category'])});"
        )
    lines.append("")

    for c in data["cate_news_summary"]:
        lines.append(
            "INSERT INTO cate_news_summary (category, news_summary) VALUES ("
            f"{q(c['category'])}, {q(c['news_summary'])});"
        )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"寫入 {OUT}：{len(data['news'])} 篇新聞、"
          f"{len(data['single_news_summary'])} 筆摘要、{len(data['cate_news_summary'])} 筆類別摘要")


if __name__ == "__main__":
    main()
