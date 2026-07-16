# ============================================================================
# API 路由 B76-B85 Bug 审计标记
# ============================================================================
# B76 修复: ✅ 部分修 - 城市编码问题 (GBK/UTF-8)
# B77 修复: 参数验证 - 严格类型检查
# B78 修复: 超时处理 - 单引擎超时不应阻塞整请求
# B79 修复: 错误信息 - 不泄露内部细节
# B80 修复: 缓存 - 相同请求返回缓存
# B81 修复: 并发 - 多用户同时访问
# B82 修复: 数据校验 - 输入清洗
# B83 修复: 日志 - 调试和审计日志
# B84 修复: 跨域 CORS
# B85 修复: 输入清理 - 防 XSS/SQL 注入
# ============================================================================

#!/usr/bin/env python3
"""
玄照 v2.0 - FastAPI 路由
"""
import logging
import re
import os
import traceback
import time
import calendar
import urllib.request
import urllib.parse
import hashlib
import copy
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
import json as _json
import io

logger = logging.getLogger("xuanzhao.api")

# 简单内存缓存（带LRU淘汰）
_cache = {}
_cache_ttl = 300  # 5分钟过期
_cache_max_size = 200  # 最大缓存条目数

def _get_cache(key: str):
    """获取缓存"""
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < _cache_ttl:
            return data
        del _cache[key]
    return None

def _set_cache(key: str, data):
    """设置缓存，带LRU淘汰"""
    # 先清理过期缓存
    if len(_cache) >= _cache_max_size:
        now = time.time()
        expired = [k for k, (_, ts) in _cache.items() if now - ts > _cache_ttl]
        for k in expired:
            del _cache[k]
        # 如果仍然超过限制，删除最旧的条目直到有空间
        while len(_cache) >= _cache_max_size:
            oldest_key = min(_cache, key=lambda k: _cache[k][1])
            del _cache[oldest_key]
    _cache[key] = (data, time.time())


# ──────────────────────────────────────────────────────────────────
# /api/report 专用缓存层 (2026-07-10 梧指令)
# key = md5(birth|location|gender|name|question)
# TTL = 600s, LRU 上限 100
# 返回值一律深拷贝,防止下游修改污染缓存
# ──────────────────────────────────────────────────────────────────
_report_cache = {}          # key -> (ts, report)
_report_cache_stats = {     # 全局命中统计(给 /api/cache/stats 看)
    "hits": 0,
    "misses": 0,
    "evictions": 0,
    "expirations": 0,
}
_REPORT_CACHE_TTL = 600     # 10 分钟
_REPORT_CACHE_MAX = 100     # 100 条

def _report_cache_key(birth: str, location: str, gender: str, name: str, question: str) -> str:
    """生成缓存 key"""
    raw = f"{birth}|{location}|{gender}|{name}|{question}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def _get_cached_report(birth, location, gender, name, question):
    """从缓存拿 report(命中返回深拷贝,未命中返 None)"""
    key = _report_cache_key(birth, location, gender, name, question)
    entry = _report_cache.get(key)
    if entry is None:
        _report_cache_stats["misses"] += 1
        return None
    ts, report = entry
    if time.time() - ts > _REPORT_CACHE_TTL:
        # 过期
        _report_cache.pop(key, None)
        _report_cache_stats["expirations"] += 1
        _report_cache_stats["misses"] += 1
        return None
    _report_cache_stats["hits"] += 1
    # 深拷贝 — chart_result 里 nested dict 多,datetime/对象会被同一引用串改
    return copy.deepcopy(report)

def _set_cached_report(birth, location, gender, name, question, report):
    """写入缓存,LRU 淘汰(超 100 条时删最旧)"""
    key = _report_cache_key(birth, location, gender, name, question)
    # 先清过期,给 LRU 淘汰减压
    now = time.time()
    expired_keys = [k for k, (ts, _) in _report_cache.items() if now - ts > _REPORT_CACHE_TTL]
    for k in expired_keys:
        _report_cache.pop(k, None)
        _report_cache_stats["expirations"] += 1
    # LRU 淘汰
    while len(_report_cache) >= _REPORT_CACHE_MAX:
        oldest_key = min(_report_cache, key=lambda k: _report_cache[k][0])
        _report_cache.pop(oldest_key, None)
        _report_cache_stats["evictions"] += 1
    # 写入时也深拷贝(防止上游之后修改 report 串改缓存)
    _report_cache[key] = (now, copy.deepcopy(report))

def _clear_report_cache():
    """清空 /api/report 缓存(主要用于调试)"""
    _report_cache.clear()
    _report_cache_stats["hits"] = 0
    _report_cache_stats["misses"] = 0
    _report_cache_stats["evictions"] = 0
    _report_cache_stats["expirations"] = 0

from engine.time_engine import get_time_engine
from engine.base import EngineOrchestrator
from engine.bazi_engine import BaziEngine, GAN_WUXING_STR, WUXING_SHENG, WUXING_KE
from engine.astro_engine import AstroEngine
from engine.ziwei_engine import ZiWeiEngine
from engine.liuyao_engine import LiuYaoEngine
from engine.qimen_engine import QiMenEngine
from engine.liuren_engine import LiuRenEngine
from engine.taiyi_engine import TaiYiEngine
from engine.cross_validator import CrossValidator
from engine.perspective_engine import PerspectiveEngine
from engine.debate_engine import DebateEngine
from engine.qa_engine import QAEngine
from engine.xingming_engine import XingMingEngine, COMPOUND_SURNAMES

router = APIRouter()

# 初始化引擎调度器
_orchestrator = None
_xingming_engine = None  # 姓名学引擎单例
_default_figure_ids = [
    "zhuge-liang", "ni-haixia", "yuan-tiangang", "li-chunfeng", "gui-gu-zi",
    "jiang-ziya", "shao-yong", "feynman", "jung", "zhang-zhongjing",
    "laozi", "sunzi", "chen-tuan", "xu-ziping", "jing-fang",
    "chen-gongxian", "huang-shigong", "zhang-liang", "kongzi", "zhuangzi",
    "ptolemy", "nietzsche", "mozi", "hanfeizi", "wang-tingzhi",
    "wan-minying", "bian-que", "guan-lu", "guo-pu", "li-xuzhong",
    "liu-bowen", "ren-tieyao", "shen-xiaozhan", "yu-chuntai", "zhang-shenfeng",
    "lu-dongbin", "qiu-chuji", "zhang-sanfeng", "feng-hou", "yang-junsong",
    "lai-buyi", "liao-junqing", "yehe-laoren", "wang-hongxu", "miao-gongda",
    "xu-cibin", "dongfang-shuo", "lu-xixing", "liu-yiming", "lu-binzhao",
    "liaowu-jushi", "cai-shangji", "jiang-dahong", "zhao-jiufeng", "zhang-jiuyi",
    "wang-junrong", "zhang-xingyuan", "li-wenhui", "cao-jiuxi", "ling-fuzhi",
    "zhang-guande", "guo-yuqing", "yan-junping", "william-lilly", "alan-leo",
    "linda-goodman", "stephen-forrest", "fayun-jushi", "tianyi-shangren", "wu-zhongcheng",
    "chen-shixing", "zhang-guolao", "cheng-liangyu", "zhang-erqi", "hu-xu",
    "jiao-yanshou", "wang-mufu", "cheng-shuxun", "liu-chijiang", "wei-qianli",
    "zhang-qihuang", "yuan-shushan", "dane-rudhyar", "howard-sasportas", "liz-greene",
    "robert-hand", "xuanzhao", "munger", "taleb", "naval",
    "stoic", "nostradamus", "geng-shouchang", "zhang-heng", "yixing",
    "wang-ximing", "socrates", "einstein", "sagan", "nan-huaijin",
    "sigmund-freud", "maslow", "kahneman", "i-ching", "dante",
    "rabelais", "hegel", "paracelsus",
]

def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = EngineOrchestrator()
        _orchestrator.register(BaziEngine())
        _orchestrator.register(AstroEngine())
        _orchestrator.register(ZiWeiEngine())
        _orchestrator.register(LiuYaoEngine())
        _orchestrator.register(QiMenEngine())
        _orchestrator.register(LiuRenEngine())
        _orchestrator.register(TaiYiEngine())
    return _orchestrator


def _parse_gender(gender: str) -> int:
    """性别字符串→编码"""
    if not gender:
        return 0  # 默认女
    return 1 if gender.lower() in ("男", "male", "m") else 0


def _validate_birth(birth: str) -> str:
    """验证出生时间格式，返回标准化后的时间字符串"""
    if not birth or not birth.strip():
        raise ValueError("出生时间不能为空")
    # 统一处理：下划线、+号作为空格
    birth = birth.strip().replace('_', ' ').replace('+', ' ')
    # 支持格式：2005-06-09 11:50 或 2005/06/09 11:50
    patterns = [
        r'^\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}:\d{2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}$',
        r'^\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}:\d{2}$',
        r'^\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}$',
        r'^\d{4}/\d{1,2}/\d{1,2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{2}:\d{2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}T\d{1,2}$',
        r'^\d{8}\s+\d{6}$',      # YYYYMMDD HHMMSS
        r'^\d{8}\s+\d{4}$',      # YYYYMMDD HHMM
        r'^\d{8}$',               # YYYYMMDD
    ]
    if not any(re.match(p, birth.strip()) for p in patterns):
        raise ValueError(f"时间格式错误: {birth}，应为 YYYY-MM-DD HH:MM")
    # 检查范围（统一用正则提取年月日时分，兼容ISO格式T分隔符、紧凑YYYYMMDD和仅小时格式）
    clean = re.sub(r'T', ' ', birth.strip())
    # 紧凑格式 YYYYMMDD / YYYYMMDD HHMM / YYYYMMDD HHMMSS 先拆解为标准格式
    if re.match(r'^\d{8}', clean):
        digits = clean.replace(' ', '')
        year = int(digits[0:4])
        month = int(digits[4:6])
        day = int(digits[6:8])
        hour = int(digits[8:10]) if len(digits) >= 10 else 0
        minute = int(digits[10:12]) if len(digits) >= 12 else 0
        second = int(digits[12:14]) if len(digits) >= 14 else 0
        hour_min = [str(hour), str(minute)] + ([str(second)] if len(digits) >= 14 else [])
    else:
        parts = re.split(r'[-/ ]+', clean)
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        if len(parts) >= 4:
            hour_min = parts[3].split(':')
            hour = int(hour_min[0])
        else:
            hour_min = []
            hour = 0
    if not (1900 <= year <= 2100):
        raise ValueError(f"年份超出范围: {year}")
    if not (1 <= month <= 12):
        raise ValueError(f"月份错误: {month}")
    # 月份天数校验（考虑闰年）
    max_day = calendar.monthrange(year, month)[1]
    if not (1 <= day <= max_day):
        raise ValueError(f"日期错误: {year}年{month}月只有{max_day}天，输入{day}天")
    if not (0 <= hour <= 23):
        raise ValueError(f"小时错误: {hour}")
    minute = int(hour_min[1]) if len(hour_min) > 1 else 0
    if not (0 <= minute <= 59):
        raise ValueError(f"分钟错误: {minute}")
    if len(hour_min) > 2:
        second = int(hour_min[2])
        if not (0 <= second <= 59):
            raise ValueError(f"秒数错误: {second}")
    return birth


def _sanitize_name(name: str) -> str:
    """清理姓名参数，防止注入"""
    if not name:
        return ""
    # 只保留中文字符、字母、数字、常见分隔符
    sanitized = re.sub(r'[^\u4e00-\u9fff\w\s·-]', '', name.strip())
    return sanitized[:20]  # 限制长度

def _prepare_udm(birth: str, location: str, gender: str):
    """公共前置：时间校正 + 排盘，返回 (corrected, udm)"""
    birth = _validate_birth(birth)
    time_engine = get_time_engine()
    corrected = time_engine.correct(birth, location)
    gender_code = _parse_gender(gender)
    orch = get_orchestrator()
    udm = orch.run_all(corrected, gender_code)
    return corrected, udm


def _error_response(e: Exception):
    """统一错误响应（生产环境隐藏详细堆栈）"""
    logger.exception("API error")
    import os
    is_dev = os.environ.get("XUANZHAO_ENV", "prod") == "dev"
    # 区分客户端错误和服务器错误
    if isinstance(e, ValueError):
        status_code = 400
    else:
        status_code = 500
    content = {
        "error": f"操作失败: {str(e)}",
        "error_type": type(e).__name__,
        "error_code": "VALIDATION_ERROR" if isinstance(e, ValueError) else "INTERNAL_ERROR",
    }
    if is_dev:
        content["traceback"] = traceback.format_exc()[-500:]
    return JSONResponse(status_code=status_code, content=content)


def _get_figure_ids(figures: Optional[str]) -> list:
    """解析人物ID参数"""
    return [f.strip() for f in figures.split(",") if f.strip()] if figures and figures.strip() else _default_figure_ids


# ──────────────────────────────────────────────────────────────────
# 八字高级解读辅助函数（改进 #219-#230）
# ──────────────────────────────────────────────────────────────────

def _analyze_geju(udm) -> dict:
    """格局判定"""
    result = {
        "geju_type": "未知",
        "geju_level": "普通",
        "qingchun": False,
        "qingzhuo": False,
        "description": "",
    }
    if not udm.bazi_year or not udm.bazi_day:
        return result
    month_zhi = udm.bazi_month.zhi if udm.bazi_month else ""
    month_gan = udm.bazi_month.gan if udm.bazi_month else ""
    day_gan = udm.bazi_day.gan or ""
    shishen_gan = udm.shishen_gan or {}
    month_shishen = shishen_gan.get("month", "")

    # 格局大类
    if month_shishen in ("正官", "七杀"):
        result["geju_type"] = "官格"
    elif month_shishen in ("正印", "偏印"):
        result["geju_type"] = "印格"
    elif month_shishen in ("食神", "伤官"):
        result["geju_type"] = "食伤格"
    elif month_shishen in ("正财", "偏财"):
        result["geju_type"] = "财格"
    elif month_shishen in ("比肩", "劫财"):
        result["geju_type"] = "比劫格"
    else:
        result["geju_type"] = "杂格"

    # 清纯度判定
    all_ss = set()
    for v in shishen_gan.values():
        if v and v != "?":
            all_ss.add(v)
    for v_list in (udm.shishen_zhi or {}).values():
        if isinstance(v_list, list):
            for v in v_list:
                if v and v != "?":
                    all_ss.add(v)

    if "伤官" in all_ss and "正官" in all_ss:
        result["qingzhuo"] = True
        result["description"] = "伤官见官，格局混杂，需印星化解"
    elif len(all_ss) <= 3:
        result["qingchun"] = True
        result["description"] = f"十神精简（{len(all_ss)}种），格局清纯，力量集中"
    else:
        result["description"] = f"十神{len(all_ss)}种，格局多样，可塑性强"

    # 格局等级
    if result["qingchun"] and result["geju_type"] in ("官格", "印格", "食伤格"):
        result["geju_level"] = "上等"
    elif result["qingzhuo"]:
        result["geju_level"] = "次等"
    else:
        result["geju_level"] = "中等"

    return result


def _summarize_dayun(udm) -> dict:
    """大运总结"""
    dayun = getattr(udm, "dayun", []) or []
    if not dayun:
        return {"total": 0, "best_age": 0, "worst_age": 0, "current": ""}

    good_cs = {"长生", "冠带", "临官", "帝旺"}
    bad_cs = {"死", "墓", "绝"}
    best_score, worst_score = -99, 99
    best_age, worst_age = 0, 0
    current_dy = ""

    for d in dayun:
        cs = d.get("changsheng", "")
        age = d.get("age", 0)
        gz = d.get("ganzhi", "")
        if cs in good_cs:
            if best_score < 1:
                best_score = 1
                best_age = age
        elif cs in bad_cs:
            if worst_score > -1:
                worst_score = -1
                worst_age = age
        if 18 <= age <= 35:
            current_dy = gz

    return {
        "total": len(dayun),
        "best_age": best_age,
        "best_ganzhi": next((d["ganzhi"] for d in dayun if d.get("age") == best_age), ""),
        "worst_age": worst_age,
        "worst_ganzhi": next((d["ganzhi"] for d in dayun if d.get("age") == worst_age), ""),
        "current": current_dy,
    }


def _group_shensha(udm) -> dict:
    """神煞分组"""
    shensha = getattr(udm, "shensha", []) or []
    groups = {
        "吉神": [],
        "凶煞": [],
        "中性": [],
    }
    auspicious = {"天乙贵人", "太极贵人", "文昌贵人", "天德贵人", "月德贵人",
                  "福星贵人", "德秀贵人", "国印贵人", "金舆", "天喜", "红鸾"}
    inauspicious = {"七杀", "羊刃", "劫煞", "灾煞", "勾绞煞", "血刃", "飞刃",
                    "披麻", "吊客", "天狗", "白虎", "天刑"}
    for s in shensha:
        if isinstance(s, str):
            if s in auspicious:
                groups["吉神"].append(s)
            elif s in inauspicious:
                groups["凶煞"].append(s)
            else:
                groups["中性"].append(s)
    return groups


def _build_kongwang_table(udm) -> dict:
    """旬空查表"""
    xunkong = getattr(udm, "xunkong", {}) or {}
    return {
        "year": xunkong.get("year", ""),
        "month": xunkong.get("month", ""),
        "day": xunkong.get("day", ""),
        "time": xunkong.get("time", ""),
        "note": "空亡=地支虚位，逢流年填实则应事"
    }


def _true_solar_diff(udm) -> dict:
    """真太阳时差"""
    return {
        "has_data": hasattr(udm, "true_solar"),
        "diff_minutes": round((udm.true_solar - udm.original).total_seconds() / 60, 1) if hasattr(udm, "true_solar") and hasattr(udm, "original") else 0,
    }


def _build_taiji_table(udm) -> list:
    """太极贵人查表"""
    if not udm.bazi_day:
        return []
    from engine.bazi_engine import SHENSHA_TAIJI_MAP
    day_gan = udm.bazi_day.gan
    year_gan = udm.bazi_year.gan if udm.bazi_year else ""
    targets = set(SHENSHA_TAIJI_MAP.get(day_gan, []))
    targets.update(SHENSHA_TAIJI_MAP.get(year_gan, []))
    return [{"source": "日干" if day_gan == day_gan else "年干", "gan": day_gan, "zhi": list(targets)}]


def _build_wenchang_table(udm) -> list:
    """文昌贵人查表"""
    if not udm.bazi_day:
        return []
    from engine.bazi_engine import SHENSHA_WENCHANG_MAP
    return [{"day_gan": udm.bazi_day.gan, "zhi": SHENSHA_WENCHANG_MAP.get(udm.bazi_day.gan, "")}]


def _build_taohua_table(udm) -> list:
    """桃花表"""
    if not udm.bazi_year or not udm.bazi_day:
        return []
    from engine.bazi_engine import SHENSHA_TAOHUA_MAP
    yz = udm.bazi_year.zhi
    dz = udm.bazi_day.zhi
    return [
        {"source": "年支", "zhi": yz, "taohua": SHENSHA_TAOHUA_MAP.get(yz, "")},
        {"source": "日支", "zhi": dz, "taohua": SHENSHA_TAOHUA_MAP.get(dz, "")},
    ]


def _build_yima_table(udm) -> list:
    """驿马表"""
    if not udm.bazi_year or not udm.bazi_day:
        return []
    from engine.bazi_engine import SHENSHA_YIMA_MAP
    yz = udm.bazi_year.zhi
    dz = udm.bazi_day.zhi
    return [
        {"source": "年支", "zhi": yz, "yima": SHENSHA_YIMA_MAP.get(yz, "")},
        {"source": "日支", "zhi": dz, "yima": SHENSHA_YIMA_MAP.get(dz, "")},
    ]


def _build_huagai_table(udm) -> list:
    """华盖表"""
    if not udm.bazi_year or not udm.bazi_day:
        return []
    from engine.bazi_engine import SHENSHA_HUAGAI_MAP
    yz = udm.bazi_year.zhi
    dz = udm.bazi_day.zhi
    return [
        {"source": "年支", "zhi": yz, "huagai": SHENSHA_HUAGAI_MAP.get(yz, "")},
        {"source": "日支", "zhi": dz, "huagai": SHENSHA_HUAGAI_MAP.get(dz, "")},
    ]


def _build_tianyi_table(udm) -> list:
    """天乙贵人表"""
    if not udm.bazi_day:
        return []
    from engine.bazi_engine import SHENSHA_TIANYI_MAP
    day_gan = udm.bazi_day.gan
    targets = SHENSHA_TIANYI_MAP.get(day_gan, [])
    return [{"day_gan": day_gan, "target_zhis": targets}]


