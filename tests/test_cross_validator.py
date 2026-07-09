"""
玄照 v2.0 - 交叉验证引擎测试

覆盖:
- CrossValidator.validate(): 多术法结果比对, 找共识和冲突
- CrossValidator.generate_comprehensive_judgment(): 综合判断生成
- ConfidenceLevel / ConsensusItem / ConflictItem 数据类
- 类级常量 (ASPECTS, QIMEN_GONG_NAMES, WUXING_ORGAN)

梧 2026-07-09 指令: 一直补充
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.cross_validator import (
    CrossValidator,
    ConsensusItem,
    ConflictItem,
    ConfidenceLevel,
)


# ============================================================
# 数据结构测试
# ============================================================

class TestDataClasses:
    def test_confidence_level_values(self):
        """ConfidenceLevel 4 档: HIGH/MEDIUM/LOW/CONTRADICTORY"""
        assert ConfidenceLevel.HIGH.value == "高"
        assert ConfidenceLevel.MEDIUM.value == "中"
        assert ConfidenceLevel.LOW.value == "低"
        assert ConfidenceLevel.CONTRADICTORY.value == "矛盾"
        assert len(ConfidenceLevel) == 4

    def test_consensus_item_creation(self):
        item = ConsensusItem(
            aspect="性格",
            finding="主火",
            supporting_methods=["八字", "紫微"],
            confidence=ConfidenceLevel.HIGH,
        )
        assert item.aspect == "性格"
        assert item.confidence == ConfidenceLevel.HIGH
        assert len(item.supporting_methods) == 2

    def test_conflict_item_creation(self):
        item = ConflictItem(
            aspect="事业",
            method_a="八字",
            finding_a="官星旺",
            method_b="紫微",
            finding_b="无主星",
            suggestion="结合大运流年看",
        )
        assert item.method_a == "八字"
        assert item.method_b == "紫微"
        assert "大运" in item.suggestion


# ============================================================
# 类级常量
# ============================================================

class TestClassConstants:
    def test_aspects_count(self):
        """7 个维度: 性格/事业/财运/感情/健康/学业/人际关系"""
        assert len(CrossValidator.ASPECTS) == 7
        assert "性格" in CrossValidator.ASPECTS
        assert "事业" in CrossValidator.ASPECTS
        assert "财运" in CrossValidator.ASPECTS
        assert "健康" in CrossValidator.ASPECTS

    def test_qimen_gong_names_count(self):
        """奇门九宫 1-9 全有"""
        assert len(CrossValidator.QIMEN_GONG_NAMES) == 9
        assert CrossValidator.QIMEN_GONG_NAMES['5'] == '中五宫'
        assert CrossValidator.QIMEN_GONG_NAMES['1'] == '坎一宫'

    def test_wuxing_organ_coverage(self):
        """五行 → 脏腑映射 5 项"""
        assert len(CrossValidator.WUXING_ORGAN) == 5
        assert "肝" in CrossValidator.WUXING_ORGAN["木"]
        assert "心" in CrossValidator.WUXING_ORGAN["火"]
        assert "肾" in CrossValidator.WUXING_ORGAN["水"]

    def test_cs_constants_defined(self):
        """CS_STRONG / CS_WEAK / CS_DEVELOPING 等常量存在 (cross-validator 内部评分阈值)"""
        assert hasattr(CrossValidator, "CS_STRONG")
        assert hasattr(CrossValidator, "CS_WEAK")
        assert hasattr(CrossValidator, "CS_DEVELOPING")


# ============================================================
# 构造与基本行为
# ============================================================

class TestCrossValidatorBasic:
    def _make_udm_mock(self):
        """mock UDM 避免依赖完整引擎"""
        udm = MagicMock()
        udm.day_master = "甲"
        udm.day_master_wuxing = "木"
        udm.strength = "身强"
        udm.xi_yong = {"xi": ["水", "木"], "ji": ["土"]}
        return udm

    def test_construction(self):
        udm = self._make_udm_mock()
        cv = CrossValidator(udm)
        assert cv.udm is udm

    def test_validate_returns_dict(self):
        """validate() 必须返回 dict (含 consensus/conflicts/confidence)
        注意: validate() 不接受参数,从 self.udm 读取所有术法结果"""
        udm = self._make_udm_mock()
        # 提供完整的 mock UDM 字段,避免 magic mock 触发意外 bug
        udm.get_wuxing_count = lambda: {"木": 2, "火": 1, "土": 1, "金": 0, "水": 0}
        udm.qimen_chart = {"1": "test"}
        udm.ziwei_chart = None
        udm.astro_chart = None
        udm.liuren_chart = None
        udm.taiyi_chart = None
        udm.liuyao_chart = None
        udm.hidden_gans = {}
        udm.get_available_methods = lambda: ["八字", "紫微", "占星", "六爻", "奇门", "大六壬", "太乙"]
        cv = CrossValidator(udm)
        result = cv.validate()
        assert isinstance(result, dict)
        # 至少有 consensus 字段
        assert "consensus" in result
        assert "conflicts" in result
        assert "overall_confidence" in result

    def test_generate_comprehensive_judgment_exists(self):
        """综合判断方法必须存在并可调用"""
        udm = self._make_udm_mock()
        cv = CrossValidator(udm)
        # 不传实参,只看方法存在
        assert callable(cv.generate_comprehensive_judgment)
        assert callable(cv.validate)


# ============================================================
# 性能与代码规模测试
# ============================================================

class TestCodeHealth:
    """验证 cross_validator.py 没有灾难性问题"""

    def test_source_file_size(self):
        """cross_validator.py 应在合理大小 (300KB 内)
        实际: ~255KB / 4803 行,这是事实,不修文件只监控"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "engine/cross_validator.py",
        )
        size = os.path.getsize(path)
        assert size < 300_000, f"cross_validator.py 太大: {size} bytes"

    def test_unused_imports_minimal(self):
        """没有大量未使用的 import"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "engine/cross_validator.py",
        )
        content = open(path, encoding="utf-8").read()
        # 简单启发式: 找 import 行数和总行数比
        import_lines = [l for l in content.split("\n") if l.strip().startswith(("import ", "from "))]
        assert len(import_lines) < 30, f"cross_validator.py import 太多: {len(import_lines)}"