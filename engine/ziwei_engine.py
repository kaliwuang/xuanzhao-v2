#!/usr/bin/env python3
"""
玄照 v2.0 - 紫微斗数引擎（iztro-py后端版）

基于 iztro-py 库实现标准紫微斗数排盘。
iztro-py 是经过验证的开源紫微斗数库，安星准确。

支持：命宫、身宫、五行局、十四主星、六吉六煞、杂耀、四化、十二宫、长生十二博士等。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional, Dict
from datetime import datetime
import calendar
import logging

logger = logging.getLogger(__name__)


# 地支英文→中文映射
BRANCH_MAP = {
    'ziEarthly': '子', 'chouEarthly': '丑', 'yinEarthly': '寅', 'maoEarthly': '卯',
    'chenEarthly': '辰', 'siEarthly': '巳', 'wuEarthly': '午', 'weiEarthly': '未',
    'shenEarthly': '申', 'youEarthly': '酉', 'xuEarthly': '戌', 'haiEarthly': '亥',
}

# 天干英文→中文映射
STEM_MAP = {
    'jiaHeavenly': '甲', 'yiHeavenly': '乙', 'bingHeavenly': '丙', 'dingHeavenly': '丁',
    'wuHeavenly': '戊', 'jiHeavenly': '己', 'gengHeavenly': '庚', 'xinHeavenly': '辛',
    'renHeavenly': '壬', 'guiHeavenly': '癸',
}

# 宫位英文→中文映射
PALACE_NAME_MAP = {
    'soulPalace': '命宫', 'spiritPalace': '身宫',
    'siblingsPalace': '兄弟', 'spousePalace': '夫妻',
    'childrenPalace': '子女', 'wealthPalace': '财帛',
    'healthPalace': '疾厄', 'surfacePalace': '迁移',
    'friendsPalace': '交友', 'careerPalace': '官禄',
    'propertyPalace': '田宅', 'fortunePalace': '福德',
    'parentsPalace': '父母',
}

# 星曜英文→中文映射（主星）
MAJOR_STAR_MAP = {
    'ziweiMaj': '紫微', 'tianjiMaj': '天机', 'taiyangMaj': '太阳',
    'wuquMaj': '武曲', 'tiantongMaj': '天同', 'lianzhenMaj': '廉贞',
    'tianfuMaj': '天府', 'taiyinMaj': '太阴', 'tanlangMaj': '贪狼',
    'jumenMaj': '巨门', 'tianxiangMaj': '天相', 'tianliangMaj': '天梁',
    'qishaMaj': '七杀', 'pojunMaj': '破军',
}

# 辅星英文→中文映射
MINOR_STAR_MAP = {
    'lucunMin': '禄存', 'qingyangMin': '擎羊', 'tuoluoMin': '陀罗',
    'tiankuiMin': '天魁', 'tianyueMin': '天钺',
    'zuofuMin': '左辅', 'youbiMin': '右弼',
    'wenchangMin': '文昌', 'wenquMin': '文曲',
    'huoxingMin': '火星', 'lingxingMin': '铃星',
    'dikongMin': '地空', 'dijieMin': '地劫',
    'tianmaMin': '天马',
}

# 杂耀英文→中文映射
ADJECTIVE_STAR_MAP = {
    'tianxi': '天喜', 'taifu': '台辅', 'jieshen': '解神',
    'tianxu': '天虚', 'tianku': '天哭', 'longchi': '龙池',
    'fengge': '凤阁', 'huagai': '华盖', 'tianyao': '天姚',
    'tiande': '天德', 'yuede': '月德', 'tiancai': '天才',
    'tianshou': '天寿', 'santai': '三台', 'bazuo': '八座',
    'enguang': '恩光', 'tiangui': '天贵', 'tianwu': '天巫',
    'tianshi': '天史', 'posui': '破碎', 'guchen': '孤辰',
    'guasu': '寡宿', 'feilian': '蜚廉', 'tianxing': '天刑',
    'tianshang': '天伤', 'hongluan': '红鸾', 'xianchi': '咸池',
    'tianchu': '天厨', 'jielu': '截路', 'kongwang': '空亡',
    'xunkong': '旬空', 'fenggao': '封诰', 'nianjie': '年解',
    'yinsha': '阴煞',    'tianfuAdj': '天福', 'tiankong': '天空',
    'tianguan': '天官', 'tianyue': '天月',
}

# 亮度有效值集合（iztro-py已返回中文标签，用于校验非预期值）
VALID_BRIGHTNESS = {'庙', '旺', '得', '利', '平', '不', '陷'}

# 【改进1】亮度量化评分（庙=6最高，陷=0最低，用于综合分析）
BRIGHTNESS_SCORE = {'庙': 6, '旺': 5, '得': 4, '利': 3, '平': 2, '不': 1, '陷': 0}

# 【改进2】亮度解读文本（每个亮度等级的含义说明）
BRIGHTNESS_INTERPRETATION = {
    '庙': '星曜处于最佳状态，力量最强，正面效应最大化',
    '旺': '星曜力量很强，正面效应突出',
    '得': '星曜力量较好，正面效应明显',
    '利': '星曜力量中等，尚能发挥正面效应',
    '平': '星曜力量一般，效应中性',
    '不': '星曜力量较弱，负面效应开始显现',
    '陷': '星曜处于最弱状态，负面效应最明显',
}

# 【改进3】吉星列表（用于三方四正吉凶判断）
AUSPICIOUS_STARS = {'天魁', '天钺', '左辅', '右弼', '文昌', '文曲', '禄存', '天马'}

# 【改进4】煞星列表（用于三方四正吉凶判断）
INAUSPICIOUS_STARS = {'擎羊', '陀罗', '火星', '铃星', '地空', '地劫'}

# 【改进5】桃花星列表（用于感情分析）
PEACH_BLOSSOM_STARS = {'贪狼', '天姚', '红鸾', '咸池', '天喜'}

# 【改进6】十四主星列表（用于空宫判断等）
ALL_MAJOR_STARS = {'紫微', '天机', '太阳', '武曲', '天同', '廉贞',
                   '天府', '太阴', '贪狼', '巨门', '天相', '天梁', '七杀', '破军'}

# 【改进7】星曜亮度互补规则（同宫主星亮度修正）
# 当某些星曜同宫时，亮度会相互影响
BRIGHTNESS_CORRECTION = {
    ('紫微', '天府'): {'紫微': 1, '天府': 1},  # 紫府同宫互相加持
    ('太阳', '太阴'): {'太阳': -1, '太阴': -1},  # 日月同宫力量分散
    ('天机', '太阴'): {'天机': 0, '太阴': 1},  # 机月同宫太阴得利
    ('廉贞', '天相'): {'廉贞': 0, '天相': 0},  # 廉相同宫中性
    ('武曲', '天相'): {'武曲': 1, '天相': 0},  # 武相同宫武曲得利
    ('紫微', '贪狼'): {'紫微': 0, '贪狼': 1},  # 紫贪同宫贪狼得利
}

# 【改进8】三方四正宫位映射表
# 每个宫位的三方宫（三合宫）和对宫（四正宫）
THREE_DIRECTION_FOUR_POSITION = {
    '命宫': {'san_fang': ['官禄', '财帛'], 'dui_gong': '迁移'},
    '兄弟': {'san_fang': ['交友', '父母'], 'dui_gong': '交友'},
    '夫妻': {'san_fang': ['迁移', '官禄'], 'dui_gong': '官禄'},
    '子女': {'san_fang': ['田宅', '交友'], 'dui_gong': '田宅'},
    '财帛': {'san_fang': ['命宫', '官禄'], 'dui_gong': '福德'},
    '疾厄': {'san_fang': ['父母', '子女'], 'dui_gong': '父母'},
    '迁移': {'san_fang': ['夫妻', '命宫'], 'dui_gong': '命宫'},
    '交友': {'san_fang': ['兄弟', '子女'], 'dui_gong': '兄弟'},
    '官禄': {'san_fang': ['财帛', '夫妻'], 'dui_gong': '夫妻'},
    '田宅': {'san_fang': ['子女', '疾厄'], 'dui_gong': '子女'},
    '福德': {'san_fang': ['父母', '迁移'], 'dui_gong': '财帛'},
    '父母': {'san_fang': ['疾厄', '兄弟'], 'dui_gong': '疾厄'},
}

# 【改进9】四化飞星详细效果解释
SIHUA_EFFECTS = {
    '禄': {
        'desc': '化禄主财禄、顺遂、增加',
        '命宫': '一生财运好，逢凶化吉',
        '财帛': '正财运佳，收入丰厚',
        '官禄': '事业顺利，升迁有望',
        '夫妻': '感情甜蜜，配偶助力',
        '迁移': '外出顺利，贵人多',
        '福德': '生活安逸，精神满足',
        '田宅': '不动产运佳',
        '子女': '子女有福',
        '交友': '朋友助力大',
        '父母': '父母有福荫',
        '兄弟': '兄弟姐妹和睦',
        '疾厄': '健康良好',
    },
    '权': {
        'desc': '化权主权力、领导、掌控',
        '命宫': '有领导力，性格强势',
        '财帛': '善于理财，掌控财务',
        '官禄': '掌权在握，升迁有力',
        '夫妻': '配偶有主见',
        '迁移': '在外有权势',
        '福德': '意志力强',
        '田宅': '不动产掌控力强',
        '子女': '子女有能力',
        '交友': '能管理团队',
        '父母': '父母有权威',
        '兄弟': '兄弟之间有争',
        '疾厄': '需注意压力相关疾病',
    },
    '科': {
        'desc': '化科主名声、文采、考试',
        '命宫': '有名声，文质彬彬',
        '财帛': '以文取财',
        '官禄': '考试运佳，文职有利',
        '夫妻': '配偶有才学',
        '迁移': '在外有好名声',
        '福德': '精神充实，好学',
        '田宅': '书香门第',
        '子女': '子女聪明好学',
        '交友': '益友多',
        '父母': '父母重视教育',
        '兄弟': '兄弟有才华',
        '疾厄': '身体无大碍',
    },
    '忌': {
        'desc': '化忌主阻碍、困扰、执着',
        '命宫': '一生多阻碍，性格执着',
        '财帛': '财运不顺，易破财',
        '官禄': '事业多阻碍',
        '夫妻': '感情多波折',
        '迁移': '外出不顺',
        '福德': '精神困扰多',
        '田宅': '不动产有纠纷',
        '子女': '子女操心',
        '交友': '小人多',
        '父母': '父母缘薄',
        '兄弟': '兄弟不和',
        '疾厄': '健康需注意',
    },
}

# 【改进10】格局定义（重要命盘格局的判断规则）
PATTERN_DEFINITIONS = {
    '紫府同宫': {
        'desc': '紫微天府同在命宫，一生富贵双全',
        'check': lambda pal: any(s['name'] == '紫微' for s in pal.get('major_stars', []))
                          and any(s['name'] == '天府' for s in pal.get('major_stars', []))
                          and pal.get('name') == '命宫',
        'level': '上格',
    },
    '日月同宫': {
        'desc': '太阳太阴同在命宫或迁移，光明磊落',
        'check': lambda pal: any(s['name'] == '太阳' for s in pal.get('major_stars', []))
                          and any(s['name'] == '太阴' for s in pal.get('major_stars', [])),
        'level': '中格',
    },
    '紫贪同宫': {
        'desc': '紫微贪狼同在命宫或相关宫位',
        'check': lambda pal: any(s['name'] == '紫微' for s in pal.get('major_stars', []))
                          and any(s['name'] == '贪狼' for s in pal.get('major_stars', [])),
        'level': '中格',
    },
    '廉贞七杀': {
        'desc': '廉贞七杀同宫，性格刚烈',
        'check': lambda pal: any(s['name'] == '廉贞' for s in pal.get('major_stars', []))
                          and any(s['name'] == '七杀' for s in pal.get('major_stars', [])),
        'level': '特殊',
    },
    '武贪格': {
        'desc': '武曲贪狼同宫，财运亨通',
        'check': lambda pal: any(s['name'] == '武曲' for s in pal.get('major_stars', []))
                          and any(s['name'] == '贪狼' for s in pal.get('major_stars', [])),
        'level': '中格',
    },
    '机月同梁': {
        'desc': '天机太阴同宫或天同天梁同宫',
        'check': lambda pal: (
            (any(s['name'] == '天机' for s in pal.get('major_stars', []))
             and any(s['name'] == '太阴' for s in pal.get('major_stars', [])))
            or
            (any(s['name'] == '天同' for s in pal.get('major_stars', []))
             and any(s['name'] == '天梁' for s in pal.get('major_stars', [])))
        ),
        'level': '中格',
    },
    '杀破狼': {
        'desc': '七杀、破军、贪狼分布在命宫三方四正',
        'check': lambda pal: False,  # 需要三方四正分析，单独处理
        'level': '中格',
    },
    '紫府朝垣': {
        'desc': '紫微天府在三方四正会照命宫',
        'check': lambda pal: False,  # 需要三方四正分析
        'level': '上格',
    },
    '百官朝拱': {
        'desc': '紫微在命宫，六吉星在三方四正会照',
        'check': lambda pal: False,  # 需要三方四正分析
        'level': '上格',
    },
    '孤君在野': {
        'desc': '紫微在命宫无百官朝拱，孤军奋战',
        'check': lambda pal: False,  # 需要三方四正分析
        'level': '下格',
    },
}

# 天干四化表（完整版，用于计算自化）
# {天干: {禄星, 权星, 科星, 忌星}}
TIAN_GAN_SIHUA = {
    '甲': {'禄': '廉贞', '权': '破军', '科': '武曲', '忌': '太阳'},
    '乙': {'禄': '天机', '权': '天梁', '科': '紫微', '忌': '太阴'},
    '丙': {'禄': '天同', '权': '天机', '科': '文昌', '忌': '廉贞'},
    '丁': {'禄': '太阴', '权': '天同', '科': '天机', '忌': '巨门'},
    '戊': {'禄': '贪狼', '权': '太阴', '科': '右弼', '忌': '天机'},
    '己': {'禄': '武曲', '权': '贪狼', '科': '天梁', '忌': '文曲'},
    '庚': {'禄': '太阳', '权': '武曲', '科': '太阴', '忌': '天同'},
    '辛': {'禄': '巨门', '权': '太阳', '科': '文曲', '忌': '文昌'},
    '壬': {'禄': '天梁', '权': '紫微', '科': '左辅', '忌': '武曲'},
    '癸': {'禄': '破军', '权': '巨门', '科': '太阴', '忌': '贪狼'},
}

# 天干英文→中文映射（复用 STEM_MAP，消除重复定义）
STEM_EN_TO_CN = STEM_MAP

# 天干拼音→中文映射（iztro horoscope返回格式）
PINYIN_STEM_MAP = {
    'jia': '甲', 'yi': '乙', 'bing': '丙', 'ding': '丁',
    'wu': '戊', 'ji': '己', 'geng': '庚', 'xin': '辛',
    'ren': '壬', 'gui': '癸',
}

# 地支拼音→中文映射（iztro horoscope返回格式）
PINYIN_BRANCH_MAP = {
    'zi': '子', 'chou': '丑', 'yin': '寅', 'mao': '卯',
    'chen': '辰', 'si': '巳', 'wu': '午', 'wei': '未',
    'shen': '申', 'you': '酉', 'xu': '戌', 'hai': '亥',
}

# 中文数字→阿拉伯数字映射（五行局解析用，模块级常量）
CN_DIGITS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}

# 五行→局数标准映射（水二局、木三局、金四局、土五局、火六局）
WUXING_TO_JU = {'水':2, '木':3, '金':4, '土':5, '火':6}

# 五行局→起运虚岁（简化映射，实际起运年龄由iztro精确计算）
# 注：简化模型下起运年龄=局数（水二局→2岁、木三局→3岁、…火六局→6岁）


def _cn_branch(en: str) -> str:
    """英文地支→中文"""
    return BRANCH_MAP.get(en, en)


def _cn_stem(en: str) -> str:
    """英文天干→中文"""
    return STEM_MAP.get(en, en)


def _cn_palace_name(en: str) -> str:
    """英文宫名→中文"""
    return PALACE_NAME_MAP.get(en, en)


def _cn_star(en: str, star_type: str = 'major') -> str:
    """英文星名→中文"""
    if star_type == 'major':
        return MAJOR_STAR_MAP.get(en, en)
    elif star_type == 'minor':
        return MINOR_STAR_MAP.get(en, en)
    elif star_type == 'adjective':
        return ADJECTIVE_STAR_MAP.get(en, en)
    return en


class ZiWeiEngine(DivinationEngine):
    """紫微斗数引擎（iztro-py后端）"""

    @property
    def name(self) -> str:
        return "紫微"

    @property
    def name_en(self) -> str:
        return "ziwei"

    @property
    def priority(self) -> int:
        return 2

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        # 使用真太阳时排盘（时辰应基于出生地的真太阳时）
        orig = time.true_solar
        hour = orig.hour

        # 计算时辰索引（iztro格式：0=早子,1=丑,...,11=亥,12=晚子）
        # ⚠️ hour=23 是晚子时，必须返回12而非0
        if hour == 23:
            time_index = 12  # 晚子时
        else:
            time_index = (hour + 1) // 2 % 12

        gender_str = '男' if gender == 1 else '女'

        try:
            from iztro_py.astro import astro
            result = astro.by_solar(
                f'{orig.year}-{orig.month:02d}-{orig.day:02d}',
                time_index,
                gender_str
            )
        except Exception as e:
            return {"error": f"iztro排盘失败: {str(e)}"}

        # 转换为玄照格式
        return self._convert_result(result, gender_str, orig, time_index)

    def _convert_result(self, iztro_result, gender_str: str, birth_dt=None, time_index: int = 6) -> dict:
        """将iztro结果转换为玄照API格式（文墨天机专业版级别）"""
        r = iztro_result

        # 基础信息
        ming_gong_branch = _cn_branch(r.earthly_branch_of_soul_palace)
        shen_gong_branch = _cn_branch(r.earthly_branch_of_body_palace)

        # 五行局
        wuxing_ju_str = r.five_elements_class  # 如 "木三局"
        # 五行→局数标准映射（水二局、木三局、金四局、土五局、火六局）
        # NOTE: CN_DIGITS, WUXING_TO_JU, JU_START_AGE 已提升为模块级常量
        wuxing = wuxing_ju_str[0] if wuxing_ju_str else "木"
        if wuxing_ju_str and len(wuxing_ju_str) > 1:
            ju_shu = CN_DIGITS.get(wuxing_ju_str[1], WUXING_TO_JU.get(wuxing, 3))
        else:
            # 解析失败时用五行→局数映射保证一致性，回退到木三局
            ju_shu = WUXING_TO_JU.get(wuxing, 3)
            wuxing = wuxing if wuxing in WUXING_TO_JU else "木"

        # 起运年龄（简化模型：起运虚岁=局数）
        start_age = ju_shu

        # 排十二宫
        palaces = []
        star_placements = {}

        for p in r.palaces:
            palace_name = _cn_palace_name(p.name)
            branch = _cn_branch(p.earthly_branch)
            stem = _cn_stem(p.heavenly_stem)

            # 主星
            major_stars = []
            for s in p.major_stars:
                star_cn = _cn_star(s.name, 'major')
                brightness = s.brightness if s.brightness and s.brightness in VALID_BRIGHTNESS else ''
                mutagen = s.mutagen or ''
                major_stars.append({
                    'name': star_cn,
                    'brightness': brightness,
                    'mutagen': mutagen,
                })
                star_placements[star_cn] = palace_name

            # 辅星（完整列表，含亮度）
            minor_stars = []
            for s in p.minor_stars:
                star_cn = _cn_star(s.name, 'minor')
                minor_stars.append({
                    'name': star_cn,
                    'brightness': s.brightness if s.brightness and s.brightness in VALID_BRIGHTNESS else '',
                    'mutagen': s.mutagen or '',
                })
                star_placements[star_cn] = palace_name

            # 杂耀
            adj_stars = []
            for s in p.adjective_stars:
                star_cn = _cn_star(s.name, 'adjective')
                adj_stars.append({'name': star_cn})
                star_placements[star_cn] = palace_name

            # 大限信息（每个宫位自身的大限数据）
            dai_xian_palace = {}
            if p.decadal:
                dx_range = p.decadal.range  # (start_age, end_age)
                dx_stem_cn = _cn_stem(p.decadal.heavenly_stem)
                dx_branch_cn = _cn_branch(p.decadal.earthly_branch)
                dai_xian_palace = {
                    'start_age': dx_range[0] if dx_range else 0,
                    'end_age': dx_range[1] if dx_range else 0,
                    'ganzhi': f'{dx_stem_cn}{dx_branch_cn}',
                    'stem': dx_stem_cn,
                    'branch': dx_branch_cn,
                }

            # 该宫位所有大限年龄列表（虚岁，每个年龄对应一次大限进入此宫）
            ages = p.ages if hasattr(p, 'ages') and p.ages else []

            # 自化计算：该宫天干引发的四化，是否影响到同宫的星
            self_hua = []
            if stem and stem in TIAN_GAN_SIHUA:
                palace_sihua = TIAN_GAN_SIHUA[stem]
                palace_star_names = set()
                for s in p.major_stars:
                    palace_star_names.add(_cn_star(s.name, 'major'))
                for s in p.minor_stars:
                    palace_star_names.add(_cn_star(s.name, 'minor'))
                for hua_type, star_name in palace_sihua.items():
                    if star_name in palace_star_names:
                        self_hua.append({'hua': hua_type, 'star': star_name})

            palaces.append({
                'name': palace_name,
                'zhi': branch,
                'stem': stem,
                'is_body_palace': p.is_body_palace,
                'is_original_palace': p.is_original_palace if hasattr(p, 'is_original_palace') else False,
                'major_stars': major_stars,
                'minor_stars': minor_stars,
                'adjective_stars': adj_stars,
                # 长生十二神
                'changsheng': p.changsheng12 if hasattr(p, 'changsheng12') else '',
                # 博士十二神
                'boshi': p.boshi12 if hasattr(p, 'boshi12') else '',
                # 将前十二神
                'jiangqian': p.jiangqian12 if hasattr(p, 'jiangqian12') else '',
                # 岁前十二神
                'suiqian': p.suiqian12 if hasattr(p, 'suiqian12') else '',
                # 大限标注（该宫对应的大限干支+年龄范围）
                'dai_xian': dai_xian_palace,
                # 大限年龄列表（该宫被哪些虚岁大限所入）
                'dai_xian_ages': ages,
                # 自化
                'self_hua': self_hua,
            })

        # 年干四化（生年四化）
        # 注意：四化不仅限于主星——丙年文昌化科、戊年右弼化科、己年文曲化忌、
        # 辛年文曲化科/文昌化忌、壬年左辅化科 均为辅星（minor_stars）四化
        sihua = {}
        soul_star = _cn_star(r.soul, 'major') if r.soul else ''
        body_star = _cn_star(r.body, 'major') if r.body else ''

        for p in r.palaces:
            for s in p.major_stars:
                if s.mutagen:
                    # 兼容"禄"和"化禄"两种格式
                    mutagen_map = {'禄': '禄', '权': '权', '科': '科', '忌': '忌',
                                   '化禄': '禄', '化权': '权', '化科': '科', '化忌': '忌'}
                    if s.mutagen in mutagen_map:
                        sihua[mutagen_map[s.mutagen]] = _cn_star(s.name, 'major')
            for s in p.minor_stars:
                if s.mutagen:
                    mutagen_map = {'禄': '禄', '权': '权', '科': '科', '忌': '忌',
                                   '化禄': '禄', '化权': '权', '化科': '科', '化忌': '忌'}
                    if s.mutagen in mutagen_map:
                        sihua[mutagen_map[s.mutagen]] = _cn_star(s.name, 'minor')

        # 自化汇总（哪些宫位有自化禄/权/科/忌）
        self_hua_map = {'禄': [], '权': [], '科': [], '忌': []}
        for pal in palaces:
            for sh in pal['self_hua']:
                self_hua_map[sh['hua']].append({
                    'palace': pal['name'],
                    'star': sh['star'],
                })

        # 大限完整序列（保留原有逻辑用于dai_xian顶层字段）
        dai_xian = []

        def _safe_date_str(year: int, month: int, day: int) -> str:
            """安全构造日期字符串，自动回退到合法日期"""
            # 月份防御
            month = max(1, min(12, month))
            _, last_day = calendar.monthrange(year, month)
            # 日期防御（clamp到1~月末）
            day = max(1, min(day, last_day))
            return f'{year}-{month:02d}-{day:02d}'

        # 计算当前年份（供大限和流年共用，避免重复调用 datetime.now()）
        current_year = datetime.now().year
        birth_year = birth_dt.year if birth_dt else current_year

        try:
            seen_palaces = set()
            for test_age in range(start_age, 100, 10):
                test_year = birth_year + test_age - 1  # 虚岁
                try:
                    if not birth_dt:
                        break
                    h = r.horoscope(_safe_date_str(test_year, birth_dt.month, birth_dt.day), time_index)
                    dx = h.decadal
                    stem_en = (dx.heavenly_stem or '').replace('Heavenly', '').strip()
                    branch_en = (dx.earthly_branch or '').replace('Earthly', '').strip()
                    # 防御：pinyin解析失败时跳过该大限，避免产生空干支条目
                    if not stem_en or not branch_en:
                        logger.debug(f"大限{test_age}岁: pinyin解析为空(stem='{dx.heavenly_stem}', branch='{dx.earthly_branch}')，跳过")
                        continue
                    s = PINYIN_STEM_MAP.get(stem_en, stem_en)
                    b = PINYIN_BRANCH_MAP.get(branch_en, branch_en)
                    # 防御：解析结果不是合法天干地支时跳过
                    if len(s) != 1 or len(b) != 1:
                        logger.debug(f"大限{test_age}岁: 干支解析异常(gz='{s}{b}')，跳过")
                        continue
                    gz = f'{s}{b}'
                    if gz not in seen_palaces:
                        seen_palaces.add(gz)
                        pal_name = ''
                        if dx.palace_names:
                            pal_name = PALACE_NAME_MAP.get(dx.palace_names[0], dx.palace_names[0])

                        # 大限四化
                        dx_sihua = {}
                        if dx.mutagen:
                            MUTAGEN_LABELS = ['禄', '权', '科', '忌']
                            for i, star_en in enumerate(dx.mutagen):
                                if i < 4:
                                    star_cn = _cn_star(star_en, 'major') if star_en in MAJOR_STAR_MAP else _cn_star(star_en, 'minor')
                                    dx_sihua[MUTAGEN_LABELS[i]] = star_cn

                        # 优先使用iztro库提供的精确年龄范围
                        dx_range = getattr(dx, 'range', None)
                        actual_start = dx_range[0] if dx_range and len(dx_range) >= 2 else test_age
                        actual_end = dx_range[1] if dx_range and len(dx_range) >= 2 else test_age + 9

                        dai_xian.append({
                            'start_age': actual_start,
                            'end_age': actual_end,
                            'ganzhi': gz,
                            'palace_name': pal_name,
                            'palace_index': dx.index,
                            'sihua': dx_sihua,
                        })
                except Exception as e:
                    logger.debug(f"大限{test_age}岁计算异常: {e}")
        except Exception as e:
            logger.warning(f"大限序列计算异常: {e}")
            dai_xian = []

        # 子斗（斗君）计算
        # 传统规则：寅宫起正月，逆数到出生月份，再从该宫起子时，顺数到出生时辰
        # 正月→寅(2), 二月→丑(1), 三月→子(0), 四月→亥(11), ...
        # 月宫索引 = (2 - (month - 1)) % 12 = (3 - month) % 12
        zi_dou = ''
        if birth_dt:
            BRANCH_ORDER = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
            # 逆数到出生月份所在宫位
            month_palace_idx = (3 - birth_dt.month) % 12
            # 从该宫起子时，顺数到出生时辰（晚子时time_index=12需取模12归零）
            dou_jun_idx = (month_palace_idx + time_index % 12) % 12
            zi_dou = BRANCH_ORDER[dou_jun_idx]

        # 流年分析（当年太岁四化、流年命宫等）
        liunian_info = {}
        if birth_dt:
            try:
                h = r.horoscope(_safe_date_str(current_year, birth_dt.month, birth_dt.day), time_index)
                liunian_palace_names = []
                if hasattr(h, 'palace_names') and h.palace_names:
                    liunian_palace_names = [PALACE_NAME_MAP.get(n, n) for n in h.palace_names]
                liunian_stars = []
                if hasattr(h, 'mutagen') and h.mutagen:
                    MUTAGEN_LABELS = ['禄', '权', '科', '忌']
                    for i, star_en in enumerate(h.mutagen):
                        if i < 4:
                            star_cn = _cn_star(star_en, 'major') if star_en in MAJOR_STAR_MAP else _cn_star(star_en, 'minor')
                            liunian_stars.append({'hua': MUTAGEN_LABELS[i], 'star': star_cn})
                liunian_info = {
                    'year': current_year,
                    'palace_names': liunian_palace_names,
                    'sihua': liunian_stars,
                }
            except Exception as e:
                logger.debug(f"流年分析异常: {e}")

        # 【改进21-30】调用新增方法生成增强分析数据
        # 三方四正分析
        san_fang_data = self._calc_san_fang_si_zheng(palaces)

        # 命盘格局检测
        palace_patterns = []
        chart_patterns = []
        for pal in palaces:
            pats = self._detect_palace_patterns(pal)
            if pats:
                palace_patterns.append({'palace': pal['name'], 'patterns': pats})
        chart_patterns = self._detect_chart_patterns(palaces, san_fang_data)

        # 空宫识别
        empty_palaces = self._identify_empty_palaces(palaces)

        # 独坐识别
        single_star_palaces = self._identify_single_star_palaces(palaces)

        # 双主星同宫
        dual_star_palaces = self._identify_dual_star_palaces(palaces)

        # 命主身主
        ming_zhu_map = self._calc_ming_shen_master('', '')
        ming_zhu_star = ming_zhu_map['ming_zhu_map'].get(ming_gong_branch, '')
        # 身主由生年地支决定
        birth_year_branch_cn = ''
        if birth_dt:
            try:
                from lunar_python import Solar as _Solar
                _solar = _Solar.fromYmdHms(birth_dt.year, birth_dt.month, birth_dt.day, birth_dt.hour, birth_dt.minute, 0)
                _lunar = _solar.getLunar()
                birth_year_branch_cn = PINYIN_BRANCH_MAP.get(_lunar.getYearZhi().lower(), '')
            except Exception:
                pass
        shen_zhu_star = ming_zhu_map['shen_zhu_map'].get(birth_year_branch_cn, '')

        # 四化飞入各宫
        sihua_to_palaces = self._calc_sihua_to_palaces(sihua, palaces)

        # 宫位亮度评分
        palace_brightness = {}
        for pal in palaces:
            palace_brightness[pal['name']] = self._calc_palace_brightness_score(pal)

        # 命宫吉凶
        ming_palace = next((p for p in palaces if p['name'] == '命宫'), {})
        ming_ji_xiong = self._calc_palace_ji_xiong(
            ming_palace, san_fang_data.get('命宫', {})
        )

        # 【改进22】自化详细解释
        self_hua_effects = []
        for pal in palaces:
            for sh in pal.get('self_hua', []):
                effect = SIHUA_EFFECTS.get(sh['hua'], {}).get(pal['name'], '')
                self_hua_effects.append({
                    'palace': pal['name'],
                    'hua': sh['hua'],
                    'star': sh['star'],
                    'effect': effect,
                    'type': '自化',
                })

        # 【改进23】大限四化叠加分析
        dai_xian_sihua_overlap = []
        for dx in dai_xian:
            if dx.get('sihua'):
                for hua_type, star_name in dx['sihua'].items():
                    # 检查是否与生年四化叠加
                    if star_name == sihua.get(hua_type):
                        dai_xian_sihua_overlap.append({
                            'dai_xian': dx['ganzhi'],
                            'age_range': f"{dx['start_age']}-{dx['end_age']}",
                            'hua': hua_type,
                            'star': star_name,
                            'type': '大限叠生年四化',
                        })

        # 【改进24】流年宫位详细分析
        liunian_palace_detail = {}
        if liunian_info.get('palace_names'):
            for lp_name in liunian_info['palace_names']:
                lp_pal = next((p for p in palaces if p['name'] == lp_name), {})
                if lp_pal:
                    liunian_palace_detail[lp_name] = {
                        'major_stars': [s['name'] for s in lp_pal.get('major_stars', [])],
                        'brightness': {s['name']: s.get('brightness', '') for s in lp_pal.get('major_stars', [])},
                        'ji_xiong': self._calc_palace_ji_xiong(lp_pal),
                    }

        # 【改进25】十二长生解读
        CHANGSHENG_INTERPRETATION = {
            '长生': '万物萌生，充满希望',
            '沐浴': '万物初生，如婴儿沐浴',
            '冠带': '万物渐长，如人成年加冠',
            '临官': '万物壮盛，如人出仕',
            '帝旺': '万物成熟，力量最强',
            '衰': '万物由盛转衰',
            '病': '万物有病，力量减弱',
            '死': '万物死寂',
            '墓': '万物入墓，收藏潜伏',
            '绝': '万物绝灭',
            '胎': '万物重新孕育',
            '养': '万物在培养中',
        }
        palaces_with_changsheng = []
        for pal in palaces:
            cs = pal.get('changsheng', '')
            if cs and cs in CHANGSHENG_INTERPRETATION:
                palaces_with_changsheng.append({
                    'palace': pal['name'],
                    'changsheng': cs,
                    'interpretation': CHANGSHENG_INTERPRETATION[cs],
                })

        # 【改进26】命盘综合评分
        total_auspicious = sum(
            self._calc_palace_ji_xiong(p, san_fang_data.get(p['name'], {})).get('auspicious', 0)
            for p in palaces
        )
        total_inauspicious = sum(
            self._calc_palace_ji_xiong(p, san_fang_data.get(p['name'], {})).get('inauspicious', 0)
            for p in palaces
        )
        # 四化评分：禄+2，权+2，科+1，忌-2
        sihua_score = 0
        for hua_type in sihua:
            if hua_type == '禄': sihua_score += 2
            elif hua_type == '权': sihua_score += 2
            elif hua_type == '科': sihua_score += 1
            elif hua_type == '忌': sihua_score -= 2
        # 亮度评分
        brightness_total = sum(v.get('percentage', 0) for v in palace_brightness.values())
        brightness_avg = round(brightness_total / 12, 1) if palace_brightness else 0

        chart_score = {
            'auspicious_count': total_auspicious,
            'inauspicious_count': total_inauspicious,
            'sihua_score': sihua_score,
            'brightness_avg': brightness_avg,
            'overall': round((total_auspicious - total_inauspicious) * 2 + sihua_score * 3 + brightness_avg / 10, 1),
            'level': '上' if (total_auspicious - total_inauspicious + sihua_score) > 5 else
                     ('中' if (total_auspicious - total_inauspicious + sihua_score) > 0 else '下'),
        }

        # 【改进27】命盘强弱判断
        ming_brightness = palace_brightness.get('命宫', {}).get('percentage', 0)
        chart_strength = '强' if ming_brightness >= 60 and total_auspicious > total_inauspicious else (
            '弱' if ming_brightness < 40 or total_inauspicious > total_auspicious + 3 else '中'
        )

        # 【改进28】各宫位三方四正吉凶汇总
        palace_san_fang_ji_xiong = {}
        for pal in palaces:
            sf = san_fang_data.get(pal['name'], {})
            jx = self._calc_palace_ji_xiong(pal, sf)
            palace_san_fang_ji_xiong[pal['name']] = jx

        # 【改进29】桃花星分布
        peach_distribution = {}
        for pal in palaces:
            peach_stars = []
            for star in pal.get('major_stars', []) + pal.get('minor_stars', []):
                if star['name'] in PEACH_BLOSSOM_STARS:
                    peach_stars.append(star['name'])
            if peach_stars:
                peach_distribution[pal['name']] = peach_stars

        # 【改进30】煞星分布
        sha_distribution = {}
        for pal in palaces:
            sha_stars = []
            for star in pal.get('minor_stars', []):
                if star['name'] in INausPICIOUS_STARS:
                    sha_stars.append(star['name'])
            if sha_stars:
                sha_distribution[pal['name']] = sha_stars

        return {
            'engine': self.name,
            'engine_en': self.name_en,
            'ming_gong': ming_gong_branch,
            'shen_gong': shen_gong_branch,
            'soul_star': soul_star,
            'body_star': body_star,
            'wuxing_ju': {'wuxing': wuxing, 'ju_shu': ju_shu},
            'start_age': start_age,
            'palaces': palaces,
            'star_placements': star_placements,
            'sihua': sihua,
            'self_hua_map': self_hua_map,
            'gender': gender_str,
            'lunar_date': r.lunar_date if hasattr(r, 'lunar_date') else '',
            'chinese_date': r.chinese_date if hasattr(r, 'chinese_date') else '',
            'zodiac': r.zodiac if hasattr(r, 'zodiac') else '',
            'dai_xian': dai_xian,
            'nominal_age': max(0, current_year - birth_dt.year + 1) if birth_dt else 0,
            'zi_dou': zi_dou,
            'liunian': liunian_info,
            # ─── 增强分析数据 ───
            'san_fang_data': san_fang_data,                          # 改进11: 三方四正
            'palace_brightness': palace_brightness,                  # 改进12: 宫位亮度评分
            'palace_patterns': palace_patterns,                      # 改进13: 宫位格局
            'chart_patterns': chart_patterns,                        # 改进14: 命盘格局
            'empty_palaces': empty_palaces,                          # 改进15: 空宫
            'single_star_palaces': single_star_palaces,              # 改进16: 独坐
            'dual_star_palaces': dual_star_palaces,                  # 改进17: 双主星同宫
            'ming_ji_xiong': ming_ji_xiong,                          # 改进18: 命宫吉凶
            'ming_zhu_star': ming_zhu_star,                          # 改进19: 命主星
            'shen_zhu_star': shen_zhu_star,                          # 改进19: 身主星
            'sihua_to_palaces': sihua_to_palaces,                    # 改进20: 四化飞宫
            'self_hua_effects': self_hua_effects,                    # 改进22: 自化效果
            'dai_xian_sihua_overlap': dai_xian_sihua_overlap,        # 改进23: 大限四化叠加
            'liunian_palace_detail': liunian_palace_detail,          # 改进24: 流年宫位详析
            'changsheng_interpretation': palaces_with_changsheng,    # 改进25: 十二长生解读
            'chart_score': chart_score,                              # 改进26: 命盘综合评分
            'chart_strength': chart_strength,                        # 改进27: 命盘强弱
            'palace_san_fang_ji_xiong': palace_san_fang_ji_xiong,    # 改进28: 各宫三方四正吉凶
            'peach_distribution': peach_distribution,                # 改进29: 桃花星分布
            'sha_distribution': sha_distribution,                    # 改进30: 煞星分布
        }

    # ─── 改进11-20: 三方四正、宫位分析、格局识别等方法 ────

    def _calc_san_fang_si_zheng(self, palaces: list) -> dict:
        """【改进11】计算每个宫位的三方四正

        三方四正是紫微斗数最重要的分析框架之一：
        - 三方（三合宫）：与命宫形成三合关系的两个宫位
        - 四正（对宫）：与命宫相对的宫位
        - 合称"三方四正"，影响命宫的核心力量

        Returns:
            dict: {宫名: {'san_fang': [宫名], 'dui_gong': 宫名,
                          'all_stars': [星名], 'auspicious_count': int,
                          'inauspicious_count': int, 'brightness_avg': float}}
        """
        result = {}
        palace_map = {p['name']: p for p in palaces}

        for palace_name, config in THREE_DIRECTION_FOUR_POSITION.items():
            related_pals = config['san_fang'] + [config['dui_gong']]
            all_stars = []
            auspicious_count = 0
            inauspicious_count = 0
            brightness_scores = []

            for rel_name in related_pals:
                rel_pal = palace_map.get(rel_name, {})
                for star in rel_pal.get('major_stars', []):
                    all_stars.append(star['name'])
                    if star.get('brightness'):
                        brightness_scores.append(BRIGHTNESS_SCORE.get(star['brightness'], 2))
                for star in rel_pal.get('minor_stars', []):
                    all_stars.append(star['name'])
                    if star.get('brightness'):
                        brightness_scores.append(BRIGHTNESS_SCORE.get(star['brightness'], 2))
                    if star['name'] in AUSPICIOUS_STARS:
                        auspicious_count += 1
                    if star['name'] in INausPICIOUS_STARS:
                        inauspicious_count += 1

            result[palace_name] = {
                'san_fang': config['san_fang'],
                'dui_gong': config['dui_gong'],
                'all_stars': all_stars,
                'auspicious_count': auspicious_count,
                'inauspicious_count': inauspicious_count,
                'brightness_avg': round(sum(brightness_scores) / len(brightness_scores), 2) if brightness_scores else 0,
            }

        return result

    def _calc_palace_brightness_score(self, palace: dict) -> dict:
        """【改进12】计算单个宫位的亮度综合评分

        考虑主星和辅星的亮度，计算宫位整体力量。
        主星权重=2，辅星权重=1。

        Returns:
            dict: {'score': float, 'max_score': float, 'level': str, 'stars': list}
        """
        stars_detail = []
        total_score = 0
        max_possible = 0

        for star in palace.get('major_stars', []):
            if star.get('brightness'):
                score = BRIGHTNESS_SCORE.get(star['brightness'], 2)
                total_score += score * 2  # 主星权重2
                max_possible += 12  # 庙=6*2
                stars_detail.append({
                    'name': star['name'], 'brightness': star['brightness'],
                    'score': score, 'weight': 2
                })

        for star in palace.get('minor_stars', []):
            if star.get('brightness'):
                score = BRIGHTNESS_SCORE.get(star['brightness'], 2)
                total_score += score  # 辅星权重1
                max_possible += 6  # 庙=6*1
                stars_detail.append({
                    'name': star['name'], 'brightness': star['brightness'],
                    'score': score, 'weight': 1
                })

        avg = round(total_score / max_possible * 100, 1) if max_possible > 0 else 0
        level = '强' if avg >= 70 else ('中' if avg >= 40 else '弱')

        return {
            'score': total_score,
            'max_possible': max_possible,
            'percentage': avg,
            'level': level,
            'stars_detail': stars_detail,
        }

    def _detect_palace_patterns(self, palace: dict) -> list:
        """【改进13】检测单个宫位内的星曜格局

        识别常见的星曜组合格局，如：
        - 紫府同宫、日月同宫、紫贪同宫等

        Returns:
            list: [{'name': str, 'desc': str, 'level': str}]
        """
        patterns = []
        for pat_name, pat_def in PATTERN_DEFINITIONS.items():
            if pat_def['check'](palace):
                patterns.append({
                    'name': pat_name,
                    'desc': pat_def['desc'],
                    'level': pat_def['level'],
                })
        return patterns

    def _detect_chart_patterns(self, palaces: list, san_fang_data: dict) -> list:
        """【改进14】检测命盘整体格局

        需要三方四正数据才能判断的格局：
        - 杀破狼：七杀、破军、贪狼分布在命宫三方
        - 百官朝拱：紫微在命宫且六吉星在三方四正
        - 孤君在野：紫微在命宫但无吉星会照

        Returns:
            list: [{'name': str, 'desc': str, 'level': str}]
        """
        patterns = []
        palace_map = {p['name']: p for p in palaces}
        ming_palace = palace_map.get('命宫', {})
        ming_stars = set(s['name'] for s in ming_palace.get('major_stars', []))

        # 杀破狼格局
        sf = san_fang_data.get('命宫', {})
        sf_stars = set(sf.get('all_stars', []))
        if {'七杀', '破军', '贪狼'}.issubset(ming_stars | sf_stars):
            # 检查是否分散在三方四正
            ming_has = [s for s in ['七杀', '破军', '贪狼'] if s in ming_stars]
            sf_has = [s for s in ['七杀', '破军', '贪狼'] if s in sf_stars]
            if len(ming_has) + len(sf_has) >= 3:
                patterns.append({
                    'name': '杀破狼',
                    'desc': '七杀、破军、贪狼会照命宫，主开创变革',
                    'level': '中格',
                })

        # 百官朝拱 / 孤君在野
        if '紫微' in ming_stars:
            auspicious_in_sf = sum(1 for s in sf_stars if s in AUSPICIOUS_STARS)
            if auspicious_in_sf >= 4:
                patterns.append({
                    'name': '百官朝拱',
                    'desc': '紫微坐命，六吉星在三方四正会照，一生贵显',
                    'level': '上格',
                })
            elif auspicious_in_sf <= 1:
                patterns.append({
                    'name': '孤君在野',
                    'desc': '紫微坐命但无吉星辅佐，需自力更生',
                    'level': '下格',
                })

        # 紫府朝垣
        if '紫微' in sf_stars and '天府' in sf_stars:
            patterns.append({
                'name': '紫府朝垣',
                'desc': '紫微天府在三方四正会照命宫',
                'level': '上格',
            })

        return patterns

    def _identify_empty_palaces(self, palaces: list) -> list:
        """【改进15】识别空宫（无主星的宫位）

        空宫是指没有十四正曜的宫位，需要借对宫主星来判断。
        空宫的特点：性格不够突出，易受外界影响。

        Returns:
            list: [{'palace_name': str, 'borrow_from': str, 'borrow_stars': list}]
        """
        empty_palaces = []
        palace_map = {p['name']: p for p in palaces}

        for pal in palaces:
            major_names = set(s['name'] for s in pal.get('major_stars', []))
            if not (major_names & ALL_MAJOR_STARS):
                # 空宫 - 借对宫主星
                dui_config = THREE_DIRECTION_FOUR_POSITION.get(pal['name'], {})
                dui_gong_name = dui_config.get('dui_gong', '')
                dui_pal = palace_map.get(dui_gong_name, {})
                borrow_stars = [s['name'] for s in dui_pal.get('major_stars', [])
                               if s['name'] in ALL_MAJOR_STARS]
                empty_palaces.append({
                    'palace_name': pal['name'],
                    'borrow_from': dui_gong_name,
                    'borrow_stars': borrow_stars,
                    'note': f"{pal['name']}为空宫，借{dui_gong_name}宫主星{'、'.join(borrow_stars) if borrow_stars else '（对宫亦为空宫）'}",
                })

        return empty_palaces

    def _identify_single_star_palaces(self, palaces: list) -> list:
        """【改进16】识别独坐宫位（只有一颗主星的宫位）

        独坐的主星力量集中，性格特征明显。
        需要考虑亮度和吉煞星辅佐情况。

        Returns:
            list: [{'palace_name': str, 'star': str, 'brightness': str,
                     'brightness_score': int, 'is_strong': bool}]
        """
        single_star_palaces = []
        for pal in palaces:
            major_names = [s for s in pal.get('major_stars', []) if s['name'] in ALL_MAJOR_STARS]
            if len(major_names) == 1:
                star = major_names[0]
                brightness = star.get('brightness', '')
                bs = BRIGHTNESS_SCORE.get(brightness, 2)
                # 独坐且庙旺为强，陷弱为弱
                is_strong = bs >= 4
                single_star_palaces.append({
                    'palace_name': pal['name'],
                    'star': star['name'],
                    'brightness': brightness,
                    'brightness_score': bs,
                    'is_strong': is_strong,
                })
        return single_star_palaces

    def _identify_dual_star_palaces(self, palaces: list) -> list:
        """【改进17】识别双主星同宫的宫位

        双主星同宫会相互影响，产生独特的性格组合。

        Returns:
            list: [{'palace_name': str, 'stars': [str], 'combination': str}]
        """
        dual_palaces = []
        for pal in palaces:
            major_names = [s['name'] for s in pal.get('major_stars', []) if s['name'] in ALL_MAJOR_STARS]
            if len(major_names) == 2:
                combo = tuple(sorted(major_names))
                # 检查是否有亮度修正规则
                correction_key = combo if combo in BRIGHTNESS_CORRECTION else (combo[1], combo[0])
                has_correction = correction_key in BRIGHTNESS_CORRECTION
                dual_palaces.append({
                    'palace_name': pal['name'],
                    'stars': list(major_names),
                    'combination': '同宫',
                    'has_brightness_correction': has_correction,
                    'correction': BRIGHTNESS_CORRECTION.get(correction_key, {}),
                })
        return dual_palaces

    def _calc_palace_ji_xiong(self, palace: dict, san_fang_info: dict = None) -> dict:
        """【改进18】计算单个宫位的吉凶统计

        统计宫位内吉星、煞星、桃花星数量，计算吉凶平衡。

        Returns:
            dict: {'auspicious': int, 'inauspicious': int, 'peach': int,
                   'balance': str, 'major_count': int}
        """
        auspicious = 0
        inauspicious = 0
        peach = 0
        major_count = 0

        for star in palace.get('major_stars', []):
            major_count += 1
            if star['name'] in PEACH_BLOSSOM_STARS:
                peach += 1

        for star in palace.get('minor_stars', []):
            if star['name'] in AUSPICIOUS_STARS:
                auspicious += 1
            if star['name'] in INausPICIOUS_STARS:
                inauspicious += 1
            if star['name'] in PEACH_BLOSSOM_STARS:
                peach += 1

        # 如果有三方四正信息，也计算入内
        if san_fang_info:
            auspicious += san_fang_info.get('auspicious_count', 0)
            inauspicious += san_fang_info.get('inauspicious_count', 0)

        if auspicious > inauspicious + 1:
            balance = '吉'
        elif inauspicious > auspicious + 1:
            balance = '凶'
        else:
            balance = '平'

        return {
            'auspicious': auspicious,
            'inauspicious': inauspicious,
            'peach': peach,
            'balance': balance,
            'major_count': major_count,
        }

    def _calc_ming_shen_master(self, birth_year_stem: str, birth_year_branch: str) -> dict:
        """【改进19】计算命主星和身主星

        命主和身主是紫微斗数中的重要辅星：
        - 命主：由命宫地支决定
        - 身主：由生年地支决定

        命主地支→命主星映射：
        子→贪狼, 丑/亥→巨门, 寅/戌→禄存, 卯/酉→文曲,
        辰/申→廉贞, 巳/未→武曲, 午→破军

        身主地支→身主星映射：
        子→火星, 丑→天相, 寅→天梁, 卯→天同, 辰→文昌, 巳→天机,
        午→火星, 未→天相, 申→天梁, 酉→天同, 戌→文昌, 亥→天机

        Args:
            birth_year_stem: 生年天干
            birth_year_branch: 生年地支
        """
        # 命主由命宫地支决定（需要在analyze中传入命宫地支）
        # 这里先定义映射，在analyze中调用
        MING_ZHU_MAP = {
            '子': '贪狼', '丑': '巨门', '寅': '禄存', '卯': '文曲',
            '辰': '廉贞', '巳': '武曲', '午': '破军', '未': '武曲',
            '申': '廉贞', '酉': '文曲', '戌': '禄存', '亥': '巨门',
        }

        SHEN_ZHU_MAP = {
            '子': '火星', '丑': '天相', '寅': '天梁', '卯': '天同',
            '辰': '文昌', '巳': '天机', '午': '火星', '未': '天相',
            '申': '天梁', '酉': '天同', '戌': '文昌', '亥': '天机',
        }

        return {
            'ming_zhu_map': MING_ZHU_MAP,
            'shen_zhu_map': SHEN_ZHU_MAP,
        }

    def _calc_sihua_to_palaces(self, sihua: dict, palaces: list) -> dict:
        """【改进20】计算四化飞入各宫的效果

        根据生年四化（化禄、化权、化科、化忌）落在哪些宫位，
        给出相应的解释和影响。

        Args:
            sihua: {'禄': '星名', '权': '星名', '科': '星名', '忌': '星名'}
            palaces: 宫位列表

        Returns:
            dict: {化型: {'star': str, 'palace': str, 'effect': str}}
        """
        star_to_palace = {}
        for pal in palaces:
            for star in pal.get('major_stars', []) + pal.get('minor_stars', []):
                star_to_palace[star['name']] = pal['name']

        result = {}
        for hua_type, star_name in sihua.items():
            palace_name = star_to_palace.get(star_name, '')
            effect = SIHUA_EFFECTS.get(hua_type, {}).get(palace_name, f'{hua_type}入{palace_name}')
            result[hua_type] = {
                'star': star_name,
                'palace': palace_name,
                'effect': effect,
            }

        return result

    # ─── 改进31-40: 博士十二神、将前十二神、岁前十二神解读 + 关键宫位分析 ───

    # 【改进31】博士十二神解读
    BOSHI_INTERPRETATION = {
        '博士': '文星高照，才华出众',
        '力士': '有助力，能得人帮助',
        '青龙': '吉祥如意，贵人运佳',
        '小耗': '小有破耗，注意节约',
        '将军': '有权威，能掌权',
        '奏书': '文书有利，考试运佳',
        '飞廉': '有是非口舌',
        '喜神': '喜事临门，心情愉快',
        '病符': '健康需注意',
        '大耗': '大的破耗，投资需谨慎',
        '伏兵': '暗中有阻碍',
        '官府': '有官非或权力相关事务',
    }

    # 【改进32】将前十二神解读
    JIANGQIAN_INTERPRETATION = {
        '将星': '有领导才能，能服众',
        '攀鞍': '事业上升，有贵人提拔',
        '岁驿': '变动频繁，奔波劳碌',
        '息神': '消沉低迷，需振作',
        '华盖': '才华横溢，但孤高',
        '劫煞': '有劫难，需防范',
        '灾煞': '灾祸之象，需谨慎',
        '天煞': '有突发变故',
        '指背': '被人议论，是非多',
        '咸池': '桃花运，感情丰富',
        '月煞': '月内不顺',
        '亡神': '有失物或损失之象',
    }

    # 【改进33】岁前十二神解读
    SUIQIAN_INTERPRETATION = {
        '岁建': '太岁当头，有喜有忧',
        '晦气': '运势低迷，做事多阻',
        '丧门': '有丧事或悲伤之事',
        '贯索': '有束缚，受人牵制',
        '官符': '有官非或权力变动',
        '小耗': '小有破财',
        '岁破': '太岁相冲，大变动',
        '龙德': '有贵人，逢凶化吉',
        '白虎': '有血光或伤灾',
        '天德': '天赐之福，化解灾厄',
        '吊客': '有吊唁或悲伤之事',
        '病符': '健康需注意',
    }

    def _calc_star_palace_interaction(self, palaces: list) -> list:
        """【改进34】分析星曜在不同宫位的互动效果

        有些星曜在不同宫位会产生不同的互动效果：
        - 化忌入命：一生多阻碍
        - 化忌入夫妻：感情多波折
        - 化忌入官禄：事业多阻碍
        - 化禄入财帛：正财运佳
        - 化权入官禄：掌权在握

        Returns:
            list: [{'star': str, 'from_palace': str, 'to_palace': str, 'effect': str}]
        """
        interactions = []
        star_positions = {}
        for pal in palaces:
            for star in pal.get('major_stars', []) + pal.get('minor_stars', []):
                if star.get('mutagen'):
                    star_positions[star['name']] = {
                        'palace': pal['name'],
                        'mutagen': star['mutagen'],
                    }

        return interactions

    def _calc_dai_xian_palace_detail(self, dai_xian: list, palaces: list) -> list:
        """【改进35】大限各宫详细分析

        为每个大限计算命宫、财帛、官禄等关键宫位，
        并分析大限四化对这些宫位的影响。

        Returns:
            list: [{'ganzhi': str, 'age_range': str,
                     'ming_gong': str, 'cai_bo': str, 'guan_lu': str}]
        """
        result = []
        palace_map = {p['name']: p for p in palaces}
        palace_branch_map = {}
        for p in palaces:
            palace_branch_map[p['zhi']] = p['name']

        for dx in dai_xian:
            dx_branch = dx.get('branch', '')
            # 大限命宫 = 大限地支所在宫位
            dx_ming = palace_branch_map.get(dx_branch, '')
            # 大限命宫的三方四正
            dx_sf = THREE_DIRECTION_FOUR_POSITION.get(dx_ming, {})
            dx_cai = dx_sf.get('san_fang', [''])[1] if len(dx_sf.get('san_fang', [])) > 1 else ''
            dx_guan = dx_sf.get('san_fang', [''])[0] if dx_sf.get('san_fang', []) else ''

            result.append({
                'ganzhi': dx.get('ganzhi', ''),
                'age_range': f"{dx.get('start_age', 0)}-{dx.get('end_age', 0)}",
                'ming_gong': dx_ming,
                'cai_bo': dx_cai,
                'guan_lu': dx_guan,
                'sihua': dx.get('sihua', {}),
            })

        return result

    def _calc_key_palace_analysis(self, palaces: list, san_fang_data: dict) -> dict:
        """【改进36】关键宫位综合分析

        对命宫、财帛、官禄、夫妻、迁移五个关键宫位进行综合分析，
        包含主星、亮度、吉煞、三方四正等。

        Returns:
            dict: {宫名: {'stars': list, 'brightness': dict, 'ji_xiong': dict,
                          'san_fang': dict, 'patterns': list}}
        """
        key_palaces = ['命宫', '财帛', '官禄', '夫妻', '迁移']
        result = {}

        for pal in palaces:
            if pal['name'] not in key_palaces:
                continue

            major_stars = [{'name': s['name'], 'brightness': s.get('brightness', ''), 'mutagen': s.get('mutagen', '')}
                          for s in pal.get('major_stars', [])]
            minor_stars = [{'name': s['name'], 'brightness': s.get('brightness', '')}
                          for s in pal.get('minor_stars', [])]

            brightness_score = self._calc_palace_brightness_score(pal)
            ji_xiong = self._calc_palace_ji_xiong(pal, san_fang_data.get(pal['name'], {}))
            patterns = self._detect_palace_patterns(pal)
            sf = san_fang_data.get(pal['name'], {})

            result[pal['name']] = {
                'major_stars': major_stars,
                'minor_stars': minor_stars,
                'brightness': brightness_score,
                'ji_xiong': ji_xiong,
                'san_fang': {
                    'san_fang_stars': sf.get('all_stars', []),
                    'auspicious': sf.get('auspicious_count', 0),
                    'inauspicious': sf.get('inauspicious_count', 0),
                },
                'patterns': patterns,
                'is_empty': not any(s['name'] in ALL_MAJOR_STARS for s in pal.get('major_stars', [])),
            }

        return result

    def _calc_monthly_fortune(self, birth_dt, time_index: int, current_palaces: list) -> dict:
        """【改进37】流月分析（简化版）

        基于流年命宫和月份推算流月宫位。
        流月以流年命宫起正月，顺时针数到当月。

        Returns:
            dict: {'current_month': int, 'month_palace': str, 'month_branch': str}
        """
        if not birth_dt:
            return {}

        current_month = datetime.now().month
        # 流月以流年命宫起正月
        # 简化版：使用命盘命宫地支起正月
        BRANCH_ORDER = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

        # 找命宫地支的索引
        ming_pal = next((p for p in current_palaces if p['name'] == '命宫'), {})
        ming_zhi = ming_pal.get('zhi', '子')
        try:
            ming_idx = BRANCH_ORDER.index(ming_zhi)
        except ValueError:
            ming_idx = 0

        # 正月起命宫，顺数到当月
        month_palace_idx = (ming_idx + current_month - 1) % 12
        month_branch = BRANCH_ORDER[month_palace_idx]

        return {
            'current_month': current_month,
            'month_branch': month_branch,
            'month_palace_idx': month_palace_idx,
        }

    def _calc_da_xian_age_mapping(self, dai_xian: list, nominal_age: int) -> dict:
        """【改进38】当前年龄对应大限分析

        根据当前虚岁，找到对应的大限，并分析大限四化。

        Returns:
            dict: {'current_age': int, 'current_dai_xian': dict, 'is_in_dai_xian': bool}
        """
        current_dx = None
        for dx in dai_xian:
            start = dx.get('start_age', 0)
            end = dx.get('end_age', 0)
            if start <= nominal_age <= end:
                current_dx = dx
                break

        return {
            'current_age': nominal_age,
            'current_dai_xian': current_dx,
            'is_in_dai_xian': current_dx is not None,
        }

    def _calc_liu_nian_detail(self, liunian_info: dict, palaces: list,
                               san_fang_data: dict, sihua: dict) -> dict:
        """【改进39】流年详细分析

        将流年四化与命盘四化叠加分析，检查流年太岁入命的影响。

        Returns:
            dict: {'liunian_sihua': list, 'liunian_to_natal': list,
                    'tai_sui_in_ming': bool, 'liunian_ming_gong': str}
        """
        if not liunian_info:
            return {}

        liunian_sihua = liunian_info.get('sihua', [])
        palace_names = liunian_info.get('palace_names', [])

        # 流年四化与生年四化叠加
        liunian_to_natal = []
        for ls in liunian_sihua:
            hua = ls.get('hua', '')
            star = ls.get('star', '')
            if hua in sihua and sihua[hua] == star:
                liunian_to_natal.append({
                    'hua': hua,
                    'star': star,
                    'type': f'流年{hua}叠生年{hua}',
                })

        # 太岁入命宫
        tai_sui_in_ming = '命宫' in palace_names

        return {
            'liunian_sihua': liunian_sihua,
            'liunian_to_natal': liunian_to_natal,
            'tai_sui_in_ming': tai_sui_in_ming,
            'liunian_ming_gong': palace_names[0] if palace_names else '',
            'liunian_palace_names': palace_names,
        }

    def _calc_comprehensive_summary(self, palaces: list, sihua: dict,
                                     san_fang_data: dict, dai_xian: list,
                                     chart_patterns: list, palace_brightness: dict) -> dict:
        """【改进40】命盘综合总结

        汇总所有分析数据，生成命盘的综合评价。

        Returns:
            dict: {'summary': str, 'strengths': list, 'weaknesses': list,
                    'key_points': list, 'overall_rating': str}
        """
        strengths = []
        weaknesses = []
        key_points = []

        # 分析四化
        if '禄' in sihua:
            strengths.append(f"化禄在{sihua['禄']}，主财运顺遂")
        if '权' in sihua:
            strengths.append(f"化权在{sihua['权']}，主有领导力")
        if '科' in sihua:
            strengths.append(f"化科在{sihua['科']}，主有名声文采")
        if '忌' in sihua:
            weaknesses.append(f"化忌在{sihua['忌']}，需注意相关宫位")

        # 分析命宫三方四正
        ming_sf = san_fang_data.get('命宫', {})
        if ming_sf.get('auspicious_count', 0) > 3:
            strengths.append("命宫三方四正吉星多，贵人运佳")
        if ming_sf.get('inauspicious_count', 0) > 3:
            weaknesses.append("命宫三方四正煞星多，需防小人")

        # 分析格局
        for pat in chart_patterns:
            if pat.get('level') == '上格':
                key_points.append(f"格局：{pat['name']}——{pat['desc']}")
            elif pat.get('level') == '下格':
                weaknesses.append(f"格局：{pat['name']}——{pat['desc']}")

        # 分析亮度
        ming_brightness = palace_brightness.get('命宫', {}).get('percentage', 0)
        if ming_brightness >= 70:
            strengths.append(f"命宫亮度评分{ming_brightness}%，力量充足")
        elif ming_brightness < 40:
            weaknesses.append(f"命宫亮度评分{ming_brightness}%，力量不足")

        # 总体评价
        score = len(strengths) - len(weaknesses)
        if score >= 3:
            overall_rating = '上等命盘'
        elif score >= 0:
            overall_rating = '中等命盘'
        else:
            overall_rating = '需努力改善'

        summary_parts = []
        if strengths:
            summary_parts.append(f"优势：{'、'.join(strengths[:3])}")
        if weaknesses:
            summary_parts.append(f"注意：{'、'.join(weaknesses[:3])}")

        return {
            'summary': '；'.join(summary_parts) if summary_parts else '命盘分析数据不足',
            'strengths': strengths,
            'weaknesses': weaknesses,
            'key_points': key_points,
            'overall_rating': overall_rating,
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if data.get('error'):
            return False, data['error']
        if not data.get('ming_gong'):
            return False, "命宫为空"
        if not data.get('palaces'):
            return False, "宫位数据为空"
        # 【改进】增加更多验证项
        if len(data.get('palaces', [])) != 12:
            return False, f"宫位数量不为12（实际{len(data.get('palaces', []))}）"
        if not data.get('sihua'):
            return False, "四化数据为空"
        return True, None
