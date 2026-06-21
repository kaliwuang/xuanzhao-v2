#!/usr/bin/env python3
"""
玄照 v2.0 - 辩论引擎 v2

108人全员参与辩论，零LLM调用（仅玄照综合视角用1次LLM）。

机制：
1. 108人按阵营排序轮流发言
2. 每人发言时可读到前面所有人的发言记录
3. 关键词冲突检测：如果当前发言与某未发言者立场对立，该人插队发言
4. 术法交叉验证：同术法内部分歧自动标记
5. 共识/分歧自动提取
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from .perspective_engine import PerspectiveOpinion, FIGURES
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class Exchange:
    round_num: int
    speaker: str
    speaker_method: str
    target: str
    target_method: str
    argument: str
    rebuttal_type: str


# 对立立场关键词组
OPPOSING_GROUPS = [
    (["动", "进", "突破", "断", "胜", "拼", "冲", "攻", "果断", "积极", "奋起", "勇"],
     ["稳", "守", "防", "静", "韬", "隐", "退", "藏", "谨慎", "保守", "沉着"]),
    (["动", "进", "突破", "果断", "拼"],
     ["顺", "自然", "无为", "随缘", "水到渠成", "随遇"]),
    (["稳", "守", "防", "静", "藏"],
     ["转", "变", "破", "革", "新", "换", "改"]),
    (["利", "财", "富", "贵", "发达"],
     ["贫", "耗", "散", "败", "衰", "困"]),
    (["吉", "顺", "亨", "通", "旺"],
     ["凶", "逆", "阻", "滞", "衰", "败"]),
]


def _keyword_match(text: str, keywords: list) -> int:
    """计算文本与关键词组的匹配分数"""
    return sum(1 for k in keywords if k in text)


def _find_conflict_target(speaker_stance: str, remaining: List[Tuple[int, PerspectiveOpinion]]) -> Optional[int]:
    """在未发言者中找到与当前发言立场最对立的人，返回其在remaining中的索引"""
    best_idx = None
    best_score = 0

    for pos_kw, neg_kw in OPPOSING_GROUPS:
        speaker_pos = _keyword_match(speaker_stance, pos_kw)
        speaker_neg = _keyword_match(speaker_stance, neg_kw)

        # 当前发言者是积极立场
        if speaker_pos > speaker_neg:
            target_kw = neg_kw
        # 当前发言者是保守立场
        elif speaker_neg > speaker_pos:
            target_kw = pos_kw
        else:
            continue

        for idx, (_, opinion) in enumerate(remaining):
            score = _keyword_match(opinion.stance, target_kw)
            if score > best_score:
                best_score = score
                best_idx = idx

    return best_idx if best_score >= 2 else None


def _detect_rebuttal(speaker: PerspectiveOpinion, previous_exchanges: List[Exchange]) -> Optional[Exchange]:
    """检测当前发言者是否与前面某人有明显分歧（纯关键词，无LLM）"""
    if not previous_exchanges:
        return None

    for pos_kw, neg_kw in OPPOSING_GROUPS:
        speaker_score = _keyword_match(speaker.stance, pos_kw + neg_kw)
        if speaker_score < 1:
            continue

        # 找最近3个发言者中立场对立的
        for ex in previous_exchanges[-3:]:
            target_score_pos = _keyword_match(ex.argument, pos_kw)
            target_score_neg = _keyword_match(ex.argument, neg_kw)

            # 立场相反
            if (_keyword_match(speaker.stance, pos_kw) > 0 and target_score_neg > 0) or \
               (_keyword_match(speaker.stance, neg_kw) > 0 and target_score_pos > 0):
                # 生成反驳
                rebuttal = f"【{speaker.figure_name}反驳{ex.speaker}】"
                if _keyword_match(speaker.stance, pos_kw) > 0:
                    rebuttal += f"我认为应当{pos_kw[0]}，{ex.speaker}过于{neg_kw[0]}。"
                else:
                    rebuttal += f"我认为应当{neg_kw[0]}，{ex.speaker}过于{pos_kw[0]}。"
                rebuttal += f"从{speaker.primary_method}的角度看，{speaker.key_points[0] if speaker.key_points else '形势需要审慎判断'}。"

                return Exchange(
                    round_num=1,
                    speaker=speaker.figure_name,
                    speaker_method=speaker.primary_method,
                    target=ex.speaker,
                    target_method=ex.speaker_method,
                    argument=rebuttal,
                    rebuttal_type="针对性反驳"
                )

    return None


class DebateEngine:
    """辩论引擎 v2 — 108人全员参与，零LLM调用"""

    def __init__(self):
        pass

    def debate(self, opinions: List[PerspectiveOpinion], question: str, rounds: int = 1) -> dict:
        """
        运行辩论 - 108人全员轮流发言 + 插队反驳机制

        流程：
        1. 108人按阵营排序，依次发言
        2. 每人发言读取前面所有发言记录
        3. 关键词冲突检测：发言后检测未发言者中是否有人立场对立，插队发言
        4. 术法内部异议：同术法的不同人物自动标记分歧
        """

        # 1. 观点聚类
        clusters = self._cluster_opinions(opinions)
        # 2. 构建发言队列
        queue = list(range(len(opinions)))
        spoken = set()  # 已发言的figure_id
        exchanges = []
        speech_history = []  # 所有发言记录

        # 3. 轮流发言 + 插队机制
        turn = 0
        max_turns = len(opinions) * 2  # 防止无限循环

        while queue and turn < max_turns:
            turn += 1
            idx = queue.pop(0)
            speaker = opinions[idx]

            if speaker.figure_id in spoken:
                continue

            spoken.add(speaker.figure_id)

            # 构建发言内容：引用前面的发言
            speech = self._compose_speech(speaker, speech_history, question)

            # 检测是否有反驳
            rebuttal = _detect_rebuttal(speaker, exchanges)

            # 记录发言
            exchange = Exchange(
                round_num=1,
                speaker=speaker.figure_name,
                speaker_method=speaker.primary_method,
                target=rebuttal.target if rebuttal else "",
                target_method=rebuttal.target_method if rebuttal else "",
                argument=speech,
                rebuttal_type=rebuttal.rebuttal_type if rebuttal else "陈述"
            )
            exchanges.append(exchange)
            speech_history.append({
                "speaker": speaker.figure_name,
                "method": speaker.primary_method,
                "stance": speaker.stance,
                "key_points": speaker.key_points[:2],
            })

            # 如果有反驳，插入反驳记录
            if rebuttal:
                exchanges.append(rebuttal)

            # 冲突检测：检查未发言者中是否有人要插队
            remaining = [(i, opinions[i]) for i in range(len(opinions))
                         if opinions[i].figure_id not in spoken]

            conflict_idx = _find_conflict_target(speaker.stance, remaining)
            if conflict_idx is not None:
                jump_idx = remaining[conflict_idx][0]
                # 插队到队列最前面
                queue.insert(0, jump_idx)

        # 4. 共识提取
        consensus = self._extract_consensus(opinions, exchanges)

        # 5. 分歧提取
        disagreements = self._extract_disagreements(opinions, exchanges)

        # 6. 玄照综合视角（唯一使用LLM的地方）
        xuanzhao = self.generate_xuanzhao_perspective(opinions, consensus, disagreements, question)

        # 7. 总结
        summary = self._generate_summary(opinions, consensus, disagreements)

        return {
            "participants": [{
                "id": o.figure_id,
                "name": o.figure_name,
                "title": o.figure_title,
                "method": o.primary_method,
                "stance": o.stance,
                "confidence": o.confidence,
            } for o in opinions],
            "clusters": clusters,
            "exchanges": exchanges,
            "consensus": consensus,
            "disagreements": disagreements,
            "summary": summary,
            "xuanzhao_perspective": xuanzhao,
        }

    def debate_stream(self, opinions: List[PerspectiveOpinion], question: str):
        """流式辩论 — 108人全员轮流发言+插队反驳，yield SSE事件"""
        import time as _time

        clusters = self._cluster_opinions(opinions)
        queue = list(range(len(opinions)))
        spoken = set()
        exchanges = []
        speech_history = []

        yield {"event": "start", "data": {
            "total_speakers": len(opinions),
            "question": question,
        }}

        turn = 0
        max_turns = len(opinions) * 2
        idx_counter = 0

        while queue and turn < max_turns:
            turn += 1
            idx = queue.pop(0)
            speaker = opinions[idx]

            if speaker.figure_id in spoken:
                continue
            spoken.add(speaker.figure_id)
            idx_counter += 1

            yield {"event": "speaker_start", "data": {
                "index": idx_counter,
                "total": len(opinions),
                "speaker": speaker.figure_name,
                "method": speaker.primary_method,
            }}

            speech = self._compose_speech(speaker, speech_history, question)
            rebuttal = _detect_rebuttal(speaker, exchanges)

            exchange = Exchange(
                round_num=1,
                speaker=speaker.figure_name,
                speaker_method=speaker.primary_method,
                target=rebuttal.target if rebuttal else "",
                target_method=rebuttal.target_method if rebuttal else "",
                argument=speech,
                rebuttal_type=rebuttal.rebuttal_type if rebuttal else "陈述"
            )
            exchanges.append(exchange)
            speech_history.append({
                "speaker": speaker.figure_name,
                "method": speaker.primary_method,
                "stance": speaker.stance,
                "key_points": speaker.key_points[:2],
            })

            if rebuttal:
                exchanges.append(rebuttal)

            # 发言事件
            yield {"event": "statement", "data": {
                "speaker": speaker.figure_name,
                "attempt": 1,
                "text": speech,
                "statement": speech,  # 前端用 data.statement
            }}

            # 个性化审判：每个审判者根据自己的术法和立场给出反馈
            judges = [{"name": opinions[i].figure_name, "method": opinions[i].primary_method,
                       "stance": opinions[i].stance, "key_points": opinions[i].key_points[:2]}
                      for i in range(len(opinions)) if opinions[i].figure_id in spoken
                      and opinions[i].figure_id != speaker.figure_id]

            for j_idx, judge in enumerate(judges):
                # 生成个性化反馈
                feedback = self._generate_judge_feedback(judge, speaker, speech)
                score = feedback["score"]
                passed = score >= 85
                judge["_cached_score"] = score  # 缓存分数避免重复计算
                if (j_idx + 1) % 5 == 0 or j_idx == len(judges) - 1:
                    yield {"event": "judgment_progress", "data": {
                        "speaker": speaker.figure_name,
                        "attempt": 1,
                        "judge": judge["name"],
                        "judge_index": j_idx + 1,
                        "total_judges": len(judges),
                        "passed": passed,
                        "score": score,
                        "feedback": feedback["comment"][:80],
                        "pass_rate": round(sum(1 for j in judges[:j_idx+1] if j.get("_cached_score", 0) >= 85) / (j_idx+1) * 100, 1),
                    }}
            # 计算最终通过率
            all_scores = [j.get("_cached_score", 85) for j in judges]
            final_pass_rate = round(sum(1 for s in all_scores if s >= 85) / len(all_scores) * 100, 1) if all_scores else 100
            avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 90

            yield {"event": "speaker_passed", "data": {
                "speaker": speaker.figure_name,
                "attempt": 1,
                "pass_rate": final_pass_rate,
                "avg_score": avg_score,
                "text": speech,
                "statement": speech,
            }}

            # 冲突检测：插队
            remaining = [(i, opinions[i]) for i in range(len(opinions))
                         if opinions[i].figure_id not in spoken]
            conflict_idx = _find_conflict_target(speaker.stance, remaining)
            if conflict_idx is not None:
                jump_idx = remaining[conflict_idx][0]
                queue.insert(0, jump_idx)

        # 共识/分歧
        consensus = self._extract_consensus(opinions, exchanges)
        disagreements = self._extract_disagreements(opinions, exchanges)
        summary = self._generate_summary(opinions, consensus, disagreements)

        # 玄照综合（唯一LLM调用）
        yield {"event": "xuanzhao_start", "data": {"message": "玄照综合推理中..."}}
        xuanzhao = self.generate_xuanzhao_perspective(opinions, consensus, disagreements, question)
        yield {"event": "xuanzhao_result", "data": xuanzhao}

        # 溟玄终审：审查并改写结论
        yield {"event": "mingxuan_start", "data": {"message": "溟玄审查结论中..."}}
        try:
            from engine.mingxuan_observer import build_mingxuan_review_result, check_ai_slop
            from engine.llm_client import get_llm_client
            llm = get_llm_client()
            mingxuan = build_mingxuan_review_result(llm, xuanzhao, question)
            yield {"event": "mingxuan_result", "data": {
                "text": mingxuan["mingxuan_text"],
                "original_pass": mingxuan["original_pass"],
                "issues": mingxuan["issues"],
            }}
        except Exception as e:
            logger.warning(f"溟玄审查失败: {e}")
            yield {"event": "mingxuan_result", "data": {
                "text": xuanzhao.get("stance", "综合分析完成"),
                "original_pass": False,
                "issues": [f"审查异常: {str(e)}"],
            }}

        yield {"event": "debate_end", "data": {
            "total_speakers": len(spoken),
            "summary": summary,
            "consensus": consensus,
            "disagreements": disagreements[:10],
        }}

    def _generate_judge_feedback(self, judge: dict, speaker: PerspectiveOpinion, speech: str) -> dict:
        """根据审判者的术法和立场生成个性化反馈（确定性评分）"""
        method = judge["method"]
        judge_stance = judge.get("stance", "")
        judge_points = judge.get("key_points", [])

        # 确定性基础分数：基于发言内容哈希
        content_hash = hash(speech + judge.get("name", "")) % 11  # 0-10
        base_score = 85 + content_hash  # 85-95

        # 术法视角的评论模板
        method_comments = {
            "八字": [
                f"从八字角度看，日主{speaker.key_points[0] if speaker.key_points else '甲木'}的论述有理",
                f"此论契合{method}之理，财官印绶的分析到位",
                f"八字格局判断准确，但大运流年的细节可再深究",
                f"十神取用得当，唯调候用神的论述略显不足",
            ],
            "奇门": [
                f"奇门遁甲看，值符值使的分析符合{method}要义",
                f"九宫八门的格局判断有据，但星神的论述可再精炼",
                f"此论深得{method}三盘合一之妙",
                f"门星神的配合分析到位，唯时干格局可再推敲",
            ],
            "紫微": [
                f"紫微斗数论命，命宫主星的取用正确",
                f"四化飞星的论述符合{method}之理",
                f"此论抓住了命盘核心，但大限流年的细节可补充",
                f"星曜组合的分析有深度，格局判断准确",
            ],
            "占星": [
                f"从星盘角度看，行星落宫的分析到位",
                f"相位角度的论述符合{method}要义",
                f"此论抓住了星盘的核心张力，但容许度的细节可再考",
                f"宫位主星的取用正确，格局判断有据",
            ],
            "六爻": [
                f"六爻纳甲论卦，用神取用正确",
                f"动变爻的分析符合{method}之理",
                f"此论抓住了卦的核心，但日建月建的影响可再推敲",
                f"世应关系的论述到位，格局判断准确",
            ],
            "梅花易数": [
                f"梅花易数论卦，体用关系的分析到位",
                f"卦象取用符合{method}之理",
                f"此论抓住了卦的核心意象，但互变卦的细节可补充",
                f"五行生克的论述准确，格局判断有据",
            ],
            "反脆弱": [
                f"从反脆弱角度看，杠铃策略的论述有深度",
                f"风险收益不对称的分析符合{method}要义",
                f"此论抓住了反脆弱的核心，但凸性机会的细节可再展开",
                f"黑天鹅应对策略的论述到位",
            ],
            "心理学": [
                f"从心理学角度看，潜意识模式的分析有洞察",
                f"认知偏差的论述符合{method}要义",
                f"此论抓住了心理的核心张力，但防御机制的细节可补充",
                f"人格特质的判断准确，分析有据",
            ],
            "兵法": [
                f"兵法论势，知己知彼的分析到位",
                f"虚实之道的论述符合{method}要义",
                f"此论抓住了兵法的核心，但时机判断的细节可再推敲",
                f"攻守策略的论述有深度，格局判断准确",
            ],
            "大六壬": [
                f"大六壬看四课三传，天地盘的分析符合{method}要义",
                f"此论抓住了{method}的核心，但月将加临时的细节可再推敲",
                f"三传走势的论述有据，神煞吉凶的判断准确",
                f"四课生克关系的分析到位，天将取用得当",
            ],
            "太乙": [
                f"太乙神数看积年推演，阴阳遁的分析符合{method}要义",
                f"此论抓住了{method}的核心，但三基五福的细节可再展开",
                f"太乙九宫的论述有据，国运大局的判断准确",
                f"主客算的分析到位，十六神将取用得当",
            ],
            "哲学推演": [
                f"从{method}角度看，控制二分法的运用得当，区分可控与不可控",
                f"此论体现了命运之爱（Amor Fati）的精神，接纳与行动并重",
                f"{method}的分析有深度，消极想象的预防思维到位",
                f"斯多葛式的理性分析准确，但情感维度的考量可再补充",
            ],
            "多元模型": [
                f"从{method}角度看，跨学科思维模型的调用恰当",
                f"此论体现了逆向思考的精神，反过来想往往更接近真相",
                f"{method}的分析到位，能力圈意识清晰，不越界判断",
                f"检查清单式的排除法运用得当，但正向推理链可再强化",
            ],
            "第一性原理": [
                f"从{method}角度看，回归基本事实的推理链清晰",
                f"此论体现了奥卡姆剃刀精神，去除了不必要的假设",
                f"{method}的分析准确，可证伪性标准把握得当",
                f"简化到本质的思维到位，但经验数据的引用可再丰富",
            ],
            "综合": [
                f"综合七术视角，跨术法数据交叉比对的逻辑严密",
                f"多维度交叉验证的分析有说服力，共识与分歧把握准确",
                f"此论体现了七术照见的综合智慧，万法归一的判断有据",
                f"综合分析全面，但个别术法的细节可再深入挖掘",
            ],
        }

        # 获取评论（确定性选择）
        comments = method_comments.get(method, [
            f"从{method}角度看，此论有理有据",
            f"{method}的分析到位，观点鲜明",
            f"此论符合{method}之理，判断准确",
        ])
        comment_idx = hash(speech + judge.get("name", "") + method) % len(comments)
        comment = comments[comment_idx]

        # 如果审判者立场与发言者相反，扣分并加评论
        opposing_keywords = [("动", "稳"), ("进", "守"), ("突破", "保守"), ("积极", "谨慎")]
        for pos, neg in opposing_keywords:
            if (pos in judge_stance and neg in speaker.stance) or \
               (neg in judge_stance and pos in speaker.stance):
                base_score = max(75, base_score - 10)
                comment += f"，但{judge['name']}认为立场需再斟酌"
                break

        return {"score": base_score, "comment": comment}

    def _compose_speech(self, speaker: PerspectiveOpinion,
                        speech_history: List[dict], question: str) -> str:
        """构建发言内容，引用前面人的发言"""
        parts = []

        # 核心立场
        parts.append(f"【{speaker.figure_name}（{speaker.primary_method}）】")
        parts.append(speaker.stance)

        # 引用前面发言中的相关/对立观点
        if speech_history:
            # 找最近的同术法发言
            same_method = [s for s in speech_history[-10:] if s["method"] == speaker.primary_method]
            if same_method:
                ref = same_method[-1]
                parts.append(f"（承接{ref['speaker']}的{speaker.primary_method}视角）")

            # 找对立观点
            for pos_kw, neg_kw in OPPOSING_GROUPS[:2]:
                if _keyword_match(speaker.stance, pos_kw) > 0:
                    for s in speech_history[-5:]:
                        if _keyword_match(s["stance"], neg_kw) > 0:
                            parts.append(f"（对{s['speaker']}的「{s['stance'][:20]}」持不同看法）")
                            break
                    break

        # 关键论据
        if speaker.key_points:
            parts.append(f"核心：{'；'.join(speaker.key_points[:2])}")

        return "".join(parts)

    def _cluster_opinions(self, opinions: List[PerspectiveOpinion]) -> Dict[str, List[str]]:
        """观点聚类——按立场关键词加权匹配"""
        clusters = {
            "积极进取": [],
            "谨慎保守": [],
            "顺其自然": [],
            "转型突破": [],
            "贵人扶持": [],
            "智慧谋略": [],
            "综合平衡": [],
        }

        keyword_scores = {
            "积极进取": {"动": 1, "进": 1, "突破": 2, "断": 1, "胜": 1, "拼": 1, "冲": 1, "攻": 1},
            "谨慎保守": {"稳": 1, "守": 1, "防": 1, "静": 1, "韬": 1, "隐": 1, "退": 1, "藏": 1},
            "顺其自然": {"顺": 1, "自然": 2, "无为": 2, "等": 1, "水到渠成": 2, "随缘": 2},
            "转型突破": {"转": 1, "变": 1, "破": 1, "革": 1, "新": 1, "换": 1, "改": 1},
            "贵人扶持": {"贵人": 2, "助力": 1, "提携": 2, "帮扶": 1, "辅佐": 1},
            "智慧谋略": {"谋": 1, "智": 1, "策略": 2, "算": 1, "布局": 2, "筹": 1},
        }

        for o in opinions:
            stance = o.stance
            scores = {}
            for cluster, keywords in keyword_scores.items():
                score = sum(w for k, w in keywords.items() if k in stance)
                scores[cluster] = score

            best = max(scores, key=scores.get)
            if scores[best] > 0:
                clusters[best].append(o.figure_name)
            else:
                clusters["综合平衡"].append(o.figure_name)

        return {k: v for k, v in clusters.items() if v}

    # ─── 共识提取关键词表（模块级常量，避免每次调用重建）──────────────
    # 多字符术法关键词（优先匹配，避免被单字符截断）
    _CONSENSUS_MULTI_KEYWORDS = [
        "身强", "身弱", "用神", "日主", "大运", "流年", "格局", "调候",
        "命宫", "主星", "四化", "三方四正", "化忌", "化禄", "化权", "化科",
        "值符", "值使", "生门", "开门", "八门", "九星", "六神",
        "三传", "四课", "天将", "月将", "神煞", "太乙", "主算", "客算",
        "顺势", "贵人", "谋略", "策略", "借势", "守正", "无为", "自然",
        "桃花", "文昌", "禄位", "财帛", "官禄", "驿马",
        "利于", "适宜", "不利", "阻碍", "突破", "稳定", "保守", "进取",
    ]
    # 单字符关键词（仅匹配不含任何多字符关键词的 key_point）
    _CONSENSUS_SINGLE_KEYWORDS = [
        "财", "官", "印", "比", "杀", "食", "伤", "吉", "凶", "利", "贵",
        "旺", "衰", "合", "冲", "刑", "破", "生", "克",
    ]

    # 各术法内部共识专用关键词（扩展现有的5词表）
    _METHOD_CONSENSUS_KEYWORDS = {
        "八字": ["身强", "身弱", "用神得力", "格局", "大运", "利", "吉", "旺", "顺", "宜"],
        "紫微": ["命宫", "主星", "化禄", "化权", "三方四正", "吉", "旺", "顺", "利"],
        "奇门": ["吉格", "吉门", "生门", "开门", "值符", "利", "吉", "顺", "旺"],
        "六爻": ["用神", "旺相", "世爻", "吉", "利", "顺", "宜", "旺"],
        "大六壬": ["贵人", "三传", "吉将", "利", "吉", "顺", "旺"],
        "太乙": ["吉算", "主算", "利", "吉", "顺", "旺"],
        "占星": ["入庙", "吉相位", "和谐", "利", "吉", "顺"],
    }

    def _extract_consensus(self, opinions: List[PerspectiveOpinion],
                           exchanges: List[Exchange]) -> List[str]:
        """提取共识——多维度关键词频率 + 立场聚类 + 同术法内部共识"""
        from collections import Counter

        all_points = []
        all_stances = []
        for o in opinions:
            all_points.extend(o.key_points)
            all_stances.append(o.stance)

        n = len(opinions)
        consensus = []

        # ── 1. 多字符术法关键词频率统计（优先匹配长词） ──
        word_counts = Counter()
        for point in all_points:
            matched_multi = set()
            for word in self._CONSENSUS_MULTI_KEYWORDS:
                if word in point:
                    matched_multi.add(word)
            # 仅在没有匹配到多字符关键词时，才尝试单字符匹配（避免子串重复计数）
            if not matched_multi:
                for word in self._CONSENSUS_SINGLE_KEYWORDS:
                    if word in point:
                        matched_multi.add(word)
            for word in matched_multi:
                word_counts[word] += 1

        # 术法关键词共识（取top 6，阈值降为≥2人且≥8%）
        for word, count in word_counts.most_common(6):
            if count >= max(2, n * 0.08):
                consensus.append(f"多人提及「{word}」（{count}/{n}人）")

        # ── 2. 立场层面的共识（检测stance中共享的立场关键词） ──
        stance_keywords = Counter()
        stance_terms = [
            "积极进取", "谨慎保守", "顺势而为", "厚积薄发", "稳中求进",
            "审时度势", "守正出奇", "无为而治", "借势而为", "避实击虚",
            "贵人相助", "突破", "守成", "转型", "深耕", "积累",
        ]
        for stance in all_stances:
            for term in stance_terms:
                if term in stance:
                    stance_keywords[term] += 1

        for term, count in stance_keywords.most_common(3):
            if count >= max(2, n * 0.1):
                consensus.append(f"{count}人持「{term}」立场")

        # ── 3. 同术法内部共识（扩展现有逻辑） ──
        method_groups = {}
        for o in opinions:
            method_groups.setdefault(o.primary_method, []).append(o)

        for method, group in method_groups.items():
            if len(group) < 2:
                continue
            stances = [o.stance for o in group]
            all_group_points = []
            for o in group:
                all_group_points.extend(o.key_points)
            group_texts = stances + all_group_points

            # 使用该术法的专用关键词
            method_kws = self._METHOD_CONSENSUS_KEYWORDS.get(method, ["利", "吉", "顺", "宜", "旺"])
            common = []
            for kw in method_kws:
                if sum(1 for t in group_texts if kw in t) >= max(2, len(group) * 0.4):
                    common.append(kw)
            if common:
                consensus.append(f"{method}内部共识：多人论及「{'、'.join(common[:3])}」")

        return consensus[:10]

    def _extract_disagreements(self, opinions: List[PerspectiveOpinion],
                               exchanges: List[Exchange]) -> List[Dict]:
        """提取分歧"""
        disagreements = []

        # 从反驳记录提取
        for ex in exchanges:
            if ex.rebuttal_type in ("针对性反驳",) and ex.target:
                disagreements.append({
                    "between": [ex.speaker, ex.target],
                    "stance_a": ex.argument[:80],
                    "stance_b": f"立场不同",
                    "aspect": "观点对立",
                })

        # 同术法内部分歧
        method_groups = {}
        for o in opinions:
            method_groups.setdefault(o.primary_method, []).append(o)

        for method, group in method_groups.items():
            if len(group) >= 2:
                # 检查是否有对立立场
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        for pos_kw, neg_kw in OPPOSING_GROUPS[:2]:
                            if _keyword_match(group[i].stance, pos_kw) > 0 and \
                               _keyword_match(group[j].stance, neg_kw) > 0:
                                disagreements.append({
                                    "between": [group[i].figure_name, group[j].figure_name],
                                    "stance_a": group[i].stance[:50],
                                    "stance_b": group[j].stance[:50],
                                    "aspect": f"{method}内部分歧",
                                })
                                break

        return disagreements[:10]

    def _generate_summary(self, opinions: List[PerspectiveOpinion],
                          consensus: List[str], disagreements: List[Dict]) -> str:
        """生成辩论总结"""
        n = len(opinions)
        methods = set(o.primary_method for o in opinions)

        summary = f"本次辩论共{n}位人物参与，涵盖{len(methods)}种术法。"

        if consensus:
            summary += f"达成{len(consensus)}项共识。"

        if disagreements:
            summary += f"存在{len(disagreements)}处分歧。"

        # 置信度统计
        avg_conf = sum(o.confidence for o in opinions) / n if n else 0
        summary += f"平均置信度{avg_conf:.0%}。"

        return summary

    def generate_xuanzhao_perspective(self, opinions: List[PerspectiveOpinion],
                                      consensus: List[str], disagreements: List[Dict],
                                      question: str) -> dict:
        """玄照综合视角——唯一使用LLM的地方"""

        # 统计基础数据
        methods_used = list(set(o.primary_method for o in opinions))
        factions = {}
        for o in opinions:
            fig = FIGURES.get(o.figure_id)
            f = fig.faction if fig else "其他"
            factions[f] = factions.get(f, 0) + 1

        stances = {}
        for o in opinions:
            if any(k in o.stance for k in ["动", "进", "突破", "断", "拼", "冲"]):
                stances["积极进取"] = stances.get("积极进取", 0) + 1
            elif any(k in o.stance for k in ["稳", "守", "防", "静", "韬", "隐"]):
                stances["谨慎保守"] = stances.get("谨慎保守", 0) + 1
            elif any(k in o.stance for k in ["顺势", "自然", "无为", "顺应"]):
                stances["顺其自然"] = stances.get("顺其自然", 0) + 1
            else:
                stances["综合平衡"] = stances.get("综合平衡", 0) + 1

        all_key_points = []
        for o in opinions:
            all_key_points.extend(o.key_points)

        # 尝试 LLM 深度合成
        llm_reasoning = None
        llm_stance = None
        llm_key_points = None
        llm_confidence = None
        try:
            llm_result = self._llm_synthesize_xuanzhao(
                opinions, consensus, disagreements, question, stances, methods_used
            )
            if llm_result:
                llm_reasoning = llm_result.get("reasoning", "")
                llm_stance = llm_result.get("stance", "")
                llm_key_points = llm_result.get("key_points", [])
                llm_confidence = llm_result.get("confidence", None)
        except Exception as e:
            logger.warning(f"LLM 玄照视角合成失败，回退规则引擎: {e}")

        # 玄照判断（LLM 优先，规则回退）
        if llm_stance:
            xuanzhao_stance = llm_stance
        else:
            if stances:
                dominant = max(stances, key=stances.get)
                if dominant == "积极进取":
                    xuanzhao_stance = "大势向好，宜积极进取，但不可冒进"
                elif dominant == "谨慎保守":
                    xuanzhao_stance = "时机未到，宜稳扎稳打，等待良机"
                elif dominant == "顺其自然":
                    xuanzhao_stance = "顺势而为，不强求，不执着，水到渠成"
                else:
                    xuanzhao_stance = "各方观点均衡，需审时度势，灵活应变"
            else:
                xuanzhao_stance = "数据不足，无法给出明确判断"

        # 构建玄照视角
        base_confidence = max(0.3, min(0.95, 0.75 + (len(consensus) * 0.05) - (len(disagreements) * 0.05)))
        perspective = {
            "figure_name": "玄照",
            "figure_title": "照见者",
            "primary_method": "综合",
            "stance": xuanzhao_stance,
            "confidence": llm_confidence if llm_confidence is not None else base_confidence,
            "reasoning": llm_reasoning if llm_reasoning else {
                "participants": len(opinions),
                "methods": methods_used,
                "factions": factions,
                "stance_distribution": stances,
            },
            "key_points": llm_key_points if llm_key_points else list(set(all_key_points))[:8],
            "consensus": consensus[:3],
            "disagreements": disagreements[:2],
            "quotes": ["七术照见，万法归一"],
            "synthesis_mode": "llm" if llm_reasoning else "rule",
        }

        return perspective

    def _llm_synthesize_xuanzhao(
        self,
        opinions: List[PerspectiveOpinion],
        consensus: List[str],
        disagreements: List[Dict],
        question: str,
        stances: Dict[str, int],
        methods_used: List[str],
    ) -> Optional[Dict]:
        """使用 LLM 综合所有视角，生成玄照深度分析"""

        from engine.llm_client import get_llm_client

        # 构造各视角观点摘要（取前20个代表）
        opinions_text = []
        for o in opinions[:20]:
            fig = FIGURES.get(o.figure_id)
            faction = fig.faction if fig else "未知"
            opinions_text.append(
                f"【{o.figure_name}】（{o.primary_method}，{faction}，置信度{o.confidence}）\n"
                f"  立场：{o.stance}\n"
                f"  核心：{'；'.join(o.key_points[:3]) if o.key_points else '无'}"
            )

        consensus_text = "；".join(consensus[:5]) if consensus else "暂无明显共识"

        disagreement_texts = []
        for d in disagreements[:3]:
            disagreement_texts.append(
                f"{d['between'][0]} vs {d['between'][1]}：{d.get('aspect', '观点对立')}"
            )

        prompt = f"""你是玄照，108位命理大师的综合视角。

问题：{question}

108位大师的观点摘要：
{chr(10).join(opinions_text)}

共识：{consensus_text}
分歧：{'；'.join(disagreement_texts) if disagreement_texts else '无明显分歧'}

立场分布：{stances}
使用术法：{methods_used}

请综合所有观点，给出玄照视角：
1. stance：一句话总结立场（30字内）
2. reasoning：深度分析（200字内）
3. key_points：3-5个关键要点
4. confidence：0.0-1.0的置信度

返回JSON格式。"""

        llm = get_llm_client()
        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000,
        )

        if result.get("parse_error"):
            return None

        return result
