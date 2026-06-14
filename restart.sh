#!/bin/bash
# Kill existing server
for pid in $(pgrep -f "uvicorn main:app"); do
    kill $pid 2>/dev/null
done
sleep 2

# Start new server
cd /data/data/com.termux/files/home/xuanzhao
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/xuanzhao.log 2>&1 &
echo "Server started with PID $!"
sleep 3

# Verify
curl -s localhost:8000/api/health
