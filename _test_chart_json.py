#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

from engine.time_engine import TimeEngine
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

te = TimeEngine()
corrected = te.correct('2005-06-09 11:50', '呼和浩特')

orch = EngineOrchestrator()
orch.register(BaziEngine())
orch.register(AstroEngine())
orch.register(ZiWeiEngine())
orch.register(LiuYaoEngine())
orch.register(QiMenEngine())
orch.register(LiuRenEngine())
orch.register(TaiYiEngine())

udm = orch.run_all(corrected, 1)

# 构建完整报告
report = {
    "出生信息": {
        "原始时间": "2005-06-09 11:50",
        "地点": "呼和浩特",
        "性别": "男",
        "真太阳时": str(corrected.true_solar),
        "经度": corrected.longitude,
        "纬度": corrected.latitude,
    },
    "八字": {},
    "紫微": {},
    "占星": {},
    "六爻": {},
    "奇门": {},
    "大六壬": {},
    "太乙": {},
    "交叉验证": {},
    "12人物观点": [],
    "交锋辩论": [],
}

# 八字
if udm.bazi_year:
    report["八字"] = {
        "四柱": {
            "年柱": udm.bazi_year.ganzhi,
            "月柱": udm.bazi_month.ganzhi if udm.bazi_month else "",
            "日柱": udm.bazi_day.ganzhi if udm.bazi_day else "",
            "时柱": udm.bazi_time.ganzhi if udm.bazi_time else "",
        },
        "纳音": udm.nayin,
        "十神": udm.shishen_gan,
        "日主": f"{udm.day_master}（{udm.day_master_wuxing}）",
        "调候用神": udm.tiaohou,
        "特征": udm.features,
        "冲": udm.get_chong(),
        "合": udm.get_he(),
        "五行统计": udm.get_wuxing_count(),
    }

# 紫微
if udm.ziwei_chart:
    zw = udm.ziwei_chart
    report["紫微"] = {
        "命宫": zw["ming_gong"],
        "五行局": zw["wuxing_ju"],
        "四化": zw["sihua"],
        "主星": zw["star_placements"],
        "十二宫": zw["palaces"],
    }

# 占星
if udm.astro_chart:
    ast = udm.astro_chart
    report["占星"] = {
        "太阳": f"{ast['sun_sign']}（{ast['sun_element']}）",
        "月亮": f"{ast['moon_sign']}（{ast['moon_element']}）",
        "上升": ast["ascendant_sign"],
        "中天": ast["mc"],
        "行星": {name: f"{info['sign']} {info['degree']}°" for name, info in ast["planets"].items()},
        "宫位": {k: f"{v['sign']} {v['cusp']}°" for k, v in ast["houses"].items()},
        "相位": ast["aspects"][:5],
    }

# 六爻
if udm.liuyao_chart:
    ly = udm.liuyao_chart
    report["六爻"] = {
        "本卦": ly["ben_gua"]["name"],
        "动爻": f"第{ly['dong_yao']}爻",
    }

# 奇门
if udm.qimen_chart:
    qm = udm.qimen_chart
    report["奇门"] = {
        "局数": qm["ju_name"],
        "地盘": qm["di_pan"],
        "八门": qm["ba_men"],
    }

# 大六壬
if udm.liuren_chart:
    lr = udm.liuren_chart
    report["大六壬"] = {
        "月将": lr["yue_jiang"],
        "四课": [k["ke"] for k in lr["si_ke"]],
        "三传": [c["name"] for c in lr["san_chuan"]],
    }

# 太乙
if udm.taiyi_chart:
    ty = udm.taiyi_chart
    report["太乙"] = {
        "太乙宫位": ty["taiyi_gong"],
        "积年数": ty["ji_nian"],
        "阴阳遁": ty["yin_yang"],
    }

# 交叉验证
validator = CrossValidator(udm)
v = validator.validate()
report["交叉验证"] = {
    "参与术法": v["available_methods"],
    "术法数量": v["method_count"],
    "综合置信度": v["overall_confidence"].value,
    "共识": [{"方面": c.aspect, "发现": c.finding, "支持术法": c.supporting_methods} for c in v["consensus"]],
    "冲突": [{"方面": c.aspect, "术法A": c.method_a, "术法B": c.method_b, "建议": c.suggestion} for c in v["conflicts"]],
}

# 12人物视角
pe = PerspectiveEngine()
opinions = pe.analyze(udm, "此人事业如何？")
report["12人物观点"] = [
    {
        "人物": o.figure_name,
        "术法": o.primary_method,
        "立场": o.stance,
        "置信度": round(o.confidence, 2),
        "要点": o.key_points,
    }
    for o in opinions
]

# 辩论
de = DebateEngine()
debate_result = de.debate(opinions, "此人事业如何？")
report["交锋辩论"] = [
    {
        "轮次": e.round_num,
        "发言者": e.speaker,
        "发言者术法": e.speaker_method,
        "目标": e.target,
        "目标术法": e.target_method,
        "论点": e.argument,
    }
    for e in debate_result["exchanges"][:6]
]
report["辩论总结"] = debate_result["summary"]

print(json.dumps(report, ensure_ascii=False, indent=2))
