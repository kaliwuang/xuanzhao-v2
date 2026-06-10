#!/usr/bin/env python3
"""
玄照 v2.0 — 命理分析命令行工具

用法:
  python xuanzhao.py analyze --birth '2005-06-09 11:50' --location 呼和浩特 --gender 男
  python xuanzhao.py predict --birth '2005-06-09 11:50' --location 呼和浩特 --gender 男 --question '事业如何'
  python xuanzhao.py demo
"""

import argparse
import sys
import os
import json
import traceback

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.time_engine import get_time_engine
from engine.bazi_engine import BaziEngine
from engine.ziwei_engine import ZiWeiEngine
from engine.astro_engine import AstroEngine
from engine.base import EngineOrchestrator
from engine.perspective_engine import PerspectiveEngine, FIGURES

# ──────────────────── 格式化输出工具 ────────────────────

LINE = "─" * 60
THICK = "━" * 60
STAR = "★"
DOT = "◆"


def banner(text: str):
    print(f"\n{THICK}")
    print(f"  {STAR} {text}")
    print(THICK)


def section(text: str):
    print(f"\n{DOT} {text}")
    print(LINE)


def kv(key: str, value, indent: int = 2):
    """格式化 key: value"""
    pad = " " * indent
    print(f"{pad}{key}：{value}")


def parse_gender(g: str) -> int:
    """性别字符串转数字 (1=男, 0=女)"""
    return 1 if g.strip() in ("男", "1", "male") else 0


# ──────────────────── 排盘核心 ────────────────────


def run_engines(birth: str, location: str, gender_str: str):
    """运行全部术法引擎，返回 (corrected_time, udm)"""
    gender = parse_gender(gender_str)
    te = get_time_engine()
    ct = te.correct(birth, location)

    # 注册引擎
    orch = EngineOrchestrator()
    orch.register(BaziEngine())
    orch.register(ZiWeiEngine())
    orch.register(AstroEngine())

    udm = orch.run_all(ct, gender)
    return ct, udm, gender


# ──────────────────── 输出：时间修正 ────────────────────


def print_time_info(ct):
    section("时间修正")
    kv("原始时间", ct.original.strftime("%Y-%m-%d %H:%M"))
    kv("出生地点", ct.location_name)
    kv("经纬度", f"({ct.latitude:.2f}, {ct.longitude:.2f})")
    kv("真太阳时", ct.true_solar.strftime("%Y-%m-%d %H:%M:%S"))
    kv("晚子时", "是" if ct.is_late_zi else "否")
    jq = ct.jieqi_context
    if jq.get("prev_jie") or jq.get("next_jie"):
        kv("节气区间", f"{jq.get('prev_jie', '?')} → {jq.get('next_jie', '?')}")


# ──────────────────── 输出：八字 ────────────────────


