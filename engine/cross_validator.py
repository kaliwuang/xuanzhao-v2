#!/usr/bin/env python3
"""
玄照 v2.0 - 七术交叉验证引擎

比对多个术法的结果，找出共识和冲突，计算置信度。
"""
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum
from .udm import DestinyModel


class ConfidenceLevel(Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"
    CONTRADICTORY = "矛盾"


@dataclass
class ConsensusItem:
    aspect: str
    finding: str
    supporting_methods: List[str]
    confidence: ConfidenceLevel


@dataclass
class ConflictItem:
    aspect: str
    method_a: str
    finding_a: str
    method_b: str
    finding_b: str
    suggestion: str


class CrossValidator:
    """交叉验证器"""

    ASPECTS = ["性格", "事业", "财运", "感情", "健康", "学业", "人际关系"]

    def __init__(self, udm: DestinyModel):
        self.udm = udm

    def validate(self) -> dict:
        results = {
            "consensus": [],
            "conflicts": [],
            "overall_confidence": ConfidenceLevel.MEDIUM,
            "method_count": len(self.udm.get_available_methods()),
            "available_methods": self.udm.get_available_methods(),
        }

        # 1. 五行属性交叉验证
        results["consensus"].extend(self._validate_wuxing())

        # 2. 性格特质交叉验证
        results["consensus"].extend(self._validate_personality())

        # 3. 事业方向交叉验证
        results["consensus"].extend(self._validate_career())

        # 4. 感情婚姻交叉验证
        results["consensus"].extend(self._validate_relationship())

        # 5. 健康体质交叉验证
        results["consensus"].extend(self._validate_health())

        # 6. 冲突检测
        results["conflicts"].extend(self._detect_conflicts())

        # 7. 综合置信度
        results["overall_confidence"] = self._calc_overall_confidence(results)

        return results

    def _validate_wuxing(self) -> List[ConsensusItem]:
        items = []
        methods = []
        findings = []

        # 八字日主五行
        if self.udm.day_master_wuxing:
            methods.append("八字")
            findings.append(f"日主属{self.udm.day_master_wuxing}")

        # 紫微主星五行
        if self.udm.ziwei_chart:
            stars = self.udm.ziwei_chart.get("star_placements", {})
            ziwei_pos = stars.get("紫微", "")
            if ziwei_pos:
                methods.append("紫微")
                findings.append(f"紫微在{ziwei_pos}")

        # 占星太阳星座元素
        if self.udm.astro_chart:
            sun_element = self.udm.astro_chart.get("sun_element", "")
            if sun_element:
                methods.append("占星")
                findings.append(f"太阳星座属{sun_element}")

        if len(methods) >= 2:
            items.append(ConsensusItem(
                aspect="五行属性",
                finding="；".join(findings),
                supporting_methods=methods,
                confidence=ConfidenceLevel.HIGH if len(methods) >= 3 else ConfidenceLevel.MEDIUM
            ))

        return items

    def _validate_personality(self) -> List[ConsensusItem]:
        items = []
        methods = []
        traits = []

        # 八字特征
        if self.udm.features:
            methods.append("八字")
            for f in self.udm.features[:3]:
                if "七杀" in f:
                    traits.append("性格刚强，有领导力")
                elif "正官" in f:
                    traits.append("守规矩，责任心强")
                elif "印" in f:
                    traits.append("善于学习，有涵养")
                elif "财" in f:
                    traits.append("务实，重视物质生活")
                elif "食伤" in f:
                    traits.append("表达力强，有创意")
                elif "比劫" in f:
                    traits.append("重情义，竞争意识强")

        # 占星特征
        if self.udm.astro_chart:
            methods.append("占星")
            sun_sign = self.udm.astro_chart.get("sun_sign", "")
            sign_traits = {
                "白羊": "冲动直率", "金牛": "稳重务实", "双子": "灵活多变",
                "巨蟹": "敏感细腻", "狮子": "自信大方", "处女": "追求完美",
                "天秤": "优雅平衡", "天蝎": "深沉执着", "射手": "乐观自由",
                "摩羯": "踏实进取", "水瓶": "独立创新", "双鱼": "浪漫感性",
            }
            if sun_sign in sign_traits:
                traits.append(sign_traits[sun_sign])

        if traits:
            items.append(ConsensusItem(
                aspect="性格特质",
                finding="；".join(list(set(traits))),
                supporting_methods=methods,
                confidence=ConfidenceLevel.HIGH if len(methods) >= 2 else ConfidenceLevel.MEDIUM
            ))

        return items

    def _validate_career(self) -> List[ConsensusItem]:
        items = []
        methods = []

        # 八字：看官杀和食伤
        if self.udm.shishen_gan:
            methods.append("八字")
            ss = self.udm.shishen_gan
            has_guan = any("官" in v for v in ss.values())
            has_sha = any("杀" in v for v in ss.values())
            has_shi = any("食" in v or "伤" in v for v in ss.values())

            if has_guan or has_sha:
                items.append(ConsensusItem(
                    aspect="事业方向",
                    finding="适合管理、领导类工作",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM
                ))
            if has_shi:
                items.append(ConsensusItem(
                    aspect="事业方向",
                    finding="适合技术、创意、表达类工作",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM
                ))

        # 奇门：看开门、生门
        if self.udm.qimen_chart:
            men = self.udm.qimen_chart.get("ba_men", {})
            kai = [k for k, v in men.items() if v == "开门"]
            sheng = [k for k, v in men.items() if v == "生门"]
            if kai:
                items.append(ConsensusItem(
                    aspect="事业方向",
                    finding=f"开门在{kai[0]}，事业有发展空间",
                    supporting_methods=["奇门"],
                    confidence=ConfidenceLevel.MEDIUM
                ))

        return items

    def _validate_relationship(self) -> List[ConsensusItem]:
        items = []

        # 八字：看夫妻宫
        if self.udm.bazi_day and self.udm.bazi_time:
            chong = self.udm.get_chong()
            he = self.udm.get_he()
            if any("午" in c and "子" in c for c in chong):
                items.append(ConsensusItem(
                    aspect="感情婚姻",
                    finding="子午冲，感情多波折",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM
                ))
            if any("午" in h and "未" in h for h in he):
                items.append(ConsensusItem(
                    aspect="感情婚姻",
                    finding="午未合，感情有缘分",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM
                ))

        # 紫微：看夫妻宫
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "夫妻":
                    stars = p.get("stars", [])
                    if stars:
                        items.append(ConsensusItem(
                            aspect="感情婚姻",
                            finding=f"夫妻宫有{'、'.join(stars)}",
                            supporting_methods=["紫微"],
                            confidence=ConfidenceLevel.MEDIUM
                        ))

        return items

    def _validate_health(self) -> List[ConsensusItem]:
        items = []

        # 八字五行平衡
        counts = self.udm.get_wuxing_count()
        if counts:
            max_wx = max(counts, key=counts.get)
            min_wx = min(counts, key=counts.get)
            if counts[max_wx] >= 4:
                items.append(ConsensusItem(
                    aspect="健康体质",
                    finding=f"{max_wx}过旺，注意{max_wx}行相关脏腑",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM
                ))
            if counts[min_wx] == 0:
                items.append(ConsensusItem(
                    aspect="健康体质",
                    finding=f"{min_wx}缺失，注意{min_wx}行相关脏腑",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM
                ))

        # 占星：看火星、土星相位
        if self.udm.astro_chart:
            aspects = self.udm.astro_chart.get("aspects", [])
            for asp in aspects:
                if asp.get("aspect") == "四分" and "火星" in [asp.get("p1"), asp.get("p2")]:
                    items.append(ConsensusItem(
                        aspect="健康体质",
                        finding="火星刑克，注意炎症、外伤",
                        supporting_methods=["占星"],
                        confidence=ConfidenceLevel.LOW
                    ))

        return items

    def _detect_conflicts(self) -> List[ConflictItem]:
        conflicts = []

        # 检测术法间的直接矛盾
        # 示例：八字说"子午冲不利婚姻" vs 紫微说"夫妻宫稳定"

        # 检查八字和紫微在感情上的冲突
        bazi_bad = False
        ziwei_good = False

        if self.udm.bazi_day and self.udm.bazi_time:
            chong = self.udm.get_chong()
            if any("子午" in c for c in chong):
                bazi_bad = True

        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "夫妻":
                    stars = p.get("stars", [])
                    if "紫微" in stars or "天府" in stars:
                        ziwei_good = True

        if bazi_bad and ziwei_good:
            conflicts.append(ConflictItem(
                aspect="感情婚姻",
                method_a="八字",
                finding_a="子午冲，感情多波折",
                method_b="紫微",
                finding_b="夫妻宫有紫微/天府，感情稳定",
                suggestion="八字看内在张力，紫微看整体格局，需结合大运流年综合判断"
            ))

        return conflicts

    def _calc_overall_confidence(self, results: dict) -> ConfidenceLevel:
        consensus = len(results["consensus"])
        conflicts = len(results["conflicts"])
        methods = results["method_count"]

        if methods >= 5 and consensus >= 5 and conflicts == 0:
            return ConfidenceLevel.HIGH
        elif methods >= 3 and consensus >= 3:
            return ConfidenceLevel.MEDIUM
        elif conflicts > 0:
            return ConfidenceLevel.CONTRADICTORY
        else:
            return ConfidenceLevel.LOW
