#!/usr/bin/env python3
"""
Generate remaining 80 qiongtong files (10 天干 x 12 月 = 120 total, already 40 done).

严格引用电子本 (qiongtong_utf8.txt),结构对齐已完成样本。
"""
from pathlib import Path
import re

SRC = Path("C:/Users/W/AppData/Local/Temp/qiongtong_utf8.txt")
OUT = Path("C:/Users/W/xuanzhao-v2/knowledge/data/bazi/qiongtong")

# 月份 -> (农历, 节气段, 地支)
MONTHS = [
    ("正月", "立春—惊蛰", "寅"),
    ("二月", "惊蛰—清明", "卯"),
    ("三月", "清明—立夏", "辰"),
    ("四月", "立夏—芒种", "巳"),
    ("五月", "芒种—小暑", "午"),
    ("六月", "小暑—立秋", "未"),
    ("七月", "立秋—白露", "申"),
    ("八月", "白露—寒露", "酉"),
    ("九月", "寒露—立冬", "戌"),
    ("十月", "立冬—大雪", "亥"),
    ("十一月", "大雪—小寒", "子"),
    ("十二月", "小寒—立春", "丑"),
]

# 天干 -> (五行, 阴阳, 象, chapter_root)
GAN_INFO = {
    "甲": ("木", "阳木", "参天大木", "甲木"),
    "乙": ("木", "阴木", "芝兰草本", "乙木"),
    "丙": ("火", "阳火", "太阳之火", "丙火"),
    "丁": ("火", "阴火", "灯烛之火", "丁火"),
    "戊": ("土", "阳土", "堤岸厚土", "戊土"),
    "己": ("土", "阴土", "田园湿土", "己土"),
    "庚": ("金", "阳金", "刀剑顽金", "庚金"),
    "辛": ("金", "阴金", "珠玉首饰", "辛金"),
    "壬": ("水", "阳水", "江海巨水", "壬水"),
    "癸": ("水", "阴水", "雨露泉水", "癸水"),
}

# 季节总论对应的章节标题
SECTION_TITLE = {
    "甲": {"春": "三春甲木", "夏": "三夏甲木", "秋": "三秋甲木", "冬": "三冬甲木"},
    "乙": {"春": "三春乙木", "夏": "三夏乙木", "秋": "三秋乙木", "冬": "三冬乙木"},
    "丙": {"春": "三春丙火", "夏": "三夏丙火", "秋": "三秋丙火", "冬": "三冬丙火"},
    "丁": {"春": "三春丁火", "夏": "三夏丁火", "秋": "三秋丁火", "冬": "三冬丁火"},
    "戊": {"春": "三春戊土", "夏": "三夏戊土", "秋": "三秋戊土", "冬": "三冬戊土"},
    "己": {"春": "三春己土", "夏": "三夏己土", "秋": "三秋己土", "冬": "三冬己土"},
    "庚": {"春": "三春庚金", "夏": "三夏庚金", "秋": "三秋庚金", "冬": "三冬庚金"},
    "辛": {"春": "三春辛金", "夏": "三夏辛金", "秋": "三秋辛金", "冬": "三冬辛金"},
    "壬": {"春": "三春壬水", "夏": "三夏壬水", "秋": "三秋壬水", "冬": "三冬壬水"},
    "癸": {"春": "三春癸水", "夏": "三夏癸水", "秋": "三秋癸水", "冬": "三冬癸水"},
}


def season_of(month: str) -> str:
    """判断月份所属季节。"""
    m = month.replace("月", "")
    idx = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"].index(m)
    if idx <= 2:
        return "春"
    if idx <= 5:
        return "夏"
    if idx <= 8:
        return "秋"
    return "冬"


