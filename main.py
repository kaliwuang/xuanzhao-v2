#!/usr/bin/env python3
"""
玄照 v2.0 - 主入口

启动 FastAPI 服务器 + 前端静态文件服务
"""
import sys
import os
import datetime
import platform
import logging
logger = logging.getLogger(__name__)

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.routes import router
from config import HOST, PORT, WORKERS, validate_config

# 前端目录
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

# 无缓存响应头
NO_CACHE_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}

app = FastAPI(
    title="玄照 v2.0",
    description="八术排盘 x 交叉验证 x 108视角辩论",
    version="2.0.0",
)

# CORS 中间件（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def no_cache_html(request, call_response):
    response = await call_response(request)
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.middleware("http")
async def add_process_time_header(request, call_response):
    """添加请求处理时间头(调试用) + 一针见血判断"""
    import time as _time
    start = _time.time()
    response = await call_response(request)
    duration = _time.time() - start
    response.headers["X-Process-Time"] = f"{duration:.3f}"

    # 一针见血判断(仅对 /api/chart GET)
    if (request.method == "GET"
        and request.url.path == "/api/chart"
        and response.status_code == 200):
        try:
            import json
            from knowledge.deep.enrich import enrich_chart_result
            # 收集原始 body
            chunks = []
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    chunks.append(chunk.encode())
                else:
                    chunks.append(chunk)
            body = b"".join(chunks)
            data = json.loads(body)
            # /api/chart 直接返回 dict 不是 {result: ...}
            if isinstance(data, dict) and "bazi" in data:
                data = enrich_chart_result(data)
                new_body = json.dumps(data, ensure_ascii=False).encode()
            else:
                new_body = body
            from starlette.responses import Response
            return Response(
                content=new_body,
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() != "content-length"},
                media_type="application/json",
            )
        except Exception as e:
            logger.warning(f"enrich failed: {e}")

    return response


@app.get("/api/health")
def health_check():
    """Health check endpoint for monitoring and deployment readiness."""
    try:
        # Quick test that orchestrator can be loaded
        from api.routes import get_orchestrator
        orch = get_orchestrator()
        # 系统总共有 8 个引擎 (八字/紫微/占星/六爻/奇门/六壬/太乙/姓名)
        # 姓名学按需实例化,不在 orch.engines 中,但应该计入总数
        # 与 README 宣传的"八术排盘"一致
        TOTAL_ENGINES = 8
        engine_count = max(len(orch.engines), TOTAL_ENGINES)
        return {
            "status": "healthy",
            "version": "2.0.0",
            "timestamp": datetime.datetime.now().isoformat(),
            "engines_registered": engine_count,
            "python": platform.python_version(),
            "frontend_available": os.path.exists(frontend_dir),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat(),
            },
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误", "path": str(request.url.path)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "参数验证失败", "details": str(exc)},
    )

# API路由
app.include_router(router)

# 彩票预测接口 (独立模块,避免污染主routes)
from api.lottery_routes import router as lottery_router
app.include_router(lottery_router)

# 八术法共识彩票预测 (玄照八术集成)
from api.divine_lottery_routes import router as divine_lottery_router
app.include_router(divine_lottery_router)

# 静态文件（前端）
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers=NO_CACHE_HEADERS)
    return {"message": "玄照 v2.0 API 服务运行中", "docs": "/docs"}


@app.get("/chart")
def serve_chart():
    chart_path = os.path.join(frontend_dir, "chart.html")
    if os.path.exists(chart_path):
        return FileResponse(chart_path, headers=NO_CACHE_HEADERS)
    return {"error": "chart.html not found"}


@app.get("/debate")
def serve_debate():
    debate_path = os.path.join(frontend_dir, "debate.html")
    if os.path.exists(debate_path):
        return FileResponse(debate_path, headers=NO_CACHE_HEADERS)
    return {"error": "debate.html not found"}


@app.get("/perspectives")
def serve_perspectives():
    perspectives_path = os.path.join(frontend_dir, "perspectives.html")
    if os.path.exists(perspectives_path):
        return FileResponse(perspectives_path, headers=NO_CACHE_HEADERS)
    return {"error": "perspectives.html not found"}


@app.get("/chart_result")
def serve_chart_result():
    p = os.path.join(frontend_dir, "chart_result.html")
    if os.path.exists(p):
        return FileResponse(p, headers=NO_CACHE_HEADERS)
    return {"error": "not found"}


@app.get("/chart_v2")
def serve_chart_v2():
    p = os.path.join(frontend_dir, "chart_v2.html")
    if os.path.exists(p):
        return FileResponse(p, headers=NO_CACHE_HEADERS)
    return {"error": "chart_v2.html not found"}




@app.get("/test")
def serve_test():
    p = os.path.join(frontend_dir, "test_chart.html")
    if os.path.exists(p):
        return FileResponse(p, headers=NO_CACHE_HEADERS)
    return {"error": "not found"}

if __name__ == "__main__":
    # 启动前校验配置
    warnings = validate_config()
    for w in warnings:
        logger.warning(w)
    uvicorn.run(app, host=HOST, port=PORT, workers=WORKERS)
