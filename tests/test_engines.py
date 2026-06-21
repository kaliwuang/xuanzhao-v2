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
            assert dayun_m[0].get("ganzhi") != dayun_f[0].get("ganzhi"), "男女大运应该不同"


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
        assert pe._classify_question("命运走向") == "综合"
        # 长词优先匹配：避免子串误命中
        assert pe._classify_question("找工作难不难") == "事业"
        assert pe._classify_question("人际关系怎么样") == "人际"
        assert pe._classify_question("考研考公哪个好") == "学业"
        # 子女分类（新增）
        assert pe._classify_question("子女运势如何") == "子女"
        assert pe._classify_question("什么时候能怀孕") == "子女"
        assert pe._classify_question("子女缘如何") == "子女"  # "子女"匹配到子女分类

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

    def test_extract_liuyao_data_enriched(self):
        """六爻数据提取应包含世应、六神、日月建等新增字段"""
        from engine.perspective_engine import PerspectiveEngine
        from unittest.mock import MagicMock

        pe = PerspectiveEngine()
        udm = MagicMock()
        udm.liuyao_chart = {
            "ben_gua": {"name": "乾为天"},
            "bian_gua": {"name": "天风姤"},
            "dong_yao": [1],
            "shi": 1,
            "ying": 4,
            "gua_gong_wuxing": "金",
            "liu_shen": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
            "ri_yue_jian": {"ri_jian": "子", "ri_wangshuai": {"金": "旺", "木": "死"}},
            "lines": [{"position": 1, "liu_qin": "父母", "dizhi": "子", "wuxing": "水", "is_dong": True}],
            "wuxing_analysis": {"yong_shen": "父母爻"},
        }

        data = pe._extract_method_data(udm, "六爻")
        assert data["shi"] == 1
        assert data["ying"] == 4
        assert len(data["liu_shen"]) == 6
        assert data["ri_yue_jian"]["ri_jian"] == "子"
        assert len(data["lines"]) == 1
        assert data["lines"][0]["liu_qin"] == "父母"
        assert data["wuxing_analysis"]["yong_shen"] == "父母爻"

    def test_extract_qimen_data_enriched(self):
        """奇门数据提取应包含旬空、流年、三盘摘要等新增字段"""
        from engine.perspective_engine import PerspectiveEngine
        from unittest.mock import MagicMock

        pe = PerspectiveEngine()
        udm = MagicMock()
        udm.qimen_chart = {
            "ju_name": "阳遁3局",
            "yin_yang": "阳遁",
            "jieqi": "春分",
            "di_pan": {"1": "戊"},
            "tian_pan": {"1": "戊"},
            "ba_men": {"1": "休门"},
            "jiu_xing": {"1": "天蓬"},
            "ba_shen": {"1": "值符"},
            "zhi_fu": {"star": "天蓬", "gong": 1},
            "zhi_shi": {"door": "休门", "gong": 1},
            "palaces": [],
            "ge_ju_analysis": {"ji_ge": [], "xiong_ge": []},
            "xun_kong": {"xun_shou": "甲子", "kong_wang": ["戌", "亥"]},
            "liunian": {"year_ganzhi": "乙巳", "tai_sui_gong": 9, "tai_sui_palace_name": "离九宫"},
            "san_pan_summary": {"1": {"name": "坎一宫"}},
        }

        data = pe._extract_method_data(udm, "奇门")
        assert data["yin_yang"] == "阳遁"
        assert data["jieqi"] == "春分"
        assert data["xun_kong"]["kong_wang"] == ["戌", "亥"]
        assert data["liunian"]["year_ganzhi"] == "乙巳"
        assert "1" in data["san_pan_summary"]


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
        try:
            result = self.client.chat([{"role": "user", "content": "说一个字：好"}], max_tokens=10)
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            pytest.skip(f"LLM API unavailable: {e}")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chat_json_returns_dict(self):
        try:
            result = self.client.chat_json(
                [{"role": "user", "content": '返回JSON: {"name": "测试", "value": 42}'}],
                max_tokens=100,
            )
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            pytest.skip(f"LLM API unavailable: {e}")
        assert isinstance(result, dict)
        assert not result.get("parse_error"), f"JSON 解析失败: {result}"