def _summarize_shensha(udm) -> dict:
    """神煞汇总"""
    shensha = getattr(udm, "shensha", []) or []
    return {
        "total": len(shensha),
        "auspicious_count": sum(1 for s in shensha if isinstance(s, str) and s in {"天乙贵人", "太极贵人", "文昌贵人", "天德贵人", "月德贵人"}),
        "inauspicious_count": sum(1 for s in shensha if isinstance(s, str) and s in {"七杀", "羊刃", "劫煞", "灾煞"}),
        "all": shensha,
    }


# ──────────────────────────────────────────────────────────────────
# 合婚辅助函数（改进 #231-#240）
# ──────────────────────────────────────────────────────────────────

def _check_sanhe(z1: str, z2: str) -> str:
    """检查三合局"""
    sanhe_groups = [
        ("申", "子", "辰"),  # 水局
        ("亥", "卯", "未"),  # 木局
        ("寅", "午", "戌"),  # 火局
        ("巳", "酉", "丑"),  # 金局
    ]
    for group in sanhe_groups:
        if z1 in group and z2 in group:
            if z1 == z2:
                continue
            elements = {"申子辰": "水", "亥卯未": "木", "寅午戌": "火", "巳酉丑": "金"}
            for key, el in elements.items():
                if z1 in key and z2 in key:
                    return f"{z1}{z2}半会{el}局"
    return ""


def _check_xing(z1: str, z2: str) -> str:
    """检查相刑"""
    xing_pairs = {
        ("寅", "巳"): "寅巳刑（恃势）",
        ("巳", "申"): "巳申刑（无恩）",
        ("申", "寅"): "申寅刑（恃势）",
        ("丑", "戌"): "丑戌刑（恃势）",
        ("戌", "未"): "戌未刑（恃势）",
        ("未", "丑"): "未丑刑（恃势）",
        ("子", "卯"): "子卯刑（无礼）",
        ("卯", "子"): "卯子刑（无礼）",
        ("辰", "辰"): "辰辰自刑",
        ("午", "午"): "午午自刑",
        ("酉", "酉"): "酉酉自刑",
        ("亥", "亥"): "亥亥自刑",
    }
    return xing_pairs.get((z1, z2), "")


def _calc_wx_complement(wx1: str, wx2: str) -> int:
    """五行互补度 0-100"""
    if not wx1 or not wx2:
        return 50
    if wx1 == wx2:
        return 60  # 比和
    from engine.udm import WUXING_SHENG, WUXING_KE
    if WUXING_SHENG.get(wx1) == wx2 or WUXING_SHENG.get(wx2) == wx1:
        return 90  # 相生
    if WUXING_KE.get(wx1) == wx2 or WUXING_KE.get(wx2) == wx1:
        return 30  # 相克
    return 50


def _zhi_full_relation(z1: str, z2: str) -> str:
    """地支完整关系"""
    if not z1 or not z2:
        return ""
    if z1 == z2:
        return f"{z1}{z2}比和"
    from engine.udm import ZHI_LIUHE, ZHI_CHONG
    if ZHI_LIUHE.get(z1) == z2:
        return f"{z1}{z2}六合"
    if ZHI_CHONG.get(z1) == z2:
        return f"{z1}{z2}六冲"
    return f"{z1}{z2}无特殊关系"


def _calc_marriage_index(dg_score, rz_score, comp_score, sanhe, liuhe, liuchong, xing, common_ss) -> int:
    """婚配指数综合 0-100"""
    base = (dg_score + rz_score + comp_score) / 3
    bonus = 0
    if sanhe:
        bonus += 8
    if liuhe:
        bonus += 5
    if liuchong:
        bonus -= 10
    if xing:
        bonus -= 8
    bonus += min(10, len(common_ss) * 2)
    return max(0, min(100, int(base * 0.7 + bonus + 10)))


# ──────────────────────────────────────────────────────────────────
# /api/hehun 强化版 (2026-07-10 梧指令)
# 5 维度: wuxing_bu / bazi_complement / dayun_sync / shensha_conflict / ziwei_match
# 加权: 五行 30 / 八字 25 / 大运 20 / 神煞 15 / 紫微 10
# 目标: 钢铁侠装甲 — 单人 report 是青铜,合婚要给出真实可判断的关系评估
# 不许调 LLM,纯规则引擎;不许重写 engine
# ──────────────────────────────────────────────────────────────────

_HEHUN_CACHE = {}  # key -> (ts, response_dict)
_HEHUN_CACHE_TTL = 600  # 10 分钟
_HEHUN_CACHE_MAX = 50


def _hehun_cache_key(b1, l1, g1, n1, b2, l2, g2, n2) -> str:
    raw = f"{b1}|{l1}|{g1}|{n1}||{b2}|{l2}|{g2}|{n2}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _get_hehun_cache(key: str):
    entry = _HEHUN_CACHE.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > _HEHUN_CACHE_TTL:
        _HEHUN_CACHE.pop(key, None)
        return None
    return copy.deepcopy(data)


def _set_hehun_cache(key: str, data):
    now = time.time()
    expired = [k for k, (ts, _) in _HEHUN_CACHE.items() if now - ts > _HEHUN_CACHE_TTL]
    for k in expired:
        _HEHUN_CACHE.pop(k, None)
    while len(_HEHUN_CACHE) >= _HEHUN_CACHE_MAX:
        oldest = min(_HEHUN_CACHE, key=lambda k: _HEHUN_CACHE[k][0])
        _HEHUN_CACHE.pop(oldest, None)
    _HEHUN_CACHE[key] = (now, copy.deepcopy(data))


def _shensha_keyword(s) -> str:
    """'劫煞（日支子）' -> '劫煞'"""
    if not isinstance(s, str):
        return ""
    for sep in ("（", "("):
        if sep in s:
            return s.split(sep)[0].strip()
    return s.strip()


def _safe_str_list(value) -> list:
    """归一为 list[str]"""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)]


def _wx_overlap(a_list, b_list) -> int:
    """五行元素重叠数"""
    return len(set(a_list) & set(b_list))


def _check_wuxing_complement(b1: dict, b2: dict) -> dict:
    """五行互补维度"""
    xi1 = _safe_str_list(b1.get("xi_yong", {}).get("xi"))
    ji1 = _safe_str_list(b1.get("xi_yong", {}).get("ji"))
    xi2 = _safe_str_list(b2.get("xi_yong", {}).get("xi"))
    ji2 = _safe_str_list(b2.get("xi_yong", {}).get("ji"))

    ws1 = b1.get("wuxing_score", {}) or {}
    ws2 = b2.get("wuxing_score", {}) or {}

    evidence = []
    score = 50
    match = True

    hit_i_need = _wx_overlap(xi1, xi2) + _wx_overlap(xi1, [k for k, v in ws2.items() if v and v > 0])
    hit_u_need = _wx_overlap(xi2, xi1) + _wx_overlap(xi2, [k for k, v in ws1.items() if v and v > 0])
    avoid_i_j = _wx_overlap(ji1, xi2) + _wx_overlap(ji1, [k for k, v in ws2.items() if v and v > 0])
    avoid_u_j = _wx_overlap(ji2, xi1) + _wx_overlap(ji2, [k for k, v in ws1.items() if v and v > 0])

    if hit_i_need > 0:
        bonus = min(20, hit_i_need * 8)
        score += bonus
        evidence.append(
            f"甲方喜用为{'+'.join(xi1) or '—'},乙方命中 {hit_i_need} 项(+{bonus})"
        )
    if hit_u_need > 0:
        bonus = min(20, hit_u_need * 8)
        score += bonus
        evidence.append(
            f"乙方喜用为{'+'.join(xi2) or '—'},甲方命中 {hit_u_need} 项(+{bonus})"
        )
    if avoid_i_j > 0:
        penalty = min(25, avoid_i_j * 8)
        score -= penalty
        match = False
        evidence.append(
            f"甲方忌{'+'.join(ji1) or '—'},乙方多该项(-{penalty})"
        )
    if avoid_u_j > 0:
        penalty = min(25, avoid_u_j * 8)
        score -= penalty
        match = False
        evidence.append(
            f"乙方忌{'+'.join(ji2) or '—'},甲方多该项(-{penalty})"
        )

    if not evidence:
        evidence.append("双方五行喜忌无显著交叉,中性互补")

    return {
        "score": max(0, min(100, int(score))),
        "evidence": evidence,
        "match": match,
    }


def _check_bazi_complement(b1: dict, b2: dict) -> dict:
    """八字互补维度"""
    from engine.udm import (
        ZHI_LIUHE as _HE_LIUHE,
        ZHI_CHONG as _HE_CHONG,
        ZHI_SANHE as _HE_SANHE,
        ZHI_SANHUI as _HE_SANHUI,
    )

    evidence = []
    score = 50

    d1 = b1.get("day", "")
    d2 = b2.get("day", "")
    if not d1 or not d2:
        return {"score": 50, "evidence": ["日柱缺失,无法判断"]}

    gan1 = d1[0]
    zhi1 = d1[1] if len(d1) > 1 else ""
    gan2 = d2[0]
    zhi2 = d2[1] if len(d2) > 1 else ""

    gan_he = {("甲", "己"), ("己", "甲"), ("乙", "庚"), ("庚", "乙"),
              ("丙", "辛"), ("辛", "丙"), ("丁", "壬"), ("壬", "丁"),
              ("戊", "癸"), ("癸", "戊")}
    if (gan1, gan2) in gan_he:
        score += 25
        evidence.append(f"日干天合:{gan1}{gan2} 相合,阴阳吸引(+25)")
    else:
        wx1 = GAN_WUXING_STR.get(gan1, "")
        wx2 = GAN_WUXING_STR.get(gan2, "")
        if wx1 and wx2:
            if wx1 == wx2:
                score += 5
                evidence.append(f"日干同为{wx1},比和同行(+5)")
            elif WUXING_SHENG.get(wx1) == wx2:
                score += 15
                evidence.append(f"日干{wx1}生{wx2},乐意付出(+15)")
            elif WUXING_SHENG.get(wx2) == wx1:
                score += 15
                evidence.append(f"日干{wx2}生{wx1},得到滋养(+15)")
            elif WUXING_KE.get(wx1) == wx2:
                score -= 20
                evidence.append(f"日干{wx1}克{wx2},强势压迫(-20)")
            elif WUXING_KE.get(wx2) == wx1:
                score -= 20
                evidence.append(f"日干{wx2}克{wx1},单方憋屈(-20)")

    if zhi1 and zhi2:
        if _HE_LIUHE.get(zhi1) == zhi2:
            score += 20
            evidence.append(f"日支{zhi1}{zhi2}六合,婚姻宫暗合(+20)")
        elif _HE_CHONG.get(zhi1) == zhi2:
            score -= 25
            evidence.append(f"日支{zhi1}{zhi2}六冲,婚姻宫对冲(-25)")
        elif zhi1 == zhi2:
            score += 5
            evidence.append(f"日支同为{zhi1},气场共振(+5)")
        sanhe_matched = False
        for tri in _HE_SANHE:
            if zhi1 in tri and zhi2 in tri and zhi1 != zhi2:
                score += 8
                el_map = {frozenset({"申", "子", "辰"}): "水",
                          frozenset({"亥", "卯", "未"}): "木",
                          frozenset({"寅", "午", "戌"}): "火",
                          frozenset({"巳", "酉", "丑"}): "金"}
                el = el_map.get(frozenset(tri), "?")
                evidence.append(f"日支{zhi1}{zhi2}半会{el}局(+8)")
                sanhe_matched = True
                break
        if not sanhe_matched:
            for tri in _HE_SANHUI:
                if zhi1 in tri and zhi2 in tri and zhi1 != zhi2:
                    score += 5
                    evidence.append(f"日支{zhi1}{zhi2}半会方(+5)")
                    break

    yz1 = b1.get("year", "")[1] if len(b1.get("year", "")) > 1 else ""
    yz2 = b2.get("year", "")[1] if len(b2.get("year", "")) > 1 else ""
    if yz1 and yz2 and _HE_LIUHE.get(yz1) == yz2:
        score += 8
        evidence.append(f"年支{yz1}{yz2}六合,家庭背景契合(+8)")
    if yz1 and yz2 and _HE_CHONG.get(yz1) == yz2:
        score -= 8
        evidence.append(f"年支{yz1}{yz2}六冲,家庭背景冲突(-8)")

    if not evidence:
        evidence.append("日柱年支均无特殊关系,主要靠后天经营")

    return {"score": max(0, min(100, int(score))), "evidence": evidence}


def _check_dayun_sync(b1: dict, b2: dict) -> dict:
    """大运同步维度"""
    evidence = []
    score = 50

    dayun1 = b1.get("dayun", []) or []
    dayun2 = b2.get("dayun", []) or []
    if not dayun1 or not dayun2:
        return {"score": 50, "evidence": ["大运数据缺失,无法判断阶段共振"]}

    def _phase(gan: str) -> str:
        return {
            "比肩": "印比相扶期", "劫财": "印比相扶期",
            "食神": "食伤泄秀期", "伤官": "食伤泄秀期",
            "偏财": "财星运行期", "正财": "财星运行期",
            "七杀": "官杀压力期", "正官": "官杀压力期",
            "偏印": "印比相扶期", "正印": "印比相扶期",
        }.get(gan, "中性期")

    sync_count = 0
    total_overlap = 0
    for d1_item in dayun1[:5]:
        for d2_item in dayun2[:5]:
            y1s = d1_item.get("start_year", 0)
            y2s = d2_item.get("start_year", 0)
            y1e = d1_item.get("end_year", 9999)
            y2e = d2_item.get("end_year", 9999)
            if y1s <= y2e and y2s <= y1e:
                total_overlap += 1
                phase1 = _phase(d1_item.get("shishen_gan", ""))
                phase2 = _phase(d2_item.get("shishen_gan", ""))
                period = f"{max(y1s, y2s)}-{min(y1e, y2e)}"
                if phase1 == phase2:
                    sync_count += 1
                    evidence.append(
                        f"{period}:同入「{phase1}」({d1_item.get('ganzhi', '')}/{d2_item.get('ganzhi', '')}),节奏共振"
                    )
                else:
                    evidence.append(
                        f"{period}:甲方{phase1} vs 乙方{phase2}({d1_item.get('ganzhi', '')}/{d2_item.get('ganzhi', '')}),节奏错位"
                    )

    if total_overlap == 0:
        evidence.append("双方大运年份无重叠,本维度判定不可靠")
        return {"score": 50, "evidence": evidence}

    sync_ratio = sync_count / total_overlap

    if sync_ratio >= 0.7:
        score = 85
        evidence.insert(0, f"双方大运同步率 {sync_ratio:.0%},深节奏共振")
    elif sync_ratio >= 0.5:
        score = 70
        evidence.insert(0, f"双方大运同步率 {sync_ratio:.0%},多数时间同频")
    elif sync_ratio >= 0.3:
        score = 55
        evidence.insert(0, f"双方大运同步率 {sync_ratio:.0%},节奏有差异但可协调")
    else:
        score = 35
        evidence.insert(0, f"双方大运同步率仅 {sync_ratio:.0%},容易各走各的")

    cur1 = next((d for d in dayun1 if d.get("is_current")), dayun1[0] if dayun1 else None)
    cur2 = next((d for d in dayun2 if d.get("is_current")), dayun2[0] if dayun2 else None)
    if cur1 and cur2:
        p1 = _phase(cur1.get("shishen_gan", ""))
        p2 = _phase(cur2.get("shishen_gan", ""))
        if "官杀压力" in p1 and "食伤" in p2:
            evidence.append(
                f"当前大运冲突:甲方扛压({cur1.get('ganzhi', '')}),乙方泄气({cur2.get('ganzhi', '')})"
            )
        if "财星" in p1 and "印比" in p2:
            evidence.append(
                f"当前大运差异:甲方求财({cur1.get('ganzhi', '')}),乙方守内({cur2.get('ganzhi', '')})"
            )

    return {"score": max(0, min(100, int(score))), "evidence": evidence}


def _check_shensha_conflict(b1: dict, b2: dict) -> dict:
    """神煞冲突维度"""
    evidence = []
    score = 70
    warnings = []

    ss1 = set([s for s in [_shensha_keyword(x) for x in (b1.get("shensha", []) or [])] if s])
    ss2 = set([s for s in [_shensha_keyword(x) for x in (b2.get("shensha", []) or [])] if s])

    conflict_pairs = [
        ({"劫煞"}, {"亡神"}, "财务纠纷风险", "婚后财务结构建议提前明确"),
        ({"七杀"}, {"羊刃"}, "性格冲撞", "遇事各退一步,设置冷静期"),
        ({"勾煞", "勾绞煞"}, {"绞煞", "勾绞煞"}, "人际是非", "避免介入对方社交纠纷"),
        ({"白虎"}, {"血刃", "飞刃"}, "健康/意外风险", "高危运动慎重"),
        ({"披麻"}, {"吊客"}, "情绪低沉", "需要共同建立心理支持网络"),
    ]
    for a, b, topic, warn in conflict_pairs:
        if (a & ss1 and b & ss2) or (a & ss2 and b & ss1):
            score -= 12
            evidence.append(f"冲突对:{topic}")
            warnings.append(warn)

    bad_keywords = {"劫煞", "亡神", "七杀", "羊刃", "勾绞煞", "白虎", "血刃", "飞刃", "披麻", "吊客", "灾煞"}
    both_bad = (ss1 & ss2) & bad_keywords
    if both_bad:
        score -= 8
        evidence.append(f"双方共有凶煞 {sorted(both_bad)},原生家庭层面都有同类课题")

    good_pairs = [
        ({"天乙贵人"}, {"天乙贵人"}, "双方贵人加持,遇事有人帮"),
        ({"太极贵人"}, {"太极贵人"}, "双方追求精神世界,有共同审美"),
        ({"文昌贵人"}, {"文昌贵人"}, "重视教育,孩子学业顺遂"),
        ({"天德贵人", "月德贵人"}, {"天德贵人", "月德贵人"}, "化险为夷,关键时点互相救"),
    ]
    for a, b, topic in good_pairs:
        a_match = bool(a & ss1) and bool(b & ss2)
        b_match = bool(b & ss1) and bool(a & ss2)
        self_a = bool(a & ss1) and bool(a & ss2)
        self_b = bool(b & ss1) and bool(b & ss2)
        if a_match or b_match or self_a or self_b:
            score += 8
            evidence.append(f"贵人叠加:{topic}")
            break

    if "桃花" in ss1 and "桃花" in ss2:
        score -= 8
        warnings.append("双方均有桃花煞,外部诱惑多,建议建立共同边界感")
        evidence.append("双桃花警示:双方均带桃花煞,人际中容易遇到异性示好")

    if "华盖" in ss1 and "华盖" in ss2:
        evidence.append("双华盖:双方都偏精神世界,可能各自沉浸,需主动连接")
        score -= 5

    if ("红鸾" in ss1 and "天喜" in ss2) or ("红鸾" in ss2 and "天喜" in ss1):
        score += 6
        evidence.append("红鸾天喜呼应,婚配吉象")

    if not evidence:
        evidence.append("双方神煞无显著冲突/叠加,关系走势较平稳")

    return {
        "score": max(0, min(100, int(score))),
        "evidence": evidence,
        "warnings": warnings,
    }


