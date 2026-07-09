#!/usr/bin/env python3
"""
玄照 v2.0 — 八术法共识彩票预测接口

整合六种术法（奇门/六爻/大六壬/太乙/紫微/八字）独立提取号码，
通过跨术法投票共识选出号码。

设计要点：
- 每个术法真正调用对应引擎（不是随机数）
- 单个引擎失败不影响整体（容错）
- 投票共识：3+ 术法命中 → 强候选；5+ → 极强
- 可选：用户提供八字时，按喜用神加权
"""

import logging
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 让相对导入能工作（兼容直接 python 启动与 uvicorn 启动两种方式）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from engine.time_engine import get_time_engine
from engine.base import EngineOrchestrator
from engine.bazi_engine import BaziEngine
from engine.ziwei_engine import ZiWeiEngine
from engine.liuyao_engine import LiuYaoEngine
from engine.qimen_engine import QiMenEngine
from engine.liuren_engine import LiuRenEngine
from engine.taiyi_engine import TaiYiEngine

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════
# 彩票范围定义
# ═══════════════════════════════════════════════════════════
_LOTTERY_RANGES = {
    "dlt": {"type": "lotto", "front": (1, 35), "back": (1, 12), "front_n": 5, "back_n": 2},
    "ssq": {"type": "lotto", "front": (1, 33), "back": (1, 16), "front_n": 6, "back_n": 1},
    "fc3d": {"type": "3d", "main": (0, 9), "n": 3},
    "pl3": {"type": "3d", "main": (0, 9), "n": 3},
}


def _lottery_pool(lottery_type: str) -> Tuple[int, int]:
    """主号码池的范围 (low, high), 含两端."""
    cfg = _LOTTERY_RANGES.get(lottery_type)
    if not cfg:
        return 1, 35
    if cfg["type"] == "lotto":
        return cfg["front"]
    return cfg["main"]


def _lottery_sizes(lottery_type: str) -> Tuple[int, int]:
    """(前区/主区号码数, 后区号码数). 3d类后者为 0."""
    cfg = _LOTTERY_RANGES.get(lottery_type)
    if not cfg:
        return 5, 2
    if cfg["type"] == "lotto":
        return cfg["front_n"], cfg["back_n"]
    return cfg["n"], 0


# ═══════════════════════════════════════════════════════════
# 玄学常数表
# ═══════════════════════════════════════════════════════════
# 12地支 → 1-12 序号
_ZHI_ORDER = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ZHI_NUM = {z: i + 1 for i, z in enumerate(_ZHI_ORDER)}

# 10天干 → 1-10 序号
_GAN_ORDER = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
GAN_NUM = {g: i + 1 for i, g in enumerate(_GAN_ORDER)}

# 五行
WX = {"木": 1, "火": 2, "土": 3, "金": 4, "水": 5}

# 后天八卦数（洛书）
HOU_TIAN = {
    "坎": 1, "坤": 2, "震": 3, "巽": 4,
    "中": 5, "乾": 6, "兑": 7, "艮": 8, "离": 9,
}

# 14主星五行（紫微核心）
# ruff: noqa: F601 — "天府"在两处定义,值都是"土"保持兼容;移除重复避免被静默覆盖
ZIWEI_STAR_WX = {
    "紫微": "土", "天府": "土",
    "太阳": "火", "太阴": "水",
    "武曲": "金", "天同": "水",
    "廉贞": "火",
    "天机": "木", "贪狼": "木",
    "巨门": "水", "天相": "水",
    "天梁": "土", "七杀": "金",
    "破军": "水", "文昌": "金",
    "文曲": "水", "左辅": "土",
    "右弼": "土", "天魁": "火", "天钺": "火",
}

# 纳音五行（60甲子纳音速查）
# 每个甲子组合对应一个五行（30种组合轮转60甲子）
NAYIN_WX = {
    "海中金": "金", "炉中火": "火", "大林木": "木", "路旁土": "土", "剑锋金": "金",
    "山头火": "火", "涧下水": "水", "城头土": "土", "白蜡金": "金", "杨柳木": "木",
    "泉中水": "水", "大海水": "水", "沙中土": "土", "天上火": "火", "覆灯火": "火",
    "沙中金": "金", "山下火": "火", "平地木": "木", "壁上土": "土", "金箔金": "金",
    "覆土": "土", "大溪水": "水", "天河水": "水", "大海": "水", "沙中": "土",
    "石榴木": "木", "大海2": "水", "钗钏金": "金", "桑柘木": "木", "大驿土": "土",
    "沙土": "土", "天上水": "水", "佛灯火": "火", "屋上土": "土",
}

