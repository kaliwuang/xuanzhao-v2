#!/usr/bin/env python3
"""
玄照 v2.0 - 问答引擎

接收用户问题，解析类型，从UDM提取数据，生成带置信度的回答。
优先使用 LLM 生成深度分析，LLM 失败时回退到规则引擎。
"""
import json
import logging
from typing import Optional, List, Dict
from enum import Enum

from .udm import DestinyModel
from .cross_validator import CrossValidator

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    CAREER = "事业"
    LOVE = "感情"
    HEALTH = "健康"
    WEALTH = "财运"
    PERSONALITY = "性格"
    ACADEMIC = "学业"
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
        QuestionType.ACADEMIC: [
            "学业", "考试", "升学", "考研", "高考", "读书", "学习",
            "成绩", "留学", "毕业", "论文", "证书", "考公", "上岸",
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

        # 生成回答（LLM 优先，规则回退）
        answer_text = self._generate_answer(qtype, data, cv_result, udm=udm, question=question)

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
            elif qtype == QuestionType.ACADEMIC and "学业" in aspect:
                data["key_points"].append(c.finding)
            elif qtype == QuestionType.GENERAL:
                data["key_points"].append(f"[{c.aspect}] {c.finding}")

        # 八字特征（不限问题类型，全部收录）
        if udm.features:
            for f in udm.features[:5]:
                if qtype == QuestionType.CAREER and any(kw in f for kw in ["七杀", "正官", "事业"]):
                    data["key_points"].append(f"八字：{f}")
                elif qtype == QuestionType.LOVE and any(kw in f for kw in ["冲", "合", "桃花"]):
                    data["key_points"].append(f"八字：{f}")
                elif qtype == QuestionType.HEALTH and any(kw in f for kw in ["五行", "体质"]):
                    data["key_points"].append(f"八字：{f}")
                elif qtype == QuestionType.ACADEMIC and any(kw in f for kw in ["印", "食伤", "文昌"]):
                    data["key_points"].append(f"八字：{f}")
                elif qtype == QuestionType.GENERAL:
                    data["key_points"].append(f"八字：{f}")

        # 日主五行（性格/综合用）
        if qtype in (QuestionType.PERSONALITY, QuestionType.GENERAL) and udm.day_master:
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

        # 占星太阳星座（性格/综合用）
        if qtype in (QuestionType.PERSONALITY, QuestionType.GENERAL) and udm.astro_chart:
            sun = udm.astro_chart.get("sun_sign", "")
            if sun:
                data["key_points"].append(f"太阳星座{sun}：外在表现的核心特质")
            moon = udm.astro_chart.get("moon_sign", "")
            if moon:
                data["key_points"].append(f"月亮星座{moon}：内在情绪模式")

        # 紫微关键宫位（事业/财运/感情/综合用）
        if udm.ziwei_chart and qtype in (QuestionType.CAREER, QuestionType.WEALTH, QuestionType.LOVE, QuestionType.GENERAL):
            palaces = udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                name = p.get("name", "")
                stars = p.get("stars", [])
                if not stars:
                    continue
                if qtype == QuestionType.CAREER and name == "官禄":
                    data["key_points"].append(f"紫微官禄宫：{'、'.join(stars)}")
                elif qtype == QuestionType.WEALTH and name == "财帛":
                    data["key_points"].append(f"紫微财帛宫：{'、'.join(stars)}")
                elif qtype == QuestionType.LOVE and name == "夫妻":
                    data["key_points"].append(f"紫微夫妻宫：{'、'.join(stars)}")
                elif qtype == QuestionType.GENERAL and name in ("命宫", "官禄", "财帛", "夫妻"):
                    data["key_points"].append(f"紫微{name}宫：{'、'.join(stars)}")

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
            QuestionType.ACADEMIC: ["学业", "学习"],
        }
        keywords = mapping.get(qtype, [])
        return any(kw in aspect for kw in keywords)

    def _generate_answer(
        self,
        qtype: QuestionType,
        data: dict,
        cv_result: dict,
        udm: DestinyModel = None,
        question: str = "",
    ) -> str:
        """生成回答文本——优先使用 LLM 深度分析，失败时回退规则引擎"""
        # 优先 LLM
        if udm and question:
            try:
                llm_answer = self._llm_generate_answer(qtype, data, cv_result, udm, question)
                if llm_answer:
                    return llm_answer
            except Exception as e:
                logger.warning(f"LLM 问答生成失败，回退规则引擎: {e}")

        # 回退：规则引擎
        return self._rule_generate_answer(qtype, data)

    def _llm_generate_answer(
        self,
        qtype: QuestionType,
        data: dict,
        cv_result: dict,
        udm: DestinyModel,
        question: str,
    ) -> Optional[str]:
        """使用 LLM 生成深度命理分析"""
        from engine.llm_client import get_llm_client

        # 构造命盘摘要
        chart_summary = self._build_chart_summary(udm, qtype)

        # 构造交叉验证摘要
        cv_summary = self._build_cv_summary(cv_result, qtype)

        system_prompt = f"""你是一位精通七术（八字、紫微、占星、六爻、奇门遁甲、大六壬、太乙）的命理分析师。

你的回答规范：
1. **数据驱动**：每一个判断都必须引用命盘中的具体数据（天干地支、星曜、宫位、门星等）
2. **多术交叉**：尽量综合多种术法的数据来支撑判断
3. **具体而非笼统**：不说"运势不错"，要说"日主壬水坐午月失令，但有庚金生扶"
4. **置信度校准**：多个术法指向一致时给出高置信度判断，仅有单一术法数据时降低置信度
5. **实用建议**：最后给出可操作的建议
6. 控制在300字以内"""

        user_prompt = f"""命盘数据摘要：
{chart_summary}

交叉验证结果：
{cv_summary}

用户的问题：{question}
问题类型：{qtype.value}

请基于以上命盘数据进行深度分析，直接回答用户问题。引用具体数据，给出实用建议。"""

        llm = get_llm_client()
        result = llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=800,
        )

        # LLM 返回错误标记时视为失败
        if result.startswith("[LLM"):
            return None

        return result

    def _build_chart_summary(self, udm: DestinyModel, qtype: QuestionType) -> str:
        """构造命盘数据摘要，供 LLM 参考"""
        parts = []

        # 八字核心数据（始终包含）
        if udm.bazi_year:
            pillars = []
            for label, p in [("年柱", udm.bazi_year), ("月柱", udm.bazi_month),
                             ("日柱", udm.bazi_day), ("时柱", udm.bazi_time)]:
                if p:
                    pillars.append(f"{label}：{p.ganzhi}")
            parts.append("【八字】" + "，".join(pillars))
            if udm.day_master:
                parts.append(f"日主：{udm.day_master}（{udm.day_master_wuxing}）")
            if udm.shishen_gan:
                ss_str = "，".join(f"{k}={v}" for k, v in udm.shishen_gan.items())
                parts.append(f"十神（天干）：{ss_str}")
            if udm.nayin:
                parts.append(f"纳音：{', '.join(f'{k}={v}' for k, v in udm.nayin.items())}")
            if udm.features:
                parts.append(f"特征：{'；'.join(udm.features[:6])}")
            if udm.tiaohou:
                parts.append(f"调候用神：{udm.tiaohou}")

        # 紫微数据
        if udm.ziwei_chart:
            parts.append(f"【紫微】命宫：{udm.ziwei_chart.get('ming_gong', '?')}")
            wj = udm.ziwei_chart.get("wuxing_ju", {})
            if wj:
                parts.append(f"五行局：{wj.get('wuxing', '?')}{wj.get('ju_shu', '?')}局")
            sihua = udm.ziwei_chart.get("sihua", {})
            if sihua:
                parts.append(f"四化：{', '.join(f'{k}→{v}' for k, v in sihua.items())}")
            palaces = udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("stars") and p.get("name") in ("命宫", "官禄", "财帛", "夫妻", "疾厄"):
                    parts.append(f"  {p['name']}宫：{'、'.join(p['stars'])}")

        # 占星数据
        if udm.astro_chart:
            parts.append(f"【占星】太阳：{udm.astro_chart.get('sun_sign', '?')}，月亮：{udm.astro_chart.get('moon_sign', '?')}，上升：{udm.astro_chart.get('ascendant_sign', '?')}")
            aspects = udm.astro_chart.get("aspects", [])
            if aspects:
                asp_strs = [f"{a.get('p1','')}{a.get('aspect','')}{a.get('p2','')}" for a in aspects[:5]]
                parts.append(f"主要相位：{', '.join(asp_strs)}")

        # 奇门数据
        if udm.qimen_chart:
            parts.append(f"【奇门】{udm.qimen_chart.get('ju_name', '?')}")
            men = udm.qimen_chart.get("ba_men", {})
            if men:
                parts.append(f"八门：{', '.join(f'{k}={v}' for k, v in list(men.items())[:4])}")

        # 六壬数据
        if udm.liuren_chart:
            parts.append(f"【大六壬】月将：{udm.liuren_chart.get('yue_jiang', '?')}")
            sk = udm.liuren_chart.get("si_ke", [])
            if sk:
                parts.append(f"四课：{'，'.join(str(s) for s in sk)}")
            sc = udm.liuren_chart.get("san_chuan", [])
            if sc:
                parts.append(f"三传：{'→'.join(str(s) for s in sc)}")

        # 六爻数据
        if udm.liuyao_chart:
            bg = udm.liuyao_chart.get("ben_gua", {})
            if bg:
                parts.append(f"【六爻】本卦：{bg.get('name', '?')}，动爻：第{udm.liuyao_chart.get('dong_yao', '?')}爻")

        # 太乙数据
        if udm.taiyi_chart:
            parts.append(f"【太乙】太乙宫：{udm.taiyi_chart.get('taiyi_gong', '?')}，积年：{udm.taiyi_chart.get('ji_nian', '?')}")

        return "\n".join(parts)

    def _build_cv_summary(self, cv_result: dict, qtype: QuestionType) -> str:
        """构造交叉验证摘要"""
        parts = []

        # 相关共识
        consensus = cv_result.get("consensus", [])
        relevant_consensus = []
        for c in consensus:
            if qtype == QuestionType.GENERAL or self._conflict_relevant(c.aspect, qtype):
                relevant_consensus.append(f"[{c.confidence.value}置信] {c.aspect}：{c.finding}（支持术法：{'、'.join(c.supporting_methods)}）")
        if relevant_consensus:
            parts.append("共识：" + "；".join(relevant_consensus[:5]))

        # 相关冲突
        conflicts = cv_result.get("conflicts", [])
        relevant_conflicts = []
        for c in conflicts:
            if qtype == QuestionType.GENERAL or self._conflict_relevant(c.aspect, qtype):
                relevant_conflicts.append(f"{c.method_a}认为{c.finding_a}，但{c.method_b}认为{c.finding_b}。建议：{c.suggestion}")
        if relevant_conflicts:
            parts.append("术法分歧：" + "；".join(relevant_conflicts[:3]))

        # 总体置信度
        overall = cv_result.get("overall_confidence")
        if overall:
            parts.append(f"总体置信度：{overall.value}")

        return "\n".join(parts) if parts else "暂无交叉验证数据"

    def _rule_generate_answer(self, qtype: QuestionType, data: dict) -> str:
        """规则引擎生成回答（LLM 失败时的回退）"""
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
        elif qtype == QuestionType.ACADEMIC:
            parts.append(self._academic_analysis(points))
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

    def _academic_analysis(self, points: List[str]) -> str:
        has_yin = any("印" in p for p in points)
        has_shishang = any("食伤" in p for p in points)
        has_study_stars = any(kw in p for p in points for kw in ["文昌", "文曲", "天机", "水星"])

        if has_yin and has_study_stars:
            return "命盘显示学业运势强，印星得力又有文昌星助，学习效率高，考试运佳。"
        elif has_yin:
            return "命盘显示印星有力，善于学习吸收，适合系统化知识积累。"
        elif has_shishang:
            return "命盘显示食伤透干，思维活跃有创意，适合需要表达和创新的学业方向。"
        elif has_study_stars:
            return "命盘有学业相关星曜助力，学习运势不错。"
        return "学业需结合大运流年具体分析，建议把握印星旺盛的年份集中攻克难关。"

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
