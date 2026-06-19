#!/usr/bin/env python3
"""全面验证所有引擎"""
from engine.time_engine import get_time_engine

te = get_time_engine()
ct = te.correct("2005-06-09 11:50", "呼和浩特")

# 测试八字引擎
try:
    from engine.bazi_engine import BaziEngine
    be = BaziEngine()
    data = be.analyze(ct, 1)
    year = data["year"]
    month = data["month"]
    day = data["day"]
    time_p = data["time"]
    print("OK 八字:", year.gan+year.zhi, month.gan+month.zhi, day.gan+day.zhi, time_p.gan+time_p.zhi)
except Exception as e:
    print("ERR 八字:", e)

# 测试紫微引擎
try:
    from engine.ziwei_engine import ZiWeiEngine
    ze = ZiWeiEngine()
    data = ze.analyze(ct, 1)
    if "error" in data:
        print("ERR 紫微:", data["error"])
    else:
        print("OK 紫微: palaces=", len(data.get("palaces", [])))
except Exception as e:
    print("ERR 紫微:", e)

# 测试占星引擎
try:
    from engine.astro_engine import AstroEngine
    ae = AstroEngine()
    data = ae.analyze(ct, 1)
    if "error" in data:
        print("ERR 占星:", data["error"])
    else:
        print("OK 占星: sun=", data.get("sun_sign", ""))
except Exception as e:
    print("ERR 占星:", e)

# 测试六爻引擎
try:
    from engine.liuyao_engine import LiuYaoEngine
    le = LiuYaoEngine()
    data = le.analyze(ct, 1)
    if "error" in data:
        print("ERR 六爻:", data["error"])
    else:
        print("OK 六爻: ben_gua=", data.get("ben_gua", {}).get("name", ""))
except Exception as e:
    print("ERR 六爻:", e)

# 测试奇门引擎
try:
    from engine.qimen_engine import QiMenEngine
    qe = QiMenEngine()
    data = qe.analyze(ct, 1)
    if "error" in data:
        print("ERR 奇门:", data["error"])
    else:
        print("OK 奇门: ju=", data.get("ju_shu", ""))
except Exception as e:
    print("ERR 奇门:", e)

# 测试大六壬引擎
try:
    from engine.liuren_engine import LiuRenEngine
    lr = LiuRenEngine()
    data = lr.analyze(ct, 1)
    if "error" in data:
        print("ERR 六壬:", data["error"])
    else:
        print("OK 六壬: yue_jiang=", data.get("yue_jiang", ""))
except Exception as e:
    print("ERR 六壬:", e)

# 测试太乙引擎
try:
    from engine.taiyi_engine import TaiYiEngine
    ty = TaiYiEngine()
    data = ty.analyze(ct, 1)
    if "error" in data:
        print("ERR 太乙:", data["error"])
    else:
        print("OK 太乙: yin_yang=", data.get("yin_yang", ""))
except Exception as e:
    print("ERR 太乙:", e)

# 测试姓名学引擎
try:
    from engine.xingming_engine import XingMingEngine
    xe = XingMingEngine()
    data = xe.analyze_name("侯", "惠斌", "男")
    if "error" in data:
        print("ERR 姓名:", data["error"])
    else:
        print("OK 姓名: wuge=", data.get("wuge", {}).get("天格", {}).get("画数", ""))
except Exception as e:
    print("ERR 姓名:", e)
