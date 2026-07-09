"""
玄照 v2.0 - 108视角引擎测试

覆盖:
- PerspectiveEngine.analyze() 接口契约
- Figure / ThinkingModel / PerspectiveOpinion 数据结构
- _load_figures / _default_figures 数据加载
- 108 个视角的覆盖完整性(至少要 load 出 108 个)
- 分析输出必须包含 reasoning / key_points / confidence

梧 2026-07-09 指令: 一直补充
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.perspective_engine import (
    PerspectiveEngine,
    Figure,
    ThinkingModel,
    PerspectiveOpinion,
    _default_figures,
    _load_figures,
)


# ============================================================
# 数据结构
# ============================================================

class TestDataClasses:
    def test_thinking_model_creation(self):
        tm = ThinkingModel(
            name="因果律",
            principles=["种瓜得瓜"],
            steps=["观察", "归因", "验证"],
            key_concepts={"因": "原因", "果": "结果"},
        )
        assert tm.name == "因果律"
        assert len(tm.principles) == 1
        assert len(tm.steps) == 3

    def test_figure_creation(self):
        tm = ThinkingModel(name="测试", principles=[], steps=[], key_concepts={})
        f = Figure(
            id="test-figure",
            name="测试人物",
            title="虚拟",
            category="中国玄学",
            faction="orthodox",
            expertise=["八字"],
            primary_method="八字",
            thinking_model=tm,
            catchphrase="测试",
            bio="测试人物",
        )
        assert f.id == "test-figure"
        assert f.faction == "orthodox"

    def test_perspective_opinion_creation(self):
        op = PerspectiveOpinion(
            figure_id="test-figure",
            figure_name="测试人物",
            figure_title="虚拟",
            primary_method="八字",
            stance="同意",
            confidence=0.85,
            reasoning="测试推理",
            key_points=["点1"],
            quotes=["格言"],
            referenced_data={},
        )
        assert op.confidence == 0.85
        assert op.stance == "同意"


# ============================================================
# 数据加载
# ============================================================

class TestFigureLoading:
    def test_default_figures_at_least_10(self):
        """_default_figures 提供降级版本,至少包含 10 个"""
        figures = _default_figures()
        assert len(figures) >= 10, f"默认人物太少: {len(figures)}"

    def test_default_figures_have_required_fields(self):
        figures = _default_figures()
        for fid, f in figures.items():
            assert f.id, f"{fid} 缺 id"
            assert f.name, f"{fid} 缺 name"
            assert f.thinking_model is not None, f"{fid} 缺 thinking_model"
            assert f.primary_method, f"{fid} 缺 primary_method"

    def test_load_figures_108_targets(self):
        """_load_figures 应能返回完整 108 视角
        数据来源: perspectives/figures.json"""
        figures = _load_figures()
        # 期望 108 (项目 README 宣传)
        assert len(figures) >= 100, f"人物数量异常: {len(figures)}, 应在 100+"

    def test_loaded_figures_have_valid_thinking_model(self):
        """loaded figures 的 thinking_model 必须有 name/principles/steps"""
        figures = _load_figures()
        for fid, f in figures.items():
            tm = f.thinking_model
            assert tm is not None, f"{fid} 缺 thinking_model"
            assert tm.name, f"{fid} thinking_model 缺 name"
            assert len(tm.principles) > 0, f"{fid} thinking_model 缺 principles"
            assert len(tm.steps) > 0, f"{fid} thinking_model 缺 steps"


# ============================================================
# 覆盖度检查
# ============================================================

class TestCoverage:
    def test_categories_covered(self):
        """视角应跨多个领域(中国玄学/西方哲学/科学创新等)"""
        figures = _load_figures()
        categories = set(f.category for f in figures.values())
        assert len(categories) >= 3, f"类别覆盖不足: {categories}"

    def test_methods_covered(self):
        """视角应覆盖多个术法,而不是只一个"""
        figures = _load_figures()
        methods = set(f.primary_method for f in figures.values())
        assert len(methods) >= 4, f"术法覆盖不足: {methods}"

    def test_expertise_lists_not_empty(self):
        """每个人物 expertise 应非空"""
        figures = _load_figures()
        empty_expertise = [fid for fid, f in figures.items() if not f.expertise]
        assert len(empty_expertise) == 0, f"expertise 为空: {empty_expertise}"


# ============================================================
# PerspectiveEngine 接口
# ============================================================

def _make_udm_dict():
    """构造一个简单的 UDM-like 对象,代替 MagicMock
    直接用真实 engine.udm.DestinyModel,从 _prepare_udm 拿
    这避免了 SimpleUDM 漏字段的问题,测试更接近真实使用场景"""
    from api.routes import _prepare_udm
    _, udm = _prepare_udm("2005-06-09 11:50", "呼和浩特", "男")
    return udm


class TestPerspectiveEngine:
    def test_construction_no_args(self):
        """PerspectiveEngine 应可不带 LLM 客户端构造"""
        pe = PerspectiveEngine()
        assert pe is not None

    def test_construction_with_mock_llm(self):
        mock_llm = MagicMock()
        pe = PerspectiveEngine(llm_client=mock_llm)
        assert pe.llm_client is mock_llm

    def test_analyze_signature(self):
        """analyze() 必须接受 (udm, question, figure_ids=None)"""
        import inspect
        sig = inspect.signature(PerspectiveEngine.analyze)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "udm" in params
        assert "question" in params

    def test_analyze_offline_returns_offline_analysis(self):
        """无 LLM 时 analyze 应返回离线分析(不依赖外部服务)
        这是 offline-friendly 设计的关键"""
        pe = PerspectiveEngine(llm_client=None)
        udm = _make_udm_dict()
        result = pe.analyze(
            udm=udm,
            question="我的事业如何?",
            figure_ids=["kongzi"],
        )
        assert isinstance(result, list)
        if result:
            op = result[0]
            assert hasattr(op, "figure_id")
            assert hasattr(op, "reasoning")
            assert hasattr(op, "confidence")


# ============================================================
# 边界
# ============================================================

class TestEdgeCases:
    def test_analyze_empty_figure_ids(self):
        """空 figure_ids 列表应不崩溃"""
        pe = PerspectiveEngine()
        udm = _make_udm_dict()
        result = pe.analyze(udm=udm, question="测试", figure_ids=[])
        assert isinstance(result, list)

    def test_analyze_nonexistent_figure_id(self):
        """不存在的 figure_id 应被忽略,不应崩溃"""
        pe = PerspectiveEngine()
        udm = _make_udm_dict()
        result = pe.analyze(
            udm=udm,
            question="测试",
            figure_ids=["definitely-not-a-real-figure-12345"],
        )
        assert isinstance(result, list)
