#!/usr/bin/env python3
"""
玄照 v2.0 - 大六壬引擎（简化版）

核心：月将加时、天地盘、四课三传。

注：大六壬算法极其复杂，此为简化版，保留核心框架。
如需完整排盘，可后续接入 kinliuren 库。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional


class LiuRenEngine(DivinationEngine):
    """大六壬引擎"""

    @property
    def name(self) -> str:
        return "大六壬"

    @property
    def name_en(self) -> str:
        return "LiuRen"

    @property
    def priority(self) -> int:
        return 5

    # 十二地支
    ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    # 十天干
    GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    # 月将（十二月将）
    YUE_JIANG = ["登明", "河魁", "从魁", "传送", "小吉", "胜光",
                 "太乙", "天罡", "太冲", "功曹", "大吉", "神后"]

    # 月将对应地支
    YUE_JIANG_ZHI = ["亥", "戌", "酉", "申", "未", "午",
                     "巳", "辰", "卯", "寅", "丑", "子"]

    # 十二天将
    TIAN_JIANG = ["贵人", "螣蛇", "朱雀", "六合", "勾陈", "青龙",
                  "天空", "白虎", "太常", "玄武", "太阴", "天后"]

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        dt = time.true_solar

        # 1. 确定占时（用时支）
        zhan_shi = self._get_hour_zhi(dt.hour)

        # 2. 确定月将
        yue_jiang = self._get_yue_jiang(dt.month)
        yue_jiang_zhi = self._get_yue_jiang_zhi(dt.month)

        # 3. 排天地盘（月将加时）
        tian_pan, di_pan = self._pai_pan(yue_jiang_zhi, zhan_shi)

        # 4. 起四课（简化）
        si_ke = self._qi_si_ke(dt)

        # 5. 发三传（简化）
        san_chuan = self._fa_san_chuan(si_ke)

        return {
            "zhan_shi": zhan_shi,
            "yue_jiang": yue_jiang,
            "yue_jiang_zhi": yue_jiang_zhi,
            "tian_pan": tian_pan,
            "di_pan": di_pan,
            "si_ke": si_ke,
            "san_chuan": san_chuan,
            "date": dt.strftime("%Y-%m-%d %H:%M"),
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if not data.get("si_ke"):
            return False, "四课为空"
        return True, None

    def _get_hour_zhi(self, hour: int) -> str:
        """时辰转地支"""
        idx = (hour + 1) // 2 % 12
        return self.ZHI[idx]

    def _get_yue_jiang(self, month: int) -> str:
        """确定月将（简化：正月建寅，月将在亥）"""
        # 月将 = 月建后一位
        idx = (13 - month) % 12
        return self.YUE_JIANG[idx]

    def _get_yue_jiang_zhi(self, month: int) -> str:
        """月将对应地支"""
        idx = (13 - month) % 12
        return self.YUE_JIANG_ZHI[idx]

    def _pai_pan(self, yue_jiang_zhi: str, zhan_shi: str) -> tuple:
        """排天地盘（月将加时）"""
        yj_idx = self.ZHI.index(yue_jiang_zhi)
        zs_idx = self.ZHI.index(zhan_shi)

        # 天盘：月将加在地盘占时上
        tian_pan = {}
        for i, zhi in enumerate(self.ZHI):
            tian_pan[zhi] = self.ZHI[(yj_idx + i - zs_idx) % 12]

        # 地盘固定
        di_pan = {zhi: zhi for zhi in self.ZHI}

        return tian_pan, di_pan

    def _qi_si_ke(self, dt) -> list:
        """起四课（基于八字日柱）"""
        try:
            from lunar_python import Solar
            solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
            lunar = solar.getLunar()
            ec = lunar.getEightChar()
            day_gan = ec.getDayGan()
            day_zhi = ec.getDayZhi()
        except Exception:
            # fallback
            day_gan = self.GAN[dt.day % 10]
            day_zhi = self.ZHI[dt.day % 12]

        return [
            {"ke": f"{day_gan}上{day_zhi}", "name": "第一课"},
            {"ke": f"{day_zhi}上{day_gan}", "name": "第二课"},
            {"ke": f"{day_gan}上{day_zhi}", "name": "第三课"},
            {"ke": f"{day_zhi}上{day_gan}", "name": "第四课"},
        ]

    def _fa_san_chuan(self, si_ke: list) -> list:
        """发三传（简化）"""
        return [
            {"chuan": "初传", "name": si_ke[0]["ke"] if si_ke else ""},
            {"chuan": "中传", "name": si_ke[1]["ke"] if len(si_ke) > 1 else ""},
            {"chuan": "末传", "name": si_ke[2]["ke"] if len(si_ke) > 2 else ""},
        ]
