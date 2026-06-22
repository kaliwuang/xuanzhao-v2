#!/usr/bin/env python3
"""
玄照 v2.0 - 八字引擎

基于 lunar-python，封装真太阳时修正、早晚子时处理、特征提取。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from .udm import Pillar, SHISHEN_MAP, ZHI_CANGGAN, GAN_WUXING, ZHI_LIUHE as ZHI_HE_MOD, ZHI_CHONG as ZHI_CHONG_MOD, WUXING_CHARS

# 五行有序列表（纳音解析用，替代 WUXING_CHARS 集合的非确定性迭代顺序）
WUXING_ORDERED = ['金', '木', '水', '火', '土']
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
from typing import Optional, Dict

# 六十甲子纳音表
NAYIN_TABLE = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "炉中火", "丁卯": "炉中火",
    "戊辰": "大林木", "己巳": "大林木", "庚午": "路旁土", "辛未": "路旁土",
    "壬申": "剑锋金", "癸酉": "剑锋金", "甲戌": "山头火", "乙亥": "山头火",
    "丙子": "涧下水", "丁丑": "涧下水", "戊寅": "城头土", "己卯": "城头土",
    "庚辰": "白蜡金", "辛巳": "白蜡金", "壬午": "杨柳木", "癸未": "杨柳木",
    "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹雳火", "己丑": "霹雳火", "庚寅": "松柏木", "辛卯": "松柏木",
    "壬辰": "长流水", "癸巳": "长流水", "甲午": "沙中金", "乙未": "沙中金",
    "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金",
    "甲辰": "覆灯火", "乙巳": "覆灯火", "丙午": "天河水", "丁未": "天河水",
    "戊申": "大驿土", "己酉": "大驿土", "庚戌": "钗钏金", "辛亥": "钗钏金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水",
    "丙辰": "沙中土", "丁巳": "沙中土", "戊午": "天上火", "己未": "天上火",
    "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水",
}

# 地支藏干传统排序表（本气→中气→余气）
TRADITIONAL_HIDE_GAN = {
    '子': '癸', '丑': '己癸辛', '寅': '甲丙戊', '卯': '乙',
    '辰': '戊乙癸', '巳': '丙戊庚', '午': '丁己',
    '未': '己丁乙', '申': '庚壬戊', '酉': '辛',
    '戌': '戊辛丁', '亥': '壬甲',
}

# 长生十二宫
CHANGSHENG_ORDER = ['长生','沐浴','冠带','临官','帝旺','衰','病','死','墓','绝','胎','养']
CHANGSHENG_START = {'甲':'亥','丙':'寅','戊':'寅','庚':'巳','壬':'申','乙':'午','丁':'酉','己':'酉','辛':'子','癸':'卯'}
DI_ZHI = '子丑寅卯辰巳午未申酉戌亥'
TIANGAN_CYCLE = '甲乙丙丁戊己庚辛壬癸'

# 天干五行（字符串形式，从udm.GAN_WUXING派生）
GAN_WUXING_STR = {k: v[0].value for k, v in GAN_WUXING.items()}

# ─── 神煞查表（模块级常量，消除重复定义）──────────────────
SHENSHA_TIANYI_MAP = {
    '甲': ['丑','未'], '戊': ['丑','未'], '庚': ['丑','未'],
    '乙': ['子','申'], '己': ['子','申'],
    '丙': ['亥','酉'], '丁': ['亥','酉'],
    '辛': ['午','寅'],
    '壬': ['卯','巳'], '癸': ['卯','巳'],
}
SHENSHA_HUAGAI_MAP = {
    '子':'辰','丑':'丑','寅':'戌','卯':'未','辰':'辰','巳':'丑',
    '午':'戌','未':'未','申':'辰','酉':'丑','戌':'戌','亥':'未',
}
SHENSHA_YIMA_MAP = {
    '子':'寅','丑':'亥','寅':'申','卯':'巳','辰':'寅','巳':'亥',
    '午':'申','未':'巳','申':'寅','酉':'亥','戌':'申','亥':'巳',
}
SHENSHA_TAOHUA_MAP = {
    '子':'酉','丑':'午','寅':'卯','卯':'子','辰':'酉','巳':'午',
    '午':'卯','未':'子','申':'酉','酉':'午','戌':'卯','亥':'子',
}
SHENSHA_WENCHANG_MAP = {
    '甲':'巳','乙':'午','丙':'申','丁':'酉','戊':'申','己':'酉',
    '庚':'亥','辛':'子','壬':'寅','癸':'卯',
}
SHENSHA_LU_MAP = {
    '甲':'寅','乙':'卯','丙':'巳','丁':'午','戊':'巳','己':'午',
    '庚':'申','辛':'酉','壬':'亥','癸':'子',
}
SHENSHA_HONGLUAN_MAP = {
    '子':'卯','丑':'寅','寅':'丑','卯':'子','辰':'亥','巳':'戌',
    '午':'酉','未':'申','申':'未','酉':'午','戌':'巳','亥':'辰',
}
SHENSHA_TIANXI_MAP = {
    '子':'酉','丑':'申','寅':'未','卯':'午','辰':'巳','巳':'辰',
    '午':'卯','未':'寅','申':'丑','酉':'子','戌':'亥','亥':'戌',
}
SHENSHA_TAIJI_MAP = {
    '甲':['子','午'],'乙':['子','午'],'丙':['卯','酉'],'丁':['卯','酉'],
    '戊':['辰','戌','丑','未'],'己':['辰','戌','丑','未'],
    '庚':['寅','亥'],'辛':['寅','亥'],'壬':['巳','申'],'癸':['巳','申'],
}
SHENSHA_YUEDE_MAP = {
    '子':'壬','丑':'庚','寅':'丙','卯':'甲','辰':'壬','巳':'庚',
    '午':'丙','未':'甲','申':'壬','酉':'庚','戌':'丙','亥':'甲',
}
SHENSHA_JIANGXING_MAP = {
    '子':'子','丑':'酉','寅':'午','卯':'卯','辰':'子','巳':'酉',
    '午':'午','未':'卯','申':'子','酉':'酉','戌':'午','亥':'卯',
}

# ─── 天德贵人（以月支查，值为天干或地支）─────────────────
# 传统口诀（《协纪辨方书》）: 正丁二坤中，三壬四辛同，五乾六甲上，七癸八艮逢，九丙十居乙，子巽丑庚中
# 正月寅→丁, 二月卯→坤(申), 三月辰→壬, 四月巳→辛, 五月午→乾(亥), 六月未→甲,
# 七月申→癸, 八月酉→艮(寅), 九月戌→丙, 十月亥→乙, 十一月子→巽(巳), 十二月丑→庚
SHENSHA_TIANDEREN_MAP = {
    '子':'巳','丑':'庚','寅':'丁','卯':'申',
    '辰':'壬','巳':'辛','午':'亥','未':'甲',
    '申':'癸','酉':'寅','戌':'丙','亥':'乙',
}

# ─── 红艳煞（以日干查）──────────────────────────────
SHENSHA_HONGYAN_MAP = {
    '甲':'午','乙':'申','丙':'寅','丁':'未',
    '戊':'辰','己':'未','庚':'戌','辛':'酉',
    '壬':'子','癸':'申',
}

# ─── 福星贵人（以日干查）──────────────────────────────
SHENSHA_FUXING_MAP = {
    '甲': ['寅'], '乙': ['丑'], '丙': ['子'],
    '丁': ['酉'], '戊': ['申'], '己': ['未'],
    '庚': ['午'], '辛': ['巳'], '壬': ['辰'], '癸': ['卯'],
}

# ─── 金舆（以日干查）────────────────────────────────
SHENSHA_JINYU_MAP = {
    '甲': ['辰'], '乙': ['巳'], '丙': ['未'], '丁': ['申'],
    '戊': ['未'], '己': ['申'], '庚': ['戌'], '辛': ['亥'],
    '壬': ['丑'], '癸': ['寅'],
}

# ─── 天赦（以月支所在季节查日柱）────────────────────
SHENSHA_TIANSHE_MAP = {
    '寅':'戊寅','卯':'戊寅','辰':'戊寅',
    '巳':'甲午','午':'甲午','未':'甲午',
    '申':'戊申','酉':'戊申','戌':'戊申',
    '亥':'甲子','子':'甲子','丑':'甲子',
}

# ─── 天医（以月支查）────────────────────────────────
SHENSHA_TIANYI_MEDICAL_MAP = {
    '子':'丑','丑':'寅','寅':'卯','卯':'辰',
    '辰':'巳','巳':'午','午':'未','未':'申',
    '申':'酉','酉':'戌','戌':'亥','亥':'子',
}

# ─── 天厨（以日干查）────────────────────────────────
SHENSHA_TIANCHU_MAP = {
    '甲':'巳','乙':'午','丙':'巳','丁':'午',
    '戊':'申','己':'酉','庚':'亥','辛':'子',
    '壬':'寅','癸':'卯',
}

# ─── 学堂（以日干查长生位）────────────────────────
SHENSHA_XUETANG_MAP = {
    '甲':'亥','乙':'午','丙':'寅','丁':'酉',
    '戊':'寅','己':'酉','庚':'巳','辛':'子',
    '壬':'申','癸':'卯',
}

# ─── 词馆（以日干查临官位）────────────────────────
SHENSHA_CIGUAN_MAP = {
    '甲':'寅','乙':'卯','丙':'巳','丁':'午',
    '戊':'巳','己':'午','庚':'申','辛':'酉',
    '壬':'亥','癸':'子',
}

# ─── 羊刃（以日干查，阳干帝旺位）──────────────────
SHENSHA_YANGREN_MAP = {
    '甲':'卯','丙':'午','戊':'午','庚':'酉','壬':'子',
}

# ─── 飞刃（以日干查，羊刃对冲）────────────────────
SHENSHA_FEIREN_MAP = {
    '甲':'酉','丙':'子','戊':'子','庚':'卯','壬':'午',
}

# ─── 流霞（以日干查）────────────────────────────────
SHENSHA_LIUXIA_MAP = {
    '甲':'酉','乙':'戌','丙':'未','丁':'申',
    '戊':'巳','己':'午','庚':'辰','辛':'卯',
    '壬':'亥','癸':'寅',
}

# ─── 亡神（以年支查三合局绝位）────────────────────
SHENSHA_WANGSHEN_MAP = {
    '子':'巳','丑':'寅','寅':'亥','卯':'申',
    '辰':'巳','巳':'寅','午':'亥','未':'申',
    '申':'巳','酉':'寅','戌':'亥','亥':'申',
}

# ─── 劫煞（以年支查三合局死位）────────────────────
SHENSHA_JIESHA_MAP = {
    '子':'卯','丑':'子','寅':'酉','卯':'午',
    '辰':'卯','巳':'子','午':'酉','未':'午',
    '申':'卯','酉':'子','戌':'酉','亥':'午',
}

# ─── 灾煞（以年支查将星对冲位）────────────────────
SHENSHA_ZAISHA_MAP = {
    '子':'午','丑':'卯','寅':'子','卯':'酉',
    '辰':'午','巳':'卯','午':'子','未':'酉',
    '申':'午','酉':'卯','戌':'子','亥':'酉',
}

# ─── 勾煞（以年支查）────────────────────────────────
SHENSHA_GOUSHA_MAP = {
    '子':'卯','丑':'辰','寅':'巳','卯':'午',
    '辰':'未','巳':'申','午':'酉','未':'戌',
    '申':'亥','酉':'子','戌':'丑','亥':'寅',
}

# ─── 绞煞（以年支查，勾煞对冲）────────────────────
SHENSHA_JIAOSHA_MAP = {
    '子':'酉','丑':'戌','寅':'亥','卯':'子',
    '辰':'丑','巳':'寅','午':'卯','未':'辰',
    '申':'巳','酉':'午','戌':'未','亥':'申',
}

# ─── 孤辰寡宿（以年支查）────────────────────────
SHENSHA_GUICHEN_MAP = {
    '子':'寅','丑':'寅','寅':'巳','卯':'巳',
    '辰':'巳','巳':'申','午':'申','未':'申',
    '申':'亥','酉':'亥','戌':'亥','亥':'寅',
}
SHENSHA_GUASU_MAP = {
    '子':'戌','丑':'戌','寅':'丑','卯':'丑',
    '辰':'丑','巳':'辰','午':'辰','未':'辰',
    '申':'未','酉':'未','戌':'未','亥':'戌',
}

# ─── 天官贵人（以日干查四支）────────────────────
SHENSHA_TIANGUAN_MAP = {
    '甲':'未','乙':'辰','丙':'巳','丁':'午',
    '戊':'戌','己':'酉','庚':'丑','辛':'寅',
    '壬':'卯','癸':'子',
}

# ─── 天福贵人（以日干查四支）────────────────────
SHENSHA_TIANFU_MAP = {
    '甲':'酉','乙':'申','丙':'子','丁':'亥',
    '戊':'卯','己':'寅','庚':'午','辛':'巳',
    '壬':'未','癸':'辰',
}

# ─── 德秀贵人（以月支查天干组合）────────────────
SHENSHA_DEXIU_MAP = {
    '子': {'德':'戊', '秀':'壬癸'},
    '丑': {'德':'戊', '秀':'壬癸'},
    '寅': {'德':'丙', '秀':'甲乙'},
    '卯': {'德':'丙', '秀':'甲乙'},
    '辰': {'德':'丙', '秀':'甲乙'},
    '巳': {'德':'庚', '秀':'丙丁'},
    '午': {'德':'庚', '秀':'丙丁'},
    '未': {'德':'庚', '秀':'丙丁'},
    '申': {'德':'甲', '秀':'庚辛'},
    '酉': {'德':'甲', '秀':'庚辛'},
    '戌': {'德':'甲', '秀':'庚辛'},
    '亥': {'德':'戊', '秀':'壬癸'},
}

# ─── 十恶大败（以日柱查）────────────────────────
SHIBA_EBA = frozenset(['甲辰','乙巳','丙申','丁亥','戊戌','己丑','庚辰','辛巳','壬申','癸亥'])

# ─── 四废（以月支所在季节查日柱）────────────────
SHENSHA_SIFEI_MAP = {
    '寅':frozenset(['庚申','辛酉']),'卯':frozenset(['庚申','辛酉']),'辰':frozenset(['庚申','辛酉']),
    '巳':frozenset(['壬子','癸亥']),'午':frozenset(['壬子','癸亥']),'未':frozenset(['壬子','癸亥']),
    '申':frozenset(['甲寅','乙卯']),'酉':frozenset(['甲寅','乙卯']),'戌':frozenset(['甲寅','乙卯']),
    '亥':frozenset(['丙午','丁未']),'子':frozenset(['丙午','丁未']),'丑':frozenset(['丙午','丁未']),
}

# ─── 阴阳差错（以日柱查）────────────────────────
YINYANG_CHACUO = frozenset([
    '丙子','丁丑','戊寅','辛卯','壬辰','癸巳',
    '丙午','丁未','戊申','辛酉','壬戌','癸亥'
])

# ─── 天转煞（以日柱纳音五行查）────────────────
SHENSHA_TIANZHUAN_MAP = {
    '金': '辛卯', '木': '癸巳', '水': '丁未', '火': '丙戌', '土': '己丑'
}
# ─── 六甲空亡（以日柱查）────────────────────────────
XUNKONG_MAP = {
    '甲子':'戌亥','甲戌':'申酉','甲申':'午未','甲午':'辰巳','甲辰':'寅卯','甲寅':'子丑',
    '乙丑':'戌亥','乙酉':'申酉','乙未':'午未','乙巳':'辰巳','乙卯':'寅卯','乙亥':'子丑',
    '丙寅':'戌亥','丙子':'申酉','丙戌':'午未','丙申':'辰巳','丙午':'寅卯','丙辰':'子丑',
    '丁卯':'戌亥','丁丑':'申酉','丁亥':'午未','丁酉':'辰巳','丁未':'寅卯','丁巳':'子丑',
    '戊辰':'戌亥','戊寅':'申酉','戊子':'午未','戊戌':'辰巳','戊申':'寅卯','戊午':'子丑',
    '己巳':'戌亥','己卯':'申酉','己丑':'午未','己亥':'辰巳','己酉':'寅卯','己未':'子丑',
    '庚午':'戌亥','庚辰':'申酉','庚寅':'午未','庚子':'辰巳','庚戌':'寅卯','庚申':'子丑',
    '辛未':'戌亥','辛巳':'申酉','辛卯':'午未','辛丑':'辰巳','辛亥':'寅卯','辛酉':'子丑',
    '壬申':'戌亥','壬午':'申酉','壬辰':'午未','壬寅':'辰巳','壬子':'寅卯','壬戌':'子丑',
    '癸酉':'戌亥','癸未':'申酉','癸巳':'午未','癸卯':'辰巳','癸丑':'寅卯','癸亥':'子丑',
}

# ─── 天干关系表（模块级常量）──────────────────────────
GAN_CHONG = {'甲':'庚','庚':'甲','乙':'辛','辛':'乙','丙':'壬','壬':'丙','丁':'癸','癸':'丁'}
GAN_HE = {'甲':'己','己':'甲','乙':'庚','庚':'乙','丙':'辛','辛':'丙','丁':'壬','壬':'丁','戊':'癸','癸':'戊'}
GAN_LIUHE = dict(GAN_HE)  # 天干六合（天德合、月德合复用此常量，独立副本防误改）
TIANGAN_SET = set('甲乙丙丁戊己庚辛壬癸')  # 天干集合（天德、天德合判断用）

# ─── 地支关系表（模块级常量）──────────────────────────
# ZHI_CHONG_MOD 和 ZHI_HE_MOD 已从 udm 导入（见上方 import）
ZHI_XING_MOD = {
    '子':'卯','卯':'子',           # 子卯刑（无礼之刑）
    '辰':'辰','午':'午','酉':'酉','亥':'亥',  # 自刑
    # 注意：寅巳申（无恩之刑）和丑戌未（恃势之刑）不在此表中，
    # 因为三刑需三支齐全才算，不可拆成两两判断（见下方 SAN_XING_CYCLES）
}
# 三刑循环组（需三支齐全才算刑，不可拆成两两判断）
SAN_XING_CYCLES = [
    frozenset({'寅', '巳', '申'}),  # 无恩之刑
    frozenset({'丑', '戌', '未'}),  # 恃势之刑
]
ZHI_HAI_MOD = {'子':'未','未':'子','丑':'午','午':'丑','寅':'巳','巳':'寅','卯':'辰','辰':'卯','申':'亥','亥':'申','酉':'戌','戌':'酉'}
ZHI_PO_MOD = {'子':'酉','酉':'子','丑':'辰','辰':'丑','寅':'亥','亥':'寅','卯':'午','午':'卯','巳':'申','申':'巳','未':'戌','戌':'未'}

# ─── 五行生克关系（模块级常量）──────────────────────
WUXING_KE = {'木':'土', '土':'水', '水':'火', '火':'金', '金':'木'}      # 我克=财
WUXING_SHENG = {'木':'火', '火':'土', '土':'金', '金':'水', '水':'木'}    # 我生=食伤
WUXING_BEI_KE = {'木':'金', '金':'火', '火':'水', '水':'土', '土':'木'}   # 克我=官杀
WUXING_BEI_SHENG = {v: k for k, v in WUXING_SHENG.items()}               # 生我=印

# ─── 地支三合/半合/三会（模块级常量，消除 _extract_features 内重复构建）───
SAN_HE_GROUPS = [
    (frozenset({'申', '子', '辰'}), '水', '申子辰'),
    (frozenset({'寅', '午', '戌'}), '火', '寅午戌'),
    (frozenset({'巳', '酉', '丑'}), '金', '巳酉丑'),
    (frozenset({'亥', '卯', '未'}), '木', '亥卯未'),
]
BAN_HE_PAIRS = {
    frozenset({'申', '子'}): ('水', '子'), frozenset({'子', '辰'}): ('水', '子'),
    frozenset({'申', '辰'}): ('水', '辰'),  # 子水缺位，水库半合
    frozenset({'寅', '午'}): ('火', '午'), frozenset({'午', '戌'}): ('火', '午'),
    frozenset({'寅', '戌'}): ('火', '戌'),
    frozenset({'巳', '酉'}): ('金', '酉'), frozenset({'酉', '丑'}): ('金', '酉'),
    frozenset({'巳', '丑'}): ('金', '丑'),
    frozenset({'亥', '卯'}): ('木', '卯'), frozenset({'卯', '未'}): ('木', '卯'),
    frozenset({'亥', '未'}): ('木', '未'),
}
SAN_HUI_GROUPS = [
    (frozenset({'寅', '卯', '辰'}), '木', '东方'),
    (frozenset({'巳', '午', '未'}), '火', '南方'),
    (frozenset({'申', '酉', '戌'}), '金', '西方'),
    (frozenset({'亥', '子', '丑'}), '水', '北方'),
]


class BaziEngine(DivinationEngine):
    """八字引擎"""

    MAX_BASE_FEATURES = 30  # 基础特征条数上限（25→30，避免复杂命盘丢失天干连珠/地支连珠等稀有特征）

    # 身强/身弱判定阈值（日主五行得分占比）
    STRONG_THRESHOLD = 0.40   # >=40% 为身强
    BALANCED_THRESHOLD = 0.25 # 25%-40% 为中和, <25% 为身弱

    @property
    def name(self) -> str:
        return "八字"

    @property
    def name_en(self) -> str:
        return "BaZi"

    @property
    def priority(self) -> int:
        return 1

    def __init__(self):
        self._available = False
        try:
            from lunar_python import Solar, EightChar
            self.Solar = Solar
            self.EightChar = EightChar
            self._available = True
        except ImportError:
            pass

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        if not self._available:
            return {"error": "lunar_python not installed"}

        # 使用真太阳时计算时柱（时辰应基于出生地的真太阳时）
        # 晚子时(23:xx)用次日日期+子时(hour=0)
        # 真太阳时 = 北京时间 + 经度修正 + 均时差
        dt = time.bazi_day_pillar_date
        hour = time.bazi_hour

        solar = self.Solar.fromYmdHms(
            dt.year, dt.month, dt.day,
            hour, time.true_solar.minute, 0
        )
        lunar = solar.getLunar()
        ec = self.EightChar(lunar)

        # 四柱
        year_pillar = Pillar(gan=ec.getYearGan(), zhi=ec.getYearZhi(), nayin=ec.getYearNaYin())
        month_pillar = Pillar(gan=ec.getMonthGan(), zhi=ec.getMonthZhi(), nayin=ec.getMonthNaYin())
        day_pillar = Pillar(gan=ec.getDayGan(), zhi=ec.getDayZhi(), nayin=ec.getDayNaYin())
        time_pillar = Pillar(gan=ec.getTimeGan(), zhi=ec.getTimeZhi(), nayin=ec.getTimeNaYin())

        day_master = ec.getDayGan()

        # 地支藏干传统排序表（本气→中气→余气）
        # lunar_python 对部分地支返回非传统顺序，需修正
        # NOTE: TRADITIONAL_HIDE_GAN is now a module-level constant

        def _fix_hide_gan(zhi: str, raw: str) -> list:
            """修正 lunar_python 藏干顺序为传统本气→中气→余气"""
            trad = TRADITIONAL_HIDE_GAN.get(zhi)
            if trad and len(trad) > 1:
                return list(trad)
            # 单藏干地支(子/卯/酉)：优先用lunar_python返回值，为空时回退到传统表
            if raw:
                return list(raw)
            return list(trad) if trad else []

        # 藏干（已修正顺序）
        raw_hidden = {
            "year": ec.getYearHideGan(),
            "month": ec.getMonthHideGan(),
            "day": ec.getDayHideGan(),
            "time": ec.getTimeHideGan(),
        }
        zhi_map = {
            "year": ec.getYearZhi(),
            "month": ec.getMonthZhi(),
            "day": ec.getDayZhi(),
            "time": ec.getTimeZhi(),
        }
        hidden_gans = {}
        for k in raw_hidden:
            hidden_gans[k] = _fix_hide_gan(zhi_map[k], raw_hidden[k])

        # 十神（按天干）
        shishen_gan = {
            "year": ec.getYearShiShenGan(),
            "month": ec.getMonthShiShenGan(),
            "day": "日元",
            "time": ec.getTimeShiShenGan(),
        }

        # 十神（按地支藏干）——使用导入的 SHISHEN_MAP（已含修正后藏干顺序）
        shishen_zhi = {}
        for k in hidden_gans:
            shishen_zhi[k] = [SHISHEN_MAP.get((day_master, g), '?') for g in hidden_gans[k]]

        # 纳音
        nayin = {
            "year": ec.getYearNaYin(),
            "month": ec.getMonthNaYin(),
            "day": ec.getDayNaYin(),
            "time": ec.getTimeNaYin(),
        }

        # 空亡
        xunkong = {
            "year": ec.getYearXunKong(),
            "month": ec.getMonthXunKong(),
            "day": ec.getDayXunKong(),
            "time": ec.getTimeXunKong(),
        }

        # 命宫·胎元·身宫
        ming_gong = ec.getMingGong()
        tai_yuan = ec.getTaiYuan()
        shen_gong = ec.getShenGong()

        # 长生十二宫计算（定义在大运之前，供大运使用）
        # NOTE: CHANGSHENG_ORDER, CHANGSHENG_START, DI_ZHI are now module-level constants

        def _calc_changsheng(dm: str, zhi: str) -> str:
            start = CHANGSHENG_START.get(dm)
            if not start or zhi not in DI_ZHI:
                return ''
            start_idx = DI_ZHI.index(start)
            zhi_idx = DI_ZHI.index(zhi)
            is_yang = dm in '甲丙戊庚壬'
            offset = (zhi_idx - start_idx) % 12 if is_yang else (start_idx - zhi_idx) % 12
            return CHANGSHENG_ORDER[offset]

        # ─── 大运/流年神煞辅助函数 ─────────────────────────
        # 给定一个地支(zhi)和天干(gan)，返回匹配的神煞名称列表
        # 复用于大运和流年，消除 ~60 行重复代码
        _year_zhi = year_pillar.zhi
        _day_zhi = day_pillar.zhi
        _month_zhi = month_pillar.zhi
        _year_gan = year_pillar.gan
        _yuede_gan = SHENSHA_YUEDE_MAP.get(_month_zhi, '')
        _tiande_val = SHENSHA_TIANDEREN_MAP.get(_month_zhi, '')
        _tiande_he = ''
        if _tiande_val:
            _tiande_he = GAN_LIUHE.get(_tiande_val, '') if _tiande_val in TIANGAN_SET else ZHI_HE_MOD.get(_tiande_val, '')
        _yuede_he = GAN_LIUHE.get(_yuede_gan, '')
        _huagai_targets = set(filter(None, [SHENSHA_HUAGAI_MAP.get(_year_zhi, ''), SHENSHA_HUAGAI_MAP.get(_day_zhi, '')]))
        _yima_targets = set(filter(None, [SHENSHA_YIMA_MAP.get(_year_zhi, ''), SHENSHA_YIMA_MAP.get(_day_zhi, '')]))
        _taohua_targets = set(filter(None, [SHENSHA_TAOHUA_MAP.get(_year_zhi, ''), SHENSHA_TAOHUA_MAP.get(_day_zhi, '')]))
        _hongluan_targets = set(filter(None, [SHENSHA_HONGLUAN_MAP.get(_year_zhi, ''), SHENSHA_HONGLUAN_MAP.get(_day_zhi, '')]))
        _tianxi_targets = set(filter(None, [SHENSHA_TIANXI_MAP.get(_year_zhi, ''), SHENSHA_TIANXI_MAP.get(_day_zhi, '')]))
        _taiji_targets = set(SHENSHA_TAIJI_MAP.get(day_master, []))
        _taiji_targets.update(SHENSHA_TAIJI_MAP.get(_year_gan, []))
        _jiangxing_targets = set(filter(None, [SHENSHA_JIANGXING_MAP.get(_year_zhi, ''), SHENSHA_JIANGXING_MAP.get(_day_zhi, '')]))

        def _check_yl_shensha(zhi: str, gan: str) -> list:
            """检查一个流年/大运干支对应的神煞列表"""
            result = []
            if zhi in SHENSHA_TIANYI_MAP.get(day_master, []):
                result.append('天乙贵人')
            if zhi in _huagai_targets:
                result.append('华盖')
            if zhi in _yima_targets:
                result.append('驿马')
            if zhi in _taohua_targets:
                result.append('桃花')
            if zhi == SHENSHA_WENCHANG_MAP.get(day_master, ''):
                result.append('文昌')
            if zhi == SHENSHA_LU_MAP.get(day_master, ''):
                result.append('禄神')
            if zhi in _hongluan_targets:
                result.append('红鸾')
            if zhi in _tianxi_targets:
                result.append('天喜')
            if zhi in _taiji_targets:
                result.append('太极贵人')
            if gan == _yuede_gan:
                result.append('月德')
            if _tiande_val:
                if _tiande_val in TIANGAN_SET and gan == _tiande_val:
                    result.append('天德贵人')
                elif _tiande_val not in TIANGAN_SET and zhi == _tiande_val:
                    result.append('天德贵人')
            if _tiande_he:
                if _tiande_he in TIANGAN_SET and gan == _tiande_he:
                    result.append('天德合')
                elif _tiande_he not in TIANGAN_SET and zhi == _tiande_he:
                    result.append('天德合')
            if _yuede_he and gan == _yuede_he:
                result.append('月德合')
            if zhi in _jiangxing_targets:
                result.append('将星')
            # 补充原局_check_shensha中有但大运/流年遗漏的神煞
            if zhi == SHENSHA_TIANGUAN_MAP.get(day_master, ''):
                result.append('天官贵人')
            if zhi == SHENSHA_TIANFU_MAP.get(day_master, ''):
                result.append('天福贵人')
            if zhi in set(SHENSHA_FUXING_MAP.get(day_master, [])):
                result.append('福星贵人')
            if zhi in set(SHENSHA_JINYU_MAP.get(day_master, [])):
                result.append('金舆')
            if zhi == SHENSHA_HONGYAN_MAP.get(day_master, ''):
                result.append('红艳煞')
            if zhi == SHENSHA_YANGREN_MAP.get(day_master, ''):
                result.append('羊刃')
            if zhi == SHENSHA_FEIREN_MAP.get(day_master, ''):
                result.append('飞刃')
            if zhi == SHENSHA_XUETANG_MAP.get(day_master, ''):
                result.append('学堂')
            if zhi == SHENSHA_CIGUAN_MAP.get(day_master, ''):
                result.append('词馆')
            # 补充原局_calc_shensha中有但大运/流年遗漏的神煞（年支/月支/日干查）
            if zhi == SHENSHA_TIANYI_MEDICAL_MAP.get(_month_zhi, ''):
                result.append('天医')
            if zhi == SHENSHA_TIANCHU_MAP.get(day_master, ''):
                result.append('天厨')
            if zhi == SHENSHA_LIUXIA_MAP.get(day_master, ''):
                result.append('流霞')
            if zhi == SHENSHA_WANGSHEN_MAP.get(_year_zhi, ''):
                result.append('亡神')
            if zhi == SHENSHA_JIESHA_MAP.get(_year_zhi, ''):
                result.append('劫煞')
            if zhi == SHENSHA_ZAISHA_MAP.get(_year_zhi, ''):
                result.append('灾煞')
            if zhi == SHENSHA_GOUSHA_MAP.get(_year_zhi, ''):
                result.append('勾煞')
            if zhi == SHENSHA_JIAOSHA_MAP.get(_year_zhi, ''):
                result.append('绞煞')
            if zhi == SHENSHA_GUICHEN_MAP.get(_year_zhi, ''):
                result.append('孤辰')
            if zhi == SHENSHA_GUASU_MAP.get(_year_zhi, ''):
                result.append('寡宿')
            return result

        # 大运（增强版：含十神、藏干、纳音、长生、神煞、流年）
        # NOTE: lunar_python's getStartYear() returns ABSOLUTE year, not age.
        # e.g., getStartYear() might return 2015, not 10.
        # Age = absolute_start_year - birth_year
        dayun_list = []
        dayun_start_year = 0
        dayun_start_age = 0
        birth_year = time.original.year
        current_year = datetime.now().year
        current_liunian = None
        try:
            yun = ec.getYun(gender=gender)
            for d in yun.getDaYun():
                gz = d.getGanZhi()
                if gz:
                    abs_start = d.getStartYear()
                    abs_end = d.getEndYear()
                    # Use library-provided ages (虚岁) instead of manual arithmetic
                    # Manual calc (abs_start - birth_year) is off by 1 for most cases
                    try:
                        start_age = int(d.getStartAge())
                        end_age = int(d.getEndAge())
                    except Exception as _age_err:
                        logger.debug(f"大运起止年龄获取异常，回退到年份差计算: {_age_err}")
                        start_age = abs_start - birth_year + 1  # 虚岁
                        end_age = start_age + 9

                    # 大运天干十神
                    dy_gan = gz[0]
                    dy_zhi = gz[1]
                    dy_shishen_gan = SHISHEN_MAP.get((day_master, dy_gan), '?')

                    # 大运地支藏干及藏干十神
                    dy_hidden = _fix_hide_gan(dy_zhi, TRADITIONAL_HIDE_GAN.get(dy_zhi, ''))
                    dy_shishen_zhi = [SHISHEN_MAP.get((day_master, h), '?') for h in dy_hidden]

                    # 大运纳音
                    dy_nayin = NAYIN_TABLE.get(gz, '')

                    # 大运长生十二宫
                    dy_changsheng = _calc_changsheng(day_master, dy_zhi)

                    # 大运带来的神煞（大运地支对照原局四柱）
                    # 使用 _check_yl_shensha 统一计算大运/流年神煞
                    dy_shensha = _check_yl_shensha(dy_zhi, dy_gan)

                    # 流年（该大运期间每年）
                    liunian_list = []
                    try:
                        for ln in d.getLiuNian():
                            ln_gz = ln.getGanZhi()
                            if ln_gz and len(ln_gz) >= 2:
                                ln_gan = ln_gz[0]
                                ln_zhi = ln_gz[1]
                                # 流年神煞（复用 _check_yl_shensha）
                                ln_shensha = _check_yl_shensha(ln_zhi, ln_gan)
                                ln_hidden = _fix_hide_gan(ln_zhi, TRADITIONAL_HIDE_GAN.get(ln_zhi, ''))
                                ln_info = {
                                    "year": ln.getYear(),
                                    "age": ln.getAge(),
                                    "ganzhi": ln_gz,
                                    "shishen_gan": SHISHEN_MAP.get((day_master, ln_gan), '?'),
                                    "nayin": NAYIN_TABLE.get(ln_gz, ''),
                                    "shensha": ln_shensha,
                                    "hidden_gans": ln_hidden,
                                    "shishen_zhi": [SHISHEN_MAP.get((day_master, h), '?') for h in ln_hidden],
                                    "changsheng": _calc_changsheng(day_master, ln_zhi),
                                }
                                liunian_list.append(ln_info)
                                # 找出当前年份的流年
                                if ln.getYear() == current_year:
                                    current_liunian = {
                                        "year": ln.getYear(),
                                        "age": ln.getAge(),
                                        "ganzhi": ln_gz,
                                        "shishen_gan": SHISHEN_MAP.get((day_master, ln_gan), '?'),
                                        "shishen_zhi": [SHISHEN_MAP.get((day_master, h), '?') for h in ln_hidden],
                                        "hidden_gans": ln_hidden,
                                        "nayin": NAYIN_TABLE.get(ln_gz, ''),
                                        "changsheng": _calc_changsheng(day_master, ln_zhi),
                                        "shensha": ln_shensha,
                                    }
                    except Exception as _ln_err:
                        logger.debug(f"大运流年处理异常: {_ln_err}")

                    dayun_list.append({
                        "start_age": start_age,
                        "end_age": end_age,
                        "ganzhi": gz,
                        "start_year": abs_start,
                        "end_year": abs_end,
                        "is_current": abs_start <= current_year <= abs_end,
                        "shishen_gan": dy_shishen_gan,
                        "shishen_zhi": dy_shishen_zhi,
                        "hidden_gans": dy_hidden,
                        "nayin": dy_nayin,
                        "changsheng": dy_changsheng,
                        "shensha": dy_shensha,
                        "liunian": liunian_list,
                    })
            dayun_start_year = dayun_list[0]["start_year"] if dayun_list else 0
            dayun_start_age = dayun_list[0]["start_age"] if dayun_list else 0
        except Exception as e:
            logger.warning(f"大运计算异常: {e}")

        # 日主五行
        day_master_wuxing = GAN_WUXING_STR.get(day_master, "")

        # 调候用神
        tiaohou = self._calc_tiaohou(day_master, month_pillar.zhi)

        # 神煞
        shensha = self._calc_shensha(
            day_master, day_pillar, year_pillar, month_pillar, time_pillar
        )

        # 特征提取
        features = self._extract_features(
            year_pillar, month_pillar, day_pillar, time_pillar,
            shishen_gan, hidden_gans
        )

        # 五行得分
        wuxing_score = self._calc_wuxing_score(
            [year_pillar, month_pillar, day_pillar, time_pillar],
            hidden_gans
        )

        # 命宫·胎元·身宫的十神（天干对日主）
        def _shishen_for_ganzhi(gz: str) -> dict:
            """给定干支，返回天干十神和藏干十神"""
            if not gz or len(gz) < 2:
                return {"gan_shishen": "", "zhi_shishen": []}
            g = gz[0]
            z = gz[1]
            gan_ss = SHISHEN_MAP.get((day_master, g), '')
            zhi_hides = _fix_hide_gan(z, TRADITIONAL_HIDE_GAN.get(z, ''))
            zhi_ss = [SHISHEN_MAP.get((day_master, h), '?') for h in zhi_hides]
            return {"gan_shishen": gan_ss, "zhi_shishen": zhi_ss, "hidden_gans": zhi_hides}

        ming_gong_info = _shishen_for_ganzhi(ming_gong)
        tai_yuan_info = _shishen_for_ganzhi(tai_yuan)
        shen_gong_info = _shishen_for_ganzhi(shen_gong)

        # 喜用神计算
        xi_yong = self._calc_xi_yong(day_master, month_pillar.zhi, wuxing_score)

        # 将身强/身弱判断注入特征列表（cross_validator 和生成报告依赖此特征）
        strength = xi_yong.get('strength', '')
        if strength == '身强':
            features.insert(0, f'身强—日主{day_master}（{day_master_wuxing}）得令得地，可任财官')
        elif strength == '身弱':
            features.insert(0, f'身弱—日主{day_master}（{day_master_wuxing}）失令失地，需印比扶助')
        elif strength == '中和':
            features.insert(0, f'中和—日主{day_master}（{day_master_wuxing}）力量均衡')

        # 长生十二宫（每柱）
        changsheng = {}
        for pillar_name, pillar in [('year', year_pillar), ('month', month_pillar), ('day', day_pillar), ('time', time_pillar)]:
            changsheng[pillar_name] = _calc_changsheng(day_master, pillar.zhi)

        # 每柱神煞（从shensha列表按关键词分组到对应柱）
        shensha_per_pillar = {'year': [], 'month': [], 'day': [], 'time': [], 'general': []}
        PILLAR_KEYWORDS = {
            'year': ['年支', '年柱', '年干'],
            'month': ['月支', '月柱', '月干'],
            'day': ['日支', '日柱', '日干'],
            'time': ['时支', '时柱', '时干'],
        }
        for s in shensha:
            matched = False
            for pillar_name, keywords in PILLAR_KEYWORDS.items():
                for kw in keywords:
                    if kw in s:
                        # Remove the parenthetical location info
                        clean = s.split('（')[0] if '（' in s else s
                        shensha_per_pillar[pillar_name].append(clean)
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                # Shensha without specific pillar - try to infer from context
                for pillar_name, pillar in [('year', year_pillar), ('month', month_pillar), ('day', day_pillar), ('time', time_pillar)]:
                    if pillar.zhi in s:
                        clean = s.split('（')[0] if '（' in s else s
                        shensha_per_pillar[pillar_name].append(clean)
                        matched = True
                        break
            if not matched:
                # 天罗/地网/十恶大败/阴阳差错/三奇/天转煞等无柱标注神煞归入general
                clean = s.split('（')[0] if '（' in s else s
                shensha_per_pillar['general'].append(clean)

        # 天干关系
        gan_relations = []
        all_gans = [year_pillar.gan, month_pillar.gan, day_pillar.gan, time_pillar.gan]
        for i in range(len(all_gans)):
            for j in range(i+1, len(all_gans)):
                g1, g2 = all_gans[i], all_gans[j]
                if GAN_CHONG.get(g1) == g2:
                    gan_relations.append(f'{g1}{g2}冲')
                if GAN_HE.get(g1) == g2:
                    gan_relations.append(f'{g1}{g2}合')

        # 地支关系
        zhi_relations = []
        all_zhis = [year_pillar.zhi, month_pillar.zhi, day_pillar.zhi, time_pillar.zhi]
        for i in range(len(all_zhis)):
            for j in range(i+1, len(all_zhis)):
                z1, z2 = all_zhis[i], all_zhis[j]
                if ZHI_CHONG_MOD.get(z1) == z2:
                    zhi_relations.append(f'{z1}{z2}冲')
                if ZHI_HE_MOD.get(z1) == z2:
                    zhi_relations.append(f'{z1}{z2}合')
                # 子卯刑 + 自刑（辰辰午午酉酉亥亥）通过ZHI_XING_MOD查表
                if ZHI_XING_MOD.get(z1) == z2 or ZHI_XING_MOD.get(z2) == z1:
                    if z1 == z2:
                        zhi_relations.append(f'{z1}自刑')
                    else:
                        zhi_relations.append(f'{z1}{z2}刑')
                if ZHI_HAI_MOD.get(z1) == z2:
                    zhi_relations.append(f'{z1}{z2}害')
                if ZHI_PO_MOD.get(z1) == z2:
                    zhi_relations.append(f'{z1}{z2}破')
        # 三刑循环（寅巳申、丑戌未）：需三支齐全才算刑，不可拆成两两判断
        zhi_set = set(all_zhis)
        for cycle in SAN_XING_CYCLES:
            if cycle <= zhi_set:
                cycle_sorted = sorted(cycle, key=lambda z: DI_ZHI.index(z))
                zhi_relations.append(f'{"·".join(cycle_sorted)}三刑')

        return {
            "engine": self.name,
            "engine_en": self.name_en,
            "year": year_pillar,
            "month": month_pillar,
            "day": day_pillar,
            "time": time_pillar,
            "day_master": day_master,
            "day_master_wuxing": day_master_wuxing,
            "hidden_gans": hidden_gans,
            "shishen_gan": shishen_gan,
            "shishen_zhi": shishen_zhi,
            "nayin": nayin,
            "xunkong": xunkong,
            "dayun": dayun_list,
            "dayun_start_year": dayun_start_year,
            "dayun_start_age": dayun_start_age,
            "tiaohou": tiaohou,
            "shensha": shensha,
            "shensha_per_pillar": shensha_per_pillar,
            "changsheng": changsheng,
            "gan_relations": gan_relations,
            "zhi_relations": zhi_relations,
            "features": features,
            "wuxing_score": wuxing_score,
            "ming_gong": ming_gong,
            "ming_gong_shishen": ming_gong_info,
            "tai_yuan": tai_yuan,
            "tai_yuan_shishen": tai_yuan_info,
            "shen_gong": shen_gong,
            "shen_gong_shishen": shen_gong_info,
            "xi_yong": xi_yong,
            "liunian": current_liunian,
            "location": {
                "longitude": getattr(time, 'longitude', None),
                "latitude": getattr(time, 'latitude', None),
            },
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if "error" in data:
            return False, data["error"]
        if not data.get("day_master"):
            return False, "日主为空"
        return True, None

    # 类级别缓存，避免每次调用都读磁盘
    _tiaohou_cache = None

    def _calc_tiaohou(self, day_gan: str, month_zhi: str) -> str:
        """调候用神计算，优先从 data/tiaohou.json 读取"""
        import json
        from pathlib import Path
        
        # 使用类级别缓存
        if BaziEngine._tiaohou_cache is None:
            tiaohou_file = Path(__file__).parent.parent / "data" / "tiaohou.json"
            if tiaohou_file.exists():
                try:
                    with open(tiaohou_file, "r", encoding="utf-8") as f:
                        BaziEngine._tiaohou_cache = json.load(f)
                except Exception as e:
                    logger.debug(f"调候用神JSON加载失败: {e}")
                    BaziEngine._tiaohou_cache = {}
            else:
                BaziEngine._tiaohou_cache = {}
        
        if BaziEngine._tiaohou_cache:
            cached = BaziEngine._tiaohou_cache.get(day_gan, {}).get(month_zhi, "")
            if cached:
                return cached
            # 缓存中无此组合，继续回退到硬编码表

        # 回退：硬编码
        table = {
            ("甲", "寅"): "丙癸", ("甲", "卯"): "庚丙戊", ("甲", "辰"): "庚丁壬",
            ("甲", "巳"): "癸庚丁", ("甲", "午"): "癸庚丁", ("甲", "未"): "癸庚丁",
            ("甲", "申"): "庚丁壬", ("甲", "酉"): "庚丁丙", ("甲", "戌"): "庚丁甲",
            ("甲", "亥"): "庚丁丙戊", ("甲", "子"): "丁丙庚", ("甲", "丑"): "丁丙庚",
            ("乙", "寅"): "丙癸", ("乙", "卯"): "丙癸", ("乙", "辰"): "癸丙戊",
            ("乙", "巳"): "癸", ("乙", "午"): "癸", ("乙", "未"): "癸",
            ("乙", "申"): "癸丙戊", ("乙", "酉"): "癸丙丁", ("乙", "戌"): "癸辛",
            ("乙", "亥"): "丙戊", ("乙", "子"): "丙", ("乙", "丑"): "丙",
            ("丙", "寅"): "壬庚", ("丙", "卯"): "壬己", ("丙", "辰"): "壬甲",
            ("丙", "巳"): "壬庚癸", ("丙", "午"): "壬庚", ("丙", "未"): "壬庚",
            ("丙", "申"): "壬戊", ("丙", "酉"): "壬戊", ("丙", "戌"): "甲壬",
            ("丙", "亥"): "甲戊庚壬", ("丙", "子"): "壬戊", ("丙", "丑"): "壬甲",
            ("丁", "寅"): "甲庚", ("丁", "卯"): "庚甲", ("丁", "辰"): "甲庚",
            ("丁", "巳"): "甲庚", ("丁", "午"): "壬庚癸", ("丁", "未"): "甲壬庚",
            ("丁", "申"): "甲庚丙", ("丁", "酉"): "甲庚丙", ("丁", "戌"): "甲庚",
            ("丁", "亥"): "甲戊", ("丁", "子"): "甲戊", ("丁", "丑"): "甲戊",
            ("戊", "寅"): "丙甲癸", ("戊", "卯"): "丙甲癸", ("戊", "辰"): "甲丙癸",
            ("戊", "巳"): "甲丙癸", ("戊", "午"): "壬甲丙", ("戊", "未"): "癸丙甲",
            ("戊", "申"): "丙癸甲", ("戊", "酉"): "丙癸", ("戊", "戌"): "甲丙癸",
            ("戊", "亥"): "丙甲", ("戊", "子"): "丙甲", ("戊", "丑"): "丙甲",
            ("己", "寅"): "丙癸庚", ("己", "卯"): "癸丙庚", ("己", "辰"): "癸丙戊",
            ("己", "巳"): "癸丙", ("己", "午"): "癸丙", ("己", "未"): "癸丙",
            ("己", "申"): "丙癸", ("己", "酉"): "丙癸", ("己", "戌"): "甲丙癸",
            ("己", "亥"): "丙甲戊", ("己", "子"): "丙甲戊", ("己", "丑"): "丙甲戊",
            ("庚", "寅"): "戊甲丙", ("庚", "卯"): "丁甲庚", ("庚", "辰"): "甲丁壬",
            ("庚", "巳"): "壬戊丙丁", ("庚", "午"): "壬癸", ("庚", "未"): "丁甲",
            ("庚", "申"): "丁甲", ("庚", "酉"): "丁甲丙", ("庚", "戌"): "甲丁",
            ("庚", "亥"): "丁丙", ("庚", "子"): "丁甲丙", ("庚", "丑"): "丙丁甲",
            ("辛", "寅"): "己壬庚", ("辛", "卯"): "壬甲", ("辛", "辰"): "壬甲",
            ("辛", "巳"): "壬甲癸", ("辛", "午"): "壬己癸", ("辛", "未"): "壬庚甲",
            ("辛", "申"): "壬甲戊", ("辛", "酉"): "壬甲", ("辛", "戌"): "壬甲",
            ("辛", "亥"): "壬丙", ("辛", "子"): "壬丙戊", ("辛", "丑"): "壬丙戊",
            ("壬", "寅"): "庚丙戊", ("壬", "卯"): "戊庚辛", ("壬", "辰"): "甲庚",
            ("壬", "巳"): "庚癸辛", ("壬", "午"): "癸庚辛", ("壬", "未"): "辛庚癸",
            ("壬", "申"): "戊丁", ("壬", "酉"): "丁甲", ("壬", "戌"): "甲庚",
            ("壬", "亥"): "戊丙庚", ("壬", "子"): "戊丙", ("壬", "丑"): "丙丁甲",
            ("癸", "寅"): "辛丙", ("癸", "卯"): "庚辛", ("癸", "辰"): "丙辛甲",
            ("癸", "巳"): "辛", ("癸", "午"): "庚辛壬", ("癸", "未"): "庚辛壬",
            ("癸", "申"): "丁甲", ("癸", "酉"): "辛丙", ("癸", "戌"): "辛甲",
            ("癸", "亥"): "庚戊辛丙", ("癸", "子"): "丙辛", ("癸", "丑"): "丙丁",
        }
        return table.get((day_gan, month_zhi), "")

    def _extract_features(self, year, month, day, time, shishen_gan, hidden_gans) -> list:
        """提取命盘核心特征"""
        features = []

        # 1. 冲
        zhis = [p.zhi for p in [year, month, day, time]]
        all_gans = [p.gan for p in [year, month, day, time]]
        pos_names = ["年","月","日","时"]
        for i, z1 in enumerate(zhis):
            for j, z2 in enumerate(zhis[i+1:], i+1):
                if ZHI_CHONG_MOD.get(z1) == z2:
                    features.append(f"{z1}{z2}冲 — {pos_names[i]}支与{pos_names[j]}支相冲")

        # 2. 合
        for i, z1 in enumerate(zhis):
            for j, z2 in enumerate(zhis[i+1:], i+1):
                # 六合（复用模块级 ZHI_HE_MOD 常量）
                if ZHI_HE_MOD.get(z1) == z2:
                    features.append(f"{z1}{z2}合 — {pos_names[i]}支与{pos_names[j]}支相合")

        # 2.5 刑（地支三刑：子卯刑/自刑 + 寅巳申/丑戌未三刑）
        # 子卯刑 & 自刑（通过 ZHI_XING_MOD 两两检测，双向查表与zhi_relations保持一致）
        xing_found = set()
        for i, z1 in enumerate(zhis):
            for j, z2 in enumerate(zhis[i+1:], i+1):
                if ZHI_XING_MOD.get(z1) == z2 or ZHI_XING_MOD.get(z2) == z1:
                    pair_key = frozenset({pos_names[i], pos_names[j]})
                    if pair_key not in xing_found:
                        xing_found.add(pair_key)
                        if z1 == z2:
                            features.append(f"{z1}自刑 — {pos_names[i]}支与{pos_names[j]}支同支自刑，性格自我矛盾")
                        else:
                            features.append(f"{z1}{z2}刑 — {pos_names[i]}支与{pos_names[j]}支相刑，人际或健康有隐患")
        # 三刑循环（寅巳申=无恩之刑，丑戌未=恃势之刑）
        zhi_set = set(zhis)
        for cycle in SAN_XING_CYCLES:
            if cycle.issubset(zhi_set):
                cycle_name = "无恩之刑" if cycle == frozenset({'寅', '巳', '申'}) else ("恃势之刑" if cycle == frozenset({'丑', '戌', '未'}) else "三刑")
                cycle_str = "".join(sorted(cycle, key=lambda z: '子丑寅卯辰巳午未申酉戌亥'.index(z)))
                positions = [pos_names[i] for i, z in enumerate(zhis) if z in cycle]
                features.append(f"{cycle_str}{cycle_name} — {'、'.join(positions)}支三刑齐全，人生多历练")

        # 2.6 天干合
        for i, g1 in enumerate(all_gans):
            for j, g2 in enumerate(all_gans[i+1:], i+1):
                if GAN_HE.get(g1) == g2:
                    features.append(f"{g1}{g2}合 — {pos_names[i]}干与{pos_names[j]}干相合")

        # 2.7 天干冲（甲庚/乙辛/丙壬/丁癸，阳克阳、阴克阴为偏冲）
        for i, g1 in enumerate(all_gans):
            for j, g2 in enumerate(all_gans[i+1:], i+1):
                if GAN_CHONG.get(g1) == g2:
                    features.append(f"{g1}{g2}冲 — {pos_names[i]}干与{pos_names[j]}干相冲，气场对立")

        # 2.8 地支害（六害：子未/丑午/寅巳/卯辰/申亥/酉戌）
        hai_found = set()
        for i, z1 in enumerate(zhis):
            for j, z2 in enumerate(zhis[i+1:], i+1):
                if ZHI_HAI_MOD.get(z1) == z2:
                    pair_key = frozenset({pos_names[i], pos_names[j]})
                    if pair_key not in hai_found:
                        hai_found.add(pair_key)
                        features.append(f"{z1}{z2}害 — {pos_names[i]}支与{pos_names[j]}支相害，暗中损耗")

        # 2.8.5 地支破（六破：子酉/丑辰/寅亥/卯午/巳申/未戌）
        po_found = set()
        for i, z1 in enumerate(zhis):
            for j, z2 in enumerate(zhis[i+1:], i+1):
                if ZHI_PO_MOD.get(z1) == z2:
                    pair_key = frozenset({pos_names[i], pos_names[j]})
                    if pair_key not in po_found:
                        po_found.add(pair_key)
                        features.append(f"{z1}{z2}破 — {pos_names[i]}支与{pos_names[j]}支相破，暗中消耗")

        # 2.9 地支三合局（三支齐全时强力聚合，两支半合也有引力）
        # 申子辰→水局，寅午戌→火局，巳酉丑→金局，亥卯未→木局
        # SAN_HE_GROUPS, BAN_HE_PAIRS 已提升为模块级常量
        for group, wx, name in SAN_HE_GROUPS:
            if group <= zhi_set:
                # 按年月日时顺序列出位置
                positions = [pos_names[i] for i, z in enumerate(zhis) if z in group]
                features.append(f"{name}三合{wx}局 — {'、'.join(positions)}支三合齐全，{wx}气汇聚，能量强大")
            else:
                # 检查半合（两支）
                matched_pairs = []
                for pair, (p_wx, _) in BAN_HE_PAIRS.items():
                    if pair <= zhi_set and pair <= group:
                        z_sorted = sorted(pair, key=lambda z: '子丑寅卯辰巳午未申酉戌亥'.index(z))
                        # 按年月日时顺序列出位置
                        positions = [pos_names[i] for i, z in enumerate(zhis) if z in pair]
                        matched_pairs.append((z_sorted, positions, p_wx))
                for z_sorted, positions, p_wx in matched_pairs:
                    features.append(f"{''.join(z_sorted)}半合{p_wx}局 — {'、'.join(positions)}支有{p_wx}气聚合之势")

        # 2.10 地支三会局（同一方位三支齐全，力量极强于三合）
        # 寅卯辰→东方木，巳午未→南方火，申酉戌→西方金，亥子丑→北方水
        # SAN_HUI_GROUPS 已提升为模块级常量
        for group, wx, direction in SAN_HUI_GROUPS:
            if group <= zhi_set:
                # 按年月日时顺序列出位置
                positions = [pos_names[i] for i, z in enumerate(zhis) if z in group]
                features.append(f"{direction}三会{wx}局 — {'、'.join(positions)}支方位齐聚，{wx}势磅礴，力量极强")

        # 3. 七杀透干
        ss = shishen_gan
        if ss.get("time") == "七杀":
            features.append("七杀透干时柱 — 自我驱动力强，但压力大")
        if ss.get("month") == "七杀":
            features.append("七杀当令 — 竞争意识强")
        if ss.get("year") == "七杀":
            features.append("年柱七杀 — 早年多磨练")

        # 4. 正官
        if ss.get("time") == "正官":
            features.append("正官透干时柱 — 责任心强，自律")
        if ss.get("month") == "正官":
            features.append("正官当令 — 正统、规矩")

        # 4.5 十神组合（天干层面的经典格局信号，八字论命的核心维度之一）
        ss_vals_non_day = [v for k, v in ss.items() if k != "day"]
        has_shangguan = "伤官" in ss_vals_non_day
        has_zhenguan = "正官" in ss_vals_non_day
        has_qisha = "七杀" in ss_vals_non_day
        has_shishen = "食神" in ss_vals_non_day
        has_zhengyin = "正印" in ss_vals_non_day
        has_pianyin = "偏印" in ss_vals_non_day
        has_yin = has_zhengyin or has_pianyin
        has_zhengcai = "正财" in ss_vals_non_day
        has_piancai = "偏财" in ss_vals_non_day
        has_cai = has_zhengcai or has_piancai

        # 伤官见官：伤官与正官同透天干——叛逆与规则的冲突
        if has_shangguan and has_zhenguan:
            features.append("伤官见官 — 才华与规矩冲突，宜以技立身而非从政")
        # 食神制杀：食神与七杀同透——化压力为动力的天赋
        if has_shishen and has_qisha:
            features.append("食神制杀 — 化压力为动力，逆境中见能力")
        # 杀印相生：七杀与正印同透——权威有根基，有贵人扶
        # 注：偏印+七杀为"枭神驾杀"，性质不同，不归入杀印相生
        if has_qisha and has_zhengyin:
            features.append("杀印相生 — 权威有根基，贵人扶上位")
        # 财官双美：财星与正官同透——名利兼收的信号
        if has_cai and has_zhenguan:
            features.append("财官双美 — 名利兼收，务实进取")
        # 伤官生财：伤官与财星同透——创意生财
        if has_shangguan and has_cai:
            features.append("伤官生财 — 才华转化为财富，以技谋利")
        # 食神生财：食神与财星同透——稳健生财
        if has_shishen and has_cai:
            features.append("食神生财 — 稳健求财，生活品质佳")
        # 枭神夺食：偏印与食神同透——才艺受阻
        if has_pianyin and has_shishen:
            features.append("枭神夺食 — 才艺易受干扰，思路易被打断")
        # 官杀混杂：正官与七杀同透天干——压力来源复杂，既有制度约束又有竞争压力
        # 八字中最重要的格局信号之一，需要合杀留官或合官留杀方能化解
        if has_zhenguan and has_qisha:
            features.append("官杀混杂 — 压力来源复杂，事业需防多头管理，宜化繁为简")
        # 官印相生：正官与正印同透——体制内发展的经典格局
        # 区别于杀印相生（七杀+正印），官印相生偏正统路径
        # 注：正官+偏印不构成官印相生，偏印为枭神，性质不同
        if has_zhenguan and has_zhengyin:
            features.append("官印相生 — 体制内发展有利，稳中有升，有贵人提携")
        # 伤官配印：伤官与印星同透——伤官的叛逆创造力被印星的学识涵养所驾驭
        # 《子平真诠》列为上格：伤官虽凶，有印则吉。才华有了底蕴，表达有了深度。
        # 与"伤官见官"（凶）形成对比：伤官见官是才华与规矩冲突，伤官配印是才华被学识驯化。
        if has_shangguan and has_yin:
            features.append("伤官配印 — 才华有底蕴，表达有深度，化叛逆为创造力")

        # 5. 印星（排除日元位置，与十神组合检查保持一致）
        yin_count = sum(1 for k, v in ss.items() if k != "day" and "印" in v)
        if yin_count >= 2:
            features.append("印星多现 — 学习能力强，有贵人")
        elif yin_count == 0:
            features.append("印星不显 — 缺乏外部支持")

        # 6. 财星
        cai_count = sum(1 for k, v in ss.items() if k != "day" and "财" in v)
        if cai_count >= 2:
            features.append("财星多现 — 对物质敏感")
        elif cai_count == 0:
            features.append("财星不显 — 不重物质")

        # 7. 食伤
        shis = [v for k, v in ss.items() if k != "day" and ("食" in v or "伤" in v)]
        if len(shis) >= 2:
            features.append("食伤旺 — 表达欲强，创造力佳")

        # 8. 比劫
        bijian = [v for k, v in ss.items() if k != "day" and ("比" in v or "劫" in v)]
        if len(bijian) >= 2:
            features.append("比劫多 — 朋友多，竞争也多")

        # 9. 日支特殊
        day_zhi = day.zhi
        if day_zhi in ["子", "午", "卯", "酉"]:
            features.append(f"日坐{day_zhi} — 四正之地，性格鲜明")

        # 10. 日主坐禄
        day_gan = day.gan
        lu_map = SHENSHA_LU_MAP
        if lu_map.get(day_gan) == day_zhi:
            features.append("日坐禄地 — 自身根基扎实")

        # 11. 天干连珠（四天干占连续四位置，如甲乙丙丁/丙丁戊己等，极罕见）
        gan_indices = sorted(TIANGAN_CYCLE.index(g) for g in all_gans)

        def _is_consecutive_4(indices, cycle_len):
            """检查4个索引是否在环形排列中连续"""
            s = sorted(set(indices))
            if len(s) < 4:
                return False
            # 计算所有4个环形间距（3个正向 + 1个绕回）
            all_gaps = [s[i+1] - s[i] for i in range(3)]
            all_gaps.append(cycle_len - s[3] + s[0])
            # 4个连续元素在环形中：恰好3个间距为1，1个间距为cycle_len-3
            # 例：[0,1,2,3]→gaps=[1,1,1,7] ✓; [7,8,9,0]→gaps=[1,1,1,7] ✓（绕回）
            #     [0,1,8,9]→gaps=[1,7,1,3] ✗（不连续）
            ones = sum(1 for g in all_gaps if g == 1)
            big = sum(1 for g in all_gaps if g == cycle_len - 3)
            return ones == 3 and big == 1

        if _is_consecutive_4(gan_indices, 10):
            features.append("天干连珠 — 四天干连续排列，五行流转顺畅")

        # 12. 地支连珠（四地支占连续四位置，如子丑寅卯/寅卯辰巳等）
        zhi_indices = [DI_ZHI.index(z) for z in zhis]
        if _is_consecutive_4(zhi_indices, 12):
            features.append("地支连珠 — 四地支连续排列，气势连贯，格局特殊")

        # 13. 藏干透干（地支藏干中的天干在四柱天干中出现，表示该元素力量外露，影响显著）
        if hidden_gans:
            gan_set = set(all_gans)
            pos_keys = ['year', 'month', 'day', 'time']
            for pos_idx, key in enumerate(pos_keys):
                hides = hidden_gans.get(key, [])
                if isinstance(hides, str):
                    hides = list(hides)
                for h_gan in hides:
                    if h_gan in gan_set:
                        # 找到透干的天干在哪个柱（检查所有柱，不仅限首个匹配）
                        for g_pos, g in enumerate(all_gans):
                            if g == h_gan and g_pos != pos_idx:
                                # 避免同柱重复（如年柱天干甲+年支寅藏甲），但继续检查其他柱
                                features.append(
                                    f"{h_gan}透干（{pos_names[pos_idx]}支{zhis[pos_idx]}藏{h_gan}→{pos_names[g_pos]}干{g}）"
                                )

        # 最多30条基础特征（身强/身弱特征由analyze()方法insert(0,...)注入，不占此名额）
        # 原20条上限仍不足：冲/合/刑/害/三合/三会+十神组合+日支日禄已占15+条，天干连珠/地支连珠等稀有特征仍可能丢失
        return features[:self.MAX_BASE_FEATURES]

    def _calc_shensha(self, day_master: str, day_pillar, year_pillar, month_pillar, time_pillar) -> list:
        """计算神煞（以日干和年支为主）"""
        shensha = []
        day_gan = day_master
        day_zhi = day_pillar.zhi
        year_zhi = year_pillar.zhi
        year_gan = year_pillar.gan
        POS_NAMES = ['年', '月', '日', '时']
        all_zhis = [year_pillar.zhi, month_pillar.zhi, day_pillar.zhi, time_pillar.zhi]
        all_gans = [year_pillar.gan, month_pillar.gan, day_pillar.gan, time_pillar.gan]
        day_gz = day_pillar.gan + day_pillar.zhi  # 日柱干支（复用，消除重复计算）

        # 辅助函数：扫描四柱地支，target_zhi 命中则追加 shensha 条目
        def _scan_zhi(name: str, target_zhi: str):
            if not target_zhi:
                return
            for pos_idx, z in enumerate(all_zhis):
                if z == target_zhi:
                    shensha.append(f'{name}（{POS_NAMES[pos_idx]}支{z}）')

        # 辅助函数：扫描四柱地支，targets 为地支集合（多个目标地支）
        def _scan_zhi_set(name: str, targets: set):
            if not targets:
                return
            for pos_idx, z in enumerate(all_zhis):
                if z in targets:
                    shensha.append(f'{name}（{POS_NAMES[pos_idx]}支{z}）')

        # 1. 天乙贵人（以日干查四支）
        tianyi_zhis = SHENSHA_TIANYI_MAP.get(day_gan, [])
        tianyi_found = set()
        for pos_idx, z in enumerate(all_zhis):
            if z in tianyi_zhis:
                pos = POS_NAMES[pos_idx]
                shensha.append(f'天乙贵人（{pos}支{z}）')
                tianyi_found.add(z)
        if len(tianyi_found) >= 2:
            shensha.append('双天乙贵人')

        # 2. 华盖（以年支和日支查四支，与大运一致）
        huagai_targets = set(filter(None, [SHENSHA_HUAGAI_MAP.get(year_zhi, ''), SHENSHA_HUAGAI_MAP.get(day_zhi, '')]))
        _scan_zhi_set('华盖', huagai_targets)

        # 3. 驿马（以年支和日支查三合局冲位，与大运一致）
        yima_targets = set(filter(None, [SHENSHA_YIMA_MAP.get(year_zhi, ''), SHENSHA_YIMA_MAP.get(day_zhi, '')]))
        _scan_zhi_set('驿马', yima_targets)

        # 4. 桃花（以年支和日支查，与大运一致）
        taohua_targets = set(filter(None, [SHENSHA_TAOHUA_MAP.get(year_zhi, ''), SHENSHA_TAOHUA_MAP.get(day_zhi, '')]))
        _scan_zhi_set('桃花', taohua_targets)

        # 5. 将星（以年支和日支查，与大运一致）
        jiangxing_targets = set(filter(None, [SHENSHA_JIANGXING_MAP.get(year_zhi, ''), SHENSHA_JIANGXING_MAP.get(day_zhi, '')]))
        _scan_zhi_set('将星', jiangxing_targets)

        # 6. 天德贵人（以月支查天干或地支）— 使用模块级 SHENSHA_TIANDEREN_MAP
        tiande = SHENSHA_TIANDEREN_MAP.get(month_pillar.zhi, '')
        if tiande:
            if tiande in TIANGAN_SET:
                # 天德为天干，查四柱天干
                for g_pos_idx, g in enumerate(all_gans):
                    if g == tiande:
                        pos = POS_NAMES[g_pos_idx]
                        shensha.append(f'天德贵人（{pos}干{g}）')
            else:
                # 天德为地支（如巳、申），查四柱地支
                for pos_idx, z in enumerate(all_zhis):
                    if z == tiande:
                        pos = POS_NAMES[pos_idx]
                        shensha.append(f'天德贵人（{pos}支{z}）')

        # 7~9. 文昌/红艳/禄神（以日干查地支，统一用 _scan_zhi 扫描四柱）
        _scan_zhi('文昌贵人', SHENSHA_WENCHANG_MAP.get(day_gan, ''))
        _scan_zhi('红艳煞', SHENSHA_HONGYAN_MAP.get(day_gan, ''))
        _scan_zhi('禄神', SHENSHA_LU_MAP.get(day_gan, ''))

        # 10. 红鸾（以年支和日支查，与华盖/驿马/桃花/将星一致）
        hongluan_targets = set(filter(None, [SHENSHA_HONGLUAN_MAP.get(year_zhi, ''), SHENSHA_HONGLUAN_MAP.get(day_zhi, '')]))
        _scan_zhi_set('红鸾', hongluan_targets)

        # 11. 天喜（以年支和日支查，红鸾对冲）
        tianxi_targets = set(filter(None, [SHENSHA_TIANXI_MAP.get(year_zhi, ''), SHENSHA_TIANXI_MAP.get(day_zhi, '')]))
        _scan_zhi_set('天喜', tianxi_targets)

        # 12. 月德（以月支查天干）
        yuede = SHENSHA_YUEDE_MAP.get(month_pillar.zhi, '')
        if yuede:
            for g_pos_idx, g in enumerate(all_gans):
                if g == yuede:
                    pos = POS_NAMES[g_pos_idx]
                    shensha.append(f'月德（{pos}干{g}）')

        # 13. 太极贵人（以日干和年干查四支，复用模块级 SHENSHA_TAIJI_MAP）
        taiji_targets = set()
        for gan in [day_gan, year_gan]:
            taiji_targets.update(SHENSHA_TAIJI_MAP.get(gan, []))
        _scan_zhi_set('太极贵人', taiji_targets)

        # 14. 福星贵人（以日干查）— 使用模块级 SHENSHA_FUXING_MAP
        fuxing_zhis = set(SHENSHA_FUXING_MAP.get(day_gan, []))
        _scan_zhi_set('福星贵人', fuxing_zhis)

        # 15. 金舆（以日干查）— 使用模块级 SHENSHA_JINYU_MAP
        jinyu_zhi = set(SHENSHA_JINYU_MAP.get(day_gan, []))
        _scan_zhi_set('金舆', jinyu_zhi)

        # 16. 天德合（以月支查天干，天德的六合）
        # tiande 已在第6步（天德贵人）赋值，此处复用
        if tiande:
            tiande_he = ''
            if tiande in TIANGAN_SET:
                tiande_he = GAN_LIUHE.get(tiande, '')
            else:
                # 天德为地支时，天德合取地支六合
                tiande_he = ZHI_HE_MOD.get(tiande, '')
            if tiande_he:
                if tiande_he in TIANGAN_SET:
                    for g_pos_idx, g in enumerate(all_gans):
                        if g == tiande_he:
                            pos = POS_NAMES[g_pos_idx]
                            shensha.append(f'天德合（{pos}干{g}）')
                else:
                    for pos_idx, z in enumerate(all_zhis):
                        if z == tiande_he:
                            pos = POS_NAMES[pos_idx]
                            shensha.append(f'天德合（{pos}支{z}）')

        # 17. 月德合（以月支查天干，月德的六合）
        # yuede 已在第12步（月德贵人）赋值，此处复用
        yuede_he = GAN_LIUHE.get(yuede, '')
        if yuede_he:
            for g_pos_idx, g in enumerate(all_gans):
                if g == yuede_he:
                    pos = POS_NAMES[g_pos_idx]
                    shensha.append(f'月德合（{pos}干{g}）')

        # 18. 天赦（以月支查日柱）— 使用模块级 SHENSHA_TIANSHE_MAP
        tianshe = SHENSHA_TIANSHE_MAP.get(month_pillar.zhi, '')
        if tianshe:
            if day_gz == tianshe:
                shensha.append('天赦')

        # 19~31. 以日干/年支/月支查地支的神煞（数据驱动循环，消除逐行重复调用）
        _SCAN_DEFS = [
            # (名称, 查表字典, 查表key)
            ('天医', SHENSHA_TIANYI_MEDICAL_MAP, month_pillar.zhi),
            ('天厨', SHENSHA_TIANCHU_MAP, day_gan),
            ('学堂', SHENSHA_XUETANG_MAP, day_gan),
            ('词馆', SHENSHA_CIGUAN_MAP, day_gan),
            ('羊刃', SHENSHA_YANGREN_MAP, day_gan),
            ('飞刃', SHENSHA_FEIREN_MAP, day_gan),
            ('流霞', SHENSHA_LIUXIA_MAP, day_gan),
            ('亡神', SHENSHA_WANGSHEN_MAP, year_zhi),
            ('劫煞', SHENSHA_JIESHA_MAP, year_zhi),
            ('灾煞', SHENSHA_ZAISHA_MAP, year_zhi),
            ('勾煞', SHENSHA_GOUSHA_MAP, year_zhi),
            ('绞煞', SHENSHA_JIAOSHA_MAP, year_zhi),
            ('孤辰', SHENSHA_GUICHEN_MAP, year_zhi),
            ('寡宿', SHENSHA_GUASU_MAP, year_zhi),
        ]
        for name, sha_map, key in _SCAN_DEFS:
            _scan_zhi(name, sha_map.get(key, ''))

        # 32. 天罗地网（以纳音五行查年柱和日柱）
        # 传统规则：火命见戌亥为天罗，水土命见辰巳为地网，金木命无天罗地网
        # 注：年柱纳音和日柱纳音均需检查（年命+日命，不同派系侧重不同）
        # 修复：年柱和日柱应独立检查，避免break中断导致日柱的天罗/地网被遗漏
        tianluo_set = {'戌', '亥'}
        diwang_set = {'辰', '巳'}
        ref_zhis = set(all_zhis)  # 查四柱全部地支
        _tianluo_found = False
        _diwang_found = False
        for _check_pillar in [year_pillar, day_pillar]:
            _nayin_str = _check_pillar.nayin or ''
            _nayin_wx = ''
            for _wx in WUXING_ORDERED:
                if _wx in _nayin_str:
                    _nayin_wx = _wx
                    break
            if not _tianluo_found and _nayin_wx == '火' and ref_zhis & tianluo_set:
                shensha.append('天罗')
                _tianluo_found = True
            if not _diwang_found and _nayin_wx in ('水', '土') and ref_zhis & diwang_set:
                shensha.append('地网')
                _diwang_found = True

        # 33. 十恶大败（以日柱查）— 使用模块级 SHIBA_EBA
        if day_gz in SHIBA_EBA:
            shensha.append('十恶大败')

        # 34. 四废（以月支所在季节查日柱）— 使用模块级 SHENSHA_SIFEI_MAP
        sifei_list = SHENSHA_SIFEI_MAP.get(month_pillar.zhi, [])
        if day_gz in sifei_list:
            shensha.append('四废')

        # 35. 六甲空亡（以日柱查空亡）
        xunkong = XUNKONG_MAP.get(day_gz, '')
        if xunkong:
            for pos_idx, z in enumerate(all_zhis):
                if z in xunkong:
                    pos = POS_NAMES[pos_idx]
                    shensha.append(f'空亡（{pos}支{z}）')

        # 36. 双华盖（以年支和日支查，复用上方第2步的华盖目标地支）
        for huagai_zhi in huagai_targets:
            huagai_count = sum(1 for z in all_zhis if z == huagai_zhi)
            if huagai_count >= 2:
                shensha.append('双华盖')
                break

        # 37. 双桃花（以年支和日支查，复用上方第4步的桃花目标地支）
        for taohua_zhi in taohua_targets:
            taohua_count = sum(1 for z in all_zhis if z == taohua_zhi)
            if taohua_count >= 2:
                shensha.append('双桃花')
                break

        # 38~39. 天官贵人/天福贵人（以日干查四支）
        _scan_zhi('天官贵人', SHENSHA_TIANGUAN_MAP.get(day_gan, ''))
        _scan_zhi('天福贵人', SHENSHA_TIANFU_MAP.get(day_gan, ''))

        # 40. 三奇贵人（天干组合：乙丙丁=天上三奇，甲戊庚=地上三奇，辛壬癸=人中三奇）
        all_gan_str = ''.join(all_gans)
        if '乙' in all_gan_str and '丙' in all_gan_str and '丁' in all_gan_str:
            shensha.append('天上三奇（乙丙丁）')
        if '甲' in all_gan_str and '戊' in all_gan_str and '庚' in all_gan_str:
            shensha.append('地上三奇（甲戊庚）')
        if '辛' in all_gan_str and '壬' in all_gan_str and '癸' in all_gan_str:
            shensha.append('人中三奇（辛壬癸）')

        # 41. 德秀贵人（以月支查天干组合）— 使用模块级 SHENSHA_DEXIU_MAP
        dexiu = SHENSHA_DEXIU_MAP.get(month_pillar.zhi, {})
        dexiu_de = dexiu.get('德', '')
        dexiu_xiu = dexiu.get('秀', '')
        if dexiu_de and dexiu_de in all_gans:
            shensha.append(f'德秀贵人（德={dexiu_de}）')
        if dexiu_xiu and any(g in dexiu_xiu for g in all_gans):
            matching = [g for g in all_gans if g in dexiu_xiu]
            shensha.append(f'秀气（{",".join(matching)}）')

        # 42. 阴阳差错（以日柱查）— 使用模块级 YINYANG_CHACUO
        if day_gz in YINYANG_CHACUO:
            shensha.append('阴阳差错')

        # NOTE: 天赦日检测已在上方第18条天赦中统一处理（两者判定条件完全一致：春戊寅/夏甲午/秋戊申/冬甲子）

        # 44. 天转煞（以日柱纳音五行查）— 使用模块级 SHENSHA_TIANZHUAN_MAP
        # 注意：天转煞用日柱纳音五行，与天罗地网用年柱纳音五行不同
        _day_nayin_str = day_pillar.nayin or ''
        _day_nayin_wx = ''
        for _wx in WUXING_ORDERED:
            if _wx in _day_nayin_str:
                _day_nayin_wx = _wx
                break
        tianzhuan_ri = SHENSHA_TIANZHUAN_MAP.get(_day_nayin_wx, '')
        if day_gz == tianzhuan_ri:
            shensha.append('天转煞')

        return shensha

    def _calc_xi_yong(self, day_gan: str, month_zhi: str, wuxing_score: dict) -> dict:
        """
        综合用神计算：普通旺衰 + 调候用神
        
        返回: {xi: [喜用五行], ji: [忌神五行], xian: [闲神五行], reason: str}
        """
        # 五行映射
        day_wx = GAN_WUXING_STR.get(day_gan, '')
        
        # 防御：日主五行为空时无法计算喜用神，返回中和默认值
        if not day_wx:
            return {
                'xi': [], 'ji': [], 'xian': ['木', '火', '土', '金', '水'],
                'strength': '未知', 'reason': f'日主{day_gan}五行无法识别',
                'day_score': 0, 'total_score': 0, 'ratio': 0,
            }
        
        # 计算日主得分占比
        total = sum(wuxing_score.values()) if wuxing_score else 1
        day_score = wuxing_score.get(day_wx, 0) if wuxing_score else 0
        ratio = day_score / total if total > 0 else 0
        
        # 普通旺衰判断（使用模块级五行生克常量）
        # 阈值：身强≥40%，中和25%-40%，身弱<25%
        # (使用类级 STRONG_THRESHOLD / BALANCED_THRESHOLD)
        if ratio >= self.STRONG_THRESHOLD:
            strength = '身强'
            # 喜：克我(官杀) + 我克(财) + 我生(食伤泄)
            base_xi = [WUXING_BEI_KE[day_wx], WUXING_KE[day_wx], WUXING_SHENG[day_wx]]
            # 忌：同我(比劫) + 生我(印)
            base_ji = [day_wx, WUXING_BEI_SHENG[day_wx]]  # 同我 + 生我
        elif ratio >= self.BALANCED_THRESHOLD:
            strength = '中和'
            base_xi = []
            base_ji = []
        else:
            strength = '身弱'
            # 喜：生我(印) + 同我(比劫)
            base_xi = [WUXING_BEI_SHENG[day_wx], day_wx]
            # 忌：克我(官杀) + 我克(财) + 我生(食伤)
            base_ji = [WUXING_BEI_KE[day_wx], WUXING_KE[day_wx], WUXING_SHENG[day_wx]]
        
        # 调候用神（优先于普通旺衰）
        # 从 data/tiaohou.json 读取完整逐月调候用神
        tiaohou_xi = []
        tiaohou_ji = []
        
        # 优先从缓存读取，回退到_calc_tiaohou（含硬编码回退表）
        tiaohou_str = ''
        if BaziEngine._tiaohou_cache:
            tiaohou_str = BaziEngine._tiaohou_cache.get(day_gan, {}).get(month_zhi, "")
        if not tiaohou_str:
            tiaohou_str = self._calc_tiaohou(day_gan, month_zhi)
        if tiaohou_str:
            # 调候用神天干 → 五行
            tiaohou_xi = list(dict.fromkeys(GAN_WUXING_STR.get(g, '') for g in tiaohou_str if GAN_WUXING_STR.get(g, '')))
        
        # 综合判断
        if strength == '中和' and tiaohou_xi:
            # 中和命局以调候为主
            xi = tiaohou_xi
            ji = [w for w in ['木', '火', '土', '金', '水'] if w not in xi]
            xian = []
            reason = f"中和命局，以调候用神为主：喜{'+'.join(xi)}"
        elif tiaohou_xi:
            # 扶抑为主，调候为辅
            # 调候用神如果与扶抑一致，增强权重；不一致时以扶抑为准
            xi = base_xi if base_xi else []
            # 如果调候提到的元素不在扶抑喜用中，不加入（避免泛喜）
            # 但如果调候忌的元素在扶抑喜用中，也不移除（扶抑优先）
            ji = base_ji if base_ji else [w for w in ['木', '火', '土', '金', '水'] if w not in xi]
            xian = []
            reason = f"{strength}，扶抑为主(喜{'+'.join(xi)})，调候参考(调{'+'.join(tiaohou_xi)})"
        else:
            # 中和无调候：无需特别扶抑，五行归入闲神
            if strength == '中和':
                xi = []
                ji = []
                xian = ['木', '火', '土', '金', '水']
                reason = f"中和命局，五行均衡，无需特别扶抑"
            else:
                xi = base_xi
                ji = base_ji
                xian = [w for w in ['木', '火', '土', '金', '水'] if w not in xi and w not in ji]
                reason = f"{strength}，无特殊调候：喜{'+'.join(xi)}"
        
        return {
            'xi': xi,
            'ji': ji,
            'xian': xian,
            'strength': strength,
            'reason': reason,
            'day_score': round(day_score, 1),
            'total_score': round(total, 1),
            'ratio': round(ratio * 100, 1),
        }

    def _calc_wuxing_score(self, pillars: list, hidden_gans: dict = None) -> Dict[str, float]:
        """
        五行得分计算。

        天干本气: 1分
        地支本气: 1分（月令本气加权1.5倍，体现月令为命局提纲）
        地支中气: 0.5分
        地支余气: 0.3分

        优先使用 analyze 中已校正的藏干数据（hidden_gans），
        确保五行得分与展示给用户的藏干一致。
        回退到 ZHI_CANGGAN（当 hidden_gans 未提供时）。
        """
        score: Dict[str, float] = {"木": 0.0, "火": 0.0, "土": 0.0, "金": 0.0, "水": 0.0}

        # 复用模块级常量 GAN_WUXING_STR（避免每次调用重复构建字典）
        gan_wuxing_map = GAN_WUXING_STR

        # 藏干得分权重（本气、中气、余气）
        BEN_QI_WEIGHT = 1.0        # 天干/地支本气基础分
        YUE_LING_BEN_QI = 1.5      # 月令本气加权（月令为命局提纲）
        ZHONG_QI_WEIGHT = 0.5      # 地支中气
        YU_QI_WEIGHT = 0.3         # 地支余气

        # 藏干数据来源：优先用已校正的 hidden_gans，回退到 ZHI_CANGGAN
        _HIDDEN_KEYS = ['year', 'month', 'day', 'time']

        for idx, pillar in enumerate(pillars):
            if not pillar:
                continue

            # 月令加权：月柱(索引1)本气得分体现"月令为命局提纲"
            is_month = (idx == 1)

            # 天干本气
            gan_wx = gan_wuxing_map.get(pillar.gan)
            if gan_wx:
                score[gan_wx] += BEN_QI_WEIGHT

            # 地支藏干：优先用已校正的 hidden_gans，回退到 ZHI_CANGGAN
            if hidden_gans and idx < len(_HIDDEN_KEYS):
                canggan_list = hidden_gans.get(_HIDDEN_KEYS[idx], [])
            else:
                canggan_list = ZHI_CANGGAN.get(pillar.zhi, [])
            # 防御：canggan_list 可能是字符串（如"己癸辛"）而非列表
            if isinstance(canggan_list, str):
                canggan_list = list(canggan_list)
            for cidx, canggan in enumerate(canggan_list):
                canggan_wx = gan_wuxing_map.get(canggan)
                if not canggan_wx:
                    continue
                if cidx == 0:
                    score[canggan_wx] += YUE_LING_BEN_QI if is_month else BEN_QI_WEIGHT
                elif cidx == 1:
                    score[canggan_wx] += ZHONG_QI_WEIGHT
                elif cidx == 2:
                    score[canggan_wx] += YU_QI_WEIGHT

        # 保留一位小数
        for k in score:
            score[k] = round(score[k], 1)

        return score
