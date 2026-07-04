"""占星引擎 - Astrology Engine using pyswisseph."""

import swisseph as swe
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from .base import DivinationEngine, CorrectedTime

logger = logging.getLogger(__name__)

# 行星落座解释表
PLANET_SIGN_INTERPS = {
    '太阳': {
        '白羊': '自我意识强，积极主动，富有开拓精神',
        '金牛': '稳重踏实，注重物质享受，有耐心',
        '双子': '思维活跃，善于沟通，兴趣广泛',
        '巨蟹': '情感丰富，重视家庭，有保护欲',
        '狮子': '自信大方，有领导力，喜欢被关注',
        '处女': '细心谨慎，追求完美，注重细节',
        '天秤': '追求和谐，善于社交，有艺术天赋',
        '天蝎': '意志坚定，洞察力强，情感深沉',
        '射手': '乐观开朗，热爱自由，追求真理',
        '摩羯': '踏实稳重，有责任感，目标明确',
        '水瓶': '独立创新，思想前卫，重视友情',
        '双鱼': '敏感多情，富有同情心，想象力丰富',
    },
    '月亮': {
        '白羊': '情绪直接，行动力强，容易冲动',
        '金牛': '情感稳定，追求安全感，喜欢舒适',
        '双子': '情绪多变，好奇心强，善于表达',
        '巨蟹': '情感细腻，重视家庭，有母性光辉',
        '狮子': '情感热烈，喜欢被认可，有表演欲',
        '处女': '情感内敛，注重细节，有服务精神',
        '天秤': '追求平衡，善于协调，重视关系',
        '天蝎': '情感深沉，直觉敏锐，有占有欲',
        '射手': '情感乐观，热爱自由，喜欢探索',
        '摩羯': '情感克制，有责任感，重视传统',
        '水瓶': '情感独立，思想理性，重视友情',
        '双鱼': '情感敏感，富有同情心，容易受影响',
    },
    '水星': {
        '白羊': '思维敏捷，表达直接，喜欢争论',
        '金牛': '思维稳重，注重实际，有耐心',
        '双子': '思维活跃，善于沟通，兴趣广泛',
        '巨蟹': '思维感性，重视情感，有想象力',
        '狮子': '思维自信，有表现欲，喜欢被认可',
        '处女': '思维细致，追求完美，善于分析',
        '天秤': '思维平衡，善于协调，有艺术感',
        '天蝎': '思维深刻，洞察力强，有研究精神',
        '射手': '思维开阔，热爱自由，有哲学倾向',
        '摩羯': '思维务实，有责任感，目标明确',
        '水瓶': '思维独立，有创新精神，重视友情',
        '双鱼': '思维敏感，有同情心，想象力丰富',
    },
    '金星': {
        '白羊': '爱情直接，有征服欲，热情主动',
        '金牛': '爱情稳定，注重物质，有占有欲',
        '双子': '爱情多变，喜欢新鲜，善于沟通',
        '巨蟹': '爱情细腻，重视家庭，有保护欲',
        '狮子': '爱情热烈，喜欢被崇拜，有表现欲',
        '处女': '爱情谨慎，注重细节，有服务精神',
        '天秤': '爱情和谐，追求平衡，有艺术天赋',
        '天蝎': '爱情深沉，有占有欲，情感强烈',
        '射手': '爱情自由，热爱冒险，有探索精神',
        '摩羯': '爱情务实，有责任感，重视传统',
        '水瓶': '爱情独立，有创新精神，重视友情',
        '双鱼': '爱情浪漫，有同情心，容易受影响',
    },
    '火星': {
        '白羊': '行动力强，有开拓精神，容易冲动',
        '金牛': '行动稳重，有耐心，但可能固执',
        '双子': '行动多变，善于沟通，但可能分散',
        '巨蟹': '行动谨慎，重视情感，有保护欲',
        '狮子': '行动自信，有领导力，喜欢表现',
        '处女': '行动细致，追求完美，善于分析',
        '天秤': '行动平衡，善于协调，有艺术感',
        '天蝎': '行动果断，有洞察力，意志坚定',
        '射手': '行动自由，热爱冒险，有探索精神',
        '摩羯': '行动务实，有责任感，目标明确',
        '水瓶': '行动独立，有创新精神，重视友情',
        '双鱼': '行动敏感，有同情心，容易受影响',
    },
    '木星': {
        '白羊': '扩展积极，有开拓精神，乐观向上',
        '金牛': '扩展稳定，注重物质，有耐心',
        '双子': '扩展多变，善于沟通，兴趣广泛',
        '巨蟹': '扩展细腻，重视情感，有保护欲',
        '狮子': '扩展自信，有领导力，喜欢表现',
        '处女': '扩展细致，追求完美，善于分析',
        '天秤': '扩展平衡，善于协调，有艺术感',
        '天蝎': '扩展深刻，有洞察力，意志坚定',
        '射手': '扩展自由，热爱冒险，有探索精神',
        '摩羯': '扩展务实，有责任感，目标明确',
        '水瓶': '扩展独立，有创新精神，重视友情',
        '双鱼': '扩展敏感，有同情心，想象力丰富',
    },
    '土星': {
        '白羊': '限制冲动，培养耐心，有挑战',
        '金牛': '限制物质，培养稳重，有压力',
        '双子': '限制沟通，培养专注，有困难',
        '巨蟹': '限制情感，培养独立，有考验',
        '狮子': '限制表现，培养谦逊，有挑战',
        '处女': '限制细节，培养大局，有压力',
        '天秤': '限制关系，培养独立，有困难',
        '天蝎': '限制情感，培养开放，有考验',
        '射手': '限制自由，培养责任，有挑战',
        '摩羯': '限制传统，培养创新，有压力',
        '水瓶': '限制独立，培养合作，有困难',
        '双鱼': '限制敏感，培养现实，有考验',
    },
    '天王星': {
        '白羊': '创新积极，有开拓精神，变革传统',
        '金牛': '创新稳定，注重物质，有耐心',
        '双子': '创新多变，善于沟通，兴趣广泛',
        '巨蟹': '创新细腻，重视情感，有保护欲',
        '狮子': '创新自信，有领导力，喜欢表现',
        '处女': '创新细致，追求完美，善于分析',
        '天秤': '创新平衡，善于协调，有艺术感',
        '天蝎': '创新深刻，有洞察力，意志坚定',
        '射手': '创新自由，热爱冒险，有探索精神',
        '摩羯': '创新务实，有责任感，目标明确',
        '水瓶': '创新独立，有创新精神，重视友情',
        '双鱼': '创新敏感，有同情心，想象力丰富',
    },
    '海王星': {
        '白羊': '灵性积极，有开拓精神，有直觉力',
        '金牛': '灵性稳定，注重物质，有耐心',
        '双子': '灵性多变，善于沟通，兴趣广泛',
        '巨蟹': '灵性细腻，重视情感，有保护欲',
        '狮子': '灵性自信，有领导力，喜欢表现',
        '处女': '灵性细致，追求完美，善于分析',
        '天秤': '灵性平衡，善于协调，有艺术感',
        '天蝎': '灵性深刻，有洞察力，意志坚定',
        '射手': '灵性自由，热爱冒险，有探索精神',
        '摩羯': '灵性务实，有责任感，目标明确',
        '水瓶': '灵性独立，有创新精神，重视友情',
        '双鱼': '灵性敏感，有同情心，想象力丰富',
    },
    '冥王星': {
        '白羊': '转化积极，有开拓精神，有重生力',
        '金牛': '转化稳定，注重物质，有耐心',
        '双子': '转化多变，善于沟通，兴趣广泛',
        '巨蟹': '转化细腻，重视情感，有保护欲',
        '狮子': '转化自信，有领导力，喜欢表现',
        '处女': '转化细致，追求完美，善于分析',
        '天秤': '转化平衡，善于协调，有艺术感',
        '天蝎': '转化深刻，有洞察力，意志坚定',
        '射手': '转化自由，热爱冒险，有探索精神',
        '摩羯': '转化务实，有责任感，目标明确',
        '水瓶': '转化独立，有创新精神，重视友情',
        '双鱼': '转化敏感，有同情心，想象力丰富',
    },
}

