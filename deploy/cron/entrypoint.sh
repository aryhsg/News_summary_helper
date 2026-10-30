#!/bin/sh
# cron 執行工作時不會自動拿到 docker run/compose 設定的環境變數（DB_USERNAME、
# GEMINI_API_KEY 之類），所以容器啟動時先把目前的環境變數存一份，讓 crontab
# 裡每個工作在執行前自己 `. /etc/environment` 讀進去，是 cron-in-docker 常見
# 的做法。
printenv | grep -v "no_proxy" >> /etc/environment

exec cron -f
