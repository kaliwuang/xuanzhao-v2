#!/usr/bin/env python3
from engine.time_engine import get_time_engine
from engine.bazi_engine import BaziEngine

te = get_time_engine()
ct = te.correct("2005-06-09 11:50", "呼和浩特")

be = BaziEngine()
data = be.analyze(ct, 1)

print("=== 八字排盘结果 ===")
yr = data["year"]
mo = data["month"]
dy = data["day"]
tm = data["time"]
print("年柱:", yr.gan + yr.zhi)
print("月柱:", mo.gan + mo.zhi)
print("日柱:", dy.gan + dy.zhi)
print("时柱:", tm.gan + tm.zhi)
print("日主:", data["day_master"])

ts = ct.true_solar
print("\n=== 真太阳时信息 ===")
print("原始时间: 11:50")
print("真太阳时:", str(ts.hour) + ":" + str(ts.minute).zfill(2))
print("时支:", ct.hour_zhi)
print("经度:", ct.longitude)
print("经度修正:", round((ct.longitude - 120.0) * 4.0, 1), "分钟")
print("是否晚子时:", ct.is_late_zi)
