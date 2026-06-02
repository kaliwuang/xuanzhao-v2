#!/usr/bin/env python3
from engine.time_engine import TimeEngine
from engine.base import EngineOrchestrator
from engine.bazi_engine import BaziEngine
from engine.astro_engine import AstroEngine
from engine.ziwei_engine import ZiWeiEngine
from engine.liuyao_engine import LiuYaoEngine
from engine.qimen_engine import QiMenEngine
from engine.liuren_engine import LiuRenEngine
from engine.taiyi_engine import TaiYiEngine
from engine.cross_validator import CrossValidator
from engine.perspective_engine import PerspectiveEngine
from engine.debate_engine import DebateEngine

te = TimeEngine()
corrected = te.correct('2005-06-09 11:50', '呼和浩特')

print('='*60)
print('玄照 v2.0 - 七术排盘报告')
print('='*60)
print('出生时间：2005-06-09 11:50（呼和浩特）')
print(f'真太阳时：{corrected.true_solar}')
print(f'经度：{corrected.longitude}°  纬度：{corrected.latitude}°')
print()

orch = EngineOrchestrator()
orch.register(BaziEngine())
orch.register(AstroEngine())
orch.register(ZiWeiEngine())
orch.register(LiuYaoEngine())
orch.register(QiMenEngine())
orch.register(LiuRenEngine())
orch.register(TaiYiEngine())

udm = orch.run_all(corrected, 1)

# 八字
print('-'*60)
print('【八字】')
print(f'四柱：{udm.bazi_year.ganzhi}  {udm.bazi_month.ganzhi}  {udm.bazi_day.ganzhi}  {udm.bazi_time.ganzhi}')
print('      年    月    日    时')
print(f'纳音：{udm.nayin.get("year","")}  {udm.nayin.get("month","")}  {udm.nayin.get("day","")}  {udm.nayin.get("time","")}')
print(f'十神：{udm.shishen_gan.get("year","")}  {udm.shishen_gan.get("month","")}  日元  {udm.shishen_gan.get("time","")}')
print(f'日主：{udm.day_master}（{udm.day_master_wuxing}）')
print(f'调候用神：{udm.tiaohou}')
print(f'特征：{", ".join(udm.features)}')
print()

# 紫微
print('-'*60)
print('【紫微斗数】')
if udm.ziwei_chart:
    zw = udm.ziwei_chart
    print(f'命宫：{zw["ming_gong"]}  五行局：{zw["wuxing_ju"]["wuxing"]}{zw["wuxing_ju"]["ju_shu"]}局')
    print(f'四化：禄-{zw["sihua"]["禄"]} 权-{zw["sihua"]["权"]} 科-{zw["sihua"]["科"]} 忌-{zw["sihua"]["忌"]}')
    print('主星分布：')
    for star, palace in zw['star_placements'].items():
        print(f'  {star} -> {palace}')
print()

# 占星
print('-'*60)
print('【西洋占星】')
if udm.astro_chart:
    ast = udm.astro_chart
    print(f'太阳：{ast["sun_sign"]}（{ast["sun_element"]}）')
    print(f'月亮：{ast["moon_sign"]}（{ast["moon_element"]}）')
    print(f'上升：{ast["ascendant_sign"]}')
    print(f'中天：{ast["mc"]}°')
    print('行星：', end='')
    for name, info in ast['planets'].items():
        print(f'{name}{info["sign"]} ', end='')
    print()
print()

# 六爻
print('-'*60)
print('【六爻】')
if udm.liuyao_chart:
    ly = udm.liuyao_chart
    print(f'本卦：{ly["ben_gua"]["name"]}')
    print(f'动爻：第{ly["dong_yao"]}爻')
print()

# 奇门
print('-'*60)
print('【奇门遁甲】')
if udm.qimen_chart:
    qm = udm.qimen_chart
    print(f'局数：{qm["ju_name"]}')
    print('地盘：', end='')
    for gong, gan in qm['di_pan'].items():
        print(f'{gong}:{gan} ', end='')
    print()
    print('八门：', end='')
    for gong, men in qm['ba_men'].items():
        print(f'{gong}:{men} ', end='')
    print()
print()

# 大六壬
print('-'*60)
print('【大六壬】')
if udm.liuren_chart:
    lr = udm.liuren_chart
    print(f'月将：{lr["yue_jiang"]}')
    print('四课：', end='')
    for ke in lr['si_ke']:
        print(f'{ke["ke"]} ', end='')
    print()
    print('三传：', end='')
    for chuan in lr['san_chuan']:
        print(f'{chuan["name"]} ', end='')
    print()
print()

# 太乙
print('-'*60)
print('【太乙神数】')
if udm.taiyi_chart:
    ty = udm.taiyi_chart
    print(f'太乙宫位：{ty["taiyi_gong"]}')
    print(f'积年数：{ty["ji_nian"]}')
    print(f'阴阳遁：{ty["yin_yang"]}')
print()

# 七术综合判断
print('='*60)
print('【七术综合判断】')
print()

# 收集各术核心信息
judgments = []

# 八字判断
if udm.bazi_year:
    dm = udm.day_master
    wx = udm.day_master_wuxing
    features = udm.features
    chong = udm.get_chong()
    he = udm.get_he()
    wuxing_count = udm.get_wuxing_count()
    wuxing_str = ' '.join([f'{k}{v}个' for k, v in wuxing_count.items() if v > 0])
    judgments.append(f'【八字】日主{dm}（{wx}），五行分布：{wuxing_str}')
    if features:
        judgments.append(f'       命局特征：{"、".join(features[:3])}')
    if chong:
        judgments.append(f'       冲：{"、".join(chong[:2])}')
    if udm.tiaohou:
        judgments.append(f'       调候用神：{udm.tiaohou}')

# 紫微判断
if udm.ziwei_chart:
    zw = udm.ziwei_chart
    ming = zw['ming_gong']
    wj = zw['wuxing_ju']
    ziwei_zhi = zw.get('ziwei_zhi', '')
    stars = zw.get('star_placements', {})
    # 找出命宫主星
    ming_stars = [s for s, p in stars.items() if p == '命宫']
    sihua = zw.get('sihua', {})
    judgments.append(f'【紫微】命宫在{ming}，五行局：{wj["wuxing"]}{wj["ju_shu"]}局，紫微在{ziwei_zhi}')
    if ming_stars:
        judgments.append(f'       命宫主星：{"、".join(ming_stars[:3])}')
    if sihua:
        sihua_str = ' '.join([f'{k}{v}' for k, v in sihua.items() if v])
        judgments.append(f'       四化：{sihua_str}')

# 占星判断
if udm.astro_chart:
    ast = udm.astro_chart
    judgments.append(f'【占星】太阳{ast["sun_sign"]}，月亮{ast["moon_sign"]}，上升{ast.get("ascendant_sign", "-")}')

# 六爻判断
if udm.liuyao_chart:
    ly = udm.liuyao_chart
    judgments.append(f'【六爻】本卦：{ly["ben_gua"]["name"]}，动爻：第{ly["dong_yao"]}爻')

# 奇门判断
if udm.qimen_chart:
    qm = udm.qimen_chart
    ju = qm['ju_name']
    men = qm.get('ba_men', {})
    # 找开门、生门位置
    kai = [g for g, m in men.items() if m == '开门']
    sheng = [g for g, m in men.items() if m == '生门']
    men_str = ''
    if kai:
        men_str += f'开门在{kai[0]} '
    if sheng:
        men_str += f'生门在{sheng[0]}'
    judgments.append(f'【奇门】{ju}')
    if men_str:
        judgments.append(f'       {men_str}')

# 大六壬判断
if udm.liuren_chart:
    lr = udm.liuren_chart
    judgments.append(f'【大六壬】月将：{lr["yue_jiang"]}')

# 太乙判断
if udm.taiyi_chart:
    ty = udm.taiyi_chart
    judgments.append(f'【太乙】{ty["taiyi_gong"]}，积年{ty["ji_nian"]}')

for j in judgments:
    print(j)

print()
print('【综合解读】')
# 基于多术交叉生成综合解读
interpretations = []
if udm.bazi_year:
    dm = udm.day_master
    wx = udm.day_master_wuxing
    features = udm.features
    interpretations.append(f'命格以{dm}（{wx}）为日主')
    if any('冲' in f for f in features):
        interpretations.append('命局带冲，一生多变动')
    if any('七杀' in f or '偏官' in f for f in features):
        interpretations.append('七杀透干，性格刚强有魄力')

if udm.ziwei_chart:
    ming = udm.ziwei_chart['ming_gong']
    stars = udm.ziwei_chart.get('star_placements', {})
    ming_stars = [s for s, p in stars.items() if p == '命宫']
    if ming_stars:
        interpretations.append(f'紫微命宫在{ming}，主星{"、".join(ming_stars[:2])}，格局已定')

if udm.astro_chart:
    sun = udm.astro_chart['sun_sign']
    moon = udm.astro_chart['moon_sign']
    interpretations.append(f'占星太阳{sun}思维灵活，月亮{moon}情感细腻')

if interpretations:
    print('。'.join(interpretations) + '。')

# 事业建议
if udm.qimen_chart:
    men = udm.qimen_chart.get('ba_men', {})
    kai = [g for g, m in men.items() if m == '开门']
    if kai:
        print(f'奇门显示开门在{kai[0]}，事业方向已明。')

# 感情提示
if udm.bazi_year:
    chong = udm.get_chong()
    if any('子午' in c or '午子' in c for c in chong):
        print('八字午子冲，感情需多注意沟通。')

print()

# 交叉验证
print('='*60)
print('【七术交叉验证】')
validator = CrossValidator(udm)
v = validator.validate()
print(f'参与术法：{len(v["available_methods"])}术')
print(f'综合置信度：{v["overall_confidence"].value}')
print()
print('共识：')
for c in v['consensus']:
    methods = '/'.join(c.supporting_methods)
    print(f'  [{c.aspect}] {c.finding}（{methods}）')
if v['conflicts']:
    print('冲突：')
    for c in v['conflicts']:
        print(f'  [{c.aspect}] {c.method_a} vs {c.method_b}')
print()

# 视角辩论
print('='*60)
print('【12人物视角辩论】')
pe = PerspectiveEngine()
opinions = pe.analyze(udm, '此人事业如何？')
for o in opinions:
    print(f'{o.figure_name}（{o.primary_method}）：{o.stance}')
print()

# 辩论
print('='*60)
print('【交锋辩论】')
de = DebateEngine()
debate_result = de.debate(opinions, '此人事业如何？')
for e in debate_result['exchanges'][:4]:
    print(f'{e.speaker}（{e.speaker_method}）-> {e.target}（{e.target_method}）：{e.argument}')
print()
print(f'总结：{debate_result["summary"]}')