# 简单宽匹配：取字符串尾字对应的五行
def _nayin_to_wx(nayin: str) -> str:
    """纳音字符串→五行. 例 '涧下水' → '水', '石榴木' → '木'."""
    if not nayin:
        return ""
    # 优先精确匹配
    if nayin in NAYIN_WX:
        return NAYIN_WX[nayin]
    # 回退：取最后一个字（多数纳音尾字即五行）
    for ch in reversed(nayin):
        if ch in WX:
            return ch
    return ""


# 五行→号码（基于洛书数延伸）
def _wx_to_candidate_nums(wx_str: str) -> List[int]:
    """五行返回相关号码池（用于3D/排列三）— 用先天数/洛书数映射."""
    if wx_str not in WX:
        return []
    # 先天八卦：乾1兑2离3震4巽5坎6艮7坤8；按五行各给一组
    mapping = {
        "金": [4, 9],   # 乾兑 → 1,2,4,9? 这里用尾4,9
        "木": [3, 8],   # 震巽 → 3,4,8
        "水": [1, 6],   # 坎 → 1,6
        "火": [2, 7],   # 离 → 2,7
        "土": [5],      # 坤中 → 5
    }
    return mapping.get(wx_str, [])


def _wx_to_extended_nums(wx_str: str, low: int, high: int) -> List[int]:
    """五行→区间内的号码（生克数加洛书基础数）."""
    if wx_str not in WX:
        return []
    base = {"金": 4, "木": 3, "水": 1, "火": 2, "土": 5}[wx_str]
    # 该五行对应号码：基础数 + 9循环（在 [low, high] 内）
    out = []
    n = base
    while n <= high:
        if n >= low:
            out.append(n)
        n += 9
    return out


# ═══════════════════════════════════════════════════════════
# 工具：限制到合法号码范围
# ═══════════════════════════════════════════════════════════
def _clamp_pool(nums: List[int], low: int, high: int) -> List[int]:
    seen, out = set(), []
    for n in nums:
        # 用 1..high 循环扩展（在大乐透 1-35 范围里）
        if n == 0:
            continue
        m = n
        while m < low:
            m += 9
        while m > high:
            m -= 9
        if low <= m <= high and m not in seen:
            seen.add(m)
            out.append(m)
    return out


# ═══════════════════════════════════════════════════════════
# 引擎容器：每个术法独立调用一次，避免重复开销
# ═══════════════════════════════════════════════════════════
def _build_divine_orchestrator() -> EngineOrchestrator:
    """注册六大术法引擎（不计占星/姓名学，专注于术数本体）."""
    orch = EngineOrchestrator()
    orch.register(BaziEngine())
    orch.register(ZiWeiEngine())
    orch.register(LiuYaoEngine())
    orch.register(QiMenEngine())
    orch.register(LiuRenEngine())
    orch.register(TaiYiEngine())
    return orch


def _get_divine_orchestrator():
    """惰性单例：避免每次请求都重建引擎对象."""
    global _DIVINE_ORCH
    try:
        _DIVINE_ORCH
    except NameError:
        _DIVINE_ORCH = _build_divine_orchestrator()
    return _DIVINE_ORCH


