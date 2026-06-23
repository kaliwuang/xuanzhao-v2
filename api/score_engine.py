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

# 吉神/凶神分类
JISHEN_KEYWORDS = ["天乙", "文昌", "禄", "天德", "月德", "太极", "天喜", "红鸾", "将星"]
XIONGSHA_KEYWORDS = ["羊刃", "七杀", "劫煞", "亡神", "孤辰", "寡宿", "天罗", "地网", "华盖"]

# ─── 主入口 ──────────────────────────────────────────────
def score_all(udm, method: str = "all") -> Dict[str, Dict]:
    """
    对所有（或指定）术法评分，返回：
    { method_name: { score, analysis, strengths, weaknesses } }
    """
    result = {}

    scorers = {
        "八字": _score_bazi,
        "紫微斗数": _score_ziwei,
        "六爻": _score_liuyao,
        "奇门遁甲": _score_qimen,
        "大六壬": _score_liuren,
        "太乙神数": _score_taiyi,
        "占星": _score_astro,
    }

    for name, fn in scorers.items():
        if method != "all" and method != name:
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
                "analysis": f"这门术法暂时没法给你打分，出了点小问题：{e}",
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
    # 提取天干地支的五行
    all_wx = set()
    for ch in all_chars:
        if ch in GAN_WX:
            all_wx.add(GAN_WX[ch])

    xi_present = any(wx in all_wx for wx in xi_list) if xi_list else False
    ji_present = any(wx in all_wx for wx in ji_list) if ji_list else False

    if strength == "身弱":
        if xi_present:
            score += 28
            strengths.append("虽然身弱，但喜用神就在八字里，有人帮忙扛事儿")
        else:
            score += 12
            weaknesses.append("身弱且喜用神不太给力，需要后天多补补")
    elif strength == "身强":
        if xi_present:
            score += 30
            strengths.append("身强又有喜用神制约，刚柔并济，格局不错")
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

    # 4. 刑冲合害（+15分）
    zhi_relations = getattr(udm, 'zhi_relations', []) or []
    chong_count = sum(1 for r in zhi_relations if "冲" in str(r))
    xing_count = sum(1 for r in zhi_relations if "刑" in str(r))
    he_count = sum(1 for r in zhi_relations if "合" in str(r))

    if chong_count == 0 and xing_count == 0:
        score += 15
        strengths.append("地支没什么刑冲，生活比较安稳")
    elif chong_count + xing_count <= 1:
        score += 10
    elif chong_count + xing_count <= 2:
        score += 5
        weaknesses.append("有点刑冲，生活中难免有些冲突和变化")
    else:
        score += 2
        weaknesses.append("刑冲比较多，人生起伏大，需要更多智慧应对")

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
                zhi = gz[1:] if len(gz) >= 2 else ""
                zhi_wx = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
                          "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
                dwx = zhi_wx.get(zhi, "")
                if dwx in xi_list:
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

    has_ji_main = any(s in str(ming_palace_stars) for s in ji_main)
    has_sha_main = any(s in str(ming_palace_stars) for s in sha_main)

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
        ming_stars_text = str(mg_data.get("major_stars", "")) + str(mg_data.get("minor_stars", "")) + str(mg_data.get("stars", ""))
        sha_in_ming = sum(1 for s in sha_stars if s in ming_stars_text)

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

    # 从格局判断
    ge_ju_str = " ".join(str(g) for g in ge_ju)
    ji_ge = ["回头生", "生合", "帝旺", "临官", "长生", "进神"]
    xiong_ge = ["回头克", "绝", "死", "墓", "退神", "空亡"]

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
        if "生" in str(ge_ju_str) or "合" in str(ge_ju_str):
            score += 28
            strengths.append("世应相生相合，人际关系和合作方面有利")
        elif "克" in str(ge_ju_str) and "世" in str(ge_ju_str):
            score += 10
            weaknesses.append("世爻受克，可能在某些关系中处于被动")
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
    ben_gua = chart.get("ben_gua", "")
    bian_gua = chart.get("bian_gua", "")
    if ben_gua:
        analysis_parts.append(f"本卦是{ben_gua}")
    if bian_gua:
        analysis_parts.append(f"变卦是{bian_gua}")

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
    ge_ju = chart.get("ge_ju_analysis", {}) or {}
    ge_ju_names = []
    if isinstance(ge_ju, dict):
        ge_ju_names = list(ge_ju.keys())
    elif isinstance(ge_ju, list):
        ge_ju_names = [str(g) for g in ge_ju]

    ji_ge_kw = ["天遁", "地遁", "人遁", "龙遁", "虎遁", "风遁", "云遁", "神遁",
                 "鬼遁", "仪奇", "三奇", "玉女守门", "九天", "九地"]
    xiong_ge_kw = ["悖格", "刑格", "大格", "小格", "飞格", "伏格", "六仪击刑", "五不遇时"]

    ji_g = sum(1 for g in ge_ju_names if any(k in str(g) for k in ji_ge_kw))
    xiong_g = sum(1 for g in ge_ju_names if any(k in str(g) for k in xiong_ge_kw))

    if ji_g > xiong_g:
        score += 40
        strengths.append(f"遇到{ji_g}个吉格，天时地利都站在你这边")
    elif xiong_g > ji_g:
        score += 15
        weaknesses.append(f"有{xiong_g}个凶格，这个时间段做事要多留心眼")
    else:
        score += 25

    # 2. 用神落宫（+30分）
    palaces = chart.get("palaces", {}) or {}
    zhi_fu_gong = chart.get("zhi_fu_gong", "")

    # 值符落宫一般为吉
    if zhi_fu_gong:
        score += 15
        strengths.append(f"值符在{zhi_fu_gong}宫，核心力量到位")
    else:
        score += 8

    # 3. 八门（+30分）
    ba_men = chart.get("ba_men", {}) or {}
    ji_men = ["开门", "休门", "生门"]
    xiong_men = ["死门", "惊门", "伤门", "杜门"]

    men_str = str(ba_men)
    ji_m = sum(1 for m in ji_men if m in men_str)
    xiong_m = sum(1 for m in xiong_men if m in men_str)

    if ji_m > xiong_m:
        score += 25
        strengths.append("八门格局不错，做事有门路")
    elif xiong_m > ji_m:
        score += 10
        weaknesses.append("八门凶门多，行事要谨慎，避免硬碰硬")
    else:
        score += 18

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
    ji_ke = ["天心", "龙德", "天恩", "天喜", "三光", "三阳", "富贵", "轩盖"]
    xiong_ke = ["天祸", "天网", "死奇", "魄化", "龙战", "无禄", "绝嗣"]

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
        ys_status = yong_shen.get("status", "") or yong_shen.get("旺衰", "")
        if "旺" in str(ys_status) or "相" in str(ys_status):
            score += 30
            strengths.append("用神旺相，所问之事有力量支撑")
        elif "休" in str(ys_status) or "囚" in str(ys_status):
            score += 15
            weaknesses.append("用神休囚，事情推进动力不足")
        elif "死" in str(ys_status) or "绝" in str(ys_status):
            score += 5
            weaknesses.append("用神很弱，这个事情目前条件不成熟")
        else:
            score += 20
    else:
        score += 15

    # 3. 四课三传（+30分）
    si_ke = chart.get("si_ke", {}) or {}
    san_chuan = chart.get("san_chuan", {}) or {}

    if si_ke:
        score += 15
    else:
        score += 8

    if san_chuan:
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
    zhu_suan = chart.get("zhu_suan", "") or chart.get("suan_analysis", {}).get("zhu_suan", "") or ""
    ke_suan = chart.get("ke_suan", "") or chart.get("suan_analysis", {}).get("ke_suan", "") or ""

    # 太乙神数以主算为主
    if zhu_suan:
        zhu_num = 0
        try:
            zhu_num = int(str(zhu_suan).strip())
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
    ding_suan = chart.get("ding_suan", "") or ""
    if ding_suan:
        try:
            ding_num = int(str(ding_suan).strip())
            if ding_num >= 5:
                score += 25
                strengths.append(f"定算{ding_suan}，格局稳固")
            elif ding_num >= 3:
                score += 18
            else:
                score += 8
                weaknesses.append(f"定算{ding_suan}，格局不太稳")
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
            for dkey, (dscore, dlabel, _) in dignities.items():
                if dkey in dignity:
                    planet_scores.append((pname, dscore, dlabel))
                    break
            else:
                planet_scores.append((pname, 22, ""))

    if planet_scores:
        avg_planet = sum(s for _, s, _ in planet_scores) / len(planet_scores)
        score += int(avg_planet * 0.4 / 35 * 40)
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
    aspects_summary = chart.get("aspects_summary", {}) or {}

    ji_aspects = ["trine", "sextile", "conjunction"]
    xiong_aspects = ["square", "opposition"]

    ji_a = sum(1 for a in aspects if isinstance(a, dict) and a.get("aspect", "").lower() in ji_aspects)
    xiong_a = sum(1 for a in aspects if isinstance(a, dict) and a.get("aspect", "").lower() in xiong_aspects)

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
