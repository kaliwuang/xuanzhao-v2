"""
玄照 v2.0 全局配置
"""
import os
from pathlib import Path

# 尝试加载 .env 文件（不依赖 python-dotenv）
def _load_dotenv():
    """简单 .env 文件加载器"""
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:  # 环境变量优先
                        os.environ[key] = value
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f".env 加载异常（忽略）: {e}")

_load_dotenv()

PROJECT_ROOT = Path(__file__).parent

# LLM API (用于视角推理) — 必须通过环境变量配置，不再硬编码默认密钥
LLM_API_KEY = os.environ.get("XUANZHAO_API_KEY", "")
LLM_BASE_URL = os.environ.get("XUANZHAO_API_BASE", "https://token-plan-sgp.xiaomimimo.com/v1")
LLM_MODEL = os.environ.get("XUANZHAO_MODEL", "mimo-v2-pro")
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

# 服务配置
HOST = os.environ.get("XUANZHAO_HOST", "0.0.0.0")
PORT = int(os.environ.get("XUANZHAO_PORT", "8000"))
WORKERS = int(os.environ.get("XUANZHAO_WORKERS", "1"))


def validate_config():
    """启动时校验关键配置项，返回警告列表"""
    warnings = []
    if not LLM_API_KEY:
        warnings.append("⚠️ XUANZHAO_API_KEY 未设置，LLM相关功能（视角推理/辩论综合/溟玄审查）将不可用")
    if LLM_TIMEOUT < 10:
        warnings.append(f"⚠️ LLM_TIMEOUT={LLM_TIMEOUT}s 过短，建议 >= 30s")
    if not DATA_DIR.exists():
        warnings.append(f"⚠️ 数据目录不存在: {DATA_DIR}")
    if not TEMPLATE_DIR.exists():
        warnings.append(f"⚠️ 前端模板目录不存在: {TEMPLATE_DIR}")
    return warnings
