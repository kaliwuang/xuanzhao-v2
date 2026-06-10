#!/usr/bin/env python3
"""
玄照 v2.0 - 108视角推理引擎

核心设计：每个人物有自己擅长的术法，用该术法的数据来推理发言。
不是模板填充，而是基于命盘数据的结构化推理。
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import json
import logging
import os

logger = logging.getLogger(__name__)
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
    """从 perspectives/figures.json 加载人物定义（回退尝试 .yaml）"""
    figures_dir = os.path.join(os.path.dirname(__file__), "..", "perspectives")

    # 优先读 JSON，回退 YAML
    json_path = os.path.join(figures_dir, "figures.json")
    yaml_path = os.path.join(figures_dir, "figures.yaml")

    figures = {}

    for fpath, loader in [
        (json_path, lambda f: json.load(f)),
        (yaml_path, lambda f: __import__("yaml").safe_load(f)),
    ]:
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = loader(f)

            for fig_data in data.get("figures", []):
                fid = fig_data.get("id", "")
                if not fid:
                    continue
                tm_data = fig_data.get("thinking_model", {})
                figure = Figure(
                    id=fid,
                    name=fig_data.get("name", ""),
                    title=fig_data.get("title", ""),
                    category=fig_data.get("category", ""),
                    faction=fig_data.get("faction", ""),
                    expertise=fig_data.get("expertise", []),
                    primary_method=fig_data.get("primary_method", ""),
                    thinking_model=ThinkingModel(
                        name=tm_data.get("name", ""),
                        principles=tm_data.get("principles", []),
                        steps=tm_data.get("steps", []),
                        key_concepts=tm_data.get("key_concepts", {}),
                    ),
                    catchphrase=fig_data.get("catchphrase", ""),
                    bio=fig_data.get("bio", ""),
                )
                # 后出现的同 id 覆盖前面的（去重）
                figures[fid] = figure

            if figures:
                logger.info(f"从 {os.path.basename(fpath)} 加载了 {len(figures)} 个人物")
                return figures
        except Exception as e:
            logger.warning(f"加载 {fpath} 失败: {e}")
            continue

    # 回退：硬编码
    logger.warning("人物定义文件未找到或加载失败，使用内置 12 人回退")
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
        "munger": Figure(
            id="munger",
            name="查理·芒格",
            title="投资哲学家",
            category="现代思想",
            faction="rational",
            expertise=["多元思维模型", "逆向思考", "投资决策"],
            primary_method="多元模型",
            thinking_model=ThinkingModel(
                name="多元思维模型",
                principles=["逆向思考", "能力圈", "多模型", "检查清单"],
                steps=["明确问题本质", "逆向思考", "跨学科调用模型", "检查清单排除盲点"],
                key_concepts={"逆向思考": "反过来想", "能力圈": "知道边界", "多元模型": "跨学科工具箱"},
            ),
            catchphrase="反过来想，总是反过来想",
            bio="伯克希尔·哈撒韦副主席，巴菲特搭档，以多元思维模型和逆向思考闻名",
        ),
        "taleb": Figure(
            id="taleb",
            name="塔勒布",
            title="不确定性思想家",
            category="现代思想",
            faction="rational",
            expertise=["反脆弱", "黑天鹅", "风险管理"],
            primary_method="反脆弱",
            thinking_model=ThinkingModel(
                name="反脆弱思维",
                principles=["反脆弱", "黑天鹅", "杠铃策略", "非线性"],
                steps=["识别脆弱点", "评估黑天鹅风险", "构建杠铃策略", "利用正向不对称性"],
                key_concepts={"反脆弱": "越冲击越强大", "黑天鹅": "极端事件", "杠铃策略": "两端极端"},
            ),
            catchphrase="风来的时候，你要在场",
            bio="《黑天鹅》《反脆弱》作者，研究不确定性与极端风险",
        ),
        "naval": Figure(
            id="naval",
            name="Naval",
            title="硅谷哲学家",
            category="现代思想",
            faction="rational",
            expertise=["长期主义", "杠杆", "幸福哲学"],
            primary_method="第一性原理",
            thinking_model=ThinkingModel(
                name="创富与幸福",
                principles=["专属知识", "杠杆", "长期博弈", "内在幸福"],
                steps=["找到专属知识", "选择杠杆放大", "长期主义筛选", "培养内在平静"],
                key_concepts={"专属知识": "天赋与热情交汇", "杠杆": "放大产出", "长期博弈": "复利信任"},
            ),
            catchphrase="寻找专属知识，用杠杆放大",
            bio="AngelList联合创始人，以财富与幸福的推文闻名",
        ),
        "stoic": Figure(
            id="stoic",
            name="斯多葛",
            title="控制二分法",
            category="现代思想",
            faction="rational",
            expertise=["控制二分法", "消极想象", "命运之爱"],
            primary_method="哲学推演",
            thinking_model=ThinkingModel(
                name="斯多葛哲学",
                principles=["控制二分", "消极想象", "命运之爱", "当下即活"],
                steps=["区分可控不可控", "消极想象预想最坏", "全力以赴可控部分", "接纳结果继续前行"],
                key_concepts={"控制二分": "能控与不能控", "消极想象": "预想坏事", "命运之爱": "Amor Fati"},
            ),
            catchphrase="控制你能控制的，其余交给命运",
            bio="古希腊罗马哲学流派，以控制二分法、消极想象和命运之爱为核心",
        ),
        "nostradamus": Figure(
            id="nostradamus",
            name="诺查丹玛斯",
            title="预言家",
            category="西方神秘学",
            faction="western",
            expertise=["四行诗预言", "星象推演", "未来预知"],
            primary_method="占星",
            thinking_model=ThinkingModel(
                name="四行诗预言",
                principles=["星象为据", "模糊预言", "周期循环", "符号解读"],
                steps=["观星象定天时", "查行星相位", "历史周期类比", "象征性预言"],
                key_concepts={"四行诗": "预言诗体", "大周期": "历史循环", "星象": "天体对应"},
            ),
            catchphrase="星辰指引未来，预言照亮黑暗",
            bio="16世纪法国预言家，著有《百诗集》",
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
            # 大运信息（十年一运的人生阶段，八字分析的核心维度）
            data["dayun"] = udm.dayun
            data["dayun_start_age"] = udm.dayun_start_age
            # 纳音五行（柱的深层属性）
            data["nayin"] = udm.nayin
            # 空亡（天干配不到地支的组合）
            data["xunkong"] = udm.xunkong
            # 藏干（地支中暗藏的天干，判断十神旺衰的关键）
            data["hidden_gans"] = udm.hidden_gans

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

        elif method == "综合":
            # 玄照视角：提取所有术法数据（7术全覆盖）
            data["available_methods"] = udm.get_available_methods()
            data["bazi"] = {
                "day_master": udm.day_master,
                "day_master_wuxing": udm.day_master_wuxing,
                "features": udm.features,
                "tiaohou": udm.tiaohou,
                "shishen": udm.shishen_gan,
                "pillars": {
                    "year": udm.bazi_year.ganzhi if udm.bazi_year else "",
                    "month": udm.bazi_month.ganzhi if udm.bazi_month else "",
                    "day": udm.bazi_day.ganzhi if udm.bazi_day else "",
                    "time": udm.bazi_time.ganzhi if udm.bazi_time else "",
                },
                "chong": udm.get_chong(),
                "he": udm.get_he(),
                "wuxing_count": udm.get_wuxing_count(),
                "dayun": udm.dayun,
                "dayun_start_age": udm.dayun_start_age,
                "nayin": udm.nayin,
                "xunkong": udm.xunkong,
                "hidden_gans": udm.hidden_gans,
            } if udm.bazi_year else {}
            data["ziwei"] = {
                "ming_gong": udm.ziwei_chart.get("ming_gong", ""),
                "wuxing_ju": udm.ziwei_chart.get("wuxing_ju", {}),
                "star_placements": udm.ziwei_chart.get("star_placements", {}),
                "sihua": udm.ziwei_chart.get("sihua", {}),
            } if udm.ziwei_chart else {}
            data["astro"] = {
                "sun_sign": udm.astro_chart.get("sun_sign", ""),
                "moon_sign": udm.astro_chart.get("moon_sign", ""),
                "ascendant_sign": udm.astro_chart.get("ascendant_sign", ""),
                "planets": udm.astro_chart.get("planets", {}),
            } if udm.astro_chart else {}
            data["qimen"] = {
                "ju_name": udm.qimen_chart.get("ju_name", ""),
                "ba_men": udm.qimen_chart.get("ba_men", {}),
                "jiu_xing": udm.qimen_chart.get("jiu_xing", {}),
            } if udm.qimen_chart else {}
            data["liuyao"] = {
                "ben_gua": udm.liuyao_chart.get("ben_gua", {}),
                "bian_gua": udm.liuyao_chart.get("bian_gua", {}),
                "dong_yao": udm.liuyao_chart.get("dong_yao", 0),
            } if udm.liuyao_chart else {}
            data["liuren"] = {
                "yue_jiang": udm.liuren_chart.get("yue_jiang", ""),
                "si_ke": udm.liuren_chart.get("si_ke", []),
                "san_chuan": udm.liuren_chart.get("san_chuan", []),
            } if udm.liuren_chart else {}
            data["taiyi"] = {
                "taiyi_gong": udm.taiyi_chart.get("taiyi_gong", ""),
                "ji_nian": udm.taiyi_chart.get("ji_nian", 0),
            } if udm.taiyi_chart else {}

        return data

    def _apply_thinking_model(self, figure: Figure, method_data: Dict, question: str) -> Dict:
        """应用思维模型生成推理 — 通过 LLM 调用"""

        from engine.llm_client import get_llm_client

        # 构造 prompt
        prompt = self._build_prompt(figure, method_data, question)

        try:
            llm = get_llm_client()
            result = llm.chat_json(
                messages=[
                    {"role": "system", "content": self._build_system_prompt(figure)},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            if result.get("parse_error"):
                # LLM 返回了非 JSON，用原始文本
                raw = result.get("raw_response", "")
                return {
                    "stance": raw[:100] if raw else "暂无明确立场",
                    "confidence": 0.5,
                    "reasoning": raw,
                    "key_points": [figure.catchphrase],
                    "quotes": [figure.catchphrase],
                }

            return {
                "stance": result.get("stance", "暂无明确立场"),
                "confidence": float(result.get("confidence", 0.7)),
                "reasoning": result.get("reasoning", ""),
                "key_points": result.get("key_points", [figure.catchphrase]),
                "quotes": result.get("quotes", [figure.catchphrase]),
            }

        except Exception as e:
            logger.warning(f"LLM 推理失败 ({figure.name}): {e}，回退模板推理")
            return self._fallback_reasoning(figure, method_data, question)

    def _build_system_prompt(self, figure: Figure) -> str:
        """构造人物 system prompt"""

        # 构造推理步骤的具体指引
        step_guides = []
        for i, step in enumerate(figure.thinking_model.steps, 1):
            step_guides.append(f"  {step}")
        steps_detail = "\n".join(step_guides)

        # 构造概念的使用指引
        concept_guides = []
        for k, v in figure.thinking_model.key_concepts.items():
            concept_guides.append(f"  · {k}：{v}——在分析中必须引用此概念")
        concepts_detail = "\n".join(concept_guides)

        return f"""你是{figure.name}（{figure.title}），{figure.bio}。
