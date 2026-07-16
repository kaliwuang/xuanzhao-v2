#!/usr/bin/env python3
"""Extract chapters from source file."""
import sys

sys.stdout.reconfigure(encoding='utf-8')

SRC = r'C:\Users\W\AppData\Local\Temp\ditiansui_utf8.txt'
OUT = r'C:\Users\W\xuanzhao-v2\knowledge\data\bazi\ditiansui\_chapters_raw.json'

with open(SRC, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-8-sig', errors='replace')
lines = [l.rstrip('\r') for l in text.split('\n')]
if lines:
    lines[0] = lines[0].lstrip('﻿')

# Drop trailing empty lines
while lines and lines[-1].strip() == '':
    lines.pop()

print(f"Total lines: {len(lines)}", file=sys.stderr)

# Chapter definitions: (num, title, section, start_line, end_line_inclusive)
# end = (next chapter start - 1) for all but last; last extends to len(lines)
chapter_defs_raw = [
    ('二', '地道', '通神论', 75),
    ('三', '人道', '通神论', 80),
    ('四', '知命', '通神论', 85),
    ('五', '理气', '通神论', 175),
    ('六', '配合', '通神论', 209),
    ('七', '天干', '通神论', 241),
    ('八', '地支', '通神论', 280),
    ('九', '干支总论', '通神论', 465),
    ('十', '形象', '通神论', 922),
    ('十一', '方局', '通神论', 1220),
    ('十二', '八格', '通神论', 1385),
    ('十三', '体用', '通神论', 1508),
    ('十四', '精神', '通神论', 1535),
    ('十五', '月令', '通神论', 1578),
    ('十六', '生时', '通神论', 1608),
    ('十七', '衰旺', '通神论', 1613),
    ('十八', '中和', '通神论', 1896),
    ('十九', '源流', '通神论', 1925),
    ('二十', '通关', '通神论', 1986),
    ('二十一', '官杀', '通神论', 2045),
    ('二十二', '伤官', '通神论', 2459),
    ('二十三', '清气', '通神论', 2855),
    ('二十四', '浊气', '通神论', 2900),
    ('二十五', '真神', '通神论', 2943),
    ('二十六', '假神', '通神论', 2988),
    ('二十七', '刚柔', '通神论', 3030),
    ('二十八', '顺逆', '通神论', 3086),
    ('二十九', '寒暖', '通神论', 3128),
    ('三十', '燥湿', '通神论', 3185),
    ('三十一', '隐显', '通神论', 3243),
    ('三十二', '众寡', '通神论', 3274),
    ('三十三', '震兑', '通神论', 3317),
    ('三十四', '坎离', '通神论', 3392),
    ('一', '夫妻', '六亲论', 3466),
    ('二', '子女', '六亲论', 3511),
    ('三', '父母', '六亲论', 3613),
    ('四', '兄弟', '六亲论', 3670),
    ('五', '何知章', '六亲论', 3701),
    ('六', '女命章', '六亲论', 4133),
    ('七', '小儿', '六亲论', 4586),
    ('八', '才德', '六亲论', 4679),
    ('九', '奋郁', '六亲论', 4720),
    ('十', '恩怨', '六亲论', 4775),
    ('十一', '闲神', '六亲论', 4817),
    ('十二', '从象', '六亲论', 4905),
    ('十三', '化象', '六亲论', 5049),
    ('十四', '假从', '六亲论', 5121),
    ('十五', '假化', '六亲论', 5193),
    ('十六', '顺局', '六亲论', 5264),
    ('十七', '反局', '六亲论', 5395),
    ('十八', '战局', '六亲论', 5644),
    ('十九', '合局', '六亲论', 5727),
    ('二十', '君象', '六亲论', 5826),
    ('二十一', '臣象', '六亲论', 5855),
    ('二十二', '母象', '六亲论', 5911),
    ('二十三', '子象', '六亲论', 5941),
    ('二十四', '性情', '六亲论', 5971),
    ('二十五', '疾病', '六亲论', 6481),
    ('二十六', '出身', '六亲论', 6823),
    ('二十七', '地位', '六亲论', 7218),
    ('二十八', '岁运', '六亲论', 7500),
    ('二十九', '贞元', '六亲论', 7601),
]

# Compute end
import json
chapters_data = []
for i, (num, title, section, start) in enumerate(chapter_defs_raw):
    if i + 1 < len(chapter_defs_raw):
        end = chapter_defs_raw[i+1][3] - 1
    else:
        end = len(lines)
    s_idx = start - 1
    e_idx = end - 1
    content = lines[s_idx:e_idx+1]
    # Strip leading/trailing blank lines
    while content and not content[0].strip():
        content.pop(0)
    while content and not content[-1].strip():
        content.pop()
    chapters_data.append({
        'num': num,
        'title': title,
        'section': section,
        'start_line': start,
        'end_line': end,
        'content_lines': content,
    })

print(f"Total chapters extracted: {len(chapters_data)}", file=sys.stderr)
for c in chapters_data[:3]:
    print(f"  {c['section']}·第{c['num']}章 {c['title']}: lines {c['start_line']}-{c['end_line']}, {len(c['content_lines'])} content lines", file=sys.stderr)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(chapters_data, f, ensure_ascii=False, indent=2)

print(f"Wrote {OUT}", file=sys.stderr)
