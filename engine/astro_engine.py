"""占星引擎 - Astrology Engine using pyswisseph."""

import swisseph as swe
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from .base import DivinationEngine, CorrectedTime

logger = logging.getLogger(__name__)


SIGN_NAMES = ['白羊','金牛','双子','巨蟹','狮子','处女','天秤','天蝎','射手','摩羯','水瓶','双鱼']
SIGN_ELEMENTS = {
    '白羊':'火','狮子':'火','射手':'火',
    '金牛':'土','处女':'土','摩羯':'土',
    '双子':'风','天秤':'风','水瓶':'风',
    '巨蟹':'水','天蝎':'水','双鱼':'水',
}

PLANETS = {
    '太阳': swe.SUN, '月亮': swe.MOON, '水星': swe.MERCURY,
    '金星': swe.VENUS, '火星': swe.MARS, '木星': swe.JUPITER,
    '土星': swe.SATURN, '天王星': swe.URANUS, '海王星': swe.NEPTUNE,
    '冥王星': swe.PLUTO,
}

ASPECT_DEFS = [
    ('合相', 0, 8), ('六合', 60, 4), ('刑', 90, 6),
    ('三合', 120, 6), ('冲', 180, 8),
]

# Essential dignities (入庙/旺/陷/弱)
# Domicile (入庙): planet rules the sign
DOMICILE = {
    '太阳': '狮子', '月亮': '巨蟹',
    '水星': ['双子', '处女'], '金星': ['金牛', '天秤'],
    '火星': ['白羊', '天蝎'], '木星': ['射手', '双鱼'],
    '土星': ['摩羯', '水瓶'],
    '天王星': ['水瓶'], '海王星': ['双鱼'], '冥王星': ['天蝎'],
}
# Exaltation (旺)
EXALTATION = {
    '太阳': '白羊', '月亮': '金牛', '水星': '处女', '金星': '双鱼',
    '火星': '摩羯', '木星': '巨蟹', '土星': '天秤',
}
# Detriment (陷): opposite signs of domicile
DETRIMENT = {
    '太阳': '水瓶', '月亮': '摩羯',
    '水星': ['射手', '双鱼'], '金星': ['白羊', '天蝎'],
    '火星': ['天秤', '金牛'], '木星': ['双子', '处女'],
    '土星': ['巨蟹', '狮子'],
    '天王星': '狮子', '海王星': '处女', '冥王星': '金牛',
}
# Fall (弱): opposite signs of exaltation
FALL = {
    '太阳': '天秤', '月亮': '天蝎', '水星': '双鱼', '金星': '处女',
    '火星': '巨蟹', '木星': '摩羯', '土星': '白羊',
}


def _essential_dignity(planet_name: str, sign: str) -> str:
    """Compute essential dignity for a planet in a given sign."""
    if not planet_name or not sign:
        return ''
    # Check domicile
    dom = DOMICILE.get(planet_name, [])
    if isinstance(dom, str):
        dom = [dom]
    if sign in dom:
        return 'domicile'
    # Check exaltation
    exalt = EXALTATION.get(planet_name, '')
    if sign == exalt:
        return 'exaltation'
    # Check detriment
    detr = DETRIMENT.get(planet_name, [])
    if isinstance(detr, str):
        detr = [detr]
    if sign in detr:
        return 'detriment'
    # Check fall
    fall = FALL.get(planet_name, '')
    if sign == fall:
        return 'fall'
    return ''


def _jd(dt: datetime) -> float:
    """Convert a datetime to Julian Day (UT).

    Args:
        dt: datetime object. Aware datetimes are auto-converted to UTC.
            Naive datetimes are ASSUMED to already be in UTC.

    Returns:
        Julian Day number in UT.
    """
    if dt.tzinfo is not None:
        utc_dt = dt.astimezone(timezone.utc)
    else:
        utc_dt = dt
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day,
                      utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0)


def _sign_degree(longitude: float) -> tuple[str, float, int]:
    """Return (sign_name, degree_in_sign, sign_index)."""
    longitude = longitude % 360.0
    idx = int(longitude / 30)
    deg = longitude - idx * 30
    return SIGN_NAMES[idx], deg, idx