你擅长的术法：{", ".join(figure.expertise)}。
你主要使用【{figure.primary_method}】来分析。

你的思维模型「{figure.thinking_model.name}」：
核心原则：
{chr(10).join(f'  · {p}' for p in figure.thinking_model.principles)}

推理步骤（必须按此顺序逐步分析）：
{steps_detail}

关键概念（分析时必须运用）：
{concepts_detail}

你的名言：「{figure.catchphrase}」

## 分析规范

1. **数据驱动**：每一个判断都必须引用命盘中的具体数据（如天干地支、星曜、宫位、门星等），不允许凭空推测
2. **思维模型一致性**：严格按照你的推理步骤逐步展开，每个步骤对应一段分析
3. **人物一致性**：语言风格、思维角度、引用典故必须符合你的人物身份和学术传统
4. **置信度校准**：
   - 0.8-1.0：命盘数据强烈支持你的判断（多个数据点一致指向同一结论）
   - 0.5-0.7：数据有一定支持但存在不确定性
   - 0.3-0.4：数据支持较弱，主要基于经验推测
5. **具体而非笼统**：不要说"运势不错"，要说"日主甲木坐寅月得令，又有壬水生扶，身强有力"
6. **key_points 必须是具体的术法论断**，如「日主壬水身强，喜火土金」而非「命格不错」"""

    def _build_prompt(self, figure: Figure, method_data: Dict, question: str) -> str:
        """构造用户 prompt"""
        data_str = json.dumps(method_data, ensure_ascii=False, indent=2)

        # 根据术法类型给出数据解读指引
        method_hints = {
            "八字": "重点分析：日主强弱、十神配置、五行喜忌、冲合关系、调候用神、大运走势、藏干暗十神。每项判断需引用具体干支。特别注意：1）大运代表十年一阶段的人生趋势，必须结合当前大运分析；2）藏干决定地支的真实十神力量；3）纳音反映柱的深层属性。",
            "紫微": "重点分析：命宫主星、三方四正星曜组合、四化飞星走向、各宫吉凶。需引用具体星曜和宫位。",
            "占星": "重点分析：太阳/月亮/上升三重人格、行星落座与相位、宫位主题。需引用具体星座和相位角度。",
            "六爻": "重点分析：本卦变卦含义、动爻变化方向、世应主客关系、用神旺衰。需引用具体爻位和六亲。",
            "奇门": "重点分析：格局吉凶、值符值使、八门九星组合、天盘地盘关系。需引用具体宫位和门星。",
            "大六壬": "重点分析：天地盘关系、四课含义、三传走势、神煞吉凶。需引用具体课传和神将。",
            "太乙": "重点分析：太乙宫位、积年推演、阴阳遁、国运大势。需引用具体宫位和数据。",
            "综合": "综合分析所有已排术法（八字/紫微/占星/六爻/奇门/大六壬/太乙）的数据，交叉比对各术法结论，找出共识与冲突。重点：1）各术法在命主核心问题上是否指向一致；2）不同术法角度的互补性；3）综合置信度评估。",
        }
        hint = method_hints.get(figure.primary_method, "基于命盘数据进行分析。")

        return f"""以下是用【{figure.primary_method}】排盘得到的命盘数据：

