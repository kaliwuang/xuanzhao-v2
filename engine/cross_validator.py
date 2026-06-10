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

        # 6. 财运交叉验证
        results["consensus"].extend(self._validate_wealth())

        # 7. 学业交叉验证
        results["consensus"].extend(self._validate_academic())

        # 8. 人际关系交叉验证
        results["consensus"].extend(self._validate_interpersonal())

        # 9. 冲突检测
        results["conflicts"].extend(self._detect_conflicts())

        # 9. 综合置信度
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

        # 紫微命宫主星（紫微斗数最核心的性格指标）
        if self.udm.ziwei_chart:
            star_placements = self.udm.ziwei_chart.get("star_placements", {})
            ming_gong = self.udm.ziwei_chart.get("ming_gong", "")
            # 找命宫内的主星
            ming_stars = []
            for star, palace in star_placements.items():
                if palace == ming_gong and star in (
                    "紫微", "天机", "太阳", "武曲", "天同", "廉贞",
                    "天府", "太阴", "贪狼", "巨门", "天相", "天梁",
                    "七杀", "破军",
                ):
                    ming_stars.append(star)
            if ming_stars:
                methods.append("紫微")
                ziwei_traits = {
                    "紫微": "领导力强，有王者气质，自信从容",
                    "天机": "聪明灵活，善于分析谋略，思维敏捷",
                    "太阳": "热情大方，光明磊落，乐于助人",
                    "武曲": "刚毅果断，重视效率和结果，执行力强",
                    "天同": "温和善良，随遇而安，人缘好",
                    "廉贞": "多才多艺，感情丰富，社交能力强",
                    "天府": "稳重踏实，有包容心，善于理财",
                    "太阴": "敏感细腻，有艺术气质，内心丰富",
                    "贪狼": "多才多艺，魅力十足，兴趣广泛",
                    "巨门": "口才好，善于表达和分析，观察力强",
                    "天相": "正直公正，善于协调，人缘佳",
                    "天梁": "有正义感，善于照顾人，有长者风范",
                    "七杀": "果断刚强，有魄力和行动力，敢闯敢拼",
                    "破军": "有开创力，不畏挑战，勇于革新",
                }
                for star in ming_stars[:2]:  # 最多取两颗主星
                    if star in ziwei_traits:
                        traits.append(f"命宫{star}：{ziwei_traits[star]}")

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
            if sheng:
                items.append(ConsensusItem(
                    aspect="事业方向",
                    finding=f"生门在{sheng[0]}，创业求新有增长潜力",
                    supporting_methods=["奇门"],
                    confidence=ConfidenceLevel.MEDIUM
                ))

        # 紫微：看官禄宫
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "官禄":
                    stars = p.get("stars", [])
                    if stars:
                        methods.append("紫微")
                        auspicious = [s for s in stars if s in ("紫微", "天府", "太阳", "天梁", "天相", "武曲")]
                        if auspicious:
                            items.append(ConsensusItem(
                                aspect="事业方向",
                                finding=f"官禄宫有{'、'.join(auspicious)}，事业格局较高",
                                supporting_methods=["紫微"],
                                confidence=ConfidenceLevel.HIGH if len(auspicious) >= 2 else ConfidenceLevel.MEDIUM
                            ))
                        else:
                            items.append(ConsensusItem(
                                aspect="事业方向",
                                finding=f"官禄宫主星{'、'.join(stars[:2])}，事业有特定方向",
                                supporting_methods=["紫微"],
                                confidence=ConfidenceLevel.MEDIUM
                            ))

        # 占星：看中天（MC）星座和太阳星座
        if self.udm.astro_chart:
            methods.append("占星")
            sun_sign = self.udm.astro_chart.get("sun_sign", "")
            mc = self.udm.astro_chart.get("mc", 0)
            career_signs = {
                "摩羯": "适合体制内、管理层、传统行业",
                "金牛": "适合金融、实业、稳定型行业",
                "狮子": "适合演艺、管理、需要展示的行业",
                "天蝎": "适合研究、调查、金融投资",
                "白羊": "适合创业、运动、开拓型行业",
                "双子": "适合传媒、教育、沟通型行业",
            }
            if sun_sign in career_signs:
                items.append(ConsensusItem(
                    aspect="事业方向",
                    finding=f"太阳{sun_sign}：{career_signs[sun_sign]}",
                    supporting_methods=["占星"],
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

        # 占星：看金星落座和第七宫
        if self.udm.astro_chart:
            planets = self.udm.astro_chart.get("planets", {})
            venus = planets.get("金星", {})
            if venus.get("sign"):
                love_styles = {
                    "金牛": "感情稳定，重视物质安全感",
                    "天蝎": "感情深沉，占有欲强",
                    "双鱼": "浪漫多情，容易陷入",
                    "天秤": "追求平衡和谐，善于经营",
                    "白羊": "热情直接，来得快去得快",
                    "巨蟹": "重感情，依赖性强",
                }
                venus_sign = venus["sign"]
                if venus_sign in love_styles:
                    items.append(ConsensusItem(
                        aspect="感情婚姻",
                        finding=f"金星{venus_sign}：{love_styles[venus_sign]}",
                        supporting_methods=["占星"],
                        confidence=ConfidenceLevel.MEDIUM
                    ))

            # 第七宫（下降点）星座
            asc = self.udm.astro_chart.get("ascendant_sign", "")
            if asc:
                # 上升对面就是第七宫头星座
                opposite_signs = {
                    "白羊": "天秤", "金牛": "天蝎", "双子": "射手",
                    "巨蟹": "摩羯", "狮子": "水瓶", "处女": "双鱼",
                    "天秤": "白羊", "天蝎": "金牛", "射手": "双子",
                    "摩羯": "巨蟹", "水瓶": "狮子", "双鱼": "处女",
                }
                desc_sign = opposite_signs.get(asc, "")
                if desc_sign:
                    items.append(ConsensusItem(
                        aspect="感情婚姻",
                        finding=f"第七宫头{desc_sign}，伴侣类型倾向{desc_sign}特质",
                        supporting_methods=["占星"],
                        confidence=ConfidenceLevel.LOW
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

        # 紫微：看疾厄宫
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "疾厄":
                    stars = p.get("stars", [])
                    if stars:
                        # 吉星在疾厄宫有化解力
                        good_stars = [s for s in stars if s in ("天同", "天梁", "天府", "紫微")]
                        bad_stars = [s for s in stars if s in ("七杀", "破军", "贪狼", "廉贞", "擎羊", "陀罗")]
                        if good_stars:
                            items.append(ConsensusItem(
                                aspect="健康体质",
                                finding=f"疾厄宫有{'、'.join(good_stars)}，有化解之力，病后恢复快",
                                supporting_methods=["紫微"],
                                confidence=ConfidenceLevel.MEDIUM
                            ))
                        if bad_stars:
                            items.append(ConsensusItem(
                                aspect="健康体质",
                                finding=f"疾厄宫有{'、'.join(bad_stars)}，需注意突发性疾病或手术",
                                supporting_methods=["紫微"],
                                confidence=ConfidenceLevel.MEDIUM
                            ))

        return items

    def _validate_wealth(self) -> List[ConsensusItem]:
        """财运交叉验证——八字财星、紫微财帛宫、奇门生门、占星金星四维比对"""
        items = []

        # 八字：看财星透干
        if self.udm.shishen_gan:
            ss = self.udm.shishen_gan
            has_zhengcai = any("正财" in v for v in ss.values())
            has_piancai = any("偏财" in v for v in ss.values())
            if has_zhengcai or has_piancai:
                finding_parts = []
                if has_zhengcai:
                    finding_parts.append("正财透干，正当收入有保障")
                if has_piancai:
                    finding_parts.append("偏财透干，有意外之财机会")
                items.append(ConsensusItem(
                    aspect="财运",
                    finding="；".join(finding_parts),
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.HIGH if has_zhengcai and has_piancai else ConfidenceLevel.MEDIUM,
                ))

        # 八字：看财星是否被克（比劫夺财）
        if self.udm.features:
            if any("比劫" in f and "财" in f for f in self.udm.features):
                items.append(ConsensusItem(
                    aspect="财运",
                    finding="比劫夺财，需防破财或合伙纠纷",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM,
                ))

        # 紫微：看财帛宫
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "财帛":
                    stars = p.get("stars", [])
                    if stars:
                        auspicious = [s for s in stars if s in ("武曲", "天府", "太阴", "紫微", "太阳")]
                        if auspicious:
                            items.append(ConsensusItem(
                                aspect="财运",
                                finding=f"财帛宫有{'、'.join(auspicious)}，财运格局较高",
                                supporting_methods=["紫微"],
                                confidence=ConfidenceLevel.HIGH if len(auspicious) >= 2 else ConfidenceLevel.MEDIUM,
                            ))
                        else:
                            items.append(ConsensusItem(
                                aspect="财运",
                                finding=f"财帛宫主星{'、'.join(stars[:2])}，财运有特定模式",
                                supporting_methods=["紫微"],
                                confidence=ConfidenceLevel.MEDIUM,
                            ))

        # 奇门：看生门
        if self.udm.qimen_chart:
            men = self.udm.qimen_chart.get("ba_men", {})
            sheng = [k for k, v in men.items() if v == "生门"]
            if sheng:
                items.append(ConsensusItem(
                    aspect="财运",
                    finding=f"生门在{sheng[0]}，求财有门路",
                    supporting_methods=["奇门"],
                    confidence=ConfidenceLevel.MEDIUM,
                ))

        # 占星：看金星落座
        if self.udm.astro_chart:
            planets = self.udm.astro_chart.get("planets", {})
            venus = planets.get("金星", {})
            if venus.get("sign"):
                wealth_styles = {
                    "金牛": "金星入庙，天生财运好，重视物质积累",
                    "天秤": "金星入庙，社交型理财，善于合作求财",
                    "双鱼": "金星旺相，直觉型理财，偏财运佳",
                    "摩羯": "务实理财，长期积累，大器晚成",
                    "处女": "精打细算，善于管理财务细节",
                    "天蝎": "投资型理财，善用杠杆和深度研究",
                }
                venus_sign = venus["sign"]
                if venus_sign in wealth_styles:
                    items.append(ConsensusItem(
                        aspect="财运",
                        finding=f"金星{venus_sign}：{wealth_styles[venus_sign]}",
                        supporting_methods=["占星"],
                        confidence=ConfidenceLevel.MEDIUM,
                    ))

        return items

    def _validate_academic(self) -> List[ConsensusItem]:
        """学业交叉验证——八字印星、紫微父母宫/官禄宫、占星水星"""
        items = []

        # 八字：看印星（正印/偏印代表学习能力）
        if self.udm.shishen_gan:
            ss = self.udm.shishen_gan
            has_zhengyin = any("正印" in v for v in ss.values())
            has_pianyin = any("偏印" in v for v in ss.values())
            if has_zhengyin or has_pianyin:
                finding_parts = []
                if has_zhengyin:
                    finding_parts.append("正印透干，学习踏实，善得师长助力")
                if has_pianyin:
                    finding_parts.append("偏印透干，思维独特，适合偏门学问")
                items.append(ConsensusItem(
                    aspect="学业",
                    finding="；".join(finding_parts),
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.HIGH if has_zhengyin and has_pianyin else ConfidenceLevel.MEDIUM,
                ))

        # 八字：看食伤（代表聪明才智和表达力）
        if self.udm.features:
            if any("食伤" in f for f in self.udm.features):
                items.append(ConsensusItem(
                    aspect="学业",
                    finding="食伤透干，聪明有创意，表达力强",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM,
                ))

        # 紫微：看官禄宫（学业方向）
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "官禄":
                    stars = p.get("stars", [])
                    study_stars = [s for s in stars if s in ("天机", "天梁", "太阳", "太阴", "文昌", "文曲")]
                    if study_stars:
                        items.append(ConsensusItem(
                            aspect="学业",
                            finding=f"官禄宫有{'、'.join(study_stars)}，学业运势不错",
                            supporting_methods=["紫微"],
                            confidence=ConfidenceLevel.HIGH if len(study_stars) >= 2 else ConfidenceLevel.MEDIUM,
                        ))

        # 占星：看水星（思维和学习能力）
        if self.udm.astro_chart:
            planets = self.udm.astro_chart.get("planets", {})
            mercury = planets.get("水星", {})
            if mercury.get("sign"):
                study_styles = {
                    "双子": "水星入庙，思维敏捷，学习速度快，多才多艺",
                    "处女": "水星入庙，分析力强，注重细节，善于钻研",
                    "水瓶": "水星旺相，创新思维，善于跨学科整合",
                    "天蝎": "深度思维，善于洞察本质，研究型学习",
                    "摩羯": "系统化学习，目标明确，持之以恒",
                }
                mercury_sign = mercury["sign"]
                if mercury_sign in study_styles:
                    items.append(ConsensusItem(
                        aspect="学业",
                        finding=f"水星{mercury_sign}：{study_styles[mercury_sign]}",
                        supporting_methods=["占星"],
                        confidence=ConfidenceLevel.MEDIUM,
                    ))

        return items

    def _validate_interpersonal(self) -> List[ConsensusItem]:
        """人际关系交叉验证——八字比劫/正官/冲合、紫微兄弟宫/仆役宫、占星水星/金星"""
        items = []

        # 八字：看比劫（兄弟朋友关系）
        if self.udm.shishen_gan:
            ss = self.udm.shishen_gan
            has_bijie = any("比肩" in v or "劫财" in v for v in ss.values())
            if has_bijie:
                items.append(ConsensusItem(
                    aspect="人际关系",
                    finding="比劫透干，朋友多、人缘广，但也需防合伙纠纷",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM,
                ))

        # 八字：看正官（社交圈层、上级关系）
        if self.udm.shishen_gan:
            ss = self.udm.shishen_gan
            has_guan = any("正官" in v for v in ss.values())
            if has_guan:
                items.append(ConsensusItem(
                    aspect="人际关系",
                    finding="正官透干，善于与上级相处，社交层次较高",
                    supporting_methods=["八字"],
                    confidence=ConfidenceLevel.MEDIUM,
                ))

        # 八字：看冲合（人际动态）
        chong = self.udm.get_chong()
        he = self.udm.get_he()
        if chong:
            items.append(ConsensusItem(
                aspect="人际关系",
                finding=f"有冲（{'、'.join(chong[:2])}），人际关系有波折或变动",
                supporting_methods=["八字"],
                confidence=ConfidenceLevel.LOW,
            ))
        if he:
            items.append(ConsensusItem(
                aspect="人际关系",
                finding=f"有合（{'、'.join(he[:2])}），人缘好，善于合作",
                supporting_methods=["八字"],
                confidence=ConfidenceLevel.MEDIUM,
            ))

        # 紫微：看兄弟宫
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "兄弟":
                    stars = p.get("stars", [])
                    if stars:
                        good_stars = [s for s in stars if s in ("天同", "天梁", "天府", "紫微", "太阳")]
                        bad_stars = [s for s in stars if s in ("七杀", "破军", "擎羊", "陀罗", "火星", "铃星")]
                        if good_stars:
                            items.append(ConsensusItem(
                                aspect="人际关系",
                                finding=f"兄弟宫有{'、'.join(good_stars)}，手足助力多，朋友圈质量高",
                                supporting_methods=["紫微"],
                                confidence=ConfidenceLevel.HIGH if len(good_stars) >= 2 else ConfidenceLevel.MEDIUM,
                            ))
                        elif bad_stars:
                            items.append(ConsensusItem(
                                aspect="人际关系",
                                finding=f"兄弟宫有{'、'.join(bad_stars)}，需注意手足或朋友间纠纷",
                                supporting_methods=["紫微"],
                                confidence=ConfidenceLevel.MEDIUM,
                            ))

        # 紫微：看仆役宫（交友宫）
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "仆役":
                    stars = p.get("stars", [])
                    if stars:
                        items.append(ConsensusItem(
                            aspect="人际关系",
                            finding=f"仆役宫有{'、'.join(stars[:3])}，下属或合作伙伴类型已定",
                            supporting_methods=["紫微"],
                            confidence=ConfidenceLevel.LOW,
                        ))

        # 占星：看水星（沟通能力）和金星（社交魅力）
        if self.udm.astro_chart:
            planets = self.udm.astro_chart.get("planets", {})
            mercury = planets.get("水星", {})
            venus = planets.get("金星", {})
            if mercury.get("sign"):
                comm_styles = {
                    "双子": "水星入庙，口才佳，善于社交沟通",
                    "天秤": "水星旺相，善于协调，人际关系和谐",
                    "处女": "水星入庙，分析型沟通，交友谨慎",
                    "射手": "直率坦诚，朋友圈广泛但不深",
                }
                merc_sign = mercury["sign"]
                if merc_sign in comm_styles:
                    items.append(ConsensusItem(
                        aspect="人际关系",
                        finding=f"水星{merc_sign}：{comm_styles[merc_sign]}",
                        supporting_methods=["占星"],
                        confidence=ConfidenceLevel.MEDIUM,
                    ))
            if venus.get("sign"):
                social_styles = {
                    "天秤": "金星入庙，天生社交高手，人缘极佳",
                    "金牛": "金星入庙，交友稳定，重视忠诚",
                    "双鱼": "金星旺相，共情力强，容易获得好感",
                    "狮子": "热情大方，社交场合亮眼",
                }
                venus_sign = venus["sign"]
                if venus_sign in social_styles:
                    items.append(ConsensusItem(
                        aspect="人际关系",
                        finding=f"金星{venus_sign}：{social_styles[venus_sign]}",
                        supporting_methods=["占星"],
                        confidence=ConfidenceLevel.MEDIUM,
                    ))

        return items

    def _detect_conflicts(self) -> List[ConflictItem]:
        conflicts = []
        chong = self.udm.get_chong()
        he = self.udm.get_he()
        features = self.udm.features or []
        shishen = self.udm.shishen_gan or {}

        # === 1. 感情婚姻冲突：八字 vs 紫微 ===
        bazi_love_bad = False
        bazi_love_reason = ""
        if any("子午" in c for c in chong):
            bazi_love_bad = True
            bazi_love_reason = "子午冲，感情多波折"
        elif any("卯酉" in c for c in chong):
            bazi_love_bad = True
            bazi_love_reason = "卯酉冲，感情易生变"

        ziwei_love_good = False
        ziwei_love_reason = ""
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "夫妻":
                    stars = p.get("stars", [])
                    if "紫微" in stars or "天府" in stars:
                        ziwei_love_good = True
                        ziwei_love_reason = f"夫妻宫有{'、'.join([s for s in stars if s in ('紫微','天府')])}，格局稳固"
                    elif "贪狼" in stars or "廉贞" in stars:
                        # 贪狼/廉贞在夫妻宫也暗示感情复杂
                        ziwei_love_good = False

        # 八字感情正面信号（有合）
        bazi_love_good = False
        bazi_love_good_reason = ""
        if any("午未" in h or "寅亥" in h or "卯戌" in h for h in he):
            bazi_love_good = True
            bazi_love_good_reason = f"八字有合（{'、'.join(he[:2])}），感情缘分佳"

        if bazi_love_bad and ziwei_love_good:
            conflicts.append(ConflictItem(
                aspect="感情婚姻",
                method_a="八字",
                finding_a=bazi_love_reason,
                method_b="紫微",
                finding_b=ziwei_love_reason,
                suggestion="八字看地支冲合的内在张力，紫微看星曜格局的整体气象。冲不代表一定不好，紫微稳也不代表没波折，需结合大运流年看应期。"
            ))

        # 反向：八字感情好但紫微夫妻宫凶
        ziwei_love_bad = False
        ziwei_love_bad_reason = ""
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "夫妻":
                    stars = p.get("stars", [])
                    bad_love = [s for s in stars if s in ("贪狼", "廉贞", "七杀", "破军", "擎羊", "陀罗", "火星", "铃星")]
                    if bad_love:
                        ziwei_love_bad = True
                        ziwei_love_bad_reason = f"夫妻宫有{'、'.join(bad_love)}，感情格局偏凶"

        if bazi_love_good and ziwei_love_bad:
            conflicts.append(ConflictItem(
                aspect="感情婚姻",
                method_a="八字",
                finding_a=bazi_love_good_reason,
                method_b="紫微",
                finding_b=ziwei_love_bad_reason,
                suggestion="八字有合代表缘分基础好，紫微夫妻宫凶代表感情模式有挑战。先天缘分佳但需注意相处方式，避免星曜暗示的负面模式。"
            ))

        # === 1b. 感情婚姻冲突：八字 vs 占星 ===
        # 占星感情分析：金星落座反映爱情风格和吸引力模式
        if self.udm.astro_chart:
            planets = self.udm.astro_chart.get("planets", {})
            venus = planets.get("金星", {})
            venus_sign = venus.get("sign", "")

            # 金星旺相的星座（感情面好）
            venus_strong_signs = {"金牛", "天秤", "双鱼"}
            # 金星落陷的星座（感情面有挑战）
            venus_weak_signs = {"天蝎", "白羊", "处女"}

            # 上升 → 第七宫头（伴侣类型）
            asc = self.udm.astro_chart.get("ascendant_sign", "")
            opposite_signs = {
                "白羊": "天秤", "金牛": "天蝎", "双子": "射手",
                "巨蟹": "摩羯", "狮子": "水瓶", "处女": "双鱼",
                "天秤": "白羊", "天蝎": "金牛", "射手": "双子",
                "摩羯": "巨蟹", "水瓶": "狮子", "双鱼": "处女",
            }
            desc_sign = opposite_signs.get(asc, "")

            # 八字感情好（有合）vs 占星金星落陷或第七宫头凶
            astro_love_bad = False
            astro_love_reason = ""
            if venus_sign in venus_weak_signs:
                astro_love_bad = True
                venus_weak_desc = {
                    "天蝎": "金星天蝎，感情深沉执着但占有欲强，易陷入极端情感",
                    "白羊": "金星白羊，感情来得快去得快，冲动型恋爱",
                    "处女": "金星处女，对伴侣要求高，感情中过于挑剔",
                }
                astro_love_reason = venus_weak_desc.get(venus_sign, f"金星{venus_sign}，爱情模式有挑战")

            if bazi_love_good and astro_love_bad:
                conflicts.append(ConflictItem(
                    aspect="感情婚姻",
                    method_a="八字",
                    finding_a=bazi_love_good_reason,
                    method_b="占星",
                    finding_b=astro_love_reason,
                    suggestion="八字有合代表缘分基础好、人际吸引力强，但占星金星落陷暗示爱情表达方式有盲区。缘分不缺但经营方式需调整，避免金星暗示的情感极端。"
                ))

            # 八字感情差（有冲）vs 占星金星旺相
            astro_love_good = False
            astro_love_reason_good = ""
            if venus_sign in venus_strong_signs:
                astro_love_good = True
                venus_strong_desc = {
                    "金牛": "金星入庙，感情稳定忠诚，重视长久关系",
                    "天秤": "金星入庙，善于经营关系，天生的平衡大师",
                    "双鱼": "金星旺相，浪漫多情，共情力强",
                }
                astro_love_reason_good = venus_strong_desc.get(venus_sign, f"金星{venus_sign}，爱情运势佳")

            if bazi_love_bad and astro_love_good:
                conflicts.append(ConflictItem(
                    aspect="感情婚姻",
                    method_a="八字",
                    finding_a=bazi_love_reason,
                    method_b="占星",
                    finding_b=astro_love_reason_good,
                    suggestion="八字有冲代表感情路上有波折和变动，但占星金星旺相暗示爱情天赋不差。内在冲突多但外在魅力足，关键在于学会处理矛盾而非逃避。"
                ))

            # 八字有桃花但占星第七宫头不佳
            has_taohua = any("桃花" in f or "红鸾" in f for f in features)
            if has_taohua and desc_sign:
                # 第七宫头如果是变动星座（双子、射手、双鱼、处女），暗示伴侣关系不稳定
                unstable_desc = {"双子", "射手", "双鱼", "处女"}
                if desc_sign in unstable_desc:
                    conflicts.append(ConflictItem(
                        aspect="感情婚姻",
                        method_a="八字",
                        finding_a="八字有桃花星，异性缘佳，感情机会多",
                        method_b="占星",
                        finding_b=f"第七宫头{desc_sign}（变动星座），伴侣关系倾向不稳定或多变",
                        suggestion="桃花旺代表吸引力强、机会多，但第七宫头变动星座暗示长期关系的稳定性是课题。机会多不等于质量高，需在众多缘分中筛选真正适合的对象。"
                    ))

        # === 2. 事业冲突：八字 vs 奇门 ===
        bazi_career_good = False
        bazi_career_reason = ""
        if any("七杀" in f for f in features):
            bazi_career_good = True
            bazi_career_reason = "七杀透干，事业驱动力强"
        if any("官" in v for v in shishen.values()):
            bazi_career_good = True
            if bazi_career_reason:
                bazi_career_reason += "；正官有力，有管理运"
            else:
                bazi_career_reason = "正官有力，有管理运"

        qimen_career_bad = False
        qimen_career_reason = ""
        if self.udm.qimen_chart:
            men = self.udm.qimen_chart.get("ba_men", {})
            # 门受克或凶门多
            xiong_men = [k for k, v in men.items() if v in ("死门", "惊门", "伤门")]
            if len(xiong_men) >= 3:
                qimen_career_bad = True
                qimen_career_reason = f"奇门凶门过多（{'、'.join(xiong_men)}），事业格局偏凶"

        if bazi_career_good and qimen_career_bad:
            conflicts.append(ConflictItem(
                aspect="事业",
                method_a="八字",
                finding_a=bazi_career_reason,
                method_b="奇门",
                finding_b=qimen_career_reason,
                suggestion="八字看先天命格，奇门看当下时势。先天有事业根基但时运不佳，宜韬光养晦等待时机。"
            ))

        # 反向：八字事业弱但奇门格局好
        qimen_career_good = False
        qimen_career_good_reason = ""
        if self.udm.qimen_chart:
            men = self.udm.qimen_chart.get("ba_men", {})
            ji_men = [k for k, v in men.items() if v in ("开门", "生门", "休门")]
            if ji_men:
                qimen_career_good = True
                qimen_career_good_reason = f"奇门吉门（{'、'.join(ji_men)}）得位，当下时运不错"

        bazi_career_weak = not bazi_career_good and any("身弱" in f for f in features)
        if bazi_career_weak and qimen_career_good:
            conflicts.append(ConflictItem(
                aspect="事业",
                method_a="八字",
                finding_a="身弱无明显官杀，先天事业根基不强",
                method_b="奇门",
                finding_b=qimen_career_good_reason,
                suggestion="八字先天事业根基偏弱，但奇门显示当下时运有利。宜借势而为，把握当前有利时机，借外力推动事业发展。"
            ))

        # === 3. 事业冲突：八字 vs 紫微官禄宫 ===
        ziwei_career_good = False
        ziwei_career_reason = ""
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "官禄":
                    stars = p.get("stars", [])
                    auspicious = [s for s in stars if s in ("紫微", "天府", "太阳", "天梁", "天相")]
                    if auspicious:
                        ziwei_career_good = True
                        ziwei_career_reason = f"官禄宫有{'、'.join(auspicious)}，事业格局高"

        bazi_career_weak = any("身弱" in f for f in features) and not bazi_career_good
        if bazi_career_weak and ziwei_career_good:
            conflicts.append(ConflictItem(
                aspect="事业",
                method_a="八字",
                finding_a="身弱无明显官杀，先天事业根基不强",
                method_b="紫微",
                finding_b=ziwei_career_reason,
                suggestion="八字论身强身弱定先天禀赋，紫微论星曜格局看后天造化。格局高但身弱，需借力打力，贵人运重要。"
            ))

        # === 4. 健康冲突：八字五行 vs 紫微疾厄宫 ===
        wuxing_count = self.udm.get_wuxing_count()
        if wuxing_count:
            max_wx = max(wuxing_count, key=wuxing_count.get)
            bazi_health_issue = wuxing_count[max_wx] >= 4
            bazi_health_reason = f"{max_wx}过旺（{wuxing_count[max_wx]}个），注意{max_wx}行相关脏腑"

            ziwei_health_good = False
            ziwei_health_reason = ""
            if self.udm.ziwei_chart:
                palaces = self.udm.ziwei_chart.get("palaces", [])
                for p in palaces:
                    if p.get("name") == "疾厄":
                        stars = p.get("stars", [])
                        good_stars = [s for s in stars if s in ("天同", "天梁", "天府")]
                        if good_stars:
                            ziwei_health_good = True
                            ziwei_health_reason = f"疾厄宫有{'、'.join(good_stars)}，有化解之力"

            if bazi_health_issue and ziwei_health_good:
                conflicts.append(ConflictItem(
                    aspect="健康体质",
                    method_a="八字",
                    finding_a=bazi_health_reason,
                    method_b="紫微",
                    finding_b=ziwei_health_reason,
                    suggestion="八字五行偏颇是先天体质，紫微疾厄宫看后天化解。有吉星守护不代表可以忽视，养生仍需注意平衡。"
                ))

            # 反向：八字五行平衡但紫微疾厄宫凶
            bazi_health_balanced = not bazi_health_issue
            ziwei_health_bad = False
            ziwei_health_bad_reason = ""
            if self.udm.ziwei_chart:
                palaces = self.udm.ziwei_chart.get("palaces", [])
                for p in palaces:
                    if p.get("name") == "疾厄":
                        stars = p.get("stars", [])
                        bad_stars = [s for s in stars if s in ("七杀", "破军", "贪狼", "廉贞", "擎羊", "陀罗")]
                        if bad_stars:
                            ziwei_health_bad = True
                            ziwei_health_bad_reason = f"疾厄宫有{'、'.join(bad_stars)}，需注意突发性疾病或手术"

            if bazi_health_balanced and ziwei_health_bad:
                conflicts.append(ConflictItem(
                    aspect="健康体质",
                    method_a="八字",
                    finding_a="八字五行基本平衡，先天体质尚可",
                    method_b="紫微",
                    finding_b=ziwei_health_bad_reason,
                    suggestion="八字五行平衡代表先天体质底子好，但紫微疾厄宫有凶星暗示特定健康风险。先天底子好不代表可以忽视，需定期体检防范凶星暗示的健康隐患。"
                ))

        # === 5. 性格冲突：八字 vs 占星 ===
        bazi_bold = any("七杀" in f or "伤官" in f for f in features)
        bazi_bold_reason = "七杀/伤官透干，性格刚强冲动" if bazi_bold else ""

        astro_cautious = False
        astro_cautious_reason = ""
        if self.udm.astro_chart:
            sun_sign = self.udm.astro_chart.get("sun_sign", "")
            if sun_sign in ("金牛", "摩羯", "处女"):
                astro_cautious = True
                astro_cautious_reason = f"太阳{sun_sign}，性格偏稳重保守"
            moon_sign = self.udm.astro_chart.get("moon_sign", "")
            if moon_sign in ("巨蟹", "双鱼"):
                astro_cautious = True
                if astro_cautious_reason:
                    astro_cautious_reason += f"；月亮{moon_sign}，内在敏感细腻"
                else:
                    astro_cautious_reason = f"月亮{moon_sign}，内在敏感细腻"

        if bazi_bold and astro_cautious:
            conflicts.append(ConflictItem(
                aspect="性格特质",
                method_a="八字",
                finding_a=bazi_bold_reason,
                method_b="占星",
                finding_b=astro_cautious_reason,
                suggestion="八字看天干透出的外在行为模式，占星看星座元素的内在气质。外刚内柔是常见组合，表面强势内心细腻。"
            ))

        # 反向：八字稳重但占星冲动
        bazi_cautious = False
        bazi_cautious_reason = ""
        if not bazi_bold and any("正官" in f or "印" in f for f in features):
            bazi_cautious = True
            bazi_cautious_reason = "正官/印星透干，性格偏稳重内敛"

        astro_bold = False
        astro_bold_reason = ""
        if self.udm.astro_chart:
            sun_sign = self.udm.astro_chart.get("sun_sign", "")
            if sun_sign in ("白羊", "狮子", "射手"):
                astro_bold = True
                astro_bold_reason = f"太阳{sun_sign}，外在表现热情冲动"
            moon_sign = self.udm.astro_chart.get("moon_sign", "")
            if moon_sign in ("白羊", "天蝎"):
                astro_bold = True
                if astro_bold_reason:
                    astro_bold_reason += f"；月亮{moon_sign}，内在驱动力强"
                else:
                    astro_bold_reason = f"月亮{moon_sign}，内在驱动力强"

        if bazi_cautious and astro_bold:
            conflicts.append(ConflictItem(
                aspect="性格特质",
                method_a="八字",
                finding_a=bazi_cautious_reason,
                method_b="占星",
                finding_b=astro_bold_reason,
                suggestion="八字看天干格局定外在行为基调，占星看星座元素定内在气质。表面稳重内心有火，是外冷内热的组合，关键时刻会展现出意想不到的行动力。"
            ))

        # === 6. 财运冲突：八字财星 vs 紫微财帛宫 ===
        bazi_wealth_good = False
        bazi_wealth_reason = ""
        if any("财" in v for v in shishen.values()):
            bazi_wealth_good = True
            bazi_wealth_reason = "财星透干，有赚钱能力和财运基础"
        if any("比劫" in f and "财" in f for f in features):
            bazi_wealth_good = False
            bazi_wealth_reason = "比劫夺财，财运有损耗风险"

        ziwei_wealth_bad = False
        ziwei_wealth_reason = ""
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "财帛":
                    stars = p.get("stars", [])
                    bad_wealth = [s for s in stars if s in ("七杀", "破军", "贪狼", "廉贞", "擎羊", "陀罗", "火星", "铃星")]
                    if bad_wealth:
                        ziwei_wealth_bad = True
                        ziwei_wealth_reason = f"财帛宫有{'、'.join(bad_wealth)}，财运波折或有破财风险"

        if bazi_wealth_good and ziwei_wealth_bad:
            conflicts.append(ConflictItem(
                aspect="财运",
                method_a="八字",
                finding_a=bazi_wealth_reason,
                method_b="紫微",
                finding_b=ziwei_wealth_reason,
                suggestion="八字看先天财星配置，紫微看后天财运格局。有财星但财帛宫凶，说明赚钱机会多但守财不易，需注意理财和风险控制。"
            ))

        # 反向：八字财运弱但紫微财帛宫吉
        ziwei_wealth_good = False
        ziwei_wealth_good_reason = ""
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "财帛":
                    stars = p.get("stars", [])
                    good_wealth = [s for s in stars if s in ("武曲", "天府", "太阴", "紫微", "太阳")]
                    if good_wealth:
                        ziwei_wealth_good = True
                        ziwei_wealth_good_reason = f"财帛宫有{'、'.join(good_wealth)}，后天财运格局高"

        bazi_wealth_weak = not bazi_wealth_good
        if any("比劫" in f for f in features):
            bazi_wealth_weak = True

        if bazi_wealth_weak and ziwei_wealth_good:
            conflicts.append(ConflictItem(
                aspect="财运",
                method_a="八字",
                finding_a="八字无明显财星或有比劫夺财，先天财运根基不强",
                method_b="紫微",
                finding_b=ziwei_wealth_good_reason,
                suggestion="八字先天财运偏弱，但紫微财帛宫有吉星，后天财运有改善空间。宜通过专业能力和社会资源来提升财运，不宜靠投机。"
            ))

        # === 7. 财运冲突：八字财星 vs 奇门 ===
        qimen_wealth_bad = False
        qimen_wealth_reason = ""
        if self.udm.qimen_chart:
            men = self.udm.qimen_chart.get("ba_men", {})
            xiong_for_wealth = [k for k, v in men.items() if v in ("死门", "惊门", "伤门")]
            if len(xiong_for_wealth) >= 2:
                qimen_wealth_bad = True
                qimen_wealth_reason = f"奇门凶门过多（{'、'.join(xiong_for_wealth)}），当下求财时运不佳"

        if bazi_wealth_good and qimen_wealth_bad:
            conflicts.append(ConflictItem(
                aspect="财运",
                method_a="八字",
                finding_a=bazi_wealth_reason,
                method_b="奇门",
                finding_b=qimen_wealth_reason,
                suggestion="八字看先天财运根基，奇门看当下求财时势。有财根但时运不济，宜等待时机，不宜冲动投资或大额支出。"
            ))

        # === 8. 学业冲突：八字印星 vs 占星水星 ===
        bazi_academic_good = False
        bazi_academic_reason = ""
        if any("正印" in v for v in shishen.values()):
            bazi_academic_good = True
            bazi_academic_reason = "正印透干，学习踏实，善得师长助力"
        if any("偏印" in v for v in shishen.values()):
            bazi_academic_good = True
            if bazi_academic_reason:
                bazi_academic_reason += "；偏印透干，思维独特"
            else:
                bazi_academic_reason = "偏印透干，思维独特，适合偏门学问"

        astro_academic_bad = False
        astro_academic_reason = ""
        if self.udm.astro_chart:
            planets = self.udm.astro_chart.get("planets", {})
            mercury = planets.get("水星", {})
            mercury_sign = mercury.get("sign", "")
            # 水星落陷的星座：射手（粗心大意）、双鱼（思维散漫）
            if mercury_sign in ("射手", "双鱼"):
                astro_academic_bad = True
                astro_academic_reason = f"水星{mercury_sign}落陷，思维不够专注，学习易分心"

        if bazi_academic_good and astro_academic_bad:
            conflicts.append(ConflictItem(
                aspect="学业",
                method_a="八字",
                finding_a=bazi_academic_reason,
                method_b="占星",
                finding_b=astro_academic_reason,
                suggestion="八字印星有力代表有学习天赋和贵人助力，占星水星落陷代表思维方式有局限。有天赋但需刻意训练专注力，扬长避短。"
            ))

        # 反向：八字印星弱但占星水星强
        bazi_academic_weak = not bazi_academic_good
        astro_academic_good = False
        astro_academic_good_reason = ""
        if self.udm.astro_chart:
            planets = self.udm.astro_chart.get("planets", {})
            mercury = planets.get("水星", {})
            mercury_sign = mercury.get("sign", "")
            if mercury_sign in ("双子", "处女"):
                astro_academic_good = True
                astro_academic_good_reason = f"水星{mercury_sign}入庙，思维敏捷，学习能力强"

        if bazi_academic_weak and astro_academic_good:
            conflicts.append(ConflictItem(
                aspect="学业",
                method_a="八字",
                finding_a="八字无明显印星，先天学习天赋一般",
                method_b="占星",
                finding_b=astro_academic_good_reason,
                suggestion="八字印星不显代表先天学习根基一般，但占星水星入庙代表思维能力出众。可通过发挥思维优势来弥补学习方法上的不足，适合灵活型学习方式。"
            ))

        # === 9. 学业冲突：八字 vs 紫微官禄宫 ===
        ziwei_academic_good = False
        ziwei_academic_reason = ""
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "官禄":
                    stars = p.get("stars", [])
                    study_stars = [s for s in stars if s in ("天机", "天梁", "太阳", "太阴", "文昌", "文曲")]
                    if study_stars:
                        ziwei_academic_good = True
                        ziwei_academic_reason = f"官禄宫有{'、'.join(study_stars)}，学业运势不错"

        # 食伤旺但印弱 = 聪明但不踏实；紫微有学业星 = 后天有改善空间
        bazi_academic_weak = not bazi_academic_good and any("食伤" in f for f in features)
        if bazi_academic_weak and ziwei_academic_good:
            conflicts.append(ConflictItem(
                aspect="学业",
                method_a="八字",
                finding_a="食伤透干但印星不显，先天学习根基不强",
                method_b="紫微",
                finding_b=ziwei_academic_reason,
                suggestion="八字看先天学习禀赋，紫微看后天学业格局。食伤旺但印弱，说明聪明但不够踏实，紫微有学业星则后天有改善空间。"
            ))

        # === 10. 人际关系冲突：八字比劫 vs 紫微兄弟宫 ===
        bazi_interpersonal_bad = False
        bazi_interpersonal_reason = ""
        if any("比肩" in v or "劫财" in v for v in shishen.values()):
            bazi_interpersonal_bad = True
            bazi_interpersonal_reason = "比劫透干，朋友多但需防合伙纠纷"

        ziwei_interpersonal_good = False
        ziwei_interpersonal_reason = ""
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "兄弟":
                    stars = p.get("stars", [])
                    good_stars = [s for s in stars if s in ("天同", "天梁", "天府", "紫微", "太阳")]
                    if good_stars:
                        ziwei_interpersonal_good = True
                        ziwei_interpersonal_reason = f"兄弟宫有{'、'.join(good_stars)}，手足助力多，朋友圈质量高"

        if bazi_interpersonal_bad and ziwei_interpersonal_good:
            conflicts.append(ConflictItem(
                aspect="人际关系",
                method_a="八字",
                finding_a=bazi_interpersonal_reason,
                method_b="紫微",
                finding_b=ziwei_interpersonal_reason,
                suggestion="八字比劫透干代表人际关系活跃但有竞争，紫微兄弟宫吉代表有贵人助力。活跃社交中需注意利益边界，贵人运可化解比劫之弊。"
            ))

        return conflicts

    def _calc_overall_confidence(self, results: dict) -> ConfidenceLevel:
        consensus = len(results["consensus"])
        conflicts = len(results["conflicts"])
        methods = results["method_count"]

        # 七术系统中，少量冲突是正常的（不同术法维度不同），
        # 关键看共识与冲突的比例，而非有无冲突。
        # 共识远多于冲突 → 整体可信；冲突反超共识 → 矛盾；其余 → 中/低。

        # 冲突主导：冲突数 >= 共识数
        if conflicts > 0 and conflicts >= consensus:
            return ConfidenceLevel.CONTRADICTORY

        # 高置信：多术法（>=4）+ 多共识（>=5）+ 冲突被共识压制
        if methods >= 4 and consensus >= 5:
            return ConfidenceLevel.HIGH

        # 中置信：一定数量的术法和共识
        if methods >= 3 and consensus >= 3:
            return ConfidenceLevel.MEDIUM

        # 有冲突但共识仍多于冲突
        if conflicts > 0 and consensus > conflicts:
            return ConfidenceLevel.MEDIUM

        # 数据不足
        return ConfidenceLevel.LOW

    def generate_comprehensive_judgment(self) -> dict:
        """生成七术综合判断——包含吉凶、趋势、建议"""
        judgment = {
            "命格总评": "",
            "事业": {"趋势": "", "建议": "", "吉凶": ""},
            "财运": {"趋势": "", "建议": "", "吉凶": ""},
            "感情": {"趋势": "", "建议": "", "吉凶": ""},
            "健康": {"趋势": "", "建议": "", "吉凶": ""},
            "学业": {"趋势": "", "建议": "", "吉凶": ""},
            "人际关系": {"趋势": "", "建议": "", "吉凶": ""},
            "性格": {"优势": "", "劣势": "", "建议": ""},
            "大运提示": "",
        }

        # 收集各术数据
        bazi_features = self.udm.features or []
        chong = self.udm.get_chong()
        he = self.udm.get_he()
        wuxing_count = self.udm.get_wuxing_count()

        # === 命格总评 ===
        grade_parts = []

        # 日主强弱
        dm = self.udm.day_master
        wx = self.udm.day_master_wuxing
        if any("身强" in f for f in bazi_features):
            grade_parts.append(f"{dm}（{wx}）身强")
        elif any("身弱" in f for f in bazi_features):
            grade_parts.append(f"{dm}（{wx}）身弱")
        else:
            grade_parts.append(f"{dm}（{wx}）")

        # 格局
        if any("格" in f for f in bazi_features):
            ge = [f for f in bazi_features if "格" in f]
            if ge:
                grade_parts.append(f"{ge[0].split('—')[0] if '—' in ge[0] else ge[0]}")

        # 冲合
        if chong and len(chong) >= 2:
            grade_parts.append(f"多冲（{len(chong)}处），一生多变动")
        elif chong:
            grade_parts.append(f"有冲，需防变动")
        if he:
            grade_parts.append(f"有合，人缘不差")

        judgment["命格总评"] = "。".join(grade_parts) + "。"

        # === 事业 ===
        career_trend = []
        career_suggest = []
        career_luck = "中"

        # 八字看官杀
        if self.udm.shishen_gan:
            ss = self.udm.shishen_gan
            has_guan = any("官" in v for v in ss.values())
            has_sha = any("杀" in v for v in ss.values())
            has_shi = any("食" in v or "伤" in v for v in ss.values())
            if has_guan or has_sha:
                career_trend.append("有管理才能，适合带领团队")
                career_luck = "吉"
            if has_shi:
                career_trend.append("有创意和表达力，适合技术或创意行业")
            if any("七杀" in f for f in bazi_features):
                career_trend.append("七杀透干，事业心强，敢闯敢拼")
                career_luck = "吉"

        # 奇门看开门
        if self.udm.qimen_chart:
            men = self.udm.qimen_chart.get("ba_men", {})
            kai = [k for k, v in men.items() if v == "开门"]
            if kai:
                career_trend.append(f"奇门开门在{kai[0]}，事业有发展空间")
                career_luck = "吉"
            sheng = [k for k, v in men.items() if v == "生门"]
            if sheng:
                career_suggest.append(f"生门在{sheng[0]}，求财宜往此方向")

        # 紫微看事业宫
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "官禄":
                    stars = p.get("stars", [])
                    if stars:
                        career_trend.append(f"官禄宫主星{stars[0]}，事业格局不错")

        judgment["事业"]["趋势"] = "；".join(career_trend) if career_trend else "平稳发展"
        judgment["事业"]["建议"] = "；".join(career_suggest) if career_suggest else "稳扎稳打，借势而为"
        judgment["事业"]["吉凶"] = career_luck

        # === 财运 ===
        wealth_trend = []
        wealth_suggest = []
        wealth_luck = "中"

        if self.udm.shishen_gan:
            ss = self.udm.shishen_gan
            has_cai = any("财" in v for v in ss.values())
            if has_cai:
                wealth_trend.append("财星透出，有赚钱意识")
                wealth_luck = "吉"

        if self.udm.qimen_chart:
            men = self.udm.qimen_chart.get("ba_men", {})
            sheng = [k for k, v in men.items() if v == "生门"]
            if sheng:
                wealth_trend.append(f"生门在{sheng[0]}，财运有门路")
                wealth_luck = "吉"

        if chong and any("财" in str(c) or "子" in str(c) for c in chong):
            wealth_trend.append("有冲，财运波动大")
            wealth_luck = "中"
            wealth_suggest.append("理财需谨慎，避免冲动投资")

        judgment["财运"]["趋势"] = "；".join(wealth_trend) if wealth_trend else "财运平稳"
        judgment["财运"]["建议"] = "；".join(wealth_suggest) if wealth_suggest else "量入为出，积少成多"
        judgment["财运"]["吉凶"] = wealth_luck

        # === 感情 ===
        love_trend = []
        love_suggest = []
        love_luck = "中"

        if chong and any(("午" in str(c) and "子" in str(c)) or ("子" in str(c) and "午" in str(c)) for c in chong):
            love_trend.append("子午冲，感情多波折")
            love_luck = "凶"
            love_suggest.append("感情需耐心经营，避免急躁")

        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "夫妻":
                    stars = p.get("stars", [])
                    if "紫微" in stars or "天府" in stars:
                        love_trend.append("夫妻宫有紫微/天府，感情基础稳")
                        if love_luck == "凶":
                            love_luck = "中"  # 紫微缓解了冲的影响
                        else:
                            love_luck = "吉"
                    if stars:
                        love_trend.append(f"夫妻宫主星{stars[0]}")

        if not love_trend:
            love_trend.append("感情运势平稳")

        judgment["感情"]["趋势"] = "；".join(love_trend)
        judgment["感情"]["建议"] = "；".join(love_suggest) if love_suggest else "顺其自然，缘分自来"
        judgment["感情"]["吉凶"] = love_luck

        # === 健康 ===
        health_trend = []
        health_suggest = []
        health_luck = "中"

        if wuxing_count:
            max_wx = max(wuxing_count, key=wuxing_count.get)
            min_wx = min(wuxing_count, key=wuxing_count.get)
            if wuxing_count[max_wx] >= 4:
                health_trend.append(f"{max_wx}过旺，注意相关脏腑")
                health_suggest.append(f"宜调理{max_wx}行平衡")
                health_luck = "凶"
            if wuxing_count[min_wx] == 0:
                health_trend.append(f"{min_wx}缺失，体质偏弱")
                health_suggest.append(f"宜补{min_wx}行")
                health_luck = "凶"

        if not health_trend:
            health_trend.append("五行基本平衡，体质尚可")
            health_luck = "吉"

        # 调候用神
        if self.udm.tiaohou:
            health_suggest.append(f"调候用神{self.udm.tiaohou}，养生可参考")

        judgment["健康"]["趋势"] = "；".join(health_trend)
        judgment["健康"]["建议"] = "；".join(health_suggest) if health_suggest else "规律作息，适度运动"
        judgment["健康"]["吉凶"] = health_luck

        # === 学业 ===
        academic_trend = []
        academic_suggest = []
        academic_luck = "中"

        # 八字：看印星（学习能力）
        if self.udm.shishen_gan:
            ss = self.udm.shishen_gan
            has_zhengyin = any("正印" in v for v in ss.values())
            has_pianyin = any("偏印" in v for v in ss.values())
            if has_zhengyin:
                academic_trend.append("正印透干，学习踏实，善得师长助力")
                academic_luck = "吉"
            if has_pianyin:
                academic_trend.append("偏印透干，思维独特，适合偏门学问")

        # 八字：看食伤（聪明才智）
        if any("食伤" in f for f in bazi_features):
            academic_trend.append("食伤透干，聪明有创意，表达力强")
            if academic_luck == "中":
                academic_luck = "吉"

        # 紫微：看官禄宫
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "官禄":
                    stars = p.get("stars", [])
                    study_stars = [s for s in stars if s in ("天机", "天梁", "太阳", "太阴", "文昌", "文曲")]
                    if study_stars:
                        academic_trend.append(f"官禄宫有{'、'.join(study_stars)}，学业运势不错")
                        academic_luck = "吉"

        # 占星：看水星
        if self.udm.astro_chart:
            planets = self.udm.astro_chart.get("planets", {})
            mercury = planets.get("水星", {})
            if mercury.get("sign") in ("双子", "处女"):
                academic_trend.append(f"水星{mercury['sign']}入庙，思维敏捷，学习能力强")
                academic_luck = "吉"

        if not academic_trend:
            academic_trend.append("学业运势平稳，无特别突出信号")

        judgment["学业"]["趋势"] = "；".join(academic_trend)
        judgment["学业"]["建议"] = "；".join(academic_suggest) if academic_suggest else "踏实学习，厚积薄发"
        judgment["学业"]["吉凶"] = academic_luck

        # === 人际关系 ===
        inter_trend = []
        inter_suggest = []
        inter_luck = "中"

        # 八字：看比劫
        if self.udm.shishen_gan:
            ss = self.udm.shishen_gan
            has_bijie = any("比肩" in v or "劫财" in v for v in ss.values())
            if has_bijie:
                inter_trend.append("比劫透干，朋友多、人缘广，但需防合伙纠纷")
            has_guan = any("正官" in v for v in ss.values())
            if has_guan:
                inter_trend.append("正官透干，善于与上级相处，社交层次较高")
                inter_luck = "吉"

        # 八字：看冲合
        if chong:
            inter_trend.append("有冲，人际关系有波折或变动")
            inter_suggest.append("人际交往中多注意沟通，避免冲突升级")
        if he:
            inter_trend.append("有合，人缘好，善于合作")
            inter_luck = "吉"

        # 紫微：看兄弟宫
        if self.udm.ziwei_chart:
            palaces = self.udm.ziwei_chart.get("palaces", [])
            for p in palaces:
                if p.get("name") == "兄弟":
                    stars = p.get("stars", [])
                    good_stars = [s for s in stars if s in ("天同", "天梁", "天府", "紫微", "太阳")]
                    bad_stars = [s for s in stars if s in ("七杀", "破军", "擎羊", "陀罗")]
                    if good_stars:
                        inter_trend.append(f"兄弟宫有{'、'.join(good_stars)}，手足助力多")
                        inter_luck = "吉"
                    elif bad_stars:
                        inter_trend.append(f"兄弟宫有{'、'.join(bad_stars)}，需注意朋友间纠纷")
                        inter_suggest.append("交友需谨慎，少参与利益纠纷")

        # 占星：看水星和金星
        if self.udm.astro_chart:
            planets = self.udm.astro_chart.get("planets", {})
            mercury = planets.get("水星", {})
            venus = planets.get("金星", {})
            if mercury.get("sign") in ("双子", "天秤"):
                inter_trend.append(f"水星{mercury['sign']}，沟通能力强")
            if venus.get("sign") in ("天秤", "金牛", "双鱼"):
                inter_trend.append(f"金星{venus['sign']}，社交魅力佳")

        if not inter_trend:
            inter_trend.append("人际关系平稳，无明显吉凶信号")

        judgment["人际关系"]["趋势"] = "；".join(inter_trend)
        judgment["人际关系"]["建议"] = "；".join(inter_suggest) if inter_suggest else "真诚待人，广结善缘"
        judgment["人际关系"]["吉凶"] = inter_luck

        # === 性格 ===
        strengths = []
        weaknesses = []

        if any("七杀" in f for f in bazi_features):
            strengths.append("魄力足，敢担当")
            weaknesses.append("压力大，易焦虑")
        if any("正官" in f for f in bazi_features):
            strengths.append("守规矩，责任心强")
        if any("印" in f for f in bazi_features):
            strengths.append("善于学习，有涵养")
        if any("食伤" in f for f in bazi_features):
            strengths.append("表达力强，有创意")
            weaknesses.append("容易急躁，话多")
        if any("财" in f for f in bazi_features):
            strengths.append("务实，重视效率")

        if self.udm.astro_chart:
            sun = self.udm.astro_chart.get("sun_sign", "")
            if sun in ["双子", "水瓶"]:
                strengths.append("思维灵活，适应力强")
                weaknesses.append("注意力分散，不够专注")
            elif sun in ["金牛", "摩羯"]:
                strengths.append("踏实稳重，耐力强")
                weaknesses.append("固执，不善变通")
            elif sun in ["狮子", "白羊"]:
                strengths.append("自信果断，领导力强")
                weaknesses.append("冲动，好面子")
            elif sun in ["巨蟹", "双鱼"]:
                strengths.append("共情力强，直觉敏锐")
                weaknesses.append("情绪化，易受外界影响")
            elif sun in ["处女", "天蝎"]:
                strengths.append("洞察力强，做事严谨")
                weaknesses.append("过于挑剔，容易内耗")
            elif sun in ["天秤", "射手"]:
                strengths.append("社交能力强，视野开阔")
                weaknesses.append("优柔寡断或过于随性")

        if not strengths:
            strengths.append("性格平和，适应力强")
        if not weaknesses:
            weaknesses.append("无明显短板")

        judgment["性格"]["优势"] = "、".join(strengths)
        judgment["性格"]["劣势"] = "、".join(weaknesses)
        judgment["性格"]["建议"] = "发挥优势，正视短板，取长补短"

        # === 大运提示 ===
        dayun_parts = []
        if chong:
            dayun_parts.append("逢冲之年多变动，宜稳不宜急")
        if any("七杀" in f for f in bazi_features):
            dayun_parts.append("七杀透干，大运逢官杀年事业有突破")
        if not dayun_parts:
            dayun_parts.append("大运平稳，顺势而为")

        judgment["大运提示"] = "；".join(dayun_parts)

        return judgment