def _find_house(lon: float, cusps: list[float]) -> int:
    """Find which house a given longitude falls in. Returns 1-12."""
    for i in range(12):
        start = cusps[i]
        end = cusps[(i + 1) % 12]
        if start == end:
            continue  # 两宫首重叠（极端情况），跳过避免误分配
        if start < end:
            if start <= lon < end:
                return i + 1
        else:  # wraps around 360
            if lon >= start or lon < end:
                return i + 1
    # 回退：找到最近的宫首
    min_dist = 360.0
    closest = 12
    for i in range(12):
        dist = abs(lon - cusps[i])
        if dist > 180:
            dist = 360 - dist
        if dist < min_dist:
            min_dist = dist
            closest = i + 1
    return closest


class AstroEngine(DivinationEngine):

    @property
    def name(self) -> str:
        return '占星'

    @property
    def name_en(self) -> str:
        return 'astro'

    @property
    def priority(self) -> int:
        return 3

    def __init__(self):
        import os
        ephe_path = os.environ.get('SWISS_EPHE_PATH', os.path.expanduser('~/.ephe'))
        swe.set_ephe_path(ephe_path)

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        # 直接使用已校正的UTC时间，避免从真太阳时逆推引入均时差误差
        utc_dt = time.utc

        jd_utc = _jd(utc_dt)

        lat = time.latitude
        lon = time.longitude

        # Calculate houses using UT (swe.houses takes UT + lon separately)
        cusps, ascmc = swe.houses(jd_utc, lat, lon, b'P')
        # cusps: 12 cusps (index 0=ASC=1st, 1=2nd, ..., 11=12th)
        # ascmc[0]=ASC, ascmc[1]=MC

        # Build house data
        houses = []
        for i in range(12):
            sign, degree, sign_idx = _sign_degree(cusps[i])
            houses.append({
                'house': i + 1,
                'cusp_longitude': round(cusps[i], 4),
                'sign': sign,
                'sign_index': sign_idx,
                'degree': round(degree, 2),
            })

        # Calculate planet positions (UTC-based)
        planets = {}
        for pname, pid in PLANETS.items():
            try:
                # calc_ut returns (longitude, latitude, distance, speed_lon, ...)
                result = swe.calc_ut(jd_utc, pid)
                plon = result[0][0] if isinstance(result[0], (list, tuple)) else result[0]
                plon = plon % 360.0
                sign, degree, sign_idx = _sign_degree(plon)
                house = _find_house(plon, list(cusps))
                planets[pname] = {
                    'longitude': round(plon, 4),
                    'sign': sign,
                    'sign_index': sign_idx,
                    'degree': round(degree, 2),
                    'house': house,
                    'speed': round(result[0][3], 4) if isinstance(result[0], (list, tuple)) and len(result[0]) > 3 else 0,
                    'retrograde': (isinstance(result[0], (list, tuple)) and len(result[0]) > 3 and result[0][3] < 0),
                    'dignity': _essential_dignity(pname, sign),
                }
            except Exception as e:
                logger.warning(f"占星：{pname}位置计算异常，跳过: {e}")
                planets[pname] = {
                    'longitude': 0, 'sign': '', 'sign_index': 0,
                    'degree': 0, 'house': 0, 'speed': 0, 'retrograde': False,
                    'dignity': '',
                    'error': str(e),
                }

        # Sun/Moon signs and elements
        sun_sign = planets['太阳']['sign']
        moon_sign = planets['月亮']['sign']
        sun_element = SIGN_ELEMENTS.get(sun_sign, '')
        moon_element = SIGN_ELEMENTS.get(moon_sign, '')

        # ASC and MC
        asc_sign, asc_deg, _ = _sign_degree(ascmc[0])
        mc_sign, mc_deg, _ = _sign_degree(ascmc[1])

        # Calculate aspects between planets
        aspects = []
        planet_names = list(planets.keys())
        for i in range(len(planet_names)):
            for j in range(i + 1, len(planet_names)):
                p1, p2 = planet_names[i], planet_names[j]
                lon1 = planets[p1]['longitude']
                lon2 = planets[p2]['longitude']
                diff = abs(lon1 - lon2)
                if diff > 180:
                    diff = 360 - diff
                for aspect_name, aspect_angle, orb_limit in ASPECT_DEFS:
                    orb = abs(diff - aspect_angle)
                    if orb <= orb_limit:
                        aspects.append({
                            'planet1': p1,
                            'planet2': p2,
                            'aspect': aspect_name,
                            'angle': aspect_angle,
                            'orb': round(orb, 2),
                            'house1': planets[p1]['house'],
                            'house2': planets[p2]['house'],
                            'sign1': planets[p1]['sign'],
                            'sign2': planets[p2]['sign'],
                        })
                        break

        # 宫主星计算
        house_rulers = {}
        ruler_map = {
            '白羊': '火星', '金牛': '金星', '双子': '水星', '巨蟹': '月亮',
            '狮子': '太阳', '处女': '水星', '天秤': '金星', '天蝎': '冥王星',
            '射手': '木星', '摩羯': '土星', '水瓶': '天王星', '双鱼': '海王星'
        }
        # Traditional rulership (used alongside modern)
        traditional_ruler_map = {
            '白羊': '火星', '金牛': '金星', '双子': '水星', '巨蟹': '月亮',
            '狮子': '太阳', '处女': '水星', '天秤': '金星', '天蝎': '火星',
            '射手': '木星', '摩羯': '土星', '水瓶': '土星', '双鱼': '木星'
        }
        for h in houses:
            sign = h.get('sign', '')
            house_num = h.get('house', 0)
            ruler = ruler_map.get(sign, '')
            trad_ruler = traditional_ruler_map.get(sign, '')
            if ruler:
                house_rulers[house_num] = {'sign': sign, 'ruler': ruler, 'traditional_ruler': trad_ruler}

        # North/South Node (Lunar Nodes)
        try:
            rahu_result = swe.calc_ut(jd_utc, swe.TRUE_NODE)
            rahu_lon = rahu_result[0][0] if isinstance(rahu_result[0], (list, tuple)) else rahu_result[0]
            rahu_lon = rahu_lon % 360.0
            ketu_lon = (rahu_lon + 180) % 360
            rahu_sign, rahu_deg, _ = _sign_degree(rahu_lon)
            ketu_sign, ketu_deg, _ = _sign_degree(ketu_lon)
            north_node = {'longitude': round(rahu_lon, 4), 'sign': rahu_sign, 'degree': round(rahu_deg, 2), 'house': _find_house(rahu_lon, list(cusps))}
            south_node = {'longitude': round(ketu_lon, 4), 'sign': ketu_sign, 'degree': round(ketu_deg, 2), 'house': _find_house(ketu_lon, list(cusps))}
        except Exception as e:
            logger.debug(f"月交点计算异常: {e}")
            north_node = {}
            south_node = {}

        return {
            'engine': self.name,
            'engine_en': self.name_en,
            'sun_sign': sun_sign,
            'sun_element': sun_element,
            'moon_sign': moon_sign,
            'moon_element': moon_element,
            'ascendant': round(ascmc[0], 4),
            'ascendant_sign': asc_sign,
            'ascendant_degree': round(asc_deg, 2),
            'mc': round(ascmc[1], 4),
            'mc_sign': mc_sign,
            'mc_degree': round(mc_deg, 2),
            'houses': houses,
            'planets': planets,
            'aspects': aspects,
            'aspects_summary': self._build_aspects_summary(aspects),
            'house_rulers': house_rulers,
            'house_system': 'Placidus',
            'gender': '男' if gender == 1 else '女',
            'birth_time': str(time.original),
            'location': time.location_name,
            'north_node': north_node,
            'south_node': south_node,
            'planetary_details': {name: {'retrograde': p.get('retrograde', False), 'speed': p.get('speed', 0), 'dignity': p.get('dignity', '')} for name, p in planets.items()},
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        # Check for engine errors first
        if data.get('error'):
            return False, data['error']
        # Check that key astrology fields are present
        required_fields = ['sun_sign', 'moon_sign', 'planets']
        for field in required_fields:
            if field not in data:
                return False, f'Missing required field: {field}'
        if not data.get('planets'):
            return False, 'No planet data calculated'
        return True, None

    def _build_aspects_summary(self, aspects: list) -> dict:
        """构建相位摘要统计"""
        summary = {
            'total': len(aspects),
            'harmonious': 0,  # 合相+六合+三合
            'challenging': 0,  # 刑+冲
            'by_type': {},
        }
        for asp in aspects:
            name = asp.get('aspect', '')
            summary['by_type'][name] = summary['by_type'].get(name, 0) + 1
            if name in ('合相', '六合', '三合'):
                summary['harmonious'] += 1
            elif name in ('刑', '冲'):
                summary['challenging'] += 1
        return summary