# 相位解释表
ASPECT_INTERPS = {
    '合相': {'nature': '融合', 'desc': '两颗行星能量融合，增强彼此影响力'},
    '六合': {'nature': '和谐', 'desc': '带来机会和轻松的能量流动'},
    '刑': {'nature': '挑战', 'desc': '带来压力和成长的机会'},
    '三合': {'nature': '和谐', 'desc': '带来天赋和顺利的能量'},
    '冲': {'nature': '对立', 'desc': '带来紧张和需要平衡的能量'},
}

# 宫位解释表
HOUSE_INTERPS = {
    1: '自我、外貌、第一印象',
    2: '财富、价值观、物质资源',
    3: '沟通、学习、兄弟姐妹',
    4: '家庭、根基、内心安全',
    5: '创造、爱情、子女',
    6: '健康、工作、日常事务',
    7: '婚姻、合作、公开的敌人',
    8: '死亡、重生、他人资源',
    9: '哲学、旅行、高等教育',
    10: '事业、名声、社会地位',
    11: '朋友、愿望、社会团体',
    12: '潜意识、秘密、隐藏的敌人',
}

# 元素分布解释
ELEMENT_INTERPS = {
    '火': {'trait': '热情、行动力强、有领导力', 'lack': '缺乏激情、行动力不足'},
    '土': {'trait': '踏实、稳重、有耐心', 'lack': '缺乏实际性、不够踏实'},
    '风': {'trait': '善于沟通、思维活跃、社交能力强', 'lack': '缺乏理性、沟通能力弱'},
    '水': {'trait': '情感丰富、直觉敏锐、有同情心', 'lack': '缺乏情感、直觉迟钝'},
}

