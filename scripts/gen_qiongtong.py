#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
穷通宝鉴 120条 md 生成器。
"""
import re
from pathlib import Path

SRC = Path(r"C:/Users/W/AppData/Local/Temp/qiongtong_utf8.txt")
OUT = Path(r"C:/Users/W/xuanzhao-v2/knowledge/data/bazi/qiongtong")

DAY_NAMES = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
MONTH_NAMES = ["正月", "二月", "三月", "四月", "五月", "六月",
               "七月", "八月", "九月", "十月", "十一月", "十二月"]
MONTH_QI = [
    "立春—惊蛰", "惊蛰—清明", "清明—立夏",
    "立夏—芒种", "芒种—小暑", "小暑—立秋",
    "立秋—白露", "白露—寒露", "寒露—立冬",
    "立冬—大雪", "大雪—小寒", "小寒—立春"
]
MONTH_ZODIAC = ["寅", "卯", "辰", "巳", "午", "未",
                 "申", "酉", "戌", "亥", "子", "丑"]


def season(month_idx):
    if month_idx in [0, 1, 2]:
        return "三春"
    if month_idx in [3, 4, 5]:
        return "三夏"
    if month_idx in [6, 7, 8]:
        return "三秋"
    return "三冬"


def file_name(day, month_idx):
    return f"穷通宝鉴_{day}日_{MONTH_NAMES[month_idx]}_调候.md"


text = SRC.read_text(encoding="utf-8")
lines = text.split("\n")


def find_season_section(day, month_idx):
    """返回该月段所在行范围 [start, end)。"""
    season_cn = season(month_idx)
    # 找 "三X天干Y" 子标题
    pat = re.compile(rf"^{re.escape(season_cn)}{re.escape(day)}")
    start_i = None
    for i, ln in enumerate(lines):
        if pat.match(ln.strip()):
            start_i = i
            break
    if start_i is None:
        return None
    # 终止: 下一季同天干 / 下一天干同季 / 论X
    end_i = len(lines)
    next_seasons = [s for s in ["三春", "三夏", "三秋", "三冬"] if s != season_cn]
    next_stems = [d for d in DAY_NAMES if d != day]
    for j in range(start_i + 1, len(lines)):
        s = lines[j].strip()
        if any(s.startswith(p) for p in next_stems) and any(s.startswith(p) for p in next_seasons + [f"论{day}"]):
            end_i = j
            break
        if s.startswith("论") and 2 <= len(s) <= 4:
            end_i = j
            break
    return (start_i, end_i)


def extract_raw(day, month_idx):
    """从该月段中抽出对应月份那段原文。"""
    rng = find_season_section(day, month_idx)
    if rng is None:
        return None
    start_i, end_i = rng
    chunk = lines[start_i:end_i]

    month_cn = MONTH_NAMES[month_idx]
    pat = re.compile(rf"^{re.escape(month_cn)}(?!季)")

    sub_start = None
    for i, ln in enumerate(chunk):
        s = ln.strip()
        if pat.match(s):
            sub_start = i
            break
    if sub_start is None:
        return None

    sub_end = len(chunk)
    for j in range(sub_start + 1, len(chunk)):
        s = chunk[j].strip()
        # 下一月
        if re.match(r"^[一二三四五六七八九十]+月(?!季)", s):
            sub_end = j
            break
        # 总论 / 季末泛论收束 (如"总之夏月之乙木...")
        if s.startswith(f"凡{season(month_idx)}{day}") or s.startswith(f"总之{season(month_idx)}{day}") or s.startswith(f"故{season(month_idx)}{day}") or s.startswith(f"书曰：{day}"):
            sub_end = j
            break
        # 时日月年专栏
        if s == "时日月年":
            sub_end = j
            break
        # 下一季同天干
        if s.startswith(f"{season(month_idx)}{day}") and s != f"{season(month_idx)}{day}木" and s != f"{season(month_idx)}{day}" and len(s) <= 5:
            sub_end = j
            break

    raw_lines = []
    for ln in chunk[sub_start:sub_end]:
        s = ln.strip()
        if not s:
            continue
        if s == "时日月年":
            break
        if re.fullmatch(r"[甲乙丙丁戊己庚辛壬癸]{2,4}", s):
            continue
        # 柱子示例: "丙寅，庚寅，戊辰，庚申"
        if re.search(r"[年日月时]", s) and len(s) < 30 and "," in s:
            continue
        raw_lines.append(s)

    return "\n".join(raw_lines)


# 引擎接口模板
def engine_template(day, month_idx):
    return f"""def qiongtong_{day.lower()}_yue(
    day_master: str,
    month_index: int,
    bazi_pillars: dict,
    hidden_stems: dict,
) -> dict:
    \"\"\"
    《穷通宝鉴》{day}日{MONTH_NAMES[month_idx]}调候用神判定。

    返回:
        {{
            "primary_yongshen": [...],
            "structure": "...",
            "tier": "...",
            "note": "...",
        }}
    \"\"\"
