"""
玄照 v2.0 全局配置
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# Claude API (用于视角推理)
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")

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
