#!/usr/bin/env python3
"""
玄照 v2.0 - 主入口

启动 FastAPI 服务器 + 前端静态文件服务
"""
import sys
import os

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from api.routes import router

app = FastAPI(
    title="玄照 v2.0",
    description="七术排盘 x 交叉验证 x 108视角辩论",
    version="2.0.0",
)

# API路由
app.include_router(router)

# 静态文件（前端）
frontend_dir = os.path.join(project_root, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "玄照 v2.0 API 服务运行中", "docs": "/docs"}


@app.get("/chart")
def serve_chart():
    chart_path = os.path.join(frontend_dir, "chart.html")
    if os.path.exists(chart_path):
        return FileResponse(chart_path)
    return {"error": "chart.html not found"}


@app.get("/debate")
def serve_debate():
    debate_path = os.path.join(frontend_dir, "debate.html")
    if os.path.exists(debate_path):
        return FileResponse(debate_path)
    return {"error": "debate.html not found"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
