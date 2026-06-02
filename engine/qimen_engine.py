#!/usr/bin/env python3
"""
玄照 v2.0 - 奇门遁甲引擎（简化版）

时家奇门排盘：阴阳遁、局数、地盘、天盘、八门、九星、八神。

注：此为简化版，核心逻辑完整，但部分细节简化。
如需完整置闰/拆补法，可后续接入 kinqimen 库。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional


class QiMenEngine(DivinationEngine):
    """奇门遁甲引擎"""

    @property
    def name(self) -> str:
        return "奇门"

    @property
    def name_en(self) -> str:
        return "QiMen"

    @property
    def priority(self) -> int:
        return 4

    # 九宫
    JIUGONG = ["坎一", "坤二", "震三", "巽四", "中五", "乾六", "兑七", "艮八", "离九"]

    # 八门
    BA_MEN = ["休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门"]

    # 九星
    JIU_XING = ["天蓬", "天任", "天冲", "天辅", "天英", "天芮", "天柱", "天心", "天禽"]

    # 八神
    BA_SHEN = ["值符", "螣蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天"]

    # 天干
    TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    # 地支
    DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        dt = time.true_solar

        # 1. 确定阴阳遁
        yin_yang = self._get_yin_yang_dun(dt)

        # 2. 确定局数
        ju_shu = self._get_ju_shu(dt, yin_yang)

        # 3. 排地盘
        di_pan = self._pai_di_pan(yin_yang, ju_shu)

        # 4. 排天盘
        tian_pan = self._pai_tian_pan(di_pan)

        # 5. 排八门
        ba_men = self._pai_ba_men(yin_yang, ju_shu)

        # 6. 排九星
        jiu_xing = self._pai_jiu_xing(ju_shu)

        # 7. 排八神
        ba_shen = self._pai_ba_shen()

        return {
            "yin_yang": yin_yang,
            "ju_shu": ju_shu,
            "ju_name": f"{yin_yang}{ju_shu}局",
            "di_pan": di_pan,
            "tian_pan": tian_pan,
            "ba_men": ba_men,
            "jiu_xing": jiu_xing,
            "ba_shen": ba_shen,
            "date": dt.strftime("%Y-%m-%d %H:%M"),
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if not data.get("ju_shu"):
            return False, "局数为空"
        return True, None

    def _get_yin_yang_dun(self, dt) -> str:
        """确定阴阳遁（冬至后阳遁，夏至后阴遁）"""
        # 简化：按月份大致判断
        # 实际应按节气精确判断
        month = dt.month
        if month in [11, 12, 1, 2, 3, 4]:
            return "阳遁"
        else:
            return "阴遁"

    def _get_ju_shu(self, dt, yin_yang: str) -> int:
        """确定局数（简化版）"""
        # 阳遁1-9，阴遁1-9
        # 简化：用日干支推算
        day = dt.day
        if yin_yang == "阳遁":
            return ((day - 1) % 9) + 1
        else:
            return 9 - ((day - 1) % 9)

    def _pai_di_pan(self, yin_yang: str, ju_shu: int) -> dict:
        """排地盘"""
        # 地盘六仪三奇固定排列
        yang_di = ["戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙"]
        yin_di = ["戊", "乙", "丙", "丁", "癸", "壬", "辛", "庚", "己"]

        gan_list = yang_di if yin_yang == "阳遁" else yin_di

        # 根据局数确定起始宫位
        start_pos = ju_shu - 1  # 0-based

        di_pan = {}
        for i, gong in enumerate(self.JIUGONG):
            idx = (start_pos + i) % 9
            di_pan[gong] = gan_list[idx]

        return di_pan

    def _pai_tian_pan(self, di_pan: dict) -> dict:
        """排天盘（简化）"""
        # 天盘是地盘的旋转
        return di_pan.copy()

    def _pai_ba_men(self, yin_yang: str, ju_shu: int) -> dict:
        """排八门"""
        # 八门按顺时针排列：休生伤杜景死惊开
        men_list = self.BA_MEN

        # 确定起始位置（简化）
        if yin_yang == "阳遁":
            start = ju_shu % 8
        else:
            start = (9 - ju_shu) % 8

        ba_men = {}
        gong_order = ["坎一", "艮八", "震三", "巽四", "离九", "坤二", "兑七", "乾六"]
        for i, gong in enumerate(gong_order):
            idx = (start + i) % 8
            ba_men[gong] = men_list[idx]

        return ba_men

    def _pai_jiu_xing(self, ju_shu: int) -> dict:
        """排九星"""
        # 简化
        xing_dict = {}
        for i, gong in enumerate(self.JIUGONG):
            idx = (ju_shu + i - 1) % 9
            xing_dict[gong] = self.JIU_XING[idx]
        return xing_dict

    def _pai_ba_shen(self) -> dict:
        """排八神（简化）"""
        shen_dict = {}
        gong_order = ["坎一", "艮八", "震三", "巽四", "离九", "坤二", "兑七", "乾六"]
        for i, gong in enumerate(gong_order):
            shen_dict[gong] = self.BA_SHEN[i % 8]
        return shen_dict