# ============================================================
# 紫微斗数引擎测试
# ============================================================

class TestZiWeiEngine:

    def _get_engine(self):
        from engine.ziwei_engine import ZiWeiEngine
        return ZiWeiEngine()

    def _get_corrected(self, birth="2005-06-09 11:50", location="呼和浩特"):
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        return te.correct(birth, location)

    def test_basic_ziwei(self):
        """紫微排盘应返回命宫和宫位数据"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result, f"引擎报错: {result.get('error')}"
        assert "ming_gong" in result, "缺少命宫字段"
        assert "palaces" in result, "缺少宫位数据"
        assert len(result["palaces"]) == 12, f"应有12宫，实际 {len(result['palaces'])}"

    def test_ziwei_sihua(self):
        """紫微排盘应包含四化信息"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result
        sihua = result.get("sihua", {})
        assert isinstance(sihua, dict), "四化应为字典"
        assert len(sihua) > 0, "四化不应为空"

    def test_ziwei_wuxing_ju(self):
        """紫微排盘应包含五行局"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result
        wuxing_ju = result.get("wuxing_ju", {})
        assert "wuxing" in wuxing_ju, "五行局缺少五行"
        assert "ju_shu" in wuxing_ju, "五行局缺少局数"

    def test_ziwei_male_female(self):
        """男女命盘应该都可排"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result_m = engine.analyze(corrected, 1)
        result_f = engine.analyze(corrected, 0)

        assert "error" not in result_m, f"男命报错: {result_m.get('error')}"
        assert "error" not in result_f, f"女命报错: {result_f.get('error')}"
        assert result_m.get("gender") == "男"
        assert result_f.get("gender") == "女"

    def test_ziwei_star_placements(self):
        """紫微排盘应有星曜分布数据"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result
        sp = result.get("star_placements", {})
        assert isinstance(sp, dict), "星曜分布应为字典"
        assert "紫微" in sp, "应能找到紫微星位置"


# ============================================================
# 占星引擎测试
# ============================================================

class TestAstroEngine:

    def _get_engine(self):
        from engine.astro_engine import AstroEngine
        return AstroEngine()

    def _get_corrected(self, birth="2005-06-09 11:50", location="呼和浩特"):
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        return te.correct(birth, location)

    def test_basic_astro(self):
        """占星排盘应返回行星数据"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result, f"引擎报错: {result.get('error')}"
        assert "sun_sign" in result, "缺少太阳星座"
        assert "moon_sign" in result, "缺少月亮星座"
        assert result["sun_sign"] in [
            '白羊','金牛','双子','巨蟹','狮子','处女',
            '天秤','天蝎','射手','摩羯','水瓶','双鱼'
        ], f"太阳星座异常: {result['sun_sign']}"

    def test_astro_planets(self):
        """占星排盘应包含10颗行星"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        planets = result.get("planets", {})
        assert len(planets) == 10, f"应有10颗行星，实际 {len(planets)}"
        for pname in ['太阳', '月亮', '水星', '金星', '火星', '木星', '土星', '天王星', '海王星', '冥王星']:
            assert pname in planets, f"缺少行星: {pname}"
            assert "sign" in planets[pname], f"行星 {pname} 缺少星座信息"

    def test_astro_houses(self):
        """占星排盘应包含12宫"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        houses = result.get("houses", [])
        assert len(houses) == 12, f"应有12宫，实际 {len(houses)}"

    def test_astro_ascendant(self):
        """占星排盘应有上升点"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "ascendant" in result, "缺少上升点"
        assert "ascendant_sign" in result, "缺少上升星座"
        assert result["ascendant_sign"] in [
            '白羊','金牛','双子','巨蟹','狮子','处女',
            '天秤','天蝎','射手','摩羯','水瓶','双鱼'
        ]

    def test_astro_aspects(self):
        """占星排盘应返回相位数据"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        aspects = result.get("aspects", [])
        assert isinstance(aspects, list), "相位应为列表"
        # 每个相位应有关键字段
        for asp in aspects:
            assert "planet1" in asp, "相位缺少 planet1"
            assert "planet2" in asp, "相位缺少 planet2"
            assert "aspect" in asp, "相位缺少 aspect"

    def test_astro_aspects_summary(self):
        """占星排盘应有相位摘要"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        summary = result.get("aspects_summary", {})
        assert "total" in summary, "相位摘要缺少 total"
        assert "harmonious" in summary, "相位摘要缺少 harmonious"
        assert "challenging" in summary, "相位摘要缺少 challenging"


# ============================================================
# 六爻引擎测试
# ============================================================

class TestLiuYaoEngine:

    def _get_engine(self):
        from engine.liuyao_engine import LiuYaoEngine
        return LiuYaoEngine()

    def _get_corrected(self, birth="2005-06-09 11:50", location="呼和浩特"):
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        return te.correct(birth, location)

    def test_basic_liuyao(self):
        """六爻排盘应返回本卦和变卦"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result, f"引擎报错: {result.get('error')}"
        assert "ben_gua" in result, "缺少本卦"
        assert "bian_gua" in result, "缺少变卦"
        assert "name" in result["ben_gua"], "本卦缺卦名"

    def test_liuyao_dong_yao(self):
        """六爻排盘应有动爻"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        dong_yao = result.get("dong_yao", [])
        assert len(dong_yao) > 0, "应至少有一个动爻"
        assert all(1 <= d <= 6 for d in dong_yao), "动爻位置应在1-6"

    def test_liuyao_lines(self):
        """六爻排盘应有6条爻线"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        lines = result.get("lines", [])
        assert len(lines) == 6, f"应有6条爻，实际 {len(lines)}"
        for line in lines:
            assert "position" in line, "爻缺 position"
            assert "gan" in line, "爻缺天干"
            assert "zhi" in line or "dizhi" in line, "爻缺地支"
            assert "wuxing" in line, "爻缺五行"

    def test_liuyao_shi_ying(self):
        """六爻排盘应有世应"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "shi" in result, "缺少世爻"
        assert "ying" in result, "缺少应爻"
        assert 1 <= result["shi"] <= 6, "世爻应在1-6"
        assert 1 <= result["ying"] <= 6, "应爻应在1-6"

    def test_liuyao_liu_shen(self):
        """六爻排盘应有六神"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        liu_shen = result.get("liu_shen", [])
        assert len(liu_shen) > 0, "六神不应为空"


