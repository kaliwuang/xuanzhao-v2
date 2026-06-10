#!/usr/bin/env python3
"""Generate a static chart result page for screenshot"""
import json

with open('/tmp/chart_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('frontend/css/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

bazi = data.get('bazi', {})
astro = data.get('astro', {})
ziwei = data.get('ziwei', {})
liuyao = data.get('liuyao', {})
qimen = data.get('qimen', {})
liuren = data.get('liuren', {})
taiyi = data.get('taiyi', {})

parts = []
parts.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>玄照 - 排盘结果</title><style>')
parts.append(css)
parts.append('</style></head><body>')
parts.append('<nav class="nav"><a href="/" class="nav-brand">玄照 <span>v2.0</span></a><div class="nav-links"><a href="/" class="active">排盘</a><a href="/perspectives">108视角</a><a href="/debate">辩论台</a></div></nav>')
parts.append('<div class="container">')
parts.append('<div class="hero"><h1 class="hero-title" style="font-size:2rem;">玄照 · 排盘结果</h1><p class="hero-subtitle">出生：2005-06-09 11:50 | 呼和浩特 | 男</p><div class="hero-divider"></div></div>')

# Bazi
if bazi:
    parts.append('<div class="card"><div class="card-title">八字四柱</div><div class="bazi-pillars">')
    for label, key in [('年柱','year'),('月柱','month'),('日柱','day'),('时柱','time')]:
        gz = bazi.get(key, '')
        if gz:
            nayin = (bazi.get('nayin',{}) or {}).get(key, '')
            parts.append(f'<div class="pillar"><div class="pillar-label">{label}</div><div class="pillar-gan">{gz[0]}</div><div class="pillar-zhi">{gz[1]}</div><div class="pillar-nayin">{nayin}</div></div>')
    parts.append('</div>')
    ss = bazi.get('shishen_gan', {})
    if ss:
        parts.append('<div class="shishen-grid">')
        for label, key in [('年柱','year'),('月柱','month'),('日柱','day'),('时柱','time')]:
            s = ss.get(key, '')
            if s:
                parts.append(f'<div class="shishen-item">{label}: {s}</div>')
        parts.append('</div>')
    dm = bazi.get('day_master','')
    dmw = bazi.get('day_master_wuxing','')
    th = bazi.get('tiaohou','')
    parts.append(f'<div style="margin-top:1rem;text-align:center;color:var(--accent-gold);">日主：{dm} ({dmw})<span style="margin-left:1rem;color:var(--text-muted);">调候用神：{th}</span></div>')
    features = bazi.get('features', [])
    if features:
        parts.append('<div class="feature-tags">')
        for f in features:
            cls = ' highlight' if '冲' in f else ''
            parts.append(f'<span class="feature-tag{cls}">{f}</span>')
        parts.append('</div>')
    parts.append('</div>')

# Astro
if astro:
    sun = astro.get('sun_sign','')
    se = astro.get('sun_element','')
    moon = astro.get('moon_sign','')
    me = astro.get('moon_element','')
    asc = astro.get('ascendant_sign','')
    parts.append(f'<div class="card"><div class="card-title">西洋占星</div><div style="margin-bottom:1rem;text-align:center;"><span style="color:var(--accent-gold);margin-right:2rem;">太阳：{sun} ({se})</span><span style="margin-right:2rem;">月亮：{moon} ({me})</span><span style="color:var(--text-muted);">上升：{asc}</span></div>')
    planets = astro.get('planets', {}) or {}
    if planets:
        parts.append('<div class="astro-planets">')
        for name, info in planets.items():
            if isinstance(info, dict):
                parts.append(f'<div class="planet"><div class="planet-name">{name}</div><div class="planet-sign">{info.get("sign","")}</div><div style="color:var(--text-muted);font-size:0.75rem;">{info.get("degree","")}</div></div>')
        parts.append('</div>')
    parts.append('</div>')

# Ziwei
if ziwei:
    wh = ziwei.get('wuxing_ju', {})
    wx = wh.get('wuxing','') if isinstance(wh, dict) else ''
    js = wh.get('ju_shu','') if isinstance(wh, dict) else ''
    mg = ziwei.get('ming_gong','')
    parts.append(f'<div class="card"><div class="card-title">紫微斗数</div><div class="ziwei-info-bar"><span>命宫：{mg}</span><span>五行局：{wx}{js}局</span></div><div class="ziwei-board">')
    cellZhi = {0:'巳',1:'午',2:'未',3:'申',4:'辰',7:'酉',8:'卯',11:'戌',12:'寅',13:'丑',14:'子',15:'亥'}
    zhiMap = {}
    for p in (ziwei.get('palaces', []) or []):
        zhiMap[p.get('zhi','')] = p
    for i in range(16):
        if i not in cellZhi:
            parts.append('<div class="ziwei-cell empty"></div>')
        else:
            zhi = cellZhi[i]
            pal = zhiMap.get(zhi)
            cls = ' ming-gong' if pal and pal.get('name') == '命宫' else ''
            stars_html = ''
            if pal and pal.get('stars'):
                for star in pal['stars']:
                    stars_html += f'<span class="ziwei-star-main">{star}</span>'
            name = pal.get('name','') if pal else ''
            parts.append(f'<div class="ziwei-cell{cls}"><div class="ziwei-cell-header"><span class="ziwei-cell-zhi">{zhi}</span><span class="ziwei-cell-name">{name}</span></div><div class="ziwei-cell-stars">{stars_html}</div></div>')
    parts.append('</div></div>')

# Liuyao
if liuyao:
    bg = liuyao.get('ben_gua', {})
    dy = liuyao.get('dong_yao', 0)
    parts.append(f'<div class="card"><div class="card-title">六爻</div><div class="gua-info"><div class="gua-name">{bg.get("name","")}</div><div>动爻：第{dy}爻</div></div></div>')

# Qimen
if qimen:
    jn = qimen.get('ju_name','')
    parts.append(f'<div class="card"><div class="card-title">奇门遁甲</div><div style="text-align:center;margin-bottom:1rem;color:var(--accent-gold);">{jn}</div><div class="qimen-grid">')
    dp = qimen.get('di_pan',{}) or {}
    bm = qimen.get('ba_men',{}) or {}
    for gong in ['巽四','离九','坤二','震三','中五','兑七','艮八','坎一','乾六']:
        cls = ' center' if gong == '中五' else ''
        parts.append(f'<div class="qimen-cell{cls}"><div class="qimen-gong">{gong}</div><div class="qimen-di">{dp.get(gong,"")}</div><div class="qimen-men">{bm.get(gong,"")}</div></div>')
    parts.append('</div></div>')

# Liuren
if liuren:
    yj = liuren.get('yue_jiang','')
    parts.append(f'<div class="card"><div class="card-title">大六壬</div><p class="info-line"><span class="label">月将：</span>{yj}</p>')
    sk = liuren.get('si_ke', [])
    if sk:
        parts.append('<p class="info-line"><span class="label">四课：</span>' + '，'.join(k.get('ke','') for k in sk) + '</p>')
    sc = liuren.get('san_chuan', [])
    if sc:
        parts.append('<p class="info-line"><span class="label">三传：</span>' + ' → '.join(c.get('name','') for c in sc) + '</p>')
    parts.append('</div>')

# Taiyi
if taiyi:
    tg = taiyi.get('taiyi_gong','')
    jn = taiyi.get('ji_nian',0)
    yy = taiyi.get('yin_yang','')
    parts.append(f'<div class="card"><div class="card-title">太乙神数</div><div class="taiyi-info"><div class="taiyi-gong">{tg}</div><div class="info-line" style="margin-top:0.5rem;"><span class="label">积年数：</span>{jn}</div><div class="info-line"><span class="label">阴阳遁：</span>{yy}</div></div></div>')

parts.append('</div></body></html>')

with open('frontend/chart_result.html', 'w', encoding='utf-8') as f:
    f.write('\n'.join(parts))
print('Static chart page created')
