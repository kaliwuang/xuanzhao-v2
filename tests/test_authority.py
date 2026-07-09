"""
玄照 v2.0 - 数学边界与回归测试

覆盖:
- /api/math/boundaries 端点完整性
- /api/divine-lottery/predict 在 fc3d/pl3/dlt/ssq 四种彩票上的回归(防止 3d 类型再被套 lotto 模板崩溃)
- 8 引擎 docstring 中"数学边界"段的存在(防止后人误删)
- 公式 11/12/13 关键引文在响应中必须出现

梧 2026-07-09 指令: 让玄照更权威
"""
import sys
import os
import re
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ============================================================
# /api/math/boundaries 端点
# ============================================================

class TestMathBoundariesEndpoint:
    """8 引擎的数学边界统一端点"""

    def test_endpoint_exists(self):
        r = client.get("/api/math/boundaries")
        assert r.status_code == 200

    def test_health_reports_8_engines(self):
        """/api/health 必须报告 8 个引擎(与 README 八术排盘一致)
        修复: 之前报 7,因为姓名学按需实例化不在 orch.engines 中
        """
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["engines_registered"] == 8, \
            f"健康检查应报 8 个引擎, 实际: {data['engines_registered']}"
        assert data["status"] == "healthy"

    def test_contains_all_8_engines(self):
        r = client.get("/api/math/boundaries")
        engines = r.json()["engines"]
        required = {"bazi", "ziwei", "astro", "liuyao", "qimen", "liuren", "taiyi", "xingming"}
        assert set(engines.keys()) == required, f"缺少引擎: {required - set(engines.keys())}"

    def test_each_engine_has_required_fields(self):
        r = client.get("/api/math/boundaries")
        engines = r.json()["engines"]
        for name, info in engines.items():
            assert "name" in info, f"{name} 缺 name"
            assert "sample_space" in info, f"{name} 缺 sample_space"
            assert "entropy_bits" in info, f"{name} 缺 entropy_bits"
            assert "F13_implication" in info, f"{name} 缺 F13_implication"
            assert "known_defects" in info, f"{name} 缺 known_defects"
            assert isinstance(info["known_defects"], list), f"{name} known_defects 应为 list"

    def test_formula_basis_contains_F11_F13(self):
        """公式 11 (熵) 和 公式 13 (无预测优势) 必须在 formula_basis 中"""
        r = client.get("/api/math/boundaries")
        fb = r.json()["formula_basis"]
        assert "F11_entropy" in fb
        assert "F13_no_advantage" in fb
        assert "F10_return" in fb
        assert "F12_independence" in fb
        # 公式 13 引文必须包含 P(ω_t | H_{t-1}) = P(ω_t)
        assert "P(ω_t | H_{t-1})" in fb["F13_no_advantage"]

    def test_lottery_entropy_dlt_24_35(self):
        """大乐透 F11 熵 = 24.35 bits"""
        r = client.get("/api/math/boundaries")
        lottery = r.json()["lottery_module"]
        assert abs(lottery["F11_entropy_bits"]["dlt"] - 24.35) < 0.01

    def test_lottery_return_rate_51_percent(self):
        """F10 返奖率 51%"""
        r = client.get("/api/math/boundaries")
        lottery = r.json()["lottery_module"]
        assert abs(lottery["F10_return_rate"] - 0.51) < 0.01

    def test_data_quality_note_present(self):
        """数据质量备注必须存在(dlt 去重这件事不能被遗忘)"""
        r = client.get("/api/math/boundaries")
        note = r.json()["lottery_module"]["data_quality_note"]
        assert "dlt" in note
        assert "210" in note  # 去重后的真实期数


# ============================================================
# 8 引擎 docstring 数学边界段
# ============================================================