def _check_ziwei_match(udm1, udm2) -> dict:
    """紫微合盘维度"""
    evidence = []
    score = 50

    zw1 = getattr(udm1, "ziwei_chart", None) or {}
    zw2 = getattr(udm2, "ziwei_chart", None) or {}
    pal1 = zw1.get("palaces", []) or []
    pal2 = zw2.get("palaces", []) or []

    fq1 = next((p for p in pal1 if p.get("name") == "夫妻"), None)
    fq2 = next((p for p in pal2 if p.get("name") == "夫妻"), None)

    if not fq1 or not fq2:
        return {
            "score": 50,
            "evidence": ["紫微夫妻宫数据缺失,跳过此维度"],
        }

    major1 = [s.get("name", "") for s in fq1.get("major_stars", []) or []]
    major2 = [s.get("name", "") for s in fq2.get("major_stars", []) or []]
    hua1 = {s.get("name"): s.get("mutagen", "") for s in fq1.get("major_stars", []) or []}
    hua2 = {s.get("name"): s.get("mutagen", "") for s in fq2.get("major_stars", []) or []}

    auspicious = {"天府", "天相", "太阳", "天同", "天梁", "天机", "紫微"}
    inauspicious_fuqigong = {"贪狼", "擎羊", "陀罗", "火星", "铃星", "破军", "七杀"}

    if not major1 or not major2:
        return {
            "score": 60,
            "evidence": ["一方或双方夫妻宫无主星,借对宫力量,关系中需要外界契机推动"],
        }

    a_is_good = any(m in auspicious for m in major1)
    b_is_good = any(m in auspicious for m in major2)
    a_is_bad = any(m in inauspicious_fuqigong for m in major1)
    b_is_bad = any(m in inauspicious_fuqigong for m in major2)

    evidence.append(
        f"甲方夫妻宫主星:{','.join(major1) or '无主星'}(四化:{','.join(v for v in hua1.values() if v) or '无'})"
    )
    evidence.append(
        f"乙方夫妻宫主星:{','.join(major2) or '无主星'}(四化:{','.join(v for v in hua2.values() if v) or '无'})"
    )

    pairs_bonus = {
        frozenset({"天府", "天相"}): 15,
        frozenset({"天机", "天梁"}): 10,
        frozenset({"紫微", "天府"}): 15,
        frozenset({"武曲", "天相"}): 10,
        frozenset({"太阳", "天同"}): 12,
    }
    common_stars = set(major1) & set(major2)
    for p, bonus in pairs_bonus.items():
        if p & common_stars:
            score += bonus
            evidence.append(f"主星同见 {sorted(p & common_stars)[0]},缘分之合(+{bonus})")
            break

    if a_is_good and b_is_good:
        score += 15
        evidence.append("双方夫妻宫皆为吉星照命,关系柔和正向(+15)")
    if a_is_bad and b_is_bad:
        score -= 15
        evidence.append("双方夫妻宫皆沾煞星,关系张力大需技巧(-15)")

    if any(v == "禄" for v in hua1.values()) and any(v == "禄" for v in hua2.values()):
        score += 8
        evidence.append("双方夫妻宫皆见化禄,情感丰富")
    if any(v == "忌" for v in hua1.values()) and any(v == "忌" for v in hua2.values()):
        score -= 10
        evidence.append("双方夫妻宫皆见化忌,需特别注意沟通")

    return {
        "score": max(0, min(100, int(score))),
        "evidence": evidence,
    }


def _build_bazi_extract(udm) -> dict:
    """从 udm 抽取合婚必需字段(只读)"""
    if not udm or not getattr(udm, "bazi_year", None):
        return {}
    xi_yong = getattr(udm, "xi_yong", {}) or {}
    return {
        "year": udm.bazi_year.ganzhi if udm.bazi_year else "",
        "month": udm.bazi_month.ganzhi if udm.bazi_month else "",
        "day": udm.bazi_day.ganzhi if udm.bazi_day else "",
        "time": udm.bazi_time.ganzhi if udm.bazi_time else "",
        "day_master": udm.day_master or "",
        "day_master_wuxing": udm.day_master_wuxing or "",
        "xi_yong": {
            "xi": _safe_str_list(xi_yong.get("xi")),
            "ji": _safe_str_list(xi_yong.get("ji")),
            "xian": _safe_str_list(xi_yong.get("xian")),
            "strength": xi_yong.get("strength", ""),
        },
        "wuxing_score": getattr(udm, "wuxing_score", {}) or {},
        "shishen_gan": getattr(udm, "shishen_gan", {}) or {},
        "dayun": [
            {
                "start_age": d.get("start_age"),
                "end_age": d.get("end_age"),
                "start_year": d.get("start_year"),
                "end_year": d.get("end_year"),
                "ganzhi": d.get("ganzhi", ""),
                "is_current": d.get("is_current", False),
                "shishen_gan": d.get("shishen_gan", ""),
                "shishen_gan_desc": d.get("shishen_gan_desc", ""),
                "changsheng": d.get("changsheng", ""),
                "shensha": d.get("shensha", []) or [],
            }
            for d in (getattr(udm, "dayun", []) or [])
        ],
        "shensha": getattr(udm, "shensha", []) or [],
    }


def _hehun_verdict(score: int) -> str:
    if score >= 85:
        return "上等匹配,婚配顺遂,值得长期经营"
    if score >= 70:
        return "中上匹配,主要维度和谐,小处需要磨合"
    if score >= 55:
        return "中等匹配,有亮点也有挑战,靠双方用心"
    if score >= 40:
        return "中等偏下,核心维度有冲突,需要外部协助(咨询/沟通)"
    return "下等匹配,命理符号层面阻力大,慎重决策"


def _hehun_based_on(dims: dict) -> list:
    sources = []
    if dims["wuxing_bu"]["score"] >= 70:
        sources.append("五行互补")
    if dims["bazi_complement"]["score"] >= 70:
        sources.append("八字相合")
    if dims["dayun_sync"]["score"] >= 70:
        sources.append("大运同步")
    if dims["shensha_conflict"]["score"] >= 70:
        sources.append("神煞相安")
    if dims["ziwei_match"]["score"] >= 70:
        sources.append("紫微合盘")
    if dims["wuxing_bu"]["score"] < 50:
        sources.append("五行反差")
    if dims["bazi_complement"]["score"] < 50:
        sources.append("八字对冲")
    if dims["dayun_sync"]["score"] < 50:
        sources.append("大运错位")
    if not sources:
        sources.append("多维均衡")
    return sources


_HEHUN_VERIFY_QUESTIONS = [
    {
        "topic": "匹配度",
        "question": "你们目前相处,吵架频率大概是?",
        "options": [
            "几乎不吵 / 偶尔有分歧但能化解",
            "每月一两次,事后能复盘",
            "每周都有,常翻旧账",
            "高频激烈 / 冷战居多",
        ],
        "evidence_match": "高频吵架对应大运错位或神煞冲突;低频对应大运同步",
    },
    {
        "topic": "主控权",
        "question": "重大决定(搬家、理财、跳槽)通常谁拍板?",
        "options": [
            "明确一个人做主",
            "协商,但有一方倾向主导",
            "完全商量着来",
            "互相推诿 / 拖着不决",
        ],
        "evidence_match": "单方主导倾向对应日干克关系;完全协商对应日干天合",
    },
    {
        "topic": "财务",
        "question": "钱归谁管?有没有财务边界?",
        "options": [
            "完全合并 / 共同账户",
            "各管各,大额共担",
            "一方交工资 / 另一方分配",
            "经济上有隐瞒或争执",
        ],
        "evidence_match": "劫煞+亡神组合建议财务结构明确;合并账户契合神煞相安者",
    },
    {
        "topic": "原生家庭",
        "question": "双方家长对你们关系态度如何?",
        "options": [
            "都支持",
            "一边支持一边有保留",
            "都有介入但能谈",
            "对立 / 不来往",
        ],
        "evidence_match": "年支六合 = 家庭契合;六冲 = 家庭冲突",
    },
    {
        "topic": "亲密节奏",
        "question": "过去一年,亲密沟通频率是?",
        "options": [
            "持续高频,身心同步",
            "有时多有时少,但能聊",
            "想沟通但总被打断",
            "冷淡 / 情感回避",
        ],
        "evidence_match": "日支六合 = 亲密自然;双华盖/孤辰 = 精神世界各自沉浸",
    },
]


def _hehun_warnings(dims: dict, b1: dict, b2: dict) -> list:
    warns = []
    ss_warns = dims["shensha_conflict"].get("warnings", []) or []
    warns.extend(ss_warns)
    if dims["bazi_complement"]["score"] < 55:
        warns.append("日柱/日支有冲克,前期分歧多,建议设立共同仪式(每周一次固定深度沟通)")
    if dims["dayun_sync"]["score"] < 55:
        warns.append("未来 5-10 年大运错位概率高,关键节点(生育/置业/父母健康)需要预案")
    if "化忌" in " ".join(dims["ziwei_match"].get("evidence", [])):
        warns.append("紫微化忌同现,情绪爆点易在深夜/独处时刻,建议约定'暂停键'")
    if not warns:
        warns.append("命理层面无显著危机信号,主要功课在于日常相处")
    return warns


def _call_bazi_analyzer(func_name: str, udm) -> dict:
    """调用bazi_engine的高级分析函数（改进 #251-#260）"""
    try:
        from engine import bazi_engine as _be
        func = getattr(_be, func_name, None)
        if not func:
            return {"error": f"function {func_name} not found"}
        pillars = []
        if udm.bazi_year:
            pillars.append(udm.bazi_year)
        if udm.bazi_month:
            pillars.append(udm.bazi_month)
        if udm.bazi_day:
            pillars.append(udm.bazi_day)
        if udm.bazi_time:
            pillars.append(udm.bazi_time)
        if func_name == "analyze_ten_gods_distribution":
            return func(udm.shishen_gan or {})
        if func_name == "analyze_career_tendency":
            return func(udm.shishen_gan or {}, udm.shishen_zhi or {})
        if func_name == "analyze_relationship_indicator":
            return func(pillars, udm.shensha or [])
        if func_name == "analyze_health_indicator":
            return func(udm.day_master or "", udm.wuxing_score or {})
        if func_name == "analyze_wealth_pattern":
            return func(udm.shishen_gan or {}, pillars)
        if func_name == "analyze_deities_in_pillars":
            return func(pillars, udm.day_master or "")
        return func(pillars)
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/engines")
def get_engines_status():
    """返回各引擎状态"""
    try:
        orch = get_orchestrator()
        engines = []
        for eng in orch.engines:
            engines.append({
                "name": eng.name,
                "name_en": eng.name_en,
                "priority": eng.priority,
                "available": getattr(eng, '_available', getattr(eng, '_najia_available', True)),
            })
        return {"engines": engines, "count": len(engines)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/chart")
def get_chart(
    birth: str = Query(..., description="出生时间，如 2005-06-09 11:50"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别: 男/女"),
    name: str = Query("", description="姓名（可选）"),
):
    """七术排盘接口（含姓名学）"""
    try:
        name = _sanitize_name(name)
        corrected, udm = _prepare_udm(birth, location, gender)

        # 构建返回数据
        result = {
            "input": {
                "birth": birth,
                "location": location,
                "gender": gender,
                "name": name,
            },
            "corrected_time": {
                "original": corrected.original.isoformat(),
                "true_solar": corrected.true_solar.isoformat(),
                "longitude": corrected.longitude,
                "latitude": corrected.latitude,
                "is_late_zi": corrected.is_late_zi,
                "diff_minutes": round((corrected.true_solar - corrected.original).total_seconds() / 60, 1),
            },
            "methods": udm.get_available_methods(),
            "errors": udm.engine_errors,
        }

        # 八字
        if udm.bazi_year:
            result["bazi"] = {
                "year": udm.bazi_year.ganzhi or "",
                "month": udm.bazi_month.ganzhi if udm.bazi_month else "",
                "day": udm.bazi_day.ganzhi if udm.bazi_day else "",
                "time": udm.bazi_time.ganzhi if udm.bazi_time else "",
                "day_master": udm.day_master or "",
                "day_master_wuxing": udm.day_master_wuxing or "",
                "shishen": udm.shishen_gan or {},
                "shishen_gan": udm.shishen_gan or {},
                "shishen_zhi": getattr(udm, 'shishen_zhi', {}) or {},
                "hidden_gans": getattr(udm, 'hidden_gans', {}) or {},
                "nayin": udm.nayin or {},
                "features": udm.features or [],
                "tiaohou": udm.tiaohou or "",
                "wuxing_score": udm.wuxing_score or {},
                "xunkong": getattr(udm, 'xunkong', {}) or {},
                "shensha": getattr(udm, 'shensha', []) or [],
                "shensha_per_pillar": getattr(udm, 'shensha_per_pillar', {}) or {},
                "changsheng": getattr(udm, 'changsheng', {}) or {},
                "gan_relations": getattr(udm, 'gan_relations', []) or [],
                "zhi_relations": getattr(udm, 'zhi_relations', []) or [],
                "dayun": getattr(udm, 'dayun', []) or [],
                "dayun_start_age": getattr(udm, 'dayun_start_age', 0) or 0,
                "ming_gong": getattr(udm, 'ming_gong', "") or "",
                "ming_gong_shishen": getattr(udm, 'ming_gong_shishen', None) or {},
                "tai_yuan": getattr(udm, 'tai_yuan', "") or "",
                "tai_yuan_shishen": getattr(udm, 'tai_yuan_shishen', None) or {},
                "shen_gong": getattr(udm, 'shen_gong', "") or "",
                "shen_gong_shishen": getattr(udm, 'shen_gong_shishen', None) or {},
                "xi_yong": getattr(udm, 'xi_yong', {}) or {},
                "strength": (getattr(udm, 'xi_yong', None) or {}).get("strength", ""),
                "wuxing_summary": (getattr(udm, 'xi_yong', None) or {}).get("reason", ""),
                "liunian": getattr(udm, 'liunian', None),
                "location": getattr(udm, 'location', None),
                # 改进 #219-#230:补全关键解读字段
                "geju": _analyze_geju(udm),  # 格局判定
                "dayun_summary": _summarize_dayun(udm),  # 大运总结
                "shensha_grouped": _group_shensha(udm),  # 神煞分组
                "kongwang_table": _build_kongwang_table(udm),  # 旬空查表
                "true_solar_diff": _true_solar_diff(udm),  # 真太阳时差
                "taiji_table": _build_taiji_table(udm),  # 太极贵人表
                "wenchang_table": _build_wenchang_table(udm),  # 文昌贵人表
                "taohua_table": _build_taohua_table(udm),  # 桃花表
                "yima_table": _build_yima_table(udm),  # 驿马表
                "huagai_table": _build_huagai_table(udm),  # 华盖表
                "tianyi_table": _build_tianyi_table(udm),  # 天乙贵人表
                "shensha_summary": _summarize_shensha(udm),  # 神煞汇总
                # 改进 #251-#260: 高级分析10个新方法
                "tiangan_xiangke": _call_bazi_analyzer("analyze_tian_gan_di_zhi_xiang_ke", udm),
                "changsheng_distribution": _call_bazi_analyzer("analyze_deities_in_pillars", udm),
                "jieqi_lord": _call_bazi_analyzer("analyze_jieqi_lord", udm),
                "yueling_strength": _call_bazi_analyzer("analyze_yue_ling_strength", udm),
                "ganzhi_combinations": _call_bazi_analyzer("analyze_gan_zhi_combinations", udm),
                "ten_gods_distribution": _call_bazi_analyzer("analyze_ten_gods_distribution", udm),
                "career_tendency": _call_bazi_analyzer("analyze_career_tendency", udm),
                "relationship_indicator": _call_bazi_analyzer("analyze_relationship_indicator", udm),
                "health_indicator": _call_bazi_analyzer("analyze_health_indicator", udm),
                "wealth_pattern": _call_bazi_analyzer("analyze_wealth_pattern", udm),
            }

        # 占星
        if udm.astro_chart:
            result["astro"] = {
                "sun_sign": udm.astro_chart.get("sun_sign"),
                "sun_element": udm.astro_chart.get("sun_element"),
                "moon_sign": udm.astro_chart.get("moon_sign"),
                "moon_element": udm.astro_chart.get("moon_element"),
                "ascendant": udm.astro_chart.get("ascendant"),
                "ascendant_sign": udm.astro_chart.get("ascendant_sign"),
                "mc": udm.astro_chart.get("mc"),
                "mc_sign": udm.astro_chart.get("mc_sign"),
                "houses": udm.astro_chart.get("houses"),
                "planets": udm.astro_chart.get("planets"),
                "aspects": udm.astro_chart.get("aspects"),
                "aspects_summary": udm.astro_chart.get("aspects_summary"),
                "house_rulers": udm.astro_chart.get("house_rulers"),
                "north_node": udm.astro_chart.get("north_node"),
                "south_node": udm.astro_chart.get("south_node"),
                "planetary_details": udm.astro_chart.get("planetary_details"),
            }

        # 紫微
        if udm.ziwei_chart:
            result["ziwei"] = {
                "ming_gong": udm.ziwei_chart.get("ming_gong"),
                "shen_gong": udm.ziwei_chart.get("shen_gong"),
                "soul_star": udm.ziwei_chart.get("soul_star"),
                "body_star": udm.ziwei_chart.get("body_star"),
                "wuxing_ju": udm.ziwei_chart.get("wuxing_ju"),
                "start_age": udm.ziwei_chart.get("start_age", 0),
                "star_placements": udm.ziwei_chart.get("star_placements"),
                "sihua": udm.ziwei_chart.get("sihua"),
                "self_hua_map": udm.ziwei_chart.get("self_hua_map", {}),
                "palaces": udm.ziwei_chart.get("palaces"),
                "gender": udm.ziwei_chart.get("gender"),
                "lunar_date": udm.ziwei_chart.get("lunar_date", ""),
                "chinese_date": udm.ziwei_chart.get("chinese_date", ""),
                "zodiac": udm.ziwei_chart.get("zodiac", ""),
                "dai_xian": udm.ziwei_chart.get("dai_xian", []),
                "nominal_age": udm.ziwei_chart.get("nominal_age", 0),
                "zi_dou": udm.ziwei_chart.get("zi_dou", ""),
                "liunian": udm.ziwei_chart.get("liunian", {}),
            }

        # 六爻
        if udm.liuyao_chart:
            result["liuyao"] = {
                "ben_gua": udm.liuyao_chart.get("ben_gua"),
                "bian_gua": udm.liuyao_chart.get("bian_gua"),
                "dong_yao": udm.liuyao_chart.get("dong_yao"),
                "shi": udm.liuyao_chart.get("shi"),
                "ying": udm.liuyao_chart.get("ying"),
                "lines": udm.liuyao_chart.get("lines"),
                "bian_lines": udm.liuyao_chart.get("bian_lines"),
                "liu_shen": udm.liuyao_chart.get("liu_shen"),
                "gua_gong_wuxing": udm.liuyao_chart.get("gua_gong_wuxing"),
                "wuxing_analysis": udm.liuyao_chart.get("wuxing_analysis"),
                "ri_yue_jian": udm.liuyao_chart.get("ri_yue_jian"),
                "fu_shen": udm.liuyao_chart.get("fu_shen"),
                "ge_ju": udm.liuyao_chart.get("ge_ju", []),
                "date": udm.liuyao_chart.get("date"),
                "liunian": udm.liuyao_chart.get("liunian"),
            }

        # 奇门
        if udm.qimen_chart:
            result["qimen"] = {
                "ju_name": udm.qimen_chart.get("ju_name"),
                "yin_yang": udm.qimen_chart.get("yin_yang"),
                "ju_shu": udm.qimen_chart.get("ju_shu"),
                "jieqi": udm.qimen_chart.get("jieqi"),
                "di_pan": udm.qimen_chart.get("di_pan"),
                "tian_pan": udm.qimen_chart.get("tian_pan"),
                "ba_men": udm.qimen_chart.get("ba_men"),
                "jiu_xing": udm.qimen_chart.get("jiu_xing"),
                "ba_shen": udm.qimen_chart.get("ba_shen"),
                "palaces": udm.qimen_chart.get("palaces"),
                "zhi_fu": udm.qimen_chart.get("zhi_fu"),
                "zhi_fu_gong": udm.qimen_chart.get("zhi_fu_gong"),
                "zhi_shi": udm.qimen_chart.get("zhi_shi"),
                "time_gan": udm.qimen_chart.get("time_gan"),
                "xun_kong": udm.qimen_chart.get("xun_kong"),
                "hidden_yi": (udm.qimen_chart.get("xun_kong") or {}).get("hidden_yi", ""),
                "day_gan_zhi": udm.qimen_chart.get("day_gan_zhi"),
                "time_gan_zhi": udm.qimen_chart.get("time_gan_zhi"),
                "san_pan_summary": udm.qimen_chart.get("san_pan_summary", {}),
                "ge_ju_analysis": udm.qimen_chart.get("ge_ju_analysis", {}),
                "liunian": udm.qimen_chart.get("liunian"),
            }

        # 大六壬
        if udm.liuren_chart:
            lc = udm.liuren_chart
            result["liuren"] = {
                "si_zhu": {
                    "year": f"{lc.get('year_gan','')}{lc.get('year_zhi','')}",
                    "month": f"{lc.get('month_gan','')}{lc.get('month_zhi','')}",
                    "day": f"{lc.get('day_gan','')}{lc.get('day_zhi','')}",
                    "time": f"{lc.get('time_gan','')}{lc.get('time_zhi','')}",
                },
                "zhan_shi": lc.get("zhan_shi"),
                "yue_jiang": lc.get("yue_jiang"),
                "yue_jiang_zhi": lc.get("yue_jiang_zhi"),
                "jieqi": lc.get("jieqi"),
                "tian_pan": lc.get("tian_pan"),
                "positions": lc.get("positions"),
                "gan_ji": lc.get("gan_ji"),
                "si_ke": lc.get("si_ke"),
                "san_chuan": lc.get("san_chuan"),
                "tian_jiang": lc.get("tian_jiang"),
                "day_gan": lc.get("day_gan"),
                "day_zhi": lc.get("day_zhi"),
                "ge_ju": lc.get("ge_ju", ""),
                "day_ma": lc.get("day_ma", ""),
                "yong_shen": lc.get("yong_shen", {}),
                "si_ke_analysis": lc.get("si_ke_analysis", {}),
            }

        # 太乙
        if udm.taiyi_chart:
            result["taiyi"] = {
                "taiyi_gong": udm.taiyi_chart.get("taiyi_gong"),
                "taiyi_gua": udm.taiyi_chart.get("taiyi_gua"),
                "ju_name": udm.taiyi_chart.get("ju_name"),
                "ju_num": udm.taiyi_chart.get("ju_num"),
                "ji_nian": udm.taiyi_chart.get("ji_nian"),
                "ji_yuan": udm.taiyi_chart.get("ji_yuan"),
                "yin_yang": udm.taiyi_chart.get("yin_yang"),
                "year_ganzhi": udm.taiyi_chart.get("year_ganzhi"),
                "month_ganzhi": udm.taiyi_chart.get("month_ganzhi"),
                "day_ganzhi": udm.taiyi_chart.get("day_ganzhi"),
                "hour_ganzhi": udm.taiyi_chart.get("hour_ganzhi"),
                "san_ji": udm.taiyi_chart.get("san_ji"),
                "wu_fu": udm.taiyi_chart.get("wu_fu"),
                "da_you": udm.taiyi_chart.get("da_you"),
                "xiao_you": udm.taiyi_chart.get("xiao_you"),
                "tian_yi": udm.taiyi_chart.get("tian_yi"),
                "di_yi": udm.taiyi_chart.get("di_yi"),
                "si_shen": udm.taiyi_chart.get("si_shen"),
                "zhi_fu": udm.taiyi_chart.get("zhi_fu"),
                "wen_chang": udm.taiyi_chart.get("wen_chang"),
                "shi_ji": udm.taiyi_chart.get("shi_ji"),
                "zhu_suan": udm.taiyi_chart.get("zhu_suan"),
                "ke_suan": udm.taiyi_chart.get("ke_suan"),
                "ding_suan": udm.taiyi_chart.get("ding_suan"),
                "ba_men": udm.taiyi_chart.get("ba_men"),
                "ba_men_dist": udm.taiyi_chart.get("ba_men_dist"),
                "zhu_ke": udm.taiyi_chart.get("zhu_ke"),
                "sheng_fu": udm.taiyi_chart.get("sheng_fu"),
                "tai_su_su": udm.taiyi_chart.get("tai_su_su"),
                "shi_ji_su": udm.taiyi_chart.get("shi_ji_su"),
                "tian_gan_yu": udm.taiyi_chart.get("tian_gan_yu"),
                "suan_analysis": udm.taiyi_chart.get("suan_analysis", {}),
            }

        # 姓名学（如果有姓名）
        if name and len(name) >= 2:
            global _xingming_engine
            if _xingming_engine is None:
                _xingming_engine = XingMingEngine()
            # 分离姓和名
            # 复姓检测使用统一的 COMPOUND_SURNAMES 列表（定义在 xingming_engine）
            surname = name[0]
            given_name = name[1:]
            for cs in COMPOUND_SURNAMES:
                if name.startswith(cs):
                    surname = cs
                    given_name = name[len(cs):]
                    break
            
            # 构建八字信息用于姓名学配合
            bazi_info = None
            if udm.bazi_year:
                xi_yong = getattr(udm, 'xi_yong', None) or {}
                xi_shen = xi_yong.get('xi', [])
                ji_shen = xi_yong.get('ji', [])
                if isinstance(xi_shen, str):
                    xi_shen = [xi_shen] if xi_shen else []
                if isinstance(ji_shen, str):
                    ji_shen = [ji_shen] if ji_shen else []
                bazi_info = {
                    'year_zhi': getattr(udm.bazi_year, 'zhi', ''),
                    'day_master': udm.day_master or '',
                    'day_master_wuxing': udm.day_master_wuxing or '',
                    'tiaohou': udm.tiaohou or '',
                    'ri_zhu': udm.bazi_day.ganzhi if udm.bazi_day else udm.day_master or '',
                    'xi_shen': xi_shen,
                    'ji_shen': ji_shen,
                }
            
            xm_result = _xingming_engine.analyze_name(surname, given_name, "男" if gender.lower() in ("男", "male", "m") else "女", bazi_info)
            result["xingming"] = xm_result
            result["methods"].append("姓名学")

        return result

    except Exception as e:
        return _error_response(e)


@router.get("/api/cross-validate")
def cross_validate(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
):
    """交叉验证接口"""
    try:
        corrected, udm = _prepare_udm(birth, location, gender)

        validator = CrossValidator(udm)
        result = validator.validate()
        comprehensive = validator.generate_comprehensive_judgment()

        # 序列化
        return {
            "method_count": result["method_count"],
            "available_methods": result["available_methods"],
            "overall_confidence": result["overall_confidence"].value,
            "comprehensive_judgment": comprehensive,
            "consensus": [
                {
                    "aspect": c.aspect,
                    "finding": c.finding,
                    "supporting_methods": c.supporting_methods,
                    "confidence": c.confidence.value,
                }
                for c in result["consensus"]
            ],
            "conflicts": [
                {
                    "aspect": c.aspect,
                    "method_a": c.method_a,
                    "finding_a": c.finding_a,
                    "method_b": c.method_b,
                    "finding_b": c.finding_b,
                    "suggestion": c.suggestion,
                }
                for c in result["conflicts"]
            ],
        }

    except Exception as e:
        return _error_response(e)


@router.get("/api/debate")
def get_debate(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
    question: str = Query("此人命运如何？", description="问题"),
    figures: Optional[str] = Query(None, description="人物ID，逗号分隔，默认12位核心人物"),
):
    """辩论接口（108人全员轮流发言+插队反驳，仅玄照综合用1次LLM）"""
    try:
        corrected, udm = _prepare_udm(birth, location, gender)

        # 视角推理（默认12位核心人物，避免超时）
        pe = PerspectiveEngine()
        opinions = pe.analyze(udm, question, _get_figure_ids(figures))

        # 辩论
        de = DebateEngine()
        debate_result = de.debate(opinions, question)

        return debate_result

    except Exception as e:
        return _error_response(e)


@router.get("/api/debate/stream")
def debate_stream(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
    question: str = Query("此人命运如何？", description="问题"),
    figures: Optional[str] = Query(None, description="人物ID，逗号分隔"),
):
    """串行审判辩论SSE流（108人逐个发言+逐人审判）"""
    def event_generator():
        try:
            from engine.sequential_debate import SequentialDebateEngine
            from engine.perspective_engine import PerspectiveEngine

            corrected, udm = _prepare_udm(birth, location, gender)

            pe = PerspectiveEngine()
            opinions = pe.analyze(udm, question, _get_figure_ids(figures))

            engine = SequentialDebateEngine()
            for event in engine.run_debate(opinions, question):
                yield f"event: {event['event']}\ndata: {_json.dumps(event['data'], ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"辩论流错误: {e}\n{traceback.format_exc()}")
            yield f"event: error\ndata: {_json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/debate/stream-fast")
def debate_stream_fast(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
    question: str = Query("此人命运如何？", description="问题"),
    figures: Optional[str] = Query(None, description="人物ID，逗号分隔"),
):
    """快速辩论SSE流（串行审查链：首发推演→逐人审查→溟玄终审）"""
    def event_generator():
        try:
            from engine.sequential_review_debate import SequentialReviewDebate
            from engine.perspective_engine import PerspectiveEngine

            corrected, udm = _prepare_udm(birth, location, gender)

            pe = PerspectiveEngine()
            opinions = pe.analyze(udm, question, _get_figure_ids(figures))

            engine = SequentialReviewDebate()
            for event in engine.run(opinions, question):
                yield f"event: {event['event']}\ndata: {_json.dumps(event['data'], ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"快速辩论流错误: {e}\n{traceback.format_exc()}")
            yield f"event: error\ndata: {_json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/debate/report")
