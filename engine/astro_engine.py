#!/usr/bin/env python3
"""
玄照 v2.0 - 西洋占星引擎

基于 pyswisseph，封装星座、宫位、相位计算。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional


class AstroEngine(DivinationEngine):
    """西洋占星引擎"""

    @property
    def name(self) -> str:
        return "占星"

    @property
    def name_en(self) -> str:
        return "Astrology"

    @property
    def priority(self) -> int:
        return 7  # 占星优先级最低

    def __init__(self):
        self.signs = [
            '白羊', '金牛', '双子', '巨蟹', '狮子', '处女',
            '天秤', '天蝎', '射手', '摩羯', '水瓶', '双鱼'
        ]

        self.elements = {
            '白羊': '火', '狮子': '火', '射手': '火',
            '金牛': '土', '处女': '土', '摩羯': '土',
            '双子': '风', '天秤': '风', '水瓶': '风',
            '巨蟹': '水', '天蝎': '水', '双鱼': '水',
        }

    def _get_swe(self):
        """动态导入 swisseph"""
        try:
            import swisseph as swe
            return swe
        except Exception as e:
            return {"error": str(e)}

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        swe = self._get_swe()
        if isinstance(swe, dict) and "error" in swe:
            return {"error": f"pyswisseph import failed: {swe['error']}"}
        if swe is None:
            return {"error": "pyswisseph not installed"}

        # 占星排盘用 UTC（pyswisseph 需要 UT）
        dt = time.utc
        lat = time.latitude
        lon = time.longitude

        # Julian Day (UT)
        jd = swe.julday(dt.year, dt.month, dt.day,
                             dt.hour + dt.minute / 60.0)

        # 行星位置
        planets = {}
        planet_ids = [
            (swe.SUN, '太阳'),
            (swe.MOON, '月亮'),
            (swe.MERCURY, '水星'),
            (swe.VENUS, '金星'),
            (swe.MARS, '火星'),
            (swe.JUPITER, '木星'),
            (swe.SATURN, '土星'),
            (swe.URANUS, '天王星'),
            (swe.NEPTUNE, '海王星'),
            (swe.PLUTO, '冥王星'),
        ]

        for pid, pname in planet_ids:
            try:
                pos = swe.calc_ut(jd, pid)
                lon_deg = pos[0][0]
                sign_idx = int(lon_deg / 30) % 12
                planets[pname] = {
                    "longitude": round(lon_deg, 2),
                    "sign": self.signs[sign_idx],
                    "element": self.elements[self.signs[sign_idx]],
                    "degree": round(lon_deg % 30, 2),
                }
            except Exception:
                planets[pname] = {"error": "calculation failed"}

        # 宫位（Placidus 分宫制）
        houses = {}
        try:
            cusps, ascmc = swe.houses(jd, lat, lon, b'P')
            ascendant = cusps[0]
            mc = ascmc[1]

            for i in range(12):
                lon_deg = cusps[i]
                sign_idx = int(lon_deg / 30) % 12
                houses[f"house_{i+1}"] = {
                    "cusp": round(lon_deg, 2),
                    "sign": self.signs[sign_idx],
                    "element": self.elements[self.signs[sign_idx]],
                }
        except Exception:
            ascendant = 0
            mc = 0

        # 上升星座
        asc_sign = ""
        if ascendant:
            asc_sign = self.signs[int(ascendant / 30) % 12]

        # 太阳星座
        sun_sign = planets.get('太阳', {}).get('sign', '')
        moon_sign = planets.get('月亮', {}).get('sign', '')

        # 主要相位
        aspects = self._calc_aspects(planets)

        return {
            "planets": planets,
            "ascendant": round(ascendant, 2) if ascendant else 0,
            "ascendant_sign": asc_sign,
            "mc": round(mc, 2) if mc else 0,
            "houses": houses,
            "sun_sign": sun_sign,
            "moon_sign": moon_sign,
            "sun_element": self.elements.get(sun_sign, ""),
            "moon_element": self.elements.get(moon_sign, ""),
            "aspects": aspects,
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if "error" in data:
            return False, data["error"]
        if not data.get("sun_sign"):
            return False, "太阳星座为空"
        return True, None

    def _calc_aspects(self, planets: dict) -> list:
        """计算主要相位"""
        aspects = []
        aspect_angles = {
            "合相": 0,
            "六分": 60,
            "四分": 90,
            "三分": 120,
            "对冲": 180,
        }

        names = list(planets.keys())
        for i, n1 in enumerate(names):
            p1 = planets[n1]
            if "longitude" not in p1:
                continue
            for n2 in names[i+1:]:
                p2 = planets[n2]
                if "longitude" not in p2:
                    continue

                diff = abs(p1["longitude"] - p2["longitude"])
                if diff > 180:
                    diff = 360 - diff

                for aspect_name, angle in aspect_angles.items():
                    if abs(diff - angle) <= 8:  # 容许度8度
                        aspects.append({
                            "p1": n1,
                            "p2": n2,
                            "aspect": aspect_name,
                            "angle": round(diff, 1),
                            "orb": round(abs(diff - angle), 1),
                        })

        return aspects
