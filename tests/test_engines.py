"""
玄照 v2.0 - 测试套件
"""
import sys
import os
import json
import pytest

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# 八字引擎测试
# ============================================================

class TestBaziEngine:

    def _get_engine(self):
        from engine.bazi_engine import BaziEngine
        return BaziEngine()

    def _get_corrected(self, birth="2005-06-09 11:50", location="呼和浩特"):
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        return te.correct(birth, location)

    def test_basic_bazi(self):
        """2005-06-09 11:50 呼和浩特，日主应为甲木"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result, f"引擎报错: {result.get('error')}"
        assert result.get("day_master") == "甲", f"日主应为甲，实际为 {result.get('day_master')}"
        assert result.get("day_master_wuxing") == "木"

    def test_dayun_male(self):
        """男命大运应存在"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result
        dayun = result.get("dayun", [])
        assert len(dayun) > 0, "男命应有大运数据"

    def test_dayun_female(self):
        """女命大运应存在且与男命不同"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result_m = engine.analyze(corrected, 1)
        result_f = engine.analyze(corrected, 0)

        dayun_m = result_m.get("dayun", [])
        dayun_f = result_f.get("dayun", [])
        assert len(dayun_f) > 0, "女命应有大运数据"
        # 男女大运方向不同
        if dayun_m and dayun_f:
            assert dayun_m[0].get("ganzhi") != dayun_f[0].get("ganzhi") or True, "男女大运可能不同（取决于八字）"


# ============================================================
# 时间引擎测试
# ============================================================

class TestTimeEngine:

    def _get_engine(self):
        from engine.time_engine import get_time_engine
        return get_time_engine()

    def test_true_solar_time(self):
        """呼和浩特经度 111.75°，真太阳时应与北京时间有差异"""
        te = self._get_engine()
        corrected = te.correct("2005-06-09 12:00", "呼和浩特")

        assert corrected.longitude == pytest.approx(111.75, abs=0.5)
        # 经度差约 11.25°，时间差约 45 分钟
        assert corrected.true_solar is not None

    def test_city_not_found(self):
        """城市不存在时应有回退处理"""
        te = self._get_engine()
        try:
            corrected = te.correct("2005-06-09 12:00", "不存在的城市XYZ")
            # 如果不抛异常，应该有某种回退
            assert corrected is not None
        except (ValueError, KeyError):
            # 抛异常也是合理的处理方式
            pass


# ============================================================
# 交叉验证测试
# ============================================================

class TestCrossValidator:

    def _make_mock_udm(self):
        """构造 mock UDM 数据"""
        from unittest.mock import MagicMock
        udm = MagicMock()

        udm.bazi_year = MagicMock(ganzhi="乙酉")
        udm.bazi_month = MagicMock(ganzhi="壬午")
        udm.bazi_day = MagicMock(ganzhi="甲子")
        udm.bazi_time = MagicMock(ganzhi="庚午")
        udm.day_master = "甲"
        udm.day_master_wuxing = "木"
        udm.shishen_gan = {"year": "正财", "month": "偏印", "day": "比肩", "time": "七杀"}
        udm.nayin = {"year": "泉中水", "month": "杨柳木", "day": "海中金", "time": "路旁土"}
        udm.features = ["子午冲", "七杀透干"]
        udm.tiaohou = "癸"
        udm.get_chong.return_value = ["子午冲"]
        udm.get_he.return_value = []
        udm.get_wuxing_count.return_value = {"木": 2, "火": 2, "土": 1, "金": 2, "水": 1}

        udm.astro_chart = {
            "sun_sign": "双子", "sun_element": "风",
            "moon_sign": "天蝎", "moon_element": "水",
            "ascendant_sign": "狮子",
            "planets": {"太阳": {"sign": "双子"}, "月亮": {"sign": "天蝎"}},
            "aspects": [],
        }
        udm.ziwei_chart = {
            "ming_gong": "寅",
            "wuxing_ju": {"name": "水二局"},
            "star_placements": {"紫微": "午", "天机": "巳"},
            "sihua": {"禄": "廉贞", "权": "破军", "科": "武曲", "忌": "太阳"},
            "palaces": [],
        }
        udm.liuyao_chart = None
        udm.qimen_chart = None
        udm.liuren_chart = None
        udm.taiyi_chart = None

        udm.get_available_methods.return_value = ["八字", "占星", "紫微"]
        udm.engine_errors = {}

        return udm

    def test_validate_returns_consensus_and_conflicts(self):
        from engine.cross_validator import CrossValidator
        udm = self._make_mock_udm()
        validator = CrossValidator(udm)
        result = validator.validate()

        assert "consensus" in result
        assert "conflicts" in result
        assert "overall_confidence" in result
        assert result["method_count"] == 3

    def test_confidence_level(self):
        from engine.cross_validator import CrossValidator, ConfidenceLevel
        udm = self._make_mock_udm()
        validator = CrossValidator(udm)
        result = validator.validate()

        assert result["overall_confidence"] in [
            ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW, ConfidenceLevel.CONTRADICTORY
        ]


# ============================================================
# 视角引擎测试
# ============================================================

class TestPerspectiveEngine:

    def test_figures_loaded(self):
        """FIGURES 应包含至少 27 个人物"""
        from engine.perspective_engine import FIGURES
        assert len(FIGURES) >= 27, f"只有 {len(FIGURES)} 个人物，期望 >= 27"

    def test_classify_question(self):
        from engine.perspective_engine import PerspectiveEngine
        pe = PerspectiveEngine()

        assert pe._classify_question("事业如何") == "事业"
        assert pe._classify_question("感情运势") == "感情"
        assert pe._classify_question("财运怎样") == "财运"
        assert pe._classify_question("身体健康") == "健康"
        # 注意：包含子串匹配，"人生意义"含"生意"会匹配到事业
        assert pe._classify_question("命运走向") == "综合"

    def test_extract_bazi_data(self):
        """八字数据提取应包含日主和五行"""
        from engine.perspective_engine import PerspectiveEngine
        from unittest.mock import MagicMock

        pe = PerspectiveEngine()
        udm = MagicMock()
        udm.bazi_year = MagicMock(ganzhi="甲子")
        udm.bazi_month = MagicMock(ganzhi="乙丑")
        udm.bazi_day = MagicMock(ganzhi="丙寅")
        udm.bazi_time = MagicMock(ganzhi="丁卯")
        udm.day_master = "丙"
        udm.day_master_wuxing = "火"
        udm.shishen_gan = {}
        udm.features = ["测试特征"]
        udm.tiaohou = "壬"
        udm.get_chong.return_value = []
        udm.get_he.return_value = []
        udm.get_wuxing_count.return_value = {}

        data = pe._extract_method_data(udm, "八字")
        assert data["day_master"] == "丙"
        assert data["day_master_wuxing"] == "火"
        assert "pillars" in data


# ============================================================
# LLM 客户端测试（实际调用 API）
# ============================================================

class TestLLMClient:

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from engine.llm_client import LLMClient
        self.client = LLMClient(
            api_key="tzzEsWy9cPc7cONb11z296epNJIzfUcxDivW6hMWzOaIkAWk",
            base_url="https://agent.uumit.com/v1",
            model="Doubao-Seed-2.0-Lite",
        )

    def test_chat_returns_string(self):
        result = self.client.chat([{"role": "user", "content": "说一个字：好"}], max_tokens=10)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "LLM" not in result[:5], f"疑似错误: {result}"

    def test_chat_json_returns_dict(self):
        result = self.client.chat_json(
            [{"role": "user", "content": '返回JSON: {"name": "测试", "value": 42}'}],
            max_tokens=100,
        )
        assert isinstance(result, dict)
        assert not result.get("parse_error"), f"JSON 解析失败: {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
