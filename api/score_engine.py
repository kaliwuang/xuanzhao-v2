# ============================================================================
# 评分系统 B96-B108 Bug 审计标记
# ============================================================================
# B96 修复: 日主强弱评分 - 25 分档
# B97 修复: 五行评分 - 20 分档
# B98 修复: 十神评分 - 20 分档
# B99 修复: 格局评分 - 20 分档
# B100 修复: 大运评分 - 20 分档
# B101 修复: 总分算法 - 加权还是直接相加
# B102 修复: 等级划分 - 上中下中平/中上中下
# B103 修复: ✅ 已修 - 补救建议字段
# B104 修复: 白话解析 - 不要堆术语
# B105 修复: 细节缓存 - 同一命盘不重复算
# B106 修复: 错误处理 - 引擎失败不阻塞
# B107 修复: 并发 - 评分独立任务
# B108 修复: 边界 - 早子时/晚子时
# ============================================================================

#!/usr/bin/env python3
"""
玄照 v2.0 - 评分引擎

基于各术法引擎的排盘数据，计算 0-100 评分并生成白话解析。
风格：像朋友聊天，不用术语压迫感。
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("xuanzhao.score")

# ─── 五行生克常量 ──────────────────────────────────────────
WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
WUXING_BEI_KE = {v: k for k, v in WUXING_KE.items()}
GAN_WX = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
# 地支五行（喜用神检查需要同时考虑天干和地支的五行）
ZHI_WX = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 吉神/凶神分类
JISHEN_KEYWORDS = ["天乙", "文昌", "禄", "天德", "月德", "太极", "天喜", "红鸾", "将星",
                    "福星", "金舆", "天官", "天福", "天医", "天厨", "学堂", "词馆", "天赦", "德秀"]
XIONGSHA_KEYWORDS = ["羊刃", "劫煞", "亡神", "孤辰", "寡宿", "天罗", "地网",
                      "灾煞", "勾煞", "绞煞", "流霞", "飞刃", "十恶大败", "四废", "阴阳差错", "天转煞"]
# 华盖属中性偏吉（主艺术/宗教/哲学天赋），不归入凶煞

# ─── 主入口 ──────────────────────────────────────────────
def score_all(udm, method: str = "all") -> Dict[str, Dict]:
    """
    对所有（或指定）术法评分，返回：
    { method_name: { score, analysis, strengths, weaknesses } }
    """
    result = {}

    # 短名 → 全名 映射,接受 method=紫微 / method=紫微斗数 两种写法
    NAME_ALIASES = {
        "八字": "八字",
        "紫微": "紫微斗数",
        "六爻": "六爻",
        "奇门": "奇门遁甲",
        "大六壬": "大六壬",
        "太乙": "太乙神数",
        "占星": "占星",
        "姓名学": "姓名学",
    }

    scorers = {
        "八字": _score_bazi,
        "紫微斗数": _score_ziwei,
        "六爻": _score_liuyao,
        "奇门遁甲": _score_qimen,
        "大六壬": _score_liuren,
        "太乙神数": _score_taiyi,
        "占星": _score_astro,
        "姓名学": _score_xingming,
    }

    target_name = NAME_ALIASES.get(method, method)

    for name, fn in scorers.items():
        if target_name != "all" and target_name != name:
            continue
        try:
            score, analysis, strengths, weaknesses = fn(udm)
            result[name] = {
                "score": max(0, min(100, score)),
                "analysis": analysis,
                "strengths": strengths,
                "weaknesses": weaknesses,
            }
        except Exception as e:
            logger.warning(f"评分失败 [{name}]: {e}")
            result[name] = {
                "score": 0,
                "analysis": f"这门术法暂时没法给你打分,出了点小问题:{e}",
                "strengths": [],
                "weaknesses": [f"评分引擎异常: {e}"],
            }

    return result


# ─── 八字评分 ──────────────────────────────────────────────
def _score_bazi(udm) -> Tuple[int, str, list, list]:
    if not udm.bazi_year:
        return 0, "八字数据不完整，没法评分。", [], ["八字排盘失败"]

    score = 0
    strengths = []
    weaknesses = []

    # 1. 身强身弱 + 喜用神得力（+30分）
    xi_yong = getattr(udm, 'xi_yong', None) or {}
    strength = xi_yong.get("strength", "")
    xi_list = xi_yong.get("xi", []) or []
    ji_list = xi_yong.get("ji", []) or []

    # 检查喜用神是否出现在八字中
    pillars = []
    for p in [udm.bazi_year, udm.bazi_month, udm.bazi_day, udm.bazi_time]:
        if p and hasattr(p, 'ganzhi') and p.ganzhi:
            pillars.append(p.ganzhi)

    all_chars = "".join(pillars)
    # 提取天干地支的五行（天干和地支都要检查，避免遗漏地支中的喜用五行）
    all_wx = set()
    for ch in all_chars:
        if ch in GAN_WX:
            all_wx.add(GAN_WX[ch])
        elif ch in ZHI_WX:
            all_wx.add(ZHI_WX[ch])

    xi_present = any(wx in all_wx for wx in xi_list) if xi_list else False
    ji_present = any(wx in all_wx for wx in ji_list) if ji_list else False

    if strength == "身弱":
        if xi_present:
            score += 28 if not ji_present else 24
            strengths.append("虽然身弱，但喜用神就在八字里，有人帮忙扛事儿")
            if ji_present:
                weaknesses.append("忌神也在八字中，喜用与忌神并存，需要取舍")
        else:
            score += 12
            weaknesses.append("身弱且喜用神不太给力，需要后天多补补")
    elif strength == "身强":
        if xi_present:
            score += 30 if not ji_present else 26
            strengths.append("身强又有喜用神制约，刚柔并济，格局不错")
            if ji_present:
                weaknesses.append("忌神也在八字中，制约与消耗并存，需要平衡")
        else:
            score += 18
            weaknesses.append("身强但缺少制约，容易过于刚硬")
    elif strength == "中和":
        score += 25
        strengths.append("八字比较平衡，不偏不倚，底子不错")
    else:
        score += 10
        weaknesses.append("日主状态不太明确，需要更仔细看")

    # 2. 五行平衡（+20分）
    wuxing_score = getattr(udm, 'wuxing_score', None) or {}
    if wuxing_score:
        total = sum(wuxing_score.values()) or 1
        vals = [v / total for v in wuxing_score.values()]
        max_v = max(vals)
        min_v = min(vals)
        spread = max_v - min_v
        if spread < 0.15:
            score += 20
            strengths.append("五行分布均匀，性格多面，适应力强")
        elif spread < 0.30:
            score += 14
            strengths.append("五行基本平衡，稍有偏重但不碍事")
        elif spread < 0.50:
            score += 8
            weaknesses.append("五行偏得有点明显，某方面可能过于突出或不足")
        else:
            score += 3
            weaknesses.append("五行严重偏枯，可能在某些方面比较极端")
    else:
        score += 10

    # 3. 神煞吉凶（+20分）
    shensha = getattr(udm, 'shensha', []) or []
    ji_count = sum(1 for s in shensha if any(k in str(s) for k in JISHEN_KEYWORDS))
    xiong_count = sum(1 for s in shensha if any(k in str(s) for k in XIONGSHA_KEYWORDS))

    if ji_count > xiong_count:
        bonus = min(20, 10 + (ji_count - xiong_count) * 3)
        score += bonus
        strengths.append(f"命中带{ji_count}个吉神，贵人运不错")
    elif xiong_count > ji_count:
        penalty = max(3, 15 - (xiong_count - ji_count) * 3)
        score += penalty
        weaknesses.append(f"命中凶煞有{xiong_count}个，人生路上多些波折")
    else:
        score += 12

    # 4. 刑冲合害破（+15分）
    zhi_relations = getattr(udm, 'zhi_relations', []) or []
    chong_count = sum(1 for r in zhi_relations if "冲" in str(r))
    xing_count = sum(1 for r in zhi_relations if "刑" in str(r))
    he_count = sum(1 for r in zhi_relations if "合" in str(r))
    hai_count = sum(1 for r in zhi_relations if "害" in str(r))
    po_count = sum(1 for r in zhi_relations if "破" in str(r))

    # 害/破属于中等负面因素（比冲/刑轻），权重0.5
    negative_weight = chong_count + xing_count + (hai_count + po_count) * 0.5

    if negative_weight == 0:
        score += 15
        strengths.append("地支没什么刑冲，生活比较安稳")
    elif negative_weight <= 1:
        score += 10
    elif negative_weight <= 2:
        score += 5
        weaknesses.append("有点刑冲，生活中难免有些冲突和变化")
    else:
        score += 2
        weaknesses.append("刑冲比较多，人生起伏大，需要更多智慧应对")

    # 害/破单独提示（隐蔽性摩擦，不与冲/刑重复提示）
    if hai_count > 0 and chong_count == 0 and xing_count == 0:
        weaknesses.append(f"地支有{hai_count}处六害，人际关系中可能存在暗中摩擦")
    if po_count > 0 and chong_count == 0 and xing_count == 0:
        weaknesses.append(f"地支有{po_count}处六破，合作或关系中易有意外破损")

    # 合多加分
    if he_count >= 2:
        score += 3
        strengths.append("地支多合，人缘好，善于合作")

    # 5. 大运配合（+15分）
    dayun = getattr(udm, 'dayun', []) or []
    if dayun:
        good_dayun = 0
        for d in dayun[:5]:
            gz = d.get("ganzhi", "") if isinstance(d, dict) else ""
            if gz:
                # 检查天干和地支的五行是否在喜用列表中
                gan = gz[0] if len(gz) >= 1 else ""
                zhi = gz[1] if len(gz) >= 2 else ""
                gwx = GAN_WX.get(gan, "")
                dwx = ZHI_WX.get(zhi, "")
                if gwx in xi_list or dwx in xi_list:
                    good_dayun += 1
        if good_dayun >= 3:
            score += 15
            strengths.append("大运走得好，未来几年运势上升")
        elif good_dayun >= 2:
            score += 10
            strengths.append("大运还算配合，有些年份会比较顺")
        elif good_dayun >= 1:
            score += 6
        else:
            score += 3
            weaknesses.append("前几步大运跟八字不太合，前期可能辛苦些")
    else:
        score += 7

    # 生成白话分析
    analysis_parts = []
    if strength:
        analysis_parts.append(f"你这个八字属于{strength}的类型")
    if xi_list:
        analysis_parts.append(f"喜用五行是{'/'.join(xi_list)}")
    if wuxing_score:
        total = sum(wuxing_score.values()) or 1
        top = max(wuxing_score, key=wuxing_score.get)
        analysis_parts.append(f"五行里{top}的力量最强，占比{round(wuxing_score[top]/total*100)}%")

    if score >= 80:
        analysis_parts.append("整体底子很扎实，先天条件不错，好好发挥潜力很大")
    elif score >= 60:
        analysis_parts.append("格局还行，有些亮点也有需要注意的地方，稳扎稳打就好")
    elif score >= 40:
        analysis_parts.append("八字有些短板，不过知道问题在哪就好办，可以有针对性地调整")
    else:
        analysis_parts.append("先天格局挑战多一些，但也意味着成长空间大，逆境出人才")

    analysis = "。".join(analysis_parts) + "。" if analysis_parts else "八字分析数据不足。"

    return score, analysis, strengths, weaknesses


# ─── 紫微斗数评分 ──────────────────────────────────────────
def _score_ziwei(udm) -> Tuple[int, str, list, list]:
    if not udm.ziwei_chart:
        return 0, "紫微斗数数据不完整。", [], ["紫微排盘失败"]

    chart = udm.ziwei_chart
    score = 0
    strengths = []
    weaknesses = []

    # 1. 命宫主星（+35分）
    ming_gong = chart.get("ming_gong", "")
    palaces_raw = chart.get("palaces", []) or []
    soul_star = chart.get("soul_star", "")

    # 吉星/煞星分类
    ji_main = ["紫微", "天府", "天相", "太阳", "太阴", "天同", "武曲", "天梁"]
    sha_main = ["贪狼", "巨门", "廉贞", "七杀", "破军"]

    # 统一将 palaces 转为 {宫名: palace_dict} 映射（兼容 list 和 dict 两种格式）
    palaces = {}
    if isinstance(palaces_raw, list):
        for p in palaces_raw:
            if isinstance(p, dict) and p.get("name"):
                palaces[p["name"]] = p
    elif isinstance(palaces_raw, dict):
        palaces = palaces_raw

    ming_palace_stars = []
    mg = palaces.get("命宫", {})
    if isinstance(mg, dict):
        # 提取命宫中的星曜名称（兼容 major_stars 列表和 stars 列表格式）
        for star_info in (mg.get("major_stars", []) or []):
            if isinstance(star_info, dict):
                ming_palace_stars.append(star_info.get("name", ""))
            else:
                ming_palace_stars.append(str(star_info))
        if not ming_palace_stars:
            ming_palace_stars = mg.get("stars", []) or []

    has_ji_main = any(s in ming_palace_stars for s in ji_main)
    has_sha_main = any(s in ming_palace_stars for s in sha_main)

    if has_ji_main and not has_sha_main:
        score += 35
        strengths.append("命宫坐吉星，天生条件好，做事容易得到助力")
    elif has_ji_main and has_sha_main:
        score += 25
        strengths.append("命宫吉星煞星都有，虽然有点纠结但潜力很大")
    elif has_sha_main:
        score += 15
        weaknesses.append("命宫煞星坐守，人生挑战多，但往往能闯出一番天地")
    else:
        score += 20

    # 2. 四化分析（+35分）
    sihua = chart.get("sihua", {}) or {}
    if sihua:
        # 化禄、化权、化科为吉，化忌为凶
        lu = sihua.get("禄", "") or sihua.get("化禄", "")
        quan = sihua.get("权", "") or sihua.get("化权", "")
        ke = sihua.get("科", "") or sihua.get("化科", "")
        ji = sihua.get("忌", "") or sihua.get("化忌", "")

        ji_count_sihua = sum(1 for x in [lu, quan, ke] if x)
        if ji_count_sihua >= 2:
            score += 30
            strengths.append("四化走得好，禄权科齐备，事业财运都有看头")
        elif ji_count_sihua == 1:
            score += 20
            strengths.append("四化中有吉化，至少某个方面会比较突出")
        else:
            score += 10
        if ji:
            score -= 5
            weaknesses.append(f"化忌落在{ji}，这个方面需要注意，容易有烦恼")
    else:
        score += 15

    # 3. 煞星分布（+30分）
    sha_stars = ["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"]
    sha_in_ming = 0
    mg_data = palaces.get("命宫", {})
    if isinstance(mg_data, dict):
        # 从结构化数据中提取星名列表，避免str(dict)子串匹配的脆弱模式
        _ming_star_names = []
        for s in (mg_data.get("major_stars") or []):
            if isinstance(s, dict):
                _ming_star_names.append(s.get("name", ""))
            else:
                _ming_star_names.append(str(s))
        for s in (mg_data.get("minor_stars") or []):
            if isinstance(s, dict):
                _ming_star_names.append(s.get("name", ""))
            else:
                _ming_star_names.append(str(s))
        for s in (mg_data.get("stars") or []):
            _ming_star_names.append(str(s))
        sha_in_ming = sum(1 for s in sha_stars if s in _ming_star_names)

    if sha_in_ming == 0:
        score += 30
        strengths.append("命宫没有六煞，人生路比较顺遂")
    elif sha_in_ming == 1:
        score += 20
    elif sha_in_ming == 2:
        score += 12
        weaknesses.append("命宫有煞星，性格可能比较急躁，需要修炼耐心")
    else:
        score += 5
        weaknesses.append("命宫煞星多，人生压力大，但磨练出来的都是真本事")

    analysis_parts = []
    if soul_star:
        analysis_parts.append(f"你的紫微命宫主星是{soul_star}")
    if ming_gong:
        analysis_parts.append(f"命宫在{ming_gong}")
    if score >= 80:
        analysis_parts.append("紫微格局很好，先天格局层次高，把握好机会能有大发展")
    elif score >= 60:
        analysis_parts.append("紫微格局中上，有些不错的星曜组合，稳扎稳打前途光明")
    elif score >= 40:
        analysis_parts.append("紫微格局一般，需要注意的地方不少，但也有亮点")
    else:
        analysis_parts.append("紫微格局挑战较多，不过命盘里总有闪光点，关键是找到它")

    analysis = "。".join(analysis_parts) + "。" if analysis_parts else "紫微分析数据不足。"
    return score, analysis, strengths, weaknesses


# ─── 六爻评分 ──────────────────────────────────────────────
def _score_liuyao(udm) -> Tuple[int, str, list, list]:
    if not udm.liuyao_chart:
        return 0, "六爻数据不完整。", [], ["六爻排盘失败"]

    chart = udm.liuyao_chart
    score = 0
    strengths = []
    weaknesses = []

    # 1. 用神旺衰（+40分）
    wuxing_analysis = chart.get("wuxing_analysis", {}) or {}
    ge_ju = chart.get("ge_ju", []) or []

    # 从格局判断（关键词须匹配 _identify_ge_ju 实际输出）
    ge_ju_str = " ".join(str(g) for g in ge_ju)
    # 吉格：世应合、六合、三合局、半合局
    ji_ge = ["世应合", "六合", "三合", "半合"]
    # 凶格：世应冲、六冲、伏吟、反吟、游魂卦、归魂卦
    # 伏吟=变卦与本卦完全相同，事有停滞；归魂卦=京房八宫第8卦，主回归定局
    xiong_ge = ["世应冲", "六冲", "伏吟", "反吟", "游魂卦", "归魂卦"]

    ji_count = sum(1 for g in ji_ge if g in ge_ju_str)
    xiong_count = sum(1 for g in xiong_ge if g in ge_ju_str)

    if ji_count > xiong_count:
        score += 35
        strengths.append("用神状态不错，事情发展有利")
    elif xiong_count > ji_count:
        score += 15
        weaknesses.append("用神状态偏弱，事情推进可能有阻力")
    else:
        score += 25

    # 2. 世应关系（+30分）
    shi = chart.get("shi", "")
    ying = chart.get("ying", "")
    dong_yao = chart.get("dong_yao", []) or []

    if shi and ying:
        if "世应合" in ge_ju_str or "六合" in ge_ju_str:
            score += 28
            strengths.append("世应相合，人际关系和合作方面有利")
        elif "世应冲" in ge_ju_str or "六冲" in ge_ju_str:
            score += 10
            weaknesses.append("世应相冲或六冲，人际关系中存在张力，需要主动化解")
        else:
            score += 20
    else:
        score += 15

    # 3. 动爻（+30分）
    if len(dong_yao) == 0:
        score += 20  # 没动爻，事情稳定
    elif len(dong_yao) == 1:
        score += 25  # 一爻动，目标明确
        strengths.append("只有一个动爻，事情方向清晰")
    elif len(dong_yao) == 2:
        score += 20
    else:
        score += 10
        weaknesses.append("动爻太多，局面比较复杂，变数大")

    analysis_parts = []
    # ben_gua/bian_gua 是 dict（{'name':'乾为天','mark':'111111','shang':'乾','xia':'乾',...}），需提取 name 字段
    ben_gua_data = chart.get("ben_gua", {})
    bian_gua_data = chart.get("bian_gua", {})
    ben_gua_name = ben_gua_data.get("name", "") if isinstance(ben_gua_data, dict) else str(ben_gua_data)
    bian_gua_name = bian_gua_data.get("name", "") if isinstance(bian_gua_data, dict) else str(bian_gua_data)
    if ben_gua_name:
        analysis_parts.append(f"本卦是{ben_gua_name}")
    if bian_gua_name:
        analysis_parts.append(f"变卦是{bian_gua_name}")

    if score >= 80:
        analysis_parts.append("卦象显示事情发展比较有利，顺势而为就好")
    elif score >= 60:
        analysis_parts.append("卦象整体还可以，有些需要注意的地方但问题不大")
    elif score >= 40:
        analysis_parts.append("卦象信息比较复杂，建议谨慎行事，多做准备")
    else:
        analysis_parts.append("卦象显示阻力较多，不宜冒进，稳住再说")

    analysis = "。".join(analysis_parts) + "。" if analysis_parts else "六爻分析数据不足。"
    return score, analysis, strengths, weaknesses


# ─── 奇门遁甲评分 ──────────────────────────────────────────
def _score_qimen(udm) -> Tuple[int, str, list, list]:
    if not udm.qimen_chart:
        return 0, "奇门遁甲数据不完整。", [], ["奇门排盘失败"]

    chart = udm.qimen_chart
    score = 0
    strengths = []
    weaknesses = []

    # 1. 吉凶格（+40分）
    # ge_ju_analysis 结构: {'ji_ge': [{'name':'天遁','gong':3,'desc':'...'}], 'xiong_ge': [...], ...}
    ge_ju = chart.get("ge_ju_analysis", {}) or {}
    ge_ju_names = []
    if isinstance(ge_ju, dict):
        for g in (ge_ju.get('ji_ge', []) or []):
            name = g.get('name', '') if isinstance(g, dict) else str(g)
            if name:
                ge_ju_names.append(name)
        for g in (ge_ju.get('xiong_ge', []) or []):
            name = g.get('name', '') if isinstance(g, dict) else str(g)
            if name:
                ge_ju_names.append(name)
    elif isinstance(ge_ju, list):
        ge_ju_names = [str(g) for g in ge_ju]

    ji_ge_kw = ["天遁", "地遁", "人遁", "龙遁", "虎遁", "风遁", "云遁",
                 "三奇", "玉女守门", "三奇得使", "飞鸟跌穴", "青龙返首",
                 "欢怡", "奇合", "丁壬合", "戊癸合", "天地合德"]
    xiong_ge_kw = ["悖格", "刑格", "大格", "小格", "击刑", "入墓", "三奇入墓",
                   "五不遇时", "太白入荧", "荧入太白", "白虎出力", "上格",
                   "太白同宫", "白虎猖狂", "朱雀投江", "螣蛇夭矫", "值使落空"]

    # 使用结构化数据计算吉凶格数量，同时考虑旬空影响（空亡宫格局效力减半）
    ji_g = 0
    xiong_g = 0
    kong_wang_count = 0  # 落空亡的格局数
    ge_ju_list = []
    if isinstance(ge_ju, dict):
        ge_ju_list = (ge_ju.get('ji_ge', []) or []) + (ge_ju.get('xiong_ge', []) or [])
    for g in ge_ju_list:
        name = g.get('name', '') if isinstance(g, dict) else str(g)
        if not name:
            continue
        in_kong = g.get('in_kong_wang', False) if isinstance(g, dict) else False
        is_ji = any(k in name for k in ji_ge_kw)
        is_xiong = any(k in name for k in xiong_ge_kw)
        if in_kong:
            kong_wang_count += 1
            # 空亡宫格局效力减半：吉格减半计分，凶格减半计分
            if is_ji:
                ji_g += 0.5
            if is_xiong:
                xiong_g += 0.5
        else:
            if is_ji:
                ji_g += 1
            if is_xiong:
                xiong_g += 1

    if ji_g > xiong_g:
        score += 40
        ji_display = int(ji_g) if ji_g == int(ji_g) else ji_g
        strengths.append(f"遇到{ji_display}个吉格，天时地利都站在你这边")
    elif xiong_g > ji_g:
        score += 15
        xiong_display = int(xiong_g) if xiong_g == int(xiong_g) else xiong_g
        weaknesses.append(f"有{xiong_display}个凶格，这个时间段做事要多留心眼")
    else:
        score += 25

    # 旬空影响提示
    if kong_wang_count > 0:
        kong_display = int(kong_wang_count) if kong_wang_count == int(kong_wang_count) else kong_wang_count
        weaknesses.append(f"有{kong_display}个格局落空亡，效力减半，需待出空后发力")

    # 奇门九宫名映射（值符宫位显示用）
    _QIMEN_GONG_NAMES = {
        1: '坎一宫', 2: '坤二宫', 3: '震三宫', 4: '巽四宫',
        5: '中五宫', 6: '乾六宫', 7: '兑七宫', 8: '艮八宫', 9: '离九宫',
    }

    # 2. 用神落宫（+30分）
    zhi_fu_gong = chart.get("zhi_fu_gong", "")

    # 值符落宫一般为吉
    if zhi_fu_gong:
        score += 15
        gong_name = _QIMEN_GONG_NAMES.get(zhi_fu_gong, f"{zhi_fu_gong}宫") if isinstance(zhi_fu_gong, int) else zhi_fu_gong
        strengths.append(f"值符在{gong_name}，核心力量到位")
    else:
        score += 8

    # 3. 八门（+30分）
    # 注意：八门系统固定3吉门+4凶门+1中性门，遍历全盘ji/xiong计数永远3>4无意义。
    # 奇门传统以值使门（当前值事之门）为八门核心，其吉凶决定八门整体质量。
    ba_men = chart.get("ba_men", {}) or {}
    ji_men = ["开门", "休门", "生门"]
    xiong_men = ["死门", "惊门", "伤门", "杜门"]
    # 取值使门（zhi_shi.door）作为八门评分核心
    zhi_shi = chart.get("zhi_shi", {}) or {}
    zhi_shi_door = zhi_shi.get("door", "") if isinstance(zhi_shi, dict) else ""

    if zhi_shi_door in ji_men:
        score += 28
        strengths.append(f"值使门是{zhi_shi_door}，吉门值事，做事有门路")
    elif zhi_shi_door in xiong_men:
        score += 10
        weaknesses.append(f"值使门是{zhi_shi_door}，凶门值事，行事要谨慎")
    elif zhi_shi_door:
        score += 18
    else:
        score += 15

    analysis_parts = []
    ju_name = chart.get("ju_name", "")
    if ju_name:
        analysis_parts.append(f"当前格局是{ju_name}")
    if score >= 80:
        analysis_parts.append("奇门格局很好，天时地利人和都占了，适合主动出击")
    elif score >= 60:
        analysis_parts.append("奇门格局中上，整体环境对你有利，把握好时机")
    elif score >= 40:
        analysis_parts.append("奇门格局一般，吉凶参半，做事需要看准时机")
    else:
        analysis_parts.append("奇门格局偏凶，建议韬光养晦，等时机转好再出手")

    analysis = "。".join(analysis_parts) + "。" if analysis_parts else "奇门分析数据不足。"
    return score, analysis, strengths, weaknesses


# ─── 大六壬评分 ──────────────────────────────────────────
def _score_liuren(udm) -> Tuple[int, str, list, list]:
    if not udm.liuren_chart:
        return 0, "大六壬数据不完整。", [], ["大六壬排盘失败"]

    chart = udm.liuren_chart
    score = 0
    strengths = []
    weaknesses = []

    # 1. 课体吉凶（+40分）
    ge_ju = chart.get("ge_ju", "") or ""
    ji_ke = ["天心", "龙德", "龍德", "天恩", "天喜", "三光", "三阳", "三陽",
             "富贵", "富貴", "轩盖", "軒蓋", "順陽"]
    xiong_ke = ["天祸", "天禍", "天网", "天網", "死奇", "魄化", "龙战", "龍戰",
                "无禄", "無祿", "绝嗣", "絕嗣"]

    if any(k in ge_ju for k in ji_ke):
        score += 40
        strengths.append(f"课体是{ge_ju}，属于吉课，事态发展有利")
    elif any(k in ge_ju for k in xiong_ke):
        score += 15
        weaknesses.append(f"课体是{ge_ju}，不太乐观，需要小心应对")
    elif ge_ju:
        score += 25
    else:
        score += 20

    # 2. 用神（+30分）
    yong_shen = chart.get("yong_shen", {}) or {}
    if yong_shen:
        # 六壬引擎返回的用神键: jiang_ji_xiong(天将吉凶), ri_gan_relation(与日干关系),
        #   chu_chuan_zhi(初传地支), chu_chuan_jiang(初传天将), jiang_han_yi(天将含义)
        jiang_ji_xiong = yong_shen.get("jiang_ji_xiong", "") or ""
        ri_gan_relation = yong_shen.get("ri_gan_relation", "") or ""
        chu_jiang = yong_shen.get("chu_chuan_jiang", "") or ""
        chu_zhi = yong_shen.get("chu_chuan_zhi", "") or ""
        jiang_han_yi = yong_shen.get("jiang_han_yi", "") or ""
        # 天将标签：用于提示文本（优先用简称，无简称则用全称）
        jiang_label = chu_jiang or "天将"

        # 天将吉凶：大吉/吉 → 旺相，凶 → 休囚（区分大吉30分 vs 吉25分）
        if jiang_ji_xiong == "大吉":
            score += 30
            if jiang_han_yi:
                strengths.append(f"初传{jiang_label}（{jiang_han_yi}），大吉之将，所问之事有贵人或天时助力")
            else:
                strengths.append(f"初传{jiang_label}为大吉之将，所问之事有力量支撑")
        elif "吉" in jiang_ji_xiong:
            score += 25
            if jiang_han_yi:
                strengths.append(f"初传{jiang_label}（{jiang_han_yi}），吉利之将，事态向好")
            else:
                strengths.append(f"初传{jiang_label}为吉利之将，事态发展有利")
        elif "凶" in jiang_ji_xiong:
            score += 10
            if jiang_han_yi:
                weaknesses.append(f"初传{jiang_label}（{jiang_han_yi}），凶将值事，事情推进有阻力")
            else:
                weaknesses.append(f"初传{jiang_label}为凶将，事情推进有阻力")
        elif "得助" in ri_gan_relation or "得财" in ri_gan_relation:
            score += 25
            if chu_zhi:
                strengths.append(f"初传{chu_zhi}与日干{ri_gan_relation}，事态向好")
            else:
                strengths.append("初传与日干关系有利，事态向好")
        elif "受制" in ri_gan_relation or "泄气" in ri_gan_relation:
            score += 12
            if chu_zhi:
                weaknesses.append(f"初传{chu_zhi}与日干{ri_gan_relation}，需要谨慎")
            else:
                weaknesses.append("初传与日干关系不利，需要谨慎")
        else:
            score += 20
    else:
        score += 15

    # 3. 四课三传（+30分）
    # 注：si_ke/san_chuan 在引擎中是 list（非 dict），默认值类型需匹配
    # 防御：kinliuren 失败时返回 [[],[],[],[]] 和 [[],[],[]]，虽 truthy 但实际无效
    si_ke = chart.get("si_ke", []) or []
    san_chuan = chart.get("san_chuan", []) or []
    si_ke_has_data = si_ke and any(k for k in si_ke)
    san_chuan_has_data = san_chuan and any(c for c in san_chuan)

    if si_ke_has_data:
        score += 15
    else:
        score += 8

    if san_chuan_has_data:
        score += 15
    else:
        score += 8

    analysis_parts = []
    if ge_ju:
        analysis_parts.append(f"课体是{ge_ju}")
    if score >= 80:
        analysis_parts.append("六壬课象很好，所问之事成功率高，可以放心去做")
    elif score >= 60:
        analysis_parts.append("课象还不错，虽然有些小问题但整体向好")
    elif score >= 40:
        analysis_parts.append("课象一般，建议多做准备，不要盲目行动")
    else:
        analysis_parts.append("课象偏凶，这个事情目前时机不太好，等等再说")

    analysis = "。".join(analysis_parts) + "。" if analysis_parts else "大六壬分析数据不足。"
    return score, analysis, strengths, weaknesses


# ─── 太乙神数评分 ──────────────────────────────────────────
def _score_taiyi(udm) -> Tuple[int, str, list, list]:
    if not udm.taiyi_chart:
        return 0, "太乙神数数据不完整。", [], ["太乙排盘失败"]

    chart = udm.taiyi_chart
    score = 0
    strengths = []
    weaknesses = []

    # 1. 主客算强弱（+50分）
    # zhu_suan/ke_suan/ding_suan 是 list（如 [5,3]），需取第一个元素
    zhu_suan_raw = chart.get("zhu_suan", []) or []
    ke_suan_raw = chart.get("ke_suan", []) or []
    zhu_suan_val = zhu_suan_raw[0] if isinstance(zhu_suan_raw, list) and zhu_suan_raw else None
    ke_suan_val = ke_suan_raw[0] if isinstance(ke_suan_raw, list) and ke_suan_raw else None

    # 太乙神数以主算为主
    # 注意：0是有效的算数值，不能用 truthiness 判断（if 0 会跳过）
    if zhu_suan_val is not None and zhu_suan_val != '':
        zhu_num = 0
        try:
            zhu_num = int(zhu_suan_val) if not isinstance(zhu_suan_val, int) else zhu_suan_val
        except (ValueError, TypeError):
            pass

        if zhu_num >= 7:
            score += 45
            strengths.append(f"主算{zhu_num}，力量很强，占尽优势")
        elif zhu_num >= 4:
            score += 30
            strengths.append(f"主算{zhu_num}，力量中等偏上，局面可控")
        elif zhu_num >= 1:
            score += 15
            weaknesses.append(f"主算{zhu_num}，力量偏弱，需要借助外力")
        else:
            score += 10
    else:
        score += 20

    # 2. 太乙落宫（+25分）
    taiyi_gong = chart.get("taiyi_gong", "")
    if taiyi_gong:
        score += 20
        strengths.append(f"太乙在{taiyi_gong}宫，主星到位")
    else:
        score += 10

    # 3. 九宫格局（+25分）
    ding_suan_raw = chart.get("ding_suan", []) or []
    ding_suan_val = ding_suan_raw[0] if isinstance(ding_suan_raw, list) and ding_suan_raw else None
    # 注意：0是有效的算数值，不能用 truthiness 判断（与主算/客算保持一致）
    if ding_suan_val is not None and ding_suan_val != '':
        try:
            ding_num = int(ding_suan_val) if not isinstance(ding_suan_val, int) else ding_suan_val
            if ding_num >= 5:
                score += 25
                strengths.append(f"定算{ding_num}，格局稳固")
            elif ding_num >= 3:
                score += 18
            else:
                score += 8
                weaknesses.append(f"定算{ding_num}，格局不太稳")
        except (ValueError, TypeError):
            score += 12
    else:
        score += 12

    analysis_parts = []
    ju_name = chart.get("ju_name", "")
    if ju_name:
        analysis_parts.append(f"太乙格局是{ju_name}")
    if score >= 80:
        analysis_parts.append("太乙显示主方力量很强，大势所趋，顺势而为即可")
    elif score >= 60:
        analysis_parts.append("太乙格局尚可，有余力应对变化")
    elif score >= 40:
        analysis_parts.append("太乙格局平平，主客力量接近，需要更多策略")
    else:
        analysis_parts.append("太乙显示主方偏弱，不宜硬来，以守为攻更好")

    analysis = "。".join(analysis_parts) + "。" if analysis_parts else "太乙分析数据不足。"
    return score, analysis, strengths, weaknesses


# ─── 占星评分 ──────────────────────────────────────────────
def _score_astro(udm) -> Tuple[int, str, list, list]:
    if not udm.astro_chart:
        return 0, "占星数据不完整。", [], ["占星排盘失败"]

    chart = udm.astro_chart
    score = 0
    strengths = []
    weaknesses = []

    # 1. 行星落座（+40分）
    planetary_details = chart.get("planetary_details", {}) or {}
    planets = chart.get("planets", {}) or {}

    # 入庙/旺/弱/陷
    dignities = {
        "domicile": (35, "入庙", "有几颗行星入庙了，天生有底气"),
        "exaltation": (35, "旺", "有行星旺位，某些能力天然强"),
        "triplicity": (28, "三分主", ""),
        "term": (23, "界", ""),
        "face": (20, "十度", ""),
        "detriment": (10, "陷", "有行星落陷，那个领域可能得多花心思"),
        "fall": (10, "弱", "有行星落弱位，需要注意平衡"),
    }

    planet_scores = []
    # 兼容 planetary_details 为 list 或 dict 两种格式
    if isinstance(planetary_details, list):
        planetary_details_dict = {}
        for item in planetary_details:
            if isinstance(item, dict) and item.get("name"):
                planetary_details_dict[item["name"]] = item
        planetary_details = planetary_details_dict
    for pname, pdetail in planetary_details.items():
        if isinstance(pdetail, dict):
            dignity = pdetail.get("dignity", "") or pdetail.get("essential_dignity", "")
            dignity = dignity.lower() if dignity else ""
            retrograde = pdetail.get("retrograde", False)
            matched = False
            for dkey, (dscore, dlabel, _) in dignities.items():
                if dkey in dignity:
                    # 逆行行星尊贵度降一级（传统占星：逆行削弱行星力量）
                    adj_score = max(10, dscore - 8) if retrograde else dscore
                    adj_label = dlabel + "（逆行削弱）" if retrograde else dlabel
                    planet_scores.append((pname, adj_score, adj_label))
                    matched = True
                    break
            if not matched:
                # 无尊贵度信息时按中性处理，逆行额外扣分
                base = 18 if retrograde else 22
                label = "（逆行）" if retrograde else ""
                planet_scores.append((pname, base, label))

    if planet_scores:
        avg_planet = sum(s for _, s, _ in planet_scores) / len(planet_scores)
        score += int(avg_planet / 35 * 40)
        # 收集优劣势
        for pn, ps, pl in planet_scores:
            if ps >= 30:
                strengths.append(f"{pn}{pl}，这个领域是你的强项")
            elif ps <= 12:
                weaknesses.append(f"{pn}{pl}，这个方面需要多注意")
    else:
        score += 20

    # 2. 相位分析（+40分）
    aspects = chart.get("aspects", []) or []

    # 占星引擎使用中文相位名：'合相','六合','刑','三合','冲'
    ji_aspects = ["合相", "六合", "三合"]
    xiong_aspects = ["刑", "冲"]

    ji_a = sum(1 for a in aspects if isinstance(a, dict) and a.get("aspect", "") in ji_aspects)
    xiong_a = sum(1 for a in aspects if isinstance(a, dict) and a.get("aspect", "") in xiong_aspects)

    if ji_a > xiong_a:
        bonus = min(40, 25 + (ji_a - xiong_a) * 3)
        score += bonus
        strengths.append(f"吉相位多（{ji_a}个），天赋和机遇配合得好")
    elif xiong_a > ji_a:
        score += max(10, 25 - (xiong_a - ji_a) * 3)
        weaknesses.append(f"刑冲相位多（{xiong_a}个），人生有些张力需要化解")
    else:
        score += 22

    # 3. 上升点和重要轴线（+20分）
    asc = chart.get("ascendant", "") or chart.get("ascendant_sign", "")
    mc = chart.get("mc", "") or chart.get("mc_sign", "")
    sun = chart.get("sun_sign", "")
    moon = chart.get("moon_sign", "")

    if sun and moon:
        score += 10
        strengths.append(f"太阳{sun}、月亮{moon}，核心自我和情感世界都有定位")
    else:
        score += 5

    if asc:
        score += 8
    else:
        score += 3

    if mc:
        score += 5
    else:
        score += 2

    analysis_parts = []
    if sun:
        analysis_parts.append(f"你的太阳星座是{sun}")
    if moon:
        analysis_parts.append(f"月亮在{moon}")
    if asc:
        analysis_parts.append("上升点有明确落座")

    if score >= 80:
        analysis_parts.append("星盘配置很优秀，很多行星状态好，人生舞台大")
    elif score >= 60:
        analysis_parts.append("星盘还不错，有亮点也有需要注意的地方，总体积极")
    elif score >= 40:
        analysis_parts.append("星盘中等，有些紧张相位但也有和谐之处，关键是怎么用")
    else:
        analysis_parts.append("星盘挑战多一些，但紧张相位往往意味着巨大的成长潜力")

    analysis = "。".join(analysis_parts) + "。" if analysis_parts else "占星分析数据不足。"
    return score, analysis, strengths, weaknesses


# ─── 姓名学评分 ──────────────────────────────────────────────
def _score_xingming(udm) -> Tuple[int, str, list, list]:
    """
    姓名学评分：基于五格数理吉凶、三才配置、人格主导运势。

    评分维度：
      1. 五格吉凶统计（+40分）—— 五格中吉数占比越高越好
      2. 三才配置（+30分）—— 天地人三格五行相生为上
      3. 人格主运（+15分）—— 人格数理是姓名学最核心的格
      4. 总格后运（+15分）—— 总格影响中晚年运势
    """
    if not udm.xingming_chart:
        return 0, "姓名学数据不完整。", [], ["姓名学排盘失败"]

    chart = udm.xingming_chart
    score = 0
    strengths = []
    weaknesses = []

    wuge = chart.get("wuge", {}) or {}
    sancai = chart.get("sancai", {}) or {}

    # 1. 五格吉凶统计（+40分）
    ge_names = ["天格", "人格", "地格", "外格", "总格"]
    ji_count = 0.0
    xiong_count = 0.0
    ge_details = []

    for ge_name in ge_names:
        ge_data = wuge.get(ge_name, {})
        if not ge_data:
            continue
        jixiong = ge_data.get("吉凶", "")
        shuli_name = ge_data.get("数理名", "")
        shuli = ge_data.get("数理", 0)
        wx = ge_data.get("五行", "")

        if jixiong == "大吉":
            ji_count += 1.5
            ge_details.append(f"{ge_name}({shuli}画·{shuli_name}·{wx})★★")
        elif jixiong == "吉":
            ji_count += 1
            ge_details.append(f"{ge_name}({shuli}画·{shuli_name}·{wx})✓")
        elif jixiong == "半吉":
            ji_count += 0.5
            ge_details.append(f"{ge_name}({shuli}画·{shuli_name}·{wx})△")
        elif jixiong == "半凶":
            xiong_count += 0.5
            ge_details.append(f"{ge_name}({shuli}画·{shuli_name}·{wx})△")
        elif jixiong == "凶":
            xiong_count += 1
            ge_details.append(f"{ge_name}({shuli}画·{shuli_name}·{wx})✗")
        elif jixiong == "大凶":
            xiong_count += 1.5
            ge_details.append(f"{ge_name}({shuli}画·{shuli_name}·{wx})✗✗")

    net = ji_count - xiong_count
    if net >= 3:
        score += 40
        ji_str = int(ji_count) if ji_count == int(ji_count) else ji_count
        strengths.append(f"五格中{ji_str}个吉数，姓名数理配置非常好")
    elif net >= 1:
        score += 30
        strengths.append(f"五格吉多凶少，姓名基础不错")
    elif net >= 0:
        score += 20
    elif net >= -2:
        score += 12
        xiong_str = int(xiong_count) if xiong_count == int(xiong_count) else xiong_count
        weaknesses.append(f"五格凶数偏多（{xiong_str}个），姓名数理有改善空间")
    else:
        score += 5
        xiong_str = int(xiong_count) if xiong_count == int(xiong_count) else xiong_count
        weaknesses.append(f"五格凶数较多（{xiong_str}个），建议考虑调整姓名")

    # 2. 三才配置（+30分）
    sancai_jixiong = sancai.get("吉凶", "") if isinstance(sancai, dict) else ""
    sancai_desc = sancai.get("解释", "") if isinstance(sancai, dict) else ""
    sancai_wuxing = sancai.get("配置", "") if isinstance(sancai, dict) else ""

    if "大吉" in sancai_jixiong:
        score += 30
        strengths.append(f"三才配置{sancai_wuxing}为{sancai_jixiong}，天地人和谐")
    elif "中吉" in sancai_jixiong:
        score += 25
        strengths.append(f"三才配置{sancai_wuxing}为{sancai_jixiong}，天地人较为协调")
    elif sancai_jixiong == "吉":
        score += 22
        strengths.append(f"三才配置{sancai_wuxing}为{sancai_jixiong}，基础稳固")
    elif "半吉" in sancai_jixiong:
        score += 16
        strengths.append(f"三才配置{sancai_wuxing}为{sancai_jixiong}，基础尚可")
    elif "半凶" in sancai_jixiong:
        score += 12
        weaknesses.append(f"三才配置{sancai_wuxing}为{sancai_jixiong}，天地人略有不协")
    elif sancai_jixiong == "凶":
        score += 8
        weaknesses.append(f"三才配置{sancai_wuxing}为{sancai_jixiong}，天地人不够协调")
    elif "大凶" in sancai_jixiong:
        score += 3
        weaknesses.append(f"三才配置{sancai_wuxing}为{sancai_jixiong}，天地人严重不协，建议调整")
    else:
        score += 15

    # 3. 人格主运（+15分）—— 人格是姓名学最核心的格
    renge = wuge.get("人格", {})
    if renge:
        rg_jx = renge.get("吉凶", "")
        rg_name = renge.get("数理名", "")
        if rg_jx == "吉":
            score += 15
            strengths.append(f"人格{rg_name}为主运，一生基础运好")
        elif rg_jx == "半吉":
            score += 10
        elif rg_jx == "半凶":
            score += 6
            weaknesses.append(f"人格{rg_name}为主运，中年运势有些波折")
        elif rg_jx == "凶":
            score += 3
            weaknesses.append(f"人格{rg_name}为主运，人生主运偏弱，需后天努力")
    else:
        score += 7

    # 4. 总格后运（+15分）—— 影响中晚年
    zongge = wuge.get("总格", {})
    if zongge:
        zg_jx = zongge.get("吉凶", "")
        zg_name = zongge.get("数理名", "")
        if zg_jx == "吉":
            score += 15
            strengths.append(f"总格{zg_name}，晚年运势好")
        elif zg_jx == "半吉":
            score += 10
        elif zg_jx == "半凶":
            score += 6
        elif zg_jx == "凶":
            score += 3
            weaknesses.append(f"总格{zg_name}，晚年运势需多注意")
    else:
        score += 7

    # 生成分析
    analysis_parts = []
    surname = chart.get("surname", "")
    given_name = chart.get("given_name", "")
    if surname and given_name:
        analysis_parts.append(f"姓名「{surname}{given_name}」")

    if ge_details:
        analysis_parts.append("五格：" + "、".join(ge_details))

    if sancai_desc:
        analysis_parts.append(f"三才：{sancai_desc}")

    if score >= 80:
        analysis_parts.append("姓名配置优秀，数理吉多凶少，三才和谐，先天姓名助力大")
    elif score >= 60:
        analysis_parts.append("姓名配置不错，有些亮点也有需要注意的地方")
    elif score >= 40:
        analysis_parts.append("姓名配置一般，部分数理不太理想，但影响有限")
    else:
        analysis_parts.append("姓名数理偏弱，建议结合八字喜用考虑调整")

    analysis = "。".join(analysis_parts) + "。" if analysis_parts else "姓名学分析数据不足。"
    return score, analysis, strengths, weaknesses