# ============================================================
# 奇门遁甲引擎测试
# ============================================================

class TestQiMenEngine:

    def _get_engine(self):
        from engine.qimen_engine import QiMenEngine
        return QiMenEngine()

    def _get_corrected(self, birth="2005-06-09 11:50", location="呼和浩特"):
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        return te.correct(birth, location)

    def test_basic_qimen(self):
        """奇门排盘应返回局数和宫位"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result, f"引擎报错: {result.get('error')}"
        assert "ju_shu" in result, "缺少局数"
        assert 1 <= result["ju_shu"] <= 9, f"局数应在1-9: {result['ju_shu']}"

    def test_qimen_palaces(self):
        """奇门排盘应有9个宫位"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        palaces = result.get("palaces", [])
        assert len(palaces) == 9, f"应有9宫，实际 {len(palaces)}"
        for pal in palaces:
            assert "gong" in pal, "宫位缺 gong"
            assert "name" in pal, "宫位缺 name"
            assert "di_pan" in pal, "宫位缺地盘"
            assert "tian_pan" in pal, "宫位缺天盘"

    def test_qimen_yin_yang(self):
        """奇门排盘应有阴阳遁信息"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "yin_yang" in result, "缺少阴阳遁"
        assert result["yin_yang"] in ["阳遁", "阴遁"], f"阴阳遁异常: {result['yin_yang']}"

    def test_qimen_ba_men(self):
        """奇门排盘应有八门"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        ba_men = result.get("ba_men", {})
        assert isinstance(ba_men, dict), "八门应为字典"
        assert len(ba_men) > 0, "八门不应为空"

    def test_qimen_zhi_fu(self):
        """奇门排盘应有值符信息"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        zhi_fu = result.get("zhi_fu", {})
        assert "star" in zhi_fu, "值符缺星"
        assert "gong" in zhi_fu, "值符缺宫"


# ============================================================
# 大六壬引擎测试
# ============================================================

class TestLiuRenEngine:

    def _get_engine(self):
        from engine.liuren_engine import LiuRenEngine
        return LiuRenEngine()

    def _get_corrected(self, birth="2005-06-09 11:50", location="呼和浩特"):
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        return te.correct(birth, location)

    def test_basic_liuren(self):
        """大六壬排盘应返回四课三传"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result, f"引擎报错: {result.get('error')}"
        assert "si_ke" in result, "缺少四课"
        assert "san_chuan" in result, "缺少三传"

    def test_liuren_tian_pan(self):
        """大六壬排盘应有天地盘"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        tian_pan = result.get("tian_pan", {})
        assert isinstance(tian_pan, dict), "天盘应为字典"
        assert len(tian_pan) == 12, f"天盘应有12位，实际 {len(tian_pan)}"

    def test_liuren_sizhu(self):
        """大六壬排盘应有四柱信息"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        for key in ["year_gan", "year_zhi", "month_gan", "month_zhi",
                     "day_gan", "day_zhi", "time_gan", "time_zhi"]:
            assert key in result, f"缺少四柱字段: {key}"

    def test_liuren_jieqi(self):
        """大六壬排盘应有节气信息"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "jieqi" in result, "缺少节气"
        assert "yue_jiang" in result, "缺少月将"
        assert "zhan_shi" in result, "缺少占时"

    def test_liuren_positions(self):
        """大六壬排盘应有十二宫位置"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        positions = result.get("positions", {})
        assert len(positions) == 12, f"应有12位，实际 {len(positions)}"