def _safe_get(d: Optional[Dict], *keys, default=None):
    """多层 dict 安全访问."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur if cur is not None else default


# ═══════════════════════════════════════════════════════════
# 各术法选号实现
# ═══════════════════════════════════════════════════════════
def _pick_qimen(chart: Optional[Dict], low: int, high: int) -> Dict[str, Any]:
    """奇门遁甲选号:
    - 值符所在宫位 (1-9 洛书)
    - 值使门（八门）的宫位
    - 用神落宫（如有）
    - 旺宫评分 top3
    """
    if not chart:
        return {"numbers": [], "reason": "奇门引擎未返回数据"}

    numbers: List[int] = []
    notes: List[str] = []

    # 1. 值符/值使所在宫
    zhi_fu_gong = chart.get("zhi_fu_gong") or _safe_get(chart, "zhi_fu", "gong")
    if isinstance(zhi_fu_gong, int) and 1 <= zhi_fu_gong <= 9:
        numbers.append(zhi_fu_gong)
        notes.append(f"值符{zhi_fu_gong}宫")

    # 2. 时干落宫（即值符所临宫的天盘干，可获九星数 = 直接是宫数）
    time_palace = chart.get("hour_palace_detail") or {}
    if isinstance(time_palace, dict):
        pal = time_palace.get("gong") or time_palace.get("宫")
        if isinstance(pal, int) and 1 <= pal <= 9:
            numbers.append(pal)
            notes.append(f"时干落{pal}宫")

    # 3. 用神落宫
    yong_shen = chart.get("yong_shen") or {}
    if isinstance(yong_shen, dict):
        pal = yong_shen.get("gong") or yong_shen.get("宫")
        if isinstance(pal, int) and 1 <= pal <= 9:
            numbers.append(pal)
            notes.append(f"用神落{pal}宫")

    # 4. 旺宫评分 top3
    palace_scores = chart.get("palace_scores") or {}
    if isinstance(palace_scores, dict):
        scored = []
        for k, v in palace_scores.items():
            try:
                gong = int(k)
                score = float(v) if not isinstance(v, dict) else float(v.get("score", 0))
                scored.append((gong, score))
            except (ValueError, TypeError):
                continue
        scored.sort(key=lambda x: -x[1])
        top = [g for g, _ in scored[:3] if 1 <= g <= 9]
        numbers.extend(top)
        if top:
            notes.append(f"旺宫top3={top}")

    # 5. 宫位高分离散取值（取天盘干转数字）
    palaces = chart.get("palaces") or []
    if isinstance(palaces, list):
        for p in palaces[:3]:
            if not isinstance(p, dict):
                continue
            gong = p.get("gong")
            tpan = p.get("tian_pan", "")
            if isinstance(gong, int) and 1 <= gong <= 9:
                gan_num = GAN_NUM.get(tpan)
                if gan_num:
                    # 天盘干序数映射到合法号码
                    mapped = _clamp_pool([gan_num], low, high)
                    if mapped:
                        numbers.extend(mapped)

    clamped = _clamp_pool(numbers, low, high)
    reason = " · ".join(notes[:4]) if notes else "奇门基础参数"
    return {"numbers": clamped, "reason": reason or "奇门局数映射"}


def _pick_liuyao(chart: Optional[Dict], low: int, high: int) -> Dict[str, Any]:
    """六爻选号:
    - 动爻位置 1-6
    - 本卦地天/变卦卦象 纳甲地支序数
    - 世爻/应爻位置
    """
    if not chart:
        return {"numbers": [], "reason": "六爻未返回数据"}

    numbers: List[int] = []
    notes: List[str] = []

    # 1. 动爻
    dong = chart.get("dong_yao") or []
    if isinstance(dong, list) and dong:
        # 动爻位置 +5循环（在 1-6 内直接保留）
        for d in dong[:4]:
            try:
                pos = int(d)
                if 1 <= pos <= 6:
                    numbers.append(pos)
            except (ValueError, TypeError):
                continue
        notes.append(f"动爻={dong[:4]}")

    # 2. 本卦纳甲六爻地支序数
    lines = chart.get("lines") or []
    if isinstance(lines, list):
        for ln in lines:
            if not isinstance(ln, dict):
                continue
            if not ln.get("is_dong"):
                continue
            zhi = ln.get("dizhi", "")
            znum = ZHI_NUM.get(zhi)
            if znum:
                numbers.append(znum)

    # 3. 变卦纳甲
    bian_lines = chart.get("bian_lines") or []
    if isinstance(bian_lines, list):
        for ln in bian_lines:
            if not isinstance(ln, dict):
                continue
            zhi = ln.get("dizhi", "")
            znum = ZHI_NUM.get(zhi)
            if znum:
                numbers.append(znum + 12 if znum + 12 <= high else znum)

    # 4. 世爻/应爻位置 × 卦宫五行
    shi = chart.get("shi")
    if isinstance(shi, int) and 1 <= shi <= 6:
        numbers.append(shi)
        notes.append(f"世爻={shi}")
    ying = chart.get("ying")
    if isinstance(ying, int) and 1 <= ying <= 6:
        numbers.append(ying)

    # 5. 卦宫五行关联号码
    gwa_wx = chart.get("gua_gong_wuxing") or ""
    if gwa_wx in WX:
        extended = _wx_to_extended_nums(gwa_wx, low, high)
        numbers.extend(extended[:3])
        notes.append(f"卦宫{gwa_wx}→{extended[:3]}")

    clamped = _clamp_pool(numbers, low, high)
    reason = " · ".join(notes[:4]) if notes else "六爻卦象"
    return {"numbers": clamped, "reason": reason}


def _pick_liuren(chart: Optional[Dict], low: int, high: int) -> Dict[str, Any]:
    """大六壬选号:
    - 三传 3 地支 → 12号码
    - 月将所乘地支 → 号码
    - 四课中吉神对应地支
    """
    if not chart:
        return {"numbers": [], "reason": "大六壬未返回数据"}

    numbers: List[int] = []
    notes: List[str] = []

    # 1. 三传（list[3] of [zhi, jiang, liuqin, gan]）
    san_chuan = chart.get("san_chuan") or []
    if isinstance(san_chuan, list):
        chuan_names = ["初传", "中传", "末传"]
        chuan_zhi = []
        for i, chuan in enumerate(san_chuan[:3]):
            zhi = ""
            if isinstance(chuan, (list, tuple)) and chuan:
                # 第一位是地支
                zhi = str(chuan[0]) if chuan[0] else ""
            elif isinstance(chuan, dict):
                zhi = chuan.get("zhi", "")
            znum = ZHI_NUM.get(zhi)
            if znum:
                chuan_zhi.append(znum)
                # 同一地支多个号码变体（位置不同权重不同）
                # 三传的初传核心度最高 → 直接给
                numbers.append(znum)
                if i == 0:
                    notes.append(f"初传{zhi}={znum}")
                elif i == 1:
                    notes.append(f"中传{zhi}={znum}")
                else:
                    notes.append(f"末传{zhi}={znum}")

    # 2. 三传地支五行加权（主五行的扩展数）
    san_chuan_detail = chart.get("san_chuan_detail") or {}
    if isinstance(san_chuan_detail, dict):
        for key in ("chu", "zhong", "mo"):
            d = san_chuan_detail.get(key) or {}
            if not isinstance(d, dict):
                continue
            wx_str = d.get("wuxing", "")
            if wx_str in WX:
                extended = _wx_to_extended_nums(wx_str, low, high)
                # 取扩展的第一组
                for n in extended[:2]:
                    numbers.append(n)

    # 3. 天将吉位（吉将为"大吉/吉"者）
    tian_jiang = chart.get("tian_jiang") or {}
    if isinstance(tian_jiang, dict):
        for zhi, jiang in tian_jiang.items():
            if not jiang or not zhi:
                continue
            # 中文天将名可能繁简不同
            jian = str(jiang)
            if any(c in jian for c in ("贵", "合", "常")) or "吉" in jian:
                znum = ZHI_NUM.get(zhi)
                if znum:
                    numbers.append(znum)

    # 4. 月将地支
    yue_jiang = chart.get("yue_jiang_zhi") or ""
    if yue_jiang in ZHI_NUM:
        numbers.append(ZHI_NUM[yue_jiang])
        notes.append(f"月将{yue_jiang}")

    clamped = _clamp_pool(numbers, low, high)
    reason = " · ".join(notes[:4]) if notes else "三传地支映射"
    return {"numbers": clamped, "reason": reason}


def _pick_taiyi(chart: Optional[Dict], low: int, high: int) -> Dict[str, Any]:
    """太乙选号:
    - 局数 ju_num 1-18
    - 主算首位数字
    - 太乙落宫 taiyi_gong 中提取的数字
    - 太极/太乙数
    """
    if not chart:
        return {"numbers": [], "reason": "太乙未返回数据"}

    numbers: List[int] = []
    notes: List[str] = []

    # 1. 局数（阳遁阴遁各 1-18）
    ju_num = chart.get("ju_num")
    if isinstance(ju_num, (int, float)) and ju_num > 0:
        try:
            ju = int(ju_num)
            numbers.append(ju)
            notes.append(f"局数{ju}")
        except (ValueError, TypeError):
            pass

    # 2. 主算（可能是列表，第一位数字）
    zhu_suan = chart.get("zhu_suan")
    if isinstance(zhu_suan, list) and zhu_suan:
        first = zhu_suan[0]
        if isinstance(first, (int, float)) and first:
            try:
                numbers.append(int(first))
                notes.append(f"主算{first}")
            except (ValueError, TypeError):
                pass

    # 3. 客算
    ke_suan = chart.get("ke_suan")
    if isinstance(ke_suan, list) and ke_suan:
        first = ke_suan[0]
        if isinstance(first, (int, float)) and first:
            try:
                numbers.append(int(first))
                notes.append(f"客算{first}")
            except (ValueError, TypeError):
                pass

    # 4. 太乙落宫提取数字（"兑七宫" → 7）
    taiyi_gong = chart.get("taiyi_gong") or ""
    if isinstance(taiyi_gong, str):
        # 用正则提取数字
        import re
        m = re.search(r"(\d+)", taiyi_gong)
        if m:
            try:
                n = int(m.group(1))
                if 1 <= n <= 18:
                    numbers.append(n)
                    notes.append(f"落宫{taiyi_gong}→{n}")
            except (ValueError, TypeError):
                pass

    # 5. taiyi_num 直接来自表格
    taiyi_num = chart.get("taiyi_num")
    if isinstance(taiyi_num, int) and 1 <= taiyi_num <= 9:
        numbers.append(taiyi_num)

    # 6. 五福/天乙/直符宫位推导
    for key in ("wu_fu", "tian_yi", "di_yi"):
        val = chart.get(key)
        if isinstance(val, str):
            import re
            m = re.search(r"(\d+)", val)
            if m:
                try:
                    numbers.append(int(m.group(1)))
                except (ValueError, TypeError):
                    pass

    clamped = _clamp_pool(numbers, low, high)
    reason = " · ".join(notes[:4]) if notes else "太乙局数主算"
    return {"numbers": clamped, "reason": reason}


def _pick_ziwei(chart: Optional[Dict], bazi_chart: Optional[Dict], low: int, high: int) -> Dict[str, Any]:
    """紫微选号:
    - 命宫地支 (1-12) 序数
    - 化禄/权/科/忌所在星的五行 → 扩展数
    - 十二宫地支序数
    - 命主星五行
    """
    if not chart:
        return {"numbers": [], "reason": "紫微未返回数据"}

    numbers: List[int] = []
    notes: List[str] = []

    # 1. 命宫地支
    ming_gong = chart.get("ming_gong")
    if ming_gong in ZHI_NUM:
        numbers.append(ZHI_NUM[ming_gong])
        notes.append(f"命宫{ming_gong}")

    # 2. 四化星曜（禄/权/科/忌），每化对应一主星
    sihua = chart.get("sihua") or {}
    if isinstance(sihua, dict):
        for huakey, starname in sihua.items():
            if not isinstance(starname, str):
                continue
            wx_str = ZIWEI_STAR_WX.get(starname)
            if wx_str:
                extended = _wx_to_extended_nums(wx_str, low, high)
                numbers.extend(extended[:2])
                notes.append(f"化{huakey}{starname}({wx_str})")
            # 主星本身也加入（与紫微序号 1-14 对应）
            # 14主星各有固定编号：紫微1天府2... 这层不强加，避免噪音

    # 3. 12 宫地支序数
    palaces = chart.get("palaces") or []
    if isinstance(palaces, list):
        # 优先命宫、官禄、财帛（财富类，与彩票相关）
        priority = {"命宫", "官禄", "财帛", "福德"}
        for p in palaces:
            if not isinstance(p, dict):
                continue
            zhi = p.get("zhi", "")
            name = p.get("name", "")
            if name in priority and zhi in ZHI_NUM:
                numbers.append(ZHI_NUM[zhi])

        # 所有 12 宫地支（含五行的吉格）
        for p in palaces:
            if not isinstance(p, dict):
                continue
            major = p.get("major_stars") or []
            if isinstance(major, list):
                for star in major:
                    if isinstance(star, dict):
                        sname = star.get("name", "")
                        wx_str = ZIWEI_STAR_WX.get(sname)
                        if wx_str:
                            ext = _wx_to_extended_nums(wx_str, low, high)
                            if ext:
                                numbers.append(ext[0])

    # 4. 身宫
    shen_gong = chart.get("shen_gong")
    if shen_gong in ZHI_NUM:
        numbers.append(ZHI_NUM[shen_gong])

    # 5. 大限/流年地支
    dai_xian = chart.get("dai_xian") or []
    if isinstance(dai_xian, list):
        for dx in dai_xian[:3]:
            if isinstance(dx, dict):
                gz = dx.get("ganzhi", "")
                if gz and len(gz) >= 2:
                    zhi = gz[1]
                    if zhi in ZHI_NUM:
                        numbers.append(ZHI_NUM[zhi])

    clamped = _clamp_pool(numbers, low, high)
    reason = " · ".join(notes[:4]) if notes else "紫微四化飞星"
    return {"numbers": clamped, "reason": reason}


def _pick_bazi(chart: Optional[Dict], udm, low: int, high: int, has_user_birth: bool) -> Dict[str, Any]:
    """八字选号:
    - 日柱/时柱纳音 → 五行 → 扩展数（核心）
    - 喜用神 (xi_yong) → 五行 → 大幅加权
    - 调候用神 → 五行
    - 日主五行（如果是用户本命日柱，不再额外加，避免重复）
    """
    if not chart:
        return {"numbers": [], "reason": "八字未返回"}

    numbers: List[int] = []
    notes: List[str] = []

    bazi_day = getattr(udm, "bazi_day", None)
    bazi_time = getattr(udm, "bazi_time", None)
    nayin = getattr(udm, "nayin", {}) or {}
    xi_yong = getattr(udm, "xi_yong", {}) or {}
    tiaohou = getattr(udm, "tiaohou", "") or ""

    # 1. 日柱纳音五行
    day_nayin = nayin.get("day", "")
    day_wx = _nayin_to_wx(day_nayin)
    if day_wx:
        ext = _wx_to_extended_nums(day_wx, low, high)
        numbers.extend(ext)
        notes.append(f"日柱{day_nayin}({day_wx})")

    # 2. 时柱纳音（用事之时，与彩票抽取时机近似）
    time_nayin = nayin.get("time", "")
    time_wx = _nayin_to_wx(time_nayin)
    if time_wx and time_wx != day_wx:
        ext = _wx_to_extended_nums(time_wx, low, high)
        numbers.extend(ext[:2])
        notes.append(f"时柱{time_nayin}({time_wx})")

    # 3. 月柱纳音
    month_nayin = nayin.get("month", "")
    month_wx = _nayin_to_wx(month_nayin)
    if month_wx:
        ext = _wx_to_extended_nums(month_wx, low, high)
        numbers.extend(ext[:2])
        notes.append(f"月柱{month_nayin}({month_wx})")

    # 4. 喜用神（如果有用户八字，则用本命喜用神加权）
    if has_user_birth:
        xi = xi_yong.get("xi") or []
        ji = xi_yong.get("ji") or []
        for wx_str in xi:
            if wx_str in WX:
                ext = _wx_to_extended_nums(wx_str, low, high)
                # 喜用神权重最高，每个都加入
                numbers.extend(ext)
        if xi:
            notes.append(f"喜用神{'+'.join(xi)}")

        # 调候用神（天干）
        if tiaohou:
            for gan in tiaohou:
                w = GAN_NUM.get(gan)
                if w:
                    # 天干序号当作洛书位
                    mapped = _clamp_pool([w], low, high)
                    if mapped:
                        numbers.append(mapped[0])

        # 年柱纳音（出生年的运气）
        year_nayin = nayin.get("year", "")
        year_wx = _nayin_to_wx(year_nayin)
        if year_wx:
            ext = _wx_to_extended_nums(year_wx, low, high)
            numbers.extend(ext[:2])
    else:
        # 不用命主喜用神（因为是抽取时机而非用户本命），只用调候
        # 调候可作为"时机之喜"
        if tiaohou:
            tiaohou_wx = [_nayin_to_wx(g) for g in tiaohou]
            # 调候天干 → 五行（拆字取五行）
            for g in tiaohou:
                # 简易：天干对应五行
                tg_wx = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
                         "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}.get(g)
                if tg_wx:
                    ext = _wx_to_extended_nums(tg_wx, low, high)
                    numbers.extend(ext[:1])

    clamped = _clamp_pool(numbers, low, high)
    reason = " · ".join(notes[:4]) if notes else "八字纳音"
    return {"numbers": clamped, "reason": reason}


# ═══════════════════════════════════════════════════════════
# 综合投票
# ═══════════════════════════════════════════════════════════
def _voting_consensus(
    picks: Dict[str, Dict[str, Any]],
    weights: Dict[str, float],
    low: int,
    high: int,
    user_favor_wx: Optional[List[str]] = None,
) -> Tuple[Dict[int, int], Counter, List[int]]:
    """
    对各术法给出的号码投票。
    返回:
      - score_map {号码: 总加权得分}
      - counter  {号码: 命中的术法数}
      - favor_nums 用户喜用神对应的优先号码
    """
    counter: Counter = Counter()
    score: Dict[int, float] = defaultdict(float)

    for method, p in picks.items():
        ns = p.get("numbers") or []
        w = weights.get(method, 0.5)
        for n in ns:
            if low <= n <= high:
                counter[n] += 1
                score[n] += w

    # 用户喜用神加权
    if user_favor_wx:
        for wx_str in user_favor_wx:
            ext = _wx_to_extended_nums(wx_str, low, high)
            for n in ext:
                if low <= n <= high:
                    score[n] += 0.5  # 喜用神额外加权
                    counter.setdefault(n, counter.get(n, 0))

    return dict(score), counter, []


def _consensus_tiers(counter: Counter) -> Dict[str, List[int]]:
    """根据跨术法命中数分层: strong (5+), moderate (3-4), weak (2)."""
    strong, moderate, weak = [], [], []
    for n, c in sorted(counter.items(), key=lambda x: -x[1]):
        if c >= 5:
            strong.append(n)
        elif c >= 3:
            moderate.append(n)
        elif c >= 2:
            weak.append(n)
    return {"strong": strong, "moderate": moderate, "weak": weak}


def _select_final_recommendations(
    score_map: Dict[int, float],
    counter: Counter,
    lottery_type: str,
    rng_seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """从候选中选最终推荐号码组合."""
    cfg = _LOTTERY_RANGES.get(lottery_type)
    if not cfg:
        return []

    import random
    rng = random.Random(rng_seed) if rng_seed is not None else random.Random()

    # 候选排序：score高的在前
    candidates = sorted(score_map.keys(), key=lambda n: (-score_map.get(n, 0), n))
    if len(candidates) < 10:
        # 候选不足时随机补全（在合法范围内）
        if cfg["type"] == "3d":
            all_n = list(range(cfg["main"][0], cfg["main"][1] + 1))
        else:
            all_n = list(range(cfg["front"][0], cfg["front"][1] + 1))
        rng.shuffle(all_n)
        for n in all_n:
            if n not in candidates:
                candidates.append(n)
            if len(candidates) >= 20:
                break

    if cfg["type"] == "3d":
        # 3D/PL3: 选 3 个号
        picks = candidates[:3]
        return [{
            "rank": 1,
            "numbers": sorted(picks),
            "front": sorted(picks),
            "back": [],
            "score": round(score_map.get(picks[0], 0) / max(len(picks), 1), 2),
            "method_count": len([n for n in picks if counter.get(n, 0) > 0]),
            "confidence": round(min(0.95, sum(score_map.get(n, 0) for n in picks) / 6.0), 2),
            "reason": "六术法共识投票",
        }]

    # 乐透
    front_n = cfg["front_n"]
    back_n = cfg["back_n"]
    if cfg["type"] == "3d":
        # 3D 类型已在前面早返回,这里再防御一次
        return []
    front_pool = [n for n in candidates if cfg["front"][0] <= n <= cfg["front"][1]]
    back_pool = [n for n in candidates if cfg["back"][0] <= n <= cfg["back"][1]]

    # 后区补全
    if len(back_pool) < back_n:
        all_back = list(range(cfg["back"][0], cfg["back"][1] + 1))
        rng.shuffle(all_back)
        for n in all_back:
            if n not in back_pool:
                back_pool.append(n)
            if len(back_pool) >= back_n * 2:
                break
    back_pool = back_pool[:back_n]

    # 前区补全（候选不够时）
    if len(front_pool) < front_n:
        all_front = list(range(cfg["front"][0], cfg["front"][1] + 1))
        rng.shuffle(all_front)
        for n in all_front:
            if n not in front_pool:
                front_pool.append(n)
            if len(front_pool) >= front_n * 2:
                break

    front_pick = sorted(front_pool[:front_n])
    return [{
        "rank": 1,
        "numbers": front_pick + back_pool,
        "front": front_pick,
        "back": back_pool,
        "score": round(sum(score_map.get(n, 0) for n in front_pick) / max(front_n, 1), 2),
        "method_count": len([n for n in front_pick if counter.get(n, 0) > 0]) +
                        len([n for n in back_pool if counter.get(n, 0) > 0]),
        "confidence": round(min(0.95, sum(score_map.get(n, 0) for n in front_pick + back_pool) / 8.0), 2),
        "reason": "六术法共识投票（前区+后区）",
    }]


# ═══════════════════════════════════════════════════════════
# 主路由
# ═══════════════════════════════════════════════════════════
def _err(msg: str, code: int = 500):
    return JSONResponse(status_code=code, content={"error": msg})


@router.get("/api/divine-lottery/predict")
def divine_lottery_predict(
    lottery_type: str = Query("dlt", description="彩票类型: dlt/ssq/fc3d/pl3"),
    target_date: Optional[str] = Query(None, description="目标日期 YYYY-MM-DD, 默认今天"),
    target_hour: int = Query(21, ge=0, le=23, description="目标时辰(0-23), 默认21=戌时(常见开奖时间)"),
    birth: Optional[str] = Query(None, description="用户八字（可选）格式: YYYY-MM-DD HH:MM"),
    location: str = Query("北京", description="出生/排盘地点"),
    gender: str = Query("男", description="性别: 男/女"),
):
    """八术法共识选号."""
    try:
        # 1. 参数解析
        lottery_type = lottery_type.lower().strip()
        if lottery_type not in _LOTTERY_RANGES:
            return _err(f"不支持的彩票类型: {lottery_type}", 400)
        low, high = _lottery_pool(lottery_type)

        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        # 用 target_date + target_hour 作为起卦时间
        try:
            birth_dt = datetime.strptime(target_date, "%Y-%m-%d")
            target_dt = birth_dt.replace(hour=target_hour, minute=0, second=0)
        except ValueError:
            return _err(f"日期格式错误: {target_date}", 400)
        target_dt_str = target_dt.strftime("%Y-%m-%d %H:%M")

        # 2. 时间校正
        te = get_time_engine()
        corrected = te.correct(target_dt_str, location)

        # 3. 排盘
        orch = _get_divine_orchestrator()
        gender_code = 1 if gender in ("男", "male", "m", "M", "1") else 0
        udm = orch.run_all(corrected, gender_code)

        # 4. 用户八字（如提供）— 用于喜用神加权
        user_favor_wx: List[str] = []
        user_birth_udm = None
        if birth:
            try:
                user_corrected = te.correct(birth, location)
                # 用户命盘也用同样的 orch（这样能复用引擎实例 / 缓存）
                user_birth_udm = orch.run_all(user_corrected, gender_code)
                xi_yong = getattr(user_birth_udm, "xi_yong", {}) or {}
                user_favor_wx = xi_yong.get("xi") or []
            except Exception as e:
                logger.warning(f"用户八字校正失败（忽略喜用神加权）: {e}")

        # 5. 提取每个术法选号
        weights = {
            "qimen": 0.85,
            "liuyao": 0.80,
            "liuren": 0.75,
            "taiyi": 0.70,
            "ziwei": 0.85,
            "bazi": 0.85,
        }
        picks: Dict[str, Dict[str, Any]] = {}

        try:
            picks["qimen"] = _pick_qimen(udm.qimen_chart, low, high)
        except Exception as e:
            logger.warning(f"奇门选号失败: {e}")
            picks["qimen"] = {"numbers": [], "reason": f"异常: {e}"}

        try:
            picks["liuyao"] = _pick_liuyao(udm.liuyao_chart, low, high)
        except Exception as e:
            logger.warning(f"六爻选号失败: {e}")
            picks["liuyao"] = {"numbers": [], "reason": f"异常: {e}"}

        try:
            picks["liuren"] = _pick_liuren(udm.liuren_chart, low, high)
        except Exception as e:
            logger.warning(f"大六壬选号失败: {e}")
            picks["liuren"] = {"numbers": [], "reason": f"异常: {e}"}

        try:
            picks["taiyi"] = _pick_taiyi(udm.taiyi_chart, low, high)
        except Exception as e:
            logger.warning(f"太乙选号失败: {e}")
            picks["taiyi"] = {"numbers": [], "reason": f"异常: {e}"}

        try:
            picks["ziwei"] = _pick_ziwei(udm.ziwei_chart, udm.bazi_day, low, high)
        except Exception as e:
            logger.warning(f"紫微选号失败: {e}")
            picks["ziwei"] = {"numbers": [], "reason": f"异常: {e}"}

        try:
            picks["bazi"] = _pick_bazi(udm.bazi_chart if hasattr(udm, "bazi_chart") else None, udm, low, high, has_user_birth=bool(birth))
        except Exception as e:
            logger.warning(f"八字选号失败: {e}")
            picks["bazi"] = {"numbers": [], "reason": f"异常: {e}"}

        # 6. 投票共识
        score_map, counter, _ = _voting_consensus(
            picks, weights, low, high, user_favor_wx=user_favor_wx or None
        )

        # 7. 分层
        tiers = _consensus_tiers(counter)

        # 8. 最终推荐（用 target_date 当随机种子使结果稳定）
        seed = int(target_dt.timestamp()) // 600  # 10分钟粒度
        recs = _select_final_recommendations(score_map, counter, lottery_type, rng_seed=seed)

        # 9. 整理返回
        divination_results = {}
        for method, p in picks.items():
            divination_results[method] = {
                "numbers": p.get("numbers", []),
                "weight": weights.get(method, 0.5),
                "reason": p.get("reason", ""),
            }

        return {
            "date": target_date,
            "lottery_type": lottery_type,
            "target_hour": target_hour,
            "draw_time_gz": {
                "day": getattr(udm.bazi_day, "ganzhi", "") if udm.bazi_day else "",
                "time": getattr(udm.bazi_time, "ganzhi", "") if udm.bazi_time else "",
            },
            "methods_used": udm.get_available_methods(),
            "engine_errors": udm.engine_errors,
            "divination_results": divination_results,
            "consensus": tiers,
            "all_scored": dict(sorted(score_map.items(), key=lambda x: -x[1])[:20]),
            "recommendations": recs,
            "user_birth_used": bool(birth),
            "user_favor_wx": user_favor_wx,
            "disclaimer": (
                "基于六术法独立排盘 + 加权投票共识的号码组合。"
                "中奖仍是极小概率事件。本接口仅供文化研究与娱乐参考。"
            ),
        }
    except Exception as e:
        logger.exception("divine_lottery_predict failed")
        return _err(f"操作失败: {e}", 500)


@router.get("/api/divine-lottery/methods")
def list_methods():
    """列出可用的术法及其权重."""
    return {
        "methods": [
            {"name": "qimen", "cn": "奇门遁甲", "weight": 0.85, "description": "时家转盘 · 九宫洛书"},
            {"name": "liuyao", "cn": "六爻", "weight": 0.80, "description": "纳甲六爻 · 动爻卦象"},
            {"name": "liuren", "cn": "大六壬", "weight": 0.75, "description": "四课三传 · 天将"},
            {"name": "taiyi", "cn": "太乙", "weight": 0.70, "description": "积年局数 · 落宫主算"},
            {"name": "ziwei", "cn": "紫微斗数", "weight": 0.85, "description": "命宫四化 · 主星五行"},
            {"name": "bazi", "cn": "八字", "weight": 0.85, "description": "日时纳音 · 喜用神"},
        ],
        "lottery_types": list(_LOTTERY_RANGES.keys()),
        "voting": "numbers appearing in ≥5 methods = strongest; ≥3 = strong; ≥2 = moderate.",
    }