```json
{data_str}
```

**数据解读指引**：{hint}

用户的问题：{question}

请严格按照你的思维模型和推理步骤进行分析，以 JSON 格式返回：
{{
  "stance": "你的一句话核心立场（必须包含具体术法论断）",
  "confidence": 0.0到1.0的置信度（按分析规范校准）,
  "reasoning": "你的完整推理过程（200-500字，按推理步骤逐段展开，每段引用具体数据）",
  "key_points": ["具体术法论断1", "具体术法论断2", "具体术法论断3"],
  "quotes": ["你的名言或相关经典引用"]
}}"""

    def _fallback_reasoning(self, figure: Figure, method_data: Dict, question: str) -> Dict:
        """LLM 失败时的模板回退"""
        question_type = self._classify_question(question)
        key_points = []
        reasoning_parts = []

        for principle in figure.thinking_model.principles[:2]:
            reasoning_parts.append(f"【{figure.name}思维】{principle}")

        dm = method_data.get("day_master", "")
        wx = method_data.get("day_master_wuxing", "")
        if dm:
            reasoning_parts.append(f"日主{dm}属{wx}")
            key_points.append(f"日主{dm}")

        features = method_data.get("features", [])
        if features:
            reasoning_parts.append(f"命局特征：{features[0]}")
            key_points.append(features[0])

        stance_map = {
            "事业": "事业宜稳健发展，借势而为",
            "感情": "感情需耐心经营，不可强求",
            "财运": "财路已现，需把握时机",
            "健康": "注意五行平衡，防患于未然",
        }
        stance = stance_map.get(question_type, "顺势而为，知命不认命")

        return {
            "stance": stance,
            "confidence": 0.6,
            "reasoning": "\n".join(reasoning_parts),
            "key_points": key_points[:5] or [figure.catchphrase],
            "quotes": [figure.catchphrase],
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
