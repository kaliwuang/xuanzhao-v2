#!/usr/bin/env python3
"""
玄照 v2.0 - 108视角推理引擎

核心设计：每个人物有自己擅长的术法，用该术法的数据来推理发言。
不是模板填充，而是基于命盘数据的结构化推理。
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import json
import os


@dataclass
class ThinkingModel:
    name: str
    principles: List[str]
    steps: List[str]
    key_concepts: Dict[str, str]


@dataclass
class Figure:
    id: str
    name: str
    title: str
    category: str
    faction: str
    expertise: List[str]
    primary_method: str
    thinking_model: ThinkingModel
    catchphrase: str
    bio: str


@dataclass
class PerspectiveOpinion:
    figure_id: str
    figure_name: str
    figure_title: str
    primary_method: str
    stance: str
    confidence: float
    reasoning: str
    key_points: List[str]
    quotes: List[str]
    referenced_data: Dict[str, Any]


# ============ 从 YAML 加载人物定义 ============


def _load_figures() -> Dict[str, Figure]:
    """从 perspectives/figures.yaml 加载人物定义"""
    import yaml

    figures_dir = os.path.join(os.path.dirname(__file__), "..", "perspectives")
    yaml_path = os.path.join(figures_dir, "figures.yaml")

    figures = {}

    if os.path.exists(yaml_path):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            for fig_data in data.get("figures", []):
                tm_data = fig_data.get("thinking_model", {})
                figure = Figure(
                    id=fig_data["id"],
                    name=fig_data["name"],
                    title=fig_data["title"],
                    category=fig_data["category"],
                    faction=fig_data["faction"],
                    expertise=fig_data["expertise"],
                    primary_method=fig_data["primary_method"],
                    thinking_model=ThinkingModel(
                        name=tm_data.get("name", ""),
                        principles=tm_data.get("principles", []),
                        steps=tm_data.get("steps", []),
                        key_concepts=tm_data.get("key_concepts", {}),
                    ),
                    catchphrase=fig_data["catchphrase"],
                    bio=fig_data["bio"],
                )
                figures[figure.id] = figure

            if figures:
                return figures
        except Exception:
            pass

    # 回退：硬编码
    return _default_figures()


def _default_figures() -> Dict[str, Figure]:
    """默认硬编码人物（YAML加载失败时回退）"""
    return {
        "zhuge-liang": Figure(
            id="zhuge-liang",
            name="诸葛亮",
            title="武侯",
            category="中国玄学",
            faction="orthodox",
            expertise=["奇门遁甲", "八字", "兵法"],
            primary_method="奇门",
            thinking_model=ThinkingModel(
                name="隆中对推演",
                principles=["未出茅庐而知三分天下", "多算胜少算", "借势而为", "以逸待劳"],
                steps=["观天象", "察地理", "识人和", "定策略"],
                key_concepts={"大势": "长期趋势", "节点": "关键转折", "借势": "顺应格局"},
            ),
            catchphrase="鞠躬尽瘁，死而后已",
            bio="三国蜀汉丞相，精通奇门遁甲、八阵图、兵法韬略",
        ),
        "ni-haixia": Figure(
            id="ni-haixia",
            name="倪海厦",
            title="天纪人纪地纪",
            category="中国玄学",
            faction="orthodox",
            expertise=["紫微斗数", "针灸", "易经", "风水"],
            primary_method="紫微",
            thinking_model=ThinkingModel(
                name="三才贯通",
                principles=["天纪看命", "人纪看病", "地纪看运", "知命不认命"],
                steps=["看命宫主星", "看三方四正", "看疾厄宫", "给建议"],
                key_concepts={"三方四正": "命宫联动", "化忌": "需注意", "大运": "十年变化"},
            ),
            catchphrase="知命不认命",
            bio="当代命理大师，精通紫微斗数、针灸、易经",
        ),
        "yuan-tiangang": Figure(
            id="yuan-tiangang",
            name="袁天罡",
            title="推背合著",
            category="中国玄学",
            faction="orthodox",
            expertise=["八字", "面相", "推背图"],
            primary_method="八字",
            thinking_model=ThinkingModel(
                name="骨相推命",
                principles=["少年看骨", "中年看气", "老年看神", "命运分段论"],
                steps=["看日主强弱", "看用神", "看大运", "分段论命"],
                key_concepts={"骨相": "先天禀赋", "大运": "十年阶段", "冲合": "动态关系"},
            ),
            catchphrase="骨相在天气运在时",
            bio="唐代玄学大宗师，与李淳风合著《推背图》",
        ),
        "li-chunfeng": Figure(
            id="li-chunfeng",
            name="李淳风",
            title="乙巳占主",
            category="中国玄学",
            faction="orthodox",
            expertise=["占星", "天文", "历法"],
            primary_method="占星",
            thinking_model=ThinkingModel(
                name="天文推命",
                principles=["天文者天道之显", "星象即人事", "乙巳占星", "天象预警"],
                steps=["观太阳", "观月亮", "观上升", "看相位"],
                key_concepts={"太阳": "核心意志", "月亮": "情感需求", "上升": "外在形象"},
            ),
            catchphrase="天文者天道之显也",
            bio="唐代天文学家，《乙巳占》作者",
        ),
        "gui-gu-zi": Figure(
            id="gui-gu-zi",
            name="鬼谷子",
            title="纵横鼻祖",
            category="中国玄学",
            faction="orthodox",
            expertise=["六爻", "纵横", "心理学"],
            primary_method="六爻",
            thinking_model=ThinkingModel(
                name="捭阖之道",
                principles=["捭之者开", "阖之者闭", "反应术", "飞箝术"],
                steps=["起卦看局势", "看动爻", "看世应", "给策略"],
                key_concepts={"动爻": "变化节点", "世应": "主客关系", "六亲": "人事分类"},
            ),
            catchphrase="捭阖之道，天地之道",
            bio="战国时期纵横家鼻祖，精通六爻、心理学",
        ),
        "jiang-ziya": Figure(
            id="jiang-ziya",
            name="姜子牙",
            title="太公",
            category="中国玄学",
            faction="orthodox",
            expertise=["奇门遁甲", "兵法", "六韬"],
            primary_method="奇门",
            thinking_model=ThinkingModel(
                name="太公兵法",
                principles=["天命在德", "以静制动", "顺势而为", "大器晚成"],
                steps=["看奇门格局", "看值符值使", "看八门九星", "给时机建议"],
                key_concepts={"值符": "核心力量", "值使": "行动引导", "生门": "生机所在"},
            ),
            catchphrase="天命在德不在力",
            bio="周朝开国元勋，精通奇门遁甲、兵法",
        ),
        "shao-yong": Figure(
            id="shao-yong",
            name="邵雍",
            title="康节先生",
            category="中国玄学",
            faction="orthodox",
            expertise=["八字", "象数", "皇极经世"],
            primary_method="八字",
            thinking_model=ThinkingModel(
                name="皇极经世",
                principles=["元会运世", "观物内省", "声音律吕", "象数推演"],
                steps=["看八字定格局", "看大运周期", "看流年应期", "推算节点"],
                key_concepts={"元会运世": "大周期", "象数": "形象数字", "流年": "年运势"},
            ),
            catchphrase="一去二三里，烟村四五家",
            bio="北宋理学家，《皇极经世》作者",
        ),
        "feynman": Figure(
            id="feynman",
            name="费曼",
            title="物理学家",
            category="现代思想",
            faction="rational",
            expertise=["占星", "科学思维", "第一性原理"],
            primary_method="占星",
            thinking_model=ThinkingModel(
                name="第一性原理",
                principles=["简化到本质", "不自欺", "怀疑一切", "简单解释"],
                steps=["收集数据", "找核心变量", "验证因果", "简单解释"],
                key_concepts={"第一性原理": "基本真理", "可证伪性": "可证伪", "奥卡姆剃刀": "最简单"},
            ),
            catchphrase="What I cannot create, I do not understand",
            bio="诺贝尔物理学奖得主，以第一性原理思维著称",
        ),
        "jung": Figure(
            id="jung",
            name="荣格",
            title="心理学家",
            category="现代思想",
            faction="western",
            expertise=["占星", "心理学", "原型理论"],
            primary_method="占星",
            thinking_model=ThinkingModel(
                name="分析心理学",
                principles=["集体无意识", "原型", "阴影整合", "个体化"],
                steps=["看太阳定意识", "看月亮定需求", "看上升定面具", "看相位定冲突"],
                key_concepts={"阴影": "压抑部分", "个体化": "整合过程", "共时性": "有意义巧合"},
            ),
            catchphrase="除非你让无意识变得有意识，否则它将主导你的生活",
            bio="瑞士心理学家，分析心理学创始人",
        ),
        "zhang-zhongjing": Figure(
            id="zhang-zhongjing",
            name="张仲景",
            title="医圣",
            category="中国玄学",
            faction="orthodox",
            expertise=["八字", "医理", "伤寒论"],
            primary_method="八字",
            thinking_model=ThinkingModel(
                name="医理推命",
                principles=["医者知命", "五行五脏", "过旺则病", "治未病"],
                steps=["看五行定体质", "看冲合定脏腑", "看大运定节点", "给养生建议"],
                key_concepts={"五行五脏": "对应关系", "过旺": "易病", "缺失": "虚弱"},
            ),
            catchphrase="上医治未病",
            bio="东汉医学家，《伤寒论》作者",
        ),
        "laozi": Figure(
            id="laozi",
            name="老子",
            title="道祖",
            category="中国玄学",
            faction="daoist",
            expertise=["八字", "道家", "无为"],
            primary_method="八字",
            thinking_model=ThinkingModel(
                name="道法自然",
                principles=["无为而治", "反者道之动", "柔弱胜刚强", "上善若水"],
                steps=["看整体格局", "看用神忌神", "看是否顺势", "给无为建议"],
                key_concepts={"无为": "顺应规律", "柔弱": "以柔克刚", "自然": "顺应本性"},
            ),
            catchphrase="道法自然",
            bio="道家创始人，《道德经》作者",
        ),
        "sunzi": Figure(
            id="sunzi",
            name="孙子",
            title="兵圣",
            category="中国玄学",
            faction="orthodox",
            expertise=["奇门遁甲", "兵法", "策略"],
            primary_method="奇门",
            thinking_model=ThinkingModel(
                name="孙子兵法",
                principles=["知己知彼", "不战而屈人之兵", "以正合以奇胜", "避实击虚"],
                steps=["看奇门定态势", "看开门生门", "看值符定方向", "给策略建议"],
                key_concepts={"知己知彼": "了解环境", "避实击虚": "攻弱点", "出奇制胜": "意想不到"},
            ),
            catchphrase="知己知彼，百战不殆",
            bio="春秋时期军事家，《孙子兵法》作者",
        ),
    }


FIGURES = _load_figures()


class PerspectiveEngine:
    """视角推理引擎"""

    def __init__(self, llm_client=None):
        self.figures = FIGURES
        self.llm = llm_client

    def analyze(self, udm, question: str, figure_ids: Optional[List[str]] = None) -> List[PerspectiveOpinion]:
        """对给定命盘，从指定视角生成观点"""
        ids = figure_ids or list(self.figures.keys())
        opinions = []

        for pid in ids:
            figure = self.figures[pid]
            opinion = self._reason(figure, udm, question)
            opinions.append(opinion)

        return opinions

    def _reason(self, figure: Figure, udm, question: str) -> PerspectiveOpinion:
        """单个视角的推理过程"""

        # 1. 从UDM提取该人物擅长的术法数据
        method_data = self._extract_method_data(udm, figure.primary_method)

        # 2. 基于思维模型做推理
        reasoning = self._apply_thinking_model(figure, method_data, question)

        return PerspectiveOpinion(
            figure_id=figure.id,
            figure_name=figure.name,
            figure_title=figure.title,
            primary_method=figure.primary_method,
            stance=reasoning["stance"],
            confidence=reasoning["confidence"],
            reasoning=reasoning["reasoning"],
            key_points=reasoning["key_points"],
            quotes=reasoning["quotes"],
            referenced_data=method_data,
        )

    def _extract_method_data(self, udm, method: str) -> Dict:
        """从UDM提取特定术法的数据"""
        data = {"method": method}

        if method == "八字":
            data["pillars"] = {
                "year": udm.bazi_year.ganzhi if udm.bazi_year else "",
                "month": udm.bazi_month.ganzhi if udm.bazi_month else "",
                "day": udm.bazi_day.ganzhi if udm.bazi_day else "",
                "time": udm.bazi_time.ganzhi if udm.bazi_time else "",
            }
            data["day_master"] = udm.day_master
            data["day_master_wuxing"] = udm.day_master_wuxing
            data["shishen"] = udm.shishen_gan
            data["features"] = udm.features
            data["chong"] = udm.get_chong()
            data["he"] = udm.get_he()
            data["wuxing_count"] = udm.get_wuxing_count()
            data["tiaohou"] = udm.tiaohou

        elif method == "紫微":
            if udm.ziwei_chart:
                data["ming_gong"] = udm.ziwei_chart.get("ming_gong", "")
                data["wuxing_ju"] = udm.ziwei_chart.get("wuxing_ju", {})
                data["star_placements"] = udm.ziwei_chart.get("star_placements", {})
                data["sihua"] = udm.ziwei_chart.get("sihua", {})
                data["palaces"] = udm.ziwei_chart.get("palaces", [])

        elif method == "六爻":
            if udm.liuyao_chart:
                data["ben_gua"] = udm.liuyao_chart.get("ben_gua", {})
                data["bian_gua"] = udm.liuyao_chart.get("bian_gua", {})
                data["dong_yao"] = udm.liuyao_chart.get("dong_yao", 0)

        elif method == "奇门":
            if udm.qimen_chart:
                data["ju_name"] = udm.qimen_chart.get("ju_name", "")
                data["di_pan"] = udm.qimen_chart.get("di_pan", {})
                data["tian_pan"] = udm.qimen_chart.get("tian_pan", {})
                data["ba_men"] = udm.qimen_chart.get("ba_men", {})
                data["jiu_xing"] = udm.qimen_chart.get("jiu_xing", {})

        elif method == "大六壬":
            if udm.liuren_chart:
                data["yue_jiang"] = udm.liuren_chart.get("yue_jiang", "")
                data["si_ke"] = udm.liuren_chart.get("si_ke", [])
                data["san_chuan"] = udm.liuren_chart.get("san_chuan", [])

        elif method == "太乙":
            if udm.taiyi_chart:
                data["taiyi_gong"] = udm.taiyi_chart.get("taiyi_gong", "")
                data["ji_nian"] = udm.taiyi_chart.get("ji_nian", 0)

        elif method == "占星":
            if udm.astro_chart:
                data["sun_sign"] = udm.astro_chart.get("sun_sign", "")
                data["moon_sign"] = udm.astro_chart.get("moon_sign", "")
                data["ascendant"] = udm.astro_chart.get("ascendant_sign", "")
                data["planets"] = udm.astro_chart.get("planets", {})
                data["aspects"] = udm.astro_chart.get("aspects", [])

        return data

    def _apply_thinking_model(self, figure: Figure, method_data: Dict, question: str) -> Dict:
        """应用思维模型生成推理，注入知识库"""

        # 基于问题类型和术法数据生成推理
        question_type = self._classify_question(question)

        # === 知识库检索注入 ===
        knowledge_snippets = []
        try:
            from knowledge.search import KnowledgeSearch
            ks = KnowledgeSearch()
            # 构建查询：人物 + 问题主题 + 术法
            query = f"{figure.name} {figure.primary_method} {question}"
            knowledge_snippets = ks.search_by_query(query, top_n=2)
        except Exception:
            pass

        # 构造推理文本
        reasoning_parts = []
        key_points = []
        quotes = []

        # 注入知识库片段
        if knowledge_snippets:
            reasoning_parts.append(f"【{figure.name}知识库参考】")
            for s in knowledge_snippets:
                reasoning_parts.append(f"  {s['category']} · {s['title']}")
                reasoning_parts.append(f"  {s.get('snippet', '')[:100]}...")

        # 引用思维模型原则
        for principle in figure.thinking_model.principles[:2]:
            reasoning_parts.append(f"【{figure.name}思维】{principle}")

        # 基于术法数据分析
        if figure.primary_method == "八字":
            dm = method_data.get("day_master", "")
            wx = method_data.get("day_master_wuxing", "")
            features = method_data.get("features", [])
            chong = method_data.get("chong", [])

            reasoning_parts.append(f"日主{dm}属{wx}，")

            if features:
                reasoning_parts.append(f"命局特征：{features[0]}。")
                key_points.append(features[0])

            if chong:
                reasoning_parts.append(f"命局有{chong[0]}，需注意变动。")
                key_points.append(f"有{chong[0]}")

            # 针对问题类型
            if question_type == "事业":
                stance = "事业宜稳健发展，借势而为"
                key_points.append("借势而为")
            elif question_type == "感情":
                stance = "感情需耐心经营，不可强求"
                key_points.append("耐心经营")
            elif question_type == "健康":
                stance = "注意五行平衡，防患于未然"
                key_points.append("五行平衡")
            else:
                stance = "顺势而为，知命不认命"

        elif figure.primary_method == "紫微":
            ming = method_data.get("ming_gong", "")
            stars = method_data.get("star_placements", {})
            sihua = method_data.get("sihua", {})

            reasoning_parts.append(f"命宫在{ming}，")

            if "紫微" in stars:
                reasoning_parts.append(f"紫微在{stars['紫微']}，格局不凡。")
                key_points.append(f"紫微在{stars['紫微']}")

            if sihua:
                lu = sihua.get("禄", "")
                if lu:
                    reasoning_parts.append(f"{lu}化禄，有福气。")
                    key_points.append(f"{lu}化禄")

            stance = "格局已定，关键在于如何运用"

        elif figure.primary_method == "奇门":
            ju = method_data.get("ju_name", "")
            men = method_data.get("ba_men", {})

            reasoning_parts.append(f"当前{ju}，")

            kai = [k for k, v in men.items() if v == "开门"]
            sheng = [k for k, v in men.items() if v == "生门"]

            if kai:
                reasoning_parts.append(f"开门在{kai[0]}，事业可动。")
                key_points.append(f"开门在{kai[0]}")
            if sheng:
                reasoning_parts.append(f"生门在{sheng[0]}，财运有望。")
                key_points.append(f"生门在{sheng[0]}")

            stance = "时机已至，当断则断"

        elif figure.primary_method == "占星":
            sun = method_data.get("sun_sign", "")
            moon = method_data.get("moon_sign", "")

            reasoning_parts.append(f"太阳{sun}，月亮{moon}。")
            key_points.append(f"太阳{sun}")
            key_points.append(f"月亮{moon}")

            stance = "星象显示，内在与外在需要平衡"

        else:
            stance = "天机不可泄露，但趋势可见"

        # 生成引用
        quotes.append(figure.catchphrase)

        return {
            "stance": stance,
            "confidence": 0.7 + (len(key_points) * 0.05),
            "reasoning": "\n".join(reasoning_parts),
            "key_points": key_points[:5],
            "quotes": quotes,
        }

    def _classify_question(self, question: str) -> str:
        """分类问题类型"""
        keywords = {
            "事业": ["事业", "工作", "职业", "升职", "跳槽", "创业", "生意"],
            "感情": ["感情", "婚姻", "恋爱", "桃花", "对象", "另一半", "分手", "复合"],
            "财运": ["财", "钱", "收入", "投资", "理财", "赚钱", "亏损"],
            "健康": ["健康", "病", "身体", "体质", "养生", "医疗"],
            "学业": ["学", "考试", "升学", "考研", "证书", "读书"],
            "人际": ["人际", "关系", "朋友", "同事", "上司", "下属"],
        }

        for qtype, words in keywords.items():
            if any(w in question for w in words):
                return qtype

        return "综合"
