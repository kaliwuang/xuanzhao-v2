#!/usr/bin/env python3
"""
玄照 v2.0 - 太乙神数引擎（简化版）

核心：太乙积年数、太乙行宫、九宫定位、三基五福。

注：太乙神数算法极复杂，此为简化版，保留核心框架。
如需完整排盘，可后续接入 kintaiyi 库。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional


class TaiYiEngine(DivinationEngine):
    """太乙神数引擎"""

    @property
    def name(self) -> str:
        return "太乙"

    @property
    def name_en(self) -> str:
        return "TaiYi"

    @property
    def priority(self) -> int:
        return 6

    # 九宫
    JIUGONG = ["坎一宫", "坤二宫", "震三宫", "巽四宫", "中五宫",
               "乾六宫", "兑七宫", "艮八宫", "离九宫"]

    # 太乙积年起点（黄帝元年 = 公元前2697年）
    HUANGDI_YEAR = -2697

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        dt = time.true_solar
        year = dt.year

        # 1. 计算太乙积年数
        ji_nian = self._calc_ji_nian(year)

        # 2. 确定太乙所在宫位
        taiyi_gong = self._get_taiyi_gong(ji_nian)

        # 3. 确定阴阳遁
        yin_yang = self._get_yin_yang(year)

        # 4. 三基（君基、臣基、民基）
        san_ji = self._get_san_ji(ji_nian)

        # 5. 五福（大游、小游、四神、五帝、天乙）
        wu_fu = self._get_wu_fu(ji_nian)

        return {
            "year": year,
            "ji_nian": ji_nian,
            "taiyi_gong": taiyi_gong,
            "yin_yang": yin_yang,
            "san_ji": san_ji,
            "wu_fu": wu_fu,
            "date": dt.strftime("%Y-%m-%d %H:%M"),
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if not data.get("taiyi_gong"):
            return False, "太乙宫位为空"
        return True, None

    def _calc_ji_nian(self, year: int) -> int:
        """计算太乙积年数"""
        # 简化：从黄帝元年算起
        return year - self.HUANGDI_YEAR

    def _get_taiyi_gong(self, ji_nian: int) -> str:
        """确定太乙所在宫位"""
        # 太乙每宫3年，9宫一圈27年
        gong_idx = (ji_nian // 3) % 9
        return self.JIUGONG[gong_idx]

    def _get_yin_yang(self, year: int) -> str:
        """确定阴阳遁"""
        # 阳年阳遁，阴年阴遁
        gan_idx = (year - 4) % 10
        if gan_idx in [0, 2, 4, 6, 8]:  # 甲丙戊庚壬
            return "阳遁"
        else:
            return "阴遁"

    def _get_san_ji(self, ji_nian: int) -> dict:
        """三基"""
        return {
            "君基": self.JIUGONG[ji_nian % 9],
            "臣基": self.JIUGONG[(ji_nian + 3) % 9],
            "民基": self.JIUGONG[(ji_nian + 6) % 9],
        }

    def _get_wu_fu(self, ji_nian: int) -> dict:
        """五福"""
        return {
            "大游": self.JIUGONG[(ji_nian + 1) % 9],
            "小游": self.JIUGONG[(ji_nian + 2) % 9],
            "四神": self.JIUGONG[(ji_nian + 4) % 9],
            "五帝": self.JIUGONG[(ji_nian + 5) % 9],
            "天乙": self.JIUGONG[(ji_nian + 7) % 9],
        }
