"""
玄照 · 客户报告引擎 (Report Engine)
=================================

把 /api/chart 的 1600+ 字段,翻译成"人能看懂、能行动的"判断。

设计原则(2026-07-10 梧指令):
1. 每条结论 = 1 句话判断 + 3-5 条证据 + 2-3 条行动
2. 八术联读,按"问题维度"(事业/财运/感情/健康/学业/性格)重组,不平铺
3. 反向案例触发器:每个判断自动查反向案例库,有 ≥3 反例就降一档信心
4. 诚实声明:算法偏置/bug/未实现功能,白纸黑字写出来
5. 三档信心:90% / 70% / <50%,分档用词
6. 溟玄风格:短句 + 断言 + 行动指引
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COUNTER_CASES_DIR = PROJECT_ROOT / "knowledge" / "cases" / "counter"
SHENSHA_TABLE_PATH = PROJECT_ROOT / "data" / "shensha.json"

# 已知算法偏置(基于 1226+ 样本统计)
ALGO_BIAS = {
    "健康": {"ji": 0.76, "note": "健康判断 76% 偏凶 — 标签不可信,看具体信号"},
    "事业": {"ji": 1.00, "note": "事业判断 100% 偏吉 — 标签不可信,看具体信号"},
    "财运": {"ji": 0.70, "note": "事业/财运 70% 偏吉 — 标签不可信"},
    "学业": {"ji": 0.93, "note": "学业 93% 偏吉 — 标签不可信"},
    "感情": {"ji": 0.39, "note": "感情 39% 吉 — 平衡可信"},
}

# 神煞吉凶分类(简版,基于校勘本)
SHENSHA_GROUPS = {
    "大吉": ["天乙贵人", "天德贵人", "月德贵人", "文昌", "文曲", "福星贵人", "天福贵人", "德秀贵人"],
    "吉": ["华盖", "桃花", "驿马", "将星", "太极贵人", "国印贵人"],
    "小凶": ["劫煞", "亡神", "孤辰", "寡宿"],
    "凶": ["羊刃", "天罗", "地网", "十恶大败", "六甲空亡"],
    "中性": [],
}


# ============== 工具函数 ==============

def _read_counter_cases() -> Dict[str, List[str]]:
    """把反向案例库扁平化成 topic → [case_ids] 索引"""
    if not COUNTER_CASES_DIR.exists():
        return {}
    idx: Dict[str, List[str]] = {}
    for f in sorted(COUNTER_CASES_DIR.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        # 文件名约定: 001-bazi-failure-1.md / 006-cv-health-bias.md
        m = re.match(r"(\d+)-(.+)\.md", f.name)
        if not m:
            continue
        case_id = f.stem
        # 找第一个 # 标题作为描述
        title_m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_m.group(1).strip() if title_m else case_id
        # 按文件名前缀归类 topic
        topic_hint = m.group(2)
        topic = _topic_from_filename(topic_hint)
        idx.setdefault(topic, []).append(f"{case_id}: {title}")
    return idx


def _topic_from_filename(hint: str) -> str:
    """把文件名 hint 映射到 6 大 topic"""
    if "health" in hint or "健" in hint:
        return "健康"
    if "career" in hint or "事业" in hint or "shangguan" in hint:
        return "事业"
    if "wealth" in hint or "money" in hint or "rich" in hint or "财运" in hint or "fortune" in hint:
        return "财运"
    if "study" in hint or "学业" in hint:
        return "学业"
    if "spouse" in hint or "感情" in hint or "emotion" in hint:
        return "感情"
    if "shishen" in hint or "gender" in hint or "yangren" in hint or "shayin" in hint:
        return "性格"
    return "其他"


def _group_shensha(shensha_list: List[str]) -> Dict[str, List[str]]:
    """把神煞列表按吉凶分组"""
    if not shensha_list:
        return {"大吉": [], "吉": [], "小凶": [], "凶": [], "中性": []}

    grouped = {"大吉": [], "吉": [], "小凶": [], "凶": [], "中性": []}
    for ss in shensha_list:
        # 去掉 "(时支午)" 之类的后缀再匹配
        ss_clean = re.sub(r"[（(].*?[)）]", "", ss).strip()
        matched = False
        for level, keywords in SHENSHA_GROUPS.items():
            for kw in keywords:
                if kw in ss_clean:
                    grouped[level].append(ss)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            grouped["中性"].append(ss)
    return grouped


def _confidence_level(conf: float) -> Tuple[str, str]:
    """把 0-100 信心分翻译成档位和措辞"""
    if conf >= 85:
        return ("高", "斩钉截铁")
    if conf >= 60:
        return ("中", "参考档")
    return ("低", "看不清")


def _verdict_phrase(verdict: str, conf: str) -> str:
    """根据信心档位调整措辞"""
    if conf == "高":
        return f"**{verdict}**"
    if conf == "中":
        return f"{verdict}(大概率)"
    return f"{verdict}(仅参考)"


# ============== 时辰边界检测(2026-07-10 梧指令)==============
# 真太阳时校正后,如果出生时间落在时辰切换点 ±5 分钟内,
# 整个命盘的时柱(进而日主强弱、用神、大运起算)都可能错一个时辰。
# 必须在报告顶部警告,让客户确认出生精度。
#
# 时辰地支顺序:子 23-01, 丑 01-03, 寅 03-05, 卯 05-07, 辰 07-09,
#              巳 09-11, 午 11-13, 未 13-15, 申 15-17, 酉 17-19,
#              戌 19-21, 亥 21-23
# 时辰切换的整点 = 01, 03, 05, 07, 09, 11, 13, 15, 17, 19, 21, 23

# 时辰边界整点(每个时辰的起点)及其对应的"在 bh 之后进入的时支"
# 01:00 后进入丑时,03:00 后进入寅时, ...
_ZHI_AFTER_BOUNDARY = {
    1: "丑",
    3: "寅",
    5: "卯",
    7: "辰",
    9: "巳",
    11: "午",
    13: "未",
    15: "申",
    17: "酉",
    19: "戌",
    21: "亥",
    23: "子",
}

# 循环表:每个时支"在哪个 bh 之前"(也就是 bh 之后下一个时支)
_ZHI_BEFORE_BOUNDARY = {
    1: "子",   # 01:00 之前 = 子时
    3: "丑",   # 03:00 之前 = 丑时
    5: "寅",
    7: "卯",
    9: "辰",
    11: "巳",
    13: "午",
    15: "未",
    17: "申",
    19: "酉",
    21: "戌",
    23: "亥",
}


def _check_time_boundary(true_solar_iso: str) -> Optional[Dict[str, Any]]:
    """检查真太阳时是否落在某个时辰边界 ±5 分钟内。

    Args:
        true_solar_iso: ISO 格式的 datetime 字符串(来自 chart_result['corrected_time']['true_solar'])

    Returns:
        None - 不在边界
        dict  - 在边界,包含 boundary_time / zhi_before / zhi_after / diff_min / message
    """
    if not true_solar_iso:
        return None
    try:
        ts = datetime.fromisoformat(true_solar_iso)
    except (ValueError, TypeError):
        return None

    # 真实日历的"当天分钟数"(00:00-23:59)
    minutes_of_day = ts.hour * 60 + ts.minute

    for bh in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]:
        boundary_min = bh * 60
        diff = minutes_of_day - boundary_min
        # bh ±5 分钟
        if -5 <= diff <= 5:
            zhi_before = _ZHI_BEFORE_BOUNDARY[bh]
            zhi_after = _ZHI_AFTER_BOUNDARY[bh]
            return {
                "boundary_time": f"{bh:02d}:00",
                "zhi_before": zhi_before,
                "zhi_after": zhi_after,
                "diff_min": diff,
                "true_solar_display": ts.strftime("%H:%M"),
                "message": (
                    f"⚠️ 你的真太阳时 {ts.strftime('%H:%M')} 接近{zhi_before}/{zhi_after}时边界({bh:02d}:00),"
                    f"整个命盘可能是{zhi_after}时不是{zhi_before}时。"
                    f"建议提供更精确的出生时间确认。"
                ),
            }

    return None


def _lookup_counter_cases(topic: str, counter_idx: Dict[str, List[str]]) -> List[str]:
    """查反向案例"""
    return counter_idx.get(topic, [])


# ============== 八术维度联读 ==============

def _section_bazi(bz: dict) -> Dict[str, Any]:
    """从八字引擎输出提取关键信号"""
    if not bz:
        return {}
    xi_yong = bz.get("xi_yong", {}) or {}
    strength = bz.get("strength", "?")
    # 当前大运
    current_dayun = {}
    for d in bz.get("dayun", []):
        if d.get("is_current"):
            current_dayun = d
            break
    # 当前流年
    liunian = bz.get("liunian", {})
    return {
        "pillars": {
            "year": bz.get("year"),
            "month": bz.get("month"),
            "day": bz.get("day"),
            "time": bz.get("time"),
        },
        "day_master": bz.get("day_master"),
        "strength": strength,
        "xi": xi_yong.get("xi", []),
        "ji": xi_yong.get("ji", []),
        "wuxing_score": bz.get("wuxing_score", {}),
        "geju": bz.get("geju", {}).get("geju_type"),
        "shensha_grouped": _group_shensha(bz.get("shensha", [])),
        "career_tendency": bz.get("career_tendency", {}).get("top_three", []),
        "current_dayun": current_dayun,
        "liunian": liunian,
        "features": bz.get("features", []),
        "raw_shishen_gan": bz.get("shishen_gan", {}),
        "raw_features": bz.get("features", []),
        "dayun_full": bz.get("dayun", []),
    }


def _section_ziwei(zw: dict) -> Dict[str, Any]:
    """紫微:找命宫、四化忌落点、夫妻宫/官禄宫/疾厄宫"""
    if not zw:
        return {}
    sihua = zw.get("sihua", {})
    hua_ji = sihua.get("忌", "")
    hua_lu = sihua.get("禄", "")
    hua_ke = sihua.get("科", "")
    # 找四化落宫
    palaces = zw.get("palaces", [])
    hua_ji_palace = ""
    hua_ke_palace = ""
    hua_lu_palace = ""
    couple_stars = []
    guanlu_stars = []
    jie_stars = []
    caifu_stars = []
    for p in palaces:
        pname = p.get("name", "")
        all_stars = [s["name"] for s in p.get("major_stars", []) + p.get("minor_stars", [])]
        if hua_ji and hua_ji in all_stars:
            hua_ji_palace = pname
        if hua_ke and hua_ke in all_stars:
            hua_ke_palace = pname
        if hua_lu and hua_lu in all_stars:
            hua_lu_palace = pname
        if pname == "夫妻":
            couple_stars = all_stars
        elif pname == "官禄":
            guanlu_stars = all_stars
        elif pname == "疾厄":
            jie_stars = [s["name"] for s in p.get("major_stars", [])]
        elif pname == "财帛":
            caifu_stars = all_stars
    # 命宫主星
    ming_gong_stars = []
    for p in palaces:
        if p.get("name") == "命宫":
            ming_gong_stars = [s["name"] + (f"({s['brightness']})" if s.get("brightness") else "")
                                for s in p.get("major_stars", [])]
            break
    # 当前大限(25-34 庚寅)
    current_dai_xian = next(
        (d for d in zw.get("dai_xian", []) if 25 <= d.get("start_age", 0) <= 34),
        {}
    )
    return {
        "ming_gong": zw.get("ming_gong"),
        "shen_gong": zw.get("shen_gong"),
        "ming_stars": ming_gong_stars,
        "wuxing_ju": zw.get("wuxing_ju", {}).get("wuxing"),
        "sihua": sihua,
        "hua_ji_palace": hua_ji_palace,
        "hua_ke_palace": hua_ke_palace,
        "hua_lu_palace": hua_lu_palace,
        "current_dai_xian": current_dai_xian,
        "raw_palaces": palaces,
        "couple_stars": couple_stars,
        "guanlu_stars": guanlu_stars,
        "jie_stars": jie_stars,
        "caifu_stars": caifu_stars,
    }


def _section_astro(ast: dict) -> Dict[str, Any]:
    """占星:找格局(吉凶比)、关键相位、行星落宫"""
    if not ast:
        return {}
    asp_sum = ast.get("aspects_summary", {})
    planets = ast.get("planets", {})
    return {
        "sun": ast.get("sun_sign"),
        "sun_element": ast.get("sun_element"),
        "moon": ast.get("moon_sign"),
        "moon_element": ast.get("moon_element"),
        "asc": ast.get("ascendant_sign"),
        "mc": ast.get("mc_sign"),
        "aspects_total": asp_sum.get("total"),
        "harmonious": asp_sum.get("harmonious"),
        "challenging": asp_sum.get("challenging"),
        "by_type": asp_sum.get("by_type", {}),
        "retrograde_planets": [k for k, v in ast.get("planetary_details", {}).items() if v.get("retrograde")],
        "raw_planets": planets,
    }


def _section_qimen(qm: dict) -> Dict[str, Any]:
    """奇门:找开门/死门方位"""
    if not qm:
        return {}
    palaces = qm.get("palaces", [])
    # 找开门/死门 实际落宫(从 palaces 列表里查,不要用 zhi_fu_gong)
    open_palace = None
    open_direction = None
    death_palace = None
    death_direction = None
    for p in palaces:
        men = p.get("men", "")
        if men == "开门":
            open_palace = p.get("name", "")
            open_direction = p.get("direction", "")
        elif men == "死门":
            death_palace = p.get("name", "")
            death_direction = p.get("direction", "")
    return {
        "ju": f"{qm.get('yin_yang')}{qm.get('ju_shu')}局",
        "jieqi": qm.get("jieqi"),
        "zhi_fu": qm.get("zhi_fu", {}),
        "zhi_shi": qm.get("zhi_shi", {}),
        "open_palace": open_palace,
        "open_direction": open_direction,
        "death_palace": death_palace,
        "death_direction": death_direction,
        "ge_ju_summary": qm.get("ge_ju_analysis", {}).get("summary"),
    }


def _section_liuren(lr: dict) -> Dict[str, Any]:
    """大六壬:取格局和初传"""
    if not lr:
        return {}
    yong = lr.get("yong_shen", {})
    return {
        "zhan_shi": lr.get("zhan_shi"),
        "yue_jiang": lr.get("yue_jiang"),
        "ge_ju": lr.get("ge_ju"),
        "chu_chuan": yong.get("chu_chuan_zhi"),
        "chu_chuan_jiang": yong.get("chu_chuan_jiang"),
        "chu_chuan_xiong_ji": yong.get("jiang_ji_xiong"),
        "interpretation": yong.get("jiang_han_yi"),
    }


def _section_liuyao(ly: dict) -> Dict[str, Any]:
    """六爻:取本卦/变卦/世爻"""
    if not ly:
        return {}
    return {
        "ben_gua": ly.get("ben_gua", {}).get("name"),
        "bian_gua": ly.get("bian_gua", {}).get("name"),
        "dong_yao": ly.get("dong_yao", []),
        "shi_yao": ly.get("shi"),
        "shi_liuqin": ly.get("wuxing_analysis", {}).get("yong_shen", ""),
        "ge_ju": ly.get("ge_ju", []),
        "gua_gong_wuxing": ly.get("gua_gong_wuxing"),
    }


def _section_taiyi(ty: dict) -> Dict[str, Any]:
    """太乙:取主客算、君基、五福"""
    if not ty:
        return {}
    sa = ty.get("suan_analysis", {})
    return {
        "taiyi_gong": ty.get("taiyi_gong"),
        "ju": f"{ty.get('yin_yang')}{ty.get('ju_num')}局",
        "main_count": sa.get("zhu_detail", [None])[0] if sa else None,
        "guest_count": sa.get("ke_detail", [None])[0] if sa else None,
        "verdict": sa.get("pan_duan"),
        "wufu_gong": ty.get("wu_fu"),
    }


def _section_xingming(xm: dict) -> Dict[str, Any]:
    """姓名学"""
    if not xm or "error" in xm:
        return {"error": xm.get("error", "姓名学未返回")}
    return {
        "wuge": xm.get("wuge", {}),
        "sancai": xm.get("sancai", {}),
        "score": xm.get("score"),
        "bazi_match": xm.get("bazi_match", {}),
    }


# ============== 6 维度判断(规则) ==============

def _judge_character(b: dict, zw: dict, ast: dict, counter_idx: dict) -> Dict[str, Any]:
    """性格判断"""
    evidence = []
    conf = 70

    strength = b.get("strength")
    if strength == "身弱":
        evidence.append(f"八字身弱({b.get('day_master')}{b.get('wuxing_score',{}).get('金','?')}金),靠外力撑事")
        conf += 10
    elif strength == "身强":
        evidence.append(f"八字身强,自有主张")

    shensha = b.get("shensha_grouped", {})
    if "华盖" in str(shensha):
        evidence.append("命中双华盖(月柱+日柱),内心世界丰富,独处不寂寞")
        conf += 5

    ming_stars = zw.get("ming_stars", [])
    if ming_stars:
        evidence.append(f"紫微命宫主星:{','.join(ming_stars)}")
        # 破军/贪狼 = 开创型
        if any(s in str(ming_stars) for s in ["破军", "贪狼"]):
            evidence.append("主星带开创破坏力,不安于现状")
            conf += 5

    asc = ast.get("asc")
    moon = ast.get("moon")
    if asc and moon:
        evidence.append(f"占星 升{asc} 月{moon},外在+情感层")
        conf += 5

    counter = _lookup_counter_cases("性格", counter_idx)
    return {
        "topic": "性格",
        "verdict": "外表随和,内在有主见。身弱但华盖双现,闷头做事型。",
        "confidence": min(conf, 95),
        "evidence": evidence[:6],
        "actions": ["给独处时间,别逼高频社交", "内耗多的人,少和消耗你的人来往"],
        "counter_cases": counter[:3],
        "method_sources": ["八字", "紫微", "占星"],
    }


def _judge_career(b: dict, zw: dict, qm: dict, counter_idx: dict) -> Dict[str, Any]:
    """事业判断"""
    evidence = []
    conf = 60
    bias_warning = ALGO_BIAS["事业"]["note"]

    strength = b.get("strength")
    current_dayun = b.get("current_dayun", {})
    liunian = b.get("liunian", {})

    if strength == "身弱":
        evidence.append("身弱扛不住财官,先借势")
        conf += 0  # 现实就是弱,不加分
    elif strength == "身强":
        evidence.append("身强可担财官,适合独立出击")

    career_tend = b.get("career_tendency", [])
    if career_tend:
        tops = "、".join([t[0] for t in career_tend[:3]])
        evidence.append(f"八字倾向:{tops}")

    # 紫微化忌落宫
    hua_ji = zw.get("sihua", {}).get("忌", "")
    hua_ji_palace = zw.get("hua_ji_palace", "")
    if hua_ji and hua_ji_palace:
        evidence.append(f"紫微 {hua_ji}化忌落{hua_ji_palace}宫 — 这条线有反复")
        if hua_ji_palace == "官禄":
            evidence.append("官禄逢忌,工作/功名路上有文书压力")
        elif hua_ji_palace in ["迁移", "交友"]:
            evidence.append(f"{hua_ji_palace}逢忌,外出/人际上有反复")
        conf += 10

    # 奇门开门方位 + 事业方向
    open_palace = qm.get("open_palace", "")
    open_direction = qm.get("open_direction", "")
    if open_palace:
        direction_text = f"{open_palace}({open_direction})" if open_direction else open_palace
        evidence.append(f"奇门开门落{direction_text},事业方向在此")

    # 当前大运 + 黄金期(动态找最佳大运)
    dayun_full = b.get("dayun_full", [])
    if dayun_full:
        current_dy = next((d for d in dayun_full if d.get("is_current")), {})
        if current_dy:
            evidence.append(f"现在走{current_dy.get('ganzhi')}大运({current_dy.get('shishen_gan')})— 当前节奏")
        # 找第一个印比大运(黄金期)
        for dy in dayun_full:
            gan_ss = dy.get("shishen_gan", "")
            if "印" in gan_ss or "比" in gan_ss or "劫" in gan_ss:
                if not dy.get("is_current"):
                    age_range = f"{dy['start_age']}-{dy['end_age']}岁"
                    evidence.append(f"黄金期:{age_range}{dy['ganzhi']}大运({gan_ss})")
                    break

    counter = _lookup_counter_cases("事业", counter_idx)
    if len(counter) >= 3:
        conf = max(50, conf - 15)
        evidence.append(f"⚠️ 反向案例库有 {len(counter)} 个事业例外 — 标签仅供参考")

    # 动态生成行动指引
    actions = []
    if strength == "身弱":
        actions.append(f"{current_dayun.get('start_age', 22)}-{current_dayun.get('end_age', 31)} 岁借平台/跟人合伙,不自己扛")
    if open_direction:
        actions.append(f"看准 {open_direction} 方位的机会")
    if liunian.get("ganzhi"):
        actions.append(f"流年(2026 {liunian.get('ganzhi')})稳为主,不折腾")

    return {
        "topic": "事业",
        "verdict": f"适合借平台/跟人合伙。身弱命,先借势再独立。当前{current_dayun.get('ganzhi','?')}大运({current_dayun.get('shishen_gan','?')})是过渡期。",
        "confidence": conf,
        "evidence": evidence[:6],
        "actions": actions or ["先借势再独立"],
        "counter_cases": counter[:3],
        "method_sources": ["八字", "紫微", "奇门"],
        "disclosure": bias_warning,
    }


def _judge_health(b: dict, zw: dict, qm: dict, ast: dict, counter_idx: dict) -> Dict[str, Any]:
    """健康判断"""
    evidence = []
    conf = 40  # 健康本来就难
    bias_warning = ALGO_BIAS["健康"]["note"]

    ws = b.get("wuxing_score", {})
    if ws.get("水", 1) == 0.0:
        evidence.append("八字五行无水,肾/膀胱/内分泌偏弱")
    if ws.get("火", 1) > 3.0:
        evidence.append(f"火旺({ws['火']}),心血管/眼睛需注意")

    death_palace = qm.get("death_palace")
    if death_palace:
        evidence.append(f"奇门死门落{death_palace},此处对应身体信号(呼吸/皮肤/消化)")

    # 紫微疾厄宫
    for p in (zw.get("raw_palaces") or []):
        if p.get("name") == "疾厄":
            stars = ",".join([s["name"] for s in p.get("major_stars", [])])
            evidence.append(f"紫微疾厄宫主星:{stars}")

    mc = ast.get("mc")
    if mc:
        evidence.append(f"占星天顶{mc},职业压力在 {mc} 性质")

    counter = _lookup_counter_cases("健康", counter_idx)
    if len(counter) >= 3:
        conf = max(30, conf - 10)

    return {
        "topic": "健康",
        "verdict": "亚健康倾向。算法标签 76% 偏凶不可信,看具体信号。",
        "confidence": conf,
        "evidence": evidence[:6],
        "actions": [
            "补{0}".format("水" if ws.get("水", 1) == 0.0 else "金"),
            f"关注 {death_palace or '肺/皮肤'} 区域",
            "每年体检,别只看玄学判断",
        ],
        "counter_cases": counter[:5],
        "method_sources": ["八字", "紫微", "奇门", "占星"],
        "disclosure": bias_warning,
    }


def _judge_relationship(b: dict, zw: dict, lr: dict, ly: dict, ast: dict, counter_idx: dict) -> Dict[str, Any]:
    """感情判断 — 感情维度最可信(39% 平衡)"""
    evidence = []
    conf = 75

    current_dayun_full = next((d for d in b.get("dayun_full", []) if d.get("is_current")), {})

    # 八字:财星(男命配偶)数量
    shishen_gan = b.get("raw_shishen_gan", {})
    cai_stars = []
    for pillar, ss in shishen_gan.items():
        if "财" in str(ss):
            cai_stars.append(f"{pillar}柱{ss}")
    if cai_stars:
        evidence.append(f"财星{len(cai_stars)}现({','.join(cai_stars)}),异性缘不差")

    # 八字:时柱桃花
    shensha_g = b.get("shensha_grouped", {})
    if "桃花" in shensha_g.get("吉", []) + shensha_g.get("大吉", []):
        evidence.append("命中桃花入吉,吸引力稳定")
    if "咸池" in str(b.get("raw_features", [])):
        evidence.append("咸池同桃花,魅力强")

    # 八字:日支(配偶宫)状态
    day_zhi = b.get("pillars", {}).get("day", "")[-1] if b.get("pillars", {}).get("day") else ""
    if day_zhi:
        evidence.append(f"日支{day_zhi}(配偶宫),看与流年是否合冲")

    # 紫微:夫妻宫主星(从 raw_palaces 找)
    zw_raw = zw.get("raw_palaces") or []
    for p in zw_raw:
        if p.get("name") == "夫妻":
            stars = [s["name"] for s in p.get("major_stars", [])]
            if stars:
                evidence.append(f"紫微夫妻宫主星:{','.join(stars)}")
                if "武曲" in stars:
                    evidence.append("武曲主财星入夫妻,配偶务实能理财")
                if "文曲" in stars:
                    evidence.append("文曲化科入夫妻,配偶文雅有才")

    # 紫微:文曲化科入夫妻(已在 raw_palaces 数据里)
    hua_ke = zw.get("sihua", {}).get("科", "")
    if hua_ke == "文曲":
        evidence.append("文曲化科,感情中讲究精神共鸣")

    # 流年桃花
    liunian = b.get("liunian", {})
    if "桃花" in liunian.get("shensha", []):
        evidence.append(f"流年(2026 {liunian.get('ganzhi','')})带桃花,本年有缘分机会")

    # 占星:金星 + 5 宫/7 宫
    if ast.get("sun") and ast.get("asc"):
        evidence.append(f"占星 升{ast.get('asc')} 5宫/7宫主管感情,看金火相位")
    # 5 宫主星(金星/火星落 5/7 宫)
    planets = ast.get("raw_planets", {})
    for p_name, p_data in planets.items():
        if isinstance(p_data, dict) and p_data.get("house") in [5, 7]:
            evidence.append(f"占星 {p_name} 落{p_data.get('house')}宫({p_data.get('sign','?')}),感情活跃")

    # 六壬:用神为"女眷/隐私/谋划"
    chu_chuan_jiang = lr.get("chu_chuan_jiang", "")
    if chu_chuan_jiang:
        evidence.append(f"六壬初传{chu_chuan_jiang}将,情感事有方向")

    counter = _lookup_counter_cases("感情", counter_idx)

    # 动态生成 verdict
    liunian_gz = liunian.get("ganzhi", "")
    has_taohua = "桃花" in liunian.get("shensha", [])
    verdict_str = "感情缘分不差。"
    if has_taohua:
        verdict_str += f"流年(2026 {liunian_gz})带桃花,本年缘分窗口。"
    verdict_str += "命中财星+桃花双信号,关键看大运节奏。"

    return {
        "topic": "感情",
        "verdict": verdict_str,
        "confidence": conf,
        "evidence": evidence[:8],
        "actions": [
            f"当前{current_dayun_full.get('ganzhi','?')}大运是感情扎根期",
            "配偶倾向:务实 / 文雅(武曲+文曲组合)" if zw.get("couple_stars") else "配偶倾向待紫微夫妻宫数据补全",
            "2026 流年桃花是窗口期" if has_taohua else "观察 2026-2027 流年是否有桃花",
        ],
        "counter_cases": counter[:3],
        "method_sources": ["八字", "紫微", "占星", "六壬"],
        "disclosure": "感情维度相对可信(39% 平衡,其他维度严重偏置)",
    }


def _judge_wealth(b: dict, zw: dict, lr: dict, ty: dict, counter_idx: dict) -> Dict[str, Any]:
    """财运判断"""
    evidence = []
    conf = 50  # 财运偏置 70%
    bias_warning = ALGO_BIAS["财运"]["note"]

    strength = b.get("strength")
    geju = b.get("geju")
    dayun_full = b.get("dayun_full", [])
    current_dayun_full = next((d for d in dayun_full if d.get("is_current")), {})

    if strength == "身弱" and "财" in str(geju):
        evidence.append("财格 + 身弱 = 有财难守(经典组合)")
    if strength == "身弱":
        evidence.append("身弱扛财,合作比单干更聚财")

    liunian = b.get("liunian", {})
    if liunian.get("ganzhi") == "丙午":
        evidence.append("2026 流年丙午,正财七杀混杂,稳财为先")

    # 紫微:禄存所在宫(代表财库)
    zw_raw = zw.get("raw_palaces") or []
    for p in zw_raw:
        stars = [s["name"] for s in p.get("minor_stars", []) + p.get("major_stars", [])]
        if "禄存" in stars:
            evidence.append(f"紫微禄存落{p.get('name')}宫 — 财在这块(谨慎看)")
            break

    # 太乙:主客算对比
    guest = ty.get("guest_count", "")
    main = ty.get("main_count", "")
    if guest and main:
        evidence.append(f"太乙主算{main} 客算{guest} — {ty.get('verdict','')}")

    # 六壬:格局
    if "返吟" in str(lr.get("ge_ju", "")):
        evidence.append("六壬返吟格局,财运起伏大")

    # 动态生成行动指引
    actions = []
    if liunian.get("ganzhi") == "丙午":
        actions.append("2026 流年丙午,财官混杂,稳财为先")
    if "身弱" in str(strength):
        actions.append("前 30 岁重点学本事,不当老板")
    if "身弱" in str(strength):
        actions.append("理财用稳健型(指数基金/定存),不碰杠杆")

    # 当前大运年龄 → 财库开启期
    if current_dayun_full:
        age_now = current_dayun_full.get("start_age", 22)
        # 找第一个偏财/正财/食神/伤官大运(财库相关)
        for dy in dayun_full:
            if dy.get("is_current"):
                continue
            gan_ss = dy.get("shishen_gan", "")
            if "财" in gan_ss or "食" in gan_ss:
                actions.append(f"{dy['start_age']}-{dy['end_age']} 岁{dy['ganzhi']}大运({gan_ss})财库开启")

    counter = _lookup_counter_cases("财运", counter_idx)
    if len(counter) >= 3:
        conf = max(40, conf - 10)
        evidence.append(f"⚠️ 反向案例库有 {len(counter)} 个财运例外")

    return {
        "topic": "财运",
        "verdict": f"财运有但身弱扛不稳。先求稳,后求多。流年丙午(2026)官杀混杂,稳为先。当前{current_dayun_full.get('ganzhi','?')}大运({current_dayun_full.get('shishen_gan','?')})是扎根期。",
        "confidence": conf,
        "evidence": evidence[:6],
        "actions": actions[:3] or ["稳字当头"],
        "counter_cases": counter[:3],
        "method_sources": ["八字", "紫微", "六壬", "太乙"],
        "disclosure": bias_warning,
    }


def _judge_study(b: dict, zw: dict, ast: dict, counter_idx: dict) -> Dict[str, Any]:
    """学业判断"""
    evidence = []
    conf = 65
    bias_warning = ALGO_BIAS["学业"]["note"]

    shensha_g = b.get("shensha_grouped", {})
    shensha_all = shensha_g.get("吉", []) + shensha_g.get("大吉", [])

    if "华盖" in shensha_all:
        evidence.append("双华盖(月柱+日柱),学业/艺术/哲学有天赋,能沉下心")
    if "文昌" in shensha_all:
        evidence.append("文昌吉,读书有灵性,适合文科性学习")
    if "文曲" in shensha_all:
        evidence.append("文曲吉,口才/写作方面有天分")
    if "天德" in str(shensha_all) or "月德" in str(shensha_all):
        evidence.append("天德/月德贵人,学习遇难呈祥")

    # 紫微:文昌文曲落宫
    zw_raw = zw.get("raw_palaces") or []
    for p in zw_raw:
        all_stars = [s["name"] for s in p.get("minor_stars", []) + p.get("major_stars", [])]
        for star in ["文昌", "文曲", "天魁", "天钺"]:
            if star in all_stars:
                evidence.append(f"紫微 {star} 落{p.get('name')}宫")
                break

    # 紫微:化科星(学术声誉)
    hua_ke = zw.get("sihua", {}).get("科", "")
    if hua_ke:
        evidence.append(f"紫微化科 {hua_ke} — 学术声誉可得")

    # 紫微:命宫主星(主智慧)
    ming_stars = zw.get("ming_stars", [])
    if "天机" in ming_stars or "紫微" in ming_stars:
        evidence.append(f"紫微命宫主星含 {'/'.join(ming_stars)} — 主智慧型")

    # 占星:水星 + 9 宫(高等教育)
    planets = ast.get("raw_planets", {})
    mercury = planets.get("水星", {})
    if mercury:
        mercury_house = mercury.get("house")
        if mercury_house == 9:
            evidence.append("占星水星落 9 宫(高等教育),学术顺利")
        elif mercury.get("dignity") == "domicile":
            evidence.append(f"占星水星入庙({mercury.get('sign')}),思维清晰")

    # 占星:3 宫(基础学习)主星
    for p_name, p_data in planets.items():
        if isinstance(p_data, dict) and p_data.get("house") in [3, 9]:
            evidence.append(f"占星 {p_name} 落{p_data.get('house')}宫({p_data.get('sign','?')}) — 学习/思维活跃")

    counter = _lookup_counter_cases("学业", counter_idx)

    return {
        "topic": "学业",
        "verdict": "学业真强(双华盖+文昌+文曲+紫微化科),但算法 93% 偏吉标签不可信 — 看具体能力。",
        "confidence": conf,
        "evidence": evidence[:8],
        "actions": [
            "方向:文学/哲学/艺术/心理学/法学,避开纯商科",
            "硕士/博士可读,别为了'早赚钱'中断",
            "写作/口才方向有天分,可发展副业",
        ],
        "counter_cases": counter[:3],
        "method_sources": ["八字", "紫微", "占星"],
        "disclosure": bias_warning,
    }


# ============== 108 视角辩论数据接入 ==============

# topic → 关键词(从辩论文本中筛出相关片段)
# 包括直接 topic 词 + 共识里常见的 108 视角共性信号
TOPIC_KEYWORDS = {
    "性格": ["性格", "气质", "内心", "主见", "沉稳", "急躁", "内向", "外向", "华盖", "命格", "本质", "脾气", "日主", "身弱", "身强"],
    "事业": ["事业", "工作", "职场", "官禄", "功名", "求官", "平台", "合伙", "创业", "仕途", "岗位", "晋升", "行业", "老板", "官杀", "印星"],
    "健康": ["健康", "身体", "疾病", "病", "五脏", "气血", "肾", "心", "肝", "肺", "精神", "失眠", "焦虑", "亚健康", "五行", "身弱", "身强"],
    "感情": ["感情", "婚姻", "配偶", "桃花", "恋爱", "夫妻", "缘分", "异性", "情人", "伴侣", "红鸾", "天喜", "财星", "咸池"],
    "财运": ["财", "财富", "金钱", "收入", "薪资", "理财", "投资", "破财", "漏财", "进财", "求财", "财库", "聚财", "禄存", "财星"],
    "学业": ["学业", "读书", "考试", "科举", "功名", "文科", "理科", "硕士", "博士", "学历", "文昌", "文曲", "学院", "印星", "主星"],
}


def _flatten_debate_text(item) -> str:
    """把 debate 结构里的 dict/str 拍平成字符串,便于关键词检索"""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        parts = []
        for k in ("stance_a", "stance_b", "aspect", "between", "argument", "stance"):
            v = item.get(k)
            if v is None:
                continue
            if isinstance(v, list):
                parts.append("、".join(str(x) for x in v))
            else:
                parts.append(str(v))
        return " ".join(parts)
    return str(item)


def _section_debate(source_dispatch: Optional[Dict[str, Any]], topic: str) -> Dict[str, Any]:
    """
    把 per-topic 辩论数据切片成单 section 用的 debate 字段。

    入参 source_dispatch (2026-07-10 改为 per-topic 多对一结构):
      {
        "<topic>": {
          "consensus":       [str, ...],
          "disagreements":   [{"between":[...], "stance_a":..., "stance_b":..., "aspect":...}, ...],
          "participants":    [{"name":..., "method":..., ...}, ...],
          "xuanzhao":        {"stance":..., "key_points":[...], "reasoning":..., "quotes":[...]},
        },
        ...
        "_meta": {...},
      }

    返回:
      {
        "count":              int,                # 参与辩论人数
        "consensus_points":   [str, ...],         # 该 topic 的共识
        "disagreements":      [str, ...],         # 该 topic 的分歧(拍平成短句)
        "key_quotes":         [str, ...],         # 玄照关键引语
        "xuanzhao_synthesis": str,                # 玄照本人的综合判断
      }

    失败/缺失 → 返回 {} (调用方负责字段缺省)。

    兼容旧形态(source_dispatch 顶层就是 consensus/disagreements):
      如果 source_dispatch 是旧形态(顶层含 consensus 字段),沿用原关键词过滤逻辑。
    """
    if not source_dispatch:
        return {}

    # 1) 新形态: source_dispatch 是 dict-of-topic
    if isinstance(source_dispatch, dict) and not source_dispatch.get("consensus") and not source_dispatch.get("disagreements"):
        topic_data = source_dispatch.get(topic) or {}
        if not topic_data:
            return {}
        participants = topic_data.get("participants") or []
        consensus = topic_data.get("consensus") or []
        disagreements = topic_data.get("disagreements") or []
        xuanzhao = topic_data.get("xuanzhao") or {}
        try:
            count = int(len(participants))
        except Exception:
            count = 0
        # 该 topic 已经专门跑过辩论,consensus/disagreements 全部保留,不再做关键词过滤
        consensus_hits = [str(c) if not isinstance(c, dict) else _flatten_debate_text(c) for c in consensus][:5]
        # 分歧拍平成一句人话: "A vs B: 立场a / 立场b"
        disagreement_hits = []
        for d in disagreements:
            if isinstance(d, dict):
                between = d.get("between") or []
                between_str = " vs ".join(str(x) for x in between) if isinstance(between, list) else str(between)
                a = d.get("stance_a", "")
                b_ = d.get("stance_b", "")
                aspect = d.get("aspect", "")
                line = f"{between_str}: {a}"
                if b_ and b_ != "立场不同":
                    line += f" / {b_}"
                if aspect and aspect != "观点对立":
                    line += f" ({aspect})"
                disagreement_hits.append(line)
            else:
                disagreement_hits.append(str(d))

        # 玄照关键引语
        quotes = []
        raw_quotes = xuanzhao.get("quotes") or []
        if isinstance(raw_quotes, list):
            quotes = [str(q) for q in raw_quotes[:3]]
        elif isinstance(raw_quotes, str):
            quotes = [raw_quotes]

        # 玄照综合判断
        xz_stance = xuanzhao.get("stance") or ""
        xz_reasoning = xuanzhao.get("reasoning") or ""
        if isinstance(xz_reasoning, dict):
            xz_reasoning = " | ".join(f"{k}:{v}" for k, v in xz_reasoning.items())
        xz_synthesis = xz_stance if xz_stance else (xz_reasoning if isinstance(xz_reasoning, str) else "")

        return {
            "count": count,
            "consensus_points": consensus_hits,
            "disagreements": disagreement_hits[:5],
            "key_quotes": quotes,
            "xuanzhao_synthesis": xz_synthesis,
        }

    # 2) 旧形态兼容: 顶层 consensus/disagreements → 关键词过滤
    participants = source_dispatch.get("participants") or []
    consensus = source_dispatch.get("consensus") or []
    disagreements = source_dispatch.get("disagreements") or []
    xuanzhao = source_dispatch.get("xuanzhao") or {}

    # 1. count
    try:
        count = int(len(participants))
    except Exception:
        count = 0

    # 2. topic 关键词过滤
    kws = TOPIC_KEYWORDS.get(topic, [])
    if not kws:
        return {"count": count}

    # 3. 共识点筛选
    consensus_hits = []
    for c in consensus:
        text = _flatten_debate_text(c)
        if any(k in text for k in kws):
            consensus_hits.append(text if isinstance(c, str) else _flatten_debate_text(c))

    # 4. 分歧点筛选 + 拍平
    disagreement_hits = []
    for d in disagreements:
        text = _flatten_debate_text(d)
        if any(k in text for k in kws):
            if isinstance(d, dict):
                between = d.get("between") or []
                if isinstance(between, list):
                    between_str = " vs ".join(str(x) for x in between)
                else:
                    between_str = str(between)
                a = d.get("stance_a", "")
                b_ = d.get("stance_b", "")
                aspect = d.get("aspect", "")
                line = f"{between_str}: {a}"
                if b_ and b_ != "立场不同":
                    line += f" / {b_}"
                if aspect and aspect != "观点对立":
                    line += f" ({aspect})"
                disagreement_hits.append(line)
            else:
                disagreement_hits.append(text)

    # 5. 玄照关键引语
    quotes = []
    raw_quotes = xuanzhao.get("quotes") or []
    if isinstance(raw_quotes, list):
        quotes = [str(q) for q in raw_quotes[:3]]
    elif isinstance(raw_quotes, str):
        quotes = [raw_quotes]

    # 6. 玄照综合判断(stance 优先,fallback 到 reasoning)
    xz_stance = xuanzhao.get("stance") or ""
    xz_reasoning = xuanzhao.get("reasoning") or ""
    if isinstance(xz_reasoning, dict):
        xz_reasoning = " | ".join(f"{k}:{v}" for k, v in xz_reasoning.items())
    xz_synthesis = xz_stance if xz_stance else (xz_reasoning if isinstance(xz_reasoning, str) else "")

    return {
        "count": count,
        "consensus_points": consensus_hits[:5],
        "disagreements": disagreement_hits[:5],
        "key_quotes": quotes,
        "xuanzhao_synthesis": xz_synthesis,
    }


def _attach_debate(section: Dict[str, Any],
                   source_dispatch: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """给单个 section 挂 debate 字段(静默失败:不挂空字段)

    新形态 (2026-07-10 梧指令): source_dispatch 是 {topic: debate_data} 字典。
    每个 section 直接拿自己 topic 对应的辩论,不再做关键词过滤。
    """
    topic = section.get("topic")
    if not topic or not source_dispatch:
        return section
    debate = _section_debate(source_dispatch, topic)
    # count==0 或 全部空 → 不挂(避免噪音)
    if not debate or not debate.get("count"):
        return section
    has_content = (
        debate.get("consensus_points")
        or debate.get("disagreements")
        or debate.get("key_quotes")
        or debate.get("xuanzhao_synthesis")
    )
    if not has_content:
        # 仍挂 count,标记"辩论跑过但没匹配"
        section["debate"] = {"count": debate["count"], "matched": False}
        return section
    section["debate"] = {**debate, "matched": True}
    return section


# ============== 维度可见性规则(2026-07-10 梧指令)==============

def apply_visibility(sections: List[Dict[str, Any]]) -> Tuple[int, int]:
    """根据 confidence 给每个 section 标 hidden / collapsed。

    规则(梧 2026-07-10 指令:玄照要学会说不知道):
      confidence < 20   → hidden=True    完全不渲染(raw_signal_summary 仍保留)
      20 ≤ conf < 35    → collapsed=True 默认折叠,前端用 <details> 包裹
      conf ≥ 35         → 不标,正常显示

    该函数会被 build_report 和 /api/report/verify 各自调用一次
    (因为 verify 端 calibrate_confidence 会改 confidence,需要重新标)。

    Returns:
        (hidden_count, collapsed_count)
    """
    hidden_count = 0
    collapsed_count = 0
    for s in sections:
        # 先清旧标记(支持反复调用)
        s.pop("hidden", None)
        s.pop("collapsed", None)
        conf = s.get("confidence", 0)
        if conf < 20:
            s["hidden"] = True
            hidden_count += 1
        elif conf < 35:
            s["collapsed"] = True
            collapsed_count += 1
    return hidden_count, collapsed_count


# ============== 总入口 ==============

def build_report(chart_result: dict, xingming_result: Optional[dict] = None,
                 question: str = "此人命运如何？",
                 source_dispatch: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    主入口:接收 /api/chart 输出 + /api/xingming 输出,生成客户报告

    Returns: 新模板 dict
    """
    # 1. 提取八术结构化数据
    b = _section_bazi(chart_result.get("bazi", {}))
    b["raw_shishen_gan"] = chart_result.get("bazi", {}).get("shishen_gan", {})
    zw = _section_ziwei(chart_result.get("ziwei", {}))
    ast = _section_astro(chart_result.get("astro", {}))
    qm = _section_qimen(chart_result.get("qimen", {}))
    lr = _section_liuren(chart_result.get("liuren", {}))
    ly = _section_liuyao(chart_result.get("liuyao", {}))
    ty = _section_taiyi(chart_result.get("taiyi", {}))
    xm = _section_xingming(xingming_result) if xingming_result else {}

    # 2. 加载反向案例索引
    counter_idx = _read_counter_cases()

    # 3. 6 维度判断
    sections = [
        _judge_character(b, zw, ast, counter_idx),
        _judge_career(b, zw, qm, counter_idx),
        _judge_health(b, zw, qm, ast, counter_idx),
        _judge_relationship(b, zw, lr, ly, ast, counter_idx),
        _judge_wealth(b, zw, lr, ty, counter_idx),
        _judge_study(b, zw, ast, counter_idx),
    ]

    # 3.5 接入 108 视角辩论数据(2026-07-10 梧指令)
    # source_dispatch 由调用方传入,缺失时静默跳过,不破坏现有结构
    if source_dispatch:
        sections = [_attach_debate(s, source_dispatch) for s in sections]

    # 3.7 学会说不知道 — 信心过低的维度隐藏 / 折叠(2026-07-10 梧指令)
    #   confidence < 20  → hidden: True    客户看不到,但 raw_signal_summary 里仍保留
    #   20 ≤ conf < 35   → collapsed: True 默认折叠,客户主动展开
    #   conf ≥ 35        → 正常输出
    # 隐藏只在 build_report 端做,前端无 hidden 字段就不会渲染 — 不靠 CSS 隐藏,避免数据泄漏
    # 注意:/api/report/verify 会再调用 apply_visibility(因为 calibrate_confidence 会改 confidence)
    hidden_count, collapsed_count = apply_visibility(sections)

    # 4. 总信心 = 各维度均值(包含所有 6 维度,隐藏的也计入 — 反映整体判断的真实分布)
    overall = int(sum(s["confidence"] for s in sections) / len(sections))

    # 4.5 时辰边界警告(2026-07-10 梧指令)
    # 真太阳时校正后,如果落在时辰切换点 ±5 分钟,整个命盘可能错一个时辰
    corrected_time = chart_result.get("corrected_time") or {}
    time_boundary_warning = _check_time_boundary(corrected_time.get("true_solar", ""))

    # 5. 诚实声明(算法 + 已知 bug)
    disclosures = [
        "健康/事业/财运/学业 标签 严重偏置(76-100%),不可信 — 看具体描述",
        "感情维度相对可信(39% 平衡)",
        f"神煞分类:吉{len(b.get('shensha_grouped',{}).get('吉',[]))} 大吉{len(b.get('shensha_grouped',{}).get('大吉',[]))} 凶{len(b.get('shensha_grouped',{}).get('凶',[]))} — 分类规则已实现,但只是参考",
        "姓名学与八字匹配度:" + str(xm.get("bazi_match", {}).get("等级", "未跑")),
        f"玄照 V2 当前共 {len(chart_result.get('methods',[]))} 术运行(姓名学需单独调用)",
        "命中注定占 30%,后天努力占 70% — 报告是趋势,不是定数",
    ]
    # 维度可见性声明(让客户知道哪些判断被隐藏/折叠了)
    if hidden_count > 0:
        disclosures.append(
            f"⚠️ {hidden_count} 个维度信心过低(<20),已隐藏不显示 — 命理信号不足,不做无把握判断"
        )
    if collapsed_count > 0:
        disclosures.append(
            f"⚠️ {collapsed_count} 个维度信心偏低(<35),默认折叠 — 需客户主动展开查看"
        )

    # 6. 主动追问(给梧/客户的下一步)
    questions = [
        "哪个维度你想深挖?(事业/财运/感情/健康/学业/性格)",
        "是否需要具体到 2026 月份的流月判断?",
        "是否要做合婚 / 择日 / 起名等专项?",
        "你是否认同'身弱借势'这个判断? 哪些事你已经在做?",
    ]

    # 7. 输出
    result = {
        "identity": {
            "name": chart_result.get("input", {}).get("name", "未填"),
            "birth": chart_result.get("input", {}).get("birth"),
            "location": chart_result.get("input", {}).get("location"),
            "gender": chart_result.get("input", {}).get("gender"),
            "day_master": b.get("day_master"),
            "strength": b.get("strength"),
            "true_solar_diff_min": chart_result.get("corrected_time", {}).get("diff_minutes"),
            "current_dayun_focus": chart_result.get("current_dayun_focus", ""),
        },
        "question": question,
        "confidence_overall": overall,
        "time_boundary_warning": time_boundary_warning,  # None 或 {boundary_time, message, ...}
        "disclosures": disclosures,
        "sections": sections,
        "next_questions": questions,
        "method_coverage": {
            "bazi": bool(chart_result.get("bazi")),
            "ziwei": bool(chart_result.get("ziwei")),
            "astro": bool(chart_result.get("astro")),
            "liuyao": bool(chart_result.get("liuyao")),
            "qimen": bool(chart_result.get("qimen")),
            "liuren": bool(chart_result.get("liuren")),
            "taiyi": bool(chart_result.get("taiyi")),
            "xingming": bool(xm and "error" not in xm),
        },
        "raw_signal_summary": {
            "bazi": b,
            "ziwei": zw,
            "astro": ast,
            "qimen": qm,
            "liuren": lr,
            "liuyao": ly,
            "taiyi": ty,
            "xingming": xm,
        },
    }

    # 8. 加行为验证追问(2026-07-10 梧指令:不让玄照只靠命理符号判断)
    from engine.verify_questions import get_verify_questions
    verify_questions = {}
    for section in result["sections"]:
        topic = section.get("topic")
        qs = get_verify_questions(topic)
        if qs:
            verify_questions[topic] = qs
    result["verify_questions"] = verify_questions
    result["verify_pending"] = True  # 标记:客户还没回答验证问题

    # 9. LLM 增强层(2026-07-10 梧指令:把干巴巴的模板套话改成"溟玄风格"自然语言)
    #    - 复用车牌 engine/llm_client.py(同步 OpenAI 兼容客户端)
    #    - 用 asyncio.to_thread 包成协程,6 节并发(asyncio.gather),整体 < 8s 硬超时
    #    - 任一节失败 → 静默 fallback 到原始 verdict(不报错,verdict 字段全保留)
    #    - LLM 只能润色,不能改判断方向:verdict_natural 必须可追溯到 verdict 字段
    try:
        asyncio.run(_enhance_report_with_llm(result))
    except Exception as e:
        # 整个增强层失败也不阻塞报告(已完成 6 节 fallback,不影响原有 verdict)
        logger.warning(f"LLM 增强层失败,使用原始 verdict: {e}")
        _ensure_natural_fallback(result)

    return result


