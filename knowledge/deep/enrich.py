"""
玄照一针见血增强模块
挂在 /api/chart 上,不影响 routes.py
"""
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger("xuanzhao.wisdom")

# 加载规则引擎
sys.path.insert(0, str(Path(__file__).parent / "deep"))
try:
    from wisdom import high_impact_insight, cross_synthesis
    WISDOM_OK = True
except Exception as e:
    logger.warning(f"wisdom 加载失败: {e}")
    WISDOM_OK = False


def enrich_chart_result(result: dict) -> dict:
    """给 /api/chart 输出加 insights 字段"""
    if not WISDOM_OK:
        result["insights"] = []
        result["current_dayun_focus"] = ""
        return result

    # 提取八字摘要
    bazi = result.get("bazi", {})
    pillars = bazi.get("year", "") + " " + bazi.get("month", "") + " " + bazi.get("day", "") + " " + bazi.get("time", "")
    bazi_summary = {
        "pillars": {
            "year": bazi.get("year", ""),
            "month": bazi.get("month", ""),
            "day": bazi.get("day", ""),
            "time": bazi.get("time", ""),
        },
        "day_master": bazi.get("day_master", ""),
        "strength": bazi.get("strength", ""),
        "wuxing_score": bazi.get("wuxing_score", {}),
        "shensha": bazi.get("shensha", []),
        "features": bazi.get("features", []),
        "dayun": bazi.get("dayun", []),
    }
    ziwei = result.get("ziwei", {})
    ziwei_summary = {"ming_gong": ziwei.get("ming_gong", "")}
    astro = result.get("astro", {})
    astro_summary = {
        "sun_sign": astro.get("sun_sign", ""),
        "ascendant_sign": astro.get("ascendant_sign", ""),
    }

    try:
        insights = high_impact_insight(bazi_summary)
        insights += cross_synthesis(bazi_summary, ziwei_summary, astro_summary)
        result["insights"] = insights

        # 当前大运主题
        dayun_list = bazi.get("dayun", [])
        if dayun_list:
            current = next((d for d in dayun_list if d.get("is_current")), None)
            if current:
                result["current_dayun_focus"] = (
                    f"你当前走 '{current.get('ganzhi', '')}' 大运,"
                    f"长生十二宫:{current.get('changsheng', '')} - {current.get('changsheng_desc', '')}"
                )
            else:
                result["current_dayun_focus"] = ""
        else:
            result["current_dayun_focus"] = ""
    except Exception as e:
        logger.warning(f"insight 生成失败: {e}")
        result["insights"] = []
        result["current_dayun_focus"] = ""

    return result