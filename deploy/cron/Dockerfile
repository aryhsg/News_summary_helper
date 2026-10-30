# 跟 Dockerfile（web/line 用的主 image）內容幾乎一樣，多裝一個 cron，
# 並把 deploy/cron/crontab 裝進去當排程定義。context 仍然是專案根目錄
# （docker-compose.yml 裡用 context: . + dockerfile: deploy/cron/Dockerfile），
# 這樣才能 COPY 到完整的程式碼跟 requirements.txt。
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

COPY deploy/cron/crontab /etc/cron.d/nsh-cron
RUN chmod 0644 /etc/cron.d/nsh-cron \
    && crontab /etc/cron.d/nsh-cron \
    && touch /var/log/cron.log

COPY deploy/cron/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