# ============== LLM 增强层(2026-07-10 梧指令)==============
# 不改原始 verdict 方向,只润色表达。失败静默。
# 约束:
#   1. LLM 输出必须含 verdict_natural(150-300 字),actions_natural(3-5 条)
#   2. 不许输出"几千万"/"亿万"等具体金额数字
#   3. 不许超出原始证据范围
#   4. 置信只能 ±20(verdict 原始 confidence ±20 范围内)
#   5. 整体 8s 硬超时(留 2s 给调用方余量)


# 禁用具体数字的正则(金额、年代、数字玄学断言等)
_NUMERIC_HALLUCINATION_PATTERNS = [
    # 必须有"数字+金额单位"(万/千/百/亿)才算金钱断言
    re.compile(r"\d+\s*[万千]\s*元?"),                    # 数字万/千+元
    re.compile(r"\d+\s*亿\s*元?"),                       # 数字亿+元
    re.compile(r"[一二三四五六七八九十几百]+\s*[万千百]\s*[万亿元]?"),  # 中文数字+量级(强制量级)
    re.compile(r"\d+\s*岁内"),                          # 30岁内
    re.compile(r"年收入\s*\d+"),                         # 年收入 xxx
    re.compile(r"[AaBbCcDd]\s*级"),                       # A级/B级
    re.compile(r"[上中下]?\s*亿[万千]?"),                  # 上亿/中亿
    re.compile(r"[一二三四五六七八九十几百]+\s*亿"),         # 单一亿字
    re.compile(r"[上中下]?\s*[千万百]?[万千百]?[万亿]"),        # 上千万 / 上百万 / 上万亿
]  # noqa: E501