def print_bazi(udm):
    section("八字四柱")

    pillars = [
        ("年柱", udm.bazi_year),
        ("月柱", udm.bazi_month),
        ("日柱", udm.bazi_day),
        ("时柱", udm.bazi_time),
    ]

    # 表头
    header = "  {:　<6} {:　<6} {:　<6} {:　<6}".format("年柱", "月柱", "日柱", "时柱")
    gans_line = "  {:　<8} {:　<8} {:　<8} {:　<8}".format(
        udm.bazi_year.gan if udm.bazi_year else "-",
        udm.bazi_month.gan if udm.bazi_month else "-",
        udm.bazi_day.gan if udm.bazi_day else "-",
        udm.bazi_time.gan if udm.bazi_time else "-",
    )
    zhis_line = "  {:　<8} {:　<8} {:　<8} {:　<8}".format(
        udm.bazi_year.zhi if udm.bazi_year else "-",
        udm.bazi_month.zhi if udm.bazi_month else "-",
        udm.bazi_day.zhi if udm.bazi_day else "-",
        udm.bazi_time.zhi if udm.bazi_time else "-",
    )
    nayin_line = "  {:　<6} {:　<6} {:　<6} {:　<6}".format(
        (udm.bazi_year.nayin or "") if udm.bazi_year else "",
        (udm.bazi_month.nayin or "") if udm.bazi_month else "",
        (udm.bazi_day.nayin or "") if udm.bazi_day else "",
        (udm.bazi_time.nayin or "") if udm.bazi_time else "",
    )

    print(f"\n  {'年柱':　^8}  {'月柱':　^8}  {'日柱':　^8}  {'时柱':　^8}")
    print(f"  {udm.bazi_year.gan if udm.bazi_year else '-':　^8}  "
          f"{udm.bazi_month.gan if udm.bazi_month else '-':　^8}  "
          f"{udm.bazi_day.gan if udm.bazi_day else '-':　^8}  "
          f"{udm.bazi_time.gan if udm.bazi_time else '-':　^8}")
    print(f"  {udm.bazi_year.zhi if udm.bazi_year else '-':　^8}  "
          f"{udm.bazi_month.zhi if udm.bazi_month else '-':　^8}  "
          f"{udm.bazi_day.zhi if udm.bazi_day else '-':　^8}  "
          f"{udm.bazi_time.zhi if udm.bazi_time else '-':　^8}")
    print(f"  {(udm.bazi_year.nayin or '') if udm.bazi_year else '':　^8}  "
          f"{(udm.bazi_month.nayin or '') if udm.bazi_month else '':　^8}  "
          f"{(udm.bazi_day.nayin or '') if udm.bazi_day else '':　^8}  "
          f"{(udm.bazi_time.nayin or '') if udm.bazi_time else '':　^8}")

    section("日主")
    kv("日主天干", udm.day_master or "?")
    kv("日主五行", udm.day_master_wuxing or "?")

    section("十神（天干）")
    for pos, name in [("年", "year"), ("月", "month"), ("日", "day"), ("时", "time")]:
        ss = udm.shishen_gan.get(name, "")
        kv(f"{pos}干十神", ss or "-")

    section("十神（地支藏干）")
    for pos, name in [("年", "year"), ("月", "month"), ("日", "day"), ("时", "time")]:
        ss = udm.shishen_zhi.get(name, [])
        display = ", ".join(ss) if isinstance(ss, list) else str(ss)
        kv(f"{pos}支藏干十神", display or "-")

    section("藏干")
    for pos, name in [("年", "year"), ("月", "month"), ("日", "day"), ("时", "time")]:
        hg = udm.hidden_gans.get(name, [])
        display = ", ".join(hg) if isinstance(hg, list) else str(hg)
        kv(f"{pos}支藏干", display or "-")

    section("纳音")
    for pos, name in [("年", "year"), ("月", "month"), ("日", "day"), ("时", "time")]:
        ny = udm.nayin.get(name, "")
        kv(f"{pos}柱纳音", ny or "-")

    section("空亡")
    for name, label in [("year", "年柱"), ("day", "日柱")]:
        xk = udm.xunkong.get(name, "")
        kv(f"{label}空亡", xk or "-")

    section("调候用神")
    kv("调候", udm.tiaohou or "无")

    section("五行分布")
    wx = udm.get_wuxing_count()
    bar_parts = []
    for element in ["木", "火", "土", "金", "水"]:
        count = wx.get(element, 0)
        bar_parts.append(f"{element}{'●' * count}{'○' * (3 - min(count, 3))}({count})")
    print("  " + "  ".join(bar_parts))

    section("冲合关系")
    chong = udm.get_chong()
    he = udm.get_he()
    kv("冲", ", ".join(chong) if chong else "无")
    kv("合", ", ".join(he) if he else "无")

    section("命盘特征")
    if udm.features:
        for i, feat in enumerate(udm.features, 1):
            print(f"  {i}. {feat}")
    else:
        print("  无明显特征")

    section("大运")
    if udm.dayun:
        print(f"  起运年龄：{udm.dayun_start_age} 岁（{udm.dayun_start_year} 年）")
        print()
        # 打印大运表
        print(f"  {'序号':　^4}  {'干支':　^6}  {'起始年龄':　^6}  {'起始年份':　^6}")
        for i, d in enumerate(udm.dayun[:10], 1):
            gz = d.get("ganzhi", "?")
            age = d.get("start_age", "?")
            yr = d.get("start_year", "?")
            print(f"  {i:>4}  {gz:　^6}  {age:>6}  {yr:>6}")
    else:
        print("  大运数据不可用")


# ──────────────────── 输出：紫微 ────────────────────


