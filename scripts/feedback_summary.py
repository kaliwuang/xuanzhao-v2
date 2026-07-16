#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
玄照反馈汇总脚本

读 data/feedback.jsonl,生成统计报告:
  - markdown 报告 → data/feedback_summary_{YYYY-MM-DD}.md
  - rating 饼图   → data/feedback_summary_{YYYY-MM-DD}.png

用法:
    python scripts/feedback_summary.py
    python scripts/feedback_summary.py --date 2026-07-09
    python scripts/feedback_summary.py --input data/feedback.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import matplotlib
    matplotlib.use("Agg")  # 无 GUI 后端,服务器也能跑
    import matplotlib.pyplot as plt

    # 解决 Windows 中文显示问题
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "Heiti SC",
        "Arial Unicode MS",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    HAS_MPL = True
except Exception:  # pragma: no cover
    HAS_MPL = False


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "data" / "feedback.jsonl"
DATA_DIR = PROJECT_ROOT / "data"

VALID_RATINGS = {"accurate", "partial", "inaccurate"}


# ---------- 数据读取 ----------

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """逐行读取 jsonl,跳过空行和损坏行(带警告)。"""
    if not path.exists():
        raise FileNotFoundError(f"找不到反馈文件: {path}")

    records: list[dict[str, Any]] = []
    skipped = 0
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[warn] 第 {lineno} 行 JSON 解析失败,已跳过: {e}", file=sys.stderr)
                skipped += 1
                continue
            if not isinstance(obj, dict):
                print(f"[warn] 第 {lineno} 行不是 JSON 对象,已跳过", file=sys.stderr)
                skipped += 1
                continue
            records.append(obj)

    if skipped:
        print(f"[info] 共跳过 {skipped} 行异常数据", file=sys.stderr)
    return records


def parse_ts(record: dict[str, Any]) -> datetime | None:
    """从记录里抽时间戳,容错处理。"""
    ts = record.get("ts")
    if not ts:
        return None
    s = str(ts).strip()
    # 去掉末尾的 'Z'
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    # 没时区就当 UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------- 统计 ----------

def pct(num: int, denom: int) -> float:
    return (num / denom * 100.0) if denom else 0.0


def build_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    """聚合所有统计指标。"""
    total = len(records)

    rating_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    topic_rating: dict[str, Counter[str]] = defaultdict(Counter)
    timestamps: list[datetime] = []

    for r in records:
        rating = (r.get("rating") or "").strip().lower()
        topic = (r.get("topic") or "").strip() or "(未填)"

        rating_counter[rating] += 1
        topic_counter[topic] += 1
        topic_rating[topic][rating] += 1

        dt = parse_ts(r)
        if dt:
            timestamps.append(dt)

    # 时间分布
    if timestamps:
        earliest = min(timestamps)
        latest = max(timestamps)
        seven_days_ago = latest - timedelta(days=7)
        recent_7d = sum(1 for t in timestamps if t >= seven_days_ago)
    else:
        earliest = latest = None
        recent_7d = 0

    # topic 准确率
    topic_table: list[dict[str, Any]] = []
    for topic, total_t in topic_counter.most_common():
        c = topic_rating[topic]
        n_accurate = c.get("accurate", 0)
        n_partial = c.get("partial", 0)
        n_inaccurate = c.get("inaccurate", 0)
        n_other = total_t - n_accurate - n_partial - n_inaccurate
        acc_pct = pct(n_accurate, total_t)
        topic_table.append({
            "topic": topic,
            "total": total_t,
            "accurate": n_accurate,
            "partial": n_partial,
            "inaccurate": n_inaccurate,
            "other": n_other,
            "accurate_pct": acc_pct,
        })

    # 排名
    good_topics = [t for t in topic_table if t["total"] >= 1 and t["accurate_pct"] > 70.0]
    bad_topics = [t for t in topic_table if t["total"] >= 1 and t["accurate_pct"] < 30.0]

    return {
        "total": total,
        "rating_counter": dict(rating_counter),
        "topic_counter": dict(topic_counter),
        "topic_table": topic_table,
        "earliest": earliest,
        "latest": latest,
        "recent_7d": recent_7d,
        "good_topics": good_topics,
        "bad_topics": bad_topics,
    }


# ---------- 渲染 ----------

def fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def render_markdown(stats: dict[str, Any], date_str: str) -> str:
    total = stats["total"]
    rc = stats["rating_counter"]
    topic_table = stats["topic_table"]

    lines: list[str] = []
    lines.append(f"# 玄照反馈汇总报告 · {date_str}")
    lines.append("")
    lines.append(f"生成时间:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 总览
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 总反馈数:**{total}**")
    if total:
        lines.append(f"- accurate:**{rc.get('accurate', 0)}** ({pct(rc.get('accurate', 0), total):.1f}%)")
        lines.append(f"- partial:**{rc.get('partial', 0)}** ({pct(rc.get('partial', 0), total):.1f}%)")
        lines.append(f"- inaccurate:**{rc.get('inaccurate', 0)}** ({pct(rc.get('inaccurate', 0), total):.1f}%)")
        other = total - rc.get("accurate", 0) - rc.get("partial", 0) - rc.get("inaccurate", 0)
        if other:
            lines.append(f"- 其他/未分类:**{other}** ({pct(other, total):.1f}%)")
    lines.append("")

    # 时间分布
    lines.append("## 时间分布")
    lines.append("")
    lines.append(f"- 最早反馈:{fmt_dt(stats['earliest'])}")
    lines.append(f"- 最新反馈:{fmt_dt(stats['latest'])}")
    lines.append(f"- 最近 7 天:**{stats['recent_7d']}** 条")
    lines.append("")

    # Topic 表
    lines.append("## 各 Topic 分布")
    lines.append("")
    if topic_table:
        lines.append("| Topic | N | accurate | partial | inaccurate | 其他 | 准确率 |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for t in topic_table:
            lines.append(
                f"| {t['topic']} | {t['total']} | {t['accurate']} | {t['partial']} | {t['inaccurate']} | {t['other']} | {t['accurate_pct']:.1f}% |"
            )
    else:
        lines.append("_暂无数据_")
    lines.append("")

    # 排名
    lines.append("## 准的 Topic(accurate% > 70%)")
    lines.append("")
    if stats["good_topics"]:
        for t in sorted(stats["good_topics"], key=lambda x: -x["accurate_pct"]):
            lines.append(f"- **{t['topic']}** — {t['accurate_pct']:.1f}% ({t['accurate']}/{t['total']})")
    else:
        lines.append("_暂无_")
    lines.append("")

    lines.append("## 不准的 Topic(accurate% < 30%)")
    lines.append("")
    if stats["bad_topics"]:
        for t in sorted(stats["bad_topics"], key=lambda x: x["accurate_pct"]):
            lines.append(f"- **{t['topic']}** — {t['accurate_pct']:.1f}% ({t['accurate']}/{t['total']})")
    else:
        lines.append("_暂无_")
    lines.append("")

    return "\n".join(lines) + "\n"


def render_pie(stats: dict[str, Any], png_path: Path) -> bool:
    """生成 rating 饼图。返回是否成功。"""
    if not HAS_MPL:
        print("[warn] matplotlib 不可用,跳过饼图生成", file=sys.stderr)
        return False

    rc = stats["rating_counter"]
    labels_map = {
        "accurate": "accurate(准)",
        "partial": "partial(部分)",
        "inaccurate": "inaccurate(不准)",
    }
    colors_map = {
        "accurate": "#4CAF50",
        "partial": "#FFC107",
        "inaccurate": "#F44336",
    }

    items = [(k, rc.get(k, 0)) for k in ["accurate", "partial", "inaccurate"] if rc.get(k, 0)]
    other_count = sum(v for k, v in rc.items() if k not in {"accurate", "partial", "inaccurate"})
    if other_count:
        items.append(("其他", other_count))

    if not items:
        print("[info] 没有 rating 数据,跳过饼图", file=sys.stderr)
        return False

    labels = [labels_map.get(k, k) for k, _ in items]
    values = [v for _, v in items]
    colors = [colors_map.get(k, "#9E9E9E") for k, _ in items]

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.75,
        textprops={"fontsize": 12},
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")

    ax.set_title(f"玄照反馈 Rating 分布 · {stats['total']} 条", fontsize=14, pad=20)
    fig.tight_layout()
    fig.savefig(png_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return True


# ---------- 主流程 ----------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="玄照反馈汇总脚本")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="jsonl 输入路径")
    p.add_argument(
        "--date",
        type=str,
        default=None,
        help="报告日期(YYYY-MM-DD),默认今天",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=DATA_DIR,
        help="输出目录,默认 data/",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    # 校验日期格式
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"[error] 日期格式不对,需要 YYYY-MM-DD,收到: {date_str}", file=sys.stderr)
        return 2

    input_path: Path = args.input
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / f"feedback_summary_{date_str}.md"
    png_path = out_dir / f"feedback_summary_{date_str}.png"

    print(f"[info] 读取 {input_path} ...")
    try:
        records = load_jsonl(input_path)
    except FileNotFoundError as e:
        print(f"[error] {e}", file=sys.stderr)
        print("提示:确认 data/feedback.jsonl 存在,或用 --input 指定路径", file=sys.stderr)
        return 1

    if not records:
        print("[warn] 没有任何反馈记录,生成空报告", file=sys.stderr)

    stats = build_stats(records)

    md = render_markdown(stats, date_str)
    md_path.write_text(md, encoding="utf-8")
    print(f"[ok] markdown 报告 → {md_path}")

    if render_pie(stats, png_path):
        print(f"[ok] 饼图 → {png_path}")
    else:
        # 即使没图也要保证主产物存在
        if not png_path.exists():
            png_path.write_text("", encoding="utf-8")

    print(f"[done] 共处理 {stats['total']} 条反馈")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[abort] 用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"[fatal] 未捕获异常: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)