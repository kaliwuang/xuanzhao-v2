#!/bin/bash
# Restart xuanzhao server
kill $(pgrep -f "uvicorn.*main:app") 2>/dev/null
sleep 2
cd /data/data/com.termux/files/home/xuanzhao
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
sleep 4
curl -s http://localhost:8000/ | head -1
echo "Server restarted"
