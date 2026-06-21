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
    # 规则：每个"节"继承前一个"中气"的月将
    # 12中气→月将：大寒→子, 雨水→亥, 春分→戌, 谷雨→酉, 小满→申, 夏至→未,
    #              大暑→午, 处暑→巳, 秋分→辰, 霜降→卯, 小雪→寅, 冬至→丑
    JIEQI_TO_YUEJIANG = {
        # 中气
        "大寒": "子", "雨水": "亥", "春分": "戌",
        "谷雨": "酉", "小满": "申", "夏至": "未",
        "大暑": "午", "处暑": "巳", "秋分": "辰",
        "霜降": "卯", "小雪": "寅", "冬至": "丑",
        # 节（继承前一个中气的月将）
        "小寒": "丑",   # 冬至后→丑
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
                san_chuan_raw, si_ke_raw, day_gan, day_zhi, tian_jiang
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
            gz = val[0] if isinstance(val[0], str) else str(val[0])
            jiang = val[1] if len(val) > 1 else ''

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
                           day_gan: str, day_zhi: str, tian_jiang: dict) -> dict:
        """分析用神：基于三传初传的天将和六亲关系"""
        if not san_chuan_raw or not isinstance(san_chuan_raw, dict):
            return {}
        # 十二天将含义（含kinliuren缩写映射，兼容繁简体）
        JIANG_YI = {
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

        # 初传信息
        chu_chuan = san_chuan_raw.get("初傳", [])
        chu_zhi = chu_chuan[0] if chu_chuan else ""
        chu_jiang = chu_chuan[1] if len(chu_chuan) > 1 else ""
        chu_liuqin = chu_chuan[2] if len(chu_chuan) > 2 else ""

        # 初传天将含义
        jiang_info = JIANG_YI.get(chu_jiang, {"吉凶": "中", "含义": ""})

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
        except Exception:
            pass

        try:
            current_solar = lunar.getSolar()
            current_md = (current_solar.getMonth(), current_solar.getDay())

            prev_name = "冬至"
            for name, m, d in JIEQI_APPROX_TABLE:
                if current_md < (m, d):
                    break
                prev_name = name
            return prev_name
        except Exception:
            pass

        # 最终回退：按农历月份估算节气（用于月将判定）
        # 月将由"节"决定（非中气），每个节继承前一个中气的月将
        # 农历月份与"节"对应：正月→立春, 二月→惊蛰, ..., 十一月→大雪, 十二月→小寒
        # lunar_python 闰月返回负数（如闰四月=-4），取绝对值映射到同月节气
        month = abs(lunar.getMonth())
        approx = {
            1: "立春", 2: "惊蛰", 3: "清明", 4: "立夏",
            5: "芒种", 6: "小暑", 7: "立秋", 8: "白露",
            9: "寒露", 10: "立冬", 11: "大雪", 12: "小寒",
        }
        return approx.get(month, "冬至")
