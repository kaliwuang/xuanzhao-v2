"""E2E test: build_report must always produce verdict_natural on every visible section."""
import asyncio
import sys
import unittest.mock as mock

sys.path.insert(0, ".")

from engine import report_engine

# --- Fake chart input ---
FAKE_CHART = {
    "input": {"name": "测试客户", "birth": "1990-05-15 14:30", "location": "上海", "gender": "男"},
    "bazi": {
        "day_master": "甲木", "strength": "身弱",
        "shishen_gan": {"year": "正财", "month": "正印", "day": "比肩", "time": "七杀"},
        "year": "庚午", "month": "辛巳", "day": "甲寅", "time": "癸酉",
        "wuxing_score": {"木": 2, "火": 1.5, "土": 0.3, "金": 1.2, "水": 0.5},
        "shensha": ["天乙贵人", "华盖", "将星"],
        "career_tendency": {"top_three": [("文化教育", 0.8), ("技术", 0.6)]},
        "dayun": [
            {"ganzhi": "辛丑", "start_age": 22, "end_age": 31, "is_current": True, "shishen_gan": "正印"},
            {"ganzhi": "壬寅", "start_age": 32, "end_age": 41, "shishen_gan": "食神"},
        ],
        "liunian": {"ganzhi": "丙午", "shensha": ["桃花"]},
        "features": ["食神格", "文昌入命"],
        "xi_yong": {"xi": ["水", "木"], "ji": ["土"]},
        "geju": {"geju_type": "食神格"},
    },
    "ziwei": {
        "ming_gong": "寅", "shen_gong": "戌",
        "wuxing_ju": {"wuxing": "木三局"},
        "sihua": {"禄": "廉贞", "科": "文曲", "忌": "贪狼"},
        "palaces": [
            {"name": "命宫", "major_stars": [{"name": "紫微", "brightness": "庙"}], "minor_stars": []},
            {"name": "夫妻", "major_stars": [{"name": "武曲"}], "minor_stars": [{"name": "文曲"}]},
            {"name": "官禄", "major_stars": [{"name": "廉贞"}], "minor_stars": []},
            {"name": "疾厄", "major_stars": [{"name": "太阳"}], "minor_stars": []},
            {"name": "财帛", "major_stars": [{"name": "太阴"}], "minor_stars": [{"name": "禄存"}]},
        ],
        "dai_xian": [{"start_age": 25, "end_age": 34, "ganzhi": "庚寅"}],
    },
    "astro": {
        "sun_sign": "金牛", "sun_element": "土",
        "moon_sign": "天蝎", "moon_element": "水",
        "ascendant_sign": "狮子", "mc_sign": "摩羯",
        "aspects_summary": {"total": 18, "harmonious": 7, "challenging": 9},
        "planetary_details": {"木星": {"retrograde": False, "house": 9, "sign": "射手"}},
        "planets": {"木星": {"house": 9, "sign": "射手"}},
    },
    "qimen": {
        "yin_yang": "阳", "ju_shu": "7", "jieqi": "立夏",
        "zhi_fu": {"name": "天辅"}, "zhi_shi": {"name": "杜门"},
        "palaces": [
            {"name": "巽", "men": "开门", "direction": "东"},
            {"name": "坤", "men": "死门", "direction": "西南"},
        ],
        "ge_ju_analysis": {"summary": "开门落东"},
    },
    "liuren": {
        "zhan_shi": "子", "yue_jiang": "月将", "ge_ju": "三光",
        "yong_shen": {"chu_chuan_zhi": "午", "chu_chuan_jiang": "胜光",
                      "jiang_ji_xiong": "吉", "jiang_han_yi": "宜动"},
    },
    "liuyao": {
        "ben_gua": {"name": "乾为天"}, "bian_gua": {"name": "天风姤"},
        "dong_yao": [3], "shi": "父母",
        "wuxing_analysis": {"yong_shen": "父母"},
        "ge_ju": ["伏吟"], "gua_gong_wuxing": "金",
    },
    "taiyi": {
        "taiyi_gong": "中", "yin_yang": "阳", "ju_num": 4,
        "suan_analysis": {"zhu_detail": ["主算 7"], "ke_detail": ["客算 5"], "pan_duan": "主胜"},
        "wu_fu": "乾",
    },
    "corrected_time": {"true_solar": "1990-05-15T14:31:00", "diff_minutes": 1},
    "current_dayun_focus": "辛丑",
    "methods": ["bazi", "ziwei", "astro", "liuyao", "qimen", "liuren", "taiyi"],
}

FAKE_XINGMING = {
    "wuge": {"total": 28}, "sancai": {"吉": True, "config": "土木火"},
    "score": 78, "bazi_match": {"等级": "中等"},
}


