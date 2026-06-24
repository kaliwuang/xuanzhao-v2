#!/usr/bin/env python3
"""
姓名学引擎测试 - 五格剖象法

覆盖五格计算的各类输入组合：
- 单姓单名、单姓双名、复姓双名、复姓单名
- _to_jishu 数理转换边界
- _is_compound_surname 复姓检测
- analyze_name 输入校验
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.xingming_engine import XingMingEngine, COMMON_STROKES, COMPOUND_SURNAMES


class TestXingMingWuge:
    """五格计算核心逻辑测试"""

    def _get_engine(self):
        return XingMingEngine()

    # ── 单姓双名 ──────────────────────────────────────────────────────

    def test_single_surname_double_given(self):
        """张伟明：单姓双名五格计算正确"""
        engine = self._get_engine()
        # 张=11, 伟=6, 明=8
        surname_strokes = [11]
        given_strokes = [6, 8]
        wuge = engine._calc_wuge(surname_strokes, given_strokes, 1, 2, False)

        # 天格 = 11+1 = 12
        assert wuge["天格"]["画数"] == 12, f"天格应为12，实际{wuge['天格']['画数']}"
        # 人格 = 张(11) + 伟(6) = 17
        assert wuge["人格"]["画数"] == 17, f"人格应为17，实际{wuge['人格']['画数']}"
        # 地格 = 6+8 = 14
        assert wuge["地格"]["画数"] == 14, f"地格应为14，实际{wuge['地格']['画数']}"
        # 外格 = 伟末字(8) + 1 = 9
        assert wuge["外格"]["画数"] == 9, f"外格应为9，实际{wuge['外格']['画数']}"
        # 总格 = 11+6+8 = 25
        assert wuge["总格"]["画数"] == 25, f"总格应为25，实际{wuge['总格']['画数']}"

    # ── 单姓单名 ──────────────────────────────────────────────────────

    def test_single_surname_single_given(self):
        """王刚：单姓单名五格计算正确"""
        engine = self._get_engine()
        # 王=4, 刚=10
        surname_strokes = [4]
        given_strokes = [10]
        wuge = engine._calc_wuge(surname_strokes, given_strokes, 1, 1, False)

        # 天格 = 4+1 = 5
        assert wuge["天格"]["画数"] == 5, f"天格应为5，实际{wuge['天格']['画数']}"
        # 人格 = 王(4) + 刚(10) = 14
        assert wuge["人格"]["画数"] == 14, f"人格应为14，实际{wuge['人格']['画数']}"
        # 地格 = 10+1 = 11（单名+1）
        assert wuge["地格"]["画数"] == 11, f"地格应为11，实际{wuge['地格']['画数']}"
        # 外格 = 2（单姓单名固定为2）
        assert wuge["外格"]["画数"] == 2, f"外格应为2，实际{wuge['外格']['画数']}"
        # 总格 = 4+10 = 14
        assert wuge["总格"]["画数"] == 14, f"总格应为14，实际{wuge['总格']['画数']}"

    # ── 复姓双名 ──────────────────────────────────────────────────────

    def test_compound_surname_double_given(self):
        """欧阳明辉：复姓双名五格计算正确"""
        engine = self._get_engine()
        # 欧=15, 阳=17, 明=8, 辉=15
        surname_strokes = [15, 17]
        given_strokes = [8, 15]
        wuge = engine._calc_wuge(surname_strokes, given_strokes, 2, 2, True)

        # 天格 = 15+17 = 32（复姓直接用姓笔画和）
        assert wuge["天格"]["画数"] == 32, f"天格应为32，实际{wuge['天格']['画数']}"
        # 人格 = 阳(17) + 明(8) = 25
        assert wuge["人格"]["画数"] == 25, f"人格应为25，实际{wuge['人格']['画数']}"
        # 地格 = 8+15 = 23
        assert wuge["地格"]["画数"] == 23, f"地格应为23，实际{wuge['地格']['画数']}"
        # 外格 = 欧(15) + 辉(15) + 1 = 31
        assert wuge["外格"]["画数"] == 31, f"外格应为31，实际{wuge['外格']['画数']}"
        # 总格 = 15+17+8+15 = 55
        assert wuge["总格"]["画数"] == 55, f"总格应为55，实际{wuge['总格']['画数']}"

    # ── 复姓单名 ──────────────────────────────────────────────────────

    def test_compound_surname_single_given(self):
        """诸葛亮：复姓单名五格计算正确"""
        engine = self._get_engine()
        # 诸=16, 葛=15, 亮=9
        surname_strokes = [16, 15]
        given_strokes = [9]
        wuge = engine._calc_wuge(surname_strokes, given_strokes, 2, 1, True)

        # 天格 = 16+15 = 31
        assert wuge["天格"]["画数"] == 31, f"天格应为31，实际{wuge['天格']['画数']}"
        # 人格 = 葛(15) + 亮(9) = 24
        assert wuge["人格"]["画数"] == 24, f"人格应为24，实际{wuge['人格']['画数']}"
        # 地格 = 9+1 = 10（单名+1）
        assert wuge["地格"]["画数"] == 10, f"地格应为10，实际{wuge['地格']['画数']}"
        # 外格 = 诸(16) + 1 = 17（复姓单名）
        assert wuge["外格"]["画数"] == 17, f"外格应为17，实际{wuge['外格']['画数']}"
        # 总格 = 16+15+9 = 40
        assert wuge["总格"]["画数"] == 40, f"总格应为40，实际{wuge['总格']['画数']}"


class TestXingMingJishu:
    """81数理转换测试"""

    def _get_engine(self):
        return XingMingEngine()

    def test_to_jishu_normal(self):
        """正常笔画数转换"""
        engine = self._get_engine()
        assert engine._to_jishu(1) == 1
        assert engine._to_jishu(81) == 81
        assert engine._to_jishu(82) == 1  # 82 % 81 = 1
        assert engine._to_jishu(162) == 81  # 162 % 81 = 0 -> 81

    def test_to_jishu_large_number(self):
        """大笔画数转换（200+）"""
        engine = self._get_engine()
        assert engine._to_jishu(200) == 38  # 200 % 81 = 38
        assert engine._to_jishu(243) == 81  # 243 % 81 = 0 -> 81

    def test_to_jishu_zero_returns_one(self):
        """0笔画应回退到1"""
        engine = self._get_engine()
        assert engine._to_jishu(0) == 1

    def test_to_jishu_negative_returns_one(self):
        """负数应回退到1"""
        engine = self._get_engine()
        assert engine._to_jishu(-5) == 1


class TestXingMingCompoundSurname:
    """复姓检测测试"""

    def test_known_compound_surnames(self):
        """常见复姓应被正确识别"""
        engine = XingMingEngine()
        for name in ["欧阳", "司马", "诸葛", "上官", "公孙", "慕容", "令狐"]:
            assert engine._is_compound_surname(name), f"{name}应为复姓"

    def test_single_surnames_not_compound(self):
        """单姓不应被误判为复姓"""
        engine = XingMingEngine()
        for name in ["张", "王", "李", "赵", "陈", "林"]:
            assert not engine._is_compound_surname(name), f"{name}不应为复姓"

    def test_non_surnames_not_compound(self):
        """非姓氏不应被误判为复姓"""
        engine = XingMingEngine()
        for name in ["欧阳锋", "诸葛孔明", ""]:
            assert not engine._is_compound_surname(name), f"{name}不应为复姓"


class TestXingMingSancai:
    """三才五行配置测试"""

    def _get_engine(self):
        return XingMingEngine()

    def test_known_sancai_config(self):
        """已知三才配置应返回查表结果"""
        engine = self._get_engine()
        # 天格11(木), 人格22(木), 地格13(火) -> 木木火
        result = engine._calc_sancai(tiange=11, renge=22, dige=13)
        assert "配置" in result
        assert "吉凶" in result
        # 木木火 在三才表中是 (1,2,1) 大吉
        assert result["吉凶"] in ("大吉", "吉", "中吉"), \
            f"木木火配置应为吉，实际: {result['吉凶']}"

    def test_sancai_wuxing_evaluation_favorable(self):
        """上生下的三才配置应为吉"""
        engine = self._get_engine()
        # 木→火→土: 木生火(上生下)=吉, 火生土(上生下)=吉
        result = engine._evaluate_sancai_wuxing("木", "火", "土")
        assert result[0] in ("大吉", "吉"), f"木火土应为吉，实际: {result[0]}"

    def test_sancai_wuxing_ke_relationship(self):
        """相克的三才配置"""
        engine = self._get_engine()
        # 金→木: 上克下(凶), 木→水: 下生上(泄气=不利)
        result = engine._evaluate_sancai_wuxing("金", "木", "水")
        assert result[0] in ("凶", "半凶", "半吉"), \
            f"金木水应为凶/半凶，实际: {result[0]}"


class TestXingMingAnalyzeName:
    """analyze_name 集成测试"""

    def _get_engine(self):
        return XingMingEngine()

    def test_empty_surname_returns_error(self):
        """空姓应返回错误"""
        engine = self._get_engine()
        result = engine.analyze_name("", "伟明", "男")
        assert "error" in result
        assert "空" in result["error"]

    def test_empty_given_returns_error(self):
        """空名应返回错误"""
        engine = self._get_engine()
        result = engine.analyze_name("张", "", "男")
        assert "error" in result

    def test_non_chinese_returns_error(self):
        """纯英文姓名应返回错误"""
        engine = self._get_engine()
        result = engine.analyze_name("Smith", "John", "男")
        assert "error" in result
        assert "汉字" in result["error"]

    def test_valid_name_returns_wuge(self):
        """正常姓名应返回五格数据"""
        engine = self._get_engine()
        result = engine.analyze_name("张", "伟明", "男")
        assert "error" not in result, f"不应有错误: {result.get('error')}"
        assert "wuge" in result
        for key in ["天格", "人格", "地格", "外格", "总格"]:
            assert key in result["wuge"], f"缺少{key}"
            assert "画数" in result["wuge"][key]
            assert "数理" in result["wuge"][key]
            assert "吉凶" in result["wuge"][key]

    def test_valid_name_returns_score(self):
        """正常姓名应返回评分"""
        engine = self._get_engine()
        result = engine.analyze_name("张", "伟明", "男")
        assert "score" in result
        assert 0 <= result["score"] <= 100

    def test_valid_name_returns_analysis(self):
        """正常姓名应返回分析文本"""
        engine = self._get_engine()
        result = engine.analyze_name("张", "伟明", "男")
        assert "analysis" in result
        assert "张伟明" in result["analysis"]

    def test_score_range_consistency(self):
        """多个姓名的评分应一致在0-100之间"""
        engine = self._get_engine()
        names = [("张", "伟明"), ("李", "静"), ("欧阳", "明辉"),
                 ("王", "磊"), ("赵", "丽")]
        for surname, given in names:
            result = engine.analyze_name(surname, given, "男")
            assert 0 <= result["score"] <= 100, \
                f"{surname}{given}评分{result['score']}超出范围"


class TestXingMingGetStroke:
    """笔画查询测试"""

    def test_common_strokes_lookup(self):
        """常用字应从查找表返回正确笔画"""
        engine = XingMingEngine()
        assert engine.get_stroke("张") == COMMON_STROKES["张"]
        assert engine.get_stroke("伟") == COMMON_STROKES["伟"]
        assert engine.get_stroke("明") == COMMON_STROKES["明"]

    def test_stroke_positive(self):
        """所有笔画数应为正整数"""
        engine = XingMingEngine()
        test_chars = ["张", "伟", "明", "王", "李", "赵", "陈", "林"]
        for char in test_chars:
            strokes = engine.get_stroke(char)
            assert strokes > 0, f"{char}笔画应为正数，实际{strokes}"
            assert isinstance(strokes, int), f"{char}笔画应为整数"

    def test_estimation_fallback(self):
        """不在查找表中的字应有估算回退"""
        engine = XingMingEngine()
        char = "龘"  # 三个龙，不在COMMON_STROKES中
        strokes = engine.get_stroke(char)
        assert strokes > 0, f"估算笔画应为正数，实际{strokes}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
