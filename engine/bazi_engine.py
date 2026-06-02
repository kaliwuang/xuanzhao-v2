#!/usr/bin/env python3
"""
玄照 v2.0 - 八字引擎

基于 lunar-python，封装真太阳时修正、早晚子时处理、特征提取。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from .udm import Pillar, SHISHEN_MAP
from typing import Optional


class BaziEngine(DivinationEngine):
    """八字引擎"""

    @property
    def name(self) -> str:
        return "八字"

    @property
    def name_en(self) -> str:
        return "BaZi"

    @property
    def priority(self) -> int:
        return 1

    def __init__(self):
        self._available = False
        try:
            from lunar_python import Solar, EightChar
            self.Solar = Solar
            self.EightChar = EightChar
            self._available = True
        except ImportError:
            pass

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        if not self._available:
            return {"error": "lunar_python not installed"}

        # 使用修正后的时间
        # 晚子时用次日日期
        dt = time.bazi_day_pillar_date
        hour = time.bazi_hour

        solar = self.Solar.fromYmdHms(
            dt.year, dt.month, dt.day,
            hour, dt.minute, 0
        )
        lunar = solar.getLunar()
        ec = self.EightChar(lunar)

        # 四柱
        year_pillar = Pillar(gan=ec.getYearGan(), zhi=ec.getYearZhi(), nayin=ec.getYearNaYin())
        month_pillar = Pillar(gan=ec.getMonthGan(), zhi=ec.getMonthZhi(), nayin=ec.getMonthNaYin())
        day_pillar = Pillar(gan=ec.getDayGan(), zhi=ec.getDayZhi(), nayin=ec.getDayNaYin())
        time_pillar = Pillar(gan=ec.getTimeGan(), zhi=ec.getTimeZhi(), nayin=ec.getTimeNaYin())

        day_master = ec.getDayGan()

        # 藏干
        hidden_gans = {
            "year": ec.getYearHideGan(),
            "month": ec.getMonthHideGan(),
            "day": ec.getDayHideGan(),
            "time": ec.getTimeHideGan(),
        }

        # 十神（按天干）
        shishen_gan = {
            "year": ec.getYearShiShenGan(),
            "month": ec.getMonthShiShenGan(),
            "day": "日元",
            "time": ec.getTimeShiShenGan(),
        }

        # 十神（按地支藏干）
        shishen_zhi = {
            "year": ec.getYearShiShenZhi(),
            "month": ec.getMonthShiShenZhi(),
            "day": ec.getDayShiShenZhi(),
            "time": ec.getTimeShiShenZhi(),
        }

        # 纳音
        nayin = {
            "year": ec.getYearNaYin(),
            "month": ec.getMonthNaYin(),
            "day": ec.getDayNaYin(),
            "time": ec.getTimeNaYin(),
        }

        # 空亡
        xunkong = {
            "year": ec.getYearXunKong(),
            "day": ec.getDayXunKong(),
        }

        # 大运
        dayun_list = []
        dayun_start_year = 0
        dayun_start_age = 0
        try:
            yun = ec.getYun(gender=gender)
            for d in yun.getDaYun():
                gz = d.getGanZhi()
                if gz:
                    dayun_list.append({
                        "start_age": d.getStartYear(),
                        "end_age": d.getStartYear() + 9,
                        "ganzhi": gz,
                        "start_year": time.original.year + d.getStartYear(),
                    })
            dayun_start_year = time.original.year + yun.getStartYear()
            dayun_start_age = yun.getStartYear()
        except Exception:
            pass

        # 日主五行
        gan_wuxing = {
            "甲": "木", "乙": "木", "丙": "火", "丁": "火",
            "戊": "土", "己": "土", "庚": "金", "辛": "金",
            "壬": "水", "癸": "水",
        }
        day_master_wuxing = gan_wuxing.get(day_master, "")

        # 调候用神
        tiaohou = self._calc_tiaohou(day_master, month_pillar.zhi)

        # 特征提取
        features = self._extract_features(
            year_pillar, month_pillar, day_pillar, time_pillar,
            shishen_gan, hidden_gans
        )

        return {
            "year": year_pillar,
            "month": month_pillar,
            "day": day_pillar,
            "time": time_pillar,
            "day_master": day_master,
            "day_master_wuxing": day_master_wuxing,
            "hidden_gans": hidden_gans,
            "shishen_gan": shishen_gan,
            "shishen_zhi": shishen_zhi,
            "nayin": nayin,
            "xunkong": xunkong,
            "dayun": dayun_list,
            "dayun_start_year": dayun_start_year,
            "dayun_start_age": dayun_start_age,
            "tiaohou": tiaohou,
            "features": features,
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if "error" in data:
            return False, data["error"]
        if not data.get("day_master"):
            return False, "日主为空"
        return True, None

    def _calc_tiaohou(self, day_gan: str, month_zhi: str) -> str:
        """调候用神计算"""
        table = {
            ("甲", "寅"): "丙癸", ("甲", "卯"): "庚丙戊", ("甲", "辰"): "庚丁壬",
            ("甲", "巳"): "癸庚丁", ("甲", "午"): "癸庚丁", ("甲", "未"): "癸庚丁",
            ("甲", "申"): "庚丁壬", ("甲", "酉"): "庚丁丙", ("甲", "戌"): "庚丁甲",
            ("甲", "亥"): "庚丁丙戊", ("甲", "子"): "丁丙庚", ("甲", "丑"): "丁丙庚",
            ("乙", "寅"): "丙癸", ("乙", "卯"): "丙癸", ("乙", "辰"): "癸丙戊",
            ("乙", "巳"): "癸", ("乙", "午"): "癸", ("乙", "未"): "癸",
            ("乙", "申"): "癸丙戊", ("乙", "酉"): "癸丙丁", ("乙", "戌"): "癸辛",
            ("乙", "亥"): "丙戊", ("乙", "子"): "丙", ("乙", "丑"): "丙",
            ("丙", "寅"): "壬庚", ("丙", "卯"): "壬己", ("丙", "辰"): "壬甲",
            ("丙", "巳"): "壬庚癸", ("丙", "午"): "壬庚", ("丙", "未"): "壬庚",
            ("丙", "申"): "壬戊", ("丙", "酉"): "壬戊", ("丙", "戌"): "甲壬",
            ("丙", "亥"): "甲戊庚壬", ("丙", "子"): "壬戊戊", ("丙", "丑"): "壬甲",
            ("丁", "寅"): "甲庚", ("丁", "卯"): "庚甲", ("丁", "辰"): "甲庚",
            ("丁", "巳"): "甲庚", ("丁", "午"): "壬庚癸", ("丁", "未"): "甲壬庚",
            ("丁", "申"): "甲庚丙", ("丁", "酉"): "甲庚丙", ("丁", "戌"): "甲庚",
            ("丁", "亥"): "甲戊", ("丁", "子"): "甲戊", ("丁", "丑"): "甲戊",
            ("戊", "寅"): "丙甲癸", ("戊", "卯"): "丙甲癸", ("戊", "辰"): "甲丙癸",
            ("戊", "巳"): "甲丙癸", ("戊", "午"): "壬甲丙", ("戊", "未"): "癸丙甲",
            ("戊", "申"): "丙癸甲", ("戊", "酉"): "丙癸", ("戊", "戌"): "甲丙癸",
            ("戊", "亥"): "丙甲", ("戊", "子"): "丙甲", ("戊", "丑"): "丙甲",
            ("己", "寅"): "丙癸庚", ("己", "卯"): "癸丙庚", ("己", "辰"): "癸丙戊",
            ("己", "巳"): "癸丙", ("己", "午"): "癸丙", ("己", "未"): "癸丙",
            ("己", "申"): "丙癸", ("己", "酉"): "丙癸", ("己", "戌"): "甲丙癸",
            ("己", "亥"): "丙甲戊", ("己", "子"): "丙甲戊", ("己", "丑"): "丙甲戊",
            ("庚", "寅"): "戊甲丙", ("庚", "卯"): "丁甲庚", ("庚", "辰"): "甲丁壬",
            ("庚", "巳"): "壬戊丙丁", ("庚", "午"): "壬癸", ("庚", "未"): "丁甲",
            ("庚", "申"): "丁甲", ("庚", "酉"): "丁甲丙", ("庚", "戌"): "甲丁",
            ("庚", "亥"): "丁丙", ("庚", "子"): "丁甲丙", ("庚", "丑"): "丙丁甲",
            ("辛", "寅"): "己壬庚", ("辛", "卯"): "壬甲", ("辛", "辰"): "壬甲",
            ("辛", "巳"): "壬甲癸", ("辛", "午"): "壬己癸", ("辛", "未"): "壬庚甲",
            ("辛", "申"): "壬甲戊", ("辛", "酉"): "壬甲", ("辛", "戌"): "壬甲",
            ("辛", "亥"): "壬丙", ("辛", "子"): "壬丙戊", ("辛", "丑"): "壬丙戊",
            ("壬", "寅"): "庚丙戊", ("壬", "卯"): "戊庚辛", ("壬", "辰"): "甲庚",
            ("壬", "巳"): "庚癸辛", ("壬", "午"): "癸庚辛", ("壬", "未"): "辛庚癸",
            ("壬", "申"): "戊丁", ("壬", "酉"): "丁甲", ("壬", "戌"): "甲庚",
            ("壬", "亥"): "戊丙庚", ("壬", "子"): "戊丙戊", ("壬", "丑"): "丙丁甲",
            ("癸", "寅"): "辛丙", ("癸", "卯"): "庚辛", ("癸", "辰"): "丙辛甲",
            ("癸", "巳"): "辛", ("癸", "午"): "庚辛壬", ("癸", "未"): "庚辛壬",
            ("癸", "申"): "丁甲", ("癸", "酉"): "辛丙", ("癸", "戌"): "辛甲",
            ("癸", "亥"): "庚戊辛丙", ("癸", "子"): "丙辛丙", ("癸", "丑"): "丙丁",
        }
        return table.get((day_gan, month_zhi), "")

    def _extract_features(self, year, month, day, time, shishen_gan, hidden_gans) -> list:
        """提取命盘核心特征"""
        features = []
        ba = {"year": year, "month": month, "day": day, "time": time}

        # 1. 冲
        zhis = [p.zhi for p in [year, month, day, time]]
        chong_pairs = [("子","午"), ("丑","未"), ("寅","申"), ("卯","酉"), ("辰","戌"), ("巳","亥")]
        for i, z1 in enumerate(zhis):
            for j, z2 in enumerate(zhis[i+1:], i+1):
                if (z1, z2) in chong_pairs or (z2, z1) in chong_pairs:
                    pos_names = ["年","月","日","时"]
                    features.append(f"{z1}{z2}冲 — {pos_names[i]}支与{pos_names[j]}支相冲")

        # 2. 合
        for i, z1 in enumerate(zhis):
            for j, z2 in enumerate(zhis[i+1:], i+1):
                # 六合
                liuhe = {"子":"丑","丑":"子","寅":"亥","亥":"寅","卯":"戌","戌":"卯","辰":"酉","酉":"辰","巳":"申","申":"巳","午":"未","未":"午"}
                if liuhe.get(z1) == z2:
                    pos_names = ["年","月","日","时"]
                    features.append(f"{z1}{z2}合 — {pos_names[i]}支与{pos_names[j]}支相合")

        # 3. 七杀透干
        ss = shishen_gan
        if ss.get("time") == "七杀":
            features.append("七杀透干时柱 — 自我驱动力强，但压力大")
        if ss.get("month") == "七杀":
            features.append("七杀当令 — 竞争意识强")
        if ss.get("year") == "七杀":
            features.append("年柱七杀 — 早年多磨练")

        # 4. 正官
        if ss.get("time") == "正官":
            features.append("正官透干时柱 — 责任心强，自律")
        if ss.get("month") == "正官":
            features.append("正官当令 — 正统、规矩")

        # 5. 印星
        yin_count = sum(1 for v in ss.values() if "印" in v)
        if yin_count >= 2:
            features.append("印星多现 — 学习能力强，有贵人")
        elif yin_count == 0:
            features.append("印星不显 — 缺乏外部支持")

        # 6. 财星
        cai_count = sum(1 for v in ss.values() if "财" in v)
        if cai_count >= 2:
            features.append("财星多现 — 对物质敏感")
        elif cai_count == 0:
            features.append("财星不显 — 不重物质")

        # 7. 食伤
        shis = [v for v in ss.values() if "食" in v or "伤" in v]
        if len(shis) >= 2:
            features.append("食伤旺 — 表达欲强，创造力佳")

        # 8. 比劫
        bijian = [v for v in ss.values() if "比" in v or "劫" in v]
        if len(bijian) >= 2:
            features.append("比劫多 — 朋友多，竞争也多")

        # 9. 日支特殊
        day_zhi = day.zhi
        if day_zhi in ["子", "午", "卯", "酉"]:
            features.append(f"日坐{day_zhi} — 四正之地，性格鲜明")

        # 10. 日主坐禄
        day_gan = day.gan
        lu_map = {"甲":"寅","乙":"卯","丙":"巳","丁":"午","戊":"巳","己":"午","庚":"申","辛":"酉","壬":"亥","癸":"子"}
        if lu_map.get(day_gan) == day_zhi:
            features.append("日坐禄地 — 自身根基扎实")

        return features[:12]  # 最多12条