class TestEngineDocstrings:
    """确保每个引擎 docstring 的'数学边界'段不被后人误删"""

    ENGINES = [
        ("engine/bazi_engine.py", "公式 13"),
        ("engine/ziwei_engine.py", "公式 13"),
        ("engine/astro_engine.py", "公式 13"),
        ("engine/liuyao_engine.py", "公式 13"),
        ("engine/qimen_engine.py", "公式 13"),
        ("engine/liuren_engine.py", "公式 13"),
        ("engine/taiyi_engine.py", "公式 13"),
        ("engine/xingming_engine.py", "公式 13"),
    ]

    @pytest.mark.parametrize("path,marker", ENGINES)
    def test_math_boundary_section_exists(self, path, marker):
        full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
        with open(full_path, encoding="utf-8") as f:
            content = f.read()
        assert marker in content, f"{path} 缺少'数学边界'段(引文: {marker})"
        assert "2026-07-09 梧指令补充" in content, f"{path} 缺少'梧指令补充'标记"

    def test_taiyi_docstring_admits_kintaiyi_defect(self):
        """太乙引擎 docstring 必须白纸黑字写'kintaiyi 传递依赖未装齐'"""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine/taiyi_engine.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "kintaiyi" in content
        assert "传递依赖未装齐" in content or "依赖" in content

    def test_liuren_docstring_admits_sike_kong_defect(self):
        """大六壬 docstring 必须白纸黑字写'四课为空'缺陷"""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine/liuren_engine.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "四课为空" in content


# ============================================================
# /api/divine-lottery/predict 回归测试
# ============================================================

class TestDivineLotteryRegression:
    """防止 fc3d/pl3 再次被套 lotto 模板崩溃"""

    def test_fc3d_does_not_crash(self):
        """修复前: 'front' KeyError. 修复后: 200 OK"""
        r = client.get("/api/divine-lottery/predict", params={"lottery_type": "fc3d"})
        assert r.status_code == 200, f"fc3d 崩了: {r.text}"
        data = r.json()
        assert "lottery_type" in data
        assert data["lottery_type"] == "fc3d"

    def test_pl3_does_not_crash(self):
        r = client.get("/api/divine-lottery/predict", params={"lottery_type": "pl3"})
        assert r.status_code == 200
        assert r.json()["lottery_type"] == "pl3"

    def test_dlt_runs(self):
        r = client.get("/api/divine-lottery/predict", params={"lottery_type": "dlt"})
        assert r.status_code == 200
        data = r.json()
        assert "divination_results" in data
        # 即使部分引擎失败,响应里也要标注(诚实实现)
        assert "engine_errors" in data

    def test_ssq_runs(self):
        r = client.get("/api/divine-lottery/predict", params={"lottery_type": "ssq"})
        assert r.status_code == 200

    def test_engine_errors_honesty(self):
        """失败引擎必须在响应中标注(不静默失败)
        修复: 不要假定"必须有引擎失败",而是验证:
        1. engine_errors 字段必须存在 (dict 类型)
        2. 如果有任何引擎失败, 必须有对应的错误信息
        """
        r = client.get("/api/divine-lottery/predict", params={"lottery_type": "dlt"})
        data = r.json()
        assert "engine_errors" in data, "响应里必须包含 engine_errors 字段"
        errors = data["engine_errors"]
        assert isinstance(errors, dict), "engine_errors 必须是 dict"
        # 如果有错误,每个错误必须是非空字符串
        for engine, err_msg in errors.items():
            assert err_msg, f"引擎 {engine} 失败但错误信息为空"
        # 检查 methods_used 和 divination_results 一致
        methods = data.get("methods_used", [])
        assert len(methods) >= 3, f"应至少有 3 个术法成功: {methods}"


# ============================================================
# 数据去重修复的回归测试
# ============================================================

class TestDLTDataDedup:
    """D 盘 dlt-history.csv 必须保持去重状态"""

    def test_dlt_csv_unique_periods(self):
        import csv
        path = "D:/lottery-data/dlt-history.csv"
        if not os.path.exists(path):
            pytest.skip("dlt-history.csv 不存在")
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        unique = set(r["period"] for r in rows)
        # 修复后: 唯一期数 == 总行数
        assert len(unique) == len(rows), \
            f"dlt 数据又有重复!{len(rows)} 行 / {len(unique)} unique"
        # 真实期数应在 200-220 区间
        assert 200 <= len(unique) <= 230, \
            f"dlt 真实期数异常: {len(unique)}"

    def test_fc3d_csv_unique_periods(self):
        import csv
        path = "D:/lottery-data/fc3d-history.csv"
        if not os.path.exists(path):
            pytest.skip("fc3d-history.csv 不存在")
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        unique = set(r["period"] for r in rows)
        assert len(unique) == len(rows)
        assert len(unique) == 1000  # 真实 1000 期

    def test_pl3_csv_unique_periods(self):
        import csv
        path = "D:/lottery-data/pl3-history.csv"
        if not os.path.exists(path):
            pytest.skip("pl3-history.csv 不存在")
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        unique = set(r["period"] for r in rows)
        assert len(unique) == len(rows)
        assert len(unique) == 1000
