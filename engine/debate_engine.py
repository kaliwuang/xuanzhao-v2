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

        # 2. 构建发言队列：按阵营分组排序
        faction_order = {"儒家": 0, "道家": 1, "兵家": 2, "法家": 3, "纵横家": 4,
                         "佛家": 5, "心理学": 6, "投资": 7, "医学": 8, "科学": 9, "其他": 10}

        opinion_map = {o.figure_id: o for o in opinions}
        queue = list(range(len(opinions)))  # 发言队列（opinions的索引）
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
            "综合平衡": [],
        }

        keyword_scores = {
            "积极进取": {"动": 1, "进": 1, "突破": 2, "断": 1, "胜": 1, "拼": 1, "冲": 1, "攻": 1},
            "谨慎保守": {"稳": 1, "守": 1, "防": 1, "静": 1, "韬": 1, "隐": 1, "退": 1, "藏": 1},
            "顺其自然": {"顺": 1, "自然": 2, "无为": 2, "等": 1, "水到渠成": 2, "随缘": 2},
            "转型突破": {"转": 1, "变": 1, "破": 1, "革": 1, "新": 1, "换": 1, "改": 1},
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

    def _extract_consensus(self, opinions: List[PerspectiveOpinion],
                           exchanges: List[Exchange]) -> List[str]:
        """提取共识——相同关键词出现频率高的观点"""
        all_points = []
        for o in opinions:
            all_points.extend(o.key_points)

        # 统计关键词频率
        from collections import Counter
        # 按字符拆分关键点的关键词
        word_counts = Counter()
        for point in all_points:
            for word in ["进", "守", "稳", "动", "突破", "顺", "自然", "财", "官",
                         "印", "比", "杀", "食", "伤", "吉", "凶", "利", "贵"]:
                if word in point:
                    word_counts[word] += 1

        consensus = []
        n = len(opinions)
        for word, count in word_counts.most_common(5):
            if count >= max(2, n * 0.1):  # 至少10%的人提到
                consensus.append(f"多数人提及「{word}」（{count}/{n}人）")

        # 同术法共识
        method_groups = {}
        for o in opinions:
            method_groups.setdefault(o.primary_method, []).append(o)

        for method, group in method_groups.items():
            if len(group) >= 2:
                stances = [o.stance for o in group]
                # 找共同关键词
                common = []
                for kw in ["利", "吉", "顺", "宜", "旺"]:
                    if sum(1 for s in stances if kw in s) >= len(group) * 0.5:
                        common.append(kw)
                if common:
                    consensus.append(f"{method}内部共识：多认为含「{''.join(common)}」之象")

        return consensus[:8]

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