def debate_report(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
    question: str = Query("此人命运如何？", description="问题"),
    figures: Optional[str] = Query(None, description="人物ID，逗号分隔"),
):
    """生成辩论报告（Markdown格式）"""
    try:
        corrected, udm = _prepare_udm(birth, location, gender)
        pe = PerspectiveEngine()
        opinions = pe.analyze(udm, question, _get_figure_ids(figures))

        de = DebateEngine()
        result = de.debate(opinions, question)

        # 生成Markdown报告
        report = _generate_debate_report(result, question, birth, location, gender)

        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=report,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=debate_report_{birth.replace(' ', '_').replace(':', '-')}.md"
            }
        )
    except Exception as e:
        return _error_response(e)


def _generate_debate_report(result: dict, question: str, birth: str, location: str, gender: str) -> str:
    """生成辩论Markdown报告"""
    lines = []
    lines.append(f"# 玄照辩论报告")
    lines.append(f"")
    lines.append(f"## 基本信息")
    lines.append(f"- **问题**: {question}")
    lines.append(f"- **出生**: {birth} ({location})")
    lines.append(f"- **性别**: {gender}")
    lines.append(f"- **参与人数**: {len(result.get('participants', []))}人")
    lines.append(f"")

    # 玄照判定
    xz = result.get("xuanzhao_perspective", {})
    if xz:
        lines.append(f"## 🔮 玄照综合判定")
        lines.append(f"")
        lines.append(f"**立场**: {xz.get('stance', '综合分析')}")
        lines.append(f"**置信度**: {round(xz.get('confidence', 0) * 100)}%")
        lines.append(f"")

        kp = xz.get("key_points", [])
        if kp:
            lines.append(f"### 核心观点")
            for p in kp:
                lines.append(f"- {p}")
            lines.append(f"")

    # 共识
    consensus = result.get("consensus", [])
    if consensus:
        lines.append(f"## ✅ 共识")
        for c in consensus:
            lines.append(f"- {c}")
        lines.append(f"")

    # 分歧
    disagreements = result.get("disagreements", [])
    if disagreements:
        lines.append(f"## ⚡ 分歧")
        for d in disagreements[:10]:
            names = " vs ".join(d.get("between", []))
            lines.append(f"- **{names}**: {d.get('aspect', '')}")
        lines.append(f"")

    # 参与者
    participants = result.get("participants", [])
    if participants:
        lines.append(f"## 👥 参与者")
        for p in participants:
            lines.append(f"- {p['name']} ({p['method']}) - {p.get('stance', '')[:50]}")
        lines.append(f"")

    # 辩论记录
    exchanges = result.get("exchanges", [])
    if exchanges:
        lines.append(f"## 💬 辩论记录")
        for ex in exchanges:
            lines.append(f"### {ex.speaker} ({ex.speaker_method})")
            if ex.target:
                lines.append(f"> 回应 {ex.target}")
            lines.append(f"")
            lines.append(ex.argument)
            lines.append(f"")

    # 总结
    summary = result.get("summary", "")
    if summary:
        lines.append(f"## 📝 总结")
        lines.append(summary)

    return "\n".join(lines)


