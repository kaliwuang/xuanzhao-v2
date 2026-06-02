#!/usr/bin/env python3
"""
玄照 v2.0 - 辩论引擎

核心功能：
1. 观点聚类（相近观点归一组）
2. 冲突检测（找出立场对立的人物）
3. 自动生成交锋
4. 共识提取

每个人物用自己的术法数据发言，互相反驳。
"""
from typing import List, Dict
from dataclasses import dataclass
from .perspective_engine import PerspectiveOpinion, FIGURES


@dataclass
class Exchange:
    round_num: int
    speaker: str
    speaker_method: str
    target: str
    target_method: str
    argument: str
    rebuttal_type: str


class DebateEngine:
    """辩论引擎"""

    def __init__(self):
        pass

    def debate(self, opinions: List[PerspectiveOpinion], question: str, rounds: int = 2) -> dict:
        """运行辩论"""

        # 1. 观点聚类
        clusters = self._cluster_opinions(opinions)

        # 2. 识别冲突对
        conflict_pairs = self._find_conflicts(opinions)

        # 3. 生成交锋
        exchanges = []
        for r in range(1, rounds + 1):
            round_exchanges = self._generate_round(r, conflict_pairs, opinions, question)
            exchanges.extend(round_exchanges)

        # 4. 共识总结
        consensus = self._extract_consensus(opinions, exchanges)

        # 5. 分歧总结
        disagreements = self._extract_disagreements(opinions, exchanges)

        # 6. 玄照视角
        xuanzhao = self.generate_xuanzhao_perspective(opinions, consensus, disagreements)

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
            "summary": self._generate_summary(opinions, consensus, disagreements),
            "xuanzhao_perspective": xuanzhao,
        }

    def _cluster_opinions(self, opinions: List[PerspectiveOpinion]) -> Dict[str, List[str]]:
        """观点聚类"""
        clusters = {
            "积极进取": [],
            "谨慎保守": [],
            "顺其自然": [],
            "转型突破": [],
        }

        for o in opinions:
            stance = o.stance
            if any(w in stance for w in ["动", "进", "突破", "断", "胜"]):
                clusters["积极进取"].append(o.figure_name)
            elif any(w in stance for w in ["稳", "守", "防", "静", "韬"]):
                clusters["谨慎保守"].append(o.figure_name)
            elif any(w in stance for w in ["顺", "自然", "无为", "等"]):
                clusters["顺其自然"].append(o.figure_name)
            elif any(w in stance for w in ["转", "变", "破", "革"]):
                clusters["转型突破"].append(o.figure_name)
            else:
                clusters["积极进取"].append(o.figure_name)

        # 去掉空集群
        return {k: v for k, v in clusters.items() if v}

    def _find_conflicts(self, opinions: List[PerspectiveOpinion]) -> List[tuple]:
        """基于观点立场找冲突对"""
        conflicts = []

        # 分组：积极进取 vs 谨慎保守
        aggressive = [o for o in opinions if any(w in o.stance for w in ["动", "进", "突破", "断"])]
        conservative = [o for o in opinions if any(w in o.stance for w in ["稳", "守", "防", "静", "韬"])]
        passive = [o for o in opinions if any(w in o.stance for w in ["顺", "自然", "无为", "等"])]

        # 积极进取 vs 谨慎保守
        for a in aggressive[:2]:
            for c in conservative[:2]:
                conflicts.append((a, c))

        # 积极进取 vs 顺其自然
        for a in aggressive[:1]:
            for p in passive[:1]:
                conflicts.append((a, p))

        # 谨慎保守 vs 顺其自然
        for c in conservative[:1]:
            for p in passive[:1]:
                conflicts.append((c, p))

        return conflicts

    def _generate_round(self, round_num: int, conflict_pairs: List[tuple],
                        opinions: List[PerspectiveOpinion], question: str) -> List[Exchange]:
        """生成一轮交锋"""
        exchanges = []

        for (p1, p2) in conflict_pairs:
            # A 反驳 B
            arg = self._generate_argument(p1, p2, question)
            exchanges.append(Exchange(
                round_num=round_num,
                speaker=p1.figure_name,
                speaker_method=p1.primary_method,
                target=p2.figure_name,
                target_method=p2.primary_method,
                argument=arg,
                rebuttal_type="逻辑反驳"
            ))

            # B 回应
            arg2 = self._generate_argument(p2, p1, question)
            exchanges.append(Exchange(
                round_num=round_num,
                speaker=p2.figure_name,
                speaker_method=p2.primary_method,
                target=p1.figure_name,
                target_method=p1.primary_method,
                argument=arg2,
                rebuttal_type="逻辑反驳"
            ))

        return exchanges

    def _generate_argument(self, speaker: PerspectiveOpinion,
                           target: PerspectiveOpinion, question: str) -> str:
        """生成反驳论据"""

        # 根据双方术法差异生成反驳
        if speaker.primary_method != target.primary_method:
            return (
                f"{speaker.figure_name}（{speaker.primary_method}视角）："
                f"从{speaker.primary_method}来看，{speaker.stance}。"
                f"{target.figure_name}用{target.primary_method}看到的是局部，"
                f"我用{speaker.primary_method}看到的是全局。"
                f"{speaker.key_points[0] if speaker.key_points else ''}"
            )
        else:
            return (
                f"{speaker.figure_name}："
                f"同为{speaker.primary_method}，但我看{speaker.key_points[0] if speaker.key_points else '重点不同'}。"
                f"{target.figure_name}忽视了这一点。"
            )

    def _extract_consensus(self, opinions: List[PerspectiveOpinion],
                           exchanges: List[Exchange]) -> List[str]:
        """提取共识"""
        consensus = []

        # 找所有观点中重复的关键词
        all_points = []
        for o in opinions:
            all_points.extend(o.key_points)

        from collections import Counter
        counts = Counter(all_points)
        for point, count in counts.most_common(3):
            if count >= 2:
                consensus.append(point)

        # 如果没有共识，提取最高置信度的观点
        if not consensus:
            best = max(opinions, key=lambda o: o.confidence)
            consensus.append(best.stance)

        return consensus

    def _extract_disagreements(self, opinions: List[PerspectiveOpinion],
                                exchanges: List[Exchange]) -> List[Dict]:
        """提取分歧"""
        disagreements = []

        # 找 stance 差异最大的
        stances = [(o.figure_name, o.stance) for o in opinions]
        for i, (n1, s1) in enumerate(stances):
            for n2, s2 in stances[i+1:]:
                if self._stance_differs(s1, s2):
                    disagreements.append({
                        "between": [n1, n2],
                        "stance_a": s1,
                        "stance_b": s2,
                    })

        return disagreements[:3]

    def _stance_differs(self, s1: str, s2: str) -> bool:
        """判断两个立场是否不同"""
        # 简单规则：如果包含明显相反的词
        opposites = [
            (["进", "动", "突破"], ["守", "静", "稳"]),
            (["早", "快"], ["晚", "慢"]),
            (["合", "留"], ["分", "离"]),
        ]

        for pos, neg in opposites:
            s1_pos = any(p in s1 for p in pos)
            s1_neg = any(n in s1 for n in neg)
            s2_pos = any(p in s2 for p in pos)
            s2_neg = any(n in s2 for n in neg)

            if (s1_pos and s2_neg) or (s1_neg and s2_pos):
                return True

        return False

    def _generate_summary(self, opinions: List[PerspectiveOpinion],
                          consensus: List[str], disagreements: List[Dict]) -> str:
        """生成辩论总结"""
        methods_used = list(set(o.primary_method for o in opinions))

        summary = f""
        summary += f"本次辩论共有{len(opinions)}位人物参与，"
        summary += f"使用{len(methods_used)}种术法（{'、'.join(methods_used)}）。"

        if consensus:
            summary += f"共识：{'；'.join(consensus[:3])}。"

        if disagreements:
            summary += f"主要分歧在于{' vs '.join(disagreements[0]['between'])}。"

        summary += "最终判断需综合各方观点，结合命主实际情况。"

        return summary

    def generate_xuanzhao_perspective(self, opinions: List[PerspectiveOpinion],
                                       consensus: List[str],
                                       disagreements: List[Dict]) -> Dict:
        """生成玄照视角——综合所有人物观点的深度分析"""
        # 统计
        methods_used = list(set(o.primary_method for o in opinions))
        factions = {}
        for o in opinions:
            fig = FIGURES.get(o.figure_id)
            if fig:
                factions[fig.faction] = factions.get(fig.faction, 0) + 1

        # 立场分布
        stances = {}
        for o in opinions:
            # 简单分类立场
            if any(k in o.stance for k in ["稳健", "保守", "谨慎", "等待"]):
                stances["谨慎保守"] = stances.get("谨慎保守", 0) + 1
            elif any(k in o.stance for k in ["积极", "突破", "变革", "行动"]):
                stances["积极进取"] = stances.get("积极进取", 0) + 1
            elif any(k in o.stance for k in ["顺势", "自然", "无为", "顺应"]):
                stances["顺其自然"] = stances.get("顺其自然", 0) + 1
            else:
                stances["综合平衡"] = stances.get("综合平衡", 0) + 1

        # 收集所有关键点
        all_key_points = []
        for o in opinions:
            all_key_points.extend(o.key_points)

        # 玄照判断
        xuanzhao_stance = ""
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

        # 构建玄照视角
        perspective = {
            "figure_name": "玄照",
            "figure_title": "照见者",
            "primary_method": "综合",
            "stance": xuanzhao_stance,
            "confidence": 0.75 + (len(consensus) * 0.05) - (len(disagreements) * 0.05),
            "reasoning": {
                "participants": len(opinions),
                "methods": methods_used,
                "factions": factions,
                "stance_distribution": stances,
            },
            "key_points": list(set(all_key_points))[:8],
            "consensus": consensus[:3],
            "disagreements": disagreements[:2],
            "quotes": ["七术照见，万法归一"],
        }

        return perspective
