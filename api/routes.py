#!/usr/bin/env python3
"""
玄照 v2.0 - FastAPI 路由
"""
import logging
import re
import traceback
import time
import calendar
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
import json as _json

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
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
    question: str = Query(..., description="问题"),
):
    """问答接口"""
    try:
        corrected, udm = _prepare_udm(birth, location, gender)

        qa = QAEngine()
        answer = qa.ask(udm, question)

        return {
            "question": question,
            "question_type": answer.question_type.value,
            "answer": answer.answer,
            "confidence": answer.confidence.value,
            "supporting_methods": answer.supporting_methods,
            "key_points": answer.key_points,
            "warnings": answer.warnings,
        }

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
    birth2: str = Query(..., description="第二人出生时间"),
    location2: str = Query("北京", description="第二人出生地点"),
    gender2: str = Query("女", description="第二人性别"),
):
    """八字合婚分析接口（增强版：日支关系+大运叠加+综合评分）"""
    try:
        if not birth1 or not birth2:
            return JSONResponse(status_code=400, content={"error": "请提供两人的出生时间"})
        corrected1, udm1 = _prepare_udm(birth1, location1, gender1)
        corrected2, udm2 = _prepare_udm(birth2, location2, gender2)
        
        bazi1 = {}
        bazi2 = {}
        
        if udm1.bazi_year:
            bazi1 = {
                "year": udm1.bazi_year.ganzhi,
                "month": udm1.bazi_month.ganzhi if udm1.bazi_month else "",
                "day": udm1.bazi_day.ganzhi if udm1.bazi_day else "",
                "time": udm1.bazi_time.ganzhi if udm1.bazi_time else "",
                "day_master": udm1.day_master,
                "xi_yong": getattr(udm1, 'xi_yong', {}),
                "dayun": getattr(udm1, 'dayun', [])[:5],
                "shensha": getattr(udm1, 'shensha', []),
            }
        
        if udm2.bazi_year:
            bazi2 = {
                "year": udm2.bazi_year.ganzhi,
                "month": udm2.bazi_month.ganzhi if udm2.bazi_month else "",
                "day": udm2.bazi_day.ganzhi if udm2.bazi_day else "",
                "time": udm2.bazi_time.ganzhi if udm2.bazi_time else "",
                "day_master": udm2.day_master,
                "xi_yong": getattr(udm2, 'xi_yong', {}),
                "dayun": getattr(udm2, 'dayun', [])[:5],
                "shensha": getattr(udm2, 'shensha', []),
            }
        
        # 日干关系
        
        daygan_relation = ""
        daygan_score = 50  # 基础分
        d1 = bazi1.get("day", "")[:1]
        d2 = bazi2.get("day", "")[:1]
        wx1 = GAN_WUXING_STR.get(d1, "")
        wx2 = GAN_WUXING_STR.get(d2, "")
        if wx1 and wx2:
            if wx1 == wx2:
                daygan_relation = "比和（同类）"
                daygan_score = 60
            elif WUXING_SHENG.get(wx1) == wx2:
                daygan_relation = f"{wx1}生{wx2}（相生）"
                daygan_score = 80
            elif WUXING_SHENG.get(wx2) == wx1:
                daygan_relation = f"{wx2}生{wx1}（相生）"
                daygan_score = 80
            elif WUXING_KE.get(wx1) == wx2:
                daygan_relation = f"{wx1}克{wx2}（相克）"
                daygan_score = 40
            elif WUXING_KE.get(wx2) == wx1:
                daygan_relation = f"{wx2}克{wx1}（相克）"
                daygan_score = 40
        
        # 日支关系（婚姻宫）
        rizhi_relation = ""
        rizhi_score = 50
        from engine.udm import ZHI_LIUHE as _UDM_ZHI_LIUHE, ZHI_CHONG as _UDM_ZHI_CHONG
        zhi1 = bazi1.get("day", "")[1:2] if len(bazi1.get("day", "")) > 1 else ""
        zhi2 = bazi2.get("day", "")[1:2] if len(bazi2.get("day", "")) > 1 else ""
        if zhi1 and zhi2:
            if _UDM_ZHI_LIUHE.get(zhi1) == zhi2:
                rizhi_relation = f"{zhi1}{zhi2}六合（暗合吸引）"
                rizhi_score = 90
            elif _UDM_ZHI_CHONG.get(zhi1) == zhi2:
                rizhi_relation = f"{zhi1}{zhi2}六冲（核心矛盾）"
                rizhi_score = 20
            elif zhi1 == zhi2:
                rizhi_relation = f"{zhi1}{zhi2}比和"
                rizhi_score = 60
            else:
                rizhi_relation = f"{zhi1}{zhi2}无特殊关系"
                rizhi_score = 50
        
        # 喜用互补
        complement = "未知"
        complement_score = 50
        xi1 = (bazi1.get("xi_yong") or {}).get("xi", "")
        xi2 = (bazi2.get("xi_yong") or {}).get("xi", "")
        ji1 = (bazi1.get("xi_yong") or {}).get("ji", "")
        ji2 = (bazi2.get("xi_yong") or {}).get("ji", "")
        if xi1 and xi2:
            # 她需要的正好是他多的
            if isinstance(xi1, list):
                xi1 = "".join(xi1)
            if isinstance(xi2, list):
                xi2 = "".join(xi2)
            if isinstance(ji1, list):
                ji1 = "".join(ji1)
            if isinstance(ji2, list):
                ji2 = "".join(ji2)
            if any(c in str(xi2) for c in str(xi1)):
                complement = "互补型（喜用互生）"
                complement_score = 90
            elif any(c in str(ji2) for c in str(xi1)):
                complement = "互耗型（喜用互克）"
                complement_score = 20
            elif xi1 == xi2:
                complement = "竞争型（喜用相同）"
                complement_score = 50
            else:
                complement = "差异型"
                complement_score = 60
        
        # 大运叠加分析
        dayun_analysis = []
        dayun1 = bazi1.get("dayun", [])
        dayun2 = bazi2.get("dayun", [])
        for d1_item in dayun1[:3]:
            for d2_item in dayun2[:3]:
                y1 = d1_item.get("start_year", 0)
                y2 = d2_item.get("start_year", 0)
                overlap_start = max(y1, y2)
                y1e = d1_item.get("end_year", 0)
                y2e = d2_item.get("end_year", 0)
                overlap_end = min(y1e, y2e)
                if overlap_start <= overlap_end:
                    gz1 = d1_item.get("ganzhi", "")
                    gz2 = d2_item.get("ganzhi", "")
                    dayun_analysis.append({
                        "period": f"{overlap_start}-{overlap_end}",
                        "person1_dayun": gz1,
                        "person2_dayun": gz2,
                        "note": f"双方同入{gz1}/{gz2}大运叠加期"
                    })
        
        # 综合评分
        total_score = int(daygan_score * 0.3 + rizhi_score * 0.3 + complement_score * 0.4)
        grade = "天作之合" if total_score >= 80 else "良好" if total_score >= 65 else "需要磨合" if total_score >= 50 else "不太建议"
        
        return {
            "person1": {"birth": birth1, "gender": gender1, "bazi": bazi1},
            "person2": {"birth": birth2, "gender": gender2, "bazi": bazi2},
            "analysis": {
                "daygan_relation": daygan_relation,
                "daygan_score": daygan_score,
                "rizhi_relation": rizhi_relation,
                "rizhi_score": rizhi_score,
                "complement_type": complement,
                "complement_score": complement_score,
                "dayun_overlap": dayun_analysis,
                "total_score": total_score,
                "grade": grade,
                "note": "综合评分=日干关系30%+日支关系30%+喜用互补40%。大运叠加期为双方运势共振期。"
            }
        }
    except Exception as e:
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