# 模式分布解释
MODALITY_INTERPS = {
    '开创': {'trait': '有开创力、主动性强、有领导力', 'lack': '缺乏主动性、不够积极'},
    '固定': {'trait': '有耐心、意志坚定、稳定', 'lack': '缺乏灵活性、固执'},
    '变动': {'trait': '适应力强、灵活多变、善于沟通', 'lack': '缺乏稳定性、善变'},
}


SIGN_NAMES = ['白羊','金牛','双子','巨蟹','狮子','处女','天秤','天蝎','射手','摩羯','水瓶','双鱼']
SIGN_ELEMENTS = {
    '白羊':'火','狮子':'火','射手':'火',
    '金牛':'土','处女':'土','摩羯':'土',
    '双子':'风','天秤':'风','水瓶':'风',
    '巨蟹':'水','天蝎':'水','双鱼':'水',
}
# B18 修复: 月相计算
# 8 个主要月相: 新月、上弦月、满月、下弦月
# 影响情绪和直觉


PLANETS = {
    '太阳': swe.SUN, '月亮': swe.MOON, '水星': swe.MERCURY,
    '金星': swe.VENUS, '火星': swe.MARS, '木星': swe.JUPITER,
    '土星': swe.SATURN, '天王星': swe.URANUS, '海王星': swe.NEPTUNE,
    '冥王星': swe.PLUTO,
}

# B19 修复: 推运 (次限/三限) 算法
# 次限推运: 出生后 N 天 = 出生后 N 年
# 三限推运: 出生后 N 天 = 出生后 N 月
# 用于精确预测流年运势
ASPECT_DEFS = [
    ('合相', 0, 8), ('六合', 60, 4), ('刑', 90, 6),
    ('三合', 120, 6), ('冲', 180, 8),
]

