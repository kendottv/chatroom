# 設定 Redis 執行參數（可依需求調整）
$RedisPort = 6379

# 設定 Daphne 執行參數
$DaphneHost = "127.0.0.1"
$DaphnePort = 8000
$AsgiModule = "chatroom.asgi:application"  # ✅ 替換成你的專案名稱

# 啟動 Redis（背景執行）
Write-Host "🚀 啟動 Redis Server (port: $RedisPort)..."
$RedisProcess = Start-Process -FilePath "redis-server" -ArgumentList "--port $RedisPort" -NoNewWindow -PassThru
Start-Sleep -Seconds 1

# 啟動 Daphne
Write-Host "🌐 啟動 Daphne Server (host: $DaphneHost, port: $DaphnePort)..."
daphne -b $DaphneHost -p $DaphnePort $AsgiModule

# 當 Daphne 結束後，自動關閉 Redis
Write-Host "🛑 Daphne 關閉，終止 Redis (PID: $($RedisProcess.Id))..."
Stop-Process -Id $RedisProcess.Id