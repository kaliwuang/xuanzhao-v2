#!/usr/bin/env python3
"""
玄照 v2.0 - 问答引擎

接收用户问题，解析类型，从UDM提取数据，生成带置信度的回答。
"""
from typing import Optional, List, Dict
from enum import Enum

from .udm import DestinyModel
from .cross_validator import CrossValidator


class QuestionType(Enum):
    CAREER = "事业"
    LOVE = "感情"
    HEALTH = "健康"
    WEALTH = "财运"
    PERSONALITY = "性格"
    GENERAL = "综合"


class ConfidenceLevel(Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class QAAnswer:
    """问答结果"""

    def __init__(
        self,
        question_type: QuestionType,
        answer: str,
        confidence: ConfidenceLevel,
        supporting_methods: List[str],
        key_points: List[str],
        warnings: List[str],
    ):
        self.question_type = question_type
        self.answer = answer
        self.confidence = confidence
        self.supporting_methods = supporting_methods
        self.key_points = key_points
        self.warnings = warnings


class QAEngine:
    """问答引擎"""

    # 关键词映射
    KEYWORDS = {
        QuestionType.CAREER: [
            "事业", "工作", "职业", "创业", "升职", "跳槽", "行业",
            "老板", "领导", "同事", "下属", "项目", "生意",
        ],
        QuestionType.LOVE: [
            "感情", "婚姻", "桃花", "对象", "配偶", "恋爱", "结婚",
            "离婚", "分手", "复合", "相亲", "缘分", "正缘", "孽缘",
        ],
        QuestionType.HEALTH: [
            "健康", "身体", "病", "医", "体质", "养生", "调理",
            "手术", "住院", "慢性", "脏腑", "五行", "气血",
        ],
        QuestionType.WEALTH: [
            "财", "钱", "收入", "投资", "股票", "基金", "买房",
            "资产", "负债", "债务", "储蓄", "消费", "奢侈",
        ],
        QuestionType.PERSONALITY: [
            "性格", "脾气", "个性", "为人", "处事", "人际", "社交",
            "内向", "外向", "乐观", "悲观", "优点", "缺点",
        ],
    }

    def __init__(self):
        pass

    def ask(self, udm: DestinyModel, question: str) -> QAAnswer:
        """回答用户问题"""
        qtype = self._classify_question(question)

        # 先做交叉验证
        validator = CrossValidator(udm)
        cv_result = validator.validate()

        # 根据问题类型提取数据
        data = self._extract_data(udm, qtype, cv_result)

        # 生成回答
        answer_text = self._generate_answer(qtype, data, cv_result)

        # 计算置信度
        confidence = self._calc_confidence(data, cv_result)

        return QAAnswer(
            question_type=qtype,
            answer=answer_text,
            confidence=confidence,
            supporting_methods=data.get("methods", []),
            key_points=data.get("key_points", []),
            warnings=data.get("warnings", []),
        )

    def _classify_question(self, question: str) -> QuestionType:
        """分类问题类型"""
        q = question.lower()
        scores = {}

        for qtype, keywords in self.KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in q)
            scores[qtype] = score

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return QuestionType.GENERAL
        return best

    def _extract_data(
        self,
        udm: DestinyModel,
        qtype: QuestionType,
        cv_result: dict,
    ) -> dict:
        """提取相关数据"""
        data = {
            "methods": cv_result.get("available_methods", []),
            "key_points": [],
            "warnings": [],
        }

        # 从交叉验证共识中提取相关内容
        for c in cv_result.get("consensus", []):
            aspect = c.aspect
            if qtype == QuestionType.CAREER and "事业" in aspect:
                data["key_points"].append(c.finding)
            elif qtype == QuestionType.LOVE and "感情" in aspect:
                data["key_points"].append(c.finding)
            elif qtype == QuestionType.HEALTH and "健康" in aspect:
                data["key_points"].append(c.finding)
            elif qtype == QuestionType.WEALTH and "财" in aspect:
                data["key_points"].append(c.finding)
            elif qtype == QuestionType.PERSONALITY and "性格" in aspect:
                data["key_points"].append(c.finding)

        # 八字特征
        if udm.features:
            for f in udm.features:
                if qtype == QuestionType.CAREER and any(kw in f for kw in ["七杀", "正官", "事业"]):
                    data["key_points"].append(f"八字：{f}")
                elif qtype == QuestionType.LOVE and any(kw in f for kw in ["冲", "合", "桃花"]):
                    data["key_points"].append(f"八字：{f}")
                elif qtype == QuestionType.HEALTH and any(kw in f for kw in ["五行", "体质"]):
                    data["key_points"].append(f"八字：{f}")

        # 日主五行（性格用）
        if qtype == QuestionType.PERSONALITY and udm.day_master:
            wuxing_desc = {
                "木": "仁慈直率，有主见",
                "火": "热情开朗，行动力强",
                "土": "稳重踏实，包容心强",
                "金": "刚毅果断，讲原则",
                "水": "聪明灵活，适应力强",
            }
            desc = wuxing_desc.get(udm.day_master_wuxing, "")
            if desc:
                data["key_points"].append(f"日主{udm.day_master}（{udm.day_master_wuxing}）：{desc}")

        # 五行统计（健康用）
        if qtype == QuestionType.HEALTH:
            counts = udm.get_wuxing_count()
            for wx, cnt in counts.items():
                if cnt == 0:
                    data["warnings"].append(f"五行缺{wx}，注意相关脏腑")

        # 占星太阳星座（性格用）
        if qtype == QuestionType.PERSONALITY and udm.astro_chart:
            sun = udm.astro_chart.get("sun_sign", "")
            if sun:
                data["key_points"].append(f"太阳星座{sun}：外在表现的核心特质")
            moon = udm.astro_chart.get("moon_sign", "")
            if moon:
                data["key_points"].append(f"月亮星座{moon}：内在情绪模式")

        # 冲突
        for conflict in cv_result.get("conflicts", []):
            if qtype == QuestionType.GENERAL or self._conflict_relevant(conflict.aspect, qtype):
                data["warnings"].append(
                    f"术法分歧：{conflict.method_a}认为{conflict.finding_a}，"
                    f"{conflict.method_b}认为{conflict.finding_b}"
                )

        return data

    def _conflict_relevant(self, aspect: str, qtype: QuestionType) -> bool:
        """判断冲突是否与问题类型相关"""
        mapping = {
            QuestionType.CAREER: ["事业", "工作"],
            QuestionType.LOVE: ["感情", "婚姻"],
            QuestionType.HEALTH: ["健康", "体质"],
            QuestionType.WEALTH: ["财", "富"],
            QuestionType.PERSONALITY: ["性格", "特质"],
        }
        keywords = mapping.get(qtype, [])
        return any(kw in aspect for kw in keywords)

    def _generate_answer(
        self,
        qtype: QuestionType,
        data: dict,
        cv_result: dict,
    ) -> str:
        """生成回答文本"""
        points = data.get("key_points", [])

        if not points:
            return f"根据现有排盘数据，关于「{qtype.value}」的可判定信息有限。建议结合具体事件分析。"

        # 构建回答
        parts = []
        parts.append(f"【{qtype.value}分析】")

        # 核心判断
        if qtype == QuestionType.CAREER:
            parts.append(self._career_analysis(points))
        elif qtype == QuestionType.LOVE:
            parts.append(self._love_analysis(points))
        elif qtype == QuestionType.HEALTH:
            parts.append(self._health_analysis(points))
        elif qtype == QuestionType.WEALTH:
            parts.append(self._wealth_analysis(points))
        elif qtype == QuestionType.PERSONALITY:
            parts.append(self._personality_analysis(points))
        else:
            parts.append(self._general_analysis(points))

        # 数据支持
        methods = data.get("methods", [])
        if methods:
            parts.append(f"\n（基于{len(methods)}术交叉验证：{'、'.join(methods)}）")

        return "\n".join(parts)

    def _career_analysis(self, points: List[str]) -> str:
        has_drive = any("七杀" in p or "正官" in p for p in points)
        has_leadership = any("领导" in p or "管理" in p for p in points)

        if has_drive and has_leadership:
            return "命盘显示事业驱动力强，有领导潜质。适合竞争性、管理类工作。"
        elif has_drive:
            return "命盘显示事业心重，自我驱动力强。适合有挑战性的工作。"
        elif has_leadership:
            return "命盘显示有领导气质，适合团队管理或统筹类工作。"
        return "事业方向需结合大运流年具体分析。"

    def _love_analysis(self, points: List[str]) -> str:
        has_chong = any("冲" in p for p in points)
        has_he = any("合" in p for p in points)

        if has_chong and has_he:
            return "感情路上有波折也有机缘，需把握时机、化解冲突。"
        elif has_chong:
            return "感情易有波动，需多注意沟通与包容。"
        elif has_he:
            return "感情缘分较好，人际关系和谐。"
        return "感情状况平稳，无特别明显的吉凶信号。"

    def _health_analysis(self, points: List[str]) -> str:
        missing = [p for p in points if "缺" in p]
        if missing:
            return "五行有偏，" + "；".join(missing) + "。建议通过饮食、作息调理。"
        return "整体体质无明显偏颇，保持规律生活即可。"

    def _wealth_analysis(self, points: List[str]) -> str:
        has_cai = any("财" in p for p in points)
        if has_cai:
            return "命盘有财星信息，财运有发展空间。"
        return "财运平稳，建议稳健理财，不宜冒险。"

    def _personality_analysis(self, points: List[str]) -> str:
        parts = []
        for p in points[:3]:
            parts.append(p)
        return "；".join(parts) + "。"

    def _general_analysis(self, points: List[str]) -> str:
        return "综合判断：" + "；".join(points[:3]) + "。"

    def _calc_confidence(
        self,
        data: dict,
        cv_result: dict,
    ) -> ConfidenceLevel:
        """计算回答置信度"""
        # 基于交叉验证的置信度
        overall = cv_result.get("overall_confidence")
        if overall and overall.value == "高":
            return ConfidenceLevel.HIGH

        # 基于数据丰富度
        points_count = len(data.get("key_points", []))
        if points_count >= 3:
            return ConfidenceLevel.HIGH
        elif points_count >= 1:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW
