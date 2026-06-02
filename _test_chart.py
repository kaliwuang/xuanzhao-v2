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
