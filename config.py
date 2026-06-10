"""
玄照 v2.0 全局配置
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# LLM API (用于视角推理)
LLM_API_KEY = os.environ.get("XUANZHAO_API_KEY", "tzzEsWy9cPc7cONb11z296epNJIzfUcxDivW6hMWzOaIkAWk")
LLM_BASE_URL = os.environ.get("XUANZHAO_API_BASE", "https://agent.uumit.com/v1")
LLM_MODEL = os.environ.get("XUANZHAO_MODEL", "Doubao-Seed-2.0-Pro")
LLM_TIMEOUT = int(os.environ.get("XUANZHAO_TIMEOUT", "120"))

# 前端模板路径
TEMPLATE_DIR = PROJECT_ROOT / "frontend"

# 数据文件路径
DATA_DIR = PROJECT_ROOT / "data"
CITIES_DB = DATA_DIR / "cities.json"

# 知识库路径
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"

# 视角定义路径
PERSPECTIVES_DIR = PROJECT_ROOT / "perspectives"

# 调试模式
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
