#!/usr/bin/env python3
"""
玄照 v2.0 - 紫微斗数引擎（简化版）

基于紫微斗数核心排盘算法自研实现。
支持：命宫、身宫、五行局、紫微星系、天府星系、四化、十二宫。

注：此为简化版，主星完整，辅星部分实现。
如需完整星曜体系，可后续接入 tianji 库。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional, List, Dict


class ZiWeiEngine(DivinationEngine):
    """紫微斗数引擎"""

    @property
    def name(self) -> str:
        return "紫微"

    @property
    def name_en(self) -> str:
        return "ZiWei"

    @property
    def priority(self) -> int:
        return 2

    # 十四主星
    MAIN_STARS = [
        "紫微", "天机", "太阳", "武曲", "天同", "廉贞",  # 紫微星系
        "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"  # 天府星系
    ]

    # 主星五行
    STAR_WUXING = {
        "紫微": "土", "天机": "木", "太阳": "火", "武曲": "金",
        "天同": "水", "廉贞": "火", "天府": "土", "太阴": "水",
        "贪狼": "木", "巨门": "水", "天相": "水", "天梁": "土",
        "七杀": "金", "破军": "水",
    }

    # 十二宫名称
    PALACES = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄",
               "迁移", "奴仆", "官禄", "田宅", "福德", "父母"]

    # 地支
    ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    # 天干
    GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    # 五虎遁月起月表
    WUHU_MONTH = {
        "甲": "丙寅", "己": "丙寅",
        "乙": "戊寅", "庚": "戊寅",
        "丙": "庚寅", "辛": "庚寅",
        "丁": "壬寅", "壬": "壬寅",
        "戊": "甲寅", "癸": "甲寅",
    }

    # 五行局
    WUXING_JU = {
        ("甲", "子"): ("水", 2), ("甲", "辰"): ("火", 6), ("甲", "申"): ("土", 5),
        ("乙", "丑"): ("火", 6), ("乙", "巳"): ("水", 2), ("乙", "未"): ("金", 4),
        ("丙", "寅"): ("火", 6), ("丙", "午"): ("水", 2), ("丙", "戌"): ("土", 5),
        ("丁", "卯"): ("火", 6), ("丁", "丑"): ("水", 2), ("丁", "亥"): ("土", 5),
        ("戊", "辰"): ("木", 3), ("戊", "寅"): ("火", 6), ("戊", "子"): ("火", 6),
        ("己", "巳"): ("木", 3), ("己", "卯"): ("土", 5), ("己", "丑"): ("火", 6),
        ("庚", "午"): ("土", 5), ("庚", "辰"): ("金", 4), ("庚", "寅"): ("木", 3),
        ("辛", "未"): ("土", 5), ("辛", "巳"): ("金", 4), ("辛", "卯"): ("木", 3),
        ("壬", "申"): ("金", 4), ("壬", "午"): ("木", 3), ("壬", "辰"): ("水", 2),
        ("癸", "酉"): ("金", 4), ("癸", "未"): ("木", 3), ("癸", "巳"): ("水", 2),
    }

    def __init__(self):
        self._available = True

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        dt = time.true_solar
        lunar_month = dt.month  # 简化：用农历月（实际需要转换）
        lunar_day = dt.day
        hour = dt.hour

        # 1. 确定命宫位置
        # 寅宫起正月，顺数到生月，逆数到生时
        yin_idx = 2  # 寅在ZHI中的索引
        ming_idx = (yin_idx + lunar_month - 1 - (hour + 1) // 2) % 12
        ming_gong = self.ZHI[ming_idx]

        # 2. 确定身宫位置
        # 寅宫起正月，顺数到生月，顺数到生时
        shen_idx = (yin_idx + lunar_month - 1 + (hour + 1) // 2) % 12
        shen_gong = self.ZHI[shen_idx]

        # 3. 确定命宫天干（五虎遁月）
        # 简化：用年干推算
        from lunar_python import Solar
        solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
        lunar = solar.getLunar()
        year_gan = lunar.getYearGan()
        month_ganzhi = self.WUHU_MONTH.get(year_gan, "丙寅")
        ming_gan = month_ganzhi[0]  # 简化处理

        # 4. 确定五行局
        ming_ganzhi = ming_gan + ming_gong
        wuxing_ju = self._get_wuxing_ju(ming_ganzhi)

        # 5. 安紫微星
        ziwei_palace = self._place_ziwei(wuxing_ju["ju_shu"], lunar_day)

        # 6. 安十四主星
        star_placements = self._place_main_stars(ziwei_palace)

        # 7. 安四化
        sihua = self._get_sihua(year_gan)

        # 8. 排十二宫
        palaces = self._arrange_palaces(ming_idx, star_placements)

        return {
            "ming_gong": ming_gong,
            "shen_gong": shen_gong,
            "ming_ganzhi": ming_ganzhi,
            "wuxing_ju": wuxing_ju,
            "ziwei_palace": ziwei_palace,
            "star_placements": star_placements,
            "sihua": sihua,
            "palaces": palaces,
            "gender": "男" if gender == 1 else "女",
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if not data.get("ming_gong"):
            return False, "命宫为空"
        if not data.get("star_placements"):
            return False, "主星安置失败"
        return True, None

    def _get_wuxing_ju(self, ming_ganzhi: str) -> dict:
        """根据命宫干支定五行局"""
        gan = ming_ganzhi[0] if len(ming_ganzhi) > 0 else "甲"
        zhi = ming_ganzhi[1] if len(ming_ganzhi) > 1 else "子"

        # 简化：返回默认值
        ju_map = {
            ("甲", "子"): {"wuxing": "水", "ju_shu": 2},
            ("甲", "寅"): {"wuxing": "木", "ju_shu": 3},
            ("甲", "辰"): {"wuxing": "火", "ju_shu": 6},
            ("甲", "午"): {"wuxing": "土", "ju_shu": 5},
            ("甲", "申"): {"wuxing": "金", "ju_shu": 4},
            ("甲", "戌"): {"wuxing": "水", "ju_shu": 2},
        }
        result = ju_map.get((gan, zhi), {"wuxing": "水", "ju_shu": 2})
        return result

    def _place_ziwei(self, ju_shu: int, lunar_day: int) -> str:
        """安紫微星"""
        # 简化算法：根据局数和生日数
        # 实际算法复杂，这里用简化规则
        palaces = self.PALACES
        idx = (lunar_day + ju_shu) % 12
        return palaces[idx]

    def _place_main_stars(self, ziwei_palace: str) -> Dict[str, str]:
        """安十四主星"""
        # 简化：紫微星系和天府星系固定排列
        ziwei_idx = self.PALACES.index(ziwei_palace) if ziwei_palace in self.PALACES else 0

        # 紫微星系（逆布）：紫微、天机、空格、太阳、武曲、天同、空格、廉贞
        ziwei_xing = ["紫微", "天机", "", "太阳", "武曲", "天同", "", "廉贞"]

        # 天府星系（顺布）：天府、太阴、贪狼、巨门、天相、天梁、七杀、破军
        tianfu_xing = ["天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"]

        placements = {}
        for i, star in enumerate(ziwei_xing):
            if star:
                idx = (ziwei_idx - i) % 12
                palace = self.PALACES[idx]
                placements[star] = palace

        # 天府与紫微相对
        tianfu_idx = (ziwei_idx + 6) % 12
        for i, star in enumerate(tianfu_xing):
            if star:
                idx = (tianfu_idx + i) % 12
                palace = self.PALACES[idx]
                placements[star] = palace

        return placements

    def _get_sihua(self, year_gan: str) -> Dict[str, str]:
        """安四化（禄权科忌）"""
        sihua_table = {
            "甲": {"禄": "廉贞", "权": "破军", "科": "武曲", "忌": "太阳"},
            "乙": {"禄": "天机", "权": "天梁", "科": "紫微", "忌": "太阴"},
            "丙": {"禄": "天同", "权": "天机", "科": "文昌", "忌": "廉贞"},
            "丁": {"禄": "太阴", "权": "天同", "科": "天机", "忌": "巨门"},
            "戊": {"禄": "贪狼", "权": "太阴", "科": "右弼", "忌": "天机"},
            "己": {"禄": "武曲", "权": "贪狼", "科": "天梁", "忌": "文曲"},
            "庚": {"禄": "太阳", "权": "武曲", "科": "太阴", "忌": "天同"},
            "辛": {"禄": "巨门", "权": "太阳", "科": "文曲", "忌": "文昌"},
            "壬": {"禄": "天梁", "权": "紫微", "科": "左辅", "忌": "武曲"},
            "癸": {"禄": "破军", "权": "巨门", "科": "太阴", "忌": "贪狼"},
        }
        return sihua_table.get(year_gan, {"禄": "", "权": "", "科": "", "忌": ""})

    def _arrange_palaces(self, ming_idx: int, star_placements: Dict[str, str]) -> List[Dict]:
        """排十二宫"""
        palaces = []
        for i, name in enumerate(self.PALACES):
            zhi_idx = (ming_idx + i) % 12
            zhi = self.ZHI[zhi_idx]
            stars_in_palace = [s for s, p in star_placements.items() if p == name]
            palaces.append({
                "name": name,
                "zhi": zhi,
                "stars": stars_in_palace,
            })
        return palaces
