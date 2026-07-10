"""
玄照 v2.0 - predict_hybrid 接口测试

覆盖(基于 [[xuanzhao-lottery-ethics-2026-07-09]]):
- 接口存在且返回 200
- formula_path / divine_path 都包含完整字段
- hybrid_disclaimer 必须显式说明公式 13 (合并不产生预测优势)
- overlap_observation 解释字段必须澄清巧合不是数学意义
- mode 必须为 hybrid_celebration
- 公式版 + 八术法版并行调用,不"合并"成第三套号

设计原则: 验证合规,不是验证"预测能力"(数学上不存在)
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════
# 1. 接口可访问 + 基本结构
# ═══════════════════════════════════════════════════════════

class TestHybridBasic:
    """接口基础可用性"""

    def test_hybrid_endpoint_exists_dlt(self):
        """dlt hybrid 接口存在"""
        r = client.get("/api/divine-lottery/predict_hybrid", params={
            "lottery_type": "dlt",
            "target_date": "2026-07-11",
            "target_hour": 21,
        })
        assert r.status_code == 200, f"got {r.status_code}"

    def test_hybrid_endpoint_exists_fc3d(self):
        """fc3d hybrid 接口存在"""
        r = client.get("/api/divine-lottery/predict_hybrid", params={
            "lottery_type": "fc3d",
            "target_date": "2026-07-10",
            "target_hour": 21,
        })
        assert r.status_code == 200

    def test_hybrid_invalid_lottery(self):
        """非法彩种返回 400"""
        r = client.get("/api/divine-lottery/predict_hybrid", params={
            "lottery_type": "xxx",
        })
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════
# 2. 输出结构完整性
# ═══════════════════════════════════════════════════════════

class TestHybridStructure:
    """输出结构完整性 — 两个独立路径都存在,不被合并"""

    @pytest.fixture
    def hybrid_dlt(self):
        r = client.get("/api/divine-lottery/predict_hybrid", params={
            "lottery_type": "dlt",
            "target_date": "2026-07-11",
            "target_hour": 21,
        })
        return r.json()

    def test_mode_is_hybrid_celebration(self, hybrid_dlt):
        """mode 字段必须明确是 hybrid_celebration,避免跟主接口混淆"""
        assert hybrid_dlt.get("mode") == "hybrid_celebration"

    def test_formula_path_present(self, hybrid_dlt):
        """公式版结果必须独立存在"""
        fp = hybrid_dlt.get("formula_path", {})
        assert fp, "formula_path 缺失"
        assert fp.get("endpoint") == "/api/lottery/predict_v2"
        rec = fp.get("recommendation", {})
        assert rec.get("front"), "前区缺失"
        assert rec.get("back"), "后区缺失"
        assert fp.get("math_facts", {}).get("sample_space_size") == 21425712

    def test_divine_path_present(self, hybrid_dlt):
        """八术法版结果必须独立存在"""
        dp = hybrid_dlt.get("divine_path", {})
        assert dp, "divine_path 缺失"
        assert dp.get("endpoint") == "/api/divine-lottery/predict"
        assert dp.get("methods_used"), "methods_used 缺失"
        assert "consensus" in dp

    def test_no_merged_third_set(self, hybrid_dlt):
        """关键:不输出'合并'的第三套号"""
        d = hybrid_dlt
        # 不应该有 "merged_recommendation" / "hybrid_pick" / "final_pick" 等
        forbidden = ["merged", "hybrid_pick", "final_pick", "combined_recommendation"]
        for k in forbidden:
            assert k not in d, f"不应出现合并字段: {k}"


# ═══════════════════════════════════════════════════════════
# 3. Disclaimer 完整性 (伦理红线)
# ═══════════════════════════════════════════════════════════

class TestHybridDisclaimer:
    """强 disclaimer 必须存在且包含公式 13"""

    @pytest.fixture
    def hybrid_dlt(self):
        r = client.get("/api/divine-lottery/predict_hybrid", params={
            "lottery_type": "dlt",
            "target_date": "2026-07-11",
            "target_hour": 21,
        })
        return r.json()

    def test_hybrid_disclaimer_exists(self, hybrid_dlt):
        """hybrid 专属 disclaimer 必须存在"""
        disc = hybrid_dlt.get("hybrid_disclaimer", "")
        assert disc, "hybrid_disclaimer 缺失"

    def test_hybrid_disclaimer_mentions_formula_13(self, hybrid_dlt):
        """hybrid disclaimer 必须引用公式 13"""
        disc = hybrid_dlt.get("hybrid_disclaimer", "")
        assert "公式 13" in disc or "P(ω_t | H" in disc, \
            "hybrid disclaimer 必须包含公式 13"

    def test_hybrid_disclaimer_explains_no_synergy(self, hybrid_dlt):
        """hybrid disclaimer 必须明确说明合并无协同优势"""
        disc = hybrid_dlt.get("hybrid_disclaimer", "")
        assert "合并" in disc and "仪式" in disc, \
            "hybrid disclaimer 必须解释合并的目的(仪式 vs 预测优势)"

    def test_formula_disclaimer_kept(self, hybrid_dlt):
        """公式版自身 disclaimer 必须保留"""
        fp_disc = hybrid_dlt.get("formula_path", {}).get("disclaimer", "")
        assert "无法提供超越随机基线的预测优势" in fp_disc

    def test_divine_disclaimer_kept(self, hybrid_dlt):
        """八术法版自身 disclaimer 必须保留"""
        dp_disc = hybrid_dlt.get("divine_path", {}).get("disclaimer", "")
        assert dp_disc, "divine disclaimer 缺失"


# ═══════════════════════════════════════════════════════════
# 4. Overlap observation 边界(防止误读为"协同优势")
# ═══════════════════════════════════════════════════════════

class TestHybridOverlap:
    """重叠观察字段必须明确边界"""

    @pytest.fixture
    def hybrid_dlt(self):
        r = client.get("/api/divine-lottery/predict_hybrid", params={
            "lottery_type": "dlt",
            "target_date": "2026-07-11",
            "target_hour": 21,
        })
        return r.json()

    def test_overlap_field_exists(self, hybrid_dlt):
        """overlap_observation 字段必须存在"""
        ov = hybrid_dlt.get("overlap_observation", {})
        assert ov, "overlap_observation 缺失"

    def test_overlap_includes_interpretation(self, hybrid_dlt):
        """overlap 必须包含 interpretation 字段明确说'巧合不是数学意义'"""
        ov = hybrid_dlt.get("overlap_observation", {})
        interp = ov.get("interpretation", "")
        assert "巧合" in interp or "不是数学意义" in interp or "公式 13" in interp, \
            "overlap 必须解释这是巧合不是数学意义"

    def test_overlap_common_numbers_is_list(self, hybrid_dlt):
        """common_numbers 必须是 list (即使空)"""
        ov = hybrid_dlt.get("overlap_observation", {})
        assert isinstance(ov.get("common_numbers"), list)


# ═══════════════════════════════════════════════════════════
# 5. 跨彩种兼容性
# ═══════════════════════════════════════════════════════════

class TestHybridCrossLottery:
    """4 个彩种都能跑"""

    @pytest.mark.parametrize("lottery_type,target_date", [
        ("fc3d", "2026-07-10"),
        ("pl3", "2026-07-10"),
        ("dlt", "2026-07-11"),
        ("ssq", "2026-07-12"),
    ])
    def test_hybrid_all_lottery_types(self, lottery_type, target_date):
        r = client.get("/api/divine-lottery/predict_hybrid", params={
            "lottery_type": lottery_type,
            "target_date": target_date,
            "target_hour": 21,
        })
        assert r.status_code == 200, f"{lottery_type} got {r.status_code}"
        d = r.json()
        # 共同检查
        assert d.get("mode") == "hybrid_celebration"
        assert d.get("formula_path", {}).get("recommendation")
        assert d.get("divine_path", {}).get("consensus")
        assert d.get("hybrid_disclaimer")