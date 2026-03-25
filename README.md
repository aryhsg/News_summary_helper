# 專案介紹

在這個資訊快速迭代的時代，短影音（Reels, TikTok, Shorts）的盛行證明了使用者對長篇資訊的耐性正急劇下降。對於資訊量龐大且生硬的經濟財經新聞，傳統的閱讀方式已成為現代人的負擔。

因此，我開發了 NSH 新聞摘要助手。透過「自動化爬蟲」即時聚合國內經濟動態，並結合「Gemini AI」進行結構化重點提煉。目標是將長篇大論轉化為精簡的條列重點，讓使用者在等公車、排隊等零碎空檔，也能透過精確的摘要，迅速掌握全球與國內的經濟脈動。

本服務同時於網頁、手機端提供服務，歡迎加入體驗！

**網站連結**：[NSH 官網](https://newssummaryhelper.aryhsg.com)

**line 官方帳號**：

<img width="180" height="180" alt="S_gainfriends_2dbarcodes_GW" src="https://github.com/user-attachments/assets/58ca3e07-39c3-4846-8f44-5b4d587dd969" />



## 技術棧 (Technology Stack)





後端核心：Python / FastAPI — 利用 Async I/O 實現高併發異步處理。



AI 引擎：Google Gemini API — 執行自然語言處理與結構化文本提煉。



資料存儲：





PostgreSQL：結構化存儲新聞與摘要數據。



Redis：實作分散式鎖，優化讀取效能。



## 維運架構：





Docker & Docker Compose：全服務容器化編排。



Nginx：作為反向代理與安全門戶。



GitHub Actions：實作 CI/CD 自動化部署流程。



Messaging Gateway: Line Messaging API





實作 Webhook 監聽機制，串接 Line 伺服器實現雙向通訊。



透過 Flex Messages 進行結構化 UI 設計，提供比純文字更佳的閱讀體驗（摘要呈現）。

## 專案架構圖
<img width="1812" height="971" alt="architecture-diagram" src="https://github.com/user-attachments/assets/8fc5ceb1-05be-488b-aaee-c2eaa2f3e004" />



1. 外部接入層 (Ingress Layer)





Cloudflare Proxy & Line Servers：作為最外層的安全防護與通訊網關。



Nginx (Reverse Proxy Container)：





唯一入口：整個 Docker 網路中唯一暴露 80/443 埠的容器。



流量分發：根據路徑路由（Routing）請求。



安全屏障：隱藏後端服務的真實 IP 與結構，對外僅展示統一的 API 介面。

2. 應用邏輯層 (Application Service Layer)





## Web API 服務：





引擎：Python FastAPI + Gunicorn (Uvicorn Workers)。



非同步架構：採用 Async I/O 驅動，確保在呼叫 Gemini API 等耗時操作時，不會阻塞其他用戶的請求。



身分驗證：在敏感端點實施 Header-based Token 驗證，防止外部非法觸發爬蟲。



## Line Bot 服務：





即時響應：處理 Line Webhook 請求，並利用 Background Tasks 處理生成時間較長的 AI 摘要，避免 Line 伺服器超時。



介面優化：利用 Line Flex Messages 提供結構化、視覺化的新聞摘要呈現。

3. 數據與快取層 (Data & Infrastructure Layer)





PostgreSQL (Persistence)：





儲存新聞元數據、摘要內容與歷史紀錄。



優化：後端使用 Connection Pooling (SQLAlchemy/Tortoise) 減少頻繁建立連線的開銷。



Redis (Caching & Locking)：





分散式鎖：確保多位用戶再生成同一新聞摘要時不會重複生成，造成 TOKEN 消耗。

4. 自動化維運層 (DevOps & Automation)





## VPS Crontab & Bash 腳本：





定時觸發 docker compose exec 執行爬蟲腳本。



外部化日誌：透過 Shell 導向 (>>) 將執行紀錄持久化至宿主機 logs/ 目錄。



## CI/CD Pipeline：





GitHub Actions：程式碼推播後自動構建映像檔並部署至遠端 VPS。



環境變數管理：敏感 Key (Gemini, Database, Line Token) 統一由 GitHub Secrets 與 VPS 系統環境變數注入。





## 未來展望與總結 (Conclusion)





拓展新聞來源：為使用者提供更多新聞，帶來更多不一樣的觀點。



功能擴展：計畫加入向量資料庫 (RAG) 實現新聞歷史語義搜索。



效能優化：預計導入 Prometheus/Grafana 進行更深層次的容器監控。
