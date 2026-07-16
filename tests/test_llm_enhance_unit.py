"""Unit tests for LLM enhance helpers."""
from engine.report_engine import (
    _has_numeric_hallucination,
    _sanitize_natural_text,
    _build_enhance_prompt,
    _parse_llm_response,
    _section_natural_fallback,
)


def test_numeric_hallucination():
    h = _has_numeric_hallucination
    # 中文数字 + 数量级
    assert h("30 岁内可成") is True
    assert h("上亿身家") is True
    assert h("收入达 a 级") is True
    assert h("收入达 A 级") is True
    assert h("5000 万") is True
    assert h("年收入 100") is True
    assert h("5 万元") is True
    # 普通表述
    assert h("you may earn more this year") is False
    assert h("挣的钱按月发") is False
    assert h("这个判断偏稳") is False
    assert h("") is False
    print("[OK] _has_numeric_hallucination")


def test_sanitize():
    assert _sanitize_natural_text("").strip() == ""
    text = '```json\n{"a": 1}\n```'
    cleaned = _sanitize_natural_text(text)
    assert "```" not in cleaned
    long = "。".join(["一二三四五六七八九十"] * 50)
    truncated = _sanitize_natural_text(long, max_len=100)
    assert len(truncated) <= 110, f"got {len(truncated)}"
    print("[OK] _sanitize_natural_text")


def test_parse():
    assert _parse_llm_response({}) == {}
    parsed = _parse_llm_response({"verdict_natural": "v", "actions_natural": ["a", "b"]})
    assert parsed["verdict_natural"] == "v"
    parsed = _parse_llm_response({
        "raw_response": 'noise {"verdict_natural": "recovered", "actions_natural": ["c"]} more',
        "parse_error": True,
    })
    assert parsed.get("verdict_natural") == "recovered"
    print("[OK] _parse_llm_response")


def test_section_fallback():
    section = {"topic": "事业", "verdict": "原始", "actions": ["行动"]}
    _section_natural_fallback(section)
    assert section["verdict_natural"] == "原始"
    assert section["actions_natural"] == ["行动"]
    assert section["llm_fallback"] is True
    print("[OK] _section_natural_fallback")


def test_prompt_content():
    section = {
        "topic": "事业",
        "verdict": "适合借平台。",
        "evidence": ["身弱扛不住财官", "开门落艮"],
        "actions": ["找平台"],
        "confidence": 60,
        "counter_cases": ["006-cv-health-bias"],
        "method_sources": ["八字"],
        "debate": {"xuanzhao_synthesis": "走印运是黄金期", "key_quotes": ["撑得过去"]},
    }
    raw_signals = {
        "bazi": {"day_master": "甲木", "strength": "身弱", "xi": ["水"], "ji": ["土"]},
        "ziwei": {}, "astro": {}, "qimen": {}, "liuren": {}, "liuyao": {}, "taiyi": {}, "xingming": {},
    }
    prompt = _build_enhance_prompt(section, raw_signals)
    # 硬性要求(prompt 是中文无空格风格)
    for must in ["溟玄风格", "不能翻转方向", "几千万", "a级", "30岁内", "150-300", "verdict_natural", "actions_natural"]:
        assert must in prompt, f"prompt 缺:{must}"
    # 原始数据
    assert "身弱扛不住财官" in prompt
    assert "开门落艮" in prompt
    assert "撑得过去" in prompt
    assert "甲木" in prompt
    print("[OK] _build_enhance_prompt")


def test_direction_detection():
    """direction 标签(LLM 防翻案的核心机制)必须正确分类"""
    from engine.report_engine import _build_enhance_prompt

    # 偏谨慎类
    s1 = {"topic": "健康", "verdict": "亚健康倾向偏凶,不稳", "evidence": [], "actions": [],
          "confidence": 40, "counter_cases": [], "method_sources": [], "debate": {}}
    p = _build_enhance_prompt(s1, {"bazi": {"day_master": "甲", "strength": "?", "xi": [], "ji": []}})
    assert "偏谨慎" in p, "亚健康/偏凶 应判定为'偏谨慎'"

    # 偏积极类
    s2 = {"topic": "事业", "verdict": "适合借势,稳", "evidence": [], "actions": [],
          "confidence": 70, "counter_cases": [], "method_sources": [], "debate": {}}
    p = _build_enhance_prompt(s2, {"bazi": {"day_master": "甲", "strength": "?", "xi": [], "ji": []}})
    assert "偏积极" in p, "适合/稳 应判定为'偏积极'"

    # 中性
    s3 = {"topic": "学业", "verdict": "看具体学科", "evidence": [], "actions": [],
          "confidence": 50, "counter_cases": [], "method_sources": [], "debate": {}}
    p = _build_enhance_prompt(s3, {"bazi": {"day_master": "甲", "strength": "?", "xi": [], "ji": []}})
    assert "中性" in p
    print("[OK] direction 检测")


if __name__ == "__main__":
    test_numeric_hallucination()
    test_sanitize()
    test_parse()
    test_section_fallback()
    test_prompt_content()
    test_direction_detection()
    print("\n[ALL UNIT TESTS PASSED]")