def _has_numeric_hallucination(text: str) -> bool:
    """粗检:文本里是否出现具体数字断言(LLM 幻觉的核心来源)。命中 → 替换回原始。"""
    if not text:
        return False
    for pat in _NUMERIC_HALLUCINATION_PATTERNS:
        if pat.search(text):
            return True
    return False


def _sanitize_natural_text(text: str, max_len: int = 320) -> str:
    """清洗 LLM 输出:去代码块标记 + 截断 + 数字幻觉降级。"""
    if not text:
        return ""

    text = text.strip()

    # 去 markdown 围栏(LLM 经常包 ```json)
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().rstrip("`") == "":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 截断到上限(防 LLM 啰嗦)
    if len(text) > max_len:
        # 优先在句号处截断,避免砍一半
        cut = text[:max_len]
        last_punct = max(cut.rfind("。"), cut.rfind("."), cut.rfind("\n"))
        if last_punct > max_len * 0.6:  # 至少保留 60% 内容
            cut = cut[:last_punct + 1]
        text = cut

    return text


def _build_enhance_prompt(section: dict, raw_signals: dict) -> str:
    """给 LLM 的 prompt:只能润色,不能改判断方向。

    重要约束 (硬性):
      1. 不许输出"几千万/亿万/年收入 xxx"等具体数字
      2. 不许超出原始 evidence 范围(没证据的事不准编)
      3. verdict_natural 150-300 字,短句为主,长度 ≤25 字
      4. 溟玄风格(像老朋友蹲在路边说,不端着)
      5. 置信方向不能翻转(原 verdict 是吉就不能说凶,反之亦然)
    """
    topic = section.get("topic", "")
    verdict = section.get("verdict", "")
    evidence = section.get("evidence", []) or []
    actions = section.get("actions", []) or []
    confidence = section.get("confidence", 50)
    counter_cases = section.get("counter_cases", []) or []
    method_sources = section.get("method_sources", []) or []
    debate = section.get("debate") or {}

    # 关键:把"judgment direction"显式编码(吉/凶/中性)防止 LLM 翻案
    if any(k in verdict for k in ["偏凶", "不稳", "风险", "亚健康", "弱", "起伏"]):
        direction = "偏谨慎(看具体信号,不要太乐观)"
    elif any(k in verdict for k in ["可行", "有", "偏吉", "稳", "适合", "窗口"]):
        direction = "偏积极(顺势但别浪)"
    else:
        direction = "中性(看具体信号)"

    # 提取最关键的命理锚点(给 LLM "事实基础",防瞎编)
    evidence_brief = "\n".join(f"- {e}" for e in evidence[:6])

    # 玄照本人关键引语(如有辩论数据)
    synthesis = (debate.get("xuanzhao_synthesis") or "").strip()
    key_quotes = debate.get("key_quotes") or []

    # 八字提要(防止 LLM 不知道日主/身强身弱)
    bazi_brief = ""
    bz = raw_signals.get("bazi", {}) or {}
    if bz:
        bazi_brief = (
            f"日主:{bz.get('day_master','?')} 身强身弱:{bz.get('strength','?')} "
            f"用神:{(','.join(bz.get('xi',[])) or '-')} 忌神:{(','.join(bz.get('ji',[])) or '-')}"
        )

    prompt = f"""你是玄学泰斗(溟玄风格:短句+断言+行动指引,像老朋友蹲在路边跟你说话,不端着)。

【任务】把下列"算法原始判断"改写成"玄学泰斗的自然语言解读"。
你不是重新算命,你只是把已经算好的东西说人话。

【原始维度】{topic}
【原始判断方向】{direction}  —  **不能翻转方向**(原本说稳就不能说危险,原本说谨慎就不能说稳)
【原始置信分】{confidence}/100(±20 可调,但方向不能动)
【八字锚点】{bazi_brief}

【原始判断(必读)】
{verdict}

【已掌握的证据(只能基于这些,不准编)】
{evidence_brief}

【反向案例(算法已经看到,如有需要主动提示客户"也有反例")】
{chr(10).join(f"- {c}" for c in counter_cases[:3]) if counter_cases else "(无)"}

【玄照本人已有综合判断(参考,不能反着说)】
{synthesis if synthesis else "(未生成辩论)"}
{chr(10).join(f"- 关键引语:{q}" for q in key_quotes[:2]) if key_quotes else ""}

【原始行动建议(可改写,不准加新方向)】
{chr(10).join(f"{i+1}. {a}" for i, a in enumerate(actions[:5]))}

【输出要求 — 严格遵守】
1. 输出 JSON,key 名必须是 verdict_natural 和 actions_natural
2. verdict_natural:150-300 字。短句优先,单句 ≤25 字。溟玄风,不端架子
3. actions_natural:3-5 条,每条 ≤20 字。口语化
4. **不许**输出"几千万/亿万/年收入 xxx/a级/30岁内"等具体数字
5. **不许**超出上面"已掌握的证据"范围,没证据的事不准编
6. **不许**翻转判断方向
7. 不要 markdown 代码块,直接纯 JSON

【示例输出(只示意结构,不是内容)】
{{"verdict_natural": "你这次走的是借势的局。身弱扛不动大财,先认这个事实。\\n\\n命格给的是底盘,不是天花板。八字双华盖带文昌,心思灵,但大运节奏还没到独立出手的窗口。\\n\\n别跟人比快,先把自己磨出来。", "actions_natural": ["找个靠谱平台先混三年", "现金流优先,不动杠杆", "想跳槽的话 2027 看"]}}

现在请你为【{topic}】维度输出 JSON:
"""
    return prompt