# B20 修复: 行星个性化容许度
# 太阳/月亮的容许度最大 (光线强,影响大)
# 水星容许度小 (离太阳最近,影响范围小)
# 外行星 (天王星/海王星/冥王星) 容许度大 (运行慢,影响持续)
PLANET_ORB_MODIFIER = {
    '太阳': 1.0, '月亮': 1.0, '水星': 0.5, '金星': 0.8,
    '火星': 0.8, '木星': 1.0, '土星': 1.0,
    '天王星': 1.2, '海王星': 1.2, '冥王星': 1.2,
}
# B16 修复: 水星逆行标记
# 水星逆行时, 沟通/思维受影响, 占星判断需注意
# 水星每 3-4 个月逆行一次, 每次约 3 周


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
    # 模式映射
    SIGN_MODALITY = {
        '白羊': '开创', '金牛': '固定', '双子': '变动', '巨蟹': '开创',
        '狮子': '固定', '处女': '变动', '天秤': '开创', '天蝎': '固定',
        '射手': '变动', '摩羯': '开创', '水瓶': '固定', '双鱼': '变动',
    }


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

        # 元素分布分析
        element_dist = self._calc_element_distribution(planets)
        
        # 模式分布分析
        modality_dist = self._calc_modality_distribution(planets)
        
        # 行星落座解读
        planet_sign_interps = self._interpret_planet_signs(planets)
        
        # 相位详细解读
        aspect_interps = self._interpret_aspects(aspects)
        
        # 宫位行星分布解读
        house_planets = self._calc_house_planets(planets, houses)
        
        # 相位格局检测
        aspect_patterns = self._detect_aspect_patterns(aspects, planets)

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
            'element_distribution': element_dist,
            'modality_distribution': modality_dist,
            'planet_sign_interpretations': planet_sign_interps,
            'aspect_interpretations': aspect_interps,
            'house_planets': house_planets,
            'aspect_patterns': aspect_patterns,
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

    def _calc_element_distribution(self, planets: dict) -> dict:
        """计算行星元素分布"""
        dist = {'火': 0, '土': 0, '风': 0, '水': 0}
        for pname, pdata in planets.items():
            sign = pdata.get('sign', '')
            element = SIGN_ELEMENTS.get(sign, '')
            if element:
                dist[element] += 1
        return dist

    def _calc_modality_distribution(self, planets: dict) -> dict:
        """计算行星模式分布"""
        dist = {'开创': 0, '固定': 0, '变动': 0}
        for pname, pdata in planets.items():
            sign = pdata.get('sign', '')
            modality = self.SIGN_MODALITY.get(sign, '')
            if modality:
                dist[modality] += 1
        return dist

    def _interpret_planet_signs(self, planets: dict) -> dict:
        """解读行星落座"""
        interps = {}
        for pname, pdata in planets.items():
            sign = pdata.get('sign', '')
            if not sign:
                continue
            interp = PLANET_SIGN_INTERPS.get(pname, {}).get(sign, '')
            if interp:
                interps[pname] = {
                    'sign': sign,
                    'interpretation': interp,
                    'element': SIGN_ELEMENTS.get(sign, ''),
                    'modality': self.SIGN_MODALITY.get(sign, ''),
                }
        return interps

    def _interpret_aspects(self, aspects: list) -> list:
        """解读相位"""
        interps = []
        for asp in aspects:
            aspect_name = asp.get('aspect', '')
            interp_info = ASPECT_INTERPS.get(aspect_name, {})
            interps.append({
                'planet1': asp.get('planet1', ''),
                'planet2': asp.get('planet2', ''),
                'aspect': aspect_name,
                'nature': interp_info.get('nature', ''),
                'description': interp_info.get('desc', ''),
                'orb': asp.get('orb', 0),
                'strength': '强' if asp.get('orb', 0) < 3 else '中' if asp.get('orb', 0) < 6 else '弱',
            })
        return interps

    def _calc_house_planets(self, planets: dict, houses: list) -> dict:
        """计算每个宫位内的行星分布"""
        house_planets = {i: [] for i in range(1, 13)}
        for pname, pdata in planets.items():
            house = pdata.get('house', 0)
            if 1 <= house <= 12:
                house_planets[house].append(pname)
        return house_planets

    def _detect_aspect_patterns(self, aspects: list, planets: dict) -> dict:
        """检测相位格局（大三角、T型相位、大十字等）"""
        patterns = {
            'grand_trine': [],  # 大三角
            't_square': [],     # T型相位
            'grand_cross': [],  # 大十字
            'yod': [],          # 指针
        }
        
        # 简化检测：基于三合相位检测大三角
        trine_aspects = [a for a in aspects if a.get('aspect') == '三合']
        if len(trine_aspects) >= 3:
            patterns['grand_trine'].append({
                'description': '三颗行星形成大三角，天赋异禀，能量流畅',
                'planets': list(set([a['planet1'] for a in trine_aspects] + [a['planet2'] for a in trine_aspects])),
            })
        
        # 检测T型相位（两个刑相位+一个冲相位）
        square_aspects = [a for a in aspects if a.get('aspect') == '刑']
        opposition_aspects = [a for a in aspects if a.get('aspect') == '冲']
        if len(square_aspects) >= 2 and len(opposition_aspects) >= 1:
            patterns['t_square'].append({
                'description': 'T型相位带来挑战和成长机会',
                'planets': list(set([a['planet1'] for a in square_aspects] + [a['planet2'] for a in square_aspects])),
            })
        
        return patterns
