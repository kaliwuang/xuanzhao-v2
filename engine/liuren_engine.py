#!/usr/bin/env python3
"""
玄照 v2.0 - 大六壬引擎（基于 kinliuren 库）

核心流程：
  1. 通过 lunar_python 获取四柱干支和节气
  2. 使用 kinliuren 库排盘：月将加时 → 天地盘 → 四课 → 三传 → 天将
  3. 返回标准化的结构化数据供 UDM 使用
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime, JIEQI_APPROX_TABLE
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# kinliuren 使用繁体中文节气名（模块级常量，避免每次 analyze() 调用重建字典）
SIMP_TO_TRAD_JIEQI = {
    '立春': '立春', '雨水': '雨水', '驚蟄': '驚蟄', '惊蛰': '驚蟄',
    '春分': '春分', '清明': '清明', '穀雨': '穀雨', '谷雨': '穀雨',
    '立夏': '立夏', '小满': '小滿', '小滿': '小滿', '芒种': '芒種', '芒種': '芒種',
    '夏至': '夏至', '小暑': '小暑', '大暑': '大暑', '立秋': '立秋',
    '处暑': '處暑', '處暑': '處暑', '白露': '白露', '秋分': '秋分',
    '寒露': '寒露', '霜降': '霜降', '立冬': '立冬', '小雪': '小雪',
    '大雪': '大雪', '冬至': '冬至', '小寒': '小寒', '大寒': '大寒',
}


# 十二天将含义（含kinliuren缩写映射，兼容繁简体）——模块级常量，避免每次调用重建
LIUREN_JIANG_YI = {
    "貴人": {"吉凶": "大吉", "含义": "贵人相助、提携"},
    "贵人": {"吉凶": "大吉", "含义": "贵人相助、提携"},
    "貴": {"吉凶": "大吉", "含义": "贵人相助、提携"},
    "贵": {"吉凶": "大吉", "含义": "贵人相助、提携"},
    "騰蛇": {"吉凶": "凶", "含义": "虚惊、怪异、纠缠"},
    "蛇": {"吉凶": "凶", "含义": "虚惊、怪异、纠缠"},
    "朱雀": {"吉凶": "凶", "含义": "口舌、文书、信息"},
    "雀": {"吉凶": "凶", "含义": "口舌、文书、信息"},
    "六合": {"吉凶": "吉", "含义": "合作、婚姻、和合"},
    "合": {"吉凶": "吉", "含义": "合作、婚姻、和合"},
    "勾陳": {"吉凶": "凶", "含义": "争斗、阻滞、官职"},
    "勾": {"吉凶": "凶", "含义": "争斗、阻滞、官职"},
    "青龍": {"吉凶": "大吉", "含义": "财喜、名声、晋升"},
    "龍": {"吉凶": "大吉", "含义": "财喜、名声、晋升"},
    "龙": {"吉凶": "大吉", "含义": "财喜、名声、晋升"},
    "天空": {"吉凶": "凶", "含义": "虚伪、空亡、欺骗"},
    "空": {"吉凶": "凶", "含义": "虚伪、空亡、欺骗"},
    "白虎": {"吉凶": "凶", "含义": "凶事、病伤、血光"},
    "虎": {"吉凶": "凶", "含义": "凶事、病伤、血光"},
    "太常": {"吉凶": "吉", "含义": "饮食、喜庆、宴席"},
    "常": {"吉凶": "吉", "含义": "饮食、喜庆、宴席"},
    "玄武": {"吉凶": "凶", "含义": "盗贼、暗昧、小人"},
    "武": {"吉凶": "凶", "含义": "盗贼、暗昧、小人"},
    "太陰": {"吉凶": "吉", "含义": "女眷、隐私、谋划"},
    "陰": {"吉凶": "吉", "含义": "女眷、隐私、谋划"},
    "阴": {"吉凶": "吉", "含义": "女眷、隐私、谋划"},
    "天后": {"吉凶": "大吉", "含义": "恩泽、庇护、婚姻"},
    "后": {"吉凶": "大吉", "含义": "恩泽、庇护、婚姻"},
}

# 天将五行
JIANG_WUXING = {
    "貴人": "土", "贵人": "土", "貴": "土", "贵": "土",
    "騰蛇": "火", "蛇": "火",
    "朱雀": "火", "雀": "火",
    "六合": "木", "合": "木",
    "勾陳": "土", "勾": "土",
    "青龍": "木", "龍": "木", "龙": "木",
    "天空": "土", "空": "土",
    "白虎": "金", "虎": "金",
    "太常": "土", "常": "土",
    "玄武": "水", "武": "水",
    "太陰": "金", "陰": "金", "阴": "金",
    "天后": "水", "后": "水",
}

# 天将阴阳
JIANG_YINYANG = {
    "貴人": "阳", "贵人": "阳", "貴": "阳", "贵": "阳",
    "騰蛇": "阴", "蛇": "阴",
    "朱雀": "阳", "雀": "阳",
    "六合": "阴", "合": "阴",
    "勾陳": "阳", "勾": "阳",
    "青龍": "阳", "龍": "阳", "龙": "阳",
    "天空": "阳", "空": "阳",
    "白虎": "阳", "虎": "阳",
    "太常": "阴", "常": "阴",
    "玄武": "阴", "武": "阴",
    "太陰": "阴", "陰": "阴", "阴": "阴",
    "天后": "阴", "后": "阴",
}

# 神煞体系（基于日干）
SHENSHA_DAY = {
    # 日干→神煞名→地支
    "甲": {"天乙贵人": "丑未", "文昌": "巳", "驿马": "寅", "桃花": "卯",
           "天德": "丁", "月德": "丙", "天喜": "申"},
    "乙": {"天乙贵人": "子申", "文昌": "午", "驿马": "巳", "桃花": "子",
           "天德": "申", "月德": "壬", "天喜": "酉"},
    "丙": {"天乙贵人": "亥酉", "文昌": "申", "驿马": "申", "桃花": "卯",
           "天德": "壬", "月德": "庚", "天喜": "戌"},
    "丁": {"天乙贵人": "亥酉", "文昌": "酉", "驿马": "亥", "桃花": "午",
           "天德": "甲", "月德": "丙", "天喜": "亥"},
    "戊": {"天乙贵人": "丑未", "文昌": "申", "驿马": "申", "桃花": "卯",
           "天德": "丙", "月德": "甲", "天喜": "子"},
    "己": {"天乙贵人": "子申", "文昌": "酉", "驿马": "亥", "桃花": "子",
           "天德": "壬", "月德": "庚", "天喜": "丑"},
    "庚": {"天乙贵人": "丑未", "文昌": "亥", "驿马": "寅", "桃花": "午",
           "天德": "丙", "月德": "丙", "天喜": "寅"},
    "辛": {"天乙贵人": "寅午", "文昌": "子", "驿马": "巳", "桃花": "酉",
           "天德": "甲", "月德": "甲", "天喜": "卯"},
    "壬": {"天乙贵人": "卯巳", "文昌": "寅", "驿马": "申", "桃花": "子",
           "天德": "丙", "月德": "壬", "天喜": "辰"},
    "癸": {"天乙贵人": "卯巳", "文昌": "卯", "驿马": "亥", "桃花": "酉",
           "天德": "壬", "月德": "庚", "天喜": "巳"},
}

# 神煞体系（基于日支）
SHENSHA_DAY_ZHI = {
    "子": {"华盖": "辰", "桃花": "酉", "驿马": "寅", "羊刃": "子"},
    "丑": {"华盖": "丑", "桃花": "午", "驿马": "亥", "羊刃": "丑"},
    "寅": {"华盖": "戌", "桃花": "卯", "驿马": "申", "羊刃": "寅"},
    "卯": {"华盖": "未", "桃花": "子", "驿马": "巳", "羊刃": "卯"},
    "辰": {"华盖": "辰", "桃花": "酉", "驿马": "寅", "羊刃": "辰"},
    "巳": {"华盖": "丑", "桃花": "午", "驿马": "亥", "羊刃": "巳"},
    "午": {"华盖": "戌", "桃花": "卯", "驿马": "申", "羊刃": "午"},
    "未": {"华盖": "未", "桃花": "子", "驿马": "巳", "羊刃": "未"},
    "申": {"华盖": "辰", "桃花": "酉", "驿马": "寅", "羊刃": "申"},
    "酉": {"华盖": "丑", "桃花": "午", "驿马": "亥", "羊刃": "酉"},
    "戌": {"华盖": "戌", "桃花": "卯", "驿马": "申", "羊刃": "戌"},
    "亥": {"华盖": "未", "桃花": "子", "驿马": "巳", "羊刃": "亥"},
}

# 地支六合
ZHI_LIUHE = {
    "子": "丑", "丑": "子", "寅": "亥", "亥": "寅",
    "卯": "戌", "戌": "卯", "辰": "酉", "酉": "辰",
    "巳": "申", "申": "巳", "午": "未", "未": "午",
}

# 地支六冲
ZHI_LIUCHONG = {
    "子": "午", "午": "子", "丑": "未", "未": "丑",
    "寅": "申", "申": "寅", "卯": "酉", "酉": "卯",
    "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳",
}

# 地支三合
ZHI_SANHE = {
    "申": "水", "子": "水", "辰": "水",
    "亥": "木", "卯": "木", "未": "木",
    "寅": "火", "午": "火", "戌": "火",
    "巳": "金", "酉": "金", "丑": "金",
}

# 地支三刑
ZHI_SANXING = {
    "寅": "巳", "巳": "申", "申": "寅",  # 无恩之刑
    "丑": "戌", "戌": "未", "未": "丑",  # 恃势之刑
    "子": "卯", "卯": "子",  # 无礼之刑
    "辰": "辰", "午": "午", "酉": "酉", "亥": "亥",  # 自刑
}

# 地支相害
ZHI_HAI = {
    "子": "未", "未": "子", "丑": "午", "午": "丑",
    "寅": "巳", "巳": "寅", "卯": "辰", "辰": "卯",
    "申": "亥", "亥": "申", "酉": "戌", "戌": "酉",
}

# 课格分类
KE_GE_TYPES = {
    # 三传格局
    "进茹": {"吉凶": "吉", "含义": "三传顺进，事主渐进"},
    "退茹": {"吉凶": "凶", "含义": "三传逆退，事主渐退"},
    "间传": {"吉凶": "中", "含义": "三传间断，事有阻隔"},
    "顺三合": {"吉凶": "大吉", "含义": "三传成三合局，和合大吉"},
    "逆三合": {"吉凶": "吉", "含义": "三传成三合局，和合"},
    "斩关": {"吉凶": "大凶", "含义": "三传克日干，主病伤灾厄"},
    "闭口": {"吉凶": "凶", "含义": "初传空亡，事无头绪"},
    "游子": {"吉凶": "凶", "含义": "三传皆马星，主出行变动"},
}

# 天将详细含义（扩展版）
JIANG_DETAIL = {
    "貴人": {"五行": "土", "方位": "中", "类象": "贵人、领导、长辈、权力",
             "疾病": "脾胃", "行人": "迟至", "失物": "可寻"},
    "贵人": {"五行": "土", "方位": "中", "类象": "贵人、领导、长辈、权力",
             "疾病": "脾胃", "行人": "迟至", "失物": "可寻"},
    "騰蛇": {"五行": "火", "方位": "南", "类象": "惊恐、怪异、缠绕、梦寐",
             "疾病": "心火", "行人": "虚惊", "失物": "难寻"},
    "蛇": {"五行": "火", "方位": "南", "类象": "惊恐、怪异、缠绕、梦寐",
           "疾病": "心火", "行人": "虚惊", "失物": "难寻"},
    "朱雀": {"五行": "火", "方位": "南", "类象": "文书、口舌、信息、考试",
             "疾病": "心火", "行人": "信至", "失物": "文书旁"},
    "雀": {"五行": "火", "方位": "南", "类象": "文书、口舌、信息、考试",
           "疾病": "心火", "行人": "信至", "失物": "文书旁"},
    "六合": {"五行": "木", "方位": "东", "类象": "合作、婚姻、交易、子孙",
             "疾病": "肝胆", "行人": "合至", "失物": "在合处"},
    "合": {"五行": "木", "方位": "东", "类象": "合作、婚姻、交易、子孙",
           "疾病": "肝胆", "行人": "合至", "失物": "在合处"},
    "勾陳": {"五行": "土", "方位": "中", "类象": "田土、争斗、牢狱、迟滞",
             "疾病": "脾胃", "行人": "迟滞", "失物": "在土中"},
    "勾": {"五行": "土", "方位": "中", "类象": "田土、争斗、牢狱、迟滞",
           "疾病": "脾胃", "行人": "迟滞", "失物": "在土中"},
    "青龍": {"五行": "木", "方位": "东", "类象": "财喜、名望、晋升、喜庆",
             "疾病": "肝胆", "行人": "喜至", "失物": "财处可寻"},
    "龍": {"五行": "木", "方位": "东", "类象": "财喜、名望、晋升、喜庆",
           "疾病": "肝胆", "行人": "喜至", "失物": "财处可寻"},
    "龙": {"五行": "木", "方位": "东", "类象": "财喜、名望、晋升、喜庆",
           "疾病": "肝胆", "行人": "喜至", "失物": "财处可寻"},
    "天空": {"五行": "土", "方位": "中", "类象": "虚伪、空亡、欺骗、僧道",
             "疾病": "中气虚", "行人": "不至", "失物": "难寻"},
    "空": {"五行": "土", "方位": "中", "类象": "虚伪、空亡、欺骗、僧道",
           "疾病": "中气虚", "行人": "不至", "失物": "难寻"},
    "白虎": {"五行": "金", "方位": "西", "类象": "凶事、病伤、血光、丧服",
             "疾病": "肺金", "行人": "凶至", "失物": "西方可寻"},
    "虎": {"五行": "金", "方位": "西", "类象": "凶事、病伤、血光、丧服",
           "疾病": "肺金", "行人": "凶至", "失物": "西方可寻"},
    "太常": {"五行": "土", "方位": "中", "类象": "饮食、喜庆、宴席、衣裳",
             "疾病": "脾胃", "行人": "宴至", "失物": "饮食处"},
    "常": {"五行": "土", "方位": "中", "类象": "饮食、喜庆、宴席、衣裳",
           "疾病": "脾胃", "行人": "宴至", "失物": "饮食处"},
    "玄武": {"五行": "水", "方位": "北", "类象": "盗贼、暗昧、小人、肾虚",
             "疾病": "肾水", "行人": "暗至", "失物": "难寻"},
    "武": {"五行": "水", "方位": "北", "类象": "盗贼、暗昧、小人、肾虚",
           "疾病": "肾水", "行人": "暗至", "失物": "难寻"},
    "太陰": {"五行": "金", "方位": "西", "类象": "女眷、隐私、谋划、暗助",
             "疾病": "肺金", "行人": "暗至", "失物": "暗处"},
    "陰": {"五行": "金", "方位": "西", "类象": "女眷、隐私、谋划、暗助",
           "疾病": "肺金", "行人": "暗至", "失物": "暗处"},
    "阴": {"五行": "金", "方位": "西", "类象": "女眷、隐私、谋划、暗助",
           "疾病": "肺金", "行人": "暗至", "失物": "暗处"},
    "天后": {"五行": "水", "方位": "北", "类象": "恩泽、庇护、婚姻、女性",
             "疾病": "肾水", "行人": "恩至", "失物": "女性处"},
    "后": {"五行": "水", "方位": "北", "类象": "恩泽、庇护、婚姻、女性",
           "疾病": "肾水", "行人": "恩至", "失物": "女性处"},
}


class LiuRenEngine(DivinationEngine):
    """大六壬引擎（kinliuren 库驱动）"""

    # 地支五行映射
    ZHI_ORDER = list("子丑寅卯辰巳午未申酉戌亥")

    ZHI_WUXING = {
        "子": "水", "丑": "土", "寅": "木", "卯": "木",
        "辰": "土", "巳": "火", "午": "火", "未": "土",
        "申": "金", "酉": "金", "戌": "土", "亥": "水",
    }

    # 天干五行映射
    GAN_WUXING = {
        "甲": "木", "乙": "木", "丙": "火", "丁": "火",
        "戊": "土", "己": "土", "庚": "金", "辛": "金",
        "壬": "水", "癸": "水",
    }

    # 五行生克
    SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

    @property
    def name(self) -> str:
        return "大六壬"

    @property
    def name_en(self) -> str:
        return "liuren"

    @property
    def priority(self) -> int:
        return 6

    # 月将名称映射
    YUE_JIANG_NAMES = {
        "亥": "登明", "戌": "河魁", "酉": "从魁", "申": "传送",
        "未": "小吉", "午": "胜光", "巳": "太乙", "辰": "天罡",
        "卯": "太冲", "寅": "功曹", "丑": "大吉", "子": "神后",
    }

    # 节气→月将地支映射
    # 规则：中气确定月将，节继承后一个中气的月将
    # 12中气→月将：大寒→子, 雨水→亥, 春分→戌, 谷雨→酉, 小满→申, 夏至→未,
    #              大暑→午, 处暑→巳, 秋分→辰, 霜降→卯, 小雪→寅, 冬至→丑
    JIEQI_TO_YUEJIANG = {
        # 中气
        "大寒": "子", "雨水": "亥", "春分": "戌",
        "谷雨": "酉", "小满": "申", "夏至": "未",
        "大暑": "午", "处暑": "巳", "秋分": "辰",
        "霜降": "卯", "小雪": "寅", "冬至": "丑",
        # 节（继承后一个中气的月将）
        # 规则：节的月将 = 该节所属中气期的月将（即后一个中气确定的月将）
        # 例：小寒在冬至→大寒之间，大寒→子，所以小寒=子
        "小寒": "子",   # 冬至→大寒期间，大寒→子
        "立春": "亥",   # 大寒→雨水期间，雨水→亥
        "惊蛰": "戌",   # 雨水→春分期间，春分→戌
        "清明": "酉",   # 春分→谷雨期间，谷雨→酉
        "立夏": "申",   # 谷雨→小满期间，小满→申
        "芒种": "未",   # 小满→夏至期间，夏至→未
        "小暑": "午",   # 夏至→大暑期间，大暑→午
        "立秋": "巳",   # 大暑→处暑期间，处暑→巳
        "白露": "辰",   # 处暑→秋分期间，秋分→辰
        "寒露": "卯",   # 秋分→霜降期间，霜降→卯
        "立冬": "寅",   # 霜降→小雪期间，小雪→寅
        "大雪": "丑",   # 小雪→冬至期间，冬至→丑
    }

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        """
        大六壬排盘主入口。

        使用 kinliuren 库进行排盘，返回标准化结构化数据。
        """
        orig = time.true_solar

        # ── 1. 获取四柱干支和节气（通过 lunar_python） ──
        try:
            from lunar_python import Solar

            # 晚子时使用bazi引擎统一的日期和时辰处理
            # bazi_day_pillar_date: 晚子时返回次日日期
            # bazi_hour: 晚子时返回0（子时），避免lunar_python内部再做一次晚子时判定导致日柱偏移
            pillar_date = time.bazi_day_pillar_date
            bazi_hour = time.bazi_hour

            solar = Solar.fromYmdHms(
                pillar_date.year, pillar_date.month, pillar_date.day,
                bazi_hour, orig.minute, 0
            )
            lunar = solar.getLunar()
            ec = lunar.getEightChar()

            year_gan = ec.getYearGan()
            year_zhi = ec.getYearZhi()
            month_gan = ec.getMonthGan()
            month_zhi = ec.getMonthZhi()
            day_gan = ec.getDayGan()
            day_zhi = ec.getDayZhi()
            time_gan = ec.getTimeGan()
            time_zhi = ec.getTimeZhi()

            # 节气（用于月将判定）
            jieqi_name = self._get_current_jieqi(lunar)
        except Exception as e:
            logger.warning(f"lunar_python获取四柱干支失败，使用默认值: {e}")
            year_gan, year_zhi = "甲", "子"
            month_gan, month_zhi = "甲", "子"
            day_gan, day_zhi = "甲", "子"
            time_gan, time_zhi = "甲", "子"
            jieqi_name = "冬至"

        # ── 2. 月将 ──
        yue_jiang_zhi = self.JIEQI_TO_YUEJIANG.get(jieqi_name, "丑")
        yue_jiang_name = self.YUE_JIANG_NAMES.get(yue_jiang_zhi, "大吉")

        # ── 3. 占时（时支，使用 bazi_hour 保持与日柱时柱一致的晚子时处理） ──
        bazi_h = time.bazi_hour
        hour_zhi_idx = (bazi_h + 1) // 2 % 12
        zhan_shi = self.ZHI_ORDER[hour_zhi_idx]

        # ── 4. 日干寄宫 ──
        shigangjigong = dict(
            zip(
                list("甲乙丙丁戊己庚辛壬癸") + list("子丑寅卯辰巳午未申酉戌亥"),
                list("寅辰巳未巳未申戌亥丑") + list("子丑寅卯辰巳午未申酉戌亥"),
            )
        )
        gan_ji = shigangjigong.get(day_gan, "寅")

        # ── 5. 使用 kinliuren 库排盘 ──
        try:
            from kinliuren.kinliuren import Liuren

            day_ganzhi = day_gan + day_zhi
            hour_ganzhi = time_gan + time_zhi

            jieqi_trad = SIMP_TO_TRAD_JIEQI.get(jieqi_name, jieqi_name)
            lr = Liuren(jieqi_trad, month_zhi, day_ganzhi, hour_ganzhi)
            lr_result = lr.result(0)

            # 提取四课
            si_ke_raw = lr_result.get("四課", {})
            si_ke = (
                si_ke_raw.get("一課", []),
                si_ke_raw.get("二課", []),
                si_ke_raw.get("三課", []),
                si_ke_raw.get("四課", []),
            )

            # 提取三传
            san_chuan_raw = lr_result.get("三傳", {})
            san_chuan = (
                san_chuan_raw.get("初傳", []),
                san_chuan_raw.get("中傳", []),
                san_chuan_raw.get("末傳", []),
            )

            # 提取天地盘
            tian_pan_raw = lr_result.get("天地盤", {})
            di_pan_list = tian_pan_raw.get("地盤", self.ZHI_ORDER)
            tian_pan_list = tian_pan_raw.get("天盤", self.ZHI_ORDER)
            tian_jiang_list = tian_pan_raw.get("天將", [""] * 12)

            # 天盘：地支→天盘地支
            tian_pan = {}
            for i, zhi in enumerate(self.ZHI_ORDER):
                if i < len(tian_pan_list):
                    tian_pan[zhi] = tian_pan_list[i]
                else:
                    tian_pan[zhi] = zhi

            # 天将：地支→天将
            tian_jiang = {}
            di_zhi_order = self.ZHI_ORDER
            for i, zhi in enumerate(di_zhi_order):
                if i < len(tian_jiang_list):
                    tian_jiang[zhi] = tian_jiang_list[i]
                else:
                    tian_jiang[zhi] = ""

            # 也可以用库自带的地转天盘/地转天将
            di_to_tian = lr_result.get("地轉天盤", tian_pan)
            di_to_jiang = lr_result.get("地轉天將", tian_jiang)

            # 格局
            ge_ju = lr_result.get("格局", [])
            ge_ju_name = "·".join(ge_ju) if ge_ju else ""

            # 日马
            day_ma = lr_result.get("日馬", "")

            # 用神分析（基于三传初传）
            yong_shen_analysis = self._analyze_yong_shen(
                san_chuan_raw, si_ke_raw, day_gan, tian_jiang
            )

            # 四课详细解读
            si_ke_analysis = self._analyze_si_ke(si_ke_raw, day_gan, tian_jiang)

        except Exception as e:
            # kinliuren 不可用时，返回最小可用结构
            logger.warning(f"kinliuren排盘失败，使用最小可用结构: {e}")
            si_ke = ([], [], [], [])
            san_chuan = ([], [], [])
            tian_pan = {zhi: zhi for zhi in self.ZHI_ORDER}
            tian_jiang = {zhi: "" for zhi in self.ZHI_ORDER}
            di_to_tian = tian_pan.copy()
            di_to_jiang = tian_jiang.copy()
            ge_ju_name = ""
            day_ma = ""
            yong_shen_analysis = {}
            si_ke_analysis = {}
            si_ke_raw = {}
            san_chuan_raw = {}
            di_to_tian = tian_pan.copy()
            di_to_jiang = tian_jiang.copy()

        # ── 6. 合并十二宫信息（便于前端渲染） ──
        positions = {}
        for zhi in self.ZHI_ORDER:
            positions[zhi] = {
                "zhi": zhi,
                "wuxing": self.ZHI_WUXING.get(zhi, ""),
                "di_zhi": zhi,
                "tian_zhi": di_to_tian.get(zhi, zhi),
                "tian_jiang": di_to_jiang.get(zhi, ""),
            }

        # ── 7. 构造返回字典 ──
        # 确保四课/三传是list（JSON序列化兼容）
        si_ke_list = [list(k) if isinstance(k, (tuple, list)) else k for k in si_ke]
        san_chuan_list = [list(c) if isinstance(c, (tuple, list)) else c for c in san_chuan]

        return {
            # 引擎标识
            "engine": self.name,
            "engine_en": self.name_en,
            # 四柱
            "year_gan": year_gan,
            "year_zhi": year_zhi,
            "month_gan": month_gan,
            "month_zhi": month_zhi,
            "day_gan": day_gan,
            "day_zhi": day_zhi,
            "time_gan": time_gan,
            "time_zhi": time_zhi,
            # 占时与月将
            "zhan_shi": zhan_shi,
            "yue_jiang": yue_jiang_name,
            "yue_jiang_zhi": yue_jiang_zhi,
            # 节气
            "jieqi": jieqi_name,
            # 天盘（地支→天盘地支）
            "tian_pan": di_to_tian,
            # 十二宫位置（便于前端渲染）
            "positions": positions,
            # 日干寄宫
            "gan_ji": gan_ji,
            # 四课（list of 4）
            "si_ke": si_ke_list,
            # 三传（list of 3）
            "san_chuan": san_chuan_list,
            # 天将（地支→天将）
            "tian_jiang": di_to_jiang,
            # 附加信息
            "ge_ju": ge_ju_name,
            "day_ma": day_ma,
            "yong_shen": yong_shen_analysis,
            "si_ke_analysis": si_ke_analysis,
            "date": orig.strftime("%Y-%m-%d %H:%M"),
            # 新增分析
            "shensha": self._analyze_shensha(day_gan, day_zhi, tian_jiang),
            "san_chuan_detail": self._analyze_san_chuan_detail(san_chuan_raw, day_gan, tian_jiang),
            "jiang_arrangement": self._analyze_jiang_arrangement(di_to_jiang, day_gan),
            "xun_kong": self._calc_xun_kong(day_gan, day_zhi),
            "zhi_relations": self._analyze_zhi_relations(tian_jiang, di_to_tian),
            # #6: 四课六亲关系
            "si_ke_liuqin": self._analyze_si_ke_liuqin(si_ke_raw, day_gan),
            # #7: 三传进退茹
            "jin_tui": self._analyze_jin_tui(san_chuan_raw),
            # #8: 天将临课分析
            "jiang_on_ke": self._analyze_jiang_on_ke(si_ke_raw, tian_jiang),
            # #9: 课传五行统计
            "wuxing_stats": self._analyze_wuxing_stats(si_ke_raw, san_chuan_raw),
            # #10: 天地盘生克关系
            "tiandi_relations": self._analyze_tiandi_relations(di_to_tian),
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        """
        验证排盘结果是否合理。

        检查：
        0. 无引擎错误
        1. 四课不为空
        2. 三传不为空
        """
        if data.get('error'):
            return False, data['error']

        si_ke = data.get("si_ke")
        if not si_ke or (isinstance(si_ke, list) and all(not k for k in si_ke)):
            return False, "四课为空"

        san_chuan = data.get("san_chuan")
        if not san_chuan or (isinstance(san_chuan, list) and all(not c for c in san_chuan)):
            return False, "三传为空"

        return True, None

    def _analyze_si_ke(self, si_ke_raw: dict, day_gan: str, tian_jiang: dict) -> dict:
        """四课详细解读"""
        if not si_ke_raw or not isinstance(si_ke_raw, dict):
            return {}
        analysis = {}

        KE_NAMES = {'一課': '干上神（日上）', '二課': '干阳神', '三課': '支上神（辰上）', '四課': '支阳神'}

        day_wx = self.GAN_WUXING.get(day_gan, '')

        for key in ['一課', '二課', '三課', '四課']:
            val = si_ke_raw.get(key, [])
            if not val or len(val) < 2:
                continue
            # 防御：val[0]可能为None或非字符串类型，安全转换
            raw_gz = val[0]
            if raw_gz is None:
                continue
            gz = str(raw_gz) if not isinstance(raw_gz, str) else raw_gz
            if not gz:
                continue
            jiang = val[1] if len(val) > 1 and val[1] is not None else ''
            jiang = str(jiang) if not isinstance(jiang, str) else jiang

            zhi = gz[-1] if gz else ''
            wx = self.ZHI_WUXING.get(zhi, '')

            # 判断该课与日干的关系
            relation = ''
            if wx and day_wx:
                if wx == day_wx:
                    relation = '比和'
                elif self.SHENG.get(day_wx) == wx:
                    relation = '我生'
                elif self.SHENG.get(wx) == day_wx:
                    relation = '生我'
                elif self.KE.get(day_wx) == wx:
                    relation = '我克'
                elif self.KE.get(wx) == day_wx:
                    relation = '克我'

            analysis[key] = {
                'name': KE_NAMES.get(key, key),
                'gan_zhi': gz,
                'tian_jiang': jiang,
                'wuxing': wx,
                'relation_to_day': relation,
            }

        return analysis

    def _analyze_yong_shen(self, san_chuan_raw: dict, si_ke_raw: dict,
                           day_gan: str, tian_jiang: dict) -> dict:
        """分析用神：基于三传初传的天将和六亲关系"""
        if not san_chuan_raw or not isinstance(san_chuan_raw, dict):
            return {}

        # 初传信息
        chu_chuan = san_chuan_raw.get("初傳", [])
        chu_zhi = chu_chuan[0] if chu_chuan else ""
        chu_jiang = chu_chuan[1] if len(chu_chuan) > 1 else ""
        chu_liuqin = chu_chuan[2] if len(chu_chuan) > 2 else ""

        # 初传天将含义
        jiang_info = LIUREN_JIANG_YI.get(chu_jiang, {"吉凶": "中", "含义": ""})

        # 日干五行
        day_wx = self.GAN_WUXING.get(day_gan, "")
        chu_wx = self.ZHI_WUXING.get(chu_zhi, "")

        # 初传与日干的关系
        relation = ""
        if day_wx and chu_wx:
            if day_wx == chu_wx:
                relation = "比和"
            elif self.SHENG.get(day_wx) == chu_wx:
                relation = "我生（泄气）"
            elif self.SHENG.get(chu_wx) == day_wx:
                relation = "生我（得助）"
            elif self.KE.get(day_wx) == chu_wx:
                relation = "我克（得财）"
            elif self.KE.get(chu_wx) == day_wx:
                relation = "克我（受制）"

        return {
            "chu_chuan_zhi": chu_zhi,
            "chu_chuan_jiang": chu_jiang,
            "chu_chuan_liuqin": chu_liuqin,
            "jiang_ji_xiong": jiang_info.get("吉凶", ""),
            "jiang_han_yi": jiang_info.get("含义", ""),
            "ri_gan_relation": relation,
        }

    def _get_current_jieqi(self, lunar) -> str:
        """获取当前节气（用于月将判定）"""
        try:
            prev_jieqi = lunar.getPrevJieQi()
            if prev_jieqi:
                return prev_jieqi.getName()
        except Exception as e:
            logger.debug(f"六壬getPrevJieQi异常，尝试近似表: {e}")

        try:
            current_solar = lunar.getSolar()
            current_md = (current_solar.getMonth(), current_solar.getDay())

            prev_name = "冬至"
            for name, m, d in JIEQI_APPROX_TABLE:
                if current_md < (m, d):
                    break
                prev_name = name
            return prev_name
        except Exception as e:
            logger.debug(f"六壬节气近似表计算异常，回退农历月份估算: {e}")

        # 最终回退：按农历月份估算节气（用于月将判定）
        # 月将由中气决定，节继承后一个中气的月将
        # 农历月份与"节"对应：正月→立春, 二月→惊蛰, ..., 十一月→大雪, 十二月→小寒
        # lunar_python 闰月返回负数（如闰四月=-4），取绝对值映射到同月节气
        # 改进：区分月内前半段（节，继承前中气月将）和后半段（中气，用当月中气月将）
        month = abs(lunar.getMonth())
        day = lunar.getDay()
        # 防御：month为0时回退到冬至（子月），避免字典查找失败
        if month < 1 or month > 12:
            month = 12
        # 节（每月前半段，约初一至十四）
        jie_approx = {
            1: "立春", 2: "惊蛰", 3: "清明", 4: "立夏",
            5: "芒种", 6: "小暑", 7: "立秋", 8: "白露",
            9: "寒露", 10: "立冬", 11: "大雪", 12: "小寒",
        }
        # 中气（每月后半段，约十五至三十）
        zhongqi_approx = {
            1: "雨水", 2: "春分", 3: "谷雨", 4: "小满",
            5: "夏至", 6: "大暑", 7: "处暑", 8: "秋分",
            9: "霜降", 10: "小雪", 11: "冬至", 12: "大寒",
        }
        # 各月中气在农历中的近似日期（用于替代粗糙的 day>=15 截断）
        # 大多数中气落在农历十二至二十三之间，但各月差异较大
        ZHONGQI_LUNAR_DAY = {
            1: 18, 2: 19, 3: 19, 4: 19, 5: 20, 6: 21,
            7: 22, 8: 22, 9: 22, 10: 23, 11: 21, 12: 20,
        }
        zhongqi_day = ZHONGQI_LUNAR_DAY.get(month, 15)
        if day >= zhongqi_day:
            return zhongqi_approx.get(month, "冬至")
        return jie_approx.get(month, "冬至")

    # ---- 大六壬引擎改进 #1-10: 核心分析方法补全 ----

    # #1: 神煞分析
    def _analyze_shensha(self, day_gan: str, day_zhi: str, tian_jiang: dict) -> dict:
        """#1: 神煞落宫分析 - 基于日干和日支"""
        result = {}
        # 基于日干的神煞
        day_shensha = SHENSHA_DAY.get(day_gan, {})
        for sha_name, sha_zhi in day_shensha.items():
            # 神煞地支可能有多个字符（如"丑未"）
            for z in sha_zhi:
                if z in self.ZHI_ORDER:
                    jiang = tian_jiang.get(z, '') if tian_jiang else ''
                    result[sha_name] = {
                        'zhi': z, 'tian_jiang': jiang,
                        'wuxing': self.ZHI_WUXING.get(z, ''),
                    }
                    break  # 取第一个有效地支

        # 基于日支的神煞
        day_zhi_sha = SHENSHA_DAY_ZHI.get(day_zhi, {})
        for sha_name, sha_zhi in day_zhi_sha.items():
            for z in sha_zhi:
                if z in self.ZHI_ORDER:
                    jiang = tian_jiang.get(z, '') if tian_jiang else ''
                    result[f'日支{sha_name}'] = {
                        'zhi': z, 'tian_jiang': jiang,
                        'wuxing': self.ZHI_WUXING.get(z, ''),
                    }
                    break
        return result

    # #2: 三传详细分析
    def _analyze_san_chuan_detail(self, san_chuan_raw: dict, day_gan: str, tian_jiang: dict) -> dict:
        """#2: 三传详细分析 - 初传/中传/末传的天将、五行、六亲关系"""
        if not san_chuan_raw or not isinstance(san_chuan_raw, dict):
            return {}

        day_wx = self.GAN_WUXING.get(day_gan, '')
        detail = {}

        for chuan_name, chuan_key in [('初傳', 'chu'), ('中傳', 'zhong'), ('末傳', 'mo')]:
            chuan = san_chuan_raw.get(chuan_name, [])
            if not chuan or len(chuan) < 1:
                continue
            zhi = chuan[0] if chuan[0] else ''
            jiang = chuan[1] if len(chuan) > 1 and chuan[1] else ''
            liuqin = chuan[2] if len(chuan) > 2 and chuan[2] else ''
            wx = self.ZHI_WUXING.get(zhi, '')

            # 与日干的关系
            relation = ''
            if day_wx and wx:
                if wx == day_wx: relation = '比和'
                elif self.SHENG.get(day_wx) == wx: relation = '我生'
                elif self.SHENG.get(wx) == day_wx: relation = '生我'
                elif self.KE.get(day_wx) == wx: relation = '我克'
                elif self.KE.get(wx) == day_wx: relation = '克我'

            # 天将含义
            jiang_info = LIUREN_JIANG_YI.get(jiang, {'吉凶': '中', '含义': ''})
            jiang_detail = JIANG_DETAIL.get(jiang, {})

            detail[chuan_key] = {
                'zhi': zhi, 'jiang': jiang, 'liuqin': liuqin,
                'wuxing': wx, 'relation': relation,
                'jiang_jixiong': jiang_info.get('吉凶', ''),
                'jiang_hanyi': jiang_info.get('含义', ''),
                'jiang_leixiang': jiang_detail.get('类象', ''),
            }
        return detail

    # #3: 天将排列分析
    def _analyze_jiang_arrangement(self, di_to_jiang: dict, day_gan: str) -> dict:
        """#3: 天将排列分析 - 十二天将分布在十二宫的吉凶统计"""
        if not di_to_jiang:
            return {}

        ji_count = 0
        xiong_count = 0
        ji_jiang = []
        xiong_jiang = []

        for zhi, jiang in di_to_jiang.items():
            if not jiang:
                continue
            info = LIUREN_JIANG_YI.get(jiang, {})
            jx = info.get('吉凶', '中')
            if jx in ('大吉', '吉'):
                ji_count += 1
                ji_jiang.append({'zhi': zhi, 'jiang': jiang, 'jixiong': jx})
            elif jx == '凶':
                xiong_count += 1
                xiong_jiang.append({'zhi': zhi, 'jiang': jiang, 'jixiong': jx})

        # 贵人位置
        guiren_pos = ''
        for zhi, jiang in di_to_jiang.items():
            if jiang in ('貴人', '贵人', '貴', '贵'):
                guiren_pos = zhi
                break

        return {
            'ji_count': ji_count, 'xiong_count': xiong_count,
            'ji_jiang': ji_jiang, 'xiong_jiang': xiong_jiang,
            'guiren_pos': guiren_pos,
            'summary': f'吉将{ji_count}个，凶将{xiong_count}个' +
                       (f'，贵人在{guiren_pos}' if guiren_pos else ''),
        }

    # #4: 旬空计算
    def _calc_xun_kong(self, day_gan: str, day_zhi: str) -> dict:
        """#4: 旬空计算 - 日柱所在旬的空亡地支"""
        TIANGAN = list('甲乙丙丁戊己庚辛壬癸')
        DIZHI = list('子丑寅卯辰巳午未申酉戌亥')
        if not day_gan or not day_zhi:
            return {}
        gan_idx = TIANGAN.index(day_gan) if day_gan in TIANGAN else 0
        zhi_idx = DIZHI.index(day_zhi) if day_zhi in DIZHI else 0
        xun_start = (zhi_idx - gan_idx) % 12
        xun_shou = TIANGAN[0] + DIZHI[xun_start]
        kong1 = DIZHI[(xun_start + 10) % 12]
        kong2 = DIZHI[(xun_start + 11) % 12]
        return {
            'xun_shou': xun_shou,
            'kong_wang': [kong1, kong2],
            'desc': f'旬首{xun_shou}，空亡{kong1}{kong2}',
        }

    # #5: 地支关系分析（天将所在地支间的关系）
    def _analyze_zhi_relations(self, tian_jiang: dict, di_to_tian: dict) -> dict:
        """#5: 地支关系分析 - 天将所在地支间的六合/六冲/三合/三刑/相害"""
        if not tian_jiang:
            return {}

        relations = []
        zhi_list = [z for z in self.ZHI_ORDER if tian_jiang.get(z)]

        for i, z1 in enumerate(zhi_list):
            for z2 in zhi_list[i+1:]:
                # 六合
                if ZHI_LIUHE.get(z1) == z2:
                    j1 = tian_jiang.get(z1, '')
                    j2 = tian_jiang.get(z2, '')
                    relations.append({
                        'type': '六合', 'zhi1': z1, 'zhi2': z2,
                        'jiang1': j1, 'jiang2': j2,
                        'desc': f'{z1}{j1}与{z2}{j2}六合',
                    })
                # 六冲
                if ZHI_LIUCHONG.get(z1) == z2:
                    j1 = tian_jiang.get(z1, '')
                    j2 = tian_jiang.get(z2, '')
                    relations.append({
                        'type': '六冲', 'zhi1': z1, 'zhi2': z2,
                        'jiang1': j1, 'jiang2': j2,
                        'desc': f'{z1}{j1}与{z2}{j2}六冲',
                    })

        return {
            'total': len(relations),
            'relations': relations,
            'summary': f'共{len(relations)}组地支关系',
        }

    # #6: 四课与日干六亲关系
    def _analyze_si_ke_liuqin(self, si_ke_raw: dict, day_gan: str) -> dict:
        """#6: 四课与日干六亲关系 - 每课地支五行与日干五行的生克"""
        if not si_ke_raw or not isinstance(si_ke_raw, dict):
            return {}
        day_wx = self.GAN_WUXING.get(day_gan, '')
        result = {}
        KE_NAMES = {'一課': '干上神', '二課': '干阳', '三課': '支上神', '四課': '支阳'}

        for key in ['一課', '二課', '三課', '四課']:
            val = si_ke_raw.get(key, [])
            if not val or len(val) < 1:
                continue
            gz = str(val[0]) if val[0] else ''
            if not gz:
                continue
            zhi = gz[-1]
            wx = self.ZHI_WUXING.get(zhi, '')
            liuqin = ''
            if day_wx and wx:
                if wx == day_wx: liuqin = '兄弟'
                elif self.SHENG.get(day_wx) == wx: liuqin = '子孙'
                elif self.SHENG.get(wx) == day_wx: liuqin = '父母'
                elif self.KE.get(day_wx) == wx: liuqin = '妻财'
                elif self.KE.get(wx) == day_wx: liuqin = '官鬼'

            result[key] = {
                'name': KE_NAMES.get(key, key),
                'gan_zhi': gz, 'zhi': zhi, 'wuxing': wx,
                'liuqin': liuqin,
            }
        return result

    # #7: 三传进退茹判定
    def _analyze_jin_tui(self, san_chuan_raw: dict) -> dict:
        """#7: 三传进退茹判定 - 三传地支是否连续顺进或逆退"""
        if not san_chuan_raw or not isinstance(san_chuan_raw, dict):
            return {}

        chu = san_chuan_raw.get('初傳', [])
        zhong = san_chuan_raw.get('中傳', [])
        mo = san_chuan_raw.get('末傳', [])

        if not chu or not zhong or not mo:
            return {}

        z1 = str(chu[0])[-1] if chu[0] else ''
        z2 = str(zhong[0])[-1] if zhong[0] else ''
        z3 = str(mo[0])[-1] if mo[0] else ''

        if not z1 or not z2 or not z3:
            return {}

        idx1 = self.ZHI_ORDER.index(z1) if z1 in self.ZHI_ORDER else -1
        idx2 = self.ZHI_ORDER.index(z2) if z2 in self.ZHI_ORDER else -1
        idx3 = self.ZHI_ORDER.index(z3) if z3 in self.ZHI_ORDER else -1

        if idx1 < 0 or idx2 < 0 or idx3 < 0:
            return {}

        # 连续顺进
        if (idx2 - idx1) % 12 == 1 and (idx3 - idx2) % 12 == 1:
            ge = KE_GE_TYPES.get('进茹', {})
            return {'type': '进茹', 'desc': ge.get('含义', '三传顺进'), '吉凶': ge.get('吉凶', '中')}
        # 连续逆退
        if (idx1 - idx2) % 12 == 1 and (idx2 - idx3) % 12 == 1:
            ge = KE_GE_TYPES.get('退茹', {})
            return {'type': '退茹', 'desc': ge.get('含义', '三传逆退'), '吉凶': ge.get('吉凶', '中')}
        # 间传（隔一位）
        if (idx2 - idx1) % 12 == 2 and (idx3 - idx2) % 12 == 2:
            ge = KE_GE_TYPES.get('间传', {})
            return {'type': '间传', 'desc': ge.get('含义', '三传间断'), '吉凶': ge.get('吉凶', '中')}

        return {'type': '', 'desc': ''}

    # #8: 天将临课分析
    def _analyze_jiang_on_ke(self, si_ke_raw: dict, tian_jiang: dict) -> dict:
        """#8: 天将临四课分析 - 每课上神所临天将"""
        if not si_ke_raw or not isinstance(si_ke_raw, dict):
            return {}

        result = {}
        for key in ['一課', '二課', '三課', '四課']:
            val = si_ke_raw.get(key, [])
            if not val or len(val) < 2:
                continue
            gz = str(val[0]) if val[0] else ''
            jiang = str(val[1]) if len(val) > 1 and val[1] else ''
            zhi = gz[-1] if gz else ''

            jiang_info = LIUREN_JIANG_YI.get(jiang, {})
            jiang_detail = JIANG_DETAIL.get(jiang, {})

            result[key] = {
                'gan_zhi': gz, 'zhi': zhi,
                'jiang': jiang,
                'jiang_jixiong': jiang_info.get('吉凶', ''),
                'jiang_hanyi': jiang_info.get('含义', ''),
                'jiang_leixiang': jiang_detail.get('类象', ''),
                'jiang_wuxing': JIANG_WUXING.get(jiang, ''),
            }
        return result

    # #9: 课传五行统计
    def _analyze_wuxing_stats(self, si_ke_raw: dict, san_chuan_raw: dict) -> dict:
        """#9: 课传五行统计 - 四课三传中各五行出现次数"""
        stats = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}

        def count_zhi(val):
            if not val:
                return
            gz = str(val[0]) if val[0] else ''
            if gz:
                zhi = gz[-1]
                wx = self.ZHI_WUXING.get(zhi, '')
                if wx in stats:
                    stats[wx] += 1

        # 四课
        if si_ke_raw:
            for key in ['一課', '二課', '三課', '四課']:
                count_zhi(si_ke_raw.get(key, []))

        # 三传
        if san_chuan_raw:
            for key in ['初傳', '中傳', '末傳']:
                count_zhi(san_chuan_raw.get(key, []))

        dominant = max(stats, key=stats.get) if any(stats.values()) else ''
        return {
            'stats': stats,
            'dominant': dominant,
            'summary': f'五行分布：{" ".join(f"{k}{v}" for k, v in stats.items() if v > 0)}' +
                       (f'，以{dominant}为主' if dominant else ''),
        }

    # #10: 天地盘生克关系
    def _analyze_tiandi_relations(self, di_to_tian: dict) -> dict:
        """#10: 天地盘生克关系 - 地支与天盘地支的五行生克"""
        if not di_to_tian:
            return {}

        relations = []
        for di_zhi, tian_zhi in di_to_tian.items():
            di_wx = self.ZHI_WUXING.get(di_zhi, '')
            tian_wx = self.ZHI_WUXING.get(tian_zhi, '')
            if not di_wx or not tian_wx:
                continue

            rel = ''
            if di_wx == tian_wx:
                rel = '比和'
            elif self.SHENG.get(di_wx) == tian_wx:
                rel = '地生天'
            elif self.SHENG.get(tian_wx) == di_wx:
                rel = '天生地'
            elif self.KE.get(di_wx) == tian_wx:
                rel = '地克天'
            elif self.KE.get(tian_wx) == di_wx:
                rel = '天克地'

            if rel and rel != '比和':
                relations.append({
                    'di_zhi': di_zhi, 'tian_zhi': tian_zhi,
                    'di_wuxing': di_wx, 'tian_wuxing': tian_wx,
                    'relation': rel,
                })

        return {
            'total': len(relations),
            'relations': relations,
        }
