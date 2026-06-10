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

    def _detect_conflicts(self) -> List[ConflictItem]:
        conflicts = []
        chong = self.udm.get_chong()
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

        if bazi_love_bad and ziwei_love_good:
            conflicts.append(ConflictItem(
                aspect="感情婚姻",
                method_a="八字",
                finding_a=bazi_love_reason,
                method_b="紫微",
                finding_b=ziwei_love_reason,
                suggestion="八字看地支冲合的内在张力，紫微看星曜格局的整体气象。冲不代表一定不好，紫微稳也不代表没波折，需结合大运流年看应期。"
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

    def generate_comprehensive_judgment(self) -> dict:
        """生成七术综合判断——包含吉凶、趋势、建议"""
        judgment = {
            "命格总评": "",
            "事业": {"趋势": "", "建议": "", "吉凶": ""},
            "财运": {"趋势": "", "建议": "", "吉凶": ""},
            "感情": {"趋势": "", "建议": "", "吉凶": ""},
            "健康": {"趋势": "", "建议": "", "吉凶": ""},
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
