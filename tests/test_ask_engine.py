"""
玄照 v2.0 - ask_engine 单元测试

覆盖范围:
- 玄学概念知识库 CONCEPT_KB(>=30)
- 视角人物库 VIEWPOINT_KB(>=18)
- 关键词匹配 _match_concepts
- 主入口 ask()(knowledge / client 两种模式)
- 反向案例加载 _load_counter_cases_for_topic
- 客户命盘证据提取 _extract_evidence_from_chart
- 通用 warning 触发(财富类问题)
- 视角切换(单视角 / 多视角 / 默认视角)

不修改 ask_engine.py;不 mock 内部函数;真实 import。
"""
import os
import sys

import pytest

# 让 tests/ 能直接 import engine/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.ask_engine import (  # noqa: E402
    CONCEPT_KB,
    VIEWPOINT_KB,
    _extract_evidence_from_chart,
    _load_counter_cases_for_topic,
    _match_concepts,
    ask,
)


# ============== 通用 mock ==============

def make_chart():
    """最小可用的 chart_result mock,覆盖 _extract_evidence_from_chart 全部字段"""
    return {
        "bazi": {
            "day_master": "甲",
            "strength": "身旺",
            "xi_yong": {"xi": ["水", "木"], "ji": ["金"]},
            "geju": {"geju_type": "正官格"},
            "shensha": ["文昌", "桃花"],
            "dayun": [{"ganzhi": "甲子", "is_current": True}],
            "liunian": {"ganzhi": "丙午"},
            "year": "甲子",
            "month": "乙丑",
            "day": "丙寅",
            "time": "丁卯",
        }
    }


# ============== 知识库规模 ==============

class TestKnowledgeBaseSize:
    def test_concept_count(self):
        """CONCEPT_KB 至少 30 个键(规格要求)"""
        assert isinstance(CONCEPT_KB, dict)
        assert len(CONCEPT_KB) >= 30, f"CONCEPT_KB 只有 {len(CONCEPT_KB)} 个,要求 >=30"

    def test_viewpoint_count(self):
        """VIEWPOINT_KB 至少 18 个键(规格要求)"""
        assert isinstance(VIEWPOINT_KB, dict)
        assert len(VIEWPOINT_KB) >= 18, f"VIEWPOINT_KB 只有 {len(VIEWPOINT_KB)} 个,要求 >=18"


# ============== _match_concepts ==============

class TestMatchConcepts:
    def test_match_concepts_basic(self):
        """直接命中:问'身弱' → 命中 '身弱'"""
        hits = _match_concepts("我身弱怎么办")
        assert "身弱" in hits

    def test_match_concepts_synonym(self):
        """同义词:问'异性缘' → 命中 '桃花'"""
        hits = _match_concepts("我的异性缘如何")
        assert "桃花" in hits

    def test_match_concepts_year(self):
        """时间词:问'今年运势' → 命中 '流年'"""
        hits = _match_concepts("今年运势怎么样")
        assert "流年" in hits

    def test_match_concepts_no_hit(self):
        """无关问题:问'今天吃什么' → 命中空"""
        hits = _match_concepts("今天吃什么")
        assert hits == []

    def test_match_concepts_new_21(self):
        """7-27 扩充的 21 个概念 + 同义词都能命中(防回归 — CONCEPT_KB 加项但 syn 表忘挂)"""
        cases = [
            ("天乙", "天乙贵人"),
            ("文昌", "文昌贵人"),
            ("太极", "太极贵人"),
            ("天德", "天德贵人"),
            ("月德", "月德贵人"),
            ("将星入命", "将星"),
            ("亡神凶煞", "亡神"),
            ("劫煞来袭", "劫煞"),
            ("偏印", "枭神(偏印)"),
            ("枭神夺食", "枭神(偏印)"),
            ("倒食怎么解", "倒食"),
            ("比肩太多", "比肩"),
            ("劫财破财", "劫财"),
            ("正印护身", "正印"),
            ("长生位", "长生"),
            ("帝旺运", "帝旺"),
            ("墓库", "墓(库)"),
            ("绝处逢生", "绝"),
            ("胎元", "胎"),
            ("养命之源", "养"),
            ("纳音五行", "纳音"),
            ("六亲关系", "六亲"),
        ]
        for q, expected in cases:
            hits = _match_concepts(q)
            assert expected in hits, f"问'{q}'应命中'{expected}', 实际 hits={hits}"


# ============== ask() 主入口:模式与结构 ==============

class TestAskModes:
    def test_ask_knowledge_mode(self):
        """不传 chart_result → answer_mode == 'knowledge'"""
        r = ask("我身弱怎么办")
        assert r["answer_mode"] == "knowledge"

    def test_ask_client_mode(self):
        """传 chart_result → answer_mode == 'client',且产生 evidence 块"""
        chart = make_chart()
        r = ask("我身弱怎么办", chart_result=chart)
        assert r["answer_mode"] == "client"
        block_types = {b.get("type") for b in r["answer_blocks"]}
        assert "evidence" in block_types

    def test_ask_returns_blocks(self):
        """answer_blocks 是 list,每个块都有 type 字段"""
        r = ask("我身弱怎么办")
        assert isinstance(r["answer_blocks"], list)
        assert len(r["answer_blocks"]) > 0
        for blk in r["answer_blocks"]:
            assert isinstance(blk, dict)
            assert "type" in blk

    def test_ask_disclosure_4_items(self):
        """disclosure list 长度 >= 4"""
        r = ask("我身弱怎么办")
        assert isinstance(r["disclosure"], list)
        assert len(r["disclosure"]) >= 4

    def test_ask_confidence_range(self):
        """confidence ∈ [0, 100]"""
        r = ask("我身弱怎么办")
        assert isinstance(r["confidence"], int)
        assert 0 <= r["confidence"] <= 100