def print_ziwei(udm):
    section("紫微斗数")

    zc = udm.ziwei_chart
    if not zc:
        print("  紫微数据不可用")
        return

    kv("命宫", zc.get("ming_gong", "?"))
    kv("身宫", zc.get("shen_gong", "?"))
    kv("命宫干支", zc.get("ming_ganzhi", "?"))
    ju = zc.get("wuxing_ju", {})
    kv("五行局", f"{ju.get('wuxing', '?')}{ju.get('ju_shu', '?')}局")
    kv("紫微星位", zc.get("ziwei_zhi", "?"))
    gender = zc.get("gender", "?")
    kv("性别", gender)

    section("四化")
    sihua = zc.get("sihua", {})
    for k in ["禄", "权", "科", "忌"]:
        star = sihua.get(k, "-")
        print(f"  化{k}：{star}")

    section("主星落宫")
    sp = zc.get("star_placements", {})
    if sp:
        # 按宫位分组
        palace_stars = {}
        for star, palace in sp.items():
            palace_stars.setdefault(palace, []).append(star)

        palaces = zc.get("palaces", [])
        for p in palaces:
            pname = p.get("name", "?")
            pzhi = p.get("zhi", "?")
            stars_in = p.get("stars", [])
            star_str = "、".join(stars_in) if stars_in else "（空宫）"
            marker = " ◀ 命宫" if pname == "命宫" else ""
            marker = " ◀ 身宫" if pname == "身宫" and not marker else marker
            print(f"  {pname}（{pzhi}）：{star_str}{marker}")
    else:
        print("  星曜数据不可用")


# ──────────────────── 输出：占星 ────────────────────


def print_astro(udm):
    section("西洋占星")

    ac = udm.astro_chart
    if not ac:
        print("  占星数据不可用")
        return

    if ac.get("error"):
        print(f"  错误：{ac['error']}")
        return

    kv("太阳星座", ac.get("sun_sign", "?"))
    kv("月亮星座", ac.get("moon_sign", "?"))
    kv("上升星座", ac.get("ascendant_sign", "?"))
    kv("太阳元素", ac.get("sun_element", "?"))
    kv("月亮元素", ac.get("moon_element", "?"))
    kv("MC（天顶）", f"{ac.get('mc', 0):.2f}°")

    section("行星位置")
    planets = ac.get("planets", {})
    if planets:
        print(f"  {'行星':　<6} {'星座':　<6} {'度数':　>6} {'元素':　<4}")
        print(f"  {'─' * 30}")
        for pname, pdata in planets.items():
            if isinstance(pdata, dict) and "sign" in pdata:
                sign = pdata.get("sign", "?")
                deg = pdata.get("degree", 0)
                elem = pdata.get("element", "?")
                print(f"  {pname:　<6} {sign:　<6} {deg:>6.2f}° {elem:　<4}")
            else:
                print(f"  {pname:　<6} （计算失败）")

    section("主要相位")
    aspects = ac.get("aspects", [])
    if aspects:
        for asp in aspects:
            p1 = asp.get("p1", "?")
            p2 = asp.get("p2", "?")
            aspect = asp.get("aspect", "?")
            angle = asp.get("angle", 0)
            orb = asp.get("orb", 0)
            print(f"  {p1} {aspect} {p2}（{angle:.1f}°，容许{orb:.1f}°）")
    else:
        print("  无主要相位")


# ──────────────────── 错误报告 ────────────────────


def print_errors(udm):
    if udm.engine_errors:
        section("引擎错误")
        for name, err in udm.engine_errors.items():
            print(f"  ⚠ {name}：{err}")


# ──────────────────── analyze 命令 ────────────────────


def cmd_analyze(args):
    """纯本地排盘，不调用 LLM"""
    banner("玄照 v2.0 — 命盘分析")

    ct, udm, _ = run_engines(args.birth, args.location, args.gender)

    print_time_info(ct)
    print_bazi(udm)
    print_ziwei(udm)
    print_astro(udm)
    print_errors(udm)

    print(f"\n{THICK}")
    print("  分析完成（纯本地数据，未调用 AI）")
    print(THICK)


# ──────────────────── predict 命令 ────────────────────


