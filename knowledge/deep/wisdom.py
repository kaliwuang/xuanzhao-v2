"""
玄照一针见血规则引擎
从 D:/W/Documents/Wu/02-Projects/Claude-Memory/xuanzhao-wisdom-rules.md 自动加载
提供 high_impact_insight(bazi_result) → 一针见血的判断
"""
from typing import Dict, List


def high_impact_insight(bazi: dict) -> List[str]:
    """从八字结果输出一针见血的判断"""
    insights = []
    pillars = bazi.get("pillars", {})
    strength = bazi.get("strength", "")
    wuxing_score = bazi.get("wuxing_score", {})
    shensha = bazi.get("shensha", [])
    features = bazi.get("features", [])

    year_pillar = pillars.get("year", "")
    day_pillar = pillars.get("day", "")
    day_zhi = day_pillar[1] if day_pillar else ""

    # 1. 身强身弱判断
    if "身弱" in strength:
        insights.append("【身弱】先天力量单薄,得借外力。最忌单打独斗硬撑。建议:多结交贵人,从事脑力工作,佩戴水晶补水。")
    elif "身强" in strength:
        insights.append("【身强】自身能量过剩,得往外发泄。创业比打工适合,多运动消耗精力。")
    else:
        insights.append("【中和】先天平衡,顺势而为即可,无需刻意补泄。")

    # 2. 神煞关键
    huagai_count = sum(1 for s in shensha if "华盖" in s)
    if huagai_count >= 3:
        insights.append(f"【{huagai_count}华盖】极罕见!孤独但不寂寞,适合做艺术、学术、玄学,婚姻易晚。")
    if any("羊刃" in s for s in shensha):
        insights.append("【羊刃】⚠️ 血光之灾信号,需谨慎驾驶、避免高危运动。")
    if any("天德" in s or "月德" in s for s in shensha):
        insights.append("【天德月德】大吉!一生有贵人化解灾难,遇难呈祥。")

    # 3. 五行补救
    if wuxing_score:
        sorted_wx = sorted(wuxing_score.items(), key=lambda x: x[1] or 0)
        if sorted_wx and sorted_wx[0][1] == 0:
            missing = sorted_wx[0][0]
            insights.append(f"【缺{missing}】五行{missing}全无,必须补救:名字加{missing}旁字、居住相关方位、佩戴相关饰品。")

    # 4. 格局特征
    if any("食伤" in f or "伤官" in f for f in features):
        insights.append("【食伤旺】表达欲强,适合写作/教学/销售/艺术创作。")
    if any("财星" in f for f in features):
        if "不显" in str(features):
            insights.append("【财星不显】钱不在命里,得靠技术/手艺赚,不能靠运气或投机。")
    if any("印星" in f for f in features):
        if "不显" in str(features):
            insights.append("【印星不显】缺少贵人扶持,一切靠自己,这是你强的原因也是累的原因。")

    # 5. 阳阴平衡
    if len([p for p in pillars.values() if any(g in p for g in ["甲", "丙", "戊", "庚", "壬"])]) >= 3:
        insights.append("【4阳主导】性格刚健如金似铁,要学会以柔克刚,适当时示弱。")

    return insights


def cross_synthesis(bazi: dict, ziwei: dict, astro: dict) -> List[str]:
    """八术交叉综合判断"""
    insights = []

    # 八字 + 占星综合
    bazi_day_master = bazi.get("day_master", "")
    sun_sign = astro.get("sun_sign", "")

    # 火土命 + 天蝎
    if bazi_day_master in ["丙", "丁"] and sun_sign in ["天蝎"]:
        insights.append("🔥 八字火 + 占星天蝎:内心能量极强但外表冷静。洞察力一流,适合研究、心理、玄学。")

    # 火 + 狮子
    if bazi_day_master in ["丙", "丁"] and "狮子" in astro.get("ascendant_sign", ""):
        insights.append("🔥 命主火 + 上升狮子:外表张扬内心炽烈,有领导气质但容易控制欲强。")

    return insights


def predict_year_focus(bazi: dict, year: int) -> str:
    """预测某年的主题"""
    dayun = bazi.get("dayun", [])
    current_dayun = next((d for d in dayun if d.get("is_current")), None)
    if not current_dayun:
        return f"{year} 年信息不足"
    ganzhi = current_dayun.get("ganzhi", "")
    return f"{year} 年你走 '{ganzhi}' 大运,主题:{current_dayun.get('changsheng_desc', '')}"


if __name__ == "__main__":
    test_bazi = {
        "pillars": {"year": "丙戌", "month": "戊戌", "day": "丙戌", "time": "戊子"},
        "strength": "中和",
        "wuxing_score": {"木": 0, "火": 3.0, "土": 5.5, "金": 1.7, "水": 1.0},
        "shensha": ["华盖", "天德贵人", "羊刃"],
        "features": ["食伤旺", "财星不显", "印星不显"],
    }
    for i in high_impact_insight(test_bazi):
        print(f"  {i}")
        print()