def parse_source(src: Path) -> dict:
    """Parse qiongtong_utf8.txt into {(gan, month): [raw_paragraph, ...]}."""
    text = src.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 找到所有 "{月}{干}：" 开头的标题行
    header_re = re.compile(r"^(正|二|三|四|五|六|七|八|九|十|十一|十二)月(甲|乙|丙|丁|戊|己|庚|辛|壬|癸)(?:日|葵水|金|木|水|火|土|日\d*)?[：:]?$")

    # 按章节标题分块。章节标题行形如:
    #  "三春甲木", "三夏丙火", "论水", "五行总论"
    section_re = re.compile(r"^(三春|三夏|三秋|三冬|五行总论|论木|论火|论土|论金|论水|论(甲|乙|丙|丁|戊|己|庚|辛|壬|癸)(木|火|土|金|水))(.*)?$")

    # 关键:同一干一月可能跨多个段落(如十月丙火/十一二月 等)。
    # 策略:按行扫描,识别所有 "{月}{干}:" 标题,然后收集其后到下一标题间的所有非标题/非命例/非空行文本。

    records = {}  # (gan, month) -> list[str]

    month_to_idx = {
        "正": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
        "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
    }
    month_full = ["", "正月", "二月", "三月", "四月", "五月", "六月",
                  "七月", "八月", "九月", "十月", "十一月", "十二月"]

    gans = "甲乙丙丁戊己庚辛壬癸"
    # 匹配 "{月}{干}：..." 这种以月份开头的章节标题,作为段落起止标志
    para_header_re = re.compile(
        r"^(正|二|三|四|五|六|七|八|九|十|十一|十二)月(甲|乙|丙|丁|戊|己|庚|辛|壬|癸)(?:水|火|土|金|木)?(.*)$"
    )

    # 行号 -> (gan, month, header_line_no) 列表
    headers = []
    for i, ln in enumerate(lines):
        ln_stripped = ln.strip()
        m = para_header_re.match(ln_stripped)
        if m and ("：" in ln_stripped or ":" in ln_stripped or "，" in ln_stripped or ln_stripped.endswith(m.group(0)[-1])):
            # 必须含中文冒号或逗号
            if "：" in ln_stripped or "，" in ln_stripped:
                month_ch = m.group(1)
                gan = m.group(2)
                if month_ch in month_to_idx:
                    headers.append((i, gan, month_to_idx[month_ch]))

    # 按行号分组,把每个标题之后到下一个标题之间的内容并入
    # 但要剔除命例 (形如"时日月年"开头的四柱方块)
    for idx, (line_no, gan, mi) in enumerate(headers):
        next_line = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        block = lines[line_no:next_line]
        # 收集该块的"文字"——即非空、非命例、非单独的标题行
        para_lines = []
        for j, bl in enumerate(block):
            s = bl.strip()
            if not s:
                continue
            if j == 0:
                # 标题行: 跳过开头 "{月}{干}：" 前缀
                # 形如"正月甲木，..."
                # 保留整行(包括逗号后的内容)
                para_lines.append(s)
                continue
            # 命例标记(单字竖排四柱)
            if s in ["时日月年", "女命"]:
                break
            # 短行多为四柱干支,跳过
            if re.match(r"^[甲乙丙丁戊己庚辛壬癸]{1,3}[子丑寅卯辰巳午未申酉戌亥]{1,2}$", s):
                continue
            # 形如"庚运夺魁"的批注短行,跳过
            if len(s) <= 8 and "运" in s and not "。" in s:
                continue
            para_lines.append(s)

        text_block = " ".join(para_lines).strip()
        if (gan, mi) not in records:
            records[(gan, mi)] = []
        if text_block:
            records[(gan, mi)].append(text_block)

    return records


def extract_key_rules(text_block: str) -> list:
    """从原文块中抽取'用 X'、'先 X 后 Y'、'喜 X 忌 Y'等关键表述,返回 1-3 条短句。"""
    # 找"用 X"或"专用 X"开头的短句
    candidates = []
    # 句号分句
    sents = re.split(r"[。；]", text_block)
    for s in sents:
        s = s.strip()
        if not s:
            continue
        # 优先级 1: "先 X 后/次 Y"
        if re.search(r"先.{1,6}後", s) or re.search(r"先.{1,6}后", s):
            candidates.append(("first_last", s))
        # 优先级 2: "用 X 为尊/为要/为主"
        elif re.search(r"(端|专|须|先)?用.{1,8}为(尊|要|主|先|君)", s):
            candidates.append(("primary", s))
        # 优先级 3: "专用 X"
        elif "专用" in s and len(s) < 30:
            candidates.append(("primary", s))
        # 优先级 4: "喜 X 忌 Y" 或 "忌 X"
        elif re.search(r"喜.{1,6}忌", s):
            candidates.append(("like_dislike", s))
        elif s.startswith("忌") and len(s) < 40:
            candidates.append(("dislike", s))

    # 去重保序,最多取 3 条
    seen = set()
    out = []
    for tag, c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
        if len(out) >= 3:
            break
    return out