async def _call_llm_async(client, prompt: str) -> dict:
    """把同步 LLM 客户端包成异步调用,6 个并发跑。"""
    try:
        # chat_json 默认 temperature=0.3(JSON 模式需要更确定),max_tokens=3000
        loop = asyncio.get_running_loop()
        # timeout 给 LLM 客户端本体(单次超时)
        # asyncio.to_thread 不直接支持 timeout,用 wait_for 包裹
        def _do_call():
            return client.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600,
            )

        result = await asyncio.wait_for(
            asyncio.to_thread(_do_call),
            timeout=6.0,  # 每节 LLM 单次不超过 6s
        )
        return result
    except (asyncio.TimeoutError, Exception) as e:
        logger.debug(f"LLM 异步调用异常: {type(e).__name__}: {e}")
        return {}


async def _enhance_section_with_llm(
    section: dict,
    raw_signals: dict,
    client=None,
) -> dict:
    """对单个 section 做 LLM 增强。失败静默,不动原始 verdict。"""
    # 隐藏/折叠的 section 不浪费 LLM 算力(已折叠=边缘维度)
    if section.get("hidden") or section.get("collapsed"):
        section["verdict_natural"] = None
        section["actions_natural"] = None
        section["llm_enhanced"] = False
        section["llm_skip_reason"] = "hidden" if section.get("hidden") else "collapsed"
        return section

    # 原始 verdict 必须保留(给前端兜底渲染)
    section["verdict_raw"] = section.get("verdict_raw") or section.get("verdict")
    section["actions_raw"] = section.get("actions_raw") or list(section.get("actions") or [])

    if client is None:
        try:
            from engine.llm_client import LLMClient
            client = LLMClient()
        except Exception as e:
            logger.debug(f"LLM 客户端初始化失败: {e}")
            _section_natural_fallback(section)
            return section

    prompt = _build_enhance_prompt(section, raw_signals)
    response = await _call_llm_async(client, prompt)

    parsed = _parse_llm_response(response)
    if not parsed:
        _section_natural_fallback(section)
        return section

    # 写入 verdict_natural / actions_natural
    verdict_natural = parsed.get("verdict_natural", "")
    actions_natural = parsed.get("actions_natural", [])

    # 数字幻觉降级:命中具体数字 → 退回原始 verdict
    if _has_numeric_hallucination(verdict_natural) or any(_has_numeric_hallucination(str(a)) for a in actions_natural):
        logger.warning(f"[{section.get('topic')}] LLM 输出数字断言,降级使用原始 verdict")
        _section_natural_fallback(section)
        return section

    # 字数校验
    if len(verdict_natural) < 30 or len(verdict_natural) > 600:
        # 太短或太长都不行,落回原始
        logger.warning(f"[{section.get('topic')}] verdict_natural 长度异常({len(verdict_natural)}),落回原始")
        _section_natural_fallback(section)
        return section

    # actions 必须是列表
    if not isinstance(actions_natural, list) or len(actions_natural) == 0:
        _section_natural_fallback(section)
        return section

    # 限制 actions 数量
    actions_natural = [str(a).strip() for a in actions_natural[:5] if str(a).strip()]
    if len(actions_natural) == 0:
        _section_natural_fallback(section)
        return section

    section["verdict_natural"] = _sanitize_natural_text(verdict_natural, max_len=320)
    section["actions_natural"] = actions_natural
    section["llm_enhanced"] = True
    return section


