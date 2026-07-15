#!/usr/bin/env python3
"""
大运方向 P0 bug 回归测试

历史问题(2026-07-15 夜盘点):
- 男命阴年 chart 给的是顺排, 应为逆排(梧真盘 2005-06-09 男命)
- 代码 engine/bazi_engine.py:680-694 有 "direction = 'backward' # 逆排" 但 pass 掉
- 库 lunar_python 的 getDaYun() 不可靠, 必须自己 reverse

修法:
- 阳年男/阴年女 → 顺排
- 阴年男/阳年女 → 逆排
- 年干阴阳: 甲丙戊庚壬 = 阳, 乙丁己辛癸 = 阴
- gender: 1=男, 0=女

判断口径: 第一个大运相对月柱的偏移
- 阳年男: 第一个大运 = 月柱 + 1(顺)
- 阴年男: 第一个大运 = 月柱 - 1(逆)
- 阳年女: 第一个大运 = 月柱 - 1(逆)
- 阴年女: 第一个大运 = 月柱 + 1(顺)

注意: 月柱本身需要先看性别, lunar_python 已经做一次 reverse 了, 我们看实际效果。

梧真盘测试数据 (2005-06-09 11:50 内蒙古呼和浩特 男):
- 年干乙(阴) + 男命 = 应该逆排
- 2005 乙酉年壬午月甲子日庚午时
- 逆排: 第1大运 = 月柱前一位 = 辛巳(2-11 岁, 2007-2015)
- 已校正记忆 [[houhuibin-correct-bazi-2026-07-02]]: 2-11 辛巳 / 12-21 庚辰 / 22-31 己卯(现)
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 60 甲子序列
JIAZI_ORDER = [
    "甲子","乙丑","丙寅","丁卯","戊辰","己巳","庚午","辛未","壬申","癸酉",
    "甲戌","乙亥","丙子","丁丑","戊寅","己卯","庚辰","辛巳","壬午","癸未",
    "甲申","乙酉","丙戌","丁亥","戊子","己丑","庚寅","辛卯","壬辰","癸巳",
    "甲午","乙未","丙申","丁酉","戊戌","己亥","庚子","辛丑","壬寅","癸卯",
    "甲辰","乙巳","丙午","丁未","戊申","己酉","庚戌","辛亥","壬子","癸丑",
    "甲寅","乙卯","丙辰","丁巳","戊午","己未","庚申","辛酉","壬戌","癸亥",
]


def _jiazi_index(gz: str) -> int:
    """甲子序号 (0-59)"""
    return JIAZI_ORDER.index(gz)


def _next_gz(gz: str, steps: int) -> str:
    """相对当前干支偏移 steps 步(正=顺, 负=逆)"""
    idx = _jiazi_index(gz)
    return JIAZI_ORDER[(idx + steps) % 60]


def _get_engine():
    from engine.time_engine import get_time_engine
    from engine.bazi_engine import BaziEngine
    te = get_time_engine()
    return BaziEngine(), te


def _extract_gz(pillar_or_str):
    """从 Pillar 对象或字符串提取干支字符串"""
    if hasattr(pillar_or_str, 'gan') and hasattr(pillar_or_str, 'zhi'):
        return f"{pillar_or_str.gan}{pillar_or_str.zhi}"
    return pillar_or_str


def _run_analyze(birth: str, location: str, gender: int):
    engine, te = _get_engine()
    corrected = te.correct(birth, location)
    result = engine.analyze(corrected, gender)
    if "error" in result:
        pytest.skip(f"bazi_engine 不可用: {result['error']}")
    return result


class TestDayunDirection:
    """大运方向 P0 bug 回归 — 4 个标准 case + 梧真盘"""

    def test_yang_year_male_forward(self):
        """阳年男 → 顺排
        1990 庚(阳)年 男命 任意时辰
        """
        result = _run_analyze("1990-05-15 14:00", "北京", 1)
        dayun = result.get("dayun", [])
        assert len(dayun) >= 1, "应至少有 1 段大运"

        # 第一段大运的干支与月柱的关系: 阳年男 → 顺排(下一位)
        month_gz = _extract_gz(result.get("month", ""))  # type: ignore[assignment]
        assert month_gz, "应返回月柱"
        first_dy_gz = dayun[0]["ganzhi"]
        expected = _next_gz(month_gz, 1)
        assert first_dy_gz == expected, (
            f"阳年男 第一大运应为月柱下一位 ({expected}), 实际 {first_dy_gz}\n"
            f"完整大运: {[d['ganzhi'] for d in dayun[:5]]}"
        )

    def test_yin_year_male_backward(self):
        """阴年男 → 逆排 ← 梧真盘
        2005 乙(阴)年 男命 任意时辰 (梧真盘 2005-06-09 11:50)
        """
        result = _run_analyze("2005-06-09 11:50", "呼和浩特", 1)
        dayun = result.get("dayun", [])
        assert len(dayun) >= 1

        month_gz = _extract_gz(result.get("month", ""))  # type: ignore[assignment]
        first_dy_gz = dayun[0]["ganzhi"]
        # 阴年男 → 逆排(上一位) ← 这正是 P0 bug 触发条件
        expected = _next_gz(month_gz, -1)  # 辛巳

        assert first_dy_gz == expected, (
            f"【P0 复现】阴年男 第一大运应为月柱上一位 ({expected}), 实际 {first_dy_gz}\n"
            f"梧真盘应得: 2-11 辛巳 / 12-21 庚辰 / 22-31 己卯 (现在)\n"
            f"完整大运: {[(d['start_age'], d['ganzhi']) for d in dayun[:5]]}"
        )

    def test_yang_year_female_backward(self):
        """阳年女 → 逆排
        2000 庚(阳)年 女命
        """
        result = _run_analyze("2000-03-20 10:00", "北京", 0)
        dayun = result.get("dayun", [])
        assert len(dayun) >= 1

        month_gz = _extract_gz(result.get("month", ""))  # type: ignore[assignment]
        first_dy_gz = dayun[0]["ganzhi"]
        expected = _next_gz(month_gz, -1)

        assert first_dy_gz == expected, (
            f"阳年女 第一大运应为月柱上一位 ({expected}), 实际 {first_dy_gz}\n"
            f"完整大运: {[d['ganzhi'] for d in dayun[:5]]}"
        )

    def test_yin_year_female_forward(self):
        """阴年女 → 顺排
        1999 己(阴)年 女命
        """
        result = _run_analyze("1999-08-15 16:00", "北京", 0)
        dayun = result.get("dayun", [])
        assert len(dayun) >= 1

        month_gz = _extract_gz(result.get("month", ""))  # type: ignore[assignment]
        first_dy_gz = dayun[0]["ganzhi"]
        expected = _next_gz(month_gz, 1)

        assert first_dy_gz == expected, (
            f"阴年女 第一大运应为月柱下一位 ({expected}), 实际 {first_dy_gz}\n"
            f"完整大运: {[d['ganzhi'] for d in dayun[:5]]}"
        )

    def test_wu_real_panel_dayun_sequence(self):
        """梧真盘完整大运序列 (梧真盘乙酉壬午甲子庚午 男命逆排)
        起运 2 岁 (梧亲证) → 22-31 现在 = 己卯
        期望序列: 2-11 辛巳 / 12-21 庚辰 / 22-31 己卯 / 32-41 戊寅 / 42-51 丁丑
        """
        result = _run_analyze("2005-06-09 11:50", "呼和浩特", 1)
        dayun = result.get("dayun", [])

        # 取前 5 段
        expected_sequence = ["辛巳", "庚辰", "己卯", "戊寅", "丁丑"]
        actual_5 = [d["ganzhi"] for d in dayun[:5]]

        assert actual_5 == expected_sequence, (
            f"梧真盘大运序列应 = {expected_sequence}\n"
            f"实际 = {actual_5}\n"
            f"含年龄: {[(d['start_age'], d['ganzhi']) for d in dayun[:5]]}"
        )

    def test_wu_real_panel_current_dayun(self):
        """梧当前大运 = 己卯 (22-31 岁)
        梧 2026 年 22 岁(按周岁,虚岁 23),应落在 22-31 这段己卯
        """
        result = _run_analyze("2005-06-09 11:50", "呼和浩特", 1)
        dayun = result.get("dayun", [])

        # 找当前大运
        current = [d for d in dayun if d.get("is_current")]
        # 如果 is_current 不准,用 2026 - 2005 = 21 岁 (周岁)
        # 梧真盘逆排 22-31 = 己卯,所以 22 岁起算 (虚 23 周岁 21)
        # 覆盖范围: 找包含梧当前岁数的
        if not current:
            current = [d for d in dayun if 21 <= d.get("start_age", 0) <= 21]

        assert current, f"应找到梧当前大运, dayun: {[(d['start_age'], d['ganzhi']) for d in dayun[:5]]}"
        assert current[0]["ganzhi"] == "己卯", \
            f"梧当前大运应为己卯, 实际 {current[0]['ganzhi']}"


class TestDayunDirectionRegression:
    """方向修好后, 这些 case 不能回归"""

    def test_yin_year_male_first_dayun_not_equal_month(self):
        """阴年男第一大运不能等于月柱本身(防 P0 bug 退化)"""
        result = _run_analyze("2005-06-09 11:50", "呼和浩特", 1)
        dayun = result.get("dayun", [])
        month_gz = _extract_gz(result.get("month", ""))  # type: ignore[assignment]
        first_dy_gz = dayun[0]["ganzhi"]

        assert first_dy_gz != month_gz, (
            f"【回归保护】第一大运等于月柱({month_gz})意味着方向未生效"
        )

    def test_yin_year_male_not_3_forward(self):
        """阴年男大运前 3 段不能是月柱 +1 +2 +3(那是顺排, 防回归)"""
        result = _run_analyze("2005-06-09 11:50", "呼和浩特", 1)
        dayun = result.get("dayun", [])
        month_gz = _extract_gz(result.get("month", ""))  # type: ignore[assignment]
        first3 = [d["ganzhi"] for d in dayun[:3]]
        forbidden = [_next_gz(month_gz, 1), _next_gz(month_gz, 2), _next_gz(month_gz, 3)]

        assert first3 != forbidden, (
            f"【回归保护】梧阴年男大运 = {first3}, 不应等于顺排序列 {forbidden}"
        )
