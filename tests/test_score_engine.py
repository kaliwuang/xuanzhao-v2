#!/usr/bin/env python3
"""
玄照 v2.0 - 评分引擎测试

覆盖所有7个术法评分函数的主路径和边界条件。
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.score_engine import score_all, _score_bazi, _score_ziwei, _score_liuyao, \
    _score_qimen, _score_liuren, _score_taiyi, _score_astro


# ============================================================
# 辅助 Mock 构造器
# ============================================================

def _make_pillar(ganzhi):
    """创建一个 mock Pillar 对象"""
    p = MagicMock()
    p.ganzhi = ganzhi
    return p


def _make_bazi_udm(strength="身强", xi=None, ji=None, wuxing_score=None,
                   shensha=None, zhi_relations=None, dayun=None):
    """构造八字排盘数据完整的 mock UDM"""
    udm = MagicMock()
    udm.bazi_year = _make_pillar("乙酉")
    udm.bazi_month = _make_pillar("壬午")
    udm.bazi_day = _make_pillar("甲子")
    udm.bazi_time = _make_pillar("庚午")
    udm.xi_yong = {
        "strength": strength,
        "xi": xi or ["水", "木"],
        "ji": ji or ["火", "土"],
        "reason": "测试"
    }
    udm.wuxing_score = wuxing_score or {"木": 2, "火": 3, "土": 1, "金": 2, "水": 2}
    udm.shensha = shensha or ["天乙（日柱）", "文昌（时柱）"]
    udm.zhi_relations = zhi_relations or ["子午冲"]
    udm.dayun = dayun or [
        {"ganzhi": "辛巳", "start_age": 5, "end_age": 14},
        {"ganzhi": "庚辰", "start_age": 15, "end_age": 24},
    ]
    return udm


def _make_ziwei_udm(soul_star="紫微", ming_gong="寅", palaces=None,
                    sihua=None, sha_stars=None):
    """构造紫微排盘数据完整的 mock UDM"""
    udm = MagicMock()
    udm.ziwei_chart = {
        "ming_gong": ming_gong,
        "soul_star": soul_star,
        "palaces": palaces or [
            {"name": "命宫", "major_stars": [{"name": soul_star}], "minor_stars": []},
            {"name": "夫妻", "major_stars": [{"name": "天同"}], "minor_stars": []},
        ],
        "sihua": sihua or {"化禄": "廉贞", "化权": "破军", "化科": "武曲", "化忌": "太阳"},
    }
    return udm


def _make_liuyao_udm(ge_ju=None, shi=1, ying=4, dong_yao=None,
                     ben_gua="乾为天", bian_gua="天风姤"):
    """构造六爻排盘数据完整的 mock UDM"""
    udm = MagicMock()
    udm.liuyao_chart = {
        "ben_gua": {"name": ben_gua, "mark": "111111"},
        "bian_gua": {"name": bian_gua, "mark": "111110"},
        "dong_yao": dong_yao or [1],
        "shi": shi,
        "ying": ying,
        "ge_ju": ge_ju or ["世应合"],
        "wuxing_analysis": {"yong_shen": "父母爻"},
    }
    return udm


def _make_qimen_udm(ji_ge=None, xiong_ge=None, zhi_fu_gong="坎一宫",
                    ba_men=None, ju_name="阳遁3局"):
    """构造奇门遁甲排盘数据完整的 mock UDM"""
    udm = MagicMock()
    udm.qimen_chart = {
        "ju_name": ju_name,
        "zhi_fu_gong": zhi_fu_gong,
        "ba_men": ba_men or {"1": "开门", "2": "生门", "3": "休门"},
        "ge_ju_analysis": {
            "ji_ge": ji_ge or [{"name": "天遁", "gong": 3, "desc": "吉"}],
            "xiong_ge": xiong_ge or [],
        },
        "palaces": [],
    }
    return udm


def _make_liuren_udm(ge_ju="天心课", yong_shen_status="旺"):
    """构造大六壬排盘数据完整的 mock UDM"""
    udm = MagicMock()
    udm.liuren_chart = {
        "ge_ju": ge_ju,
        "yong_shen": {"status": yong_shen_status, "旺衰": yong_shen_status},
        "si_ke": ([], [], [], []),
        "san_chuan": ([], [], []),
    }
    return udm


def _make_taiyi_udm(zhu_suan=7, ke_suan=3, ding_suan=5, taiyi_gong="坎一宫"):
    """构造太乙神数排盘数据完整的 mock UDM"""
    udm = MagicMock()
    udm.taiyi_chart = {
        "zhu_suan": [zhu_suan],
        "ke_suan": [ke_suan],
        "ding_suan": [ding_suan],
        "taiyi_gong": taiyi_gong,
        "ju_name": "太乙第一局",
    }
    return udm


def _make_astro_udm(sun_sign="双子", moon_sign="天蝎", asc_sign="狮子",
                    aspects=None, planetary_details=None):
    """构造占星排盘数据完整的 mock UDM"""
    udm = MagicMock()
    udm.astro_chart = {
        "sun_sign": sun_sign,
        "moon_sign": moon_sign,
        "ascendant_sign": asc_sign,
        "ascendant": asc_sign,
        "mc_sign": "白羊",
        "mc": "白羊",
        "sun_element": "风",
        "planets": {},
        "aspects": aspects or [
            {"planet1": "太阳", "planet2": "月亮", "aspect": "三合"},
            {"planet1": "金星", "planet2": "火星", "aspect": "合相"},
        ],
        "planetary_details": planetary_details or {},
    }
    return udm


# ============================================================
# 八字评分测试
# ============================================================

class TestScoreBazi:

    def test_bazi_no_data_returns_zero(self):
        """八字数据缺失时应返回0分"""
        udm = MagicMock()
        udm.bazi_year = None
        score, analysis, strengths, weaknesses = _score_bazi(udm)
        assert score == 0
        assert "不完整" in analysis

    def test_bazi_shenqiang_with_xi(self):
        """身强+喜用神得力应得高分"""
        udm = _make_bazi_udm(strength="身强", xi=["水", "木"])
        score, analysis, strengths, weaknesses = _score_bazi(udm)
        assert 50 <= score <= 100, f"身强+喜用神应得较高分，实际: {score}"
        assert len(strengths) > 0

    def test_bazi_shenruo_with_xi(self):
        """身弱+喜用神出现应有加分"""
        udm = _make_bazi_udm(strength="身弱", xi=["水", "木"])
        score, analysis, strengths, weaknesses = _score_bazi(udm)
        assert score > 0

    def test_bazi_zhonghe(self):
        """中和八字应有基础分"""
        udm = _make_bazi_udm(strength="中和")
        score, analysis, strengths, weaknesses = _score_bazi(udm)
        assert score >= 25  # 中和基础分

    def test_bazi_score_in_range(self):
        """八字评分应在0-100之间"""
        udm = _make_bazi_udm()
        score, _, _, _ = _score_bazi(udm)
        assert 0 <= score <= 100

    def test_bazi_balanced_wuxing(self):
        """五行均匀应有五行加分"""
        udm = _make_bazi_udm(
            wuxing_score={"木": 2, "火": 2, "土": 2, "金": 2, "水": 2}
        )
        score, _, strengths, _ = _score_bazi(udm)
        assert any("均匀" in s or "平衡" in s for s in strengths)

    def test_bazi_unbalanced_wuxing(self):
        """五行严重偏枯应有弱点提示"""
        udm = _make_bazi_udm(
            wuxing_score={"木": 0, "火": 0, "土": 0, "金": 10, "水": 0}
        )
        score, _, _, weaknesses = _score_bazi(udm)
        assert len(weaknesses) > 0

    def test_bazi_many_jishen(self):
        """多吉神应加分"""
        udm = _make_bazi_udm(shensha=["天乙（日柱）", "文昌（时柱）", "禄（月柱）", "天德（年柱）"])
        score, _, strengths, _ = _score_bazi(udm)
        assert any("吉神" in s for s in strengths)

    def test_bazi_many_xiongsha(self):
        """多凶煞应扣分"""
        udm = _make_bazi_udm(shensha=["羊刃（日柱）", "七杀（月柱）", "劫煞（年柱）"])
        score, _, _, weaknesses = _score_bazi(udm)
        assert any("凶煞" in w for w in weaknesses)

    def test_bazi_no_chong(self):
        """无刑冲应加分"""
        udm = _make_bazi_udm()
        # 直接覆盖 zhi_relations 为空列表（绕过 mock helper 的 or 默认值）
        udm.zhi_relations = []
        score, _, strengths, _ = _score_bazi(udm)
        assert any("安稳" in s or "刑冲" in s for s in strengths)

    def test_bazi_analysis_contains_key_info(self):
        """分析文本应包含日主信息"""
        udm = _make_bazi_udm(strength="身强")
        _, analysis, _, _ = _score_bazi(udm)
        assert "身强" in analysis
        assert "喜用" in analysis


# ============================================================
# 紫微斗数评分测试
# ============================================================

class TestScoreZiwei:

    def test_ziwei_no_data_returns_zero(self):
        """紫微数据缺失时应返回0分"""
        udm = MagicMock()
        udm.ziwei_chart = None
        score, analysis, strengths, weaknesses = _score_ziwei(udm)
        assert score == 0
        assert "不完整" in analysis

    def test_ziwei_ji_main_star(self):
        """命宫坐吉星应得高分"""
        udm = _make_ziwei_udm(soul_star="紫微")
        score, _, strengths, _ = _score_ziwei(udm)
        assert score >= 25
        assert any("吉星" in s for s in strengths)

    def test_ziwei_sha_main_star(self):
        """命宫煞星应得较低分"""
        udm = _make_ziwei_udm(
            soul_star="七杀",
            palaces=[{"name": "命宫", "major_stars": [{"name": "七杀"}], "minor_stars": []}]
        )
        score, _, _, weaknesses = _score_ziwei(udm)
        assert score >= 0
        assert any("煞星" in w for w in weaknesses)

    def test_ziwei_score_in_range(self):
        """紫微评分应在0-100之间"""
        udm = _make_ziwei_udm()
        score, _, _, _ = _score_ziwei(udm)
        assert 0 <= score <= 100

    def test_ziwei_good_sihua(self):
        """四化走得好应加分"""
        udm = _make_ziwei_udm(
            sihua={"化禄": "廉贞", "化权": "破军", "化科": "武曲"}
        )
        score, _, strengths, _ = _score_ziwei(udm)
        assert any("四化" in s or "禄" in s for s in strengths)

    def test_ziwei_ji_in_sihua(self):
        """化忌应扣分"""
        udm = _make_ziwei_udm(
            sihua={"化忌": "太阳"}
        )
        score, _, _, weaknesses = _score_ziwei(udm)
        assert any("化忌" in w for w in weaknesses)

    def test_ziwei_no_sha_in_ming(self):
        """命宫无煞星应加分"""
        udm = _make_ziwei_udm()
        score, _, strengths, _ = _score_ziwei(udm)
        # 紫微是吉星，不应有煞星
        assert score > 0

    def test_ziwei_analysis_mentions_star(self):
        """分析应提及命宫主星"""
        udm = _make_ziwei_udm(soul_star="紫微")
        _, analysis, _, _ = _score_ziwei(udm)
        assert "紫微" in analysis


# ============================================================
# 六爻评分测试
# ============================================================

class TestScoreLiuyao:

    def test_liuyao_no_data_returns_zero(self):
        """六爻数据缺失时应返回0分"""
        udm = MagicMock()
        udm.liuyao_chart = None
        score, analysis, strengths, weaknesses = _score_liuyao(udm)
        assert score == 0
        assert "不完整" in analysis

    def test_liuyao_ji_ge(self):
        """吉格应得高分"""
        udm = _make_liuyao_udm(ge_ju=["六合", "世应合"])
        score, _, strengths, _ = _score_liuyao(udm)
        assert score >= 25

    def test_liuyao_xiong_ge(self):
        """凶格应得低分"""
        udm = _make_liuyao_udm(ge_ju=["六冲", "反吟"])
        score, _, _, weaknesses = _score_liuyao(udm)
        assert any("偏弱" in w or "阻力" in w for w in weaknesses)

    def test_liuyao_score_in_range(self):
        """六爻评分应在0-100之间"""
        udm = _make_liuyao_udm()
        score, _, _, _ = _score_liuyao(udm)
        assert 0 <= score <= 100

    def test_liuyao_single_dong_yao(self):
        """单一动爻应有加分"""
        udm = _make_liuyao_udm(dong_yao=[3])
        score, _, strengths, _ = _score_liuyao(udm)
        assert any("清晰" in s or "明确" in s for s in strengths)

    def test_liuyao_many_dong_yao(self):
        """多个动爻应有弱点提示"""
        udm = _make_liuyao_udm(dong_yao=[1, 2, 3, 4])
        score, _, _, weaknesses = _score_liuyao(udm)
        assert any("复杂" in w or "变数" in w for w in weaknesses)

    def test_liuyao_analysis_mentions_gua(self):
        """分析应提及卦名"""
        udm = _make_liuyao_udm(ben_gua="乾为天", bian_gua="天风姤")
        _, analysis, _, _ = _score_liuyao(udm)
        assert "乾为天" in analysis
        assert "天风姤" in analysis


# ============================================================
# 奇门遁甲评分测试
# ============================================================

class TestScoreQimen:

    def test_qimen_no_data_returns_zero(self):
        """奇门数据缺失时应返回0分"""
        udm = MagicMock()
        udm.qimen_chart = None
        score, analysis, strengths, weaknesses = _score_qimen(udm)
        assert score == 0
        assert "不完整" in analysis

    def test_qimen_ji_ge(self):
        """吉格应得高分"""
        udm = _make_qimen_udm(ji_ge=[{"name": "天遁", "gong": 3, "desc": "吉"}])
        score, _, strengths, _ = _score_qimen(udm)
        assert score >= 25

    def test_qimen_xiong_ge(self):
        """凶格应得低分"""
        udm = _make_qimen_udm(
            ji_ge=[],
            xiong_ge=[{"name": "悖格", "gong": 5, "desc": "凶"}, {"name": "刑格", "gong": 3, "desc": "凶"}]
        )
        score, _, _, weaknesses = _score_qimen(udm)
        assert any("凶格" in w or "留心" in w for w in weaknesses)

    def test_qimen_score_in_range(self):
        """奇门评分应在0-100之间"""
        udm = _make_qimen_udm()
        score, _, _, _ = _score_qimen(udm)
        assert 0 <= score <= 100

    def test_qimen_zhi_fu_present(self):
        """值符有数据应加分"""
        udm = _make_qimen_udm(zhi_fu_gong="坎一宫")
        score, _, strengths, _ = _score_qimen(udm)
        assert any("值符" in s for s in strengths)

    def test_qimen_ji_men(self):
        """吉门多应加分"""
        udm = _make_qimen_udm(ba_men={"1": "开门", "2": "生门", "3": "休门", "4": "景门"})
        score, _, strengths, _ = _score_qimen(udm)
        assert any("八门" in s or "门路" in s for s in strengths)

    def test_qimen_analysis_mentions_ju(self):
        """分析应提及格局"""
        udm = _make_qimen_udm(ju_name="阳遁3局")
        _, analysis, _, _ = _score_qimen(udm)
        assert "阳遁3局" in analysis


# ============================================================
# 大六壬评分测试
# ============================================================

class TestScoreLiuren:

    def test_liuren_no_data_returns_zero(self):
        """六壬数据缺失时应返回0分"""
        udm = MagicMock()
        udm.liuren_chart = None
        score, analysis, strengths, weaknesses = _score_liuren(udm)
        assert score == 0
        assert "不完整" in analysis

    def test_liuren_ji_ke(self):
        """吉课应得高分"""
        udm = _make_liuren_udm(ge_ju="天心课")
        score, _, strengths, _ = _score_liuren(udm)
        assert score >= 25

    def test_liuren_xiong_ke(self):
        """凶课应得低分"""
        udm = _make_liuren_udm(ge_ju="天祸课")
        score, _, _, weaknesses = _score_liuren(udm)
        assert any("小心" in w or "不太乐观" in w for w in weaknesses)

    def test_liuren_score_in_range(self):
        """六壬评分应在0-100之间"""
        udm = _make_liuren_udm()
        score, _, _, _ = _score_liuren(udm)
        assert 0 <= score <= 100

    def test_liuren_yong_shen_wang(self):
        """用神旺相应得高分"""
        udm = _make_liuren_udm(yong_shen_status="旺")
        score, _, strengths, _ = _score_liuren(udm)
        assert any("旺" in s for s in strengths)

    def test_liuren_yong_shen_weak(self):
        """用神休囚应得低分"""
        udm = _make_liuren_udm(yong_shen_status="休")
        score, _, _, weaknesses = _score_liuren(udm)
        assert any("动力不足" in w or "休囚" in w for w in weaknesses)

    def test_liuren_analysis_mentions_geju(self):
        """分析应提及课体"""
        udm = _make_liuren_udm(ge_ju="天心课")
        _, analysis, _, _ = _score_liuren(udm)
        assert "天心课" in analysis


# ============================================================
# 太乙神数评分测试
# ============================================================

class TestScoreTaiyi:

    def test_taiyi_no_data_returns_zero(self):
        """太乙数据缺失时应返回0分"""
        udm = MagicMock()
        udm.taiyi_chart = None
        score, analysis, strengths, weaknesses = _score_taiyi(udm)
        assert score == 0
        assert "不完整" in analysis

    def test_taiyi_strong_zhu_suan(self):
        """主算强应得高分"""
        udm = _make_taiyi_udm(zhu_suan=8)
        score, _, strengths, _ = _score_taiyi(udm)
        assert score >= 30
        assert any("很强" in s or "力量" in s for s in strengths)

    def test_taiyi_weak_zhu_suan(self):
        """主算弱应得低分"""
        udm = _make_taiyi_udm(zhu_suan=1)
        score, _, _, weaknesses = _score_taiyi(udm)
        assert any("偏弱" in w or "外力" in w for w in weaknesses)

    def test_taiyi_score_in_range(self):
        """太乙评分应在0-100之间"""
        udm = _make_taiyi_udm()
        score, _, _, _ = _score_taiyi(udm)
        assert 0 <= score <= 100

    def test_taiyi_with_gong(self):
        """太乙有落宫应加分"""
        udm = _make_taiyi_udm(taiyi_gong="坎一宫")
        score, _, strengths, _ = _score_taiyi(udm)
        assert any("坎一宫" in s for s in strengths)

    def test_taiyi_analysis_mentions_ju(self):
        """分析应提及格局"""
        udm = _make_taiyi_udm()
        _, analysis, _, _ = _score_taiyi(udm)
        assert "太乙" in analysis


# ============================================================
# 占星评分测试
# ============================================================

class TestScoreAstro:

    def test_astro_no_data_returns_zero(self):
        """占星数据缺失时应返回0分"""
        udm = MagicMock()
        udm.astro_chart = None
        score, analysis, strengths, weaknesses = _score_astro(udm)
        assert score == 0
        assert "不完整" in analysis

    def test_astro_ji_aspects(self):
        """吉相位多应得高分"""
        udm = _make_astro_udm(aspects=[
            {"planet1": "太阳", "planet2": "月亮", "aspect": "三合"},
            {"planet1": "金星", "planet2": "木星", "aspect": "六合"},
            {"planet1": "水星", "planet2": "火星", "aspect": "合相"},
        ])
        score, _, strengths, _ = _score_astro(udm)
        assert score >= 20
        assert any("吉相位" in s for s in strengths)

    def test_astro_xiong_aspects(self):
        """刑冲相位多应扣分"""
        udm = _make_astro_udm(aspects=[
            {"planet1": "太阳", "planet2": "土星", "aspect": "刑"},
            {"planet1": "火星", "planet2": "冥王星", "aspect": "冲"},
            {"planet1": "金星", "planet2": "天王星", "aspect": "刑"},
        ])
        score, _, _, weaknesses = _score_astro(udm)
        assert any("刑冲" in w or "张力" in w for w in weaknesses)

    def test_astro_score_in_range(self):
        """占星评分应在0-100之间"""
        udm = _make_astro_udm()
        score, _, _, _ = _score_astro(udm)
        assert 0 <= score <= 100

    def test_astro_analysis_mentions_signs(self):
        """分析应提及太阳和月亮星座"""
        udm = _make_astro_udm(sun_sign="双子", moon_sign="天蝎")
        _, analysis, _, _ = _score_astro(udm)
        assert "双子" in analysis
        assert "天蝎" in analysis


# ============================================================
# score_all 综合测试
# ============================================================

class TestScoreAll:

    def _make_full_udm(self):
        """构造所有术法数据完整的 mock UDM"""
        udm = MagicMock()
        # 八字
        udm.bazi_year = _make_pillar("乙酉")
        udm.bazi_month = _make_pillar("壬午")
        udm.bazi_day = _make_pillar("甲子")
        udm.bazi_time = _make_pillar("庚午")
        udm.xi_yong = {"strength": "身强", "xi": ["水", "木"], "ji": ["火", "土"]}
        udm.wuxing_score = {"木": 2, "火": 3, "土": 1, "金": 2, "水": 2}
        udm.shensha = ["天乙（日柱）"]
        udm.zhi_relations = ["子午冲"]
        udm.dayun = [{"ganzhi": "辛巳", "start_age": 5, "end_age": 14}]
        # 紫微
        udm.ziwei_chart = {
            "ming_gong": "寅", "soul_star": "紫微",
            "palaces": [{"name": "命宫", "major_stars": [{"name": "紫微"}], "minor_stars": []}],
            "sihua": {"化禄": "廉贞", "化权": "破军", "化科": "武曲"},
        }
        # 六爻
        udm.liuyao_chart = {
            "ben_gua": {"name": "乾为天"}, "bian_gua": {"name": "天风姤"},
            "dong_yao": [1], "shi": 1, "ying": 4, "ge_ju": ["世应合"],
            "wuxing_analysis": {"yong_shen": "父母爻"},
        }
        # 奇门
        udm.qimen_chart = {
            "ju_name": "阳遁3局", "zhi_fu_gong": "坎一宫",
            "ba_men": {"1": "开门", "2": "生门"},
            "ge_ju_analysis": {"ji_ge": [{"name": "天遁", "gong": 3, "desc": "吉"}], "xiong_ge": []},
            "palaces": [],
        }
        # 大六壬
        udm.liuren_chart = {
            "ge_ju": "天心课", "yong_shen": {"status": "旺"},
            "si_ke": ([], [], [], []), "san_chuan": ([], [], []),
        }
        # 太乙
        udm.taiyi_chart = {
            "zhu_suan": [7], "ke_suan": [3], "ding_suan": [5],
            "taiyi_gong": "坎一宫", "ju_name": "太乙第一局",
        }
        # 占星
        udm.astro_chart = {
            "sun_sign": "双子", "moon_sign": "天蝎",
            "ascendant_sign": "狮子", "ascendant": "狮子",
            "mc_sign": "白羊", "mc": "白羊",
            "planets": {},
            "aspects": [{"planet1": "太阳", "planet2": "月亮", "aspect": "三合"}],
            "planetary_details": {},
        }
        return udm

    def test_score_all_returns_all_methods(self):
        """score_all 应返回所有7个术法的评分"""
        udm = self._make_full_udm()
        result = score_all(udm)
        assert len(result) == 7
        for method in ["八字", "紫微斗数", "六爻", "奇门遁甲", "大六壬", "太乙神数", "占星"]:
            assert method in result, f"缺少 {method}"

    def test_score_all_scores_in_range(self):
        """所有评分应在0-100之间"""
        udm = self._make_full_udm()
        result = score_all(udm)
        for method, data in result.items():
            assert 0 <= data["score"] <= 100, f"{method} 评分超出范围: {data['score']}"

    def test_score_all_has_analysis(self):
        """每个术法应有分析文本"""
        udm = self._make_full_udm()
        result = score_all(udm)
        for method, data in result.items():
            assert isinstance(data["analysis"], str), f"{method} analysis 不是字符串"
            assert len(data["analysis"]) > 0, f"{method} analysis 为空"

    def test_score_all_has_strengths_weaknesses(self):
        """每个术法应有优劣势列表"""
        udm = self._make_full_udm()
        result = score_all(udm)
        for method, data in result.items():
            assert isinstance(data["strengths"], list), f"{method} strengths 不是列表"
            assert isinstance(data["weaknesses"], list), f"{method} weaknesses 不是列表"

    def test_score_all_empty_udm(self):
        """空 UDM 不应崩溃，所有术法应返回0分或错误提示"""
        udm = MagicMock()
        udm.bazi_year = None
        udm.ziwei_chart = None
        udm.liuyao_chart = None
        udm.qimen_chart = None
        udm.liuren_chart = None
        udm.taiyi_chart = None
        udm.astro_chart = None
        result = score_all(udm)
        assert len(result) == 7
        for method, data in result.items():
            assert data["score"] == 0, f"{method} 空数据应返回0分"

    def test_score_all_single_method(self):
        """指定单个术法应只返回该术法"""
        udm = self._make_full_udm()
        result = score_all(udm, method="八字")
        assert len(result) == 1
        assert "八字" in result

    def test_score_all_engine_exception_handled(self):
        """引擎异常不应导致整体崩溃"""
        udm = MagicMock()
        udm.bazi_year = _make_pillar("甲子")
        udm.xi_yong = None
        udm.wuxing_score = None
        udm.shensha = None
        udm.zhi_relations = None
        udm.dayun = None
        udm.ziwei_chart = None
        udm.liuyao_chart = None
        udm.qimen_chart = None
        udm.liuren_chart = None
        udm.taiyi_chart = None
        udm.astro_chart = None
        # 不应抛出异常
        result = score_all(udm)
        assert len(result) == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
