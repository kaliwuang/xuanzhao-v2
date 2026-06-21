#!/usr/bin/env python3
"""
玄照 v2.0 - 统一数据模型 (Unified Destiny Model)

所有术法引擎输出到同一个数据结构，便于交叉比对。
不绑定任何具体术法，是时间-空间-能量的抽象。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class Wuxing(Enum):
    WOOD = "木"
    FIRE = "火"
    EARTH = "土"
    METAL = "金"
    WATER = "水"


class Yinyang(Enum):
    YANG = "阳"
    YIN = "阴"


# 天干五行阴阳映射
GAN_WUXING = {
    "甲": (Wuxing.WOOD, Yinyang.YANG),
    "乙": (Wuxing.WOOD, Yinyang.YIN),
    "丙": (Wuxing.FIRE, Yinyang.YANG),
    "丁": (Wuxing.FIRE, Yinyang.YIN),
    "戊": (Wuxing.EARTH, Yinyang.YANG),
    "己": (Wuxing.EARTH, Yinyang.YIN),
    "庚": (Wuxing.METAL, Yinyang.YANG),
    "辛": (Wuxing.METAL, Yinyang.YIN),
    "壬": (Wuxing.WATER, Yinyang.YANG),
    "癸": (Wuxing.WATER, Yinyang.YIN),
}

# 地支五行阴阳映射
ZHI_WUXING = {
    "子": (Wuxing.WATER, Yinyang.YANG),
    "丑": (Wuxing.EARTH, Yinyang.YIN),
    "寅": (Wuxing.WOOD, Yinyang.YANG),
    "卯": (Wuxing.WOOD, Yinyang.YIN),
    "辰": (Wuxing.EARTH, Yinyang.YANG),
    "巳": (Wuxing.FIRE, Yinyang.YIN),
    "午": (Wuxing.FIRE, Yinyang.YANG),
    "未": (Wuxing.EARTH, Yinyang.YIN),
    "申": (Wuxing.METAL, Yinyang.YANG),
    "酉": (Wuxing.METAL, Yinyang.YIN),
    "戌": (Wuxing.EARTH, Yinyang.YANG),
    "亥": (Wuxing.WATER, Yinyang.YIN),
}

# 地支藏干
ZHI_CANGGAN = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "戊", "庚"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}

# 天干五合
GAN_WUHE = {
    "甲": "己", "己": "甲",
    "乙": "庚", "庚": "乙",
    "丙": "辛", "辛": "丙",
    "丁": "壬", "壬": "丁",
    "戊": "癸", "癸": "戊",
}

# 地支六合
ZHI_LIUHE = {
    "子": "丑", "丑": "子",
    "寅": "亥", "亥": "寅",
    "卯": "戌", "戌": "卯",
    "辰": "酉", "酉": "辰",
    "巳": "申", "申": "巳",
    "午": "未", "未": "午",
}

# 五行字符集合（纳音解析用）
WUXING_CHARS = {'金', '木', '水', '火', '土'}

# 地支六冲
ZHI_CHONG = {
    "子": "午", "午": "子",
    "丑": "未", "未": "丑",
    "寅": "申", "申": "寅",
    "卯": "酉", "酉": "卯",
    "辰": "戌", "戌": "辰",
    "巳": "亥", "亥": "巳",
}

# 地支三合
ZHI_SANHE = [
    {"申", "子", "辰"},  # 水局
    {"亥", "卯", "未"},  # 木局
    {"寅", "午", "戌"},  # 火局
    {"巳", "酉", "丑"},  # 金局
]

# 地支三会
ZHI_SANHUI = [
    {"亥", "子", "丑"},  # 北方水
    {"寅", "卯", "辰"},  # 东方木
    {"巳", "午", "未"},  # 南方火
    {"申", "酉", "戌"},  # 西方金
]

# 十神（以日干为日主）
SHISHEN_MAP = {
    # 日主甲（阳木）
    ("甲", "甲"): "比肩", ("甲", "乙"): "劫财",
    ("甲", "丙"): "食神", ("甲", "丁"): "伤官",
    ("甲", "戊"): "偏财", ("甲", "己"): "正财",
    ("甲", "庚"): "七杀", ("甲", "辛"): "正官",
    ("甲", "壬"): "偏印", ("甲", "癸"): "正印",
    # 日主乙（阴木）
    ("乙", "乙"): "比肩", ("乙", "甲"): "劫财",
    ("乙", "丁"): "食神", ("乙", "丙"): "伤官",
    ("乙", "己"): "偏财", ("乙", "戊"): "正财",
    ("乙", "辛"): "七杀", ("乙", "庚"): "正官",
    ("乙", "癸"): "偏印", ("乙", "壬"): "正印",
    # 日主丙（阳火）
    ("丙", "丙"): "比肩", ("丙", "丁"): "劫财",
    ("丙", "戊"): "食神", ("丙", "己"): "伤官",
    ("丙", "庚"): "偏财", ("丙", "辛"): "正财",
    ("丙", "壬"): "七杀", ("丙", "癸"): "正官",
    ("丙", "甲"): "偏印", ("丙", "乙"): "正印",
    # 日主丁（阴火）
    ("丁", "丁"): "比肩", ("丁", "丙"): "劫财",
    ("丁", "己"): "食神", ("丁", "戊"): "伤官",
    ("丁", "辛"): "偏财", ("丁", "庚"): "正财",
    ("丁", "癸"): "七杀", ("丁", "壬"): "正官",
    ("丁", "乙"): "偏印", ("丁", "甲"): "正印",
    # 日主戊（阳土）
    ("戊", "戊"): "比肩", ("戊", "己"): "劫财",
    ("戊", "庚"): "食神", ("戊", "辛"): "伤官",
    ("戊", "壬"): "偏财", ("戊", "癸"): "正财",
    ("戊", "甲"): "七杀", ("戊", "乙"): "正官",
    ("戊", "丙"): "偏印", ("戊", "丁"): "正印",
    # 日主己（阴土）
    ("己", "己"): "比肩", ("己", "戊"): "劫财",
    ("己", "辛"): "食神", ("己", "庚"): "伤官",
    ("己", "癸"): "偏财", ("己", "壬"): "正财",
    ("己", "乙"): "七杀", ("己", "甲"): "正官",
    ("己", "丁"): "偏印", ("己", "丙"): "正印",
    # 日主庚（阳金）
    ("庚", "庚"): "比肩", ("庚", "辛"): "劫财",
    ("庚", "壬"): "食神", ("庚", "癸"): "伤官",
    ("庚", "甲"): "偏财", ("庚", "乙"): "正财",
    ("庚", "丙"): "七杀", ("庚", "丁"): "正官",
    ("庚", "戊"): "偏印", ("庚", "己"): "正印",
    # 日主辛（阴金）
    ("辛", "辛"): "比肩", ("辛", "庚"): "劫财",
    ("辛", "癸"): "食神", ("辛", "壬"): "伤官",
    ("辛", "乙"): "偏财", ("辛", "甲"): "正财",
    ("辛", "丁"): "七杀", ("辛", "丙"): "正官",
    ("辛", "己"): "偏印", ("辛", "戊"): "正印",
    # 日主壬（阳水）
    ("壬", "壬"): "比肩", ("壬", "癸"): "劫财",
    ("壬", "甲"): "食神", ("壬", "乙"): "伤官",
    ("壬", "丙"): "偏财", ("壬", "丁"): "正财",
    ("壬", "戊"): "七杀", ("壬", "己"): "正官",
    ("壬", "庚"): "偏印", ("壬", "辛"): "正印",
    # 日主癸（阴水）
    ("癸", "癸"): "比肩", ("癸", "壬"): "劫财",
    ("癸", "乙"): "食神", ("癸", "甲"): "伤官",
    ("癸", "丁"): "偏财", ("癸", "丙"): "正财",
    ("癸", "己"): "七杀", ("癸", "戊"): "正官",
    ("癸", "辛"): "偏印", ("癸", "庚"): "正印",
}


@dataclass
class Pillar:
    """柱（年/月/日/时）"""
    gan: str                    # 天干
    zhi: str                    # 地支
    nayin: Optional[str] = None  # 纳音

    @property
    def ganzhi(self) -> str:
        return self.gan + self.zhi

    @property
    def wuxing(self) -> str:
        """柱的五行（以纳音为主，无纳音用干支五行）"""
        if self.nayin:
            last_char = self.nayin[-1]
            if last_char in WUXING_CHARS:
                return last_char
            # 回退：遍历纳音字符串找五行
            for ch in reversed(self.nayin):
                if ch in WUXING_CHARS:
                    return ch
        gz_wx = GAN_WUXING.get(self.gan, (None, None))[0]
        return gz_wx.value if gz_wx else ""


@dataclass
class DestinyModel:
    """
    统一命盘数据模型。
    所有术法引擎填充这个模型，视角引擎读取这个模型。
    """
    # === 时空锚点 ===
    corrected_time: Optional[Any] = None

    # === 八字数据 ===
    bazi_year: Optional[Pillar] = None
    bazi_month: Optional[Pillar] = None
    bazi_day: Optional[Pillar] = None
    bazi_time: Optional[Pillar] = None
    day_master: Optional[str] = None      # 日主天干
    day_master_wuxing: Optional[str] = None

    # 藏干
    hidden_gans: Dict[str, List[str]] = field(default_factory=dict)

    # 十神（按天干）
    shishen_gan: Dict[str, str] = field(default_factory=dict)

    # 十神（按地支藏干）
    shishen_zhi: Dict[str, List[str]] = field(default_factory=dict)

    # 纳音
    nayin: Dict[str, str] = field(default_factory=dict)

    # 空亡
    xunkong: Dict[str, str] = field(default_factory=dict)

    # 大运
    dayun: List[Dict] = field(default_factory=list)
    dayun_start_year: int = 0
    dayun_start_age: int = 0

    # 调候用神
    tiaohou: Optional[str] = None

    # 神煞
    shensha: List[str] = field(default_factory=list)

    # 每柱神煞（按柱分组）
    shensha_per_pillar: Dict[str, List[str]] = field(default_factory=dict)

    # 长生十二宫（每柱）
    changsheng: Dict[str, str] = field(default_factory=dict)

    # 干支关系（天干冲合、地支刑冲合害）
    gan_relations: List[str] = field(default_factory=list)
    zhi_relations: List[str] = field(default_factory=list)

    # === 紫微数据 ===
    ziwei_chart: Optional[Dict] = None

    # === 六爻数据 ===
    liuyao_chart: Optional[Dict] = None

    # === 奇门数据 ===
    qimen_chart: Optional[Dict] = None

    # === 大六壬数据 ===
    liuren_chart: Optional[Dict] = None

    # === 太乙数据 ===
    taiyi_chart: Optional[Dict] = None

    # === 占星数据 ===
    astro_chart: Optional[Dict] = None

    # === 姓名学数据 ===
    xingming_chart: Optional[Dict] = None

    # === 引擎错误记录 ===
    engine_errors: Dict[str, str] = field(default_factory=dict)

    # === 特征提取（交叉验证用）===
    features: List[str] = field(default_factory=list)

    # === 五行得分 ===
    wuxing_score: Dict[str, float] = field(default_factory=dict)

    # === 命宫·胎元·身宫 ===
    ming_gong: Optional[str] = None
    ming_gong_shishen: Optional[Dict] = None
    tai_yuan: Optional[str] = None
    tai_yuan_shishen: Optional[Dict] = None
    shen_gong: Optional[str] = None
    shen_gong_shishen: Optional[Dict] = None

    # 喜用神
    xi_yong: Dict = field(default_factory=dict)

    # 当前流年
    liunian: Optional[Dict] = None

    # 出生地经纬度
    location: Optional[Dict] = None

    # 出生公历年份（交叉验证用）
    birth_year: int = 0

    @property
    def bazi_pillars(self) -> List[Optional[Pillar]]:
        return [self.bazi_year, self.bazi_month, self.bazi_day, self.bazi_time]

    @property
    def zhis(self) -> List[str]:
        """四地支"""
        return [p.zhi for p in self.bazi_pillars if p]

    @property
    def gans(self) -> List[str]:
        """四天干"""
        return [p.gan for p in self.bazi_pillars if p]

    def get_shishen(self, gan: str) -> str:
        """获取某天干对日主的十神"""
        if not self.day_master:
            return ""
        return SHISHEN_MAP.get((self.day_master, gan), "")

    def get_chong(self) -> List[str]:
        """返回所有冲的组合"""
        zhis = self.zhis
        result = []
        for i, z1 in enumerate(zhis):
            for j, z2 in enumerate(zhis[i+1:], i+1):
                if ZHI_CHONG.get(z1) == z2:
                    result.append(f"{z1}{z2}冲")
        return result

    def get_he(self) -> List[str]:
        """返回所有合的组合"""
        zhis = self.zhis
        result = []
        # 六合
        for i, z1 in enumerate(zhis):
            for j, z2 in enumerate(zhis[i+1:], i+1):
                if ZHI_LIUHE.get(z1) == z2:
                    result.append(f"{z1}{z2}合")
        # 三合
        zhi_set = set(zhis)
        for sanhe in ZHI_SANHE:
            if len(zhi_set & sanhe) == 2:
                matched = zhi_set & sanhe
                result.append(f"{' '.join(matched)}半合")
            if sanhe <= zhi_set:
                result.append(f"{' '.join(sanhe)}三合")
        # 三会
        for sanhui in ZHI_SANHUI:
            if sanhui <= zhi_set:
                result.append(f"{' '.join(sanhui)}三会")
        return result

    def get_wuxing_count(self) -> Dict[str, int]:
        """五行统计（天干+地支本气）"""
        counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        for g in self.gans:
            wx = GAN_WUXING.get(g, (None, None))[0]
            if wx:
                counts[wx.value] = counts.get(wx.value, 0) + 1
        for z in self.zhis:
            wx = ZHI_WUXING.get(z, (None, None))[0]
            if wx:
                counts[wx.value] = counts.get(wx.value, 0) + 1
        return counts

    def get_dayun_ganzhi(self) -> List[str]:
        """获取大运干支列表"""
        return [d.get("ganzhi", "") for d in self.dayun]

    def get_available_methods(self) -> List[str]:
        """获取已排盘的术法列表"""
        methods = []
        if self.bazi_year:
            methods.append("八字")
        if self.ziwei_chart:
            methods.append("紫微")
        if self.liuyao_chart:
            methods.append("六爻")
        if self.qimen_chart:
            methods.append("奇门")
        if self.liuren_chart:
            methods.append("大六壬")
        if self.taiyi_chart:
            methods.append("太乙")
        if self.astro_chart:
            methods.append("占星")
        if self.xingming_chart:
            methods.append("姓名学")
        return methods
