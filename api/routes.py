#!/usr/bin/env python3
"""
玄照 v2.0 - FastAPI 路由
"""
import logging
import re
import traceback
import hashlib
import time
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
from engine.bazi_engine import BaziEngine
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
    return 1 if gender in ("男", "male", "m") else 0


def _validate_birth(birth: str):
    """验证出生时间格式"""
    if not birth or not birth.strip():
        raise ValueError("出生时间不能为空")
    # 支持格式：2005-06-09 11:50 或 2005/06/09 11:50
    patterns = [
        r'^\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}:\d{2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}$',
        r'^\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}:\d{2}$',
        r'^\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{2}:\d{2}$',
        r'^\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{2}$',
    ]
    if not any(re.match(p, birth.strip()) for p in patterns):
        raise ValueError(f"时间格式错误: {birth}，应为 YYYY-MM-DD HH:MM")
    # 检查范围（统一用正则提取年月日时分，兼容ISO格式T分隔符和仅小时格式）
    clean = re.sub(r'T', ' ', birth.strip())
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
    import calendar
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


def _sanitize_name(name: str) -> str:
    """清理姓名参数，防止注入"""
    if not name:
        return ""
    # 只保留中文字符、字母、数字、常见分隔符
    sanitized = re.sub(r'[^\u4e00-\u9fff\w\s·-]', '', name.strip())
    return sanitized[:20]  # 限制长度

def _prepare_udm(birth: str, location: str, gender: str):
    """公共前置：时间校正 + 排盘，返回 (corrected, udm)"""
    _validate_birth(birth)
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
                "available": getattr(eng, '_available', True),
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
                    'ri_zhu': udm.day_master or '',
                    'xi_shen': xi_shen,
                    'ji_shen': ji_shen,
                }
            
            xm_result = _xingming_engine.analyze_name(surname, given_name, "男" if gender in ("男", "male", "m") else "女", bazi_info)
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
        from datetime import datetime

        # 解析时间
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"]:
            try:
                dt = datetime.strptime(birth.strip(), fmt)
                break
            except ValueError:
                continue
        else:
            return JSONResponse(status_code=400, content={"error": "无法解析时间"})

        # 通过真太阳时校正（与引擎使用相同时间）
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

        # 对比（两者都使用真太阳时校正后的时间）
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
    """获取所有可用人物"""
    try:
        from engine.perspective_engine import FIGURES
        return {
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
        wuxing_map = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", 
                     "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
        sheng_map = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
        ke_map = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
        
        daygan_relation = ""
        daygan_score = 50  # 基础分
        d1 = bazi1.get("day", "")[:1]
        d2 = bazi2.get("day", "")[:1]
        wx1 = wuxing_map.get(d1, "")
        wx2 = wuxing_map.get(d2, "")
        if wx1 and wx2:
            if wx1 == wx2:
                daygan_relation = "比和（同类）"
                daygan_score = 60
            elif sheng_map.get(wx1) == wx2:
                daygan_relation = f"{wx1}生{wx2}（相生）"
                daygan_score = 80
            elif sheng_map.get(wx2) == wx1:
                daygan_relation = f"{wx2}生{wx1}（相生）"
                daygan_score = 80
            elif ke_map.get(wx1) == wx2:
                daygan_relation = f"{wx1}克{wx2}（相克）"
                daygan_score = 40
            elif ke_map.get(wx2) == wx1:
                daygan_relation = f"{wx2}克{wx1}（相克）"
                daygan_score = 40
        
        # 日支关系（婚姻宫）
        rizhi_relation = ""
        rizhi_score = 50
        ZHI_LIUHE = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
                     "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}
        ZHI_LIUCHONG = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅",
                        "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}
        zhi1 = bazi1.get("day", "")[1:2] if len(bazi1.get("day", "")) > 1 else ""
        zhi2 = bazi2.get("day", "")[1:2] if len(bazi2.get("day", "")) > 1 else ""
        if zhi1 and zhi2:
            if ZHI_LIUHE.get(zhi1) == zhi2:
                rizhi_relation = f"{zhi1}{zhi2}六合（暗合吸引）"
                rizhi_score = 90
            elif ZHI_LIUCHONG.get(zhi1) == zhi2:
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