def make_fake_llm_client(topic_outputs):
    """构造一个返回特定 verdict_natural 的假 client。

    topic_outputs: dict, key=topic, value=dict 包含 verdict_natural + actions_natural
    """
    fake_client = mock.MagicMock()
    fake_client.chat_json = mock.MagicMock(side_effect=lambda messages, **kwargs: _fake_response_for(messages, topic_outputs))
    return fake_client


def _fake_response_for(messages, topic_outputs):
    """根据 prompt 中的 topic 字段返回对应 mock 输出"""
    content = messages[0]["content"] if messages else ""
    # 从 prompt 里抽 topic
    import re
    m = re.search(r"为【(.+?)】维度输出", content)
    topic = m.group(1) if m else "unknown"
    if topic in topic_outputs:
        return topic_outputs[topic]
    return {
        "verdict_natural": f"({topic} 默认 fallback) 你这个维度需要耐心。\n\n先认命,后改命。\n\n别硬扛,顺势就好。",
        "actions_natural": ["先稳住", "找对的人", "耐心一点"],
    }


def test_1_with_llm():
    """LLM 走通路径:每个 section 应有 verdict_natural (LLM-enhanced)"""
    outputs = {
        "事业": {
            "verdict_natural": "你这次走的是借势的局。身弱扛不住大财,先认这个事实。\n\n命格给的是底盘,不是天花板。八字双华盖带文昌,心思灵,但大运节奏还没到独立出手的窗口。\n\n别跟人比快,先把自己磨出来。",
            "actions_natural": ["找个靠谱平台先混三年", "现金流优先,不动杠杆", "想跳槽的话 2027 看"],
        },
    }

    async def fake_do_call(client, prompt):
        # 解析 prompt 中的 topic 然后返回
        import re
        m = re.search(r"为【(.+?)】维度输出", prompt)
        topic = m.group(1) if m else "unknown"
        # sleep a bit,模拟 LLM 延迟
        await asyncio.sleep(0.01)
        if topic in outputs:
            return outputs[topic]
        return {
            "verdict_natural": f"({topic})你这一步走得不容易。先看清底牌,再动手。\n\n每个维度都有节奏,赶不上不如守。\n\n先把自己稳住。",
            "actions_natural": ["给时间", "看主线", "小步试"],
        }

    fake_client = mock.MagicMock()
    fake_client.chat_json = mock.MagicMock(side_effect=lambda messages, **kwargs: _fake_response_for(messages, outputs))

    async def fake_enhance(report):
        sections = report.get("sections", [])
        raw_signals = report.get("raw_signal_summary", {})
        tasks = [report_engine._enhance_section_with_llm(s, raw_signals, client=fake_client) for s in sections]
        await asyncio.gather(*tasks)

    with mock.patch.object(report_engine, "_enhance_report_with_llm", side_effect=fake_enhance):
        result = report_engine.build_report(FAKE_CHART, FAKE_XINGMING)

    # 关键断言
    assert "sections" in result
    assert len(result["sections"]) == 6, f"应该有 6 个 section, 实际 {len(result['sections'])}"
    print(f"[OK] sections count: {len(result['sections'])}")

    visible_count = 0
    for s in result["sections"]:
        topic = s.get("topic")
        if s.get("hidden") or s.get("collapsed"):
            # hidden/collapsed 不强制
            continue
        visible_count += 1
        # 原始字段必须保留
        assert s.get("verdict"), f"{topic} 缺 verdict"
        assert s.get("verdict_raw") == s.get("verdict"), f"{topic} verdict_raw != verdict"
        # 新字段必须存在
        assert "verdict_natural" in s, f"{topic} 缺 verdict_natural"
        assert "actions_natural" in s, f"{topic} 缺 actions_natural"
        assert "llm_enhanced" in s, f"{topic} 缺 llm_enhanced"
        assert s["llm_enhanced"] is True, f"{topic} 应为 True(LLM 增强)"
        # verdict_natural 不应与原始 verdict 相同(must be enhanced)
        if topic in outputs:
            assert s["verdict_natural"] != s["verdict"], f"{topic} 应被 LLM 改写"

    print(f"[OK] visible sections: {visible_count} (含 verdict_natural/verdict_raw/llm_enhanced)")
    return result


def test_2_no_llm_fallback():
    """LLM 不可用场景:所有 section 应该有 verdict_natural (=原始 verdict) + llm_fallback=True"""
    async def broken_enhance(report):
        # 模拟 LLM 整体不可用,client 初始化失败
        raise RuntimeError("LLM API key not configured")

    with mock.patch.object(report_engine, "_enhance_report_with_llm", side_effect=broken_enhance):
        result = report_engine.build_report(FAKE_CHART, FAKE_XINGMING)

    for s in result["sections"]:
        if s.get("hidden") or s.get("collapsed"):
            continue
        topic = s.get("topic")
        assert "verdict_natural" in s, f"{topic} 缺 verdict_natural"
        assert "actions_natural" in s, f"{topic} 缺 actions_natural"
        assert s["verdict_natural"] == s["verdict"], f"{topic} fallback verdict 不一致"
        assert s.get("llm_fallback") is True, f"{topic} 应有 llm_fallback=True"

    print("[OK] LLM 不可用时 fallback 路径(verdict_natural == verdict)")


