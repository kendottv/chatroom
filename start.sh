#!/bin/bash

# 設定 Redis 執行參數（可依需求調整）
REDIS_PORT=6379

# 設定 Daphne 執行參數
DAPHNE_HOST=127.0.0.1
DAPHNE_PORT=8000
ASGI_MODULE="chatroom.asgi:application"  # ✅ 替換成你的專案名稱

# 啟動 Redis（背景）
echo "🚀 啟動 Redis Server (port: $REDIS_PORT)..."
redis-server --port $REDIS_PORT &
REDIS_PID=$!
sleep 1

# 啟動 Daphne
echo "🌐 啟動 Daphne Server (host: $DAPHNE_HOST, port: $DAPHNE_PORT)..."
daphne -b $DAPHNE_HOST -p $DAPHNE_PORT $ASGI_MODULE

# 當 Daphne 結束後，自動關閉 Redis
echo "🛑 Daphne 關閉，終止 Redis ($REDIS_PID)..."
kill $REDIS_PID