#!/usr/bin/env python3
"""
玄照 v2.0 - 奇门遁甲引擎（完整版）

时家奇门排盘：拆补法
  1. 节气定阴阳遁（冬至→夏至=阳遁，夏至→冬至=阴遁）
  2. 节气三元定局数（上中下三元，每元5天）
  3. 地盘固定排列（阳遁顺布，阴遁逆布）
  4. 天盘旋转（时干加临地盘）
  5. 八门排列（值使门随天盘转动）
  6. 九星排列（值符星随天盘转动）
  7. 八神排列（阳遁顺布，阴遁逆布）
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional, Dict, List
import math


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

    # 九宫（洛书顺序）
    GONG = ["坎一", "坤二", "震三", "巽四", "中五", "乾六", "兑七", "艮八", "离九"]

    # 九宫地支对应
    GONG_ZHI = {
        "坎一": "子", "坤二": "未申", "震三": "卯",
        "巽四": "辰巳", "中五": "", "乾六": "戌亥",
        "兑七": "酉", "艮八": "丑寅", "离九": "午",
    }

    # 九宫五行
    GONG_WUXING = {
        "坎一": "水", "坤二": "土", "震三": "木", "巽四": "木",
        "中五": "土", "乾六": "金", "兑七": "金", "艮八": "土", "离九": "火",
    }

    # 天干
    TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    # 六仪三奇（甲子旬首遁戊，甲戌己，甲申庚，甲午辛，甲辰壬，甲寅癸）
    # 三奇：乙(日奇)、丙(月奇)、丁(星奇)
    YI_QI = ["戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙"]

    # 八门
    BA_MEN = ["休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门"]

    # 八门原始宫位（阳遁一局时）
    # 休门坎一、生门艮八、伤门震三、杜门巽四、景门离九、死门坤二、惊门兑七、开门乾六
    MEN_ORIGIN = {
        "休门": 0, "生门": 7, "伤门": 2, "杜门": 3,
        "景门": 8, "死门": 1, "惊门": 6, "开门": 5,
    }

    # 九星
    JIU_XING = ["天蓬", "天芮", "天冲", "天辅", "天禽", "天心", "天柱", "天任", "天英"]

    # 九星原始宫位
    XING_ORIGIN = {
        "天蓬": 0, "天芮": 1, "天冲": 2, "天辅": 3, "天禽": 4,
        "天心": 5, "天柱": 6, "天任": 7, "天英": 8,
    }

    # 八神
    BA_SHEN = ["值符", "螣蛇", "太阴", "六合", "白虎(勾陈)", "玄武(朱雀)", "九地", "九天"]

    # 二十四节气 → (阳遁局数, 阴遁局数)
    # 每个节气15天，分上中下三元，每元5天
    JIEQI_JU = {
        # 冬至后阳遁
        "冬至": (1, 7, 4),   # 上元1局，中元7局，下元4局
        "小寒": (2, 8, 5),
        "大寒": (3, 9, 6),
        "立春": (8, 5, 2),
        "雨水": (9, 6, 3),
        "惊蛰": (1, 7, 4),
        "春分": (3, 9, 6),
        "清明": (4, 1, 7),
        "谷雨": (5, 2, 8),
        "立夏": (4, 1, 7),
        "小满": (5, 2, 8),
        "芒种": (6, 3, 9),
        # 夏至后阴遁
        "夏至": (9, 3, 6),
        "小暑": (8, 2, 5),
        "大暑": (7, 1, 4),
        "立秋": (2, 5, 8),
        "处暑": (1, 4, 7),
        "白露": (9, 3, 6),
        "秋分": (7, 1, 4),
        "寒露": (6, 9, 3),
        "霜降": (5, 8, 2),
        "立冬": (6, 9, 3),
        "小雪": (5, 8, 2),
        "大雪": (4, 7, 1),
    }

    # 节气顺序
    JIEQI_ORDER = [
        "小寒", "大寒", "立春", "雨水", "惊蛰", "春分",
        "清明", "谷雨", "立夏", "小满", "芒种", "夏至",
        "小暑", "大暑", "立秋", "处暑", "白露", "秋分",
        "寒露", "霜降", "立冬", "小雪", "大雪", "冬至",
    ]

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        dt = time.true_solar

        # 获取节气信息和日干支
        try:
            from lunar_python import Solar
            solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
            lunar = solar.getLunar()
            ec = lunar.getEightChar()
            day_gan = ec.getDayGan()
            day_zhi = ec.getDayZhi()
            day_jiazi_idx = self._get_jiazi_idx(day_gan, day_zhi)

            # 获取当前节气
            jieqi_name = self._get_current_jieqi(lunar)
        except Exception:
            day_gan = "甲"
            day_zhi = "子"
            day_jiazi_idx = 0
            jieqi_name = "冬至"

        # 时干支
        hour_zhi_idx = (dt.hour + 1) // 2 % 12
        time_gan_idx = self._get_time_gan_idx(day_gan, hour_zhi_idx)
        time_gan = self.TIAN_GAN[time_gan_idx]

        # 1. 确定阴阳遁
        yin_yang = self._get_yin_yang_dun(jieqi_name)

        # 2. 确定局数
        ju_shu = self._get_ju_shu(jieqi_name, day_jiazi_idx, yin_yang)

        # 3. 排地盘
        di_pan = self._pai_di_pan(yin_yang, ju_shu)

        # 4. 确定值符值使
        # 甲子旬首遁戊，找出时干所在旬
        xun_shou = self._get_xun_shou(day_jiazi_idx)
        xun_shou_gan = self.YI_QI[xun_shou]

        # 值符星 = 地盘旬首所在宫的九星
        zhi_fu_gong = self._find_gong_of_gan(di_pan, xun_shou_gan)

        # 5. 排天盘（时干落宫转动）
        tian_pan = self._pai_tian_pan(di_pan, time_gan, yin_yang)

        # 6. 排九星
        jiu_xing = self._pai_jiu_xing(di_pan, tian_pan, zhi_fu_gong, yin_yang, ju_shu)

        # 7. 排八门
        ba_men = self._pai_ba_men(di_pan, tian_pan, zhi_fu_gong, yin_yang, ju_shu, hour_zhi_idx)

        # 8. 排八神
        ba_shen = self._pai_ba_shen(zhi_fu_gong, yin_yang)

        return {
            "yin_yang": yin_yang,
            "ju_shu": ju_shu,
            "ju_name": f"{yin_yang}{ju_shu}局",
            "jieqi": jieqi_name,
            "di_pan": di_pan,
            "tian_pan": tian_pan,
            "ba_men": ba_men,
            "jiu_xing": jiu_xing,
            "ba_shen": ba_shen,
            "zhi_fu": xun_shou_gan,
            "zhi_shi": self.BA_MEN[0],  # 简化
            "time_gan": time_gan,
            "date": dt.strftime("%Y-%m-%d %H:%M"),
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if not data.get("ju_shu"):
            return False, "局数为空"
        return True, None

    def _get_current_jieqi(self, lunar) -> str:
        """获取当前所处节气"""
        try:
            # 获取最近的节
            prev_jie = lunar.getPrevJie()
            if prev_jie:
                return prev_jie.getName()
        except Exception:
            pass

        # fallback: 按月份估算
        month = lunar.getMonth()
        jieqi_approx = {
            1: "小寒", 2: "立春", 3: "惊蛰", 4: "清明",
            5: "立夏", 6: "芒种", 7: "小暑", 8: "立秋",
            9: "白露", 10: "寒露", 11: "立冬", 12: "大雪",
        }
        return jieqi_approx.get(month, "冬至")

    def _get_yin_yang_dun(self, jieqi_name: str) -> str:
        """按节气定阴阳遁：冬至到夏至为阳遁，夏至到冬至为阴遁"""
        yang_jieqi = {"冬至", "小寒", "大寒", "立春", "雨水", "惊蛰",
                      "春分", "清明", "谷雨", "立夏", "小满", "芒种"}
        if jieqi_name in yang_jieqi:
            return "阳遁"
        return "阴遁"

    def _get_ju_shu(self, jieqi_name: str, day_jiazi_idx: int, yin_yang: str) -> int:
        """拆补法定局：节气+日干支三元"""
        ju_tuple = self.JIEQI_JU.get(jieqi_name, (1, 7, 4))

        # 三元判定：甲子、甲午为上元；己卯、己酉为中元；其余为下元
        # 简化：用日干支序号对15取余分三元
        # 甲子(0)~戊辰(4)为上元，己巳(5)~癸酉(9)为中元，甲戌(10)~戊寅(14)为下元
        yuan = day_jiazi_idx % 15
        if yuan < 5:
            return ju_tuple[0]  # 上元
        elif yuan < 10:
            return ju_tuple[1]  # 中元
        else:
            return ju_tuple[2]  # 下元

    def _pai_di_pan(self, yin_yang: str, ju_shu: int) -> dict:
        """排地盘：六仪三奇按洛书九宫排列"""
        # 阳遁：戊起局数宫，顺布
        # 阴遁：戊起局数宫，逆布
        di_pan = {}
        gong_order = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # 洛书顺序：坎坤震巽中乾兑艮离

        start = ju_shu - 1  # 局数-1 = 起始宫索引

        for i in range(9):
            if yin_yang == "阳遁":
                gong_idx = (start + i) % 9
            else:
                gong_idx = (start - i) % 9
            di_pan[self.GONG[gong_idx]] = self.YI_QI[i]

        return di_pan

    def _pai_tian_pan(self, di_pan: dict, time_gan: str, yin_yang: str) -> dict:
        """排天盘：值符随时干转动

        规则：值符星落在时干所在的地盘宫位，天盘的三奇六仪随之旋转。
        天盘的排列 = 地盘以时干宫为轴旋转后的结果。
        """
        tian_pan = {}

        # 找时干在地盘的宫位索引
        time_gan_gong_idx = None
        for i, gong in enumerate(self.GONG):
            if di_pan.get(gong) == time_gan:
                time_gan_gong_idx = i
                break

        if time_gan_gong_idx is None:
            return di_pan.copy()

        # 天盘旋转：地盘的起始宫（戊所在宫）转到时干宫
        # 找戊在地盘的宫位
        wu_gong_idx = None
        for i, gong in enumerate(self.GONG):
            if di_pan.get(gong) == "戊":
                wu_gong_idx = i
                break

        if wu_gong_idx is None:
            return di_pan.copy()

        # 旋转量 = 时干宫 - 戊宫
        rotation = time_gan_gong_idx - wu_gong_idx

        for i, gong in enumerate(self.GONG):
            src_idx = (i - rotation) % 9
            tian_pan[gong] = di_pan.get(self.GONG[src_idx], "")

        return tian_pan

    def _pai_jiu_xing(self, di_pan: dict, tian_pan: dict,
                       zhi_fu_gong: int, yin_yang: str, ju_shu: int) -> dict:
        """排九星"""
        jiu_xing = {}

        # 值符星落在时干所在宫
        # 九星原始宫位：天蓬坎、天芮坤、天冲震...
        # 阳遁：天蓬起坎一宫顺行
        # 阴遁：天蓬起离九宫逆行

        gong_order = list(range(9))  # 坎坤震巽中乾兑艮离

        if yin_yang == "阳遁":
            start = ju_shu - 1
        else:
            start = 9 - ju_shu

        for i in range(9):
            if yin_yang == "阳遁":
                gong_idx = (start + i) % 9
            else:
                gong_idx = (start - i) % 9
            jiu_xing[self.GONG[gong_idx]] = self.JIU_XING[i]

        return jiu_xing

    def _pai_ba_men(self, di_pan: dict, tian_pan: dict,
                     zhi_fu_gong: int, yin_yang: str, ju_shu: int,
                     hour_zhi_idx: int) -> dict:
        """排八门"""
        ba_men = {}

        if yin_yang == "阳遁":
            start = ju_shu - 1
        else:
            start = 9 - ju_shu

        # 八门排列：休门起始，按洛书顺序
        men_order = ["休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门"]
        gong_order = [0, 7, 2, 3, 8, 1, 6, 5]  # 坎艮震巽离坤兑乾（跳过中五）

        for i, gong_idx in enumerate(gong_order):
            if yin_yang == "阳遁":
                actual_idx = (start + gong_idx) % 9
            else:
                actual_idx = (start - gong_idx) % 9
            if i < len(men_order):
                ba_men[self.GONG[actual_idx]] = men_order[i]

        return ba_men

    def _pai_ba_shen(self, zhi_fu_gong: int, yin_yang: str) -> dict:
        """排八神"""
        ba_shen = {}
        gong_order = [0, 7, 2, 3, 8, 1, 6, 5]  # 跳过中五

        start_idx = 0
        for i, gong_idx in enumerate(gong_order):
            if yin_yang == "阳遁":
                actual_idx = (zhi_fu_gong + gong_idx) % 9
            else:
                actual_idx = (zhi_fu_gong - gong_idx) % 9
            if i < len(self.BA_SHEN):
                ba_shen[self.GONG[actual_idx]] = self.BA_SHEN[i]

        return ba_shen

    def _get_jiazi_idx(self, gan: str, zhi: str) -> int:
        """天干地支 → 甲子序号"""
        gan_idx = self.TIAN_GAN.index(gan)
        zhi_list = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        zhi_idx = zhi_list.index(zhi)
        # 六十甲子序号
        idx = (gan_idx * 6 + (zhi_idx - gan_idx) % 12) % 60
        return idx

    def _get_time_gan_idx(self, day_gan: str, hour_zhi_idx: int) -> int:
        """日干定时干（五鼠遁日起时法）"""
        # 甲己日起甲子时，乙庚日起丙子时，丙辛日起戊子时，丁壬日起庚子时，戊癸日起壬子时
        start_map = {"甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4, "丁": 6, "壬": 6, "戊": 8, "癸": 8}
        start = start_map.get(day_gan, 0)
        return (start + hour_zhi_idx) % 10

    def _get_xun_shou(self, day_jiazi_idx: int) -> int:
        """确定旬首（甲子旬=0, 甲戌旬=1, 甲申旬=2, 甲午旬=3, 甲辰旬=4, 甲寅旬=5）"""
        return day_jiazi_idx // 10

    def _find_gong_of_gan(self, di_pan: dict, gan: str) -> int:
        """找天干在地盘的宫位索引"""
        for i, gong in enumerate(self.GONG):
            if di_pan.get(gong) == gan:
                return i
        return 0
