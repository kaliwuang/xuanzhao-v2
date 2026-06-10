#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
玄照 v2.0 — 独立 CLI 工具
七术排盘 × 视角推理 × 交叉验证

用法:
  python xuanzhao.py analyze --birth "2005-06-09 11:50" --location 呼和浩特 --gender 男
  python xuanzhao.py predict --birth "2005-06-09 11:50" --location 呼和浩特 --gender 男 --question "事业如何"
  python xuanzhao.py demo
"""
import argparse
import json
import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERSION = "2.0.0"


def cmd_analyze(args):
    """七术排盘（纯本地，不调 LLM）"""
    from engine.time_engine import get_time_engine
    from engine.base import EngineOrchestrator
    from engine.bazi_engine import BaziEngine
    from engine.astro_engine import AstroEngine
    from engine.ziwei_engine import ZiWeiEngine
    from engine.liuyao_engine import LiuYaoEngine
    from engine.qimen_engine import QiMenEngine
    from engine.liuren_engine import LiuRenEngine
    from engine.taiyi_engine import TaiYiEngine

    te = get_time_engine()
    corrected = te.correct(args.birth, args.location)
    gender = 1 if args.gender in ("男", "male", "m") else 0

    orch = EngineOrchestrator()
    for eng in [BaziEngine(), AstroEngine(), ZiWeiEngine(),
                LiuYaoEngine(), QiMenEngine(), LiuRenEngine(), TaiYiEngine()]:
        orch.register(eng)

    udm = orch.run_all(corrected, gender)

    # 输出
    print("\n" + "═" * 50)
    print("        玄照 · 七术排盘报告")
    print("═" * 50)
    print(f"\n出生: {args.birth}  地点: {args.location}  性别: {args.gender}")
    print(f"真太阳时: {corrected.true_solar.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"经度: {corrected.longitude}°  纬度: {corrected.latitude}°")
    if corrected.is_late_zi:
        print("⚠️  晚子时，日柱已按次日计算")

    # 八字
    if udm.bazi_year:
        print(f"\n{'─' * 50}")
        print("【八字命盘】")
        print(f"  年柱: {udm.bazi_year.ganzhi}    月柱: {udm.bazi_month.ganzhi if udm.bazi_month else '?'}")
        print(f"  日柱: {udm.bazi_day.ganzhi if udm.bazi_day else '?'}    时柱: {udm.bazi_time.ganzhi if udm.bazi_time else '?'}")
        print(f"  日主: {udm.day_master} ({udm.day_master_wuxing})")
        if udm.shishen_gan:
            print(f"  十神: {json.dumps(udm.shishen_gan, ensure_ascii=False)}")
        if udm.nayin:
            print(f"  纳音: {json.dumps(udm.nayin, ensure_ascii=False)}")
        if udm.features:
            print(f"  特征: {' | '.join(udm.features)}")
        if udm.tiaohou:
            print(f"  调候用神: {udm.tiaohou}")
        chong = udm.get_chong()
        he = udm.get_he()
        if chong:
            print(f"  冲: {' | '.join(chong)}")
        if he:
            print(f"  合: {' | '.join(he)}")
        wx_count = udm.get_wuxing_count()
        if wx_count:
            print(f"  五行分布: {json.dumps(wx_count, ensure_ascii=False)}")

    # 占星
    if udm.astro_chart:
        print(f"\n{'─' * 50}")
        print("【占星命盘】")
        ac = udm.astro_chart
        print(f"  太阳: {ac.get('sun_sign', '?')} ({ac.get('sun_element', '?')})")
        print(f"  月亮: {ac.get('moon_sign', '?')} ({ac.get('moon_element', '?')})")
        print(f"  上升: {ac.get('ascendant_sign', '?')}")
        planets = ac.get("planets", {})
        if planets:
            print(f"  行星: ", end="")
            for name, data in planets.items():
                if isinstance(data, dict):
                    print(f"{name}={data.get('sign', '?')} ", end="")
            print()

    # 紫微
    if udm.ziwei_chart:
        print(f"\n{'─' * 50}")
        print("【紫微斗数】")
        zw = udm.ziwei_chart
        print(f"  命宫: {zw.get('ming_gong', '?')}")
        wj = zw.get("wuxing_ju", {})
        if isinstance(wj, dict):
            print(f"  五行局: {wj.get('name', '?')}")
        sihua = zw.get("sihua", {})
        if sihua:
            print(f"  四化: {json.dumps(sihua, ensure_ascii=False)}")

    # 六爻
    if udm.liuyao_chart:
        print(f"\n{'─' * 50}")
        print("【六爻纳甲】")
        ly = udm.liuyao_chart
        print(f"  本卦: {ly.get('ben_gua', {}).get('name', '?')}")
        print(f"  动爻: 第{ly.get('dong_yao', '?')}爻")

    # 奇门
    if udm.qimen_chart:
        print(f"\n{'─' * 50}")
        print("【奇门遁甲】")
        qm = udm.qimen_chart
        print(f"  局: {qm.get('ju_name', '?')}")

    # 大六壬
    if udm.liuren_chart:
        print(f"\n{'─' * 50}")
        print("【大六壬】")
        lr = udm.liuren_chart
        print(f"  月将: {lr.get('yue_jiang', '?')}")

    # 太乙
    if udm.taiyi_chart:
        print(f"\n{'─' * 50}")
        print("【太乙神数】")
        ty = udm.taiyi_chart
        print(f"  太乙宫: {ty.get('taiyi_gong', '?')}")

    # 引擎错误
    if udm.engine_errors:
        print(f"\n⚠️  引擎错误:")
        for eng_name, err in udm.engine_errors.items():
            print(f"  {eng_name}: {err}")

    available = udm.get_available_methods()
    print(f"\n{'═' * 50}")
    print(f"可用术法: {', '.join(available)} ({len(available)}/7)")
    print("═" * 50)

    if args.format == "json":
        result = {
            "birth": args.birth, "location": args.location, "gender": args.gender,
            "true_solar": corrected.true_solar.isoformat(),
            "methods": available, "errors": udm.engine_errors,
        }
        if udm.bazi_year:
            result["bazi"] = {
                "year": udm.bazi_year.ganzhi, "month": udm.bazi_month.ganzhi if udm.bazi_month else "",
                "day": udm.bazi_day.ganzhi if udm.bazi_day else "", "time": udm.bazi_time.ganzhi if udm.bazi_time else "",
                "day_master": udm.day_master, "day_master_wuxing": udm.day_master_wuxing,
                "features": udm.features, "tiaohou": udm.tiaohou,
            }
        if udm.astro_chart:
            result["astro"] = {"sun_sign": udm.astro_chart.get("sun_sign"), "moon_sign": udm.astro_chart.get("moon_sign")}
        if udm.ziwei_chart:
            result["ziwei"] = {"ming_gong": udm.ziwei_chart.get("ming_gong")}
        print("\n" + json.dumps(result, ensure_ascii=False, indent=2))


def cmd_predict(args):
    """排盘 + LLM 视角推理"""
    from engine.time_engine import get_time_engine
    from engine.base import EngineOrchestrator
    from engine.bazi_engine import BaziEngine
    from engine.astro_engine import AstroEngine
    from engine.ziwei_engine import ZiWeiEngine
    from engine.liuyao_engine import LiuYaoEngine
    from engine.qimen_engine import QiMenEngine
    from engine.liuren_engine import LiuRenEngine
    from engine.taiyi_engine import TaiYiEngine
    from engine.perspective_engine import PerspectiveEngine

    # 先排盘
    te = get_time_engine()
    corrected = te.correct(args.birth, args.location)
    gender = 1 if args.gender in ("男", "male", "m") else 0

    orch = EngineOrchestrator()
    for eng in [BaziEngine(), AstroEngine(), ZiWeiEngine(),
                LiuYaoEngine(), QiMenEngine(), LiuRenEngine(), TaiYiEngine()]:
        orch.register(eng)
    udm = orch.run_all(corrected, gender)

    print("\n" + "═" * 50)
    print("      玄照 · 群体智能预测报告")
    print("═" * 50)
    print(f"\n出生: {args.birth}  地点: {args.location}")
    print(f"问题: {args.question}")

    # 八字摘要
    if udm.bazi_year:
        pillars = f"{udm.bazi_year.ganzhi} {udm.bazi_month.ganzhi if udm.bazi_month else ''} {udm.bazi_day.ganzhi if udm.bazi_day else ''} {udm.bazi_time.ganzhi if udm.bazi_time else ''}"
        print(f"八字: {pillars}")
        print(f"日主: {udm.day_master} ({udm.day_master_wuxing})")
        if udm.features:
            print(f"特征: {' | '.join(udm.features)}")
        if udm.tiaohou:
            print(f"调候: {udm.tiaohou}")

    # 选择代表视角
    representative = ["zhuge-liang", "ni-haixia", "yuan-tiangang", "feynman", "jung"]
    if args.figures:
        representative = [f.strip() for f in args.figures.split(",")]

    print(f"\n{'─' * 50}")
    print(f"【多视角推理】({len(representative)} 个视角)")
    print("─" * 50)

    pe = PerspectiveEngine()
    opinions = pe.analyze(udm, args.question, representative)

    for op in opinions:
        print(f"\n┌─ {op.figure_name} ({op.figure_title}) ── {op.primary_method}视角")
        print(f"│  立场: {op.stance}")
        print(f"│  置信度: {op.confidence:.0%}")
        print(f"│  推理:")
        for line in op.reasoning.split("\n"):
            if line.strip():
                print(f"│    {line.strip()}")
        if op.key_points:
            print(f"│  要点: {' · '.join(op.key_points)}")
        if op.quotes:
            print(f"│  名言: 「{op.quotes[0]}」")
        print(f"└{'─' * 48}")

    # 交叉验证
    from engine.cross_validator import CrossValidator
    validator = CrossValidator(udm)
    result = validator.validate()

    print(f"\n{'═' * 50}")
    print("【交叉验证】")
    print(f"可用术法: {', '.join(result['available_methods'])}")
    print(f"整体置信度: {result['overall_confidence'].value}")

    if result["consensus"]:
        print(f"\n共识 ({len(result['consensus'])} 项):")
        for c in result["consensus"]:
            print(f"  ✓ {c.aspect}: {c.finding} [{c.confidence.value}]")

    if result["conflicts"]:
        print(f"\n分歧 ({len(result['conflicts'])} 项):")
        for c in result["conflicts"]:
            print(f"  ✗ {c.aspect}: {c.method_a}说「{c.finding_a}」vs {c.method_b}说「{c.finding_b}」")
            print(f"    建议: {c.suggestion}")

    print("\n" + "═" * 50)


def cmd_demo(args):
    """演示模式"""
    print("玄照 v" + VERSION + " 演示")
    print("使用预设数据运行完整流程...\n")

    # 先 analyze
    class Args:
        birth = "2005-06-09 11:50"
        location = "呼和浩特"
        gender = "男"
        format = "text"

    cmd_analyze(Args())

    print("\n\n" + "━" * 50)
    print("接下来运行 predict（需要 LLM API）...")
    print("━" * 50)

    class PredictArgs:
        birth = "2005-06-09 11:50"
        location = "呼和浩特"
        gender = "男"
        question = "此人事业和感情如何？"
        figures = None

    cmd_predict(PredictArgs())

    if args.output:
        print(f"\n报告已显示。如需保存到文件，请使用 shell 重定向: python xuanzhao.py demo > {args.output}")


def main():
    parser = argparse.ArgumentParser(description=f"玄照 v{VERSION} — 玄学群体智能预测系统")
    sub = parser.add_subparsers(dest="command")

    # analyze
    p_analyze = sub.add_parser("analyze", help="七术排盘（纯本地）")
    p_analyze.add_argument("--birth", required=True, help="出生时间，如 2005-06-09 11:50")
    p_analyze.add_argument("--location", default="北京", help="出生地点")
    p_analyze.add_argument("--gender", default="男", help="性别: 男/女")
    p_analyze.add_argument("--format", default="text", choices=["text", "json"], help="输出格式")

    # predict
    p_predict = sub.add_parser("predict", help="排盘 + LLM 视角推理")
    p_predict.add_argument("--birth", required=True, help="出生时间")
    p_predict.add_argument("--location", default="北京", help="出生地点")
    p_predict.add_argument("--gender", default="男", help="性别")
    p_predict.add_argument("--question", default="此人命运如何？", help="要问的问题")
    p_predict.add_argument("--figures", default=None, help="指定视角ID，逗号分隔")

    # demo
    p_demo = sub.add_parser("demo", help="演示模式")
    p_demo.add_argument("--output", default=None, help="输出文件路径（仅提示）")

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