"""


# 字句疏解 - 抽核心术语
TERM_DICT = {
    "甲": "十天干之首,五行属木,阳木,为参天大木之象。",
    "乙": "十天干第二位,五行属木,阴木,为花草藤蔓之象。",
    "丙": "十天干第三位,五行属火,阳火,为太阳之火。",
    "丁": "十天干第四位,五行属火,阴火,为灯烛之火。",
    "戊": "十天干第五位,五行属土,阳土,为高岗厚土。",
    "己": "十天干第六位,五行属土,阴土,为田园湿土。",
    "庚": "十天干第七位,五行属金,阳金,为刀剑斧钺。",
    "辛": "十天干第八位,五行属金,阴金,为珠玉首饰。",
    "壬": "十天干第九位,五行属水,阳水,为江河大海。",
    "癸": "十天干第十位,五行属水,阴水,为雨露泉泽。",
}


def make_md(day, month_idx):
    raw = extract_raw(day, month_idx)
    if not raw:
        return None

    zodiac = MONTH_ZODIAC[month_idx]
    season_cn = season(month_idx)
    chapter = f"{season_cn}{day}{get_element(day)}·{MONTH_NAMES[month_idx]}"
    title = f"穷通宝鉴·{day}日{MONTH_NAMES[month_idx]}·调候"
    fname = file_name(day, month_idx)
    qi = MONTH_QI[month_idx]

    # 摘要(从原文前 60 字内抽一句含"用X/喜X/忌X")
    summary = ""
    for s in raw.split("\n"):
        m = re.search(r"([^。,，]{2,40}(?:用[^。,，]+|喜[^。,，]+|忌[^。,，]+|端用[^。,，]+|先[^。,，]+再用[^。,，]+)[^。,，]{0,40}[。,，])", s)
        if m:
            summary = m.group(1).strip()
            if summary and not summary.endswith("。"):
                summary += "。"
            break

    if not summary:
        summary = raw.split("\n")[0][:120]

    md = f"""---
source: 《穷通宝鉴》(明·余春台辑)
chapter: {chapter}
day_master: {day}
month: {MONTH_NAMES[month_idx]}({qi})
zodiac: {zodiac}
category: 调候用神
---

# {title}

## 一、原文(本条)

> {raw.replace(chr(10), ' ')}

## 二、字句疏解

- **{MONTH_NAMES[month_idx]}**:农历{MONTH_NAMES[month_idx]},节气自{MONTH_QI[month_idx].split('—')[0]}起、至{MONTH_QI[month_idx].split('—')[1]}前,所属地支 {zodiac}。
- **{day}{get_element(day)}**:{TERM_DICT[day]}
- **调候**:命理术语。指八字命局需借天干地支之五行,调和四时气候之寒暖燥湿,使日主不偏不倚,中和为贵。
- **用神**:命局中对日主起调候、扶抑等核心作用的五行或十干。
- **喜忌**:喜者,见之则吉;忌者,见之则凶。

## 三、实战规则(从本章原文抽出)

本章明文规则如下,严格按原文录入,不增不减。

### 3.1 本条核心

{summary}

### 3.2 调候要点

- **季令**:{season_cn}{day}{get_element(day)},{season_cn}气候对日主的影响贯穿全条。
- **节气**:{qi},以{MONTH_ZODIAC[month_idx]}为月支。
- **关键用神**:依原文所列"用 X"、"先 X 後 Y"、"喜 X 忌 Y"等字样定。
- **格局吉应**:依原文"科甲"、"大富贵"、"平常"、"僧道"等定性词对应。

## 四、玄照引擎接口规范

```python
{engine_template(day, month_idx).strip()}
```

> **调用约定**:
> - 本函数仅覆盖 `day_master="{day}"` 且 `month_index={month_idx+1}` 的情形。
> - 输入四柱需先经标准化(地支用子丑寅卯…、藏干按本库藏干表查)。
> - 当原文所述关键用神齐全时,按"科甲 / 大富贵"层级返回。
> - 当关键用神缺位时,按"平常 / 僧道"层级返回。
> - 详细字段填充逻辑以本库《穷通宝鉴》原文为准。

## 五、未完成部分

- [ ] 与本季{day}{get_element(day)}总论段的交叉核对(细化"先 X 後 Y"的取值顺序)。
- [ ] 与《论{get_element_parent(day)}》篇总论的五行属性交叉核对。
- [ ] 玄照引擎 `bazi_pillars` 入参字段命名规范待与其他调候条目对齐。
"""

    return md


def get_element(day):
    """天干对应五行。"""
    return {
        "甲": "木", "乙": "木",
        "丙": "火", "丁": "火",
        "戊": "土", "己": "土",
        "庚": "金", "辛": "金",
        "壬": "水", "癸": "水"
    }[day]


def get_element_parent(day):
    """天干对应父母五行类。"""
    return get_element(day)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    generated = []
    skipped = []
    for day in DAY_NAMES:
        for month_idx in range(12):
            md = make_md(day, month_idx)
            if md is None:
                skipped.append((day, MONTH_NAMES[month_idx]))
                continue
            fp = OUT / file_name(day, month_idx)
            fp.write_text(md, encoding="utf-8")
            generated.append(str(fp.relative_to(OUT)))

    print(f"生成: {len(generated)} / 120")
    print(f"跳过: {len(skipped)}")
    for s in skipped:
        print(f"  - {s[0]} {s[1]}")


if __name__ == "__main__":
    main()