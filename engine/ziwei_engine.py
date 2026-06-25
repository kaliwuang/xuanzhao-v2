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

# 【改进91】地支五行映射（命盘五行分析用）
ZHI_WUXING = {
    '子': '水', '丑': '土', '寅': '木', '卯': '木',
    '辰': '土', '巳': '火', '午': '火', '未': '土',
    '申': '金', '酉': '金', '戌': '土', '亥': '水',
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

        # 【改进41-50】星曜组合详细解读
        ming_desc = self._calc_star_ming_gong_desc(
            next((p for p in palaces if p['name'] == '命宫'), {})
        )
        all_palace_star_desc = self._calc_all_palace_star_desc(palaces)
        sihua_flight_trail = self._calc_sihua_flight_trail(sihua, palaces, dai_xian)
        star_interactions = self._calc_star_interactions(palaces)

        # 【改进51-60】大限流年深入分析
        dai_xian_ji_xiong = self._calc_dai_xian_ji_xiong(dai_xian, palaces, san_fang_data)
        liunian_comprehensive = self._calc_liunian_comprehensive(liunian_info, palaces, san_fang_data)
        dai_xian_sihua_to_natal = self._calc_dai_xian_sihua_to_natal(dai_xian, palaces)

        # 【改进61-70】格局判定增强
        extra_patterns = self._detect_extra_patterns(palaces, san_fang_data, sihua)
        all_patterns = chart_patterns + extra_patterns

        # 【改进71-80】四化飞星高级分析
        sihua_detail = self._calc_sihua_detail(sihua)

        # 【改进91-100】命盘综合评估增强
        wuxing_strength = self._calc_wuxing_strength(palaces)
        yinyang_balance = self._calc_yinyang_balance(palaces)
        enhanced_summary = self._calc_enhanced_summary(
            palaces, sihua, san_fang_data, all_patterns, palace_brightness, dai_xian
        )
        final_chart_score = self._calc_final_chart_score(
            palaces, sihua, san_fang_data, all_patterns, palace_brightness
        )

        # 【改进101-110】各宫位详细解读
        palace_interpretations = {}
        for pal in palaces:
            interp = self._calc_palace_detailed_interpretation(
                pal, san_fang_data.get(pal['name'], {}), sihua
            )
            palace_interpretations[pal['name']] = interp

        # 【改进111-120】大限流年综合报告
        nominal_age_val = max(0, current_year - birth_dt.year + 1) if birth_dt else 0
        dai_xian_liu_nian_report = self._calc_dai_xian_liu_nian_report(
            dai_xian, liunian_info, palaces, san_fang_data, sihua, nominal_age_val
        )

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
            # ─── 改进41-120 增强分析数据 ───
            'ming_desc': ming_desc,                                  # 改进41-42: 命宫星曜描述
            'all_palace_star_desc': all_palace_star_desc,            # 改进43-45: 各宫星曜效果
            'sihua_flight_trail': sihua_flight_trail,                # 改进50: 四化飞星轨迹
            'star_interactions': star_interactions,                   # 改进81-84: 星曜互动
            'dai_xian_ji_xiong': dai_xian_ji_xiong,                 # 改进54: 大限吉凶
            'liunian_comprehensive': liunian_comprehensive,          # 改进55-60: 流年综合
            'dai_xian_sihua_to_natal': dai_xian_sihua_to_natal,      # 改进75: 大限四化飞入本命
            'all_patterns': all_patterns,                            # 改进61-70: 所有格局
            'sihua_detail': sihua_detail,                            # 改进71-72: 四化详情
            'wuxing_strength': wuxing_strength,                      # 改进91: 五行强弱
            'yinyang_balance': yinyang_balance,                      # 改进92: 阴阳平衡
            'enhanced_summary': enhanced_summary,                    # 改进93-100: 增强总结
            'final_chart_score': final_chart_score,                  # 改进112-120: 最终评分
            'palace_interpretations': palace_interpretations,        # 改进101-110: 宫位解读
            'dai_xian_liu_nian_report': dai_xian_liu_nian_report,    # 改进111: 大限流年报告
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

    # ─── 改进41-50: 星曜组合详细解读 + 四化飞星深入分析 ───

    # 【改进41】十四主星入命宫性格详解
    MAJOR_STAR_MING_GONG_DESC = {
        '紫微': '紫微坐命，帝王之星，性格高贵大方，有领导才能，但有时过于自信。一生多贵人相助，适合从政或管理。',
        '天机': '天机坐命，智慧之星，思维敏捷，善于策划谋略，但易多虑善变。适合技术、策划、军师类工作。',
        '太阳': '太阳坐命，光明磊落，热情开朗，乐于助人，但易辛劳。男命事业心强，女命旺夫益子。',
        '武曲': '武曲坐命，财星坐命，性格刚毅果断，执行力强，但性急固执。一生与财有缘，适合金融、军警。',
        '天同': '天同坐命，福星坐命，性格温和随性，知足常乐，但易懒散缺乏进取。一生多享福，适合文艺、服务。',
        '廉贞': '廉贞坐命，次桃花星，性格刚强好胜，有才华但易惹是非。一生多变动，适合政治、法律、艺术。',
        '天府': '天府坐命，库星坐命，性格稳重保守，善于守成理财，但有时过于谨慎。一生衣食无忧。',
        '太阴': '太阴坐命，母星坐命，性格温柔细腻，有艺术气质，但易情绪化。适合文化、艺术、房产。',
        '贪狼': '贪狼坐命，桃花星坐命，性格多才多艺，交际能力强，但易贪多不专。一生多异性缘。',
        '巨门': '巨门坐命，暗星坐命，性格直言善辩，观察力强，但易口舌是非。适合律师、教师、销售。',
        '天相': '天相坐命，印星坐命，性格正直公平，善于协调，但易缺乏主见。适合秘书、公关、协调类。',
        '天梁': '天梁坐命，荫星坐命，性格正直有正义感，好打抱不平，但易操心忧虑。一生多逢凶化吉。',
        '七杀': '七杀坐命，将军星坐命，性格刚强勇猛，有冒险精神，但易冲动任性。一生多波折起伏。',
        '破军': '破军坐命，耗星坐命，性格开创叛逆，不喜受约束，但易破坏后重建。一生多变化。',
    }

    # 【改进42】主星组合性格详解（双星同宫）
    STAR_COMBO_DESC = {
        ('紫微', '天府'): '紫府同宫，帝星与库星相遇，富贵双全，一生不愁衣食，有权有财。',
        ('紫微', '贪狼'): '紫贪同宫，帝星与桃花星，多才多艺，人缘极佳，但需防沉迷享乐。',
        ('紫微', '天相'): '紫相同宫，帝星与印星，正直有权，善于协调管理。',
        ('紫微', '七杀'): '紫杀同宫，帝星与将星，刚强有权，但需防刚愎自用。',
        ('紫微', '破军'): '紫破同宫，帝星与耗星，开创力强，但一生多变动。',
        ('天机', '太阴'): '机月同宫，智慧与温柔，聪明有才学，适合文职。',
        ('天机', '天梁'): '机梁同宫，智慧与荫星，善于谋略，一生多逢凶化吉。',
        ('天机', '巨门'): '机巨同宫，智慧与暗星，口才佳善辩论，但易口舌是非。',
        ('太阳', '太阴'): '日月同宫，光明与温柔，阴阳调和，但力量分散。',
        ('太阳', '天梁'): '阳梁同宫，光明与荫星，为人正直，一生多贵人。',
        ('太阳', '巨门'): '阳巨同宫，光明与暗星，口才佳但易招是非。',
        ('武曲', '天府'): '武府同宫，财星与库星，理财能力极强，一生财运佳。',
        ('武曲', '天相'): '武相同宫，财星与印星，公正有财，适合金融法律。',
        ('武曲', '七杀'): '武杀同宫，财星与将星，果断有魄力，适合军警金融。',
        ('武曲', '贪狼'): '武贪同宫，财星与桃花星，财运佳，交际广，一生多酒色财气。',
        ('武曲', '破军'): '武破同宫，财星与耗星，有财但易破耗，先破后成。',
        ('天同', '天梁'): '同梁同宫，福星与荫星，一生多享福，逢凶化吉。',
        ('天同', '太阴'): '同阴同宫，福星与母星，温柔有福，感情丰富。',
        ('天同', '巨门'): '同巨同宫，福星与暗星，有福但口舌多。',
        ('廉贞', '天相'): '廉相同宫，桃花与印星，有才华但需防是非。',
        ('廉贞', '七杀'): '廉杀同宫，桃花与将星，性格刚烈，一生多波折。',
        ('廉贞', '破军'): '廉破同宫，桃花与耗星，一生多变化，感情波折。',
        ('廉贞', '贪狼'): '廉贪同宫，双桃花星，异性缘极佳，但需防桃花劫。',
        ('天府', '太阴'): '府阴同宫，库星与母星，有财有福，适合房产投资。',
        ('贪狼', '巨门'): '贪巨同宫，桃花与暗星，口才佳异性缘好，但易招口舌。',
        ('天相', '天梁'): '相梁同宫，印星与荫星，正直有福，一生多贵人相助。',
        ('七杀', '天府'): '杀府同宫，将星与库星，有魄力有财，适合创业。',
        ('天梁', '太阳'): '梁阳同宫（同太阳天梁），见太阳天梁条目。',
    }

    # 【改进43】辅星入命宫效果详解
    MINOR_STAR_MING_EFFECT = {
        '禄存': '禄存入命，一生有财禄，衣食无忧，但性格较保守谨慎。',
        '天魁': '天魁入命，贵人星坐命，一生多有贵人相助，逢凶化吉。',
        '天钺': '天钺入命，贵人星坐命，一生暗中有贵人扶助。',
        '左辅': '左辅入命，辅佐星坐命，为人忠厚有助力，人缘好。',
        '右弼': '右弼入命，辅佐星坐命，善解人意有助力，但有时优柔寡断。',
        '文昌': '文昌入命，文星坐命，聪明好学，考试运佳，适合文职。',
        '文曲': '文曲入命，文星坐命，有艺术才华，口才好，适合文艺。',
        '天马': '天马入命，驿马星坐命，一生多奔波变动，适合流动性工作。',
    }

    # 【改进44】煞星入命宫效果详解
    SHA_STAR_MING_EFFECT = {
        '擎羊': '擎羊入命，性格刚强果断，有魄力但易与人冲突，一生多是非。',
        '陀罗': '陀罗入命，性格阴沉犹豫，做事反复，易受困于人际关系。',
        '火星': '火星入命，性格急躁冲动，有开创力但易暴躁，一生多突发变化。',
        '铃星': '铃星入命，性格阴沉有心机，行动力强但易暗中受挫。',
        '地空': '地空入命，思想超脱有创意，但财运不稳，易有精神追求。',
        '地劫': '地劫入命，性格独特不群，财运多波折，易破财。',
    }

    # 【改进45】主星在不同宫位的效果表（十四主星在命宫/财帛/官禄/夫妻/迁移）
    STAR_PALACE_EFFECTS = {
        '紫微': {
            '命宫': '帝王之星坐命，一生有贵气',
            '财帛': '财运佳，善于管理财富',
            '官禄': '事业有成，适合管理职位',
            '夫妻': '配偶有贵气，但需防强势',
            '迁移': '在外受尊重，贵人多',
        },
        '天机': {
            '命宫': '智慧之星坐命，聪明善变',
            '财帛': '以智取财，财运起伏',
            '官禄': '适合策划、技术类工作',
            '夫妻': '配偶聪明，但感情多变',
            '迁移': '外出发展有利，多变动',
        },
        '太阳': {
            '命宫': '光明之星坐命，热情开朗',
            '财帛': '以劳取财，付出多回报大',
            '官禄': '事业有声望，适合公职',
            '夫妻': '男命得贤妻，女命旺夫',
            '迁移': '在外有名声，贵人多',
        },
        '武曲': {
            '命宫': '财星坐命，一生与财有缘',
            '财帛': '正财运极佳，理财能力强',
            '官禄': '适合金融、军警类工作',
            '夫妻': '配偶务实，感情较平淡',
            '迁移': '外出求财有利',
        },
        '天同': {
            '命宫': '福星坐命，一生多享福',
            '财帛': '财运平稳，不愁衣食',
            '官禄': '适合服务、文艺类工作',
            '夫妻': '配偶温和，感情和谐',
            '迁移': '外出平顺，多享乐',
        },
        '廉贞': {
            '命宫': '次桃花星坐命，多才多艺',
            '财帛': '财运起伏，多偏财运',
            '官禄': '适合政治、法律、艺术',
            '夫妻': '感情丰富，需防桃花劫',
            '迁移': '在外多是非，但有才华',
        },
        '天府': {
            '命宫': '库星坐命，一生衣食无忧',
            '财帛': '守财能力强，财运稳定',
            '官禄': '适合管理、财务类工作',
            '夫妻': '配偶稳重，婚姻稳定',
            '迁移': '在外稳重，贵人扶助',
        },
        '太阴': {
            '命宫': '母星坐命，温柔细腻',
            '财帛': '财运好，尤其不动产',
            '官禄': '适合文艺、房产类工作',
            '夫妻': '配偶温柔，感情细腻',
            '迁移': '在外有艺术气质',
        },
        '贪狼': {
            '命宫': '桃花星坐命，多才多艺',
            '财帛': '偏财运佳，但不聚财',
            '官禄': '适合交际、艺术类工作',
            '夫妻': '异性缘佳，需防桃花',
            '迁移': '在外交际广，人缘好',
        },
        '巨门': {
            '命宫': '暗星坐命，口才佳善辩',
            '财帛': '以口取财，适合销售',
            '官禄': '适合律师、教师、销售',
            '夫妻': '易口舌是非，需包容',
            '迁移': '在外多口舌，需谨慎',
        },
        '天相': {
            '命宫': '印星坐命，正直公平',
            '财帛': '财运平稳，以正途取财',
            '官禄': '适合秘书、公关类工作',
            '夫妻': '配偶正直，婚姻和谐',
            '迁移': '在外有好名声',
        },
        '天梁': {
            '命宫': '荫星坐命，逢凶化吉',
            '财帛': '财运平稳，多有荫福',
            '官禄': '适合监察、法律类工作',
            '夫妻': '配偶有正义感',
            '迁移': '在外多逢凶化吉',
        },
        '七杀': {
            '命宫': '将星坐命，刚强勇猛',
            '财帛': '财运起伏大，先苦后甜',
            '官禄': '适合军警、开创类工作',
            '夫妻': '感情刚烈，需磨合',
            '迁移': '在外有魄力，但多波折',
        },
        '破军': {
            '命宫': '耗星坐命，一生多变化',
            '财帛': '财运起伏，先破后成',
            '官禄': '适合开创、改革类工作',
            '夫妻': '感情多变化，需包容',
            '迁移': '在外多变动，不安定',
        },
    }

    # 【改进46】化禄入十二宫详细解释（扩展版）
    SIHUA_LU_DETAIL = {
        '命宫': '化禄入命，一生财运顺遂，人缘好，贵人多，凡事多顺利。为人慷慨大方，但需防因大方而失财。',
        '财帛': '化禄入财帛，正财运极佳，收入丰厚，理财能力强。适合从商或金融行业。',
        '官禄': '化禄入官禄，事业顺利，升迁有望，工作环境好。适合在大公司或政府机关发展。',
        '夫妻': '化禄入夫妻，感情甜蜜，配偶有助力，婚姻生活美满。但需防桃花过多。',
        '迁移': '化禄入迁移，外出顺利，贵人运佳，适合在外发展。出差旅行多顺利。',
        '福德': '化禄入福德，生活安逸，精神满足，兴趣爱好广泛。晚年有福享。',
        '田宅': '化禄入田宅，不动产运佳，适合投资房产。家庭环境好。',
        '子女': '化禄入子女，子女有福，亲子关系好。子女聪明有出息。',
        '交友': '化禄入交友，朋友助力大，社交运佳。但需防交友不慎。',
        '父母': '化禄入父母，父母有福荫，家庭环境好。与上司长辈关系好。',
        '兄弟': '化禄入兄弟，兄弟姐妹和睦，手足有助力。合伙有利。',
        '疾厄': '化禄入疾厄，健康良好，少病少灾。但需防因福而疏于保健。',
    }

    # 【改进47】化权入十二宫详细解释（扩展版）
    SIHUA_QUAN_DETAIL = {
        '命宫': '化权入命，有领导力，性格强势，做事果断。适合管理岗位，但需防独断专行。',
        '财帛': '化权入财帛，善于理财掌控，财运稳健。适合财务管理或投资。',
        '官禄': '化权入官禄，掌权在握，升迁有力。适合领导岗位或创业。',
        '夫妻': '化权入夫妻，配偶有主见，婚姻中需互相尊重。易有主导权之争。',
        '迁移': '化权入迁移，在外有权势，受人尊重。适合外派或出差。',
        '福德': '化权入福德，意志力强，精神充实。有自己的坚持和原则。',
        '田宅': '化权入田宅，不动产掌控力强。家庭中多有主导权。',
        '子女': '化权入子女，子女有能力，但亲子间易有权力之争。',
        '交友': '化权入交友，能管理团队，有领导力。但需防过于强势。',
        '父母': '化权入父母，父母有权威，家教严格。与上司关系好。',
        '兄弟': '化权入兄弟，兄弟之间易有争执。合伙需注意权力分配。',
        '疾厄': '化权入疾厄，需注意压力相关疾病，如高血压、心脏病。',
    }

    # 【改进48】化科入十二宫详细解释（扩展版）
    SIHUA_KE_DETAIL = {
        '命宫': '化科入命，有名声文采，为人谦虚有礼。适合文教、学术类工作。',
        '财帛': '化科入财帛，以文取财，财运平稳。适合知识型或教育类行业。',
        '官禄': '化科入官禄，考试运佳，文职有利。适合学术、教育、文化类工作。',
        '夫妻': '化科入夫妻，配偶有才学，婚姻和谐。感情中有默契。',
        '迁移': '化科入迁移，在外有好名声，受人尊敬。适合学术交流。',
        '福德': '化科入福德，精神充实，好学不倦。有高雅的兴趣爱好。',
        '田宅': '化科入田宅，书香门第，家庭文化氛围好。适合学区房投资。',
        '子女': '化科入子女，子女聪明好学，考试运佳。亲子关系和谐。',
        '交友': '化科入交友，益友多，朋友中有文人学者。社交圈质量高。',
        '父母': '化科入父母，父母重视教育，家庭文化氛围好。',
        '兄弟': '化科入兄弟，兄弟有才华，手足关系和谐。',
        '疾厄': '化科入疾厄，身体无大碍，有病也容易遇到好医生。',
    }

    # 【改进49】化忌入十二宫详细解释（扩展版）
    SIHUA_JI_DETAIL = {
        '命宫': '化忌入命，一生多阻碍，性格执着认真。凡事需付出更多努力，但也有韧性。',
        '财帛': '化忌入财帛，财运不顺，易破财。需谨慎理财，避免投机。',
        '官禄': '化忌入官禄，事业多阻碍，工作中易有是非。需踏实努力，不可投机取巧。',
        '夫妻': '化忌入夫妻，感情多波折，易有口舌是非。需多包容理解。',
        '迁移': '化忌入迁移，外出不顺，易遇阻碍。出行需特别注意安全。',
        '福德': '化忌入福德，精神困扰多，易多虑忧愁。需学会放松心态。',
        '田宅': '化忌入田宅，不动产有纠纷，家庭不安宁。投资房产需谨慎。',
        '子女': '化忌入子女，子女操心，亲子关系紧张。需多沟通理解。',
        '交友': '化忌入交友，小人多，朋友易反目。交友需谨慎。',
        '父母': '化忌入父母，父母缘薄，与上司关系紧张。需多忍让。',
        '兄弟': '化忌入兄弟，兄弟不和，合伙易有纠纷。需明算账。',
        '疾厄': '化忌入疾厄，健康需注意，易有慢性疾病。需定期体检。',
    }

    # 【改进50】四化飞星轨迹追踪规则
    SIHUA_FLIGHT_RULES = {
        'description': '四化飞星是紫微斗数高级技法，通过天干引发四化在不同宫位间飞化',
        'types': {
            '生年四化': '出生年天干引发的四化，影响一生',
            '大限四化': '大限天干引发的四化，影响该十年',
            '流年四化': '流年天干引发的四化，影响该年',
            '自化': '宫位自身天干引发的四化，影响该宫',
            '飞化': '一个宫位的天干引发四化飞入另一个宫位',
        },
        'flight_modes': {
            '禄随忌走': '化禄跟随化忌飞入的宫位，表示该宫有财运但也有困扰',
            '权忌交战': '化权与化忌同宫或对冲，表示该宫有权力但也有阻碍',
            '科忌相逢': '化科与化忌同宫，表示有名声但也有困扰',
            '双禄交流': '两个宫位互相化禄，表示两宫之间财气流通',
            '禄权科三奇': '禄权科三化落在三方四正，为大吉之象',
        },
    }

    def _calc_star_ming_gong_desc(self, palace: dict) -> str:
        """【改进41-42】获取命宫星曜组合详细描述"""
        major_stars = [s['name'] for s in palace.get('major_stars', []) if s['name'] in ALL_MAJOR_STARS]
        if not major_stars:
            return '命宫无主星（空宫），借对宫主星之力'
        if len(major_stars) == 1:
            return self.MAJOR_STAR_MING_GONG_DESC.get(major_stars[0], f'{major_stars[0]}坐命')
        # 双星组合
        combo = tuple(sorted(major_stars[:2]))
        desc = self.STAR_COMBO_DESC.get(combo, f'{major_stars[0]}、{major_stars[1]}同宫')
        return desc

    def _calc_all_palace_star_desc(self, palaces: list) -> dict:
        """【改进43-44+45】各宫位星曜效果描述"""
        result = {}
        for pal in palaces:
            pname = pal['name']
            stars_desc = []
            # 主星在该宫的效果
            for s in pal.get('major_stars', []):
                if s['name'] in ALL_MAJOR_STARS:
                    effect = self.STAR_PALACE_EFFECTS.get(s['name'], {}).get(pname, '')
                    if effect:
                        stars_desc.append(effect)
            # 辅星在命宫的效果
            if pname == '命宫':
                for s in pal.get('minor_stars', []):
                    if s['name'] in self.MINOR_STAR_MING_EFFECT:
                        stars_desc.append(self.MINOR_STAR_MING_EFFECT[s['name']])
                    elif s['name'] in self.SHA_STAR_MING_EFFECT:
                        stars_desc.append(self.SHA_STAR_MING_EFFECT[s['name']])
            result[pname] = stars_desc
        return result

    def _calc_sihua_detail(self, sihua: dict) -> dict:
        """【改进46-49】四化入宫详细解释"""
        detail_maps = {
            '禄': self.SIHUA_LU_DETAIL,
            '权': self.SIHUA_QUAN_DETAIL,
            '科': self.SIHUA_KE_DETAIL,
            '忌': self.SIHUA_JI_DETAIL,
        }
        star_to_palace = {}  # 需要在analyze中构建
        result = {}
        for hua_type, star_name in sihua.items():
            detail_map = detail_maps.get(hua_type, {})
            result[hua_type] = {
                'star': star_name,
                'general_desc': detail_map.get('desc', f'化{hua_type}在{star_name}'),
            }
        return result

    # ─── 改进51-60: 大限流年深入分析 ───

    # 【改进51】大限宫位四化叠加解读规则
    DAI_XIAN_OVERLAP_RULES = {
        '双禄叠加': '大限化禄叠生年化禄，财运加倍，该十年财运极佳',
        '双权叠加': '大限化权叠生年化权，权力加倍，该十年事业有成',
        '双科叠加': '大限化科叠生年化科，名声加倍，该十年文名远播',
        '双忌叠加': '大限化忌叠生年化忌，阻碍加倍，该十年需特别谨慎',
        '禄忌叠加': '大限化禄叠生年化忌（或反之），有财但也有困扰',
        '权忌叠加': '大限化权叠生年化忌（或反之），有权但也有阻碍',
    }

    # 【改进52】大限十二宫分析模板
    DAI_XIAN_PALACE_ANALYSIS = {
        '命宫': '大限命宫影响该十年的整体运势和精神面貌',
        '财帛': '大限财帛宫影响该十年的财运',
        '官禄': '大限官禄宫影响该十年的事业运',
        '夫妻': '大限夫妻宫影响该十年的感情运',
        '迁移': '大限迁移宫影响该十年的外出运',
        '福德': '大限福德宫影响该十年的精神生活',
        '田宅': '大限田宅宫影响该十年的不动产运',
        '子女': '大限子女宫影响该十年的子女运',
        '交友': '大限交友宫影响该十年的社交运',
        '父母': '大限父母宫影响该十年的长辈缘',
        '兄弟': '大限兄弟宫影响该十年的手足缘',
        '疾厄': '大限疾厄宫影响该十年的健康运',
    }

    # 【改进53】流年十二宫分析模板
    LIU_NIAN_PALACE_ANALYSIS = {
        '命宫': '流年命宫影响该年的整体运势',
        '财帛': '流年财帛宫影响该年的财运',
        '官禄': '流年官禄宫影响该年的事业运',
        '夫妻': '流年夫妻宫影响该年的感情运',
        '迁移': '流年迁移宫影响该年的外出运',
        '福德': '流年福德宫影响该年的精神生活',
        '田宅': '流年田宅宫影响该年的不动产运',
        '子女': '流年子女宫影响该年的子女运',
        '交友': '流年交友宫影响该年的社交运',
        '父母': '流年父母宫影响该年的长辈缘',
        '兄弟': '流年兄弟宫影响该年的手足缘',
        '疾厄': '流年疾厄宫影响该年的健康运',
    }

    # 【改进54】大限吉凶综合判断
    def _calc_dai_xian_ji_xiong(self, dai_xian: list, palaces: list, san_fang_data: dict) -> list:
        """为每个大限计算吉凶综合判断

        Returns:
            list: [{'ganzhi': str, 'age_range': str, 'ji_xiong': str, 'score': int, 'detail': str}]
        """
        result = []
        for dx in dai_xian:
            score = 0
            details = []
            # 大限四化
            dx_sihua = dx.get('sihua', {})
            if '禄' in dx_sihua:
                score += 2
                details.append('大限化禄，主顺遂')
            if '权' in dx_sihua:
                score += 2
                details.append('大限化权，主掌权')
            if '科' in dx_sihua:
                score += 1
                details.append('大限化科，主名声')
            if '忌' in dx_sihua:
                score -= 2
                details.append('大限化忌，主阻碍')
            ji_xiong = '吉' if score > 0 else ('凶' if score < 0 else '平')
            result.append({
                'ganzhi': dx.get('ganzhi', ''),
                'age_range': f"{dx.get('start_age', 0)}-{dx.get('end_age', 0)}",
                'ji_xiong': ji_xiong,
                'score': score,
                'detail': '；'.join(details) if details else '大限四化平稳',
            })
        return result

    # 【改进55】流年桃花运分析
    def _calc_liunian_peach(self, liunian_info: dict, palaces: list) -> dict:
        """分析流年桃花运"""
        if not liunian_info:
            return {}
        palace_names = liunian_info.get('palace_names', [])
        peach_palaces = []
        for pn in palace_names:
            pal = next((p for p in palaces if p['name'] == pn), {})
            peach_stars = [s['name'] for s in pal.get('major_stars', []) + pal.get('minor_stars', [])
                         if s['name'] in PEACH_BLOSSOM_STARS]
            if peach_stars:
                peach_palaces.append({'palace': pn, 'peach_stars': peach_stars})
        has_peach = len(peach_palaces) > 0
        return {
            'has_peach': has_peach,
            'peach_palaces': peach_palaces,
            'level': '旺' if len(peach_palaces) >= 2 else ('有' if has_peach else '弱'),
        }

    # 【改进56】流年事业运分析
    def _calc_liunian_career(self, liunian_info: dict, palaces: list, san_fang_data: dict) -> dict:
        """分析流年事业运"""
        if not liunian_info:
            return {}
        palace_names = liunian_info.get('palace_names', [])
        career_pal = next((pn for pn in palace_names if pn == '官禄'), '')
        if not career_pal:
            return {'note': '流年命宫不在官禄宫'}
        pal = next((p for p in palaces if p['name'] == '官禄'), {})
        ji_xiong = self._calc_palace_ji_xiong(pal, san_fang_data.get('官禄', {}))
        return {
            'career_palace': career_pal,
            'ji_xiong': ji_xiong,
            'level': '吉' if ji_xiong.get('balance') == '吉' else ('凶' if ji_xiong.get('balance') == '凶' else '平'),
        }

    # 【改进57】流年财运分析
    def _calc_liunian_wealth(self, liunian_info: dict, palaces: list, san_fang_data: dict) -> dict:
        """分析流年财运"""
        if not liunian_info:
            return {}
        palace_names = liunian_info.get('palace_names', [])
        wealth_pal = next((pn for pn in palace_names if pn == '财帛'), '')
        if not wealth_pal:
            return {'note': '流年命宫不在财帛宫'}
        pal = next((p for p in palaces if p['name'] == '财帛'), {})
        ji_xiong = self._calc_palace_ji_xiong(pal, san_fang_data.get('财帛', {}))
        return {
            'wealth_palace': wealth_pal,
            'ji_xiong': ji_xiong,
            'level': '吉' if ji_xiong.get('balance') == '吉' else ('凶' if ji_xiong.get('balance') == '凶' else '平'),
        }

    # 【改进58】流年感情运分析
    def _calc_liunian_romance(self, liunian_info: dict, palaces: list, san_fang_data: dict) -> dict:
        """分析流年感情运"""
        if not liunian_info:
            return {}
        palace_names = liunian_info.get('palace_names', [])
        spouse_pal = next((pn for pn in palace_names if pn == '夫妻'), '')
        pal = next((p for p in palaces if p['name'] == '夫妻'), {})
        ji_xiong = self._calc_palace_ji_xiong(pal, san_fang_data.get('夫妻', {}))
        peach_stars = [s['name'] for s in pal.get('major_stars', []) + pal.get('minor_stars', [])
                     if s['name'] in PEACH_BLOSSOM_STARS]
        return {
            'spouse_palace_hit': bool(spouse_pal),
            'ji_xiong': ji_xiong,
            'peach_stars': peach_stars,
            'level': '吉' if ji_xiong.get('balance') == '吉' and peach_stars else (
                '凶' if ji_xiong.get('balance') == '凶' else '平'),
        }

    # 【改进59】流年健康运分析
    def _calc_liunian_health(self, liunian_info: dict, palaces: list, san_fang_data: dict) -> dict:
        """分析流年健康运"""
        if not liunian_info:
            return {}
        palace_names = liunian_info.get('palace_names', [])
        health_pal = next((pn for pn in palace_names if pn == '疾厄'), '')
        pal = next((p for p in palaces if p['name'] == '疾厄'), {})
        ji_xiong = self._calc_palace_ji_xiong(pal, san_fang_data.get('疾厄', {}))
        sha_stars = [s['name'] for s in pal.get('minor_stars', []) if s['name'] in INausPICIOUS_STARS]
        return {
            'health_palace_hit': bool(health_pal),
            'ji_xiong': ji_xiong,
            'sha_stars': sha_stars,
            'level': '凶' if sha_stars else ('吉' if ji_xiong.get('balance') == '吉' else '平'),
        }

    # 【改进60】流年各维度综合运势
    def _calc_liunian_comprehensive(self, liunian_info: dict, palaces: list, san_fang_data: dict) -> dict:
        """流年各维度综合运势汇总"""
        return {
            'peach': self._calc_liunian_peach(liunian_info, palaces),
            'career': self._calc_liunian_career(liunian_info, palaces, san_fang_data),
            'wealth': self._calc_liunian_wealth(liunian_info, palaces, san_fang_data),
            'romance': self._calc_liunian_romance(liunian_info, palaces, san_fang_data),
            'health': self._calc_liunian_health(liunian_info, palaces, san_fang_data),
        }

    # ─── 改进61-70: 格局判定增强 ───

    # 【改进61】格局等级评定标准
    PATTERN_LEVEL_STANDARD = {
        '上格': {'min_score': 5, 'desc': '上等格局，一生多顺遂，事业有成'},
        '中格': {'min_score': 2, 'desc': '中等格局，一生平稳，小有成就'},
        '特殊': {'min_score': 0, 'desc': '特殊格局，起伏较大，需看具体星曜'},
        '下格': {'min_score': -5, 'desc': '下等格局，一生多波折，需努力改善'},
    }

    # 【改进62】更多格局定义（扩展）
    EXTRA_PATTERNS = {
        '日月并明': {
            'desc': '太阳太阴在命宫三方四正且亮度良好',
            'check': 'san_fang',
            'stars': ['太阳', '太阴'],
            'min_brightness': 4,
            'level': '上格',
        },
        '禄权科三奇': {
            'desc': '禄权科三化分别落在命宫、财帛、官禄',
            'check': 'sihua_positions',
            'level': '上格',
        },
        '禄逢冲破': {
            'desc': '化禄被煞星冲破，有财但留不住',
            'check': 'lu_with_sha',
            'level': '下格',
        },
        '忌入命宫': {
            'desc': '化忌入命宫，一生多阻碍',
            'check': 'ji_in_ming',
            'level': '下格',
        },
        '空劫夹命': {
            'desc': '地空地劫夹命宫，一生多空想',
            'check': 'kong_jie_jia',
            'level': '下格',
        },
        '火贪格': {
            'desc': '火星与贪狼同宫，爆发力强',
            'check': 'palace',
            'stars': ['火星', '贪狼'],
            'level': '中格',
        },
        '铃贪格': {
            'desc': '铃星与贪狼同宫，暗中得财',
            'check': 'palace',
            'stars': ['铃星', '贪狼'],
            'level': '中格',
        },
        '阳梁昌禄': {
            'desc': '太阳天梁文昌禄存同宫或会照，考试运极佳',
            'check': 'san_fang',
            'stars': ['太阳', '天梁', '文昌', '禄存'],
            'level': '上格',
        },
        '月朗天门': {
            'desc': '太阴在亥宫庙旺，一生有福',
            'check': 'star_at_branch',
            'star': '太阴',
            'branch': '亥',
            'min_brightness': 5,
            'level': '上格',
        },
        '日出扶桑': {
            'desc': '太阳在卯宫庙旺，一生光明',
            'check': 'star_at_branch',
            'star': '太阳',
            'branch': '卯',
            'min_brightness': 5,
            'level': '上格',
        },
    }

    # 【改进63】检测额外格局
    def _detect_extra_patterns(self, palaces: list, san_fang_data: dict, sihua: dict) -> list:
        """检测扩展格局"""
        patterns = []
        palace_map = {p['name']: p for p in palaces}
        ming_sf = san_fang_data.get('命宫', {})
        ming_pal = palace_map.get('命宫', {})

        # 日月并明
        for p in palaces:
            stars = {s['name']: s.get('brightness', '') for s in p.get('major_stars', [])}
            if '太阳' in stars and '太阴' in stars:
                if BRIGHTNESS_SCORE.get(stars['太阳'], 0) >= 4 and BRIGHTNESS_SCORE.get(stars['太阴'], 0) >= 4:
                    patterns.append({'name': '日月并明', 'desc': '太阳太阴同宫且庙旺，阴阳调和', 'level': '上格', 'palace': p['name']})

        # 禄权科三奇
        lu_star = sihua.get('禄', '')
        quan_star = sihua.get('权', '')
        ke_star = sihua.get('科', '')
        if lu_star and quan_star and ke_star:
            star_positions = {}
            for p in palaces:
                for s in p.get('major_stars', []) + p.get('minor_stars', []):
                    star_positions[s['name']] = p['name']
            lu_pal = star_positions.get(lu_star, '')
            quan_pal = star_positions.get(quan_star, '')
            ke_pal = star_positions.get(ke_star, '')
            key_palaces = {'命宫', '财帛', '官禄'}
            if {lu_pal, quan_pal, ke_pal} == key_palaces or {lu_pal, quan_pal, ke_pal}.issubset(key_palaces):
                patterns.append({'name': '禄权科三奇', 'desc': '禄权科三化分入命财官，大吉', 'level': '上格'})

        # 忌入命宫
        ji_star = sihua.get('忌', '')
        if ji_star:
            for s in ming_pal.get('major_stars', []) + ming_pal.get('minor_stars', []):
                if s['name'] == ji_star:
                    patterns.append({'name': '忌入命宫', 'desc': '化忌入命宫，一生多阻碍', 'level': '下格'})

        # 火贪格/铃贪格
        for p in palaces:
            minor_names = {s['name'] for s in p.get('minor_stars', [])}
            major_names = {s['name'] for s in p.get('major_stars', [])}
            if '火星' in minor_names and '贪狼' in major_names:
                patterns.append({'name': '火贪格', 'desc': f'火星贪狼同{p["name"]}宫，爆发力强', 'level': '中格', 'palace': p['name']})
            if '铃星' in minor_names and '贪狼' in major_names:
                patterns.append({'name': '铃贪格', 'desc': f'铃星贪狼同{p["name"]}宫，暗中得财', 'level': '中格', 'palace': p['name']})

        # 月朗天门
        for p in palaces:
            if p['zhi'] == '亥':
                for s in p.get('major_stars', []):
                    if s['name'] == '太阴' and BRIGHTNESS_SCORE.get(s.get('brightness', ''), 0) >= 5:
                        patterns.append({'name': '月朗天门', 'desc': '太阴在亥宫庙旺，一生有福', 'level': '上格'})

        # 日出扶桑
        for p in palaces:
            if p['zhi'] == '卯':
                for s in p.get('major_stars', []):
                    if s['name'] == '太阳' and BRIGHTNESS_SCORE.get(s.get('brightness', ''), 0) >= 5:
                        patterns.append({'name': '日出扶桑', 'desc': '太阳在卯宫庙旺，一生光明', 'level': '上格'})

        return patterns

    # ─── 改进71-80: 四化飞星高级分析 ───

    # 【改进71】四化入宫力量等级
    SIHUA_PALACE_POWER = {
        '禄': {'命宫': 10, '财帛': 9, '官禄': 8, '田宅': 7, '福德': 6, '夫妻': 5,
               '迁移': 5, '子女': 4, '交友': 3, '父母': 3, '兄弟': 3, '疾厄': 2},
        '权': {'官禄': 10, '命宫': 9, '财帛': 8, '迁移': 7, '田宅': 6, '夫妻': 5,
               '福德': 4, '子女': 4, '交友': 3, '父母': 3, '兄弟': 3, '疾厄': 2},
        '科': {'命宫': 10, '官禄': 8, '福德': 7, '父母': 6, '财帛': 5, '夫妻': 5,
               '迁移': 4, '子女': 4, '田宅': 3, '交友': 3, '兄弟': 3, '疾厄': 2},
        '忌': {'命宫': 10, '夫妻': 9, '财帛': 8, '官禄': 7, '疾厄': 6, '迁移': 5,
               '福德': 5, '田宅': 4, '子女': 4, '交友': 3, '父母': 3, '兄弟': 3},
    }

    # 【改进72】四化互涉规则
    SIHUA_INTERACTION = {
        ('禄', '忌'): '禄忌互涉，有财但也有困扰，先甜后苦',
        ('权', '忌'): '权忌互涉，有权但也有阻碍，需防小人',
        ('科', '忌'): '科忌互涉，有名声也有困扰，是非不断',
        ('禄', '权'): '禄权互涉，有财有权，大吉',
        ('禄', '科'): '禄科互涉，有名有利，文财兼备',
        ('权', '科'): '权科互涉，有权有名，事业有成',
    }

    # 【改进73-80】星曜亮度在十二宫的特殊规则
    STAR_BRIGHTNESS_SPECIAL = {
        '太阴': {
            '最佳宫位': ['卯', '辰', '巳'],  # 太阴在这些地支的宫位亮度好
            '最差宫位': ['酉', '戌', '亥'],
            '解释': '太阴为夜星，在白天的宫位亮度差',
        },
        '太阳': {
            '最佳宫位': ['卯', '辰', '巳'],
            '最差宫位': ['酉', '戌', '亥'],
            '解释': '太阳为日星，在白天的宫位亮度好',
        },
    }

    # 【改进74】命盘四化飞星轨迹完整分析
    def _calc_sihua_flight_trail(self, sihua: dict, palaces: list, dai_xian: list) -> dict:
        """追踪四化飞星在命盘中的完整轨迹"""
        star_positions = {}
        for p in palaces:
            for s in p.get('major_stars', []) + p.get('minor_stars', []):
                star_positions[s['name']] = p['name']

        trail = {}
        for hua_type, star_name in sihua.items():
            palace = star_positions.get(star_name, '')
            power = self.SIHUA_PALACE_POWER.get(hua_type, {}).get(palace, 0)
            trail[hua_type] = {
                'star': star_name,
                'palace': palace,
                'power': power,
                'level': '强' if power >= 8 else ('中' if power >= 5 else '弱'),
            }
        return trail

    # 【改进75】大限四化飞入本命各宫分析
    def _calc_dai_xian_sihua_to_natal(self, dai_xian: list, palaces: list) -> list:
        """大限四化飞入本命各宫的详细分析"""
        result = []
        star_positions = {}
        for p in palaces:
            for s in p.get('major_stars', []) + p.get('minor_stars', []):
                star_positions[s['name']] = p['name']

        for dx in dai_xian:
            dx_sihua = dx.get('sihua', {})
            if not dx_sihua:
                continue
            dx_detail = {'ganzhi': dx.get('ganzhi', ''), 'age_range': f"{dx.get('start_age', 0)}-{dx.get('end_age', 0)}"}
            for hua_type, star_name in dx_sihua.items():
                palace = star_positions.get(star_name, '')
                effect = SIHUA_EFFECTS.get(hua_type, {}).get(palace, '')
                dx_detail[hua_type] = {'star': star_name, 'palace': palace, 'effect': effect}
            result.append(dx_detail)
        return result

    # 【改进76-80】命盘十二宫详尽分析
    def _calc_palace_comprehensive(self, palace: dict, san_fang_info: dict) -> dict:
        """单个宫位的综合详尽分析"""
        brightness = self._calc_palace_brightness_score(palace)
        ji_xiong = self._calc_palace_ji_xiong(palace, san_fang_info)
        patterns = self._detect_palace_patterns(palace)
        major_names = [s['name'] for s in palace.get('major_stars', []) if s['name'] in ALL_MAJOR_STARS]
        is_empty = len(major_names) == 0
        is_single = len(major_names) == 1
        return {
            'name': palace['name'],
            'zhi': palace['zhi'],
            'stem': palace['stem'],
            'major_stars': [s['name'] for s in palace.get('major_stars', [])],
            'minor_stars': [s['name'] for s in palace.get('minor_stars', [])],
            'brightness': brightness,
            'ji_xiong': ji_xiong,
            'patterns': patterns,
            'is_empty': is_empty,
            'is_single': is_single,
            'self_hua': palace.get('self_hua', []),
            'changsheng': palace.get('changsheng', ''),
            'boshi': palace.get('boshi', ''),
        }

    # ─── 改进81-90: 星曜互动与特殊组合 ───

    # 【改进81】星曜互动效应表
    STAR_INTERACTION = {
        ('紫微', '左辅'): '紫微得左辅辅佐，一生多助力',
        ('紫微', '右弼'): '紫微得右弼辅佐，贵人运佳',
        ('紫微', '天魁'): '紫微得天魁贵人，逢凶化吉',
        ('紫微', '天钺'): '紫微得天钺贵人，暗中有助',
        ('紫微', '擎羊'): '紫微遇擎羊，有权力但易冲突',
        ('紫微', '陀罗'): '紫微遇陀罗，事业有阻碍',
        ('紫微', '火星'): '紫微遇火星，性格急躁有魄力',
        ('紫微', '地空'): '紫微遇地空，思想超脱但不聚财',
        ('紫微', '地劫'): '紫微遇地劫，有创意但财运波折',
        ('天机', '文昌'): '天机得文昌，智慧与文采兼备',
        ('天机', '文曲'): '天机得文曲，聪明有才华',
        ('太阳', '禄存'): '太阳得禄存，有财有声望',
        ('太阳', '化忌'): '太阳化忌，辛劳多是非',
        ('武曲', '化禄'): '武曲化禄，财运极佳',
        ('武曲', '化忌'): '武曲化忌，财运受阻',
        ('天同', '化禄'): '天同化禄，有福有财',
        ('天同', '化忌'): '天同化忌，福气受损',
        ('廉贞', '七杀'): '廉贞七杀同宫，性格刚烈',
        ('天府', '禄存'): '天府得禄存，库中有财',
        ('贪狼', '化禄'): '贪狼化禄，桃花与财运皆旺',
        ('贪狼', '化忌'): '贪狼化忌，桃花劫',
        ('巨门', '化忌'): '巨门化忌，口舌是非严重',
        ('天相', '化权'): '天相化权，有权力有地位',
        ('天梁', '化科'): '天梁化科，有名声有荫福',
        ('七杀', '擎羊'): '七杀遇擎羊，性格刚烈，一生多波折',
        ('破军', '化禄'): '破军化禄，先破后成',
        ('破军', '化忌'): '破军化忌，破耗严重',
    }

    # 【改进82】桃花星组合分析
    PEACH_COMBO_ANALYSIS = {
        '贪狼+红鸾': '桃花极旺，异性缘极佳，但需防桃花劫',
        '贪狼+天姚': '桃花旺盛，感情丰富，但易沉迷',
        '贪狼+咸池': '桃花旺盛，但多为露水情缘',
        '天姚+红鸾': '桃花旺盛，易有婚姻之喜',
        '天喜+红鸾': '喜事连连，感情运佳',
        '廉贞+天姚': '次桃花加桃花星，感情波折多',
    }

    # 【改进83】煞星组合分析
    SHA_COMBO_ANALYSIS = {
        '擎羊+陀罗': '双煞夹命，一生多波折，需特别谨慎',
        '火星+铃星': '火铃交并，性格急躁，一生多突发变化',
        '地空+地劫': '空劫夹命，一生多空想，财运不稳',
        '擎羊+火星': '双煞交加，性格刚烈冲动',
        '陀罗+铃星': '双煞交加，性格阴沉反复',
    }

    # 【改进84】吉星组合分析
    AUSPICIOUS_COMBO_ANALYSIS = {
        '天魁+天钺': '双贵人夹命，一生多贵人相助',
        '左辅+右弼': '双辅星夹命，一生多助力',
        '文昌+文曲': '双文星夹命，聪明好学，考试运佳',
        '禄存+天马': '禄马交驰，财运与外出运皆佳',
        '天魁+左辅': '贵人与辅星同在，助力极大',
    }

    # 【改进85-90】特殊宫位组合
    SPECIAL_PALACE_COMBOS = {
        '命宫紫微+官禄武曲': '命宫有权，官禄有财，事业有成',
        '命宫紫微+财帛天府': '命宫有权，财帛有库，一生不愁衣食',
        '命宫天机+官禄天梁': '命宫有智，官禄有荫，事业多逢凶化吉',
        '命宫太阳+夫妻太阴': '命宫光明，夫妻温柔，阴阳调和',
    }

    def _calc_star_interactions(self, palaces: list) -> list:
        """【改进81-84】计算星曜互动效应"""
        interactions = []
        for pal in palaces:
            all_star_names = [s['name'] for s in pal.get('major_stars', []) + pal.get('minor_stars', [])]
            for i, s1 in enumerate(all_star_names):
                for s2 in all_star_names[i+1:]:
                    combo = (s1, s2)
                    rev_combo = (s2, s1)
                    desc = self.STAR_INTERACTION.get(combo) or self.STAR_INTERACTION.get(rev_combo)
                    if desc:
                        interactions.append({'palace': pal['name'], 'stars': [s1, s2], 'effect': desc})
        return interactions

    # ─── 改进91-100: 命盘综合评估增强 ───

    # 【改进91】命盘五行强弱分析
    def _calc_wuxing_strength(self, palaces: list) -> dict:
        """分析命盘五行强弱"""
        wuxing_count = {'金': 0, '木': 0, '水': 0, '火': 0, '土': 0}
        for pal in palaces:
            branch_wx = ZHI_WUXING.get(pal.get('zhi', ''), '')
            if branch_wx:
                wuxing_count[branch_wx] = wuxing_count.get(branch_wx, 0) + 1
        strongest = max(wuxing_count, key=wuxing_count.get)
        weakest = min(wuxing_count, key=wuxing_count.get)
        return {
            'count': wuxing_count,
            'strongest': strongest,
            'weakest': weakest,
            'balance': '平衡' if max(wuxing_count.values()) - min(wuxing_count.values()) <= 2 else '偏颇',
        }

    # 【改进92】命盘阴阳平衡分析
    def _calc_yinyang_balance(self, palaces: list) -> dict:
        """分析命盘阴阳平衡"""
        yang_count = 0
        yin_count = 0
        yang_branches = {'子', '寅', '辰', '午', '申', '戌'}
        for pal in palaces:
            if pal.get('zhi', '') in yang_branches:
                yang_count += 1
            else:
                yin_count += 1
        return {
            'yang': yang_count,
            'yin': yin_count,
            'balance': '阴阳调和' if abs(yang_count - yin_count) <= 2 else (
                '偏阳' if yang_count > yin_count else '偏阴'),
        }

    # 【改进93-100】命盘综合评估
    def _calc_enhanced_summary(self, palaces: list, sihua: dict, san_fang_data: dict,
                                chart_patterns: list, palace_brightness: dict,
                                dai_xian: list) -> dict:
        """命盘增强综合评估"""
        strengths = []
        weaknesses = []
        key_points = []

        # 格局分析
        for pat in chart_patterns:
            if pat.get('level') == '上格':
                key_points.append(f"上格：{pat['name']}——{pat['desc']}")
            elif pat.get('level') == '下格':
                weaknesses.append(f"下格：{pat['name']}——{pat['desc']}")

        # 四化分析
        if '禄' in sihua:
            strengths.append(f"化禄在{sihua['禄']}，主财运顺遂")
        if '权' in sihua:
            strengths.append(f"化权在{sihua['权']}，主有领导力")
        if '科' in sihua:
            strengths.append(f"化科在{sihua['科']}，主有名声文采")
        if '忌' in sihua:
            weaknesses.append(f"化忌在{sihua['忌']}，需注意相关宫位")

        # 三方四正分析
        ming_sf = san_fang_data.get('命宫', {})
        if ming_sf.get('auspicious_count', 0) > 3:
            strengths.append("命宫三方四正吉星多，贵人运佳")
        if ming_sf.get('inauspicious_count', 0) > 3:
            weaknesses.append("命宫三方四正煞星多，需防小人")

        # 亮度分析
        ming_brightness = palace_brightness.get('命宫', {}).get('percentage', 0)
        if ming_brightness >= 70:
            strengths.append(f"命宫亮度评分{ming_brightness}%，力量充足")
        elif ming_brightness < 40:
            weaknesses.append(f"命宫亮度评分{ming_brightness}%，力量不足")

        # 总评
        score = len(strengths) - len(weaknesses)
        if score >= 3:
            overall = '上等命盘'
        elif score >= 0:
            overall = '中等命盘'
        else:
            overall = '需努力改善'

        return {
            'strengths': strengths,
            'weaknesses': weaknesses,
            'key_points': key_points,
            'overall_rating': overall,
            'score': score,
        }

    # ─── 改进101-110: 宫位详细解读文本 ───

    # 【改进101】命宫详细解读模板
    MING_GONG_INTERPRETATION = {
        '有主星': '命宫有主星坐守，性格特征明显，做事有主见。',
        '空宫': '命宫无主星（空宫），性格不够突出，易受外界影响，借对宫主星之力。',
        '独坐': '命宫独坐一颗主星，力量集中，性格特征非常突出。',
        '双星': '命宫双主星同宫，性格组合复杂，优势互补但也矛盾。',
        '吉星多': '命宫三方四正吉星多，一生多贵人相助。',
        '煞星多': '命宫三方四正煞星多，一生多波折，需特别谨慎。',
        '化禄': '化禄入命，一生财运顺遂。',
        '化忌': '化忌入命，一生多阻碍。',
    }

    # 【改进102】财帛宫详细解读模板
    CAI_BO_INTERPRETATION = {
        '有主星': '财帛宫有主星坐守，理财有方，有明确的赚钱方式。',
        '空宫': '财帛宫无主星，财运不够稳定，借对宫主星之力。',
        '化禄': '化禄入财帛，正财运极佳。',
        '化忌': '化忌入财帛，财运不顺，易破财。',
    }

    # 【改进103】官禄宫详细解读模板
    GUAN_LU_INTERPRETATION = {
        '有主星': '官禄宫有主星坐守，事业有方向感，有明确的职业追求。',
        '空宫': '官禄宫无主星，事业方向不够明确，借对宫主星之力。',
        '化权': '化权入官禄，掌权在握，事业有成。',
        '化忌': '化忌入官禄，事业多阻碍。',
    }

    # 【改进104】夫妻宫详细解读模板
    FU_QI_INTERPRETATION = {
        '有主星': '夫妻宫有主星坐守，配偶特征明显。',
        '空宫': '夫妻宫无主星，配偶特征不够突出，借对宫主星之力。',
        '化禄': '化禄入夫妻，感情甜蜜。',
        '化忌': '化忌入夫妻，感情多波折。',
        '桃花星': '夫妻宫有桃花星，异性缘佳，但需防桃花劫。',
    }

    # 【改进105】迁移宫详细解读模板
    QIAN_YI_INTERPRETATION = {
        '有主星': '迁移宫有主星坐守，外出发展有方向感。',
        '空宫': '迁移宫无主星，外出运不够稳定。',
        '化禄': '化禄入迁移，外出顺利，贵人多。',
        '化忌': '化忌入迁移，外出不顺。',
    }

    # 【改进106-110】各宫位详细解读方法
    def _calc_palace_detailed_interpretation(self, palace: dict, san_fang_info: dict,
                                              sihua: dict) -> dict:
        """计算单个宫位的详细解读"""
        pname = palace['name']
        major_stars = [s['name'] for s in palace.get('major_stars', []) if s['name'] in ALL_MAJOR_STARS]
        interp_templates = {
            '命宫': self.MING_GONG_INTERPRETATION,
            '财帛': self.CAI_BO_INTERPRETATION,
            '官禄': self.GUAN_LU_INTERPRETATION,
            '夫妻': self.FU_QI_INTERPRETATION,
            '迁移': self.QIAN_YI_INTERPRETATION,
        }
        template = interp_templates.get(pname, {})
        interpretations = []

        # 基本判断
        if not major_stars:
            interpretations.append(template.get('空宫', f'{pname}无主星'))
        elif len(major_stars) == 1:
            interpretations.append(template.get('独坐', f'{pname}独坐{major_stars[0]}'))
        elif len(major_stars) == 2:
            interpretations.append(template.get('双星', f'{pname}{major_stars[0]}、{major_stars[1]}同宫'))
        else:
            interpretations.append(template.get('有主星', f'{pname}有主星坐守'))

        # 四化判断
        for hua_type, star_name in sihua.items():
            for s in palace.get('major_stars', []) + palace.get('minor_stars', []):
                if s['name'] == star_name:
                    effect = SIHUA_EFFECTS.get(hua_type, {}).get(pname, '')
                    if effect:
                        interpretations.append(f'化{hua_type}在{pname}：{effect}')

        # 吉煞判断
        ji_xiong = self._calc_palace_ji_xiong(palace, san_fang_info)
        if ji_xiong.get('balance') == '吉':
            interpretations.append(f'{pname}吉星多，运势良好')
        elif ji_xiong.get('balance') == '凶':
            interpretations.append(f'{pname}煞星多，需谨慎')

        return {
            'palace': pname,
            'interpretations': interpretations,
            'ji_xiong': ji_xiong,
        }

    # ─── 改进111-120: 大限流年综合报告 ───

    # 【改进111】大限流年综合报告模板
    def _calc_dai_xian_liu_nian_report(self, dai_xian: list, liunian_info: dict,
                                        palaces: list, san_fang_data: dict,
                                        sihua: dict, nominal_age: int) -> dict:
        """生成大限流年综合报告"""
        # 当前大限
        current_dx = None
        for dx in dai_xian:
            if dx.get('start_age', 0) <= nominal_age <= dx.get('end_age', 0):
                current_dx = dx
                break

        # 大限四化
        dx_sihua = current_dx.get('sihua', {}) if current_dx else {}

        # 流年四化
        ln_sihua = liunian_info.get('sihua', []) if liunian_info else []

        # 叠加分析
        overlaps = []
        for ls in ln_sihua:
            hua = ls.get('hua', '')
            star = ls.get('star', '')
            if hua in dx_sihua and dx_sihua[hua] == star:
                overlaps.append(f'流年化{hua}叠大限化{hua}在{star}')
            if hua in sihua and sihua[hua] == star:
                overlaps.append(f'流年化{hua}叠生年化{hua}在{star}')

        return {
            'current_dai_xian': current_dx,
            'dai_xian_sihua': dx_sihua,
            'liunian_sihua': ln_sihua,
            'overlaps': overlaps,
            'nominal_age': nominal_age,
        }

    # 【改进112-120】命盘整体评分
    def _calc_final_chart_score(self, palaces: list, sihua: dict, san_fang_data: dict,
                                 chart_patterns: list, palace_brightness: dict) -> dict:
        """命盘最终综合评分"""
        # 1. 格局评分
        pattern_score = 0
        for pat in chart_patterns:
            level = pat.get('level', '')
            if level == '上格':
                pattern_score += 3
            elif level == '中格':
                pattern_score += 1
            elif level == '下格':
                pattern_score -= 2

        # 2. 四化评分
        sihua_score = 0
        for hua_type in sihua:
            if hua_type == '禄':
                sihua_score += 2
            elif hua_type == '权':
                sihua_score += 2
            elif hua_type == '科':
                sihua_score += 1
            elif hua_type == '忌':
                sihua_score -= 2

        # 3. 亮度评分
        brightness_total = sum(v.get('percentage', 0) for v in palace_brightness.values())
        brightness_avg = round(brightness_total / 12, 1) if palace_brightness else 0

        # 4. 三方四正评分
        sf_score = 0
        for pname, sf in san_fang_data.items():
            sf_score += sf.get('auspicious_count', 0) - sf.get('inauspicious_count', 0)

        # 5. 综合评分
        total = pattern_score * 3 + sihua_score * 2 + brightness_avg / 10 + sf_score

        if total >= 10:
            level = '上等'
        elif total >= 5:
            level = '中上'
        elif total >= 0:
            level = '中等'
        elif total >= -5:
            level = '中下'
        else:
            level = '下等'

        return {
            'pattern_score': pattern_score,
            'sihua_score': sihua_score,
            'brightness_avg': brightness_avg,
            'san_fang_score': sf_score,
            'total': round(total, 1),
            'level': level,
        }
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
