"""
玄照 · 行为验证问题库 + 校准
================================

为每个维度生成 2-3 个行为验证问题,客户回答后校准信心。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


# 问题库 — 每个问题独立,选项设计为不引导
# value 用于匹配;"match" 表示跟命理期望一致;"mismatch" 表示不一致
VERIFY_QUESTIONS = {
    "性格": [
        {
            "qid": "char_social_freq",
            "question": "不谈工作/学校必须,生活里一周跟不同人/朋友聊天,大概几天?",
            "evidence_match": "食神内秀/华盖孤高",
            "expected_signal": "内向低频",
            "weight": 0.3,
            "options": [
                {"label": "一周 4 天以上", "value": "high"},
                {"label": "一周 1-3 天", "value": "mid"},
                {"label": "一周不到 1 天", "value": "low"},
                {"label": "几乎不社交", "value": "very_low"},
            ],
            "match": ["low", "very_low"],  # 命理期望
            "note": "食神格身弱:典型社交低频",
        },
        {
            "qid": "char_expression",
            "question": "表达东西(想法、感受、记录),说和写哪个更多?",
            "evidence_match": "食神制杀/七杀藏时柱",
            "expected_signal": "写多于说",
            "weight": 0.3,
            "options": [
                {"label": "说为主,写字为辅", "value": "speak"},
                {"label": "写字为主,说为辅", "value": "write"},
                {"label": "两者差不多", "value": "equal"},
                {"label": "都不太做", "value": "neither"},
            ],
            "match": ["write", "equal"],  # 食神/七杀格都偏写
            "note": "食神制杀:写 > 说,慢热型",
        },
        {
            "qid": "char_decision",
            "question": "做决定时,你更偏哪种?",
            "evidence_match": "食神格/身弱",
            "expected_signal": "想后才做",
            "weight": 0.2,
            "options": [
                {"label": "想清楚才做,边做边调", "value": "think_first"},
                {"label": "先动,错了再调", "value": "act_first"},
                {"label": "拖到最后才决定", "value": "delay"},
                {"label": "问人/看别人怎么做", "value": "ask_others"},
            ],
            "match": ["think_first", "delay"],
            "note": "食神格/身弱:慢热,想后才做",
        },
    ],

    "事业": [
        {
            "qid": "career_independence",
            "question": "你现在的工作/学业状态是?",
            "evidence_match": "身弱+食神/印星",
            "expected_signal": "团队/平台/被指导",
            "weight": 0.3,
            "options": [
                {"label": "完全独立(自己接活/创业/自由职业)", "value": "independent"},
                {"label": "团队核心(合伙/小团队负责人)", "value": "team_lead"},
                {"label": "团队成员(进公司/跟项目/读研跟导师)", "value": "team_member"},
                {"label": "还在读书/还在学习阶段", "value": "student"},
            ],
            "match": ["team_member", "student"],
            "note": "身弱+食神:借势,不在独立阶段",
        },
        {
            "qid": "career_response_to_failure",
            "question": "工作/项目搞砸了,你通常?",
            "evidence_match": "七杀格/身弱",
            "expected_signal": "先自己扛/想清楚",
            "weight": 0.2,
            "options": [
                {"label": "立刻找人讨论/求助", "value": "ask_immediately"},
                {"label": "自己想清楚再决定要不要说", "value": "think_then_decide"},
                {"label": "先自己扛,扛不住再说", "value": "carry_alone"},
                {"label": "回避/装作没事", "value": "avoid"},
            ],
            "match": ["think_then_decide", "carry_alone"],
            "note": "身弱+食神:不轻易暴露,但不会硬撑",
        },
    ],

    "健康": [
        {
            "qid": "health_real_signal",
            "question": "过去一年里,身体实际有过的真信号(选最明显的)",
            "evidence_match": "五行过旺/死门落宫",
            "expected_signal": "对应位置信号",
            "weight": 0.3,
            "options": [
                {"label": "肠胃/消化", "value": "stomach"},
                {"label": "腰椎/脊椎/肩膀", "value": "spine"},
                {"label": "皮肤/过敏", "value": "skin"},
                {"label": "睡眠(入睡难/半夜醒)", "value": "sleep"},
                {"label": "头晕/心悸/呼吸", "value": "head_heart"},
                {"label": "都没明显问题", "value": "none"},
            ],
            "match": [],  # 健康问题不预设期望 — 让真实信号浮出来
            "note": "真实信号 > 命理推断",
        },
        {
            "qid": "health_pattern",
            "question": "如果有信号,主要在什么情况下出现?",
            "evidence_match": "五行生克/死门宫位",
            "expected_signal": "压力相关",
            "weight": 0.2,
            "options": [
                {"label": "压力大/焦虑时", "value": "stress"},
                {"label": "换季/天气变化", "value": "season"},
                {"label": "吃错东西/不规律", "value": "food"},
                {"label": "规律出现(每月/每周)", "value": "regular"},
                {"label": "看不出来", "value": "unknown"},
                {"label": "没信号", "value": "none"},
            ],
            "match": [],
            "note": "规律性 vs 触发性 — 影响健康建议方向",
        },
    ],

    "感情": [
        {
            "qid": "love_current_state",
            "question": "现在感情状态是?",
            "evidence_match": "流年桃花/红鸾/财星",
            "expected_signal": "有对象",
            "weight": 0.3,
            "options": [
                {"label": "现在有对象,在谈", "value": "dating"},
                {"label": "心里有人但没说", "value": "crush"},
                {"label": "今年刚开始/已经结束一段", "value": "recent"},
                {"label": "单身,没动心", "value": "single"},
            ],
            "match": ["dating", "recent"],  # 桃花+红鸾流年:有缘分
            "note": "2026 丙午流年桃花+红鸾",
        },
        {
            "qid": "love_partner_style",
            "question": "你的对象/心动对象更接近哪种?",
            "evidence_match": "紫微夫妻宫/八字配偶星",
            "expected_signal": "文雅/务实型",
            "weight": 0.2,
            "options": [
                {"label": "安静理性,读书多", "value": "scholar"},
                {"label": "活泼外向,爱社交", "value": "social"},
                {"label": "务实,做事靠谱", "value": "practical"},
                {"label": "艺术/创作型", "value": "artistic"},
                {"label": "还没对象", "value": "none"},
            ],
            "match": ["scholar", "practical", "artistic"],
            "note": "紫微夫妻宫武曲/文曲组合 → 文雅+务实",
        },
    ],

    "财运": [
        {
            "qid": "wealth_pattern",
            "question": "你目前的收入/资金状态是?",
            "evidence_match": "身弱+财格",
            "expected_signal": "稳定但不大",
            "weight": 0.3,
            "options": [
                {"label": "稳定(工资/家里给/奖学金)", "value": "stable"},
                {"label": "波动(项目/接活/家里有时给有时不给)", "value": "fluctuate"},
                {"label": "紧张(收入不够花)", "value": "tight"},
                {"label": "还在读书/没独立收入", "value": "none"},
            ],
            "match": ["stable", "fluctuate", "none"],
            "note": "身弱财格:稳定 > 大波动",
        },
        {
            "qid": "wealth_decision",
            "question": "花钱时,你更偏哪种?",
            "evidence_match": "食神泄秀/身弱",
            "expected_signal": "想清楚再花",
            "weight": 0.2,
            "options": [
                {"label": "想清楚再花", "value": "think_spend"},
                {"label": "感觉对了就花", "value": "impulse"},
                {"label": "该花花,该省省", "value": "balanced"},
                {"label": "看心情", "value": "mood"},
            ],
            "match": ["think_spend", "balanced"],
            "note": "身弱+食神:理性消费",
        },
    ],

    "学业": [
        {
            "qid": "study_current",
            "question": "你现在学业状态是?",
            "evidence_match": "文昌/华盖/紫微化科",
            "expected_signal": "正在读",
            "weight": 0.3,
            "options": [
                {"label": "本科在读", "value": "undergrad"},
                {"label": "硕士在读", "value": "master"},
                {"label": "博士在读", "value": "phd"},
                {"label": "已经工作", "value": "work"},
                {"label": "gap year/休学", "value": "gap"},
            ],
            "match": ["undergrad", "master", "phd"],
            "note": "学业维度: 当前在读才有意义",
        },
        {
            "qid": "study_direction",
            "question": "你的专业/兴趣方向更接近?",
            "evidence_match": "八字倾向/紫微化科",
            "expected_signal": "文科性",
            "weight": 0.2,
            "options": [
                {"label": "文学/哲学/历史/心理学", "value": "humanities"},
                {"label": "艺术/设计/音乐", "value": "arts"},
                {"label": "商科/经济/管理", "value": "business"},
                {"label": "理工/计算机/工程", "value": "stem"},
                {"label": "医学/法律", "value": "professional"},
                {"label": "还没定", "value": "undecided"},
            ],
            "match": ["humanities", "arts"],
            "note": "八字食神/紫微化科 → 文科性方向",
        },
    ],
}


def get_verify_questions(topic: str) -> List[Dict]:
    """获取某维度的验证问题"""
    return VERIFY_QUESTIONS.get(topic, [])


def calibrate_confidence(section: Dict, answers: Dict[str, str]) -> Dict:
    """
    根据客户回答,校准每个维度的信心分

    Args:
        section: report_engine 输出的单个维度 dict(含 verdict, evidence, confidence 等)
        answers: {qid: value} 客户的回答

    Returns:
        校准后的 section (in-place 修改 + 添加 verify_result 字段)
    """
    topic = section.get("topic")
    questions = get_verify_questions(topic)

    if not questions:
        return section

    matches = 0
    mismatches = 0
    neutral = 0
    total_weight = 0
    matched_weight = 0

    verify_log = []

    for q in questions:
        qid = q["qid"]
        ans = answers.get(qid)
        if not ans:
            continue

        weight = q.get("weight", 0.2)
        total_weight += weight

        is_match = ans in q.get("match", [])
        match_list = q.get("match", [])

        if not match_list:
            # 这个问题的设计是收集真实信号,不预设期望
            neutral += 1
            verify_log.append({
                "qid": qid,
                "question": q["question"],
                "answer": ans,
                "expected": "(无预设)",
                "result": "info",  # info 表示只是收集信号
            })
        elif is_match:
            matches += 1
            matched_weight += weight
            verify_log.append({
                "qid": qid,
                "question": q["question"],
                "answer": ans,
                "expected": "/".join(match_list),
                "result": "match",
            })
        else:
            mismatches += 1
            verify_log.append({
                "qid": qid,
                "question": q["question"],
                "answer": ans,
                "expected": "/".join(match_list),
                "result": "mismatch",
            })

    # 信心校准
    old_conf = section.get("confidence", 60)
    new_conf = old_conf

    if total_weight > 0:
        match_ratio = matched_weight / total_weight

        if match_ratio >= 0.7:
            # 大部分匹配 → 升一档 (+5-15)
            boost = int(15 * match_ratio)
            new_conf = min(95, old_conf + boost)
            verify_status = "confirmed"
        elif match_ratio >= 0.4:
            # 部分匹配 → 持平
            new_conf = old_conf
            verify_status = "partial"
        else:
            # 多数不匹配 → 降一档 (-10-20)
            drop = int(15 * (1 - match_ratio))
            new_conf = max(20, old_conf - drop)
            verify_status = "mismatch"

        # 警告:有信息收集类问题且出现冲突(比如健康"都没问题"vs 命理推断"火旺心血管弱")
        info_answers = [a for a in verify_log if a.get("result") == "info"]
        if info_answers and mismatches >= 1:
            new_conf = max(20, new_conf - 10)
            verify_status = "info_conflict"

    else:
        verify_status = "no_answers"

    # 修改 section
    section["confidence"] = new_conf
    section["confidence_delta"] = new_conf - old_conf
    section["verify_status"] = verify_status
    section["verify_log"] = verify_log
    section["verify_summary"] = {
        "matches": matches,
        "mismatches": mismatches,
        "neutral": neutral,
        "total_questions": len(questions),
    }

    # 证据更新:加验证标签
    if verify_status == "confirmed":
        section["evidence"].append(f"✅ 行为验证: {matches}/{matches+mismatches} 匹配命理期望")
    elif verify_status == "mismatch":
        section["evidence"].append(f"⚠️ 行为验证冲突: {mismatches}/{matches+mismatches} 不匹配 — 命理推断待修正")
        section["actions"].insert(0, "⚠️ 行为信号跟命理推断不符,建议复盘")
    elif verify_status == "info_conflict":
        section["evidence"].append(f"⚠️ 真实行为信号缺失(可能没有真信号),命理推断存疑")

    return section