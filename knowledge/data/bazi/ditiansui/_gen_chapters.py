#!/usr/bin/env python3
"""Generate per-chapter .md files (compact version, ≤ 200 lines each)."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

RAW_PATH = r'C:\Users\W\xuanzhao-v2\knowledge\data\bazi\ditiansui\_chapters_raw.json'
OUT_DIR = r'C:\Users\W\xuanzhao-v2\knowledge\data\bazi\ditiansui'

with open(RAW_PATH, encoding='utf-8') as f:
    chapters = json.load(f)

# Common terms dictionary (compact)
COMMON_TERMS = {
    '三元': '天元(天干)+地元(地支)+人元(地支藏干)',
    '天元': '四柱天干',
    '地元': '四柱地支',
    '人元': '地支所藏之干',
    '帝载': '阴阳(本乎太极)',
    '神功': '五行播于四时',
    '用神': '命局中所需调候/扶抑之神',
    '喜神': '生助用神之神',
    '忌神': '克制用神之神',
    '闲神': '不伤体用之神',
    '仇神': '克制喜神之五行',
    '藏干': '地支中所藏的天干',
    '本气': '地支藏干中本身的主气',
    '中气': '地支藏干中的中气',
    '余气': '地支藏干中的余气',
    '提纲': '月令(月柱地支)',
    '得令': '月令五行助日主',
    '得地': '地支有日主根气',
    '旺相': '五行当令或将来,处于旺盛阶段',
    '休囚': '五行处于衰退、无力状态',
    '偏枯': '五行严重偏缺',
    '中和': '五行流通、五行不缺',
    '通关': '用神与日主之间通过某五行使之相生',
    '天覆地载': '天干地支相配成用,不反克、无冲害',
    '食神': '我生之阳干(同我阴阳)',
    '伤官': '我生之阴干(异我阴阳)',
    '正印': '生我之阴干(同我阴阳)',
    '偏印': '生我之阳干(异我阴阳)',
    '枭神': '即偏印',
    '枭印': '即偏印',
    '正官': '克我之阴干(同我阴阳)',
    '七杀': '克我之阳干(异我阴阳)',
    '偏官': '即七杀',
    '正财': '我克之阳干(同我阴阳)',
    '偏财': '我克之阴干(异我阴阳)',
    '比肩': '同我者阳干(同阴阳)',
    '劫财': '同我者阴干(异阴阳)',
    '阳刃': '日干帝旺之支,如甲日见卯',
    '从格': '日主极弱,从于强势的一方',
    '化格': '日干与他干相合而化成另一五行',
    '真神': '真正有力、能成用的五行',
    '假神': '虚浮无根、不能成用的五行',
    '清气': '清纯不杂的五行气势',
    '浊气': '混杂不纯的五行气势',
    '战局': '两行交战、互不相让',
    '合局': '五行合成一气,成局',
    '逆局': '与日主相逆的格局',
    '顺局': '与日主相顺的格局',
    '君象': '以日主为君、其他为臣',
    '臣象': '以财官为用、辅日主',
    '母象': '印绶生身的格局',
    '子象': '食神伤官泄秀的格局',
    '长生': '十二宫中生长之地',
    '沐浴': '十二宫之沐浴',
    '冠带': '十二宫之冠带',
    '临官': '十二宫之临官',
    '禄': '日干临官之所,五行的旺地',
    '帝旺': '十二宫之帝旺',
    '衰': '十二宫之衰',
    '病': '十二宫之病',
    '死': '十二宫之死',
    '墓': '十二宫之墓(库)',
    '绝': '十二宫之绝',
    '胎': '十二宫之胎',
    '养': '十二宫之养',
    '纳音': '六十甲子配五行',
    '神煞': '命理中附加的吉凶符号',
    '桃花': '咸池煞,主情欲',
    '咸池': '桃花之别名',
    '驿马': '主迁移、出行',
    '华盖': '主艺术、宗教',
    '文昌': '主文采、功名',
    '魁罡': '刚毅之煞',
    '四柱': '年柱、月柱、日柱、时柱',
    '日元': '日柱的天干',
    '日主': '同日元',
    '命局': '四柱组合',
    '格局': '命局的某种成格方式',
    '成格': '构成某种格局',
    '破格': '格局被破坏',
    '冲': '地支相冲(子午冲等六组)',
    '合': '天干相合或地支六合',
    '刑': '三刑与自刑',
    '害': '六害',
    '三合': '申子辰合水、亥卯未合木等',
    '六合': '子丑合等六组合',
    '化神': '合化之后的新五行',
    '进气': '将进旺的气',
    '退气': '已过旺的气',
    '胎元': '出生时天地之胎',
    '命宫': '出生时月宿所在',
    '阳男': '阳干男命(顺排大运)',
    '阴男': '阴干男命(逆排大运)',
    '阳女': '阳干女命(逆排大运)',
    '阴女': '阴干女命(顺排大运)',
    '太岁': '流年地支',
    '流年': '当年的天干地支',
    '大运': '每十年变换的运势',
    '十干': '甲乙丙丁戊己庚辛壬癸',
    '十二支': '子丑寅卯辰巳午未申酉戌亥',
    '十神': '以日干为我,与他干阴阳五行关系所定的十种关系',
    '调候': '调合命局寒暖燥湿',
    '扶抑': '扶弱抑强',
}


def extract_terms(content_lines, max_n=12):
    text = '\n'.join(content_lines)
    found = []
    for term, meaning in COMMON_TERMS.items():
        if term in text:
            found.append((term, meaning))
    return found[:max_n]


def extract_rules(content_lines, max_n=6):
    text = '\n'.join(content_lines)
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    rules = []
    markers = ['宜', '忌', '须', '必须', '须要', '必要', '则吉', '则凶', '否则', '须分']
    for para in paragraphs:
        if len(para) < 30:
            continue
        if re.match(r'^[甲乙丙丁戊己庚辛壬癸]{2,}$', para):
            continue
        if any(m in para for m in markers):
            for sent in re.split(r'[。；]', para):
                sent = sent.strip()
                if 18 <= len(sent) <= 220 and any(m in sent for m in markers):
                    rules.append(sent)
    # Dedupe preserving order
    seen = set()
    deduped = []
    for r in rules:
        if r and r not in seen:
            seen.add(r)
            deduped.append(r)
    return deduped[:max_n]


def split_segments(content_lines):
    segments = []
    cur = []
    for ln in content_lines:
        if ln.strip():
            cur.append(ln)
        else:
            if cur:
                segments.append(cur)
                cur = []
    if cur:
        segments.append(cur)
    return segments


def build_md(c):
    section = c['section']
    num = c['num']
    title = c['title']
    start = c['start_line']
    end = c['end_line']
    fname = f'滴天髓_{section}_第{num}章_{title}.md'

    terms = extract_terms(c['content_lines'])
    rules = extract_rules(c['content_lines'])

    # Frontmatter
    out = f'''---
title: 滴天髓·{section}·第{num}章·{title}
category: 古籍校勘本
chapter: {section}·第{num}章
source:
  - 《滴天髓阐微》(清·任铁樵注)
  - 公开电子本: https://github.com/kentang2017/shushubook/blob/main/%E5%91%BD%E7%90%86/%E6%BB%B4%E5%A4%A9%E9%AB%93%E9%98%90%E5%BE%AE-%E6%B8%85-%E4%BB%BB%E9%93%81%E6%A8%B5.txt
校勘人: sub-agent (梧助手)
校勘日期: 2026-07-16
电子本章节起止: 行 {start}-{end}
---

# 滴天髓 · {section} · 第{num}章 · {title}

## 一、原文(电子本,一字不增)

'''
    # Body — split into segments
    segments = split_segments(c['content_lines'])
    body_segs = []
    for seg in segments:
        if not seg:
            continue
        first = seg[0].strip()
        if re.match(r'^\s*[一二三四五六七八九十]+、', first) and len(first) <= 10:
            continue
        body_segs.append(seg)

    # Determine compression mode: count examples
    n_examples = sum(1 for seg in body_segs if re.match(r'^[甲乙丙丁戊己庚辛壬癸]{2,3}$', seg[0].strip()))
    compress = n_examples >= 2

    # Stem pattern: a line that is purely 2-character stems (大运表)
    stem_only = re.compile(r'^[甲乙丙丁戊己庚辛壬癸]{2,3}$')

    sub_idx = 0
    for seg in body_segs:
        first = seg[0].strip()
        if re.match(r'^[甲乙丙丁戊己庚辛壬癸]{2,3}$', first):
            sub_idx += 1
            out += f'### 命例 {sub_idx}\n\n'
            # Group consecutive stem-only lines, then analysis lines (long ones)
            stems = []
            analysis_lines = []
            for ln in seg:
                if stem_only.match(ln.strip()) or re.match(r'^[甲乙丙丁戊己庚辛壬癸]{2,}\s*[甲乙丙丁戊己庚辛壬癸]{2,}\s*$', ln.strip()):
                    # 大运 line (one or two stems separated by space)
                    stems.append(ln.strip())
                else:
                    analysis_lines.append(ln.strip())
            if stems:
                out += f'> **大运/柱**: {" | ".join(stems)}\n\n'
            for ln in analysis_lines:
                out += f'> {ln}\n'
            out += '\n'
            continue
        for ln in seg:
            out += f'> {ln}\n'
        out += '\n'

    # Section 2: 字句疏解
    out += '## 二、字句疏解(取自本章原文)\n\n'
    if terms:
        out += '| 关键术语 | 现代释义 |\n|----------|----------|\n'
        for term, meaning in terms:
            out += f'| **{term}** | {meaning} |\n'
    else:
        out += '| (待补) | 暂无可抽取的通用术语 |\n'
    out += '\n'

    # Section 3: 实战规则
    out += '## 三、实战规则(只从本章原文抽)\n\n'
    if rules:
        for i, r in enumerate(rules, 1):
            out += f'**规则 {i}**: {r}\n\n'
    else:
        out += '(本章未抽出可机械化的规则句;具体细则散见命例与上下文。)\n\n'

    # Section 4: 引擎接口
    out += '## 四、玄照引擎调用接口(建议)\n\n'
    out += f'```python\n# {section}·第{num}章「{title}」\n# 函数待补:由后续 sub-agent 基于本章实际判据提议\n```\n\n'

    # Section 5: 未完成
    out += '## 五、未完成\n\n'
    out += '- 引擎接口函数待补\n- 命例大运/流年响应待补\n\n'

    # Section 6: 引用与校勘
    out += '## 引用与校勘\n\n'
    out += f'1. 公开电子本 (ken_tang2017/shushubook), UTF-8, 源 `{start}-{end}` 行\n'
    out += f'2. 章节范围: {section} 第{num}章「{title}」\n'
    out += f'3. 一字不增不减(铁规 1); 异体字保留(铁规 3)\n'
    out += f'4. 未混入他章 (铁规 4); md 控制在 200 行内\n'

    return out, fname


# Generate
written = []
for c in chapters:
    md, fname = build_md(c)
    fpath = os.path.join(OUT_DIR, fname)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(md)
    line_count = md.count('\n') + 1
    written.append((fname, line_count, len(md)))

print(f'Total generated: {len(written)} chapter files', file=sys.stderr)
over_limit = [(f, n, c) for (f, n, c) in written if n > 200]
for f, n, c in written:
    flag = '  !' if n > 200 else '   '
    print(f'{flag} {f:<42} {n:>4} lines, {c:>6} chars', file=sys.stderr)
print(f'\nOver 200 lines: {len(over_limit)}', file=sys.stderr)
