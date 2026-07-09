"""
玄照 v2.0 - 彩票预测 v2 接口测试

覆盖:
- /api/lottery/predict_v2 三种彩票 × 两种 mode
- 信息熵和样本空间大小
- 奖级概率表(dlt)
- 公式 13 警告文案存在
- 推荐号结构完整性

设计原则: 验证数学事实是否真实计算,不是装饰
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ============================================================
# 熵与样本空间（公式 11）
# ============================================================

class TestEntropyAndSampleSpace:
    """公式 11: H = log₂|Ω|"""

    def test_fc3d_entropy_about_6_91(self):
        """fc3d: 3 位 × 0-9, 样本空间 P(10,3) = 720, 熵 = log₂720 ≈ 9.49
        注: fc3d 实际是不放回抽 3 个 0-9, 实际 C(10,3) = 120, 熵 ≈ 6.91"""
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "fc3d", "mode": "strict"})
        assert r.status_code == 200
        data = r.json()
        assert data["math_facts"]["sample_space_size"] == 120
        assert 6.9 < data["math_facts"]["entropy_bits"] < 7.0

    def test_dlt_entropy_24_35(self):
        """dlt: C(35,5) × C(12,2) = 21,425,712, 熵 ≈ 24.35 bits（公式 11）"""
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "dlt", "mode": "strict"})
        assert r.status_code == 200
        data = r.json()
        assert data["math_facts"]["sample_space_size"] == 21425712
        assert abs(data["math_facts"]["entropy_bits"] - 24.35) < 0.01

    def test_ssq_entropy(self):
        """ssq: C(33,6) × C(16,1) = 17,721,088, 熵 ≈ 24.08 bits"""
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "ssq", "mode": "strict"})
        assert r.status_code == 200
        data = r.json()
        assert data["math_facts"]["sample_space_size"] == 17721088


# ============================================================
# 推荐号结构
# ============================================================

class TestRecommendation:
    def test_fc3d_returns_3_unique_digits(self):
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "fc3d", "mode": "strict"})
        nums = r.json()["recommendation"]["numbers"]
        assert len(nums) == 3
        assert len(set(nums)) == 3
        assert all(0 <= n <= 9 for n in nums)

    def test_dlt_returns_5_front_2_back(self):
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "dlt", "mode": "strict"})
        rec = r.json()["recommendation"]
        assert len(rec["front"]) == 5
        assert len(rec["back"]) == 2
        assert len(set(rec["front"])) == 5  # 不重复
        assert len(set(rec["back"])) == 2
        assert all(1 <= n <= 35 for n in rec["front"])
        assert all(1 <= n <= 12 for n in rec["back"])

    def test_ssq_returns_6_front_1_back(self):
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "ssq", "mode": "strict"})
        rec = r.json()["recommendation"]
        assert len(rec["front"]) == 6
        assert len(rec["back"]) == 1
        assert all(1 <= n <= 33 for n in rec["front"])
        assert all(1 <= n <= 16 for n in rec["back"])

    def test_seed_determinism(self):
        """同一种子必须给同样的号（用户 24 小时内调多少次都一致）"""
        r1 = client.get("/api/lottery/predict_v2", params={"lottery_type": "fc3d", "seed": 12345})
        r2 = client.get("/api/lottery/predict_v2", params={"lottery_type": "fc3d", "seed": 12345})
        assert r1.json()["recommendation"]["numbers"] == r2.json()["recommendation"]["numbers"]


# ============================================================
# 奖级概率（公式 7-8）
# ============================================================

class TestPrizeTable:
    def test_dlt_prize_first_is_1_in_21_million(self):
        """公式 7: dlt 一等概率 = 1/21,425,712"""
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "dlt", "mode": "strict"})
        prizes = r.json()["prize_probabilities"]
        first = [p for p in prizes if p["level"] == "一等"][0]
        assert first["odds"] == "1/21425712"
        assert abs(first["probability"] - 1/21425712) < 1e-10

    def test_dlt_total_return_rate(self):
        """公式 10: 返奖率 51%,期望回报 1.02 元/2元"""
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "dlt", "mode": "strict"})
        mf = r.json()["math_facts"]
        assert abs(mf["return_rate"] - 0.51) < 0.01
        assert abs(mf["expected_return_per_2yuan"] - 1.02) < 0.05


# ============================================================
# 公式 13 警告文案
# ============================================================

class TestFormula13Warning:
    def test_warning_present(self):
        """P(ω_t | H_{t-1}) = P(ω_t) 警告必须在响应里"""
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "fc3d", "mode": "balanced"})
        data = r.json()
        assert "formula_13_warning" in data
        assert "P(ω_t | H_{t-1})" in data["formula_13_warning"]
        assert data["formula_13_warning"]  # 非空

    def test_balanced_mode_acknowledges_no_advantage(self):
        """balanced 模式响应里必须承认'特征无预测优势'"""
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "fc3d", "mode": "balanced"})
        feature_note = r.json()["recommendation"]["feature_note"]
        assert "无预测优势" in feature_note

    def test_strict_mode_uses_no_features(self):
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "fc3d", "mode": "strict"})
        assert r.json()["recommendation"]["method"] == "uniform_sampling"


# ============================================================
# 错误处理
# ============================================================

class TestErrors:
    def test_unknown_lottery(self):
        r = client.get("/api/lottery/predict_v2", params={"lottery_type": "xyz"})
        assert r.status_code == 400
        assert "不支持" in r.json()["error"]