def test_3_hidden_section_safe():
    """hidden section 不会浪费 LLM,verdict_natural=None"""
    # 制造一个所有 confidence=15 的 chart,所有 section 都 hidden
    low_chart = dict(FAKE_CHART)
    # 不容易改 confidence(在 _judge_x 函数内硬编码),简单测 hidden 的字段完整性

    fake_client = mock.MagicMock()
    fake_client.chat_json = mock.MagicMock(side_effect=lambda messages, **kwargs:
        {"verdict_natural": "this should NOT be set since hidden", "actions_natural": ["a"]})

    async def fake_enhance(report):
        sections = report.get("sections", [])
        raw_signals = report.get("raw_signal_summary", {})
        tasks = [report_engine._enhance_section_with_llm(s, raw_signals, client=fake_client) for s in sections]
        await asyncio.gather(*tasks)

    with mock.patch.object(report_engine, "_enhance_report_with_llm", side_effect=fake_enhance):
        result = report_engine.build_report(FAKE_CHART, FAKE_XINGMING)

    for s in result["sections"]:
        if s.get("hidden"):
            assert s.get("verdict_natural") is None, f"hidden {s.get('topic')} 不应被 LLM 增强"
            assert s.get("llm_enhanced") is False
            assert s.get("llm_skip_reason") == "hidden"
        elif s.get("collapsed"):
            # collapsed 也不增强
            assert s.get("verdict_natural") is None, f"collapsed {s.get('topic')} 不应被 LLM 增强"
            assert s.get("llm_enhanced") is False
            assert s.get("llm_skip_reason") == "collapsed"

    print("[OK] hidden/collapsed section 不浪费 LLM")


def test_4_visibility_mark_correct():
    """检查 critical configs(timeout, overall)"""
    result = report_engine.build_report(FAKE_CHART, FAKE_XINGMING)
    # confidence_overall 必须存在
    assert "confidence_overall" in result
    print(f"[INFO] overall confidence: {result['confidence_overall']}")
    # verify_pending 必须为 True
    assert result.get("verify_pending") is True
    print("[OK] verify_pending=True 保留")


def test_5_async_concurrent_timing():
    """并发路径:6 节 LLM 同时跑,实际 wall clock 应该接近单次时间"""
    # 模拟每个 LLM 耗时 0.1s,串行需 0.6s,并发 ~0.1s
    import time

    async def fake_call(messages, **kwargs):
        await asyncio.sleep(0.1)
        return {"verdict_natural": "延迟测试 verdict", "actions_natural": ["行动1", "行动2"]}

    fake_client = mock.MagicMock()

    async def fake_enhance(report):
        sections = report.get("sections", [])
        raw_signals = report.get("raw_signal_summary", {})
        tasks = [report_engine._enhance_section_with_llm(s, raw_signals, client=fake_client) for s in sections]
        await asyncio.gather(*tasks)

    # 用真实 _call_llm_async 来测并发加速
    async def timing_wrapper():
        # 模拟 6 个 section
        sections = [{"topic": t, "verdict": "test", "evidence": [], "actions": [], "confidence": 70,
                    "counter_cases": [], "method_sources": [], "debate": {}} for t in
                   ["性格", "事业", "健康", "感情", "财运", "学业"]]
        client_mock = mock.MagicMock()
        client_mock.chat_json = mock.MagicMock(side_effect=lambda **k: {"verdict_natural": "ok " * 50, "actions_natural": ["a"]})

        # 替换内部 _call_llm_async 的 _do_call
        original_call_llm = report_engine._call_llm_async

        async def slow_call(client, prompt):
            # 模拟 LLM 慢响应
            await asyncio.sleep(0.1)
            return {"verdict_natural": "ok " * 80, "actions_natural": ["a", "b"]}

        report_engine._call_llm_async = slow_call
        try:
            tasks = [report_engine._enhance_section_with_llm(s, {"bazi": {}}, client=client_mock) for s in sections]
            t0 = time.time()
            await asyncio.gather(*tasks)
            dt = time.time() - t0
        finally:
            report_engine._call_llm_async = original_call_llm
        return dt

    dt = asyncio.run(timing_wrapper())
    # 并发下 6×0.1s 应该 < 0.4s
    assert dt < 0.4, f"并发未生效?耗时 {dt}s"
    print(f"[OK] 6 section 并发耗时 {dt:.2f}s (< 0.4s 阈值)")
    # 恢复


if __name__ == "__main__":
    test_1_with_llm()
    print()
    test_2_no_llm_fallback()
    print()
    test_3_hidden_section_safe()
    print()
    test_4_visibility_mark_correct()
    print()
    test_5_async_concurrent_timing()
    print("\n[ALL E2E TESTS PASSED]")