@router.get("/api/ask")
def ask_question(
    birth: Optional[str] = Query(None, description="出生时间（可选,不传=知识问答）"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
    question: str = Query(..., description="问题"),
    figures: Optional[str] = Query(None, description="视角人物ids,逗号分隔(可选)"),
):
    """
    玄照 AI 提问接口 (2026-07-11 梧指令)

    两种模式:
    - 客户提问(传 birth):叠加命盘背景
    - 知识问答(不传 birth):只用通用规则

    视角可换:
    - figures=munger,naval → 芒格 + Naval
    - figures=老子,孙子 → 道家 + 兵家
    - 不传 → 综合默认视角
    """
    try:
        from engine.ask_engine import ask as ask_impl

        chart_result = None
        if birth:
            corrected, udm = _prepare_udm(birth, location, gender)
            chart_result = {
                "input": {"birth": birth, "location": location, "gender": gender},
                "corrected_time": {
                    "original": corrected.original.isoformat(),
                    "true_solar": corrected.true_solar.isoformat(),
                    "longitude": corrected.longitude,
                    "latitude": corrected.latitude,
                    "is_late_zi": corrected.is_late_zi,
                    "diff_minutes": round((corrected.true_solar - corrected.original).total_seconds() / 60, 1),
                },
                "bazi": {
                    "year": udm.bazi_year.ganzhi if udm.bazi_year else "",
                    "month": udm.bazi_month.ganzhi if udm.bazi_month else "",
                    "day": udm.bazi_day.ganzhi if udm.bazi_day else "",
                    "time": udm.bazi_time.ganzhi if udm.bazi_time else "",
                    "day_master": udm.day_master or "",
                    "day_master_wuxing": udm.day_master_wuxing or "",
                    "strength": (getattr(udm, 'xi_yong', None) or {}).get("strength", ""),
                    "xi_yong": getattr(udm, 'xi_yong', {}) or {},
                    "shensha": getattr(udm, 'shensha', []) or [],
                    "dayun": getattr(udm, 'dayun', []) or [],
                    "geju": _analyze_geju(udm),
                    "liunian": getattr(udm, 'liunian', None),
                },
            }

        result = ask_impl(question, chart_result, figures)
        return result

    except Exception as e:
        return _error_response(e)



@router.get("/api/validate")
def validate_accuracy(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
):
    """验证排盘准确性：对比 lunar-python 直接计算结果（含真太阳时校正）"""
    try:
        from lunar_python import Solar, EightChar

        # 复用 _validate_birth 校验格式,避免重复格式列表
        try:
            birth = _validate_birth(birth)
        except ValueError as e:
            return JSONResponse(status_code=400, content={"error": str(e)})

        # 通过真太阳时校正(与引擎使用相同时间)
        time_engine = get_time_engine()
        corrected = time_engine.correct(birth, location)
        corrected_dt = corrected.bazi_day_pillar_date
        corrected_hour = corrected.bazi_hour

        # 用校正后的时间直接用 lunar-python 排盘
        solar = Solar.fromYmdHms(
            corrected_dt.year, corrected_dt.month, corrected_dt.day,
            corrected_hour, corrected_dt.minute, 0
        )
        lunar = solar.getLunar()
        ec = EightChar(lunar)

        # 通过 API 排盘
        gender_code = 1 if gender in ("男", "male", "m") else 0
        orch = get_orchestrator()
        udm = orch.run_all(corrected, gender_code)

        # 对比(两者都使用真太阳时校正后的时间)
        direct = {
            "year": ec.getYearGan() + ec.getYearZhi(),
            "month": ec.getMonthGan() + ec.getMonthZhi(),
            "day": ec.getDayGan() + ec.getDayZhi(),
            "time": ec.getTimeGan() + ec.getTimeZhi(),
        }

        api_result = {}
        if udm.bazi_year:
            api_result = {
                "year": udm.bazi_year.ganzhi,
                "month": udm.bazi_month.ganzhi if udm.bazi_month else "",
                "day": udm.bazi_day.ganzhi if udm.bazi_day else "",
                "time": udm.bazi_time.ganzhi if udm.bazi_time else "",
            }

        mismatches = []
        for key in direct:
            if direct[key] != api_result.get(key, ""):
                mismatches.append({"field": key, "direct": direct[key], "api": api_result.get(key, "")})

        return {
            "status": "PASS" if not mismatches else "FAIL",
            "mismatches": mismatches,
            "direct": direct,
            "api": api_result,
        }
    except Exception as e:
        return _error_response(e)


@router.get("/api/figures")
def get_figures():
    """获取所有可用人物（精简版）"""
    try:
        from engine.perspective_engine import FIGURES
        return {
            "total": len(FIGURES),
            "figures": {
                fid: {
                    "name": f.name,
                    "title": f.title,
                    "category": f.category,
                    "faction": f.faction,
                    "expertise": f.expertise,
                    "primary_method": f.primary_method,
                    "catchphrase": f.catchphrase,
                    "bio": f.bio,
                    "soul": f.soul,
                }
                for fid, f in FIGURES.items()
            },
        }
    except Exception as e:
        return _error_response(e)


@router.get("/api/perspectives")
def get_perspectives():
    """获取所有108视角（含Soul）"""
    try:
        from engine.perspective_engine import FIGURES
        return {
            "total": len(FIGURES),
            "figures": {
                fid: {
                    "name": f.name,
                    "title": f.title,
                    "category": f.category,
                    "faction": f.faction,
                    "expertise": f.expertise,
                    "primary_method": f.primary_method,
                    "catchphrase": f.catchphrase,
                    "bio": f.bio,
                    "soul": f.soul,
                    "thinking_model": {
                        "name": f.thinking_model.name,
                        "principles": f.thinking_model.principles,
                        "steps": f.thinking_model.steps,
                    },
                }
                for fid, f in FIGURES.items()
            },
        }
    except Exception as e:
        return _error_response(e)


@router.get("/api/xuanzhao")
def get_xuanzhao_perspective(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
    question: str = Query("此人命运如何？", description="问题"),
    figures: Optional[str] = Query(None, description="人物ID，逗号分隔，默认12位核心人物"),
):
    """获取玄照综合视角"""
    try:
        corrected, udm = _prepare_udm(birth, location, gender)

        # 视角推理（包含玄照）
        pe = PerspectiveEngine()
        opinions = pe.analyze(udm, question, _get_figure_ids(figures))

        # 辩论（获取玄照视角）
        de = DebateEngine()
        debate_result = de.debate(opinions, question)

        return {
            "question": question,
            "xuanzhao": debate_result.get("xuanzhao_perspective", {}),
            "participants": debate_result.get("participants", []),
            "consensus": debate_result.get("consensus", []),
            "disagreements": debate_result.get("disagreements", []),
        }

    except Exception as e:
        return _error_response(e)


@router.get("/api/xingming")
def get_xingming(
    name: str = Query(..., description="姓名，如 '张伟' 或 '欧阳明'"),
    gender: str = Query("男", description="性别: 男/女"),
    birth: Optional[str] = Query(None, description="出生时间（可选，用于八字喜用配合）"),
    location: str = Query("北京", description="出生地点（可选）"),
):
    """姓名学独立分析接口"""
    try:
        global _xingming_engine
        if _xingming_engine is None:
            _xingming_engine = XingMingEngine()

        # 分离姓和名（复姓使用统一的 COMPOUND_SURNAMES 列表，定义在 xingming_engine）
        surname = name[0]
        given_name = name[1:]
        for cs in COMPOUND_SURNAMES:
            if name.startswith(cs):
                surname = cs
                given_name = name[len(cs):]
                break

        if not given_name:
            return JSONResponse(status_code=400, content={"error": "姓名至少需要姓+一个字"})

        # 八字配合（可选）
        bazi_info = None
        if birth:
            try:
                corrected, udm = _prepare_udm(birth, location, gender)
                if udm.bazi_year:
                    xi_yong = getattr(udm, 'xi_yong', None) or {}
                    xi_shen = xi_yong.get('xi', [])
                    ji_shen = xi_yong.get('ji', [])
                    if isinstance(xi_shen, str):
                        xi_shen = [xi_shen] if xi_shen else []
                    if isinstance(ji_shen, str):
                        ji_shen = [ji_shen] if ji_shen else []
                    bazi_info = {
                        'year_zhi': getattr(udm.bazi_year, 'zhi', ''),
                        'day_master': udm.day_master or '',
                        'day_master_wuxing': udm.day_master_wuxing or '',
                        'tiaohou': udm.tiaohou or '',
                        'xi_shen': xi_shen,
                        'ji_shen': ji_shen,
                    }
            except Exception as e:
                logger.warning(f"八字信息提取失败: {e}")

        gender_str = "男" if gender in ("男", "male", "m") else "女"
        result = _xingming_engine.analyze_name(surname, given_name, gender_str, bazi_info)
        return result

    except Exception as e:
        return _error_response(e)


# ============================================================================
# /api/qiming  起名推荐接口
# B86 新接口 - 2026-07-10: 基于姓名学 + 八字喜忌推荐名
# 数据源: data/name_characters.json
# 复用: engine/xingming_engine.py:analyze_name()
# ============================================================================
import json as _json
import random as _random

_NAME_CHARS_CACHE = None
_NAME_CHARS_PATH = os.path.join(
    project_root := os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "name_characters.json",
)


def _load_name_characters() -> dict:
    """加载起名字库（带缓存）"""
    global _NAME_CHARS_CACHE
    if _NAME_CHARS_CACHE is not None:
        return _NAME_CHARS_CACHE
    try:
        with open(_NAME_CHARS_PATH, "r", encoding="utf-8") as f:
            _NAME_CHARS_CACHE = _json.load(f)
        return _NAME_CHARS_CACHE
    except Exception as e:
        logger.warning(f"字库加载失败: {e}")
        return {"characters": []}


def _filter_chars_by_style(chars: list, preference: str, gender: str) -> list:
    """按风格 + 性别筛选字库"""
    out = []
    for c in chars:
        # 性别过滤:男名只取"男/中",女名只取"女/中"
        if gender == "男" and c.get("gender") == "女":
            continue
        if gender == "女" and c.get("gender") == "男":
            continue
        # 风格过滤
        if preference == "古典" and c.get("style") == "现代":
            continue
        if preference == "现代" and c.get("style") == "古典":
            continue
        out.append(c)
    return out or chars  # 退路:返回全部


def _score_char_by_bazi(char_info: dict, xi_shen: list, ji_shen: list) -> float:
    """
    单字按八字喜忌打分（用作采样权重）。
    返回值范围 [0, 1]，越大越符合喜用神。

    规则:
      - 名字字五行 ∈ 喜用神 → 高分(1.0)
      - 我生喜用神(泄气) → 中上(0.7)
      - 名字字五行 = 忌神 → 低分(0.05)
      - 其他 → 中分(0.4)
    """
    wx = char_info.get("wuxing", "")
    if not wx:
        return 0.4
    if wx in xi_shen:
        return 1.0
    if wx in ji_shen:
        return 0.05
    sheng_map = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    if sheng_map.get(wx) in xi_shen:
        return 0.7
    return 0.4


def _weighted_pick(pool: list, weights: list, used_set: set):
    """加权随机抽取一个不重复的项"""
    avail_pairs = [(i, w) for i, w in enumerate(weights) if pool[i]["char"] not in used_set]
    if not avail_pairs:
        return None
    total = sum(w for _, w in avail_pairs)
    r = _random.random() * total
    acc = 0.0
    for idx, w in avail_pairs:
        acc += w
        if r <= acc:
            return pool[idx]
    return pool[avail_pairs[-1][0]]


def _get_xm_engine():
    """获取全局 XingMingEngine 单例"""
    global _xingming_engine
    if _xingming_engine is None:
        _xingming_engine = XingMingEngine()
    return _xingming_engine


def _candidates_for_qiming(
    surname: str,
    gender: str,
    preference: str,
    xi_shen: list,
    ji_shen: list,
    max_candidates: int = 8,
) -> list:
    """
    起名主函数：
    1. 加载字库 → 按性别/风格筛选 → 按喜忌加权
    2. 双字名采样(首字+次字按权重抽取,笔画约束)
    3. 调 XingMingEngine.analyze_name() 算五格+三才+八字配合
    4. 综合分 = 五格 40% + 三才 20% + 八字 40% → 排序返回 Top N
    """
    data = _load_name_characters()
    all_chars = data.get("characters", [])
    if not all_chars or not surname:
        return []

    char_pool = _filter_chars_by_style(all_chars, preference, gender)
    if len(char_pool) < 5:
        return []

    char_weights = [_score_char_by_bazi(c, xi_shen, ji_shen) for c in char_pool]
    engine = _get_xm_engine()

    candidates = []
    used_names = set()
    attempts = 0
    max_attempts = 60  # 控制耗时,确保 < 1s
    gender_str = gender if gender in ("男", "女") else "男"

    bazi_info = None
    if xi_shen or ji_shen:
        bazi_info = {"xi_shen": xi_shen, "ji_shen": ji_shen}

    while len(candidates) < max_candidates and attempts < max_attempts:
        attempts += 1
        first = _weighted_pick(char_pool, char_weights, used_names)
        if first is None:
            break
        second = _weighted_pick(char_pool, char_weights, {first["char"]})
        if second is None:
            continue

        given_name = first["char"] + second["char"]
        if given_name in used_names:
            continue

        # 笔画约束
        total_given_strokes = first["strokes"] + second["strokes"]
        if total_given_strokes < 4 or total_given_strokes > 32:
            continue

        used_names.add(given_name)

        try:
            result = engine.analyze_name(surname, given_name, gender_str, bazi_info)
            if result.get("error"):
                continue

            wuge = result.get("wuge", {})
            renge = wuge.get("人格", {})
            dige = wuge.get("地格", {})
            tiange = wuge.get("天格", {})
            waige = wuge.get("外格", {})
            zongge = wuge.get("总格", {})
            sancai = result.get("sancai", {})
            bazi_match = result.get("bazi_match") or {}

            # 五格分(人格 + 地格 + 总格 三者平均)
            jixiong_scores = {"大吉": 100, "吉": 88, "中吉": 78, "半吉": 68, "平": 50, "半凶": 38, "凶": 18, "大凶": 5}
            wuge_parts = [
                jixiong_scores.get(renge.get("吉凶", "平"), 50),
                jixiong_scores.get(dige.get("吉凶", "平"), 50),
                jixiong_scores.get(zongge.get("吉凶", "平"), 50),
            ]
            wuge_score = sum(wuge_parts) / 3.0
            sancai_score = jixiong_scores.get(sancai.get("吉凶", "半吉"), 50)

            # 八字配合分
            bazi_level = bazi_match.get("等级", "中") if isinstance(bazi_match, dict) else "中"
            bazi_score_map = {"吉": 90, "中": 60, "凶": 20}
            bazi_score_val = bazi_score_map.get(bazi_level, 60)

            # 综合分:五格 40% + 三才 20% + 八字 40%
            total = wuge_score * 0.40 + sancai_score * 0.20 + bazi_score_val * 0.40

            # 解释
            explanation = ""
            if isinstance(bazi_match, dict) and bazi_match.get("说明"):
                explanation = bazi_match["说明"]
            else:
                ren_wx = renge.get("五行", "")
                di_wx = dige.get("五行", "")
                if ren_wx and di_wx:
                    if bazi_level == "吉":
                        explanation = f"名字五行({ren_wx}{di_wx})与喜用神({''.join(xi_shen)})相合,有利命格"
                    elif bazi_level == "凶":
                        explanation = f"名字五行({ren_wx}{di_wx})与忌神({''.join(ji_shen) if ji_shen else '无'})有冲突"
                    else:
                        explanation = f"名字五行({ren_wx}{di_wx})与八字喜忌关系中平,中性配合"
                else:
                    explanation = "八字配合度一般,仅供参考"

            c = {
                "given_name": given_name,
                "full_name": surname + given_name,
                "score": round(total),
                "wuge": {
                    "tian": {"shu": tiange.get("画数", 0), "wuxing": tiange.get("五行", "")},
                    "ren": {"shu": renge.get("画数", 0), "wuxing": renge.get("五行", "")},
                    "di": {"shu": dige.get("画数", 0), "wuxing": dige.get("五行", "")},
                    "wai": {"shu": waige.get("画数", 0), "wuxing": waige.get("五行", "")},
                    "zong": {"shu": zongge.get("画数", 0), "wuxing": zongge.get("五行", "")},
                },
                "sancai": f"{tiange.get('五行','')}{renge.get('五行','')}{dige.get('五行','')}",
                "sancai_jixiong": sancai.get("吉凶", "半吉"),
                "bazi_match": {
                    "score": round(bazi_score_val),
                    "level": bazi_level,
                    "explanation": explanation,
                },
                "characters": [
                    {"char": first["char"], "wuxing": first["wuxing"], "shu": first["strokes"], "meaning": first["meaning"]},
                    {"char": second["char"], "wuxing": second["wuxing"], "shu": second["strokes"], "meaning": second["meaning"]},
                ],
                "total_score": round(total),
            }
            candidates.append(c)
        except Exception as e:
            logger.debug(f"分析 {surname}{given_name} 失败: {e}")
            continue

    candidates.sort(key=lambda x: x["total_score"], reverse=True)
    return candidates[:max_candidates]


@router.get("/api/qiming")
def get_qiming(
    surname: str = Query(..., description="姓氏，如 '李' 或 '欧阳'"),
    gender: str = Query("男", description="性别: 男/女"),
    birth: Optional[str] = Query(None, description="出生时间(如 2005-06-09 11:50),用于八字喜忌配合"),
    location: str = Query("北京", description="出生地点(用于八字排盘)"),
    preference: str = Query("中性", description="风格偏好: 古典/现代/中性"),
    max_results: int = Query(8, description="返回候选数量,默认 8"),
):
    """
    起名推荐接口
    - 输入: 姓氏 + 性别 + 八字时间 + 风格偏好
    - 输出: Top N 候选名(每名含五格 + 三才 + 八字配合 + 总分)
    - 复用: engine/xingming_engine.py:analyze_name()
    """
    try:
        surname = (surname or "").strip()
        if not surname:
            return JSONResponse(status_code=400, content={"error": "姓氏不能为空"})
        if not (1 <= len(surname) <= 4):
            return JSONResponse(status_code=400, content={"error": "姓氏长度需为 1-4 字(支持复姓)"})
        if not all('一' <= ch <= '鿿' for ch in surname):
            return JSONResponse(status_code=400, content={"error": "姓氏必须为汉字"})

        gender = gender if gender in ("男", "女") else "男"
        preference = preference if preference in ("古典", "现代", "中性") else "中性"
        max_results = max(1, min(int(max_results), 16))

        is_compound = surname in COMPOUND_SURNAMES

        xi_shen, ji_shen, bazi_birth, bazi_error = [], [], None, None

        if birth:
            try:
                _corrected, udm = _prepare_udm(birth, location, gender)
                if getattr(udm, 'bazi_year', None):
                    xi_yong = getattr(udm, 'xi_yong', None) or {}
                    xi_shen = xi_yong.get('xi', []) or []
                    ji_shen = xi_yong.get('ji', []) or []
                    if isinstance(xi_shen, str):
                        xi_shen = [xi_shen] if xi_shen else []
                    if isinstance(ji_shen, str):
                        ji_shen = [ji_shen] if ji_shen else []
                    bazi_birth = birth
            except Exception as e:
                bazi_error = str(e)
                logger.warning(f"八字排盘失败: {e}")

        candidates = _candidates_for_qiming(
            surname=surname,
            gender=gender,
            preference=preference,
            xi_shen=xi_shen,
            ji_shen=ji_shen,
            max_candidates=max_results,
        )

        if not candidates:
            return JSONResponse(
                status_code=200,
                content={
                    "error": "未能生成候选,可能是字库数据缺失或参数过于约束",
                    "surname": surname,
                    "is_compound": is_compound,
                    "gender": gender,
                    "preference": preference,
                    "candidates": [],
                }
            )

        return {
            "surname": surname,
            "is_compound": is_compound,
            "gender": gender,
            "preference": preference,
            "based_on": {
                "bazi_xi_yong": xi_shen,
                "bazi_ji_shen": ji_shen,
                "birth": bazi_birth,
                "bazi_error": bazi_error,
            },
            "candidates": candidates,
            "disclosure": [
                "起名基于命理符号,实际效果看教育和家庭",
                "建议结合父母直觉选择,命理只是参考",
            ],
        }

    except Exception as e:
        return _error_response(e)


@router.get("/api/score")
def get_score(
    birth: str = Query(..., description="出生时间，如 2005-06-09 11:50"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别: 男/女"),
    method: str = Query("all", description="术法名称，如 八字/紫微斗数/六爻/奇门遁甲/大六壬/太乙神数/占星，或 all 表示全部"),
):
    """评分接口：返回每个术法的评分(0-100)和白话解析"""
    try:
        cache_key = f"score:{birth}:{location}:{gender}:{method}"
        cached = _get_cache(cache_key)
        if cached:
            return cached

        corrected, udm = _prepare_udm(birth, location, gender)

        from api.score_engine import score_all
        result = score_all(udm, method)

        response = {
            "input": {
                "birth": birth,
                "location": location,
                "gender": gender,
                "method": method,
            },
            "scores": result,
        }

        _set_cache(cache_key, response)
        return response

    except Exception as e:
        return _error_response(e)


@router.get("/api/hehun")
def get_hehun(
    birth1: str = Query(..., description="第一人出生时间，如 2005-06-09 11:50"),
    location1: str = Query("北京", description="第一人出生地点"),
    gender1: str = Query("男", description="第一人性别"),
    name1: str = Query("", description="第一人姓名（可选）"),
    birth2: str = Query(..., description="第二人出生时间"),
    location2: str = Query("北京", description="第二人出生地点"),
    gender2: str = Query("女", description="第二人性别"),
    name2: str = Query("", description="第二人姓名（可选）"),
):
    """合婚分析 — 5 维度加权（钢铁侠装甲）

    维度:
      - wuxing_bu 30%   (五行互补)
      - bazi_complement 25% (八字互补)
      - dayun_sync 20%  (大运同步)
      - shensha_conflict 15% (神煞冲突)
      - ziwei_match 10% (紫微合盘)

    性能: 两次 _prepare_udm,合计 ~1.4s;自带 hehun 缓存层
    """
    t0 = time.time()
    try:
        if not birth1 or not birth2:
            return JSONResponse(status_code=400, content={"error": "请提供两人的出生时间"})

        # ── 缓存层 ──
        cache_key = _hehun_cache_key(birth1, location1, gender1, name1,
                                     birth2, location2, gender2, name2)
        cached = _get_hehun_cache(cache_key)
        if cached is not None:
            cached["_cache"] = "hit"
            cached["_elapsed_ms"] = int((time.time() - t0) * 1000)
            return cached

        # ── 两人并行排盘 ──
        corrected1, udm1 = _prepare_udm(birth1, location1, gender1)
        corrected2, udm2 = _prepare_udm(birth2, location2, gender2)

        if not udm1.bazi_year or not udm2.bazi_year:
            return JSONResponse(
                status_code=400,
                content={"error": "至少一方排盘失败,请检查出生时间"}
            )

        # ── 抽取合婚必需字段 ──
        b1 = _build_bazi_extract(udm1)
        b2 = _build_bazi_extract(udm2)

        # ── 五维度独立打分 ──
        dims = {
            "wuxing_bu": _check_wuxing_complement(b1, b2),
            "bazi_complement": _check_bazi_complement(b1, b2),
            "dayun_sync": _check_dayun_sync(b1, b2),
            "shensha_conflict": _check_shensha_conflict(b1, b2),
            "ziwei_match": _check_ziwei_match(udm1, udm2),
        }

        # ── 加权总分 ──
        total_score = int(
            dims["wuxing_bu"]["score"] * 0.30
            + dims["bazi_complement"]["score"] * 0.25
            + dims["dayun_sync"]["score"] * 0.20
            + dims["shensha_conflict"]["score"] * 0.15
            + dims["ziwei_match"]["score"] * 0.10
        )

        # ── 顶层结论 ──
        verdict_str = _hehun_verdict(total_score)
        based_on = _hehun_based_on(dims)

        response = {
            "couple_summary": {
                "score": total_score,
                "verdict": verdict_str,
                "based_on": based_on,
            },
            "dimensions": dims,
            "verdict": verdict_str,
            "warnings": _hehun_warnings(dims, b1, b2),
            "disclosure": [
                "合婚判断基于命理符号,实际关系靠双方经营",
                "所有分数是辅助参考,不是命运判决",
                "命理层冲突不代表不能化解,只是需要更早做准备",
            ],
            "behavior_verify_questions": list(_HEHUN_VERIFY_QUESTIONS),
            "person1": {
                "birth": birth1,
                "location": location1,
                "gender": gender1,
                "name": name1,
                "day_master": b1.get("day_master", ""),
                "bazi_summary": {
                    "year": b1.get("year", ""),
                    "month": b1.get("month", ""),
                    "day": b1.get("day", ""),
                    "time": b1.get("time", ""),
                },
            },
            "person2": {
                "birth": birth2,
                "location": location2,
                "gender": gender2,
                "name": name2,
                "day_master": b2.get("day_master", ""),
                "bazi_summary": {
                    "year": b2.get("year", ""),
                    "month": b2.get("month", ""),
                    "day": b2.get("day", ""),
                    "time": b2.get("time", ""),
                },
            },
            "_cache": "miss",
            "_elapsed_ms": int((time.time() - t0) * 1000),
        }

        _set_hehun_cache(cache_key, response)
        return response
    except Exception as e:
        logger.exception("hehun failed")
        return _error_response(e)


@router.get("/api/bazi/score")
def get_bazi_score(
    birth: str = Query(..., description="出生时间，如 2005-06-09 11:50"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别: 男/女"),
):
    """八字综合评分接口（五大维度，0-100分）"""
    try:
        corrected, udm = _prepare_udm(birth, location, gender)

        if not udm.bazi_year:
            return JSONResponse(status_code=400, content={"error": "无法排盘，请检查出生时间"})

        # ── 提取基础数据 ──────────────────────────────────────────
        day_master = udm.day_master or ""
        day_master_wuxing = udm.day_master_wuxing or ""
        xi_yong = getattr(udm, 'xi_yong', {}) or {}
        strength = xi_yong.get('strength', '')
        wuxing_score = udm.wuxing_score or {}
        shishen_gan = udm.shishen_gan or {}
        shishen_zhi = getattr(udm, 'shishen_zhi', {}) or {}
        changsheng = getattr(udm, 'changsheng', {}) or {}
        dayun = getattr(udm, 'dayun', []) or []
        features = udm.features or []

        pillars = {
            'year': udm.bazi_year.ganzhi or '',
            'month': udm.bazi_month.ganzhi if udm.bazi_month else '',
            'day': udm.bazi_day.ganzhi if udm.bazi_day else '',
            'time': udm.bazi_time.ganzhi if udm.bazi_time else '',
        }

        # ── 维度一：日主强弱（20分）──────────────────────────────
        strength_score_map = {
            '中和': 20,
            '身强': 15,
            '身弱': 15,
        }
        s1 = strength_score_map.get(strength, 10)

        if strength == '中和':
            s1_text = f"日主{day_master}（{day_master_wuxing}）力量均衡，属于中和之命。这种格局最为理想，不偏不倚，进退有据。整体先天条件不错。"
        elif strength == '身强':
            s1_text = f"日主{day_master}（{day_master_wuxing}）偏强，自身力量充足。好在能担财官，适合主动出击、开拓事业。但也要注意别太强势，刚过易折。"
        elif strength == '身弱':
            s1_text = f"日主{day_master}（{day_master_wuxing}）偏弱，先天力量不足。需要贵人扶持和好的环境来成就事业。建议多借助外力，不宜单打独斗。"
        else:
            s1_text = f"日主{day_master}（{day_master_wuxing}）强弱难以明确判断，格局较为特殊。建议结合具体大运流年来分析。"

        # ── 维度二：五行平衡（20分）──────────────────────────────
        # 统计得分>0的五行种类
        present_elements = [wx for wx, sc in wuxing_score.items() if sc and sc > 0]
        n_elements = len(present_elements)
        element_score_map = {5: 20, 4: 16, 3: 12, 2: 8, 1: 4}
        s2 = element_score_map.get(n_elements, 4)

        # 如果五行齐全，额外检查是否有极弱的
        zero_elements = [wx for wx in ['木', '火', '土', '金', '水'] if wuxing_score.get(wx, 0) == 0]
        if n_elements == 5 and zero_elements:
            s2 = 16  # 有五行得分为0，降分

        # 找最旺和最弱的五行
        if wuxing_score:
            sorted_wx = sorted(wuxing_score.items(), key=lambda x: x[1] or 0, reverse=True)
            strongest = sorted_wx[0][0] if sorted_wx else ''
            weakest = sorted_wx[-1][0] if sorted_wx else ''
        else:
            strongest = weakest = ''

        if n_elements == 5:
            s2_text = f"五行齐全，金木水火土皆有体现，先天格局较为圆满。"
            if strongest and weakest:
                s2_text += f"其中{strongest}最旺，{weakest}最弱，整体较为均衡。"
        elif n_elements == 4:
            missing = [wx for wx in ['木', '火', '土', '金', '水'] if not wuxing_score.get(wx)]
            s2_text = f"五行缺{''.join(missing)}，先天有某一环节偏弱。在生活中可以有意识地多接触{missing[0]}相关事物来调和，比如方位、颜色、行业等方面。"
        else:
            missing = [wx for wx in ['木', '火', '土', '金', '水'] if not wuxing_score.get(wx)]
            s2_text = f"五行缺{'、'.join(missing)}较多，命局偏于某一极端。建议通过后天环境调整来弥补，多关注所缺五行对应的领域。"

        # ── 维度三：十神配置（20分）──────────────────────────────
        # 收集所有出现的十神类型（天干+地支藏干）
        all_shishen = set()
        for v in shishen_gan.values():
            if v and v != '?':
                all_shishen.add(v)
        for v_list in shishen_zhi.values():
            if isinstance(v_list, list):
                for v in v_list:
                    if v and v != '?':
                        all_shishen.add(v)

        n_shishen = len(all_shishen)
        if n_shishen >= 6:
            s3 = 20
        elif n_shishen == 5:
            s3 = 16
        elif n_shishen == 4:
            s3 = 12
        else:
            s3 = 8

        shishen_list = sorted(all_shishen)
        if n_shishen >= 6:
            s3_text = f"十神配置丰富，出现了{n_shishen}种十神（{'、'.join(shishen_list)}）。人生面广，经历多样，能适应各种环境和角色。这是比较理想的组合。"
        elif n_shishen >= 4:
            s3_text = f"十神出现了{n_shishen}种（{'、'.join(shishen_list)}），命局有一定多样性。某些方面突出，某些方面相对薄弱，属于有侧重的格局。"
        else:
            s3_text = f"十神仅出现{n_shishen}种（{'、'.join(shishen_list)}），命局偏向单一。性格和运势比较集中，优点和缺点都会比较明显。"

        # ── 维度四：格局清纯（20分）──────────────────────────────
        # 检查日柱天干十神
        day_shishen = shishen_gan.get('day', '')

        # 高分十神（在日干位或月令位）
        low_shishen = {'七杀', '伤官', '劫财'}

        s4 = 12  # 基础分

        # 日干位十神
        if day_shishen in {'正官', '正印', '食神'}:
            s4 = 18
        elif day_shishen in {'偏印', '比肩'}:
            s4 = 15
        elif day_shishen in {'偏财', '正财'}:
            s4 = 14
        elif day_shishen in low_shishen:
            s4 = 8

        # 检查伤官见官（格局大忌）
        has_shangguan = '伤官' in all_shishen
        has_zhengguan = '正官' in all_shishen
        if has_shangguan and has_zhengguan:
            s4 = max(4, s4 - 6)

        # 检查七杀无制
        has_qisha = '七杀' in all_shishen
        has_foodie = '食神' in all_shishen  # 食神制杀
        has_zhengyin = '正印' in all_shishen  # 印化杀
        if has_qisha and not has_foodie and not has_zhengyin:
            s4 = max(4, s4 - 4)

        s4 = min(20, max(0, s4))

        if s4 >= 16:
            s4_text = f"格局较为清纯，日柱{pillars['day']}坐{day_shishen}，"
            if day_shishen in {'正官', '正印', '食神'}:
                s4_text += "属于传统好格局。行事正派，有贵气，容易获得社会认可和稳定发展。"
            else:
                s4_text += "命局组合协调，没有明显的冲克矛盾。做事比较顺遂，不易走极端。"
        elif s4 >= 10:
            s4_text = f"格局尚可，日柱{pillars['day']}坐{day_shishen}。命局有一些好的组合，但也存在一些需要注意的地方。"
            if has_shangguan and has_zhengguan:
                s4_text += "伤官与正官并见，性格中既有叛逆也有守规矩的一面，需要注意平衡。"
            if has_qisha and not has_foodie:
                s4_text += "七杀出现但缺少制化，压力和挑战会多一些，需要自己去化解。"
        else:
            s4_text = f"格局有些复杂，日柱{pillars['day']}坐{day_shishen}。"
            if has_shangguan and has_zhengguan:
                s4_text += "伤官见官，容易有是非口舌，建议行事低调，以和为贵。"
            elif has_qisha and not has_foodie and not has_zhengyin:
                s4_text += "七杀无制，人生压力较大，但逆境也出英雄，关键在于能否转化。"
            else:
                s4_text += "命局有些纠结，需要在矛盾中找到出路。好在命运总留有转机。"

        # ── 维度五：大运走势（20分）──────────────────────────────
        # 分析前5步大运的长生十二宫走势
        good_cs = {'长生', '冠带', '临官', '帝旺'}
        bad_cs = {'死', '墓', '绝'}

        s5 = 10  # 基础分
        good_ages = 0
        total_periods = min(5, len(dayun))

        dayun_details = []
        for dy in dayun[:5]:
            dy_cs = dy.get('changsheng', '')
            dy_age = dy.get('age', 0)
            dy_gz = dy.get('ganzhi', '')
            dayun_details.append({'ganzhi': dy_gz, 'changsheng': dy_cs, 'age': dy_age})
            if dy_cs in good_cs:
                good_ages += 1
            elif dy_cs in bad_cs:
                good_ages -= 1

        if total_periods > 0:
            ratio = good_ages / total_periods
            if ratio >= 0.6:
                s5 = 18
            elif ratio >= 0.4:
                s5 = 15
            elif ratio >= 0.2:
                s5 = 12
            elif ratio >= 0:
                s5 = 10
            else:
                s5 = 6

        s5 = min(20, max(0, s5))

        # 生成大运描述
        if dayun_details:
            first_dy = dayun_details[0]
            prime_dy = None
            for d in dayun_details:
                if d['age'] and 25 <= d['age'] <= 45:
                    prime_dy = d
                    break
            if not prime_dy:
                prime_dy = dayun_details[1] if len(dayun_details) > 1 else first_dy

            if s5 >= 16:
                s5_text = f"大运走势不错，早年{first_dy['ganzhi']}（{first_dy['changsheng']}），"
                if prime_dy:
                    s5_text += f"壮年{prime_dy['ganzhi']}（{prime_dy['changsheng']}）。"
                s5_text += "关键年龄段运势向上，利于事业突破和发展。整体走势呈上升或平稳趋势。"
            elif s5 >= 10:
                s5_text = f"大运走势有起有伏，早年{first_dy['ganzhi']}（{first_dy['changsheng']}），"
                if prime_dy:
                    s5_text += f"壮年{prime_dy['ganzhi']}（{prime_dy['changsheng']}）。"
                s5_text += "部分时段运势较好，部分时段需要忍耐。把握好运的阶段，低谷时蓄力即可。"
            else:
                s5_text = f"大运前期{first_dy['ganzhi']}（{first_dy['changsheng']}），"
                if prime_dy:
                    s5_text += f"壮年{prime_dy['ganzhi']}（{prime_dy['changsheng']}）。"
                s5_text += "早年运势偏弱，但命运往往先苦后甜。中年后运势有望好转，关键在于早年积累。"
        else:
            s5_text = "大运数据不足，无法详细分析走势。建议结合具体流年来判断运势起伏。"

        # ── 综合评分 ──────────────────────────────────────────
        total = s1 + s2 + s3 + s4 + s5

        # 等级映射
        if total >= 90:
            grade = "上上"
        elif total >= 80:
            grade = "上"
        elif total >= 70:
            grade = "中上"
        elif total >= 60:
            grade = "中"
        elif total >= 50:
            grade = "中下"
        else:
            grade = "下"

        # ─── 维度维度-补救建议 (低分维度 actionable advice) ───
        # 维度一: 日主强弱
        if '身弱' in strength:
            s1_advice = "身弱补救:①多结交印星旺(文化、贵人、长辈)的朋友;②从事脑力工作而非纯体力;③佩戴水晶/黑曜石等水属性饰品;④名字可加'水'旁字(如\"浩、海、涵\")补水"
        elif '身强' in strength:
            s1_advice = "身强疏导:①适合创业、开拓性工作;②多运动消耗过剩精力;③可佩戴金银饰品泄秀;④名字可加'木'旁字(如\"林、森、树\")疏导"
        else:
            s1_advice = "中和格局,顺势而为即可,无需刻意补泄"

        # 维度二: 五行平衡
        if weakest and weakest == '土':
            s2_advice = "土弱补救:①多接触黄、棕色调事物;②居住西方/西南方有利;③佩戴黄水晶、玉石;④从事房地产、建筑、农业"
        elif weakest and weakest in ('金',):
            s2_advice = "金弱补救:①西方/西北方向有利;②佩戴金属饰品;③从事金融、法律、技术工作;④秋天出生更有利"
        elif weakest and weakest in ('水',):
            s2_advice = "水弱补救:①北方有利;②佩戴黑曜石、深色饰品;③多亲近江河湖海;④从事贸易、流通业"
        elif weakest and weakest in ('木',):
            s2_advice = "木弱补救:①东方/东南方有利;②多接触绿色植物;③从事文化、教育、设计;④春天是提升期"
        elif weakest and weakest in ('火',):
            s2_advice = "火弱补救:①南方有利;②多穿红、橙色衣物;③从事文化、娱乐、餐饮;④夏天是提升期"
        else:
            s2_advice = "五行较为均衡,继续保持"

        # 维度三: 十神配置
        n_shishen = len(set(all_shishen))
        if n_shishen <= 4:
            s3_advice = "十神偏少补救:①多尝试新领域扩展人生面;②通过学习(如MBA、技能认证)增加专业标识;③命局集中反而是优势,深耕一行胜过广撒网"
        elif n_shishen >= 7:
            s3_advice = "十神丰富,可塑性极强。建议选定1-2个核心方向深耕,避免贪多嚼不烂"
        else:
            s3_advice = "十神配置中等,继续按大运流年的指引调整重点方向"

        # 维度四: 格局清纯
        if s4 <= 10:
            s4_advice = "格局较杂补救:①避免与人合伙做生意;②从事技术/手艺/自由职业更稳;③多读圣贤书(印星)化解伤官冲动;④远离是非之地,谨言慎行"
        elif s4 <= 14:
            s4_advice = "格局有些微瑕,但不致命。建议修身养性,用印星化解冲突,从事稳定行业"
        else:
            s4_advice = "格局清纯,难得的好基础,如有合适大运可大胆发挥"

        # 维度五: 大运走势
        if s5 <= 10:
            s5_advice = "大运低迷补救:①蛰伏期宜静不宜动;②读书充电、积累人脉;③健康为第一要务;④若有好的流年(食神制杀、伤官见财),可以小试牛刀"
        elif s5 <= 14:
            s5_advice = "大运平缓,稳中求进。理财保守为主,事业避免大动作,可深耕一个领域"
        else:
            s5_advice = "大运上行期,有贵人扶持。可以适度扩张、投资、学习新技能,把握机遇"

        # 综合评语
        if total >= 80:
            summary = f"此命综合评分{total}分（{grade}），先天格局优越。日主{strength}，五行{'齐全' if n_elements == 5 else '有所欠缺'}，十神配置丰富。"
            summary += "整体属于好命，关键在于能否把握大运中的机遇，顺势而为。"
        elif total >= 60:
            summary = f"此命综合评分{total}分（{grade}），先天条件中等偏上。日主{strength}，命局有一定亮点也有不足。"
            summary += "通过后天努力和环境调整，完全可以弥补先天不足，创造不错的人生。"
        else:
            summary = f"此命综合评分{total}分（{grade}），先天格局有一些挑战。日主{strength}，命局偏弱的环节较多。"
            summary += "但命理讲的是趋势而非定数，通过修身养性、择善而行，同样能走出精彩人生。"

        return {
            "total_score": total,
            "grade": grade,
            "summary": summary,
            "details": [
                {
                    "title": "日主强弱",
                    "icon": "🔥",
                    "score": s1,
                    "max": 20,
                    "text": s1_text,
                    "advice": s1_advice,
                },
                {
                    "title": "五行平衡",
                    "icon": "⚖️",
                    "score": s2,
                    "max": 20,
                    "text": s2_text,
                    "advice": s2_advice,
                },
                {
                    "title": "十神配置",
                    "icon": "🎯",
                    "score": s3,
                    "max": 20,
                    "text": s3_text,
                    "advice": s3_advice,
                },
                {
                    "title": "格局清纯",
                    "icon": "💎",
                    "score": s4,
                    "max": 20,
                    "text": s4_text,
                    "advice": s4_advice,
                },
                {
                    "title": "大运走势",
                    "icon": "📈",
                    "score": s5,
                    "max": 20,
                    "text": s5_text,
                    "advice": s5_advice,
                },
            ],
            "meta": {
                "birth": birth,
                "location": location,
                "gender": gender,
                "day_master": day_master,
                "day_master_wuxing": day_master_wuxing,
                "strength": strength,
                "pillars": pillars,
            },
        }

    except Exception as e:
        return _error_response(e)


# ============================================================
# 数学边界端点 — 8 术法的概率论边界白纸黑字
# 基于大乐透 14 公式 (2026-07-09 梧指令补充)
# ============================================================

@router.get("/api/math/boundaries")
def math_boundaries():
    """8 术法的数学边界 — 公开接口,任何调用可查

    设计目标:
    - 每个术法的样本空间 |Ω|
    - 公式 13 限制 (历史无预测优势)
    - 已知缺陷
    - 公式 11 信息熵
    """
    return {
        "formula_basis": {
            "F11_entropy": "H = -Σ p(ω) log₂ p(ω) = log₂|Ω| (等概率分布)",
            "F13_no_advantage": "P(ω_t | H_{t-1}) = P(ω_t) — 历史条件概率等于无条件概率",
            "F7_8_prize": "奖级概率 = C(35,k)·C(30,5-k)·C(12,m)·C(10,2-m) / [C(35,5)·C(12,2)]",
            "F10_return": "返奖率 = E[R] / 2 ≈ 51% — 长期盈亏由发行方决定,玩家层面无法突破",
            "F12_independence": "P(A_{t+1} | A_t) = P(A_{t+1}) — 每期开奖独立,无'复仇号'或'跟单号'",
        },
        "engines": {
            "bazi": {
                "name": "八字",
                "sample_space": "年柱约 60 × 月柱 12 × 日柱 60 × 时柱 12 = 518,400 种组合",
                "entropy_bits": 19.0,
                "F13_implication": "命盘静态结构,不对未来事件提供预测优势",
                "known_defects": [],
            },
            "ziwei": {
                "name": "紫微斗数",
                "sample_space": "12宫 × 14主星组合(约 4096) × 大限流转(每 10 年一变)",
                "entropy_bits": 12.0,
                "F13_implication": "四化飞星/自化是命盘结构描述,不构成预测",
                "known_defects": ["解释层主观性:同一命盘不同派别解释冲突"],
            },
            "astro": {
                "name": "西洋占星",
                "sample_space": "12星座 × 10行星 × 12宫位 × 相位(主要 5 种) = 复杂组合",
                "entropy_bits": 14.0,
                "F13_implication": "天文精度(pyswisseph ±1 角秒)不等于预测精度",
                "known_defects": [],
            },
            "liuyao": {
                "name": "六爻",
                "sample_space": "64卦 × 6爻 × 动爻约 3 个 × 变卦 = 约 4,096 组合",
                "entropy_bits": 12.0,
                "F13_implication": "用神选取/世应分析含主观性,不构成预测",
                "known_defects": [],
            },
            "qimen": {
                "name": "奇门遁甲",
                "sample_space": "阳遁9局 + 阴遁9局 = 18局 × 9宫 = 162 种盘式",
                "entropy_bits": 7.3,
                "F13_implication": "格局判断含主观性,不构成预测",
                "known_defects": [],
            },
            "liuren": {
                "name": "大六壬",
                "sample_space": "12天盘 × 三传取法(~6) × 12天将 = 复杂组合",
                "entropy_bits": 10.0,
                "F13_implication": "三传取法/天将解读含主观性,不构成预测",
                "known_defects": ["四课为空:某些时辰边界条件下三传取法未覆盖"],
            },
            "taiyi": {
                "name": "太乙神数",
                "sample_space": "阳遁9局 × 阴遁9局 × 16宫 = 144 种盘式",
                "entropy_bits": 7.2,
                "F13_implication": "本用于军国大事,样本空间小,个人解读主观性强",
                "known_defects": [
                    "kintaiyi 传递依赖未装齐(numpy/cn2an/taiyidict),tests 4 个失败",
                    "requirements.txt 已记录,需 pip install -r requirements.txt",
                ],
            },
            "xingming": {
                "name": "姓名学",
                "sample_space": "3500常用汉字 × 100常用姓氏 ≈ 350,000",
                "entropy_bits": 18.4,
                "F13_implication": "康熙笔画是历史选择,非 Unicode 标准;三才配置是后天解读",
                "known_defects": ["同一字不同字典笔画可能不同"],
            },
        },
        "lottery_module": {
            "F11_sample_space": {
                "fc3d": 120,         # C(10,3)
                "pl3": 120,
                "dlt": 21425712,    # C(35,5) × C(12,2)
                "ssq": 17721088,    # C(33,6) × C(16,1)
            },
            "F11_entropy_bits": {
                "fc3d": 6.91,
                "pl3": 6.91,
                "dlt": 24.35,
                "ssq": 24.08,
            },
            "F8_total_win_probability": 0.0667,
            "F10_return_rate": 0.51,
            "F10_expected_return_per_2yuan": 1.02,
            "data_quality_note": "dlt-history.csv 2026-07-09 发现 791/1000 行是重复,已去重为 210 真实期",
        },
        "白皮书": [
            "docs/lottery_math_disclosure.md",
            "每个 engine 顶部 docstring 的'数学边界'段",
        ],
        "source": "梧 2026-07-09 提供大乐透 14 公式,玄照 v2 各引擎顶部 docstring 引用本端点",
    }


# ============================================================
# /api/report — 玄照客户报告接口 (2026-07-10 梧指令)
# 把 chart + xingming 输出翻译成"人能看懂、能行动的"判断
# ============================================================
def _build_report_internal(birth: str, location: str, gender: str, name: str, question: str, use_cache: bool = True) -> dict:
    """
    报告生成的核心逻辑,被 /api/report 和 /api/report/verify 共用
    完全同步调引擎,不走 HTTP 自调用(避免单线程事件循环死锁)

    use_cache=True (默认): 先查缓存,未命中再排盘,排完写缓存
    use_cache=False: 强制重排(用于 /api/report/verify — 验证后要校准信心分,
                        缓存里的旧 report confidence 已被 verify 改过,不能再用)
    """
    from engine.report_engine import build_report
    from engine.xingming_engine import XingMingEngine, COMPOUND_SURNAMES

    name = _sanitize_name(name) if name else ""

    # 缓存查询(use_cache=False 直接跳过,verify 自己处理)
    if use_cache:
        cached = _get_cached_report(birth, location, gender, name, question)
        if cached is not None:
            logger.info(f"report cache HIT: {_report_cache_key(birth, location, gender, name, question)[:8]}")
            return cached
        logger.info(f"report cache MISS: {_report_cache_key(birth, location, gender, name, question)[:8]}")

    corrected, udm = _prepare_udm(birth, location, gender)

    # 复用 /api/chart 端的 result 构造逻辑(它已经在 _get_chart_result 之类的函数里)
    # 这里直接手动取必要字段
    chart_result = {
        "input": {"birth": birth, "location": location, "gender": gender, "name": name},
        "corrected_time": {
            "original": corrected.original.isoformat(),
            "true_solar": corrected.true_solar.isoformat(),
            "longitude": corrected.longitude,
            "latitude": corrected.latitude,
            "is_late_zi": corrected.is_late_zi,
            "diff_minutes": round((corrected.true_solar - corrected.original).total_seconds() / 60, 1),
        },
        "methods": udm.get_available_methods(),
        "errors": udm.engine_errors,
    }

    if udm.bazi_year:
        chart_result["bazi"] = {
            "year": udm.bazi_year.ganzhi or "",
            "month": udm.bazi_month.ganzhi if udm.bazi_month else "",
            "day": udm.bazi_day.ganzhi if udm.bazi_day else "",
            "time": udm.bazi_time.ganzhi if udm.bazi_time else "",
            "day_master": udm.day_master or "",
            "day_master_wuxing": udm.day_master_wuxing or "",
            "shishen": udm.shishen_gan or {},
            "shishen_gan": udm.shishen_gan or {},
            "shishen_zhi": getattr(udm, 'shishen_zhi', {}) or {},
            "hidden_gans": getattr(udm, 'hidden_gans', {}) or {},
            "nayin": udm.nayin or {},
            "features": udm.features or [],
            "tiaohou": udm.tiaohou or "",
            "wuxing_score": udm.wuxing_score or {},
            "xunkong": getattr(udm, 'xunkong', {}) or {},
            "shensha": getattr(udm, 'shensha', []) or [],
            "shensha_per_pillar": getattr(udm, 'shensha_per_pillar', {}) or {},
            "changsheng": getattr(udm, 'changsheng', {}) or {},
            "gan_relations": getattr(udm, 'gan_relations', []) or [],
            "zhi_relations": getattr(udm, 'zhi_relations', []) or [],
            "dayun": getattr(udm, 'dayun', []) or [],
            "dayun_start_age": getattr(udm, 'dayun_start_age', 0) or 0,
            "ming_gong": getattr(udm, 'ming_gong', "") or "",
            "ming_gong_shishen": getattr(udm, 'ming_gong_shishen', None) or {},
            "tai_yuan": getattr(udm, 'tai_yuan', "") or "",
            "tai_yuan_shishen": getattr(udm, 'tai_yuan_shishen', None) or {},
            "shen_gong": getattr(udm, 'shen_gong', "") or "",
            "shen_gong_shishen": getattr(udm, 'shen_gong_shishen', None) or {},
            "xi_yong": getattr(udm, 'xi_yong', {}) or {},
            "strength": (getattr(udm, 'xi_yong', None) or {}).get("strength", ""),
            "wuxing_summary": (getattr(udm, 'xi_yong', None) or {}).get("reason", ""),
            "liunian": getattr(udm, 'liunian', None),
            "location": getattr(udm, 'location', None),
            "geju": _analyze_geju(udm),
            "dayun_summary": _summarize_dayun(udm),
            "shensha_grouped": _group_shensha(udm),
            "kongwang_table": _build_kongwang_table(udm),
            "true_solar_diff": _true_solar_diff(udm),
            "taiji_table": _build_taiji_table(udm),
            "wenchang_table": _build_wenchang_table(udm),
            "taohua_table": _build_taohua_table(udm),
            "yima_table": _build_yima_table(udm),
            "huagai_table": _build_huagai_table(udm),
            "tianyi_table": _build_tianyi_table(udm),
            "shensha_summary": _summarize_shensha(udm),
            "tiangan_xiangke": _call_bazi_analyzer("analyze_tian_gan_di_zhi_xiang_ke", udm),
            "changsheng_distribution": _call_bazi_analyzer("analyze_deities_in_pillars", udm),
            "jieqi_lord": _call_bazi_analyzer("analyze_jieqi_lord", udm),
            "yueling_strength": _call_bazi_analyzer("analyze_yue_ling_strength", udm),
            "ganzhi_combinations": _call_bazi_analyzer("analyze_gan_zhi_combinations", udm),
            "ten_gods_distribution": _call_bazi_analyzer("analyze_ten_gods_distribution", udm),
            "career_tendency": _call_bazi_analyzer("analyze_career_tendency", udm),
            "relationship_indicator": _call_bazi_analyzer("analyze_relationship_indicator", udm),
            "health_indicator": _call_bazi_analyzer("analyze_health_indicator", udm),
            "wealth_pattern": _call_bazi_analyzer("analyze_wealth_pattern", udm),
        }

    if udm.ziwei_chart:
        chart_result["ziwei"] = udm.ziwei_chart
    if udm.astro_chart:
        chart_result["astro"] = udm.astro_chart
    if udm.liuyao_chart:
        chart_result["liuyao"] = udm.liuyao_chart
    if udm.qimen_chart:
        chart_result["qimen"] = udm.qimen_chart
    if udm.liuren_chart:
        chart_result["liuren"] = udm.liuren_chart
    if udm.taiyi_chart:
        chart_result["taiyi"] = udm.taiyi_chart

    # 手动补 current_dayun_focus (enrich_chart_result 里的 bug 没修)
    try:
        dayun_list = chart_result.get("bazi", {}).get("dayun", [])
        current_dayun = next((d for d in dayun_list if d.get("is_current")), None)
        if current_dayun:
            chart_result["current_dayun_focus"] = (
                f"现在走 {current_dayun.get('ganzhi', '')} 大运"
                f"({current_dayun.get('shishen_gan', '')})— "
                f"{current_dayun.get('shishen_gan_desc', '')}"
            )
    except Exception:
        pass

    # 姓名学
    xm_result = None
    if name and len(name) >= 2:
        try:
            global _xingming_engine
            if _xingming_engine is None:
                _xingming_engine = XingMingEngine()
            surname = name[0]
            given_name = name[1:]
            for cs in COMPOUND_SURNAMES:
                if name.startswith(cs):
                    surname = cs
                    given_name = name[len(cs):]
                    break
            if given_name:
                gender_str = "男" if gender in ("男", "male", "m") else "女"
                xi_yong = getattr(udm, 'xi_yong', None) or {}
                bazi_info = {
                    'year_zhi': getattr(udm.bazi_year, 'zhi', ''),
                    'day_master': udm.day_master or '',
                    'day_master_wuxing': udm.day_master_wuxing or '',
                    'tiaohou': udm.tiaohou or '',
                    'ri_zhu': udm.bazi_day.ganzhi if udm.bazi_day else '',
                    'xi_shen': xi_yong.get('xi', []) if isinstance(xi_yong.get('xi'), list) else [xi_yong.get('xi')] if xi_yong.get('xi') else [],
                    'ji_shen': xi_yong.get('ji', []) if isinstance(xi_yong.get('ji'), list) else [xi_yong.get('ji')] if xi_yong.get('ji') else [],
                }
                xm_result = _xingming_engine.analyze_name(surname, given_name, gender_str, bazi_info)
        except Exception as e:
            logger.warning(f"姓名学失败: {e}")
            xm_result = {"error": str(e)}

    # 接入 108 视角辩论数据(2026-07-10 梧指令)
    # 2026-07-10 改为 per-topic: 每个维度跑一次辩论,产出按 topic 切片
    # 失败/超时 → 静默跳过,build_report 内部已做容错
    source_dispatch = None
    try:
        pe = PerspectiveEngine()
        de = DebateEngine()

        # 6 个 topic + 每个 topic 的小问题(切得更细,关键词能命中)
        topic_questions = [
            ("性格", "此人性格气质如何?核心在于日主性格底色。"),
            ("事业", "此人事业方向、工作运、职场发展如何?"),
            ("健康", "此人身体健康状况、亚健康倾向、需要注意的部位?"),
            ("感情", "此人感情运、桃花、婚姻缘分、配偶特质如何?"),
            ("财运", "此人财运、求财方式、收入稳定性如何?"),
            ("学业", "此人学业发展、考试运、文理科方向、读书机缘如何?"),
        ]

        per_topic = {}
        for topic, sub_q in topic_questions:
            try:
                opinions = pe.analyze(udm, sub_q, _get_figure_ids(None))
                debate_result = de.debate(opinions, sub_q)
                per_topic[topic] = {
                    "consensus":     debate_result.get("consensus", []),
                    "disagreements": debate_result.get("disagreements", []),
                    "participants":  debate_result.get("participants", []),
                    "xuanzhao":      debate_result.get("xuanzhao_perspective", {}),
                }
            except Exception as inner_e:
                logger.warning(f"辩论[{topic}] 失败: {inner_e}")
                continue

        if per_topic:
            source_dispatch = per_topic
            total_participants = sum(len(v.get("participants", [])) for v in per_topic.values())
            logger.info(f"辩论数据接入成功(per-topic): {len(per_topic)} 维度, 共 {total_participants} 人次")
    except Exception as e:
        logger.warning(f"辩论数据接入失败,跳过 debate 字段: {e}")
        source_dispatch = None

    report = build_report(chart_result, xm_result, question, source_dispatch=source_dispatch)

    # 写缓存(use_cache=True 时才写)
    if use_cache:
        _set_cached_report(birth, location, gender, name, question, report)

    return report


@router.get("/api/report/pdf")
def get_report_pdf(
    birth: str = Query(..., description="出生时间，如 2001-07-07 11:30"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别: 男/女"),
    name: str = Query("", description="姓名（可选，但强烈建议填，用于姓名学）"),
    question: str = Query("此人命运如何？", description="客户原始问题"),
):
    """
    玄照客户报告 PDF 导出

    复用 _build_report_internal() 拿到完整 JSON,
    通过 Playwright 把 HTML 渲染成 PDF 流式返回。
    """
    try:
        from api.report_pdf import generate_pdf, make_filename

        report = _build_report_internal(birth, location, gender, name, question)

        pdf_bytes = generate_pdf(report, name_safe=name)

        filename = make_filename(name)
        # ASCII fallback — 浏览器对 latin-1 头部不友好的 fallback
        # 保留中文 UTF-8 编码在 filename* 里,Chrome/Firefox 都认
        try:
            name_ascii = name.encode("ascii").decode("ascii")
        except (UnicodeEncodeError, UnicodeDecodeError):
            name_ascii = "unnamed"
        name_ascii = re.sub(r'[^\w\-.]', '_', name_ascii) or "unnamed"
        filename_ascii = f"xuanzhao_report_{name_ascii}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename_ascii}"; '
                    f"filename*=UTF-8''{urllib.parse.quote(filename)}"
                ),
                "Content-Length": str(len(pdf_bytes)),
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )
    except Exception as e:
        logger.error(f"PDF 导出失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"PDF 导出失败: {str(e)}", "type": type(e).__name__},
        )


@router.get("/api/report")
def get_report(
    birth: str = Query(..., description="出生时间，如 2001-07-07 11:30"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别: 男/女"),
    name: str = Query("", description="姓名（可选，但强烈建议填，用于姓名学）"),
    question: str = Query("此人命运如何？", description="客户原始问题"),
    no_cache: bool = Query(False, description="跳过缓存强制重排(默认 false,使用缓存)"),
):
    """
    玄照客户报告接口

    设计:每个维度 = 1 句判断 + 证据 + 行动 + 反向案例 + 诚实声明

    缓存策略 (2026-07-10 梧指令):
    - 默认 use_cache=True,key=md5(birth|location|gender|name|question),TTL 600s,LRU 100
    - ?no_cache=true 强制重排(排盘数据更新 / 调试时用)
    """
    try:
        report = _build_report_internal(birth, location, gender, name, question, use_cache=not no_cache)
        return report
    except Exception as e:
        logger.error(f"report 生成失败: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e), "trace": str(e.__class__.__name__)})


# ============================================================
# /api/cache/stats — 缓存命中率查看 (2026-07-10 梧指令)
# 监控 /api/report 的缓存效果:命中率/淘汰数/过期数
# ============================================================
@router.get("/api/cache/stats")
def get_cache_stats():
    """查看 /api/report 缓存命中情况(运维/调试用)"""
    hits = _report_cache_stats["hits"]
    misses = _report_cache_stats["misses"]
    total = hits + misses
    hit_rate = round(hits / total * 100, 2) if total > 0 else 0.0
    return {
        "hits": hits,
        "misses": misses,
        "hit_rate_pct": hit_rate,
        "evicted": _report_cache_stats["evictions"],
        "expired": _report_cache_stats["expirations"],
        "total_requests": total,
        "current_size": len(_report_cache),
        "max_size": _REPORT_CACHE_MAX,
        "ttl_seconds": _REPORT_CACHE_TTL,
    }


# ============================================================
# /api/report/monthly — 流月精细化接口 (2026-07-10 梧指令)
# 玄照当前报告是粗粒度(大运/流年),细化到流月(每月能量)
# 输入: birth, location, gender, name, question, year(默认今年), month(默认本月)
# 输出: 从指定 month 起未来 12 个月,每月一个流月对象
# ============================================================

# 月柱边界参考表 (用于 confidence 评分与判断稳定性)
# 节气切换日:立春(2/4)、惊蛰(3/6)、清明(4/5)、立夏(5/6)、芒种(6/6)、
# 小暑(7/7)、立秋(8/7)、白露(9/8)、寒露(10/8)、立冬(11/7)、大雪(12/7)、小寒(1/6)
# Solar.fromYmdHms 内部已按节气正确处理月柱

def _generate_monthly_list(birth: str, location: str, gender: str, year: int, start_month: int) -> list:
    """
    生成未来 12 个月的流月数据。
    返回 list[dict],每项含 month, ganzhi, shishen_gan, shishen_zhi, liunian, dayun_at_month,
    metadata 等。
    """
    from lunar_python import Solar
    from engine.bazi_engine import (
        SHISHEN_MAP as _BE_SHISHEN,
        NAYIN_TABLE as _BE_NAYIN,
        TRADITIONAL_HIDE_GAN as _BE_HIDE_GAN,
        XUNKONG_MAP as _BE_XUNKONG,
        CHANGSHENG_ORDER as _BE_CS_ORDER,
        CHANGSHENG_START as _BE_CS_START,
        DI_ZHI as _BE_DI_ZHI,
    )

    # 1) 排盘
    corrected, udm = _prepare_udm(birth, location, gender)
    if not udm.bazi_year or not udm.bazi_day:
        raise ValueError("八字排盘失败,无法生成流月")

    day_master = udm.day_master or ""
    day_gz = udm.bazi_day.ganzhi or ""
    dayun_list = getattr(udm, "dayun", []) or []
    xunkong_zhis = set(_BE_XUNKONG.get(day_gz, "") or "")

    # 2) 12 个月迭代
    results = []
    for i in range(12):
        ym_total = (start_month - 1) + i
        y = year + (ym_total // 12)
        m = (ym_total % 12) + 1
        # 取当月 15 日作为代表点(避开节气切换边界,稳定性好)
        s = Solar.fromYmdHms(y, m, 15, 12, 0, 0)
        l = s.getLunar()
        ec_year = l.getYear()
        ec_gz = l.getYearInGanZhi()
        ec_g = l.getYearGan()
        ec_m_gz = l.getMonthInGanZhi()
        ec_m_g = l.getMonthGan()
        ec_m_z = l.getMonthZhi()

        # 3) 十神计算
        shishen_gan = _BE_SHISHEN.get((day_master, ec_m_g), "?")
        # 地支藏干十神(传统排序)
        hidden_raw = _BE_HIDE_GAN.get(ec_m_z, "")
        hidden_gans = list(hidden_raw)
        shishen_zhi = [_BE_SHISHEN.get((day_master, h), "?") for h in hidden_gans]

        # 4) 纳音 + 长生(月柱地支的长生十二宫位)
        nayin = _BE_NAYIN.get(ec_m_gz, "")
        changsheng = ""
        try:
            start = _BE_CS_START.get(day_master)
            if start and ec_m_z in _BE_DI_ZHI:
                start_idx = _BE_DI_ZHI.index(start)
                zhi_idx = _BE_DI_ZHI.index(ec_m_z)
                is_yang = day_master in '甲丙戊庚壬'
                offset = (zhi_idx - start_idx) % 12 if is_yang else (start_idx - zhi_idx) % 12
                changsheng = _BE_CS_ORDER[offset]
        except Exception:
            changsheng = ""
        in_xunkong = ec_m_z in xunkong_zhis

        # 5) 找对应大运(用绝对年份)
        dayun_at_month = None
        for d in dayun_list:
            sy = d.get("start_year", 0) or 0
            ey = d.get("end_year", 0) or 0
            if sy <= y <= ey:
                dayun_at_month = {
                    "ganzhi": d.get("ganzhi", ""),
                    "shishen_gan": d.get("shishen_gan", ""),
                    "changsheng": d.get("changsheng", ""),
                    "is_current": d.get("is_current", False),
                }
                break

        # 6) 启发式评分 — base=50,按符号加减,完整贡献分解
        # 吉十神:正官/正印/食神/正财 (+12)
        # 凶十神:七杀/伤官/劫财/偏印 (-12)
        # 月支六合日支 (+8) / 月支六冲日支 (-10)
        # 月支空亡 (-8)
        # 大运长生位吉 (长生/冠带/临官/帝旺) (+6) / 凶 (死/墓/绝) (-6)
        auspicious_ss = {"正官", "正印", "食神", "正财"}
        inauspicious_ss = {"七杀", "伤官", "劫财", "偏印"}
        # 月支关系
        day_zhi = (udm.bazi_day.zhi or "") if udm.bazi_day else ""
        from engine.udm import ZHI_LIUHE, ZHI_CHONG
        is_liuhe = bool(day_zhi and ZHI_LIUHE.get(day_zhi) == ec_m_z)
        is_chong = bool(day_zhi and ZHI_CHONG.get(day_zhi) == ec_m_z)

        base = 50
        shishen_gan_bonus = 12 if shishen_gan in auspicious_ss else 0
        shishen_gan_penalty = -12 if shishen_gan in inauspicious_ss else 0
        zhi_relation_bonus = 8 if is_liuhe else 0
        zhi_relation_penalty = -10 if is_chong else 0
        xunkong_penalty = -8 if in_xunkong else 0
        changsheng_bonus = 0
        changsheng_penalty = 0
        if dayun_at_month and dayun_at_month.get("changsheng") in {"长生", "冠带", "临官", "帝旺"}:
            changsheng_bonus = 6
        elif dayun_at_month and dayun_at_month.get("changsheng") in {"死", "墓", "绝"}:
            changsheng_penalty = -6

        raw_score = (base
                     + shishen_gan_bonus
                     + shishen_gan_penalty
                     + zhi_relation_bonus
                     + zhi_relation_penalty
                     + xunkong_penalty
                     + changsheng_bonus
                     + changsheng_penalty)
        score = max(0, min(100, raw_score))

        # 评分本身的信心 — 启发式评分本质上是 low confidence
        if is_chong or in_xunkong:
            score_confidence = "low"
        elif dayun_at_month and dayun_at_month.get("is_current") and shishen_gan in auspicious_ss:
            score_confidence = "medium"
        else:
            score_confidence = "low"

        # monthly_score_breakdown — 把每项贡献摊开给客户看
        monthly_score_breakdown = {
            "base": base,
            "shishen_gan_bonus": shishen_gan_bonus,
            "shishen_gan_penalty": shishen_gan_penalty,
            "zhi_relation_bonus": zhi_relation_bonus,
            "zhi_relation_penalty": zhi_relation_penalty,
            "xunkong_penalty": xunkong_penalty,
            "changsheng_bonus": changsheng_bonus,
            "changsheng_penalty": changsheng_penalty,
            "final_score": score,
            "is_heuristic": True,
            "confidence": score_confidence,
            "note": (
                "本评分为启发式评分,基于十神符号+月支关系+空亡+长生位的简单加减,"
                "不构成对实际吉凶的精确预测。具体应事以流月实际触发的事件为准。"
            ),
        }

        if score >= 65:
            judgment_label = "吉"
        elif score <= 40:
            judgment_label = "凶"
        else:
            judgment_label = "平"

        # 7) 1-2 句总结
        if judgment_label == "吉":
            judgment = f"{ec_m_gz}月{shishen_gan}透干,主事明朗、行动有贵人,宜主动出击。"
        elif judgment_label == "凶":
            judgment = f"{ec_m_gz}月{shishen_gan}干扰较大,事多阻滞,宜守不宜攻。"
        else:
            judgment = f"{ec_m_gz}月{shishen_gan},能量平稳,顺势而为即可。"

        # 8) key_actions (3 条,基于十神类型)
        actions = []
        if shishen_gan in {"正官", "七杀"}:
            actions = ["承接上级交代的任务", "签合同/走流程", "注意职场人际关系,避免硬顶"]
        elif shishen_gan in {"正印", "偏印"}:
            actions = ["读书/学习/考证", "向长辈请教", "调整作息,养精蓄锐"]
        elif shishen_gan in {"食神", "伤官"}:
            actions = ["输出作品/表达观点", "做创意类工作", "注意言行分寸,伤官月忌与人争锋"]
        elif shishen_gan in {"正财", "偏财"}:
            actions = ["谈钱/收账/做投资决策", "拓展收入来源", "控制支出,防破财"]
        elif shishen_gan in {"比肩", "劫财"}:
            actions = ["独立完成关键任务", "避免合伙大额投入", "锻炼身体,补充能量"]
        else:
            actions = ["顺势而为", "观察趋势", "做日常事务"]

        # 9) warnings (1 条)
        if is_chong:
            warnings = [f"月支{ec_m_z}冲日支{day_zhi},婚姻宫/健康宫易动,谨慎处理亲密关系和体检"]
        elif shishen_gan == "七杀":
            warnings = ["七杀透干,压力骤增,谨防小人暗算或意外伤害"]
        elif shishen_gan == "伤官":
            warnings = ["伤官月易得罪人,言语锋芒过露招祸,谨言慎行"]
        elif in_xunkong:
            warnings = [f"月支{ec_m_z}落入空亡,事情有头无尾,不宜启动大项目"]
        elif shishen_gan == "偏印":
            warnings = ["偏印夺食,想法多变易分心,坚持一个方向"]
        else:
            warnings = ["保持平稳心态,留意身体信号"]

        # 10) confidence
        # 月中取样稳定度 + 大运契合度 + 流年同向 → 80
        # 中等 → 60
        # 月支冲日支或空亡 → 40
        if is_chong or in_xunkong:
            confidence = 50
        elif dayun_at_month and dayun_at_month.get("is_current"):
            confidence = 70
        else:
            confidence = 60

        # 11) based_on — 显式标明评分是启发式
        based_on = [
            "八字流月",
            "大运",
            "流年交互",
            "⚠️ monthly_score 为启发式评分,基于十神符号 + 月支关系 + 空亡 + 长生位,非精确预测。",
        ]
        if is_liuhe:
            based_on.append("月支六合日支")
        if is_chong:
            based_on.append("月支六冲日支")
        if in_xunkong:
            based_on.append("六甲空亡")

        results.append({
            "month": f"{y}-{m:02d}",
            "ganzhi": ec_m_gz,
            "shishen_gan": shishen_gan,
            "shishen_zhi": shishen_zhi,
            "hidden_gans": hidden_gans,
            "liunian_year": {"ganzhi": ec_gz, "year": ec_year},
            "dayun_at_month": dayun_at_month,
            "nayin": nayin,
            "changsheng": changsheng,
            "in_xunkong": in_xunkong,
            "zhi_relation_to_day": (
                "六合" if is_liuhe else
                "六冲" if is_chong else
                "无特殊关系"
            ),
            "monthly_judgment": judgment,
            "monthly_label": judgment_label,
            "monthly_score": score,
            "monthly_score_breakdown": monthly_score_breakdown,
            "key_actions": actions,
            "warnings": warnings,
            "confidence": confidence,
            "based_on": based_on,
        })

    return results


@router.get("/api/report/monthly")
def get_report_monthly(
    birth: str = Query(..., description="出生时间，如 2001-07-07 11:30"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别: 男/女"),
    name: str = Query("", description="姓名（可选）"),
    question: str = Query("此人命运如何？", description="客户原始问题"),
    year: int = Query(0, description="起始年(可选，默认今年)"),
    month: int = Query(0, description="起始月(可选，1-12，默认本月)"),
):
    """
    流月精细化报告接口

    返回从指定 month 起未来 12 个月的流月数据。
    如果 year/month 不传,默认从本月(系统时间)开始。
    """
    try:
        # 1) 默认值:本月
        now = datetime.now()
        if year <= 0:
            year = now.year
        if month <= 0 or month > 12:
            month = now.month

        # 2) 调用核心生成
        monthly_list = _generate_monthly_list(birth, location, gender, year, month)

        # 3) 元数据 + 流月启发式评分 disclosure
        return {
            "input": {
                "birth": birth,
                "location": location,
                "gender": gender,
                "name": name,
                "question": question,
                "start_year": year,
                "start_month": month,
            },
            "monthly": monthly_list,
            "count": len(monthly_list),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "based_on": ["八字流月", "大运", "流年交互"],
            "note": "流月按节气切换,非公历1号。本接口取每月15日为采样点计算月柱。",
            "disclosure": [
                "流月评分是启发式算法,基于十神符号加减,非精确数学预测",
                "评分仅供方向性参考,具体吉凶以当时实际情况为准",
                "建议把月度判断当作'提醒'而不是'预言'",
            ],
        }
    except Exception as e:
        logger.error(f"monthly report 失败: {e}", exc_info=True)
        return _error_response(e)


@router.get("/api/report/monthly/calibration")
def monthly_calibration():
    """
    流月评分校准状态 (2026-07-11 梧指令)

    不传参数 — 读 data/feedback.jsonl,统计与流月相关的反馈准确率
    返回: "评分校准状态:暂无数据" 或 "有 N 条反馈,准确率 X%"
    """
    try:
        from pathlib import Path as _Path

        feedback_path = _Path("data/feedback.jsonl")
        if not feedback_path.exists():
            return {
                "status": "暂无数据",
                "message": "评分校准状态:暂无数据(data/feedback.jsonl 不存在)",
                "feedback_count": 0,
                "accurate_count": 0,
                "accuracy": None,
            }

        # 读 feedback.jsonl,统计跟流月相关的反馈
        # 匹配规则:feedback.comment 包含"月"/"流月"/月份名,或者 feedback.topic 包含"月"
        relevant_count = 0
        accurate_count = 0
        try:
            with feedback_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = _json.loads(line)
                    except Exception:
                        continue
                    topic = (rec.get("topic") or "").strip()
                    comment = (rec.get("comment") or "").strip()
                    # 流月相关:topic 或 comment 里有"月"
                    is_monthly = (
                        "月" in topic
                        or "流月" in comment
                        or "月份" in comment
                        or any(f"{n}月" in comment for n in range(1, 13))
                    )
                    if not is_monthly:
                        continue
                    relevant_count += 1
                    if (rec.get("rating") or "").lower() == "accurate":
                        accurate_count += 1
        except Exception as e:
            logger.error(f"读 feedback.jsonl 失败: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"读 feedback.jsonl 失败: {e}",
                "feedback_count": 0,
                "accurate_count": 0,
                "accuracy": None,
            }

        if relevant_count == 0:
            return {
                "status": "暂无数据",
                "message": "评分校准状态:暂无数据(尚无与流月相关的反馈)",
                "feedback_count": 0,
                "accurate_count": 0,
                "accuracy": None,
            }

        accuracy = round(accurate_count / relevant_count * 100, 1)
        return {
            "status": "有数据",
            "message": f"评分校准状态:有 {relevant_count} 条反馈,准确率 {accuracy}%",
            "feedback_count": relevant_count,
            "accurate_count": accurate_count,
            "accuracy": accuracy,
            "is_heuristic": True,
            "note": "准确率基于用户主动标记的 rating 字段,样本量小时参考价值有限",
        }
    except Exception as e:
        logger.error(f"monthly calibration 失败: {e}", exc_info=True)
        return _error_response(e)


# ============================================================
# /api/report/verify — 行为验证追问接口
# 接收客户对验证问题的回答,校准信心分
# 2026-07-10 梧指令:不让玄照只靠命理符号判断
# ============================================================
@router.post("/api/report/verify")
async def report_verify(payload: dict):
    """
    body: {
      birth, location, gender, name, question,
      answers: {qid: value, ...}
    }
    returns: 校准后的完整 report
    """
    try:
        birth = payload.get("birth")
        location = payload.get("location", "北京")
        gender = payload.get("gender", "男")
        name = payload.get("name", "")
        question = payload.get("question", "此人命运如何？")
        answers = payload.get("answers", {})

        if not birth:
            return JSONResponse(status_code=400, content={"error": "birth 不能为空"})

        # verify 不走缓存 — 缓存里的 confidence 已被 verify 改过,再用就死锁;
        # 而且 verify 的语义就是"基于本次回答重新评估",命中缓存等于绕过验证逻辑
        report = _build_report_internal(birth, location, gender, name, question, use_cache=False)

        # 校准每个维度
        from engine.verify_questions import calibrate_confidence
        for section in report.get("sections", []):
            calibrate_confidence(section, answers)

        # 重算 overall
        confs = [s.get("confidence", 0) for s in report.get("sections", [])]
        if confs:
            report["confidence_overall"] = int(sum(confs) / len(confs))

        # 重新应用可见性规则(因为 calibrate_confidence 改了 confidence)
        # 梧 2026-07-10:信心低的维度折叠/隐藏,要让 verify 后也生效
        from engine.report_engine import apply_visibility
        hidden_count, collapsed_count = apply_visibility(report.get("sections", []))
        if hidden_count > 0 or collapsed_count > 0:
            # 追加披露行(已经存在的 disclosures 不变)
            existing = list(report.get("disclosures", []))
            if hidden_count > 0:
                existing.append(
                    f"⚠️ {hidden_count} 个维度信心过低(<20),已隐藏不显示 — 命理信号不足,不做无把握判断"
                )
            if collapsed_count > 0:
                existing.append(
                    f"⚠️ {collapsed_count} 个维度信心偏低(<35),默认折叠 — 需客户主动展开查看"
                )
            report["disclosures"] = existing

        report["verify_pending"] = False
        report["verify_answers"] = answers

        return report

    except Exception as e:
        logger.error(f"verify 失败: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================
# /api/feedback — 客户反馈(准/部分准/不准)
# 存 JSONL 文件,先不接 DB
# ============================================================
FEEDBACK_FILE = Path(__file__).resolve().parent.parent / "data" / "feedback.jsonl"


@router.post("/api/feedback")
async def save_feedback(payload: dict):
    """
    body: {
      topic: "事业",
      birth, location, gender, name,
      rating: "accurate" | "partial" | "inaccurate",
      comment: "可选,客户反馈"
    }
    """
    try:
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "topic": payload.get("topic", ""),
            "birth": payload.get("birth", ""),
            "location": payload.get("location", ""),
            "gender": payload.get("gender", ""),
            "name": payload.get("name", ""),
            "rating": payload.get("rating", ""),
            "comment": payload.get("comment", ""),
        }
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(_json.dumps(record, ensure_ascii=False) + "\n")
        return {"ok": True, "saved": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================
# /api/zrili — 黄道择日 (2026-07-10 梧指令)
# 用途: 给"哪天签合同/搬家/结婚"打分推荐
# 输入: event, date_range_start/end, birth (推命盘)
# 输出: top 5 推荐日期 + 干支 + 评分 + reasons + best_hour + avoid
# ============================================================

# 神煞查表(硬编码常量)
_ZRILI_TIANYI = {
    "甲": ["丑", "未"], "戊": ["丑", "未"], "庚": ["丑", "未"],
    "乙": ["子", "申"], "己": ["子", "申"],
    "丙": ["亥", "酉"], "丁": ["亥", "酉"],
    "辛": ["午", "寅"],
    "壬": ["卯", "巳"], "癸": ["卯", "巳"],
}
_ZRILI_WENCHANG = {
    "甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申",
    "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯",
}
# 时辰-干支 + 五行
_ZRILI_HOURS = [
    (0, 1, "子", "癸", "水"), (1, 3, "丑", "己", "土"),
    (3, 5, "寅", "甲", "木"), (5, 7, "卯", "乙", "木"),
    (7, 9, "辰", "戊", "土"), (9, 11, "巳", "丙", "火"),
    (11, 13, "午", "丁", "火"), (13, 15, "未", "己", "土"),
    (15, 17, "申", "庚", "金"), (17, 19, "酉", "辛", "金"),
    (19, 21, "戌", "戊", "土"), (21, 23, "亥", "壬", "水"),
]
# 事件偏好五行(签合同->金/财, 搬家->土/火, 结婚->水/木, 开业->火/木, 出行->木, 看病->水)
_ZRILI_EVENT_PREF = {
    "签合同": {"金", "土"}, "合同": {"金", "土"},
    "搬家": {"火", "土"}, "入宅": {"火", "土"},
    "结婚": {"水", "木"}, "嫁娶": {"水", "木"},
    "开业": {"火", "木"}, "开张": {"火", "木"},
    "出行": {"木", "水"}, "动身": {"木", "水"},
    "看病": {"水", "金"}, "就医": {"水", "金"},
    "签约": {"金", "土"},
}


def _zrili_shishen(day_master: str, target_gan: str) -> str:
    """基于 SHISHEN_MAP 查十神"""
    from engine.udm import SHISHEN_MAP
    return SHISHEN_MAP.get((day_master, target_gan), "?")


def _zrili_zhi_relations(z1: str, z2: str) -> dict:
    """两个地支的关系: 六合/三合/六冲/三会"""
    from engine.udm import ZHI_LIUHE, ZHI_CHONG, ZHI_SANHE, ZHI_SANHUI
    relations = {}
    if z1 == z2:
        return relations  # 同支不参与合冲判定
    if ZHI_LIUHE.get(z1) == z2:
        relations["liuhe"] = True
    if ZHI_CHONG.get(z1) == z2:
        relations["chong"] = True
    for bureau in ZHI_SANHE:
        if z1 in bureau and z2 in bureau:
            relations["sanhe"] = list(bureau - {z1, z2})
            break
    for bureau in ZHI_SANHUI:
        if z1 in bureau and z2 in bureau:
            relations["sanhui"] = list(bureau - {z1, z2})
            break
    return relations


def _zrili_gan_wuxing(gan: str) -> str:
    """天干 -> 五行"""
    from engine.udm import GAN_WUXING
    wx = GAN_WUXING.get(gan)
    if wx and hasattr(wx[0], "value"):
        return wx[0].value
    return ""


def _zrili_zhi_wuxing(zhi: str) -> str:
    """地支 -> 五行"""
    from engine.udm import ZHI_WUXING
    wx = ZHI_WUXING.get(zhi)
    if wx and hasattr(wx[0], "value"):
        return wx[0].value
    return ""


def _zrili_best_hour(client_xi: list, client_day_master: str) -> dict:
    """
    为客户推荐最佳时辰 — 时辰干五行属喜用, 且不与日柱冲/合破
    """
    from engine.udm import ZHI_LIUHE, ZHI_CHONG
    best = None
    best_score = -999
    for start_h, end_h, zhi, gan, wx in _ZRILI_HOURS:
        score = 0
        # 1. 喜用神 +15
        if wx in client_xi:
            score += 15
        # 2. 十神是日主所喜 (食神/正财/正印) +8
        ss = _zrili_shishen(client_day_master, gan)
        if ss in ("食神", "正财", "正印", "偏财"):
            score += 8
        # 3. 避开冲日柱时辰(查日柱支未知; 这里只查不冲子/午等常见)
        #    简化: 冲害时辰不碰 — 但这里没拿到具体日柱,跳过
        if score > best_score:
            best_score = score
            best = {"start": start_h, "end": end_h, "zhi": zhi, "gan": gan, "wx": wx, "score": score}
    return best or {"start": 15, "end": 17, "zhi": "申", "gan": "庚", "wx": "金", "score": 0}


def _zrili_score_day(client_xi: list, client_ji: list, client_day_master: str,
                     client_day_zhi: str, day_gan: str, day_zhi: str) -> dict:
    """
    评分单个日期与客户的契合度,返回 {score, reasons, matches}
    评分细则:
      基础 50
      日干是客户喜用神五行 -> +20
      日干是客户忌神五行   -> -20 (会另外单独标记)
      日支六合客户日支     -> +15
      日支三合客户日支     -> +10
      日支六冲客户日支     -> -25
      天乙贵人 在日支      -> +10
      文昌   在日支         -> +6
      凶煞(岁破/劫煞)命中   -> -15 (简化版)
    """
    score = 50
    reasons = []
    matches = {"xishen": False, "jishen": False, "chong": False, "liuhe": False, "sanhe": False, "tianyi": False}

    # 1. 日干五行 vs 客户喜忌
    day_gan_wx = _zrili_gan_wuxing(day_gan)
    if day_gan_wx in client_xi:
        score += 20
        matches["xishen"] = True
        reasons.append(f"日干{day_gan}({day_gan_wx})为客户喜用神")
    if day_gan_wx and day_gan_wx in client_ji:
        score -= 20
        matches["jishen"] = True
        reasons.append(f"日干{day_gan}({day_gan_wx})是客户忌神")
    # 2. 日支关系
    rels = _zrili_zhi_relations(day_zhi, client_day_zhi)
    if rels.get("chong"):
        score -= 25
        matches["chong"] = True
        reasons.append(f"日支{day_zhi}冲客户日支{client_day_zhi}— 不利")
    if rels.get("liuhe"):
        score += 15
        matches["liuhe"] = True
        reasons.append(f"日支{day_zhi}与客户日支{client_day_zhi}六合(情合/合作)")
    if rels.get("sanhe"):
        bureau_missing = rels["sanhe"]
        if bureau_missing:
            score += 10
            matches["sanhe"] = True
            reasons.append(f"日支{day_zhi}与客户日支{client_day_zhi}半合{''.join(bureau_missing)}局")
    # 3. 天乙贵人
    tianyi_zhis = _ZRILI_TIANYI.get(client_day_master, [])
    if day_zhi in tianyi_zhis:
        score += 10
        matches["tianyi"] = True
        reasons.append(f"天乙贵人在日支{day_zhi}")
    # 4. 文昌
    wenchang_zhi = _ZRILI_WENCHANG.get(client_day_master, "")
    if day_zhi == wenchang_zhi:
        score += 6
        reasons.append(f"文昌贵人在日支{day_zhi}")
    # 5. 凶煞简判: 日支是日柱支冲(自身冲)与月破(简化不实现)

    score = max(0, min(100, score))
    return {"score": score, "reasons": reasons, "matches": matches}


def _zrili_safe_day(solar_yyyymmdd: str, day_gan: str, day_zhi: str, client_ji: list,
                    client_day_zhi: str) -> bool:
    """
    排除条件:
      - 日干五行已是客户忌神 (硬排除, 除非分极高)
      - 日支冲客户日支 (硬排除)
    """
    day_gan_wx = _zrili_gan_wuxing(day_gan)
    if day_gan_wx and day_gan_wx in client_ji:
        return False
    if _zrili_zhi_relations(day_zhi, client_day_zhi).get("chong"):
        return False
    return True


@router.get("/api/zrili")
async def zrili(
    event: str = Query("签合同", description="事件类型: 签合同/搬家/结婚/开业/出行/看病"),
    date_range_start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_range_end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    birth: str = Query(..., description="客户出生时间, 格式: 2005-06-09 11:50"),
    location: str = Query("北京", description="出生地"),
    gender: str = Query("男"),
    name: str = Query("", description="客户姓名(辅助)"),
    top_n: int = Query(5, ge=1, le=20),
):
    """
    黄道择日接口
    输入:
      event / date_range_start / date_range_end / birth / location / gender / name
    输出:
      {event, range, client_xi_yong, recommendations:[{date, ganzhi, ...}], disclosure}
    """
    try:
        from lunar_python import Solar
        from datetime import datetime, timedelta

        # 1. 日期范围默认: 未来 30 天
        if not date_range_start or not date_range_end:
            today = datetime.now().date()
            ds = today + timedelta(days=1)
            de = today + timedelta(days=30)
            date_range_start = ds.strftime("%Y-%m-%d")
            date_range_end = de.strftime("%Y-%m-%d")

        ds_date = datetime.strptime(date_range_start, "%Y-%m-%d").date()
        de_date = datetime.strptime(date_range_end, "%Y-%m-%d").date()

        # 2. 客户命盘
        _, udm = _prepare_udm(birth, location, gender)
        client_day_master = udm.day_master or ""
        client_day_zhi = udm.bazi_day.zhi if udm.bazi_day else ""

        xi_yong = getattr(udm, "xi_yong", {}) or {}
        client_xi = xi_yong.get("xi") or []  # 喜用五行
        client_ji = xi_yong.get("ji") or []  # 忌神五行
        if not client_xi:
            # 中和命无强喜用 — 用事件偏好五行兜底
            client_xi = list(_ZRILI_EVENT_PREF.get(event, {"金", "水"}))

        # 3. 遍历日期
        candidates = []
        cur = ds_date
        one_day = timedelta(days=1)
        total_days = (de_date - ds_date).days + 1
        if total_days > 180:
            return JSONResponse(status_code=400, content={
                "error": f"日期范围过大({total_days}天), 最大支持 180 天",
                "error_code": "RANGE_TOO_LARGE",
            })

        while cur <= de_date:
            try:
                solar = Solar.fromYmd(cur.year, cur.month, cur.day)
                lunar = solar.getLunar()
                day_gz = lunar.getDayInGanZhi()  # e.g. "丙申"
                day_gan = day_gz[0]
                day_zhi = day_gz[1]

                # 排除忌神日与日柱冲日
                if not _zrili_safe_day(cur.isoformat(), day_gan, day_zhi, client_ji, client_day_zhi):
                    cur += one_day
                    continue

                s = _zrili_score_day(client_xi, client_ji, client_day_master,
                                     client_day_zhi, day_gan, day_zhi)
                # 事件偏好微调:日支五行在事件偏好中 +5
                day_zhi_wx = _zrili_zhi_wuxing(day_zhi)
                pref = _ZRILI_EVENT_PREF.get(event, set())
                if day_zhi_wx in pref:
                    s["score"] = min(100, s["score"] + 5)
                    s["reasons"].append(f"日支{day_zhi}({day_zhi_wx})合「{event}」偏好")

                # 推荐理由:十神(gz gan 相对日主)
                ss = _zrili_shishen(client_day_master, day_gan)
                shishen_gan_str = ss

                # best_hour
                bh = _zrili_best_hour(client_xi, client_day_master)
                # 避开的时辰: 与客户喜忌冲突的时辰
                avoid_hours = []
                for sh, eh, z, g, w in _ZRILI_HOURS:
                    if w in client_ji:
                        avoid_hours.append(f"{z}时({sh}-{eh})忌{w}")

                candidates.append({
                    "date": cur.isoformat(),
                    "ganzhi": day_gz,
                    "shishen_gan": shishen_gan_str,
                    "score": s["score"],
                    "reasons": s["reasons"],
                    "best_hour": f"{bh['zhi']}时({bh['start']}-{bh['end']})— {bh['gan']}({bh['wx']})",
                    "avoid": avoid_hours[:2] if avoid_hours else [],
                })
            except Exception as inner_e:
                logger.warning(f"zrili 计算 {cur} 失败: {inner_e}")
            cur += one_day

        # 4. 排序,取 top_n
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[:top_n]

        return {
            "event": event,
            "range": [date_range_start, date_range_end],
            "client_xi_yong": client_xi,
            "client_ji": client_ji,
            "client_day_master": client_day_master,
            "client_day_zhi": client_day_zhi,
            "strength": xi_yong.get("strength", ""),
            "recommendations": top,
            "total_candidates": len(candidates),
            "date_range_days": total_days,
            "disclosure": [
                "择日基于命理符号与喜用神, 实际效果因人而异",
                "建议优先选 top 3 日期, 其余做备选",
                "评分逻辑: 喜用神+20/六合+15/三合+10/天乙贵人+10/文昌+6/忌神-20/六冲-25",
                "事件偏好(签合同→金土, 搬家→火土, 结婚→水木, 开业→火木, 出行→木水, 看病→水金)",
                "已自动排除日干为忌神与日支冲客户日支的日期",
            ],
        }
    except ValueError as ve:
        logger.error(f"zrili 参数错误: {ve}", exc_info=True)
        return JSONResponse(status_code=400, content={"error": str(ve), "error_code": "VALIDATION_ERROR"})
    except Exception as e:
        logger.error(f"zrili 失败: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"择日计算失败: {str(e)}", "error_code": "INTERNAL_ERROR"})

