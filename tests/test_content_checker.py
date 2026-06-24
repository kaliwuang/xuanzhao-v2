#!/usr/bin/env python3
"""
玄照 v2.0 - 内容质量检查引擎测试

覆盖 ContentChecker 的所有检查维度：
1. 禁用词检测（单个/多个/重复出现）
2. 超长句检测（中文标点分句）
3. 比喻数量检查（去重逻辑）
4. AI列举式模板结构检测
5. 段落长度检查
6. 七段结构完整性检查
7. 评分计算逻辑（扣分/底线/通过判定）
8. quick_check 快速入口
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.content_checker import ContentChecker, check_text


@pytest.fixture
def checker():
    return ContentChecker()


# ============================================================
# 禁用词检测
# ============================================================

class TestBannedWords:

    def test_no_banned_words(self, checker):
        """无禁用词时应返回空列表"""
        text = "这段文字写得很好，没有任何模板词。"
        result = checker._check_banned_words(text)
        assert result == []

    def test_single_banned_word(self, checker):
        """单个禁用词应被检出"""
        text = "首先我们要理解命理的本质。"
        result = checker._check_banned_words(text)
        assert "首先" in result

    def test_multiple_banned_words(self, checker):
        """多个不同禁用词都应被检出"""
        text = "首先看日主，其次看喜用，因此整体格局不错。"
        result = checker._check_banned_words(text)
        assert "首先" in result
        assert "其次" in result
        assert "因此" in result

    def test_repeated_banned_word(self, checker):
        """同一禁用词出现多次应重复计入"""
        text = "首先看天干，其次看地支，首先还要看纳音。"
        result = checker._check_banned_words(text)
        assert result.count("首先") == 2

    def test_all_banned_words_list(self, checker):
        """BANNED_WORDS 列表应非空且包含预期关键词"""
        assert len(ContentChecker.BANNED_WORDS) > 10
        assert "首先" in ContentChecker.BANNED_WORDS
        assert "综上所述" in ContentChecker.BANNED_WORDS
        assert "众所周知" in ContentChecker.BANNED_WORDS


# ============================================================
# 超长句检测
# ============================================================

class TestSentenceLength:

    def test_short_sentences_pass(self, checker):
        """短句不应被检出"""
        text = "日主为甲。喜用神是水。命局不错。"
        result = checker._check_sentence_length(text, max_len=25)
        assert len(result) == 0

    def test_long_sentence_detected(self, checker):
        """超过25字的句子应被检出"""
        text = "这是一句非常非常非常非常非常非常非常非常非常非常非常非常长的句子，超过了限制。"
        result = checker._check_sentence_length(text, max_len=25)
        assert len(result) > 0

    def test_chinese_punctuation_splits(self, checker):
        """中文句号、叹号、问号都应作为分句依据"""
        text = "短句。这是一个超级超级超级超级超级超级超级超级超级超级超级超级长句！短句？"
        result = checker._check_sentence_length(text, max_len=25)
        assert len(result) == 1  # 只有中间那句超长

    def test_semicolon_splits(self, checker):
        """分号也应作为分句依据"""
        text = "前半句；这是超过二十五字的非常非常非常非常非常非常非常非常长的后半句。"
        result = checker._check_sentence_length(text, max_len=25)
        assert len(result) == 1

    def test_empty_text(self, checker):
        """空文本不应检出超长句"""
        result = checker._check_sentence_length("", max_len=25)
        assert len(result) == 0


# ============================================================
# 比喻检测
# ============================================================

class TestMetaphors:

    def test_no_metaphors(self, checker):
        """无比喻词时应返回0"""
        text = "日主甲木，性格刚强。"
        assert checker._check_metaphors(text) == 0

    def test_single_metaphor(self, checker):
        """一个比喻词应返回1"""
        text = "甲木如同参天大树，根基深厚。"
        assert checker._check_metaphors(text) == 1

    def test_multiple_metaphors(self, checker):
        """多个不同比喻词应各自计数"""
        text = "甲木如同参天大树，仿佛烈日骄阳，好比一把利剑。"
        assert checker._check_metaphors(text) == 3

    def test_dedup_repeated_metaphor(self, checker):
        """同一比喻词重复出现只计一次"""
        text = "如同春风，如同秋雨，如同烈火。"
        assert checker._check_metaphors(text) == 1

    def test_metaphor_patterns_non_empty(self, checker):
        """METAPHOR_PATTERNS 应包含预期关键词"""
        assert "如同" in ContentChecker.METAPHOR_PATTERNS
        assert "仿佛" in ContentChecker.METAPHOR_PATTERNS
        assert len(ContentChecker.METAPHOR_PATTERNS) >= 10


# ============================================================
# AI列举式模板检测
# ============================================================

class TestListLikeStructures:

    def test_no_list_patterns(self, checker):
        """无列举结构时应返回0"""
        text = "这段文字流畅自然，没有模板化结构。"
        assert checker._check_list_like_structures(text) == 0

    def test_numbered_list_detected(self, checker):
        """第一，第二，第三式列举应被检出"""
        text = "第一，看日主强弱；第二，看喜用神；第三，看大运流年。"
        result = checker._check_list_like_structures(text)
        assert result >= 3

    def test_one_side_other_side(self, checker):
        """一方面另一方面结构应被检出"""
        text = "一方面日主偏弱，另一方面喜用神得力。"
        result = checker._check_list_like_structures(text)
        assert result >= 1

    def test_circled_numbers_detected(self, checker):
        """圈数字编号应被检出"""
        text = "①日主强弱 ②喜用神 ③大运"
        result = checker._check_list_like_structures(text)
        assert result >= 3


# ============================================================
# 段落长度检查
# ============================================================

class TestParagraphLength:

    def test_short_paragraphs_pass(self, checker):
        """短段落不应被检出"""
        text = "第一段只有一句话。\n\n第二段也只有一句话。"
        result = checker._check_paragraph_length(text, max_sentences=3)
        assert len(result) == 0

    def test_long_paragraph_detected(self, checker):
        """超过3句的段落应被检出"""
        text = "第一句。第二句。第三句。第四句。第五句。"
        result = checker._check_paragraph_length(text, max_sentences=3)
        assert len(result) == 1

    def test_double_newline_splits(self, checker):
        """双换行符作为段落分隔"""
        text = "短段落。\n\n第一句。第二句。第三句。第四句。"
        result = checker._check_paragraph_length(text, max_sentences=3)
        assert len(result) == 1  # 只有第二段超长


# ============================================================
# 七段结构检查
# ============================================================

class TestStructure:

    def test_no_structure(self, checker):
        """无结构关键词时应返回0"""
        text = "今天天气不错。"
        assert checker._check_structure(text) == 0

    def test_full_structure(self, checker):
        """包含全部七段关键词时应返回7"""
        text = (
            "真实场景中，一位命主前来咨询。"
            "概念解析显示日主为甲木。"
            "四层机制分析了命局层次。"
            "操作方法是先排盘再分析。"
            "错误误区在于只看天干不看地支。"
            "应用案例表明此法有效。"
            "顿悟时刻，命主恍然大悟。"
        )
        assert checker._check_structure(text) == 7

    def test_partial_structure(self, checker):
        """部分结构应返回对应数量"""
        text = "开场引子很有趣。概念解析清楚。总结归真。"
        result = checker._check_structure(text)
        assert 1 <= result <= 7


# ============================================================
# 评分与综合判定
# ============================================================

class TestCheckResult:

    def test_perfect_text_scores_high(self, checker):
        """无禁用词、有比喻、有结构的文本应得高分"""
        text = (
            "真实场景中一位命主前来。概念解析日主甲木。"
            "四层机制层次分明。操作方法清晰可行。"
            "错误误区需警惕。应用案例有实证。顿悟归真。"
            "如同参天大树，仿佛烈日骄阳，好比一把利剑，恰似春风拂面。"
        )
        result = checker.check(text)
        assert result["score"] >= 90
        assert result["passed"] is True

    def test_banned_words_reduce_score(self, checker):
        """禁用词应扣分"""
        text = "首先看日主。其次看喜用。"
        result = checker.check(text)
        assert result["score"] < 100
        assert any(i["type"] == "禁用词" for i in result["issues"])

    def test_score_never_below_zero(self, checker):
        """分数不应低于0"""
        text = "首先" * 50
        result = checker.check(text)
        assert result["score"] >= 0

    def test_high_severity_fails(self, checker):
        """有高严重度问题时应不通过"""
        text = "首先看日主。"
        result = checker.check(text)
        has_high = any(i["severity"] == "高" for i in result["issues"])
        if has_high:
            assert result["passed"] is False

    def test_result_has_required_keys(self, checker):
        """结果应包含 passed, score, issues 三个键"""
        result = checker.check("测试文本。")
        assert "passed" in result
        assert "score" in result
        assert "issues" in result

    def test_issues_have_type_and_severity(self, checker):
        """每个 issue 应包含 type 和 severity"""
        text = "首先看日主。这是一个超级超级超级超级超级超级超级超级超级超级超级超级长的句子。"
        result = checker.check(text)
        for issue in result["issues"]:
            assert "type" in issue
            assert "severity" in issue


# ============================================================
# quick_check 快速入口
# ============================================================

class TestQuickCheck:

    def test_quick_check_returns_tuple(self, checker):
        """quick_check 应返回 (bool, str) 元组"""
        passed, msg = checker.quick_check("测试文本。")
        assert isinstance(passed, bool)
        assert isinstance(msg, str)

    def test_quick_check_pass(self, checker):
        """优质文本应通过 quick_check"""
        text = (
            "真实场景引子。概念解析。四层机制。操作方法。错误误区。应用案例。顿悟归真。"
            "如同大树，仿佛骄阳，好比利剑，恰似春风。"
        )
        passed, msg = checker.quick_check(text)
        assert passed is True
        assert "通过" in msg

    def test_quick_check_fail(self, checker):
        """有问题的文本应不通过 quick_check"""
        text = "首先" * 20 + "其次" * 20
        passed, msg = checker.quick_check(text)
        assert passed is False
        assert "未通过" in msg


# ============================================================
# 便捷函数 check_text
# ============================================================

class TestCheckTextFunction:

    def test_check_text_returns_dict(self):
        """check_text 便捷函数应返回字典"""
        result = check_text("测试文本。")
        assert isinstance(result, dict)
        assert "passed" in result
        assert "score" in result

    def test_check_text_consistent_with_class(self):
        """check_text 结果应与直接实例化一致"""
        text = "首先看日主。甲木如同大树。"
        result_func = check_text(text)
        result_class = ContentChecker().check(text)
        assert result_func["score"] == result_class["score"]
        assert result_func["passed"] == result_class["passed"]
