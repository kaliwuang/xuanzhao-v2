#!/usr/bin/env python3
"""
玄照 v2.0 - 六爻引擎（完整版）

梅花易数时间起卦法 + 纳甲装卦 + 六亲 + 六神 + 世应 + 变卦

起卦方法：时间起卦
  上卦 = (年数 + 月数 + 日数) % 8
  下卦 = (年数 + 月数 + 日数 + 时数) % 8
  动爻 = (年数 + 月数 + 日数 + 时数) % 6

纳甲法：按京房纳甲体系
  乾纳甲壬，坤纳乙癸，震纳庚，巽纳辛，坎纳戊，离纳己，艮纳丙，兑纳丁
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional, Dict, List, Tuple


class LiuYaoEngine(DivinationEngine):
    """六爻引擎"""

    @property
    def name(self) -> str:
        return "六爻"

    @property
    def name_en(self) -> str:
        return "LiuYao"

    @property
    def priority(self) -> int:
        return 3

    # 八卦基本信息：(五行, 纳甲天干, 二进制三爻)
    # 二进制：1=阳爻(—), 0=阴爻(--)
    # 从下往上读
    BAGUA = {
        "乾": ("金", "甲", (1, 1, 1)),
        "兑": ("金", "丁", (1, 1, 0)),
        "离": ("火", "己", (1, 0, 1)),
        "震": ("木", "庚", (0, 0, 1)),
        "巽": ("木", "辛", (1, 1, 0)),  # 从下: 0,1,1 → 巽
        "坎": ("水", "戊", (0, 1, 0)),
        "艮": ("土", "丙", (0, 0, 1)),  # 从下: 1,0,0 → 艮
        "坤": ("土", "乙", (0, 0, 0)),
    }

    # 修正八卦二进制（从下爻到上爻）
    BAGUA_LINES = {
        "乾": (1, 1, 1),  # ─ ─ ─
        "兑": (0, 1, 1),  # -- ─ ─
        "离": (1, 0, 1),  # ─ -- ─
        "震": (1, 0, 0),  # ─ -- --
        "巽": (0, 1, 1),  # -- ─ ─  # 注意：兑巽相同二进制，靠上下卦区分
        "坎": (0, 1, 0),  # -- ─ --
        "艮": (0, 0, 1),  # -- -- ─
        "坤": (0, 0, 0),  # -- -- --
    }

    # 更正：八卦二进制（从初爻到上爻）
    # 乾=111, 兑=011, 离=101, 震=100, 巽=011, 坎=010, 艮=001, 坤=000
    # 兑和巽都是011？不对，重新定义：
    # 乾(天)=阳阳阳=111
    # 兑(泽)=阴阳阳=011  (初爻阴)
    # 离(火)=阳阴阳=101
    # 震(雷)=阳阴阴=100  (初爻阳，二三爻阴)
    # 巽(风)=阴阳阳=011  (初爻阴，二三爻阳)  ← 这和兑一样？
    # 不对！标准：
    # 兑=上缺: 初爻阳，二爻阳，三爻阴 → 1,1,0
    # 巽=下断: 初爻阴，二爻阳，三爻阳 → 0,1,1
    # 坎=中满: 初爻阴，二爻阳，三爻阴 → 0,1,0
    # 艮=上实: 初爻阴，二爻阴，三爻阳 → 0,0,1
    # 坤=三断: 阴阴阴 → 0,0,0

    # 最终正确的八卦二进制（从初爻到上爻）
    GUA_LINES = {
        "乾": (1, 1, 1),
        "兑": (1, 1, 0),
        "离": (1, 0, 1),
        "震": (1, 0, 0),
        "巽": (0, 1, 1),
        "坎": (0, 1, 0),
        "艮": (0, 0, 1),
        "坤": (0, 0, 0),
    }

    # 八卦五行
    GUA_WUXING = {
        "乾": "金", "兑": "金", "离": "火", "震": "木",
        "巽": "木", "坎": "水", "艮": "土", "坤": "土",
    }

    # 纳甲表：八卦 → (内卦纳干, 外卦纳干)
    # 乾纳甲壬(内甲外壬), 坤纳乙癸(内乙外癸)
    # 震纳庚, 巽纳辛, 坎纳戊, 离纳己, 艮纳丙, 兑纳丁
    NAJIA = {
        "乾": ("甲", "壬"),
        "坤": ("乙", "癸"),
        "震": ("庚", "庚"),
        "巽": ("辛", "辛"),
        "坎": ("戊", "戊"),
        "离": ("己", "己"),
        "艮": ("丙", "丙"),
        "兑": ("丁", "丁"),
    }

    # 纳甲地支：八卦 → (内卦六爻地支, 外卦六爻地支)
    # 从初爻到上爻
    NAJIA_ZHI = {
        "乾": (["子", "寅", "辰"], ["午", "申", "戌"]),
        "坤": (["未", "巳", "卯"], ["丑", "亥", "酉"]),
        "震": (["子", "寅", "辰"], ["午", "申", "戌"]),
        "巽": (["丑", "亥", "酉"], ["未", "巳", "卯"]),
        "坎": (["寅", "辰", "午"], ["申", "戌", "子"]),
        "离": (["卯", "丑", "亥"], ["酉", "未", "巳"]),
        "艮": (["辰", "午", "申"], ["戌", "子", "寅"]),
        "兑": (["巳", "卯", "丑"], ["亥", "酉", "未"]),
    }

    # 数字转八卦（先天八卦序：乾1兑2离3震4巽5坎6艮7坤8/0）
    NUM_TO_GUA = ["坤", "乾", "兑", "离", "震", "巽", "坎", "艮"]

    # 六十四卦名 (上卦, 下卦) → 卦名
    GUA64_NAMES = {
        ("乾", "乾"): "乾为天", ("乾", "坤"): "天地否", ("乾", "震"): "天雷无妄",
        ("乾", "巽"): "天风姤", ("乾", "坎"): "天水讼", ("乾", "离"): "天火同人",
        ("乾", "艮"): "天山遁", ("乾", "兑"): "天泽履",
        ("坤", "坤"): "坤为地", ("坤", "乾"): "地天泰", ("坤", "震"): "地雷复",
        ("坤", "巽"): "地风升", ("坤", "坎"): "地水师", ("坤", "离"): "地火明夷",
        ("坤", "艮"): "地山谦", ("坤", "兑"): "地泽临",
        ("震", "震"): "震为雷", ("震", "乾"): "雷天大壮", ("震", "坤"): "雷地豫",
        ("震", "巽"): "雷风恒", ("震", "坎"): "雷水解", ("震", "离"): "雷火丰",
        ("震", "艮"): "雷山小过", ("震", "兑"): "雷泽归妹",
        ("巽", "巽"): "巽为风", ("巽", "乾"): "风天小畜", ("巽", "坤"): "风地观",
        ("巽", "震"): "风雷益", ("巽", "坎"): "风水涣", ("巽", "离"): "风火家人",
        ("巽", "艮"): "风山渐", ("巽", "兑"): "风泽中孚",
        ("坎", "坎"): "坎为水", ("坎", "乾"): "水天需", ("坎", "坤"): "水地比",
        ("坎", "震"): "水雷屯", ("坎", "巽"): "水风井", ("坎", "离"): "水火既济",
        ("坎", "艮"): "水山蹇", ("坎", "兑"): "水泽节",
        ("离", "离"): "离为火", ("离", "乾"): "火天大有", ("离", "坤"): "火地晋",
        ("离", "震"): "火雷噬嗑", ("离", "巽"): "火风鼎", ("离", "坎"): "火水未济",
        ("离", "艮"): "火山旅", ("离", "兑"): "火泽睽",
        ("艮", "艮"): "艮为山", ("艮", "乾"): "山天大畜", ("艮", "坤"): "山地剥",
        ("艮", "震"): "山雷颐", ("艮", "巽"): "山风蛊", ("艮", "坎"): "山水蒙",
        ("艮", "离"): "山火贲", ("艮", "兑"): "山泽损",
        ("兑", "兑"): "兑为泽", ("兑", "乾"): "泽天夬", ("兑", "坤"): "泽地萃",
        ("兑", "震"): "泽雷随", ("兑", "巽"): "泽风大过", ("兑", "坎"): "泽水困",
        ("兑", "离"): "泽火革", ("兑", "艮"): "泽山咸",
    }

    # 六神（按日干排）
    LIU_SHEN = {
        "甲": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
        "乙": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
        "丙": ["朱雀", "勾陈", "螣蛇", "白虎", "玄武", "青龙"],
        "丁": ["朱雀", "勾陈", "螣蛇", "白虎", "玄武", "青龙"],
        "戊": ["勾陈", "螣蛇", "白虎", "玄武", "青龙", "朱雀"],
        "己": ["勾陈", "螣蛇", "白虎", "玄武", "青龙", "朱雀"],
        "庚": ["螣蛇", "白虎", "玄武", "青龙", "朱雀", "勾陈"],
        "辛": ["螣蛇", "白虎", "玄武", "青龙", "朱雀", "勾陈"],
        "壬": ["白虎", "玄武", "青龙", "朱雀", "勾陈", "螣蛇"],
        "癸": ["白虎", "玄武", "青龙", "朱雀", "勾陈", "螣蛇"],
    }

    # 世应表：64卦 → (世爻位, 应爻位)，1-6从初爻到上爻
    # 八纯卦世在六爻，应在三爻
    # 归魂卦世在三爻，应在六爻
    # 游魂卦世在四爻，应在初爻
    # 一世卦世在初爻，应在四爻
    # 二世卦世在二爻，应在五爻
    # 三世卦世在三爻，应在六爻
    # 四世卦世在四爻，应在初爻
    # 五世卦世在五爻，应在二爻
    # 本宫卦世在六爻，应在三爻
    SHI_YING_TABLE = {
        # 乾宫
        "乾为天": (6, 3), "天风姤": (1, 4), "天山遁": (2, 5), "天地否": (3, 6),
        "风地观": (4, 1), "山地剥": (5, 2), "火地晋": (4, 1), "火天大有": (3, 6),
        # 坤宫
        "坤为地": (6, 3), "地雷复": (1, 4), "地泽临": (2, 5), "地天泰": (3, 6),
        "雷天大壮": (4, 1), "泽天夬": (5, 2), "水天需": (4, 1), "水地比": (3, 6),
        # 震宫
        "震为雷": (6, 3), "雷地豫": (1, 4), "雷水解": (2, 5), "雷风恒": (3, 6),
        "地风升": (4, 1), "水风井": (5, 2), "泽风大过": (4, 1), "泽雷随": (3, 6),
        # 巽宫
        "巽为风": (6, 3), "风天小畜": (1, 4), "风火家人": (2, 5), "风雷益": (3, 6),
        "天雷无妄": (4, 1), "火雷噬嗑": (5, 2), "山雷颐": (4, 1), "山风蛊": (3, 6),
        # 坎宫
        "坎为水": (6, 3), "水泽节": (1, 4), "水雷屯": (2, 5), "水火既济": (3, 6),
        "泽火革": (4, 1), "雷火丰": (5, 2), "地火明夷": (4, 1), "地水师": (3, 6),
        # 离宫
        "离为火": (6, 3), "火山旅": (1, 4), "火风鼎": (2, 5), "火水未济": (3, 6),
        "山水蒙": (4, 1), "风水涣": (5, 2), "天水讼": (4, 1), "天火同人": (3, 6),
        # 艮宫
        "艮为山": (6, 3), "山火贲": (1, 4), "山天大畜": (2, 5), "山泽损": (3, 6),
        "火泽睽": (4, 1), "天泽履": (5, 2), "风泽中孚": (4, 1), "风山渐": (3, 6),
        # 兑宫
        "兑为泽": (6, 3), "泽水困": (1, 4), "泽地萃": (2, 5), "泽山咸": (3, 6),
        "水山蹇": (4, 1), "地山谦": (5, 2), "雷山小过": (4, 1), "雷泽归妹": (3, 6),
    }

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

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        dt = time.true_solar

        # 获取农历信息用于起卦
        try:
            from lunar_python import Solar
            solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
            lunar = solar.getLunar()
            year_num = lunar.getYear()
            month_num = lunar.getMonth()
            day_num = lunar.getDay()
            ec = lunar.getEightChar()
            day_gan = ec.getDayGan()
            day_zhi = ec.getDayZhi()
        except Exception:
            year_num = dt.year
            month_num = dt.month
            day_num = dt.day
            day_gan = "甲"
            day_zhi = "子"

        hour_zhi_idx = (dt.hour + 1) // 2 % 12
        hour_num = hour_zhi_idx + 1  # 子=1, 丑=2...

        # 1. 梅花易数起卦
        shang_num = abs(year_num) + month_num + day_num
        xia_num = shang_num + hour_num

        shang_gua = self._num_to_gua(shang_num)
        xia_gua = self._num_to_gua(xia_num)

        # 动爻
        dong_yao = (shang_num + hour_num) % 6
        if dong_yao == 0:
            dong_yao = 6

        # 2. 获取六爻（本卦）
        ben_lines = self._get_hexagram_lines(shang_gua, xia_gua)

        # 3. 变卦
        bian_lines = list(ben_lines)
        bian_lines[dong_yao - 1] = 1 - bian_lines[dong_yao - 1]
        bian_shang = self._lines_to_gua(bian_lines[3:6])
        bian_xia = self._lines_to_gua(bian_lines[0:3])

        # 4. 卦名
        ben_name = self.GUA64_NAMES.get((shang_gua, xia_gua), f"{shang_gua}上{xia_gua}下")
        bian_name = self.GUA64_NAMES.get((bian_shang, bian_xia), f"{bian_shang}上{bian_xia}下")

        # 5. 纳甲装卦
        yao_list = self._najia_zhuanggua(shang_gua, xia_gua, ben_lines, day_gan, day_zhi)

        # 6. 世应
        shi_ying = self.SHI_YING_TABLE.get(ben_name, (6, 3))
        shi_pos, ying_pos = shi_ying

        # 7. 六亲（根据卦宫五行定六亲）
        gua_gong_wuxing = self.GUA_WUXING.get(shang_gua, "金")  # 以上卦五行为卦宫

        # 8. 六神
        liu_shen = self.LIU_SHEN.get(day_gan, self.LIU_SHEN["甲"])

        # 9. 变爻纳甲
        bian_yao_list = self._najia_zhuanggua(bian_shang, bian_xia, bian_lines, day_gan, day_zhi)

        return {
            "ben_gua": {
                "name": ben_name,
                "shang": shang_gua,
                "xia": xia_gua,
                "shang_wuxing": self.GUA_WUXING.get(shang_gua, ""),
                "xia_wuxing": self.GUA_WUXING.get(xia_gua, ""),
            },
            "bian_gua": {
                "name": bian_name,
                "shang": bian_shang,
                "xia": bian_xia,
            },
            "dong_yao": dong_yao,
            "shi": shi_pos,
            "ying": ying_pos,
            "lines": yao_list,
            "bian_lines": bian_yao_list,
            "liu_shen": liu_shen,
            "gua_gong_wuxing": gua_gong_wuxing,
            "date": dt.strftime("%Y-%m-%d %H:%M"),
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if not data.get("ben_gua"):
            return False, "本卦为空"
        return True, None

    def _num_to_gua(self, num: int) -> str:
        """数字转八卦（先天数：乾1兑2离3震4巽5坎6艮7坤8/0）"""
        idx = abs(num) % 8
        if idx == 0:
            idx = 8
        gua_list = ["", "乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
        return gua_list[idx]

    def _get_hexagram_lines(self, shang: str, xia: str) -> list:
        """获取六爻二进制（从初爻到上爻）"""
        xia_lines = self.GUA_LINES[xia]    # 下卦 = 初二三爻
        shang_lines = self.GUA_LINES[shang]  # 上卦 = 四五六爻
        return list(xia_lines) + list(shang_lines)

    def _lines_to_gua(self, three_lines: tuple) -> str:
        """三爻二进制 → 八卦名"""
        for name, lines in self.GUA_LINES.items():
            if lines == tuple(three_lines):
                return name
        return "乾"

    def _najia_zhuanggua(self, shang_gua: str, xia_gua: str,
                          lines: list, day_gan: str, day_zhi: str) -> list:
        """纳甲装卦：为每一爻分配天干、地支、五行、六亲"""
        xia_zhi = self.NAJIA_ZHI.get(xia_gua, (["子", "寅", "辰"], ["午", "申", "戌"]))[0]
        shang_zhi = self.NAJIA_ZHI.get(shang_gua, (["子", "寅", "辰"], ["午", "申", "戌"]))[1]
        all_zhi = xia_zhi + shang_zhi  # 6个地支

        xia_gan = self.NAJIA.get(xia_gua, ("甲", "壬"))[0]
        shang_gan = self.NAJIA.get(shang_gua, ("甲", "壬"))[1]

        # 卦宫五行（以上卦定宫）
        gua_wuxing = self.GUA_WUXING.get(shang_gua, "金")

        yao_list = []
        for i in range(6):
            zhi = all_zhi[i]
            gan = xia_gan if i < 3 else shang_gan
            yao_wuxing = self.ZHI_WUXING.get(zhi, "")
            liuqin = self._calc_liuqin(gua_wuxing, yao_wuxing)

            yao_list.append({
                "position": i + 1,
                "yinyang": "阳" if lines[i] == 1 else "阴",
                "gan": gan,
                "zhi": zhi,
                "wuxing": yao_wuxing,
                "liuqin": liuqin,
                "is_dong": False,  # 后面设置
                "is_shi": False,
                "is_ying": False,
            })

        return yao_list

    def _calc_liuqin(self, gua_wuxing: str, yao_wuxing: str) -> str:
        """计算六亲"""
        # 生我者父母，我生者子孙，克我者官鬼，我克者妻财，同我者兄弟
        relations = {
            ("金", "金"): "兄弟", ("金", "木"): "妻财", ("金", "水"): "子孙",
            ("金", "火"): "官鬼", ("金", "土"): "父母",
            ("木", "木"): "兄弟", ("木", "土"): "妻财", ("木", "火"): "子孙",
            ("木", "金"): "官鬼", ("木", "水"): "父母",
            ("水", "水"): "兄弟", ("水", "火"): "妻财", ("水", "土"): "子孙",
            ("水", "木"): "官鬼", ("水", "金"): "父母",
            ("火", "火"): "兄弟", ("火", "金"): "妻财", ("火", "水"): "子孙",
            ("火", "土"): "官鬼", ("火", "木"): "父母",
            ("土", "土"): "兄弟", ("土", "水"): "妻财", ("土", "木"): "子孙",
            ("土", "火"): "官鬼", ("土", "金"): "父母",
        }
        return relations.get((gua_wuxing, yao_wuxing), "兄弟")