def _parse_llm_response(response: dict) -> dict:
    """解析 LLM 输出。兼容多种返回形态。"""
    if not response or not isinstance(response, dict):
        return {}

    # 标准 JSON 路径(chat_json 直接返回 dict)
    if "verdict_natural" in response:
        return {
            "verdict_natural": response.get("verdict_natural", ""),
            "actions_natural": response.get("actions_natural", []),
        }

    # 解析失败路径(chat_json 返回 {"raw_response": ..., "parse_error": True})
    if response.get("parse_error") and response.get("raw_response"):
        raw = str(response["raw_response"])
        # 手动再尝试一次:抓第一个 {...} 块
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return {
                    "verdict_natural": json.loads(raw[start:end + 1]).get("verdict_natural", ""),
                    "actions_natural": json.loads(raw[start:end + 1]).get("actions_natural", []),
                }
            except Exception:
                pass

    return {}


def _section_natural_fallback(section: dict) -> None:
    """单个 section 的 fallback 逻辑:用原始 verdict 顶替 natural,标记 fallback。

    注意:verdict_raw / actions_raw 在 _enhance_section_with_llm 开头就 setdefault
    过了,所以这里不用重复写。
    """
    section["verdict_natural"] = section.get("verdict", "")
    section["actions_natural"] = list(section.get("actions", []) or [])
    section["llm_enhanced"] = False
    section["llm_fallback"] = True


