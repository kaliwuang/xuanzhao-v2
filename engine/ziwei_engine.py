#!/usr/bin/env python3
"""
玄照 v2.0 - 紫微斗数引擎（标准安星版）

基于紫微斗数全书标准排盘算法实现。
支持：命宫、身宫、五行局、十四主星、六吉星、四化、十二宫。

安星流程：
1. 定命宫（寅起正月，顺数生月，逆数生时）
2. 定身宫（寅起正月，顺数生月，顺数生时）
3. 定五行局（命宫干支纳音）
4. 起紫微（局数除日数，商数定宫位）
5. 安紫微星系（逆布）：紫微、天机、空、太阳、武曲、天同、空、廉贞
6. 安天府星系（顺布）：天府、太阴、贪狼、巨门、天相、天梁、七杀、破军
7. 安辅星：禄存、擎羊、陀罗、天魁、天钺、左辅、右弼、文昌、文曲
8. 安四化
9. 排十二宫
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

    # 十二宫名称（固定逆时针顺序）
    PALACES = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄",
               "迁移", "奴仆", "官禄", "田宅", "福德", "父母"]

    # 地支
    ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    # 天干
    GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    # 五虎遁月（寅月天干）
    WUHU_MONTH = {
        "甲": "丙", "己": "丙",
        "乙": "戊", "庚": "戊",
        "丙": "庚", "辛": "庚",
        "丁": "壬", "壬": "壬",
        "戊": "甲", "癸": "甲",
    }

    # 六十甲子纳音五行局
    JU_MAP = {
        # 水二局
        ("丙", "子"): ("水", 2), ("丁", "丑"): ("水", 2),
        ("甲", "子"): ("水", 2), ("乙", "丑"): ("水", 2),
        ("壬", "辰"): ("水", 2), ("癸", "巳"): ("水", 2),
        ("庚", "辰"): ("水", 2), ("辛", "巳"): ("水", 2),
        ("戊", "午"): ("水", 2), ("己", "未"): ("水", 2),
        ("丙", "午"): ("水", 2), ("丁", "未"): ("水", 2),
        # 木三局
        ("壬", "寅"): ("木", 3), ("癸", "卯"): ("木", 3),
        ("庚", "寅"): ("木", 3), ("辛", "卯"): ("木", 3),
        ("戊", "辰"): ("木", 3), ("己", "巳"): ("木", 3),
        ("丙", "辰"): ("木", 3), ("丁", "巳"): ("木", 3),
        ("甲", "寅"): ("木", 3), ("乙", "卯"): ("木", 3),
        # 金四局
        ("壬", "申"): ("金", 4), ("癸", "酉"): ("金", 4),
        ("庚", "申"): ("金", 4), ("辛", "酉"): ("金", 4),
        ("甲", "辰"): ("金", 4), ("乙", "巳"): ("金", 4),
        ("丙", "申"): ("金", 4), ("丁", "酉"): ("金", 4),
        # 土五局
        ("甲", "午"): ("土", 5), ("乙", "未"): ("土", 5),
        ("丙", "戌"): ("土", 5), ("丁", "亥"): ("土", 5),
        ("戊", "申"): ("土", 5), ("己", "酉"): ("土", 5),
        ("庚", "戌"): ("土", 5), ("辛", "亥"): ("土", 5),
        ("壬", "午"): ("土", 5), ("癸", "未"): ("土", 5),
        # 火六局
        ("戊", "子"): ("火", 6), ("己", "丑"): ("火", 6),
        ("丙", "寅"): ("火", 6), ("丁", "卯"): ("火", 6),
        ("甲", "戌"): ("火", 6), ("乙", "亥"): ("火", 6),
        ("壬", "子"): ("火", 6), ("癸", "丑"): ("火", 6),
        ("庚", "子"): ("火", 6), ("辛", "丑"): ("火", 6),
    }

    # 四化表
    SIHUA_TABLE = {
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

    # 禄存安宫（由生年天干定）
    LU_CUN = {
        "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午",
        "戊": "巳", "己": "午", "庚": "申", "辛": "酉",
        "壬": "亥", "癸": "子",
    }

    # 天魁安宫
    TIAN_KUI = {
        "甲": "丑", "乙": "子", "丙": "亥", "丁": "酉",
        "戊": "丑", "己": "子", "庚": "丑", "辛": "午",
        "壬": "卯", "癸": "卯",
    }

    # 天钺安宫
    TIAN_YUE = {
        "甲": "未", "乙": "申", "丙": "酉", "丁": "亥",
        "戊": "未", "己": "申", "庚": "未", "辛": "寅",
        "壬": "巳", "癸": "巳",
    }

    def __init__(self):
        self._available = True

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        dt = time.true_solar
        hour = dt.hour

        from lunar_python import Solar
        solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
        lunar = solar.getLunar()
        year_gan = lunar.getYearGan()
        lunar_month = lunar.getMonth()
        lunar_day = lunar.getDay()

        # 1. 定命宫
        yin_idx = 2
        shi_idx = ((hour + 1) // 2) % 12
        ming_idx = (yin_idx + lunar_month - 1 - shi_idx) % 12
        ming_gong = self.ZHI[ming_idx]

        # 2. 定身宫
        shen_idx = (yin_idx + lunar_month - 1 + shi_idx) % 12
        shen_gong = self.ZHI[shen_idx]

        # 3. 定命宫天干（五虎遁月 + 顺推）
        yin_gan = self.WUHU_MONTH.get(year_gan, "丙")
        yin_gan_idx = self.GAN.index(yin_gan)
        steps = (ming_idx - yin_idx) % 12
        ming_gan = self.GAN[(yin_gan_idx + steps) % 10]

        # 4. 定五行局
        ming_ganzhi = ming_gan + ming_gong
        wuxing_ju = self._get_wuxing_ju(ming_ganzhi)

        # 5. 起紫微星（返回地支索引）
        ziwei_zhi_idx = self._place_ziwei(wuxing_ju[1], lunar_day)

        # 6. 安十四主星（返回 {星名: 地支索引}）
        star_zhi = self._place_main_stars(ziwei_zhi_idx)

        # 7. 安辅星
        aux_stars = self._place_auxiliary_stars(year_gan, lunar_month, shi_idx, star_zhi)
        star_zhi.update(aux_stars)

        # 8. 安四化
        sihua = self.SIHUA_TABLE.get(year_gan, {"禄": "", "权": "", "科": "", "忌": ""})

        # 9. 排十二宫（地支映射到宫名）
        palaces = self._arrange_palaces(ming_idx, star_zhi)

        # 生成 {星名: 宫名} 映射
        star_placements = {}
        for star, zhi in star_zhi.items():
            for p in palaces:
                if p["zhi"] == self.ZHI[zhi]:
                    star_placements[star] = p["name"]
                    break

        return {
            "ming_gong": ming_gong,
            "shen_gong": shen_gong,
            "ming_ganzhi": ming_ganzhi,
            "wuxing_ju": {"wuxing": wuxing_ju[0], "ju_shu": wuxing_ju[1]},
            "ziwei_zhi": self.ZHI[ziwei_zhi_idx],
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

    def _get_wuxing_ju(self, ming_ganzhi: str) -> tuple:
        """返回 (五行, 局数)"""
        gan = ming_ganzhi[0] if len(ming_ganzhi) > 0 else "甲"
        zhi = ming_ganzhi[1] if len(ming_ganzhi) > 1 else "子"
        return self.JU_MAP.get((gan, zhi), ("水", 2))

    def _place_ziwei(self, ju_shu: int, lunar_day: int) -> int:
        """安紫微星，返回地支索引。

        算法：从亥宫起，每局数个生日推进一宫（顺时针）。
        口诀对应：
          水二局 1-2日→亥，3-4日→子...
          火六局 1-6日→亥，7-12日→子...
        """
        step = (lunar_day - 1) // ju_shu
        return (11 + step) % 12  # 从亥(11)起顺时针

    def _place_main_stars(self, ziwei_zhi_idx: int) -> Dict[str, int]:
        """安十四主星，返回 {星名: 地支索引}。"""
        star_zhi = {}

        # 紫微星系（逆布，从紫微位置开始）
        ziwei_xing = ["紫微", "天机", "", "太阳", "武曲", "天同", "", "廉贞"]
        for i, star in enumerate(ziwei_xing):
            if star:
                star_zhi[star] = (ziwei_zhi_idx - i) % 12

        # 天府与紫微相对（相隔6宫），天府星系（顺布）
        tianfu_zhi_idx = (ziwei_zhi_idx + 6) % 12
        tianfu_xing = ["天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"]
        for i, star in enumerate(tianfu_xing):
            star_zhi[star] = (tianfu_zhi_idx + i) % 12

        return star_zhi

    def _place_auxiliary_stars(self, year_gan: str, lunar_month: int,
                                shi_idx: int, star_zhi: Dict[str, int]) -> Dict[str, int]:
        """安辅星，返回 {星名: 地支索引}。"""
        aux = {}

        # 禄存（由生年天干定）
        lu_cun_zhi = self.ZHI.index(self.LU_CUN.get(year_gan, "寅"))
        aux["禄存"] = lu_cun_zhi

        # 擎羊（禄存前一位，顺时针）
        aux["擎羊"] = (lu_cun_zhi + 1) % 12

        # 陀罗（禄存后一位，逆时针）
        aux["陀罗"] = (lu_cun_zhi - 1) % 12

        # 天魁（由生年天干定）
        aux["天魁"] = self.ZHI.index(self.TIAN_KUI.get(year_gan, "丑"))

        # 天钺（由生年天干定）
        aux["天钺"] = self.ZHI.index(self.TIAN_YUE.get(year_gan, "未"))

        # 左辅（由生月定，正月辰起顺行）
        # 辰=4，正月=1，左辅在辰；二月=2，左辅在巳...
        zuo_fu_idx = (4 + lunar_month - 1) % 12
        aux["左辅"] = zuo_fu_idx

        # 右弼（由生月定，正月戌起逆行）
        # 戌=10，正月=1，右弼在戌；二月=2，右弼在酉...
        you_bi_idx = (10 - (lunar_month - 1)) % 12
        aux["右弼"] = you_bi_idx

        # 文昌（由生时定，子时戌起逆行）
        # 戌=10，子时=0，文昌在戌；丑时=1，文昌在酉...
        wen_chang_idx = (10 - shi_idx) % 12
        aux["文昌"] = wen_chang_idx

        # 文曲（由生时定，子时辰起顺行）
        # 辰=4，子时=0，文曲在辰；丑时=1，文曲在巳...
        wen_qu_idx = (4 + shi_idx) % 12
        aux["文曲"] = wen_qu_idx

        return aux

    def _arrange_palaces(self, ming_idx: int, star_zhi: Dict[str, int]) -> List[Dict]:
        """排十二宫。紫微斗数十二宫从命宫开始逆时针排列。"""
        palaces = []
        for i, name in enumerate(self.PALACES):
            # 逆时针：从命宫开始，每次减1
            zhi_idx = (ming_idx - i) % 12
            zhi = self.ZHI[zhi_idx]
            stars_in_palace = [s for s, z in star_zhi.items() if z == zhi_idx]
            palaces.append({
                "name": name,
                "zhi": zhi,
                "stars": stars_in_palace,
            })
        return palaces