def cmd_predict(args):
    """排盘 + LLM 视角推理"""
    banner("玄照 v2.0 — 多视角推理")

    ct, udm, gender = run_engines(args.birth, args.location, args.gender)

    # 先打印排盘
    print_time_info(ct)
    print_bazi(udm)
    print_ziwei(udm)
    print_astro(udm)
    print_errors(udm)

    # LLM 视角推理
    question = args.question or "综合运势如何"

    # 选择代表视角：从各类别各选一两个
    selected_ids = _pick_perspectives(5)

    section(f"AI 多视角推理 — 问题：{question}")
    print(f"  选取 {len(selected_ids)} 个视角：{', '.join(FIGURES[fid].name for fid in selected_ids)}")
    print()

    from engine.llm_client import get_llm_client
    llm = get_llm_client()
    pe = PerspectiveEngine(llm_client=llm)

    try:
        opinions = pe.analyze(udm, question, figure_ids=selected_ids)
    except Exception as e:
        print(f"  ⚠ 视角推理出错：{e}")
        traceback.print_exc()
        opinions = []

    for op in opinions:
        _print_opinion(op)

    print(f"\n{THICK}")
    print("  推理完成（本地排盘 + AI 多视角分析）")
    print(THICK)


def _pick_perspectives(n: int = 5) -> list:
    """从所有人物中选取 n 个代表视角，覆盖不同术法和流派"""
    priority_ids = [
        "yuan-tiangang",   # 八字 — 中国玄学
        "ni-haixia",       # 紫微 — 中国玄学
        "li-chunfeng",     # 占星 — 中国玄学
        "jung",            # 占星 — 西方心理学
        "feynman",         # 占星 — 现代理性
    ]
    # 只返回实际存在的 id
    available = [fid for fid in priority_ids if fid in FIGURES]
    return available[:n]


def _print_opinion(op):
    """打印单个视角观点"""
    confidence_bar = "●" * int(op.confidence * 10) + "○" * (10 - int(op.confidence * 10))

    print(f"\n  ┌─ {op.figure_name}（{op.figure_title}）─ {op.primary_method}")
    print(f"  │  口头禅：「{FIGURES[op.figure_id].catchphrase}」")
    print(f"  │")
    print(f"  │  立场：{op.stance}")
    print(f"  │  置信度：[{confidence_bar}] {op.confidence:.0%}")
    print(f"  │")
    print(f"  │  推理：")
    # 缩进推理文本
    for line in op.reasoning.split("\n"):
        line = line.strip()
        if line:
            print(f"  │    {line}")
    print(f"  │")
    if op.key_points:
        print(f"  │  核心观点：")
        for pt in op.key_points:
            print(f"  │    ◆ {pt}")
    if op.quotes:
        print(f"  │")
        print(f"  │  引用：")
        for q in op.quotes:
            print(f"  │    「{q}」")
    print(f"  └{'─' * 50}")


# ──────────────────── demo 命令 ────────────────────


def cmd_demo(args):
    """用预设数据跑完整流程"""
    print("玄照 v2.0 — 演示模式")
    print("使用预设数据：2005-06-09 11:50, 呼和浩特, 男")
    print()

    # 先跑 analyze
    class DemoArgs:
        birth = "2005-06-09 11:50"
        location = "呼和浩特"
        gender = "男"

    demo_args = DemoArgs()

    # --- 第一部分：排盘 ---
    cmd_analyze(demo_args)

    # --- 第二部分：LLM 推理 ---
    print("\n\n")
    print("═" * 60)
    print("  接下来调用 AI 进行多视角推理演示...")
    print("═" * 60)

    demo_args.question = "事业如何"
    cmd_predict(demo_args)


# ──────────────────── 主入口 ────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="玄照 v2.0 — 命理分析命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python xuanzhao.py analyze --birth '2005-06-09 11:50' --location 呼和浩特 --gender 男
  python xuanzhao.py predict --birth '2005-06-09 11:50' --location 呼和浩特 --gender 男 --question '事业如何'
  python xuanzhao.py demo
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="排盘分析（纯本地，不调 LLM）")
    p_analyze.add_argument("--birth", required=True, help="出生时间，如 '2005-06-09 11:50'")
    p_analyze.add_argument("--location", required=True, help="出生地点，如 呼和浩特")
    p_analyze.add_argument("--gender", required=True, help="性别：男/女")

    # predict
    p_predict = subparsers.add_parser("predict", help="排盘 + AI 多视角推理")
    p_predict.add_argument("--birth", required=True, help="出生时间")
    p_predict.add_argument("--location", required=True, help="出生地点")
    p_predict.add_argument("--gender", required=True, help="性别：男/女")
    p_predict.add_argument("--question", default="综合运势如何", help="要问的问题")

    # demo
    p_demo = subparsers.add_parser("demo", help="用预设数据演示完整流程")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "predict":
        cmd_predict(args)
    elif args.command == "demo":
        cmd_demo(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
