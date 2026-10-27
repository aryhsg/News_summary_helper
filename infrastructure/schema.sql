-- News_summary_helper 資料庫 schema
-- 取代過時且不完整的 infrastructure/tables.py（該檔案少了 news 表、也少了
-- single_news_summary/cate_news_summary 實際會用到的 category 欄位）。
-- 欄位依照 infrastructure/db.py 實際執行的 SQL 語句還原，而非延用舊檔案內容。
-- 掛載到 Postgres 容器的 /docker-entrypoint-initdb.d/，容器初次啟動時自動建表。

CREATE TABLE IF NOT EXISTS news (
    news_id        VARCHAR(50) PRIMARY KEY,
    category       VARCHAR(50) NOT NULL,
    title          TEXT NOT NULL,
    content        TEXT,
    url            VARCHAR(500),
    article_image  VARCHAR(500),
    keywords       TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_news_category ON news (category);
CREATE INDEX IF NOT EXISTS idx_news_keywords ON news USING GIN (keywords);

-- 原本的 id INT PRIMARY KEY 從未被 insert_news_summary() 實際賦值，直接拿掉；
-- ON CONFLICT (news_id) DO NOTHING 需要 news_id 本身具備唯一性，故改為 PRIMARY KEY。
CREATE TABLE IF NOT EXISTS single_news_summary (
    news_id        VARCHAR(50) PRIMARY KEY REFERENCES news(news_id) ON DELETE CASCADE,
    news_summary   TEXT,
    category       VARCHAR(50) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_single_news_summary_category ON single_news_summary (category);

-- 同理拿掉無用的 id 欄位；ON CONFLICT (category) DO UPDATE 需要 category 唯一，改為 PRIMARY KEY。
-- news_summary 原本是 VARCHAR(5000)，存的是結構化 JSON 摘要，容易超出長度，改用 TEXT。
CREATE TABLE IF NOT EXISTS cate_news_summary (
    category       VARCHAR(50) PRIMARY KEY,
    news_summary   TEXT
);
