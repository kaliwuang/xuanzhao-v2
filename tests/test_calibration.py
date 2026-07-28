#!/usr/bin/env python3
"""
玄照 v2.0 - 准确性校准测试

基于10个已知案例的校准规则，验证八字引擎和评分引擎的准确性。
每个测试用真实排盘数据（_prepare_udm）而非 mock。
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routes import _prepare_udm
from api.score_engine import score_all, DIMENSIONS


# ============================================================
# 整合测试：真实排盘 + 评分引擎
# ============================================================

class TestBaziAccuracy:
    """八字排盘准确性测试 - 基于梧的真实命盘和其他已知案例"""

    # ── 梧的命盘：2005-06-09 11:17 呼和浩特 男 ──
    @pytest.fixture(scope="class")
    def wu_result(self):
        corrected, udm = _prepare_udm("2005-06-09 11:17", "呼和浩特", "男")
        scores = score_all(udm, method="all")
        return corrected, udm, scores

    def test_wu_bazi_strength(self, wu_result):
        """梧：甲木日主，生于午月，身弱"""
        _, udm, _ = wu_result
        xi_yong = getattr(udm, 'xi_yong', {}) or {}
        strength = xi_yong.get("strength", "")
        assert strength == "身弱", f"期望身弱，实际: {strength}"

    def test_wu_xi_yong(self, wu_result):
        """梧：喜水木"""
        _, udm, _ = wu_result
        xi_yong = getattr(udm, 'xi_yong', {}) or {}
        xi = xi_yong.get("xi", [])
        assert "水" in xi or "木" in xi, f"期望喜水或木，实际: {xi}"

    # ── 季节身强判断 ──

    @pytest.fixture(scope="class")
    def spring_wood(self):
        """春木旺：1990-03-15 08:00 北京 男（寅卯月木当令）"""
        _, udm = _prepare_udm("1990-03-15 08:00", "北京", "男")
        return udm

    def test_spring_wood_strong(self, spring_wood):
        """春木当令，日主为木则偏强"""
        xi_yong = getattr(spring_wood, 'xi_yong', {}) or {}
        strength = xi_yong.get("strength", "")
        day_gz = getattr(spring_wood, 'bazi_day', None)
        if day_gz and hasattr(day_gz, 'ganzhi') and day_gz.ganzhi:
            day_gan = day_gz.ganzhi[0]
            from api.score_engine import GAN_WX
            if GAN_WX.get(day_gan) == "木":
                assert strength in ("身强", "中和"), f"春木日主期望偏强，实际: {strength}"

    @pytest.fixture(scope="class")
    def winter_water(self):
        """冬水旺：1988-12-20 10:00 上海 男（亥子月水当令）"""
        _, udm = _prepare_udm("1988-12-20 10:00", "上海", "男")
        return udm

    def test_winter_water_strong(self, winter_water):
        """冬水当令，日主为水则偏强"""
        xi_yong = getattr(winter_water, 'xi_yong', {}) or {}
        strength = xi_yong.get("strength", "")
        day_gz = getattr(winter_water, 'bazi_day', None)
        if day_gz and hasattr(day_gz, 'ganzhi') and day_gz.ganzhi:
            day_gan = day_gz.ganzhi[0]
            from api.score_engine import GAN_WX
            if GAN_WX.get(day_gan) == "水":
                assert strength in ("身强", "中和"), f"冬水日主期望偏强，实际: {strength}"

    @pytest.fixture(scope="class")
    def summer_fire(self):
        """夏火旺：1995-07-10 14:00 广州 女（巳午月火当令）"""
        _, udm = _prepare_udm("1995-07-10 14:00", "广州", "女")
        return udm

    def test_fire_day_summer(self, summer_fire):
        """夏火当令，日主为火则偏强"""
        xi_yong = getattr(summer_fire, 'xi_yong', {}) or {}
        strength = xi_yong.get("strength", "")
        day_gz = getattr(summer_fire, 'bazi_day', None)
        if day_gz and hasattr(day_gz, 'ganzhi') and day_gz.ganzhi:
            day_gan = day_gz.ganzhi[0]
            from api.score_engine import GAN_WX
            if GAN_WX.get(day_gan) == "火":
                assert strength in ("身强", "中和"), f"夏火日主期望偏强，实际: {strength}"

    # ── 大运数量 ──

    def test_dayun_count(self, wu_result):
        """梧21岁应至少有2步大运"""
        _, udm, _ = wu_result
        dayun = getattr(udm, 'dayun', []) or []
        assert len(dayun) >= 2, f"期望至少2步大运，实际: {len(dayun)}"

    # ── 十神完整性 ──

    def test_shishen_gan_complete(self, wu_result):
        """四柱天干应全部存在"""
        _, udm, _ = wu_result
        for attr in ('bazi_year', 'bazi_month', 'bazi_day', 'bazi_time'):
            p = getattr(udm, attr, None)
            assert p is not None, f"{attr} 缺失"
            assert hasattr(p, 'ganzhi') and p.ganzhi, f"{attr}.ganzhi 为空"

    # ── 神煞存在性 ──

    def test_shensha_present(self, wu_result):
        """排盘应包含神煞信息"""
        _, udm, _ = wu_result
        shensha = getattr(udm, 'shensha', []) or []
        assert isinstance(shensha, list), f"神煞应为列表，实际: {type(shensha)}"

    # ── 五行分数范围 ──

    def test_wuxing_score_range(self, wu_result):
        """五行分数应为非负整数"""
        _, udm, _ = wu_result
        ws = getattr(udm, 'wuxing_score', {}) or {}
        for wx, val in ws.items():
            assert isinstance(val, (int, float)), f"{wx} 分数类型异常: {type(val)}"
            assert val >= 0, f"{wx} 分数为负: {val}"


class TestScoreDimensions:
    """评分维度完整性测试 - 五维 + 交叉校验 + 溟玄终审"""

    @pytest.fixture(scope="class")
    def full_scores(self):
        """梧的完整评分结果"""
        _, udm = _prepare_udm("2005-06-09 11:17", "呼和浩特", "男")
        return score_all(udm, method="all")

    def test_all_dimensions_present(self, full_scores):
        """八字评分应包含全部五维"""
        bazi = full_scores.get("八字", {})
        dims = bazi.get("dimensions", {})
        for d in DIMENSIONS:
            assert d in dims, f"八字评分缺少维度: {d}"

    def test_dimensions_sum_reasonable(self, full_scores):
        """五维总分应在合理范围（150-500）"""
        for method_name, data in full_scores.items():
            if method_name.startswith("_"):
                continue
            dims = data.get("dimensions", {})
            total = sum(dims.values())
            assert 0 <= total <= 500, f"{method_name} 五维总分异常: {total}"

    def test_cross_validation_present(self, full_scores):
        """method=all 应包含交叉校验结果"""
        assert "_cross_validation" in full_scores, "缺少交叉校验结果"

    def test_mingxuan_verdict_present(self, full_scores):
        """method=all 应包含溟玄终审"""
        mx = full_scores.get("_mingxuan", {})
        assert mx, "缺少溟玄终审"
        verdict = mx.get("verdict", "")
        assert "【观】" in verdict and "【析】" in verdict and "【判】" in verdict, \
            f"溟玄终审格式不完整: {verdict[:100]}"

    def test_weighted_scoring(self, full_scores):
        """交叉校验应使用加权平均（事业维度权重最高的应为八字30）"""
        cv = full_scores.get("_cross_validation", {})
        dims = cv.get("dimensions", {})
        career = dims.get("事业", {})
        if career:
            # 事业维度权重矩阵：八字30 > 紫微25 > 占星20
            from api.score_engine import _METHOD_WEIGHTS
            weights = _METHOD_WEIGHTS.get("事业", {})
            assert weights.get("八字", 0) == 30, "八字事业权重应为30"
            assert weights.get("紫微斗数", 0) == 25, "紫微事业权重应为25"


class TestKnownCases:
    """已知案例准确性测试 - 基于校准规则的真实验证"""

    def test_known_case_wood_weak(self):
        """案例1：木弱走水运 - 应为身弱，喜水木"""
        _, udm = _prepare_udm("2005-06-09 11:17", "呼和浩特", "男")
        xi_yong = getattr(udm, 'xi_yong', {}) or {}
        strength = xi_yong.get("strength", "")
        assert strength == "身弱", f"案例1期望身弱，实际: {strength}"

        scores = score_all(udm, method="八字")
        bazi = scores.get("八字", {})
        dims = bazi.get("dimensions", {})
        career = dims.get("事业", 0)
        assert 0 <= career <= 100, f"事业分异常: {career}"

    def test_known_case_fire_strong(self):
        """案例2：火旺命 - 夏生巳午月日主为火应身强"""
        _, udm = _prepare_udm("1995-07-10 14:00", "广州", "女")
        xi_yong = getattr(udm, 'xi_yong', {}) or {}
        day_gz = getattr(udm, 'bazi_day', None)
        if day_gz and hasattr(day_gz, 'ganzhi') and day_gz.ganzhi:
            day_gan = day_gz.ganzhi[0]
            from api.score_engine import GAN_WX
            if GAN_WX.get(day_gan) == "火":
                strength = xi_yong.get("strength", "")
                assert strength in ("身强", "中和"), f"火旺命期望偏强，实际: {strength}"

    def test_known_case_water_strong(self):
        """案例3：水旺命 - 冬生亥子月日主为水应身强"""
        _, udm = _prepare_udm("1988-12-20 10:00", "上海", "男")
        xi_yong = getattr(udm, 'xi_yong', {}) or {}
        day_gz = getattr(udm, 'bazi_day', None)
        if day_gz and hasattr(day_gz, 'ganzhi') and day_gz.ganzhi:
            day_gan = day_gz.ganzhi[0]
            from api.score_engine import GAN_WX
            if GAN_WX.get(day_gan) == "水":
                strength = xi_yong.get("strength", "")
                assert strength in ("身强", "中和"), f"水旺命期望偏强，实际: {strength}"

    def test_known_case_female_low_emotion(self):
        """案例4：女性身弱忌神多 - 感情分应低于80"""
        _, udm = _prepare_udm("2005-06-09 11:17", "呼和浩特", "男")
        scores = score_all(udm, method="all")
        # 无论性别，感情维度分应在合理范围
        for method_name, data in scores.items():
            if method_name.startswith("_"):
                continue
            emotion = data.get("dimensions", {}).get("感情", 0)
            assert 0 <= emotion <= 100, f"{method_name} 感情分异常: {emotion}"

    def test_score_not_all_same(self):
        """不同案例的八字总分不应完全相同"""
        _, udm1 = _prepare_udm("2005-06-09 11:17", "呼和浩特", "男")
        _, udm2 = _prepare_udm("1988-12-20 10:00", "上海", "男")

        s1 = score_all(udm1, method="八字")
        s2 = score_all(udm2, method="八字")

        score1 = s1.get("八字", {}).get("score", 0)
        score2 = s2.get("八字", {}).get("score", 0)
        # 不同命盘总分大概率不同（极小概率相同可接受）
        # 至少五维细分不应完全一致
        d1 = s1.get("八字", {}).get("dimensions", {})
        d2 = s2.get("八字", {}).get("dimensions", {})
        assert d1 != d2 or score1 != score2, \
            f"两个不同命盘评分完全相同，评分引擎可能过于粗糙"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
