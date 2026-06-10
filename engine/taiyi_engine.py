#!/usr/bin/env python3
"""
玄照 v2.0 - 太乙神数引擎（完整版）

核心：
  1. 太乙积年（黄帝元年=公元前2697年起算）
  2. 太乙行宫（每年移一宫，九宫一圈）
  3. 三基（君基、臣基、民基）
  4. 五福（大游、小游、四神、五帝、天乙）
  5. 阴阳遁
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

    # 九宫（洛书顺序）
    JIUGONG = ["坎一宫", "坤二宫", "震三宫", "巽四宫", "中五宫",
               "乾六宫", "兑七宫", "艮八宫", "离九宫"]

    JIUGONG_SHORT = ["坎一", "坤二", "震三", "巽四", "中五",
                     "乾六", "兑七", "艮八", "离九"]

    # 九宫五行
    GONG_WUXING = {
        "坎一宫": "水", "坤二宫": "土", "震三宫": "木", "巽四宫": "木",
        "中五宫": "土", "乾六宫": "金", "兑七宫": "金", "艮八宫": "土", "离九宫": "火",
    }

    # 太乙积年起点（黄帝元年 = 公元前2697年）
    HUANGDI_YEAR = -2697

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        dt = time.true_solar
        year = dt.year

        # 1. 计算太乙积年数
        ji_nian = self._calc_ji_nian(year)

        # 2. 确定太乙所在宫位
        taiyi_gong = self._get_taiyi_gong(ji_nian)

        # 3. 确定阴阳遁（按节气）
        yin_yang = self._get_yin_yang(year, dt.month, dt.day)

        # 4. 三基（君基、臣基、民基）
        san_ji = self._get_san_ji(ji_nian)

        # 5. 五福（大游、小游、四神、五帝、天乙）
        wu_fu = self._get_wu_fu(ji_nian)

        # 6. 计算年干支
        year_gan_idx = (year - 4) % 10
        year_zhi_idx = (year - 4) % 12
        gan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"][year_gan_idx]
        zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"][year_zhi_idx]

        return {
            "year": year,
            "year_ganzhi": f"{gan}{zhi}",
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
        """计算太乙积年数（从黄帝元年起算）"""
        # 黄帝元年 = 公元前2697年
        # 积年 = 公元年 + 2697
        return year - self.HUANGDI_YEAR

    def _get_taiyi_gong(self, ji_nian: int) -> str:
        """确定太乙所在宫位（每年移一宫，九宫一圈）"""
        # 太乙行宫：从一宫开始，每一年移一宫
        # 积年数对9取余，对应九宫
        gong_idx = (ji_nian - 1) % 9  # -1因为积年1年在一宫
        return self.JIUGONG[gong_idx]

    def _get_yin_yang(self, year: int, month: int = 6, day: int = 15) -> str:
        """确定阴阳遁（按节气：冬至到夏至为阳遁，夏至到冬至为阴遁）"""
        # 大致节气日期判断
        # 冬至(12.22) → 夏至(6.21) = 阳遁
        # 夏至(6.21) → 冬至(12.22) = 阴遁
        if (month == 12 and day >= 22) or month in [1, 2, 3, 4, 5] or (month == 6 and day < 21):
            return "阳遁"
        return "阴遁"

    def _get_san_ji(self, ji_nian: int) -> dict:
        """
        三基：
        君基 = 太乙所在宫
        臣基 = 君基 + 3宫
        民基 = 君基 + 6宫
        """
        base = (ji_nian - 1) % 9
        return {
            "君基": self.JIUGONG[base],
            "臣基": self.JIUGONG[(base + 3) % 9],
            "民基": self.JIUGONG[(base + 6) % 9],
        }

    def _get_wu_fu(self, ji_nian: int) -> dict:
        """
        五福：
        大游 = 积年 * 365.25 / 360 对9取余（简化）
        小游 = 大游 + 1
        四神 = 大游 + 4
        五帝 = 大游 + 5
        天乙 = 大游 + 7
        """
        # 简化计算：以积年为基础
        base = (ji_nian - 1) % 9
        return {
            "大游": self.JIUGONG[(base + 1) % 9],
            "小游": self.JIUGONG[(base + 2) % 9],
            "四神": self.JIUGONG[(base + 4) % 9],
            "五帝": self.JIUGONG[(base + 5) % 9],
            "天乙": self.JIUGONG[(base + 7) % 9],
        }