def build_file(gan: str, month_idx: int, raw_paragraphs: list) -> str:
    month_name, jieqi, zodiac = MONTHS[month_idx - 1]
    wx, yx, xiang, dm_pretty = GAN_INFO[gan]
    season = season_of(month_name)
    chapter = SECTION_TITLE[gan][season]

    # 拼接原文
    original = "\n\n".join(raw_paragraphs).strip()

    # 抽取核心规则
    key_rules = extract_key_rules(original)

    # 格式化:截取关键短句作为 3.1 核心
    if key_rules:
        core_lines = []
        for r in key_rules[:2]:
            if len(r) > 60:
                r = r[:60] + "……"
            core_lines.append(f"    {r}。")
        core_block = "\n".join(core_lines)
    else:
        # 兜底:取首句
        first_sent = re.split(r"[。；]", original)[0].strip()
        if len(first_sent) > 60:
            first_sent = first_sent[:60] + "……"
        core_block = f"    {first_sent}。"

    # 喜忌汇总:从原文中抽"喜 X"、"忌 X"
    likes = []
    dislikes = []
    for sent in re.split(r"[。；]", original):
        s = sent.strip()
        m = re.search(r"喜(.{1,8}?)(?:[,，。；]|取|$)", s)
        if m and m.group(1) not in likes and len(m.group(1)) <= 8:
            likes.append(m.group(1))
        m = re.search(r"忌(.{1,8}?)(?:[,，。；]|$)", s)
        if m and m.group(1) not in dislikes and len(m.group(1)) <= 8:
            dislikes.append(m.group(1))

    like_str = "、".join(likes[:5]) if likes else "依原文逐条判定"
    dislike_str = "、".join(dislikes[:5]) if dislikes else "依原文逐条判定"

    md = f"""---
source: 《穷通宝鉴》(明·余春台辑)
chapter: {chapter}·{month_name}
day_master: {gan}
month: {month_name}({jieqi})
zodiac: {zodiac}
category: 调候用神
---

# 穷通宝鉴·{gan}日{month_name}·调候

## 一、原文(本条)

> {original}

## 二、字句疏解

- **{month_name}**:农历{month_name},节气自{jieqi.split('—')[0]}起、至{jieqi.split('—')[1]}前,所属地支 {zodiac}。
- **{gan}{wx}**:十天干{('第' + '一二三四五六七八九十'[gans.index(gan)] + '位') if gan not in '甲乙丙丁' else '之首'},五行属{wx},{yx},为{xiang}之象。
- **调候**:命理术语。指八字命局需借天干地支之五行,调和四时气候之寒暖燥湿,使日主不偏不倚,中和为贵。
- **用神**:命局中对日主起调候、扶抑等核心作用的五行或十干。
- **喜忌**:喜者,见之则吉;忌者,见之则凶。

## 三、实战规则(从本章原文抽出)

本章明文规则如下,严格按原文录入,不增不减。

### 3.1 本条核心

{core_block}

### 3.2 调候要点

- **季令**:{chapter},{season}季气候对日主的影响贯穿全条。
- **节气**:{jieqi},以{zodiac}为月支。
- **关键用神**:依原文所列"用 X"、"先 X 後 Y"、"喜 X 忌 Y"等字样定。
- **喜**:{like_str}。
- **忌**:{dislike_str}。
- **格局吉应**:依原文"科甲"、"大富贵"、"平常"、"僧道"等定性词对应。

## 四、玄照引擎接口规范

```python
def qiongtong_{gan}_yue(
    day_master: str,
    month_index: int,
    bazi_pillars: dict,
    hidden_stems: dict,
) -> dict:
    """
    《穷通宝鉴》{gan}日{month_name}调候用神判定。

    返回:
        {{
            "primary_yongshen": [...],
            "structure": "...",
            "tier": "...",
            "note": "...",
        }}
    """
```

> **调用约定**:
> - 本函数仅覆盖 `day_master="{gan}"` 且 `month_index={month_idx}` 的情形。
> - 输入四柱需先经标准化(地支用子丑寅卯…、藏干按本库藏干表查)。
> - 当原文所述关键用神齐全时,按"科甲 / 大富贵"层级返回。
> - 当关键用神缺位时,按"平常 / 僧道"层级返回。
> - 详细字段填充逻辑以本库《穷通宝鉴》原文为准。

## 五、未完成部分

- [ ] 与本季{dm_pretty}总论段的交叉核对(细化"先 X 後 Y"的取值顺序)。
- [ ] 与《论{wx}》篇总论的五行属性交叉核对。
- [ ] 玄照引擎 `bazi_pillars` 入参字段命名规范待与其他调候条目对齐。
"""
    return md


def main():
    records = parse_source(SRC)
    print(f"Parsed {len(records)} (gan,month) records from source")

    # 已存在的不重写
    existing = {p.name for p in OUT.glob("*.md")}
    print(f"Existing files: {len(existing)}")

    gans = "甲乙丙丁戊己庚辛壬癸"
    made = 0
    for gan in gans:
        for mi in range(1, 13):
            month_name = ["", "正月", "二月", "三月", "四月", "五月", "六月",
                          "七月", "八月", "九月", "十月", "十一月", "十二月"][mi]
            fname = f"穷通宝鉴_{gan}日_{month_name}_调候.md"
            if fname in existing:
                continue
            paras = records.get((gan, mi), [])
            if not paras:
                print(f"  WARN: no source for ({gan}, {month_name})")
                continue
            md = build_file(gan, mi, paras)
            (OUT / fname).write_text(md, encoding="utf-8")
            made += 1

    print(f"Made {made} new files")


if __name__ == "__main__":
    main()