# ============== ask() 主入口:视角切换 ==============

class TestAskViewpoints:
    def test_ask_viewpoint_munger(self):
        """单视角:figures='munger' → viewpoint_used 含 munger"""
        r = ask("我身弱怎么办", figures="munger")
        assert "munger" in r["viewpoints_used"]

    def test_ask_viewpoint_multi(self):
        """多视角:figures='munger,naval' → viewpoint_used 同时含两个"""
        r = ask("我身弱怎么办", figures="munger,naval")
        assert "munger" in r["viewpoints_used"]
        assert "naval" in r["viewpoints_used"]

    def test_ask_default_viewpoints(self):
        """不传 figures → 用默认 5 个综合视角"""
        r = ask("我身弱怎么办")
        expected = {"munger", "laozi", "sunzi", "kahneman", "jung"}
        assert set(r["viewpoints_used"]) == expected


# ============== ask() 主入口:warning 与反向案例 ==============

class TestAskWarnings:
    def test_ask_warning_money(self):
        """问'我能赚多少' → 含 warning 块(不预测具体数字)"""
        r = ask("我能赚多少钱")
        warning_blocks = [b for b in r["answer_blocks"] if b.get("type") == "warning"]
        assert len(warning_blocks) >= 1
        # 关键承诺:不能预测具体数字
        joined = " ".join(b.get("text", "") for b in warning_blocks)
        assert "无法预测" in joined or "具体" in joined

    def test_counter_cases_loaded(self):
        """问'身弱' → 含 counter 类型块(反向案例自动加载)"""
        r = ask("我身弱怎么办")
        counter_blocks = [b for b in r["answer_blocks"] if b.get("type") == "counter"]
        assert len(counter_blocks) >= 1
        # 块里应该带 cases 列表
        for b in counter_blocks:
            assert isinstance(b.get("cases"), list)
            assert len(b["cases"]) > 0


# ============== 知识库字段完整性 ==============

class TestConceptKBIntegrity:
    def test_all_concepts_have_definition(self):
        """每个 CONCEPT_KB 概念都必须有 definition 字段"""
        for name, data in CONCEPT_KB.items():
            assert isinstance(data, dict), f"{name} 不是 dict"
            assert "definition" in data, f"{name} 缺 definition"
            assert isinstance(data["definition"], str)
            assert len(data["definition"]) > 0, f"{name} definition 为空"

    def test_all_concepts_have_confidence(self):
        """每个 CONCEPT_KB 概念都必须有 confidence 且 ∈ [0,100]"""
        for name, data in CONCEPT_KB.items():
            assert "confidence" in data, f"{name} 缺 confidence"
            assert isinstance(data["confidence"], (int, float))
            assert 0 <= data["confidence"] <= 100, (
                f"{name} confidence={data['confidence']} 越界"
            )


# ============== 客户命盘证据提取 ==============

class TestEvidenceExtract:
    def test_evidence_extract(self):
        """_extract_evidence_from_chart 正确提取 day_master / xi_yong / ji_shen"""
        chart = make_chart()
        ev = _extract_evidence_from_chart(chart)

        assert isinstance(ev, dict)
        # 必提字段
        assert ev["day_master"] == "甲"
        assert ev["xi_yong"] == ["水", "木"]
        assert ev["ji_shen"] == ["金"]
        # 配套字段也都该有
        assert "pillars" in ev
        assert ev["pillars"] == {
            "year": "甲子",
            "month": "乙丑",
            "day": "丙寅",
            "time": "丁卯",
        }
        assert ev["strength"] == "身旺"
        assert ev["geju"] == "正官格"
        assert ev["shensha_count"] == 2
        assert ev["current_dayun"]["ganzhi"] == "甲子"
        assert ev["liunian"]["ganzhi"] == "丙午"


# ============== 反向案例加载器 ==============

class TestLoadCounterCases:
    def test_load_counter_for_personality(self):
        """性格类话题能加载到反向案例(身弱 → 性格)"""
        cases = _load_counter_cases_for_topic("性格")
        assert isinstance(cases, list)
        assert len(cases) > 0
        # 每个 case 都应是 'filename: title' 形式
        for c in cases:
            assert ":" in c

    def test_load_counter_for_wealth(self):
        """财运类话题也能加载(财格 → 财运)"""
        cases = _load_counter_cases_for_topic("财运")
        assert isinstance(cases, list)
        # 不强制非空,但若非空应符合格式
        for c in cases:
            assert ":" in c

    def test_load_counter_unknown_topic(self):
        """未知话题返回空 list(不抛异常)"""
        cases = _load_counter_cases_for_topic("这个话题不存在_xyz")
        assert cases == []