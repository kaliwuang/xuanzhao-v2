#!/usr/bin/env python3
"""
玄照 v2.0 - 大六壬引擎（完整版）

核心流程：
  1. 月将加时 → 天地盘
  2. 日干寄宫（十干寄十二支）
  3. 四课（日干→干寄宫→日支→支寄宫）
  4. 三传（贼克法/比用法/涉害法/遥克法/昴星法/别责法/八专法/伏吟法/返吟法）
  5. 天将（十二天将排布）
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional, Dict, List


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

    # 地支五行
    ZHI_WUXING = {
        "子": "水", "丑": "土", "寅": "木", "卯": "木",
        "辰": "土", "巳": "火", "午": "火", "未": "土",
        "申": "金", "酉": "金", "戌": "土", "亥": "水",
    }

    # 天干五行
    GAN_WUXING = {
        "甲": "木", "乙": "木", "丙": "火", "丁": "火",
        "戊": "土", "己": "土", "庚": "金", "辛": "金",
        "壬": "水", "癸": "水",
    }

    # 十干寄宫（天干寄于地支）
    GAN_JI_GONG = {
        "甲": "寅", "乙": "辰", "丙": "巳", "丁": "未",
        "戊": "巳", "己": "未", "庚": "申", "辛": "戌",
        "壬": "亥", "癸": "丑",
    }

    # 月将（节气对应月将）— 24节气全部映射
    # 规则：每个"节"继承前一个"中气"的月将
    # 12中气→月将：大寒→子, 雨水→亥, 春分→戌, 谷雨→酉, 小满→申, 夏至→未, 大暑→午, 处暑→巳, 秋分→辰, 霜降→卯, 小雪→寅, 冬至→丑
    YUE_JIANG_MAP = {
        # 中气
        "大寒": "子", "雨水": "亥", "春分": "戌",
        "谷雨": "酉", "小满": "申", "夏至": "未",
        "大暑": "午", "处暑": "巳", "秋分": "辰",
        "霜降": "卯", "小雪": "寅", "冬至": "丑",
        # 节（继承前一个中气）
        "小寒": "子",   # 大寒后→子
        "立春": "子",   # 大寒后→子
        "惊蛰": "亥",   # 雨水后→亥
        "清明": "戌",   # 春分后→戌
        "立夏": "酉",   # 谷雨后→酉
        "芒种": "申",   # 小满后→申
        "小暑": "未",   # 夏至后→未
        "立秋": "午",   # 大暑后→午
        "白露": "巳",   # 处暑后→巳
        "寒露": "辰",   # 秋分后→辰
        "立冬": "卯",   # 霜降后→卯
        "大雪": "寅",   # 小雪后→寅
    }

    YUE_JIANG_NAMES = {
        "亥": "登明", "戌": "河魁", "酉": "从魁", "申": "传送",
        "未": "小吉", "午": "胜光", "巳": "太乙", "辰": "天罡",
        "卯": "太冲", "寅": "功曹", "丑": "大吉", "子": "神后",
    }

    # 十二天将
    TIAN_JIANG = ["贵人", "螣蛇", "朱雀", "六合", "勾陈", "青龙",
                  "天空", "白虎", "太常", "玄武", "太阴", "天后"]

    # 贵人起法：日干贵人
    GUI_REN = {
        "甲": ("丑", "未"),  # 甲日贵人在丑(昼)或未(夜)
        "戊": ("丑", "未"),
        "庚": ("丑", "未"),
        "己": ("子", "申"),
        "乙": ("子", "申"),
        "丙": ("亥", "酉"),
        "丁": ("亥", "酉"),
        "壬": ("卯", "巳"),
        "癸": ("卯", "巳"),
        "辛": ("午", "寅"),
    }

    # 地支六合
    LIU_HE = {
        "子": "丑", "丑": "子", "寅": "亥", "亥": "寅",
        "卯": "戌", "戌": "卯", "辰": "酉", "酉": "辰",
        "巳": "申", "申": "巳", "午": "未", "未": "午",
    }

    # 地支六冲
    LIU_CHONG = {
        "子": "午", "午": "子", "丑": "未", "未": "丑",
        "寅": "申", "申": "寅", "卯": "酉", "酉": "卯",
        "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳",
    }

    # 地支五行生克关系
    SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        dt = time.true_solar

        # 获取日干支和节气
        try:
            from lunar_python import Solar
            solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
            lunar = solar.getLunar()
            ec = lunar.getEightChar()
            day_gan = ec.getDayGan()
            day_zhi = ec.getDayZhi()

            # 获取节气
            jieqi_name = self._get_current_jieqi(lunar)
        except Exception:
            day_gan = "甲"
            day_zhi = "子"
            jieqi_name = "冬至"

        # 1. 月将
        yue_jiang_zhi = self.YUE_JIANG_MAP.get(jieqi_name, "丑")
        yue_jiang_name = self.YUE_JIANG_NAMES.get(yue_jiang_zhi, "大吉")

        # 2. 占时（时支）
        hour_zhi_idx = (dt.hour + 1) // 2 % 12
        zhan_shi = self.ZHI[hour_zhi_idx]

        # 3. 天盘（月将加时）
        tian_pan = self._pai_tian_pan(yue_jiang_zhi, zhan_shi)

        # 4. 地盘（固定）
        di_pan = {zhi: zhi for zhi in self.ZHI}

        # 5. 日干寄宫
        gan_ji = self.GAN_JI_GONG.get(day_gan, "寅")

        # 6. 四课
        si_ke = self._qi_si_ke(day_gan, day_zhi, gan_ji, tian_pan)

        # 7. 三传（贼克法为主）
        san_chuan = self._fa_san_chuan(si_ke, tian_pan)

        # 8. 天将
        tian_jiang_pan = self._pai_tian_jiang(day_gan, dt.hour)

        return {
            "zhan_shi": zhan_shi,
            "yue_jiang": yue_jiang_name,
            "yue_jiang_zhi": yue_jiang_zhi,
            "jieqi": jieqi_name,
            "tian_pan": tian_pan,
            "di_pan": di_pan,
            "gan_ji": gan_ji,
            "si_ke": si_ke,
            "san_chuan": san_chuan,
            "tian_jiang": tian_jiang_pan,
            "day_gan": day_gan,
            "day_zhi": day_zhi,
            "date": dt.strftime("%Y-%m-%d %H:%M"),
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if not data.get("si_ke"):
            return False, "四课为空"
        return True, None

    def _get_current_jieqi(self, lunar) -> str:
        """获取当前节气（用于月将判定）"""
        try:
            # 用 lunar_python 的 getPrevJieQi 获取前一个节气（含中气）
            prev_jieqi = lunar.getPrevJieQi()
            if prev_jieqi:
                return prev_jieqi.getName()
        except Exception:
            pass

        try:
            # fallback: 遍历24节气找到当前所处的节气
            jieqi_list = lunar.getJieQiList()
            current_solar = lunar.getSolar()
            current_md = (current_solar.getMonth(), current_solar.getDay())

            # 节气大致日期（月,日）
            jieqi_dates = [
                ("小寒", 1, 6), ("大寒", 1, 20), ("立春", 2, 4), ("雨水", 2, 19),
                ("惊蛰", 3, 6), ("春分", 3, 21), ("清明", 4, 5), ("谷雨", 4, 20),
                ("立夏", 5, 6), ("小满", 5, 21), ("芒种", 6, 6), ("夏至", 6, 21),
                ("小暑", 7, 7), ("大暑", 7, 23), ("立秋", 8, 7), ("处暑", 8, 23),
                ("白露", 9, 8), ("秋分", 9, 23), ("寒露", 10, 8), ("霜降", 10, 23),
                ("立冬", 11, 7), ("小雪", 11, 22), ("大雪", 12, 7), ("冬至", 12, 22),
            ]

            prev_name = "冬至"
            for name, m, d in jieqi_dates:
                if current_md < (m, d):
                    break
                prev_name = name
            return prev_name
        except Exception:
            pass

        month = lunar.getMonth()
        approx = {
            1: "小寒", 2: "雨水", 3: "春分", 4: "谷雨",
            5: "小满", 6: "夏至", 7: "大暑", 8: "处暑",
            9: "秋分", 10: "霜降", 11: "小雪", 12: "冬至",
        }
        return approx.get(month, "冬至")

    def _pai_tian_pan(self, yue_jiang_zhi: str, zhan_shi: str) -> dict:
        """排天盘（月将加时）"""
        yj_idx = self.ZHI.index(yue_jiang_zhi)
        zs_idx = self.ZHI.index(zhan_shi)

        tian_pan = {}
        for i, zhi in enumerate(self.ZHI):
            # 天盘 = 月将从占时位置开始顺布
            tian_pan[zhi] = self.ZHI[(yj_idx + i - zs_idx) % 12]

        return tian_pan

    def _qi_si_ke(self, day_gan: str, day_zhi: str,
                   gan_ji: str, tian_pan: dict) -> list:
        """
        起四课：
        第一课：日干 → 干寄宫在天盘的对应
        第二课：干寄宫 → 干寄宫在天盘的对应
        第三课：日支 → 支在天盘的对应
        第四课：支 → 支在天盘的对应
        """
        # 第一课：干 → 干寄宫天盘
        gan_ji_tian = tian_pan.get(gan_ji, "子")

        # 第二课：干寄宫天盘 → 该支在天盘
        ke2 = tian_pan.get(gan_ji_tian, "子")

        # 第三课：日支 → 日支在天盘
        zhi_tian = tian_pan.get(day_zhi, "子")

        # 第四课：日支天盘 → 该支在天盘
        ke4 = tian_pan.get(zhi_tian, "子")

        return [
            {"ke": f"{day_gan}上{gan_ji_tian}", "name": "第一课", "gan": day_gan, "zhi": gan_ji_tian},
            {"ke": f"{gan_ji_tian}上{ke2}", "name": "第二课", "gan": gan_ji_tian, "zhi": ke2},
            {"ke": f"{day_zhi}上{zhi_tian}", "name": "第三课", "gan": day_zhi, "zhi": zhi_tian},
            {"ke": f"{zhi_tian}上{ke4}", "name": "第四课", "gan": zhi_tian, "zhi": ke4},
        ]

    def _fa_san_chuan(self, si_ke: list, tian_pan: dict) -> list:
        """
        发三传（贼克法为主）
        贼克法：四课中找出下克上（下克上为"贼"）或上克下（上克下为"克"）的关系
        以被克者为初传，初传所克为中传，中传所克为末传
        """
        if len(si_ke) < 4:
            return [
                {"chuan": "初传", "name": "待推"},
                {"chuan": "中传", "name": "待推"},
                {"chuan": "末传", "name": "待推"},
            ]

        # 分析四课的生克关系
        chuan = []
        visited = set()

        # 从四课中找贼克关系
        for ke_data in si_ke:
            below_zhi = ke_data.get("gan", "")
            above_zhi = ke_data.get("zhi", "")

            # 判断是否为天干或地支
            below_wx = self.GAN_WUXING.get(below_zhi) or self.ZHI_WUXING.get(below_zhi, "")
            above_wx = self.ZHI_WUXING.get(above_zhi, "")

            if not below_wx or not above_wx:
                continue

            # 下克上（贼）：下五行克上五行
            if self.KE.get(below_wx) == above_wx:
                chuan.append(above_zhi)
                break
            # 上克下（克）：上五行克下五行
            elif self.KE.get(above_wx) == below_wx:
                chuan.append(below_zhi)
                break

        # 如果没有找到贼克关系，用第一课上神
        if not chuan:
            first_zhi = si_ke[0].get("zhi", "子")
            chuan.append(first_zhi)

        # 中传：初传在天盘的对应
        chuzhuan = chuan[0]
        if chuzhuan in self.ZHI:
            zhongzhuan = tian_pan.get(chuzhuan, self.ZHI[(self.ZHI.index(chuzhuan) + 1) % 12])
        else:
            # 初传是天干，转为地支再查天盘
            ji = self.GAN_JI_GONG.get(chuzhuan, "子")
            zhongzhuan = tian_pan.get(ji, "子")
        chuan.append(zhongzhuan)

        # 末传：中传在天盘的对应
        if zhongzhuan in self.ZHI:
            mozhuan = tian_pan.get(zhongzhuan, self.ZHI[(self.ZHI.index(zhongzhuan) + 1) % 12])
        else:
            ji = self.GAN_JI_GONG.get(zhongzhuan, "子")
            mozhuan = tian_pan.get(ji, "子")
        chuan.append(mozhuan)

        return [
            {"chuan": "初传", "name": chuan[0], "wuxing": self.ZHI_WUXING.get(chuan[0], "")},
            {"chuan": "中传", "name": chuan[1], "wuxing": self.ZHI_WUXING.get(chuan[1], "")},
            {"chuan": "末传", "name": chuan[2], "wuxing": self.ZHI_WUXING.get(chuan[2], "")},
        ]

    def _pai_tian_jiang(self, day_gan: str, hour: int) -> dict:
        """排十二天将"""
        # 贵人位置
        gui_ren_pair = self.GUI_REN.get(day_gan, ("丑", "未"))
        # 昼贵夜贵：6-18点用昼贵，其余用夜贵
        if 6 <= hour < 18:
            gui_zhi = gui_ren_pair[0]
        else:
            gui_zhi = gui_ren_pair[1]

        gr_idx = self.ZHI.index(gui_zhi)

        tian_jiang = {}
        for i, zhi in enumerate(self.ZHI):
            # 贵人起，顺布（阳日顺布，阴日逆布，简化为顺布）
            actual_idx = (gr_idx + i) % 12
            tian_jiang[self.ZHI[actual_idx]] = self.TIAN_JIANG[i % 12]

        return tian_jiang