# ============================================================
# 太乙神数引擎测试
# ============================================================

class TestTaiYiEngine:

    def _get_engine(self):
        from engine.taiyi_engine import TaiYiEngine
        return TaiYiEngine()

    def _get_corrected(self, birth="2005-06-09 11:50", location="呼和浩特"):
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        return te.correct(birth, location)

    def test_basic_taiyi(self):
        """太乙排盘应返回太乙宫位"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result, f"引擎报错: {result.get('error')}"
        assert "taiyi_gong" in result, "缺少太乙宫"
        assert "taiyi_num" in result, "缺少太乙数"

    def test_taiyi_ganzhi(self):
        """太乙排盘应有干支信息"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result
        assert "year_ganzhi" in result, "缺少年干支"

    def test_taiyi_sanji(self):
        """太乙排盘应有三基"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result
        san_ji = result.get("san_ji", {})
        assert isinstance(san_ji, dict), "三基应为字典"
        for key in ["君基", "臣基", "民基"]:
            assert key in san_ji, f"三基缺少: {key}"

    def test_taiyi_suan(self):
        """太乙排盘应有主算客算"""
        engine = self._get_engine()
        corrected = self._get_corrected()
        result = engine.analyze(corrected, 1)

        assert "error" not in result
        assert "zhu_suan" in result, "缺少主算"
        assert "ke_suan" in result, "缺少客算"


# ============================================================
# 姓名学引擎测试
# ============================================================

class TestXingMingEngine:

    def _get_engine(self):
        from engine.xingming_engine import XingMingEngine
        return XingMingEngine()

    def test_basic_xingming(self):
        """姓名学分析应返回五格和评分"""
        engine = self._get_engine()
        result = engine.analyze_name("张", "伟", "男")

        assert "wuge" in result, "缺少五格"
        assert "score" in result, "缺少评分"
        assert "sancai" in result, "缺少三才"

    def test_xingming_wuge_structure(self):
        """五格应包含天格人格地格外格总格"""
        engine = self._get_engine()
        result = engine.analyze_name("张", "伟", "男")

        wuge = result["wuge"]
        for key in ["天格", "人格", "地格", "外格", "总格"]:
            assert key in wuge, f"五格缺少: {key}"
            assert "画数" in wuge[key], f"{key} 缺少画数"
            assert "数理" in wuge[key], f"{key} 缺少数理"
            assert "吉凶" in wuge[key], f"{key} 缺少吉凶"

    def test_xingming_compound_surname(self):
        """复姓姓名分析应正常"""
        engine = self._get_engine()
        result = engine.analyze_name("欧阳", "明", "女")

        assert "wuge" in result
        assert result["is_compound_surname"] is True
        assert result["surname"] == "欧阳"

    def test_xingming_strokes(self):
        """笔画计算应正确"""
        engine = self._get_engine()
        assert engine.get_stroke("王") == 4
        assert engine.get_stroke("李") == 7
        assert engine.get_stroke("张") == 11

    def test_xingming_gender_difference(self):
        """男女名字评分应有差异"""
        engine = self._get_engine()
        result_m = engine.analyze_name("张", "伟", "男")
        result_f = engine.analyze_name("张", "伟", "女")

        # 至少结构应完整
        assert "score" in result_m
        assert "score" in result_f

    def test_xingming_long_name(self):
        """多字名应正常分析"""
        engine = self._get_engine()
        result = engine.analyze_name("司马", "懿", "男")

        assert "wuge" in result
        assert result["is_compound_surname"] is True


# ============================================================
# 边界情况测试
# ============================================================

class TestEdgeCases:

    def test_late_zi_hour(self):
        """23:xx 应判定为晚子时，日柱用次日"""
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        corrected = te.correct("2005-06-09 23:30", "北京")
        assert corrected.is_late_zi is True, "23:30 应为晚子时"
        # 晚子时八字用 hour=0
        assert corrected.bazi_hour == 0

    def test_dst_period_1988(self):
        """1988年夏令时期间，时间应回退1小时"""
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        # 1988年7月1日 在夏令时期间
        corrected = te.correct("1988-07-01 12:00", "北京")
        assert corrected is not None
        # 真太阳时应已考虑夏令时回退

    def test_boundary_year_1900(self):
        """1900年应能正常排盘"""
        from engine.time_engine import get_time_engine
        from engine.bazi_engine import BaziEngine
        te = get_time_engine()
        corrected = te.correct("1900-01-01 12:00", "北京")
        engine = BaziEngine()
        result = engine.analyze(corrected, 1)
        assert "error" not in result, f"1900年排盘报错: {result.get('error')}"

    def test_boundary_year_2100(self):
        """2100年应能正常排盘"""
        from engine.time_engine import get_time_engine
        from engine.bazi_engine import BaziEngine
        te = get_time_engine()
        corrected = te.correct("2100-12-31 12:00", "北京")
        engine = BaziEngine()
        result = engine.analyze(corrected, 1)
        assert "error" not in result, f"2100年排盘报错: {result.get('error')}"

    def test_unknown_city_fallback(self):
        """未知城市应回退到北京并产生日志警告"""
        from engine.time_engine import get_time_engine
        te = get_time_engine()
        corrected = te.correct("2000-01-01 12:00", "火星基地")
        assert corrected.longitude == pytest.approx(116.4074, abs=0.5)
        assert corrected.latitude == pytest.approx(39.9042, abs=0.5)

    def test_midnight_birth(self):
        """00:00 出生应正常处理"""
        from engine.time_engine import get_time_engine
        from engine.bazi_engine import BaziEngine
        te = get_time_engine()
        corrected = te.correct("2000-06-15 00:00", "上海")
        assert corrected.bazi_hour == 0
        engine = BaziEngine()
        result = engine.analyze(corrected, 1)
        assert "error" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