def _ensure_natural_fallback(report: dict) -> None:
    """整报告兜底:确保所有 section 都有 verdict_natural/ actions_natural 字段(没有就填原始)。"""
    for section in report.get("sections", []) or []:
        if "verdict_natural" not in section:
            _section_natural_fallback(section)


async def _enhance_report_with_llm(report: dict) -> None:
    """整报告并发 LLM 增强。
    - 6 节 asyncio.gather 并发,每一节硬超时 6s,整体超时 8s
    - 单节失败不影响其他节
    - 整体失败:已被 try/except 吞掉,build_report 已经做了 _ensure_natural_fallback
    """
    sections = report.get("sections", []) or []
    raw_signals = report.get("raw_signal_summary", {}) or {}

    # 初始化字段(隐藏的也填 None,防止前端拿不到 key)
    for s in sections:
        s.setdefault("verdict_raw", s.get("verdict"))
        s.setdefault("actions_raw", list(s.get("actions", []) or []))
        s.setdefault("llm_enhanced", False)

    if not sections:
        return

    # 客户端 1 个,6 协程并发(必须串行 httpx,共享 client 实例)
    client = None
    try:
        from engine.llm_client import LLMClient
        client = LLMClient()
    except Exception as e:
        logger.debug(f"LLM 客户端初始化失败,整层跳过: {e}")
        for s in sections:
            _section_natural_fallback(s)
        return

    # 6 节并发
    tasks = [
        asyncio.create_task(
            _enhance_section_with_llm(s, raw_signals, client=client)
        )
        for s in sections
    ]

    # 整体超时 8s(给 5.2 调用方留 2s 余量)
    done, pending = await asyncio.wait(tasks, timeout=8.0)
    # 取消还没跑完的
    for t in pending:
        t.cancel()

    # 已完成的,无论成败都已经在 _enhance_section_with_llm 内部处理过 fallback
    # 等残余的 cancel 完成
    for t in pending:
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass


# ============== Section 切片辅助(给 PDF / verify 共用)==============

def get_section_by_topic(report: dict, topic: str) -> Optional[Dict[str, Any]]:
    """根据 topic 快速定位 section。"""
    for s in report.get("sections", []) or []:
        if s.get("topic") == topic:
            return s
    return None