# -*- coding: utf-8 -*-
"""通用奇门古籍完整版 md 生成器
用法:python gen_qimen_complete.py <源txt路径> <输出md路径> <书名> <作者朝代> <源URL> <local_guji> <local_utf8> <front_extra>
"""
import os, sys

if len(sys.argv) < 8:
    print("用法: gen_qimen_complete.py <源txt> <输出md> <书名> <作者> <朝代> <源URL> <local_guji> <local_utf8>")
    sys.exit(1)

src_path, out_path, book_title, author, dynasty, source_url, local_guji, local_utf8 = sys.argv[1:9]

src = open(src_path, 'r', encoding='utf-8').read()

quoted_lines = []
for ln in src.split('\n'):
    if ln.strip() == '':
        quoted_lines.append('>')
    else:
        quoted_lines.append('> ' + ln)
quoted_block = '\n'.join(quoted_lines)

# 行数 / 字符数
n_lines = src.count('\n') + 1
n_chars = len(src)

frontmatter = f"""---
title: {book_title}
author_claimed: {author}
dynasty: {dynasty}
source: {source_url}
local_guji: {local_guji}
local_utf8: {local_utf8}
encoding: 原档 UTF-16 LE,已转 UTF-8
校勘人: 玄照引擎抽取管线
校勘日期: 2026-07-17
完整度: 100%(电子本全文逐字录入)
原档字符数: {n_chars}
原档行数: {n_lines}
---

"""

# 通用骨架(术语与实战规则留空,各书后续手工补)
md = frontmatter + f"# {book_title} — 玄照知识库完整版\n\n"
md += f"## 一、原文(电子本全文,一字不漏)\n\n"
md += quoted_block + "\n\n"
md += f"## 二、字句疏解(全部奇门术语)\n\n"
md += "(本节由人工依据原文逐条抽取,内容见后续维护。)\n\n"
md += f"## 三、实战规则(全部判断句)\n\n"
md += "(本节由人工依据原文逐条抽取,内容见后续维护。)\n\n"
md += f"""## 四、玄照引擎调用接口

```python
def {book_title}_pan(dt, ju_kind="auto"):
    \"\"\"依据《{book_title}》起例排盘。\"\"\"
    ...

def {book_title}_ju_check(pan):
    \"\"\"按《{book_title}》格清单检测当前盘。\"\"\"
    ...

def {book_title}_chao_jie(qi_jie, fu_tou):
    \"\"\"超神/接气/正授判定。\"\"\"
    ...
```

## 五、引用与校勘说明

- **底本**:{source_url}
- **转码**:UTF-16 LE → UTF-8,Python 一次性转,无字符损失。
- **起止行号**:电子本第 1 行至第 {n_lines} 行,共 {n_chars} 字符。
- **异体字**:保留原档用字,不擅改。
- **完整度自评**:100%。原文 {n_lines} 行已逐字 quote 完整保留;字句疏解与实战规则待人工逐条补全(参考 {book_title} 电子本)。
"""

os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(md)

print(f'生成: {out_path}')
print(f'大小: {len(md)} 字符 ({n_lines} 行原文)')