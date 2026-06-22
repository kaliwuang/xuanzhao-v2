#!/usr/bin/env python3
"""
玄照 v2.0 - 六爻引擎

主路径：基于 najia 库的纳甲六爻排盘
回退路径：自包含的梅花易数 + 京房纳甲体系

起卦方法：时间起卦（确定性，基于出生时间哈希）
纳甲法：按京房纳甲体系
  乾纳甲壬，坤纳乙癸，震纳庚，巽纳辛，坎纳戊，离纳己，艮纳丙，兑纳丁
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)

# 甲子年基准年（用于干支年份近似计算，lunar_python不可用时的回退路径）
JIA_ZI_YEAR = 1984


class LiuYaoEngine(DivinationEngine):
    """六爻引擎（najia 库主路径 + 自包含回退）"""

    # ─── 属性 ────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "六爻"

    @property
    def name_en(self) -> str:
        return "liuyao"

    @property
    def priority(self) -> int:
        return 4

    # ─── 八卦二进制（从初爻到上爻）─── 自包含回退用 ────

    GUA_LINES = {
        "乾": (1, 1, 1), "兑": (1, 1, 0), "离": (1, 0, 1), "震": (1, 0, 0),
        "巽": (0, 1, 1), "坎": (0, 1, 0), "艮": (0, 0, 1), "坤": (0, 0, 0),
    }

    GUA_WUXING = {
        "乾": "金", "兑": "金", "离": "火", "震": "木",
        "巽": "木", "坎": "水", "艮": "土", "坤": "土",
    }

    NAJIA = {
        "乾": ("甲", "壬"), "坤": ("乙", "癸"), "震": ("庚", "庚"), "巽": ("辛", "辛"),
        "坎": ("戊", "戊"), "离": ("己", "己"), "艮": ("丙", "丙"), "兑": ("丁", "丁"),
    }

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

    # 卦码(bit tuple)→八卦名 的反向映射（消除 GUAS 二进制索引的位序 bug）
    LINES_TO_GUA = {
        (1, 1, 1): "乾", (1, 1, 0): "兑", (1, 0, 1): "离", (1, 0, 0): "震",
        (0, 1, 1): "巽", (0, 1, 0): "坎", (0, 0, 1): "艮", (0, 0, 0): "坤",
    }

    # 六十四卦→京房八宫归属（修正builtin路径gong字段：游魂/归魂等非本宫卦不能用上卦名代替宫名）
    GUA64_TO_GONG = {
        '乾为天': '乾', '天风姤': '乾', '天山遁': '乾', '天地否': '乾',
        '风地观': '乾', '山地剥': '乾', '火地晋': '乾', '火天大有': '乾',
        '坤为地': '坤', '地雷复': '坤', '地泽临': '坤', '地天泰': '坤',
        '雷天大壮': '坤', '泽天夬': '坤', '水天需': '坤', '水地比': '坤',
        '震为雷': '震', '雷地豫': '震', '雷水解': '震', '雷风恒': '震',
        '地风升': '震', '水风井': '震', '泽风大过': '震', '泽雷随': '震',
        '巽为风': '巽', '风天小畜': '巽', '风火家人': '巽', '风雷益': '巽',
        '天雷无妄': '巽', '火雷噬嗑': '巽', '山雷颐': '巽', '山风蛊': '巽',
        '坎为水': '坎', '水泽节': '坎', '水雷屯': '坎', '水火既济': '坎',
        '泽火革': '坎', '雷火丰': '坎', '地火明夷': '坎', '地水师': '坎',
        '离为火': '离', '火山旅': '离', '火风鼎': '离', '火水未济': '离',
        '山水蒙': '离', '风水涣': '离', '天水讼': '离', '天火同人': '离',
        '艮为山': '艮', '山火贲': '艮', '山天大畜': '艮', '山泽损': '艮',
        '火泽睽': '艮', '天泽履': '艮', '风泽中孚': '艮', '风山渐': '艮',
        '兑为泽': '兑', '泽水困': '兑', '泽地萃': '兑', '泽山咸': '兑',
        '水山蹇': '兑', '地山谦': '兑', '雷山小过': '兑', '雷泽归妹': '兑',
    }

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

    LIU_SHEN = {
        "甲": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
        "乙": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
        "丙": ["朱雀", "勾陈", "螣蛇", "白虎", "玄武", "青龙"],
        "丁": ["朱雀", "勾陈", "螣蛇", "白虎", "玄武", "青龙"],
        "戊": ["勾陈", "螣蛇", "白虎", "玄武", "青龙", "朱雀"],
        "己": ["螣蛇", "白虎", "玄武", "青龙", "朱雀", "勾陈"],
        "庚": ["白虎", "玄武", "青龙", "朱雀", "勾陈", "螣蛇"],
        "辛": ["白虎", "玄武", "青龙", "朱雀", "勾陈", "螣蛇"],
        "壬": ["玄武", "青龙", "朱雀", "勾陈", "螣蛇", "白虎"],
        "癸": ["玄武", "青龙", "朱雀", "勾陈", "螣蛇", "白虎"],
    }

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

    # 京房八宫归属 → 卦宫五行
    GUA_GONG_WUXING = {
        "乾为天": "金", "天风姤": "金", "天山遁": "金", "天地否": "金",
        "风地观": "金", "山地剥": "金", "火地晋": "金", "火天大有": "金",
        "坤为地": "土", "地雷复": "土", "地泽临": "土", "地天泰": "土",
        "雷天大壮": "土", "泽天夬": "土", "水天需": "土", "水地比": "土",
        "震为雷": "木", "雷地豫": "木", "雷水解": "木", "雷风恒": "木",
        "地风升": "木", "水风井": "木", "泽风大过": "木", "泽雷随": "木",
        "巽为风": "木", "风天小畜": "木", "风火家人": "木", "风雷益": "木",
        "天雷无妄": "木", "火雷噬嗑": "木", "山雷颐": "木", "山风蛊": "木",
        "坎为水": "水", "水泽节": "水", "水雷屯": "水", "水火既济": "水",
        "泽火革": "水", "雷火丰": "水", "地火明夷": "水", "地水师": "水",
        "离为火": "火", "火山旅": "火", "火风鼎": "火", "火水未济": "火",
        "山水蒙": "火", "风水涣": "火", "天水讼": "火", "天火同人": "火",
        "艮为山": "土", "山火贲": "土", "山天大畜": "土", "山泽损": "土",
        "火泽睽": "土", "天泽履": "土", "风泽中孚": "土", "风山渐": "土",
        "兑为泽": "金", "泽水困": "金", "泽地萃": "金", "泽山咸": "金",
        "水山蹇": "金", "地山谦": "金", "雷山小过": "金", "雷泽归妹": "金",
    }

    ZHI_WUXING = {
        "子": "水", "丑": "土", "寅": "木", "卯": "木",
        "辰": "土", "巳": "火", "午": "火", "未": "土",
        "申": "金", "酉": "金", "戌": "土", "亥": "水",
    }

    GAN_WUXING = {
        "甲": "木", "乙": "木", "丙": "火", "丁": "火",
        "戊": "土", "己": "土", "庚": "金", "辛": "金",
        "壬": "水", "癸": "水",
    }

    # ─── 初始化 ──────────────────────────────────────────

    def __init__(self):
        self._najia_available = False
        try:
            from najia import Najia
            # 测试实例化（najia 2.0.1 的 __init__ 有 verbose=None 的 bug）
            Najia(verbose=0)
            self._Najia = Najia
            self._najia_available = True
        except Exception as e:
            logger.debug(f"najia 库加载失败，将使用内置引擎: {e}")

    # ─── 确定性爻值生成 ──────────────────────────────────

    def _generate_params(self, dt) -> list:
        """
        基于时间哈希确定性生成6个爻值。

        编码（najia 库格式）：
          0 = 阴静, 1 = 阳静, 3 = 老阳（阳动）, 4 = 老阴（阴动）

        至少包含一个动爻以确保有变卦。
        """
        # 使用时间戳（秒级精度）作为种子，确保同分钟内不同调用产生相同卦象（六爻传统）
        seed = f"{dt.year}{dt.month:02d}{dt.day:02d}{dt.hour:02d}{dt.minute:02d}"
        h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)

        params = []
        for i in range(6):
            v = (h >> (i * 3)) & 7
            # 概率分布：~25% 阳静, ~25% 阴静, ~25% 阳动, ~25% 阴动
            if v < 2:
                params.append(1)   # 阳静
            elif v < 4:
                params.append(0)   # 阴静
            elif v < 6:
                params.append(3)   # 老阳（阳动）
            else:
                params.append(4)   # 老阴（阴动）

        # 确保至少一个动爻（根据哈希值随机选择老阳或老阴）
        if not any(p > 2 for p in params):
            params[h % 6] = 3 if (h // 6) % 2 == 0 else 4

        return params

    # ─── 主分析方法 ──────────────────────────────────────

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        """
        六爻排盘分析。

        优先使用 najia 库；若不可用或出错则回退到自包含引擎。
        """
        try:
            if self._najia_available:
                return self._analyze_najia(time, gender)
        except Exception as e:
            logger.warning(f"najia 库排盘失败，回退到内置引擎: {e}")

        return self._analyze_builtin(time, gender)

    # ─── najia 库排盘 ────────────────────────────────────

    def _analyze_najia(self, time: CorrectedTime, gender: int) -> dict:
        """使用 najia 库进行纳甲六爻排盘"""
        from najia.utils import get_najia
        from najia.const import (
            ZHI5, ZHIS, XING5, GUA5, GUAS, GUA64, GANS
        )

        orig = time.true_solar

        # 1. 确定性起卦
        params = self._generate_params(orig)

        # 2. 排盘
        date_str = f"{orig.year}-{orig.month:02d}-{orig.day:02d} {orig.hour:02d}:{orig.minute:02d}"
        n = self._Najia(verbose=0)
        n.compile(params=params, gender=gender, date=date_str)
        data = n.data

        mark = data.get('mark', '')          # 二进制卦码 "111000"
        dong = data.get('dong') or []  # 动爻列表（0-indexed），防御None
        # 过滤dong列表中的无效值（None、负数、越界索引）
        dong = [d for d in dong if d is not None and 0 <= d < 6]
        shi_ying = data.get('shiy', (6, 3, 0))  # (世爻, 应爻, 宫位) 世应1-indexed
        qin6 = data.get('qin6', [])          # 六亲 list[6]
        god6 = data.get('god6', [])          # 六神 list[6]
        gong_name = data.get('gong', '')     # 卦宫名 e.g. "乾"

        # 3. 获取纳甲干支
        najia_gz = get_najia(mark)   # list[6] e.g. ["甲子", "甲寅", ...]

        # 4. 构建 lines
        lines = []
        for i in range(6):
            gz = najia_gz[i]
            if len(gz) < 2:
                logger.warning(f"najia返回异常干支'{gz}'(位置{i+1})，用默认值甲子替代")
                gan, dizhi = '甲', '子'
            else:
                gan = gz[0]
                dizhi = gz[1]
            try:
                wz_idx = ZHIS.index(dizhi)
            except ValueError:
                logger.warning(f"najia返回未知地支'{dizhi}'(位置{i+1}，干支'{gz}')，回退子水")
                dizhi = '子'
                wz_idx = 0
            wuxing = XING5[ZHI5[wz_idx]]
            # 阴阳由卦码mark决定（1=阳爻，0=阴爻），而非地支奇偶
            yinyang = '阳' if i < len(mark) and mark[i] == '1' else '阴'
            lines.append({
                'liu_qin': qin6[i],
                'liu_shen': god6[i],
                'wuxing': wuxing,
                'dizhi': dizhi,
                'gan': gan,
                'yinyang': yinyang,
                'position': i + 1,
                'is_dong': i in dong,
                'is_shi': (i + 1) == shi_ying[0],
                'is_ying': (i + 1) == shi_ying[1],
            })

        # 5. 变卦
        bian_data = data.get('bian')
        bian_gua = {}
        bian_lines = []
        if bian_data:
            bian_mark = bian_data.get('mark', '')
            bian_qin6 = bian_data.get('qin6', [])
            bian_name = bian_data.get('name', '')

            # 变卦也需要正确查卦名（直接用 LINES_TO_GUA，无需反转）
            if len(bian_mark) >= 6:
                bian_xia_gua = self.LINES_TO_GUA.get(tuple(int(c) for c in bian_mark[:3]), '')
                bian_shang_gua = self.LINES_TO_GUA.get(tuple(int(c) for c in bian_mark[3:]), '')
            else:
                bian_shang_gua = bian_xia_gua = ''
            bian_gua = {
                'name': bian_name,
                'mark': bian_mark,
                'shang': bian_shang_gua,
                'xia': bian_xia_gua,
                'gong': bian_data.get('gong', ''),
            }

            if bian_mark and len(bian_mark) >= 6:
                bian_najia = get_najia(bian_mark)
                for i in range(6):
                    gz = bian_najia[i]
                    if len(gz) < 2:
                        logger.warning(f"变卦najia返回异常干支'{gz}'(位置{i+1})，用默认值甲子替代")
                        gan, dizhi = '甲', '子'
                    else:
                        gan = gz[0]
                        dizhi = gz[1]
                    try:
                        wz_idx = ZHIS.index(dizhi)
                    except ValueError:
                        logger.warning(f"变卦najia返回未知地支'{dizhi}'(位置{i+1}，干支'{gz}')，回退子水")
                        dizhi = '子'
                        wz_idx = 0
                    wuxing = XING5[ZHI5[wz_idx]]
                    # 阴阳由变卦卦码决定（与本卦一致的编码逻辑）
                    bian_yinyang = '阳' if i < len(bian_mark) and bian_mark[i] == '1' else '阴'
                    bian_lines.append({
                        'liu_qin': bian_qin6[i] if i < len(bian_qin6) else '',
                        'liu_shen': god6[i] if i < len(god6) else '',
                        'wuxing': wuxing,
                        'dizhi': dizhi,
                        'gan': gan,
                        'yinyang': bian_yinyang,
                        'position': i + 1,
                        'is_shi': (i + 1) == shi_ying[0],
                        'is_ying': (i + 1) == shi_ying[1],
                    })

        # 7. 本卦信息（先算上下卦名，供卦宫五行回退使用）
        # ⚠️ 位序：mark 从初爻到上爻存储（bit0=初爻），直接用 LINES_TO_GUA 查卦名（无需反转）
        if len(mark) >= 6:
            xia_gua = self.LINES_TO_GUA.get(tuple(int(c) for c in mark[:3]), '')
            shang_gua = self.LINES_TO_GUA.get(tuple(int(c) for c in mark[3:]), '')
        else:
            shang_gua = xia_gua = ''
        # GUA64 以 (上卦, 下卦) 元组为键，不能用字符串 mark 查找
        # 使用 or 而非 get default，确保 data['name'] 为空字符串时也触发 fallback
        ben_gua_name = data.get('name') or self.GUA64_NAMES.get((shang_gua, xia_gua), '')

        # 6. 卦宫五行（依赖shang_gua，故移到其后）
        if gong_name and gong_name in GUAS:
            gong_idx = GUAS.index(gong_name)
            gua_gong_wuxing = XING5[GUA5[gong_idx]]
        else:
            # 卦宫名不在GUAS中时，用上下卦的五行来推断（非硬编码回退到乾金）
            gua_gong_wuxing = self.GUA_WUXING.get(shang_gua) or self.GUA_WUXING.get(xia_gua, '金')
        ben_gua = {
            'name': ben_gua_name,
            'mark': mark,
            'shang': shang_gua,
            'xia': xia_gua,
            'gong': gong_name,
        }

        # 8. 伏神（隐藏信息）
        hide = data.get('hide')

        # 9. 五行分析摘要
        wuxing_count = {}
        for line in lines:
            wx = line.get('wuxing', '')
            if wx:
                wuxing_count[wx] = wuxing_count.get(wx, 0) + 1

        # 世爻五行分析
        shi_yao = next((l for l in lines if l.get('is_shi')), {})
        shi_wuxing = shi_yao.get('wuxing', '')
        gua_gong_wx = gua_gong_wuxing or ''

        # 用神分析（根据卦宫五行和世爻关系）
        yong_shen = ''
        if shi_wuxing and gua_gong_wx:
            if shi_wuxing == gua_gong_wx:
                yong_shen = '世爻与卦宫同五行，自身有力'
            else:
                rel = self._calc_liuqin(gua_gong_wx, shi_wuxing)
                relation_desc = self._get_wuxing_relation(shi_wuxing, gua_gong_wx)
                yong_shen = f'世爻为{rel}，{relation_desc}'

        # 10. 详细用神分析
        yong_shen_detail = self._build_yong_shen_detail(
            lines, bian_lines, shi_ying[0], shi_ying[1], gua_gong_wuxing, list(dong)
        )

        # 11. 格局识别
        bian_gua_name = bian_gua.get('name', '')
        ge_ju = self._identify_ge_ju(
            ben_gua_name, bian_gua_name, lines, bian_lines, shi_ying[0], shi_ying[1]
        )

        result = {
            'engine': self.name,
            'engine_en': self.name_en,
            'ben_gua': ben_gua,
            'bian_gua': bian_gua,
            'dong_yao': [d + 1 for d in dong],  # najia 0-indexed → 统一为 1-indexed
            'shi': shi_ying[0],
            'ying': shi_ying[1],
            'lines': lines,
            'bian_lines': bian_lines,
            'liu_shen': list(god6),
            'gua_gong_wuxing': gua_gong_wuxing,
            'date': orig.strftime("%Y-%m-%d %H:%M"),
            'wuxing_analysis': {
                'wuxing_count': wuxing_count,
                'shi_wuxing': shi_wuxing,
                'yong_shen': yong_shen,
                'yong_shen_detail': yong_shen_detail,
            },
            'ge_ju': ge_ju,
        }

        # 日月建分析（使用bazi统一的晚子时修正，与_builtin路径保持一致）
        try:
            from lunar_python import Solar
            # 晚子时(23:xx)用次日日期+子时(hour=0)，与八字引擎统一
            ri_dt = time.bazi_day_pillar_date
            ri_hour = time.bazi_hour
            solar = Solar.fromYmdHms(ri_dt.year, ri_dt.month, ri_dt.day, ri_hour, orig.minute, 0)
            lunar = solar.getLunar()
            ec = lunar.getEightChar()
            day_g = ec.getDayGan()
            day_z = ec.getDayZhi()
            month_z = ec.getMonthZhi()
            result['ri_yue_jian'] = self._calc_ri_yue_jian(day_g, day_z, month_z, gua_gong_wuxing)
        except Exception as e:
            logger.debug(f"六爻日月建计算异常: {e}")

        # 流年太岁分析（复用共享方法）
        try:
            result['liunian'] = self._build_liunian(lines)
        except Exception as e:
            logger.debug(f"流年分析失败: {e}")

        if hide:
            result['fu_shen'] = hide

        return result

    # ─── 自包含引擎（回退）──────────────────────────────

    def _analyze_builtin(self, time: CorrectedTime, gender: int) -> dict:
        """自包含的梅花易数 + 京房纳甲排盘（无需外部库）"""
        orig = time.true_solar

        # 晚子时使用八字引擎统一的日期和时辰处理（与其他引擎保持一致）
        pillar_date = time.bazi_day_pillar_date
        bazi_hour = time.bazi_hour

        # 获取农历信息用于起卦
        lunar = None
        try:
            from lunar_python import Solar
            solar = Solar.fromYmdHms(pillar_date.year, pillar_date.month, pillar_date.day, bazi_hour, orig.minute, 0)
            lunar = solar.getLunar()
            year_num = lunar.getYear()
            month_num = lunar.getMonth()
            day_num = lunar.getDay()
            ec = lunar.getEightChar()
            day_gan = ec.getDayGan()
            day_zhi = ec.getDayZhi()
        except Exception as e:
            logger.warning(f"lunar_python 异常，使用公历近似起卦: {e}")
            year_num = orig.year
            month_num = orig.month
            day_num = orig.day
            day_gan = "甲"
            day_zhi = "子"

        hour_zhi_idx = (bazi_hour + 1) // 2 % 12
        hour_num = hour_zhi_idx + 1

        # 1. 梅花易数起卦
        shang_num = abs(year_num) + month_num + day_num
        xia_num = shang_num + hour_num

        shang_gua = self._num_to_gua(shang_num)
        xia_gua = self._num_to_gua(xia_num)

        # 动爻
        dong_yao_pos = (shang_num + hour_num) % 6
        if dong_yao_pos == 0:
            dong_yao_pos = 6

        # 2. 获取六爻（本卦）
        ben_lines = self._get_hexagram_lines(shang_gua, xia_gua)

        # 3. 变卦
        bian_lines_raw = list(ben_lines)
        bian_lines_raw[dong_yao_pos - 1] = 1 - bian_lines_raw[dong_yao_pos - 1]
        bian_shang = self._lines_to_gua(bian_lines_raw[3:6])
        bian_xia = self._lines_to_gua(bian_lines_raw[0:3])

        # 4. 卦名
        ben_name = self.GUA64_NAMES.get((shang_gua, xia_gua), f"{shang_gua}上{xia_gua}下")
        bian_name = self.GUA64_NAMES.get((bian_shang, bian_xia), f"{bian_shang}上{bian_xia}下")

        # 5. 纳甲装卦
        gua_gong_wuxing = self.GUA_GONG_WUXING.get(ben_name, self.GUA_WUXING.get(shang_gua, "金"))
        yao_list = self._najia_zhuanggua(shang_gua, xia_gua, ben_lines, day_gan, day_zhi, gua_gong_wuxing)

        # 5b. 标记动爻（本卦保留原始阴阳，变卦才显示变化后的阴阳）
        yao_list[dong_yao_pos - 1]['is_dong'] = True

        # 6. 世应
        shi_ying = self.SHI_YING_TABLE.get(ben_name, (6, 3))
        shi_pos, ying_pos = shi_ying
        yao_list[shi_pos - 1]['is_shi'] = True
        yao_list[ying_pos - 1]['is_ying'] = True

        # 7. 六神
        liu_shen = self.LIU_SHEN.get(day_gan, self.LIU_SHEN["甲"])

        # 8. 变爻纳甲（变卦使用自身宫五行计算六亲，而非本卦宫五行）
        bian_gua_gong_wuxing = self.GUA_GONG_WUXING.get(bian_name, self.GUA_WUXING.get(bian_shang, gua_gong_wuxing))
        bian_yao_list = self._najia_zhuanggua(bian_shang, bian_xia, bian_lines_raw, day_gan, day_zhi, bian_gua_gong_wuxing)
        bian_yao_list[shi_pos - 1]['is_shi'] = True
        bian_yao_list[ying_pos - 1]['is_ying'] = True

        # 9. 为每行添加 liu_shen
        for i, yao in enumerate(yao_list):
            yao['liu_shen'] = liu_shen[i]

        # 构建标准化 lines 输出
        lines = []
        for yao in yao_list:
            lines.append({
                'liu_qin': yao['liuqin'],
                'liu_shen': yao.get('liu_shen', ''),
                'wuxing': yao['wuxing'],
                'dizhi': yao['zhi'],
                'gan': yao['gan'],
                'position': yao['position'],
                'is_dong': yao['is_dong'],
                'is_shi': yao['is_shi'],
                'is_ying': yao['is_ying'],
                'yinyang': yao.get('yinyang', ''),
            })

        bian_lines = []
        for i, yao in enumerate(bian_yao_list):
            bian_lines.append({
                'liu_qin': yao['liuqin'],
                'liu_shen': liu_shen[i] if i < len(liu_shen) else '',
                'wuxing': yao['wuxing'],
                'dizhi': yao['zhi'],
                'gan': yao['gan'],
                'position': yao['position'],
                'yinyang': yao.get('yinyang', ''),
                'is_shi': yao.get('is_shi', False),
                'is_ying': yao.get('is_ying', False),
            })

        # 构造卦码字符串（与najia路径格式一致：从初爻到上爻的0/1序列）
        mark_str = ''.join(str(b) for b in ben_lines)
        bian_mark_str = ''.join(str(b) for b in bian_lines_raw)

        result = {
            'engine': self.name,
            'engine_en': self.name_en,
            'ben_gua': {
                'name': ben_name,
                'mark': mark_str,
                'shang': shang_gua,
                'xia': xia_gua,
                'gong': self.GUA64_TO_GONG.get(ben_name, shang_gua),  # 京房八宫归属（游魂/归魂卦宫名≠上卦名）
                'shang_wuxing': self.GUA_WUXING.get(shang_gua, ''),
                'xia_wuxing': self.GUA_WUXING.get(xia_gua, ''),
            },
            'bian_gua': {
                'name': bian_name,
                'mark': bian_mark_str,
                'shang': bian_shang,
                'xia': bian_xia,
                'gong': self.GUA64_TO_GONG.get(bian_name, bian_shang),
            },
            'dong_yao': [dong_yao_pos],
            'shi': shi_pos,
            'ying': ying_pos,
            'lines': lines,
            'bian_lines': bian_lines,
            'liu_shen': liu_shen,
            'gua_gong_wuxing': gua_gong_wuxing,
            'date': orig.strftime("%Y-%m-%d %H:%M"),
            'wuxing_analysis': self._builtin_wuxing_analysis(
                lines, bian_lines, shi_pos, ying_pos, gua_gong_wuxing, [dong_yao_pos]
            ),
            'ge_ju': self._identify_ge_ju(
                ben_name, bian_name, lines, bian_lines, shi_pos, ying_pos
            ),
            'ri_yue_jian': self._calc_ri_yue_jian_safe(day_gan, day_zhi, lunar, gua_gong_wuxing),
        }

        # 流年太岁分析（复用共享方法）
        try:
            result['liunian'] = self._build_liunian(lines)
        except Exception as e:
            logger.debug(f"流年分析失败: {e}")

        return result

    # ─── 自包含工具方法 ──────────────────────────────────

    def _num_to_gua(self, num: int) -> str:
        """数字转八卦（先天数：乾1兑2离3震4巽5坎6艮7坤8/0）"""
        idx = abs(num) % 8
        if idx == 0:
            idx = 8
        gua_list = ["", "乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
        return gua_list[idx]

    def _get_hexagram_lines(self, shang: str, xia: str) -> list:
        """获取六爻二进制（从初爻到上爻）"""
        xia_lines = self.GUA_LINES[xia]
        shang_lines = self.GUA_LINES[shang]
        return list(xia_lines) + list(shang_lines)

    def _lines_to_gua(self, three_lines) -> str:
        """三爻二进制 → 八卦名"""
        t = tuple(three_lines)
        result = self.LINES_TO_GUA.get(t, "")
        if not result:
            logger.warning(f"_lines_to_gua: 未识别的三爻组合 {t}，回退到坤")
            result = "坤"
        return result

    def _najia_zhuanggua(self, shang_gua: str, xia_gua: str,
                         lines: list, day_gan: str, day_zhi: str,
                         gua_gong_wuxing: str = None) -> list:
        """纳甲装卦：为每一爻分配天干、地支、五行、六亲"""
        xia_zhi = self.NAJIA_ZHI.get(xia_gua, (["子", "寅", "辰"], ["午", "申", "戌"]))[0]
        shang_zhi = self.NAJIA_ZHI.get(shang_gua, (["子", "寅", "辰"], ["午", "申", "戌"]))[1]
        all_zhi = xia_zhi + shang_zhi

        xia_gan = self.NAJIA.get(xia_gua, ("甲", "壬"))[0]
        shang_gan = self.NAJIA.get(shang_gua, ("甲", "壬"))[1]

        gua_wuxing = gua_gong_wuxing or self.GUA_WUXING.get(shang_gua, "金")

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
                "is_dong": False,
                "is_shi": False,
                "is_ying": False,
            })

        return yao_list

    def _builtin_wuxing_analysis(self, lines: list, bian_lines: list,
                                 shi_pos: int, ying_pos: int,
                                 gua_gong_wuxing: str, dong: list) -> dict:
        """内置引擎的五行分析摘要（与najia路径输出一致，含详细用神分析）"""
        wuxing_count = {}
        for line in lines:
            wx = line.get('wuxing', '')
            if wx:
                wuxing_count[wx] = wuxing_count.get(wx, 0) + 1

        shi_wuxing = ''
        for line in lines:
            if line.get('position') == shi_pos:
                shi_wuxing = line.get('wuxing', '')
                break

        gua_gong_wx = gua_gong_wuxing or ''
        yong_shen = ''
        if shi_wuxing and gua_gong_wx:
            if shi_wuxing == gua_gong_wx:
                yong_shen = '世爻与卦宫同五行，自身有力'
            else:
                rel = self._calc_liuqin(gua_gong_wx, shi_wuxing)
                relation_desc = self._get_wuxing_relation(shi_wuxing, gua_gong_wx)
                yong_shen = f'世爻为{rel}，{relation_desc}'

        # 详细用神分析
        yong_shen_detail = self._build_yong_shen_detail(
            lines, bian_lines, shi_pos, ying_pos, gua_gong_wuxing, dong
        )

        return {
            'wuxing_count': wuxing_count,
            'shi_wuxing': shi_wuxing,
            'yong_shen': yong_shen,
            'yong_shen_detail': yong_shen_detail,
        }

    # ─── 地支冲合关系 ──────────────────────────────────────

    ZHI_CHONG = {
        "子": "午", "午": "子", "丑": "未", "未": "丑",
        "寅": "申", "申": "寅", "卯": "酉", "酉": "卯",
        "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳",
    }

    ZHI_HE = {
        "子": "丑", "丑": "子", "寅": "亥", "亥": "寅",
        "卯": "戌", "戌": "卯", "辰": "酉", "酉": "辰",
        "巳": "申", "申": "巳", "午": "未", "未": "午",
    }

    # 三合局：地支→(局名, 五行)  申子辰合水、寅午戌合火、巳酉丑合金、亥卯未合木
    ZHI_SAN_HE = {
        "子": ("水局", "水"), "申": ("水局", "水"), "辰": ("水局", "水"),
        "午": ("火局", "火"), "寅": ("火局", "火"), "戌": ("火局", "火"),
        "酉": ("金局", "金"), "巳": ("金局", "金"), "丑": ("金局", "金"),
        "卯": ("木局", "木"), "亥": ("木局", "木"), "未": ("木局", "木"),
    }

    SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
    KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}
    SHENG_REV = {v: k for k, v in SHENG.items()}
    KE_REV = {v: k for k, v in KE.items()}

    LIUQIN_TABLE = {
        ("金", "金"): "兄弟", ("金", "木"): "妻财", ("金", "水"): "子孙",
        ("金", "火"): "官鬼", ("金", "土"): "父母",
        ("木", "木"): "兄弟", ("木", "土"): "妻财", ("木", "火"): "子孙",
        ("木", "金"): "官鬼", ("木", "水"): "父母",
        ("水", "水"): "兄弟", ("水", "火"): "妻财", ("水", "土"): "官鬼",
        ("水", "木"): "子孙", ("水", "金"): "父母",
        ("火", "火"): "兄弟", ("火", "金"): "妻财", ("火", "水"): "官鬼",
        ("火", "土"): "子孙", ("火", "木"): "父母",
        ("土", "土"): "兄弟", ("土", "水"): "妻财", ("土", "木"): "官鬼",
        ("土", "火"): "父母", ("土", "金"): "子孙",
    }

    def _calc_liuqin(self, gua_wuxing: str, yao_wuxing: str) -> str:
        """计算六亲。当五行参数无效时返回空字符串而非默认'兄弟'（兄弟仅在同五行时成立）"""
        if not gua_wuxing or not yao_wuxing:
            return ''
        return self.LIUQIN_TABLE.get((gua_wuxing, yao_wuxing), '')

    def _get_wuxing_relation(self, wx_a: str, wx_b: str) -> str:
        """计算两个五行之间的关系（A 对 B）"""
        if not wx_a or not wx_b:
            return '未知'
        if wx_a == wx_b:
            return '比和'
        if self.SHENG.get(wx_a) == wx_b:
            return f'{wx_a}生{wx_b}（我生）'
        if self.SHENG.get(wx_b) == wx_a:
            return f'{wx_b}生{wx_a}（生我）'
        # 克: A克B
        if self.KE.get(wx_a) == wx_b:
            return f'{wx_a}克{wx_b}（我克）'
        if self.KE.get(wx_b) == wx_a:
            return f'{wx_b}克{wx_a}（克我）'
        return '未知'

    DONG_YAO_MEANINGS = {
        0: '无动爻，卦象静止，事情稳定不变',
        1: '一爻动，事有专主，变化明确，易断',
        2: '二爻动，事情有两方面变化，需看动爻关系',
        3: '三爻动，事情变化较多，以中间动爻为主',
        4: '四爻动，变化纷繁，以不变之爻为主断',
        5: '五爻动，以唯一静爻为主断',
        6: '六爻全动，事情剧变，需看变卦整体',
    }

    def _get_dong_yao_meaning(self, count: int) -> str:
        """解释动爻数量的含义"""
        return self.DONG_YAO_MEANINGS.get(count, '动爻异常')

    # 京房八宫游魂卦（各宫第7卦）——世在四爻，主游移不定
    YOU_HUN_GUAS = frozenset({
        "火地晋",     # 乾宫
        "水天需",     # 坤宫
        "泽风大过",   # 震宫
        "山雷颐",     # 巽宫
        "地火明夷",   # 坎宫
        "天水讼",     # 离宫
        "风泽中孚",   # 艮宫
        "雷山小过",   # 兑宫
    })

    # 京房八宫归魂卦（各宫第8卦）——世在三爻，主回归落实
    GUI_HUN_GUAS = frozenset({
        "火天大有",   # 乾宫
        "水地比",     # 坤宫
        "泽雷随",     # 震宫
        "山风蛊",     # 巽宫
        "地水师",     # 坎宫
        "天火同人",   # 离宫
        "风山渐",     # 艮宫
        "雷泽归妹",   # 兑宫
    })

    def _identify_ge_ju(self, ben_name: str, bian_name: str,
                        lines: list, bian_lines: list,
                        shi_pos: int, ying_pos: int) -> list:
        """
        识别六爻格局。

        返回格局列表，可能包含：
        - 伏吟：变卦与本卦卦码完全相同
        - 反吟：变卦与本卦卦码完全相反
        - 六冲：上卦与下卦地支形成六冲关系
        - 六合：上卦与下卦地支形成六合关系
        - 世应冲：世爻与应爻地支相冲
        - 世应合：世爻与应爻地支相合
        - 三合X局：六爻地支中三支组成三合局（水/火/金/木）
        - 半合X局：六爻地支中有两支属于同一三合局（半合）
        - 游魂卦：京房八宫第7卦，事有游移反复
        - 归魂卦：京房八宫第8卦，事归定局
        """
        ge_ju = []

        # 1. 伏吟/反吟（基于完整六爻地支对比——传统定义）
        if lines and bian_lines and len(lines) == 6 and len(bian_lines) == 6:
            # 伏吟：变卦与本卦所有爻地支完全相同（卦象不变）
            # 防御空地支：所有爻都必须有有效地支才算伏吟
            all_same = all(
                l.get('dizhi') and l.get('dizhi') == bl.get('dizhi')
                for l, bl in zip(lines, bian_lines)
            )
            if all_same:
                ge_ju.append('伏吟')
            # 反吟：变卦与本卦所有爻地支六冲（卦象完全相反）
            elif all(
                self.ZHI_CHONG.get(l.get('dizhi', '')) == bl.get('dizhi', '')
                for l, bl in zip(lines, bian_lines)
            ):
                ge_ju.append('反吟')

        # 2. 六冲/六合（检查上卦与下卦的地支配对）
        if lines and len(lines) == 6:
            # 对应位置：初爻-四爻, 二爻-五爻, 三爻-上爻
            chong_count = 0
            he_count = 0
            for i in range(3):
                zhi_below = lines[i].get('dizhi', '')
                zhi_above = lines[i + 3].get('dizhi', '')
                if zhi_below and zhi_above:
                    if self.ZHI_CHONG.get(zhi_below) == zhi_above:
                        chong_count += 1
                    if self.ZHI_HE.get(zhi_below) == zhi_above:
                        he_count += 1

            if chong_count == 3:
                ge_ju.append('六冲')
            elif he_count == 3:
                ge_ju.append('六合')

        # 3. 世应冲/合
        if lines and len(lines) == 6:
            shi_zhi = lines[shi_pos - 1].get('dizhi', '') if 1 <= shi_pos <= 6 else ''
            ying_zhi = lines[ying_pos - 1].get('dizhi', '') if 1 <= ying_pos <= 6 else ''
            if shi_zhi and ying_zhi:
                if self.ZHI_CHONG.get(shi_zhi) == ying_zhi:
                    ge_ju.append('世应冲')
                elif self.ZHI_HE.get(shi_zhi) == ying_zhi:
                    ge_ju.append('世应合')

        # 4. 三合局（检查六爻中是否有三支组成三合局）
        #    传统六爻重要格局：申子辰合水、寅午戌合火、巳酉丑合金、亥卯未合木
        #    注意：必须对地支去重计数，否则重复地支（如两个子+一个申）会被误判为三合
        if lines and len(lines) == 6:
            zhis = [l.get('dizhi', '') for l in lines]
            # 统计各三合局出现的爻位（按去重后的地支计数）
            _san_he_groups = {}
            for i, z in enumerate(zhis):
                if not z or z not in self.ZHI_SAN_HE:
                    continue
                ju_name, ju_wx = self.ZHI_SAN_HE[z]
                if ju_name not in _san_he_groups:
                    _san_he_groups[ju_name] = {'wx': ju_wx, 'positions': [], 'unique_zhis': set()}
                _san_he_groups[ju_name]['positions'].append(i + 1)
                _san_he_groups[ju_name]['unique_zhis'].add(z)

            for ju_name, info in _san_he_groups.items():
                distinct_count = len(info['unique_zhis'])
                if distinct_count == 3:
                    ge_ju.append(f'三合{ju_name}')
                elif distinct_count == 2:
                    ge_ju.append(f'半合{ju_name}')

        # 5. 游魂卦/归魂卦（京房八宫核心格局——反映事物发展周期的阶段）
        if ben_name in self.YOU_HUN_GUAS:
            ge_ju.append('游魂卦')
        elif ben_name in self.GUI_HUN_GUAS:
            ge_ju.append('归魂卦')

        return ge_ju if ge_ju else ['普通']

    def _build_yong_shen_detail(self, lines: list, bian_lines: list,
                                shi_pos: int, ying_pos: int,
                                gua_gong_wuxing: str, dong: list) -> dict:
        """
        构建详细的用神分析。

        包含世爻六亲、世爻与卦宫五行关系、动爻分析、
        变卦与本卦宫五行关系、世应距离与五行关系。
        """
        # 世爻信息
        shi_yao = next((l for l in lines if l.get('position') == shi_pos), {})
        shi_wuxing = shi_yao.get('wuxing', '')
        shi_liu_qin = shi_yao.get('liu_qin', '')
        shi_dizhi = shi_yao.get('dizhi', '')

        # 应爻信息
        ying_yao = next((l for l in lines if l.get('position') == ying_pos), {})
        ying_wuxing = ying_yao.get('wuxing', '')
        ying_dizhi = ying_yao.get('dizhi', '')

        # 世爻与卦宫五行关系
        shi_yao_wuxing_relation = self._get_wuxing_relation(shi_wuxing, gua_gong_wuxing)

        # 动爻分析
        dong_yao_count = len(dong) if dong else 0
        dong_yao_meaning = self._get_dong_yao_meaning(dong_yao_count)

        # 世应距离
        shi_ying_distance = abs(shi_pos - ying_pos)
        shi_ying_relation = self._get_wuxing_relation(shi_wuxing, ying_wuxing)

        # 变卦宫五行关系
        bian_gua_relation = ''
        if bian_lines and len(bian_lines) >= 6:
            # 变卦的宫五行需要从 GUA_GONG_WUXING 查找
            # 这里用变卦的世爻五行来近似分析
            bian_shi_yao = next((l for l in bian_lines if l.get('position') == shi_pos), {})
            bian_shi_wx = bian_shi_yao.get('wuxing', '')
            if bian_shi_wx and shi_wuxing:
                bian_gua_relation = self._get_wuxing_relation(shi_wuxing, bian_shi_wx)

        return {
            'shi_yao_liu_qin': shi_liu_qin,
            'shi_yao_wuxing': shi_wuxing,
            'shi_yao_dizhi': shi_dizhi,
            'shi_yao_wuxing_relation': shi_yao_wuxing_relation,
            'dong_yao_count': dong_yao_count,
            'dong_yao_meaning': dong_yao_meaning,
            'shi_ying_distance': shi_ying_distance,
            'shi_ying_relation': shi_ying_relation,
            'bian_gua_relation': bian_gua_relation,
        }

    # ─── 验证 ────────────────────────────────────────────


    def _build_liunian(self, lines: list) -> dict:
        """流年太岁分析（najia/builtin路径共用）"""
        try:
            from lunar_python import Solar as _Solar
        except ImportError:
            logger.debug("lunar_python不可用，流年分析使用datetime近似")
            return self._build_liunian_fallback(lines)
        now = datetime.now()
        _solar = _Solar.fromYmdHms(now.year, now.month, now.day, now.hour, now.minute, 0)
        _lunar = _solar.getLunar()
        _year_zhi = _lunar.getYearZhi()
        _year_gan = _lunar.getYearGan()
        return self._analyze_tai_sui_lines(lines, now.year, _year_gan, _year_zhi)

    def _build_liunian_fallback(self, lines: list) -> dict:
        """lunar_python不可用时的流年近似分析"""
        now = datetime.now()
        year_offset = now.year - JIA_ZI_YEAR  # 甲子年基准
        gan_idx = year_offset % 10
        zhi_idx = year_offset % 12
        _year_gan = '甲乙丙丁戊己庚辛壬癸'[gan_idx]
        _year_zhi = '子丑寅卯辰巳午未申酉戌亥'[zhi_idx]
        return self._analyze_tai_sui_lines(lines, now.year, _year_gan, _year_zhi)

    def _analyze_tai_sui_lines(self, lines: list, year: int, year_gan: str, year_zhi: str) -> dict:
        """太岁与六爻各爻的关系分析（主路径/fallback共用，消除~45行重复代码）"""
        _tai_sui_wx = self.ZHI_WUXING.get(year_zhi, '')

        _shi_yao = next((l for l in lines if l.get('is_shi')), {})
        _shi_dizhi = _shi_yao.get('dizhi', '')
        _tai_sui_vs_shi = ''
        if _shi_dizhi and year_zhi:
            if _shi_dizhi == year_zhi:
                _tai_sui_vs_shi = '太岁临世爻，年运有靠'
            elif self.ZHI_HE.get(_shi_dizhi) == year_zhi:
                _tai_sui_vs_shi = '世爻与太岁六合，年运顺遂'
            elif self.ZHI_CHONG.get(_shi_dizhi) == year_zhi:
                _tai_sui_vs_shi = '世爻与太岁六冲，年运多变'
            else:
                _tai_sui_vs_shi = f'太岁{year_zhi}({_tai_sui_wx})与世爻{_shi_dizhi}无特殊关系'

        _tai_sui_yao_rel = []
        for _line in lines:
            _dz = _line.get('dizhi', '')
            _pos = _line.get('position', 0)
            if _dz == year_zhi:
                _tai_sui_yao_rel.append({'position': _pos, 'relation': '太岁临爻'})
            elif self.ZHI_HE.get(_dz) == year_zhi:
                _tai_sui_yao_rel.append({'position': _pos, 'relation': '六合太岁'})
            elif self.ZHI_CHONG.get(_dz) == year_zhi:
                _tai_sui_yao_rel.append({'position': _pos, 'relation': '六冲太岁'})

        return {
            'year': year,
            'year_ganzhi': f'{year_gan}{year_zhi}',
            'tai_sui_zhi': year_zhi,
            'tai_sui_wuxing': _tai_sui_wx,
            'tai_sui_vs_shi': _tai_sui_vs_shi,
            'tai_sui_yao_rel': _tai_sui_yao_rel,
        }

    def _calc_ri_yue_jian_safe(self, day_gan: str, day_zhi: str, lunar, gua_gong_wuxing: str = '') -> dict:
        """安全版日建月建计算：lunar对象可能不完整"""
        try:
            month_zhi = lunar.getMonthZhi() if lunar else '子'
        except Exception as e:
            logger.debug(f"六爻月支获取异常，回退子: {e}")
            month_zhi = "子"
        return self._calc_ri_yue_jian(day_gan, day_zhi, month_zhi, gua_gong_wuxing)

    def _calc_ri_yue_jian(self, day_gan: str, day_zhi: str, month_zhi: str, gua_gong_wuxing: str = '') -> dict:
        """计算日建月建对各爻的影响"""
        # 防御空值（lunar_python不可用时day_zhi/month_zhi可能为空）
        ri_jian = day_zhi  # 日建 = 日支
        yue_jian = month_zhi  # 月建 = 月支
        if not ri_jian or not yue_jian:
            return {
                'ri_jian': ri_jian, 'ri_jian_wuxing': '',
                'yue_jian': yue_jian, 'yue_jian_wuxing': '',
                'day_gan': day_gan, 'day_liuqin': '',
                'ri_wangshuai': {wx: '无' for wx in ['木','火','土','金','水']},
                'yue_wangshuai': {wx: '无' for wx in ['木','火','土','金','水']},
            }
        
        # 日建月建五行
        ri_wx = self.ZHI_WUXING.get(ri_jian, '')
        yue_wx = self.ZHI_WUXING.get(yue_jian, '')
        
        def _wx_relation(wx: str, ref_wx: str) -> str:
            """计算爻的五行相对于日建/月建的旺衰状态

            传统旺相休囚死定义（《卜筮正宗》标准，从令/日建月建的角度）：
              旺 = 与令同五行
              相 = 令生爻（令去生爻，爻处于上升期）
              休 = 爻生令（爻去生令，爻泄气休息）
              囚 = 爻克令（爻耗力去克令，受困）
              死 = 令克爻（令克制爻，最弱）
            """
            if not wx or not ref_wx:
                return '无'
            if wx == ref_wx:
                return '旺（比和）'
            if self.SHENG.get(ref_wx) == wx:
                return '相（令生爻）'
            if self.SHENG_REV.get(ref_wx) == wx:
                return '休（爻生令）'
            if self.KE.get(ref_wx) == wx:
                return '死（令克爻）'
            if self.KE_REV.get(ref_wx) == wx:
                return '囚（爻克令）'
            return '无'

        # 为每个五行计算日建/月建旺衰
        all_wx = ['木','火','土','金','水']
        ri_wangshuai = {wx: _wx_relation(wx, ri_wx) for wx in all_wx}
        yue_wangshuai = {wx: _wx_relation(wx, yue_wx) for wx in all_wx}

        return {
            'ri_jian': ri_jian,
            'ri_jian_wuxing': ri_wx,
            'yue_jian': yue_jian,
            'yue_jian_wuxing': yue_wx,
            'day_gan': day_gan,
            'day_liuqin': self._calc_liuqin(gua_gong_wuxing, self.GAN_WUXING.get(day_gan, '')),
            'ri_wangshuai': ri_wangshuai,
            'yue_wangshuai': yue_wangshuai,
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        """验证六爻排盘结果"""
        if "error" in data:
            return False, data["error"]
        if not data.get("ben_gua"):
            return False, "本卦为空"
        lines = data.get("lines", [])
        if len(lines) != 6:
            return False, f"爻数不为6（实际{len(lines)}）"
        if data.get("shi") is None or data.get("ying") is None:
            return False, "世应位置缺失"
        return True, None
