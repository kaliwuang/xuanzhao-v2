import re
import os

files = [
    r'C:\Users\W\AppData\Local\Temp\qimen_utf8\qimen_baojian_utf8.txt',
    r'C:\Users\W\AppData\Local\Temp\qimen_utf8\qimen_zhigui_utf8.txt',
    r'C:\Users\W\AppData\Local\Temp\qimen_utf8\qimen_faqiao_utf8.txt',
    r'C:\Users\W\AppData\Local\Temp\qimen_utf8\qimen_miji_utf8.txt',
]

for fp in files:
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()
    lines = text.split('\n')
    keys = []
    for ln in lines:
        s = ln.strip()
        if 2 <= len(s) <= 25 and not re.search(r'[，。！？、；：「」『』《》（）\(\)\[\]]', s):
            if s:
                keys.append(s)
    seen = set()
    out = []
    for k in keys:
        if k not in seen:
            seen.add(k); out.append(k)
    base = os.path.basename(fp).replace('.txt', '')
    out_path = f'C:/Users/W/xuanzhao-v2/scripts/qimen_extract/{base}_keys.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print(f'{base}: {len(out)} keys → {out_path}')