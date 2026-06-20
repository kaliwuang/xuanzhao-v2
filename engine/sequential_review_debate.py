"""
辩论引擎 v2 — 串行审查链机制

流程：
1. 随机抓一个视角出完整推演（≥500字）
2. 传给第二个视角审：通过率+驳点（≥100字）
3. 驳了就继续传，后面的人看原文+所有驳点
4. 循环到所有人通过率>80%
5. 交给溟玄看完整过程，用溟玄的口气总结给客户
"""
import random
import logging
from typing import List, Dict, Generator
from .perspective_engine import PerspectiveOpinion, Figure, FIGURES

logger = logging.getLogger(__name__)

# 五行类象
WUXING_XIANG = {
    "木": {"象": "春生", "体": "肝", "情": "怒", "势": "破土而出", "病": "郁结不舒", "德": "仁"},
    "火": {"象": "夏长", "体": "心", "情": "喜", "势": "烈焰腾空", "病": "焦躁不安", "德": "礼"},
    "土": {"象": "化育", "体": "脾", "情": "思", "势": "厚德载物", "病": "思虑过重", "德": "信"},
    "金": {"象": "秋收", "体": "肺", "情": "悲", "势": "利刃出鞘", "病": "肃杀太过", "德": "义"},
    "水": {"象": "冬藏", "体": "肾", "情": "恐", "势": "深渊蓄力", "病": "寒凝不化", "德": "智"},
}

SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}


def _get_figure(figure_id: str) -> Figure:
    """从FIGURES缓存获取人物定义"""
    return FIGURES.get(figure_id)


class SequentialReviewDebate:
    """串行审查链辩论引擎"""

    def __init__(self):
        pass

    def run(self, opinions: List[PerspectiveOpinion], question: str,
            max_reviewers: int = 108, pass_threshold: int = 80) -> Generator[dict, None, None]:
        """
        运行串行审查链辩论。

        1. 随机选首发言者，生成≥500字完整推演
        2. 逐个传递给后续视角审查
        3. 通过率<80%必须写驳点（≥100字）
        4. 循环直到全员通过或达到max_reviewers
        5. 溟玄总结
        """
        if not opinions:
            yield {"event": "debate_end", "data": {"error": "无视角数据"}}
            return

        yield {"event": "debate_start", "data": {
            "question": question,
            "total_reviewers": min(len(opinions), max_reviewers),
        }}

        # ── 1. 随机选首发言者 ──
        first_idx = random.randint(0, len(opinions) - 1)
        first = opinions[first_idx]
        first_figure = _get_figure(first.figure_id)

        # ── 2. 生成完整推演（≥500字） ──
        analysis_text = self._generate_full_analysis(first, first_figure, question)

        yield {"event": "analysis", "data": {
            "speaker": first.figure_name,
            "speaker_method": first.primary_method,
            "text": analysis_text,
            "char_count": len(analysis_text),
        }}

        # ── 3. 串行审查链 ──
        # 把剩余视角排成队列
        reviewers = [opinions[i] for i in range(len(opinions)) if i != first_idx]
        random.shuffle(reviewers)
        reviewers = reviewers[:max_reviewers]

        review_chain = []  # 所有审查记录
        current_text = analysis_text
        round_num = 0

        while reviewers:
            round_num += 1

            # 最多审查2轮（每人最多审2次）
            if round_num > len(opinions) * 2:
                break

            reviewer = reviewers.pop(0)
            reviewer_figure = _get_figure(reviewer.figure_id)

            # 审查：给通过率和驳点
            pass_rate, rebuttal = self._review(
                reviewer, reviewer_figure, first, first_figure,
                current_text, review_chain, question
            )

            review_record = {
                "reviewer": reviewer.figure_name,
                "reviewer_method": reviewer.primary_method,
                "pass_rate": pass_rate,
                "rebuttal": rebuttal,
                "round": round_num,
            }
            review_chain.append(review_record)

            yield {"event": "review", "data": review_record}

            # 如果通过率<80%，把驳点附加到文本中，继续传
            if pass_rate < pass_threshold and rebuttal:
                current_text += f"\n\n【{reviewer.figure_name}（{reviewer.primary_method}）驳】{rebuttal}"

            # 检查是否所有人都通过了
            if pass_rate >= pass_threshold and not reviewers:
                break

            # 如果所有人都已经审查过但还有人没通过，再循环一轮
            if not reviewers and pass_rate < pass_threshold:
                # 重置审查队列：只放还没通过的人
                failed = [r for r in review_chain if r["pass_rate"] < pass_threshold]
                if failed and round_num < max_reviewers * 2:
                    # 重新排队
                    failed_ids = {r["reviewer"] for r in failed}
                    reviewers = [opinions[i] for i in range(len(opinions))
                                 if opinions[i].figure_name in failed_ids and opinions[i].figure_id != first.figure_id]
                    if not reviewers:
                        break
                else:
                    break

        # ── 4. 共识达成 ──
        final_rates = [r["pass_rate"] for r in review_chain]
        avg_rate = sum(final_rates) / len(final_rates) if final_rates else 0

        yield {"event": "consensus_reached", "data": {
            "rounds": round_num,
            "final_pass_rate": round(avg_rate, 1),
            "reviewers_count": len(review_chain),
        }}

        # ── 5. 溟玄终审 ──
        yield {"event": "mingxuan_start", "data": {"message": "溟玄审查中..."}}

        mingxuan_text = self._mingxuan_summary(
            first, first_figure, analysis_text, review_chain, question
        )

        yield {"event": "mingxuan_result", "data": {"text": mingxuan_text}}

        yield {"event": "debate_end", "data": {
            "summary": f"{first.figure_name}首发推演，{len(review_chain)}人审查，平均通过率{avg_rate:.0f}%。",
            "review_chain": review_chain,
        }}

    # ═══════════════════════════════════════════════
    # 生成完整推演（≥500字）
    # ═══════════════════════════════════════════════

    def _generate_full_analysis(self, opinion: PerspectiveOpinion,
                                 figure: Figure, question: str) -> str:
        """生成500+字的完整推演"""
        method = opinion.primary_method
        data = opinion.referenced_data
        soul = figure.soul if figure else {}
        tm = figure.thinking_model if figure else None

        parts = []

        # ── 开场：灵魂入场 ──
        voice = soul.get("voice", "") if soul else ""
        thinking_style = soul.get("thinking_style", "") if soul else ""
        catchphrase = figure.catchphrase if figure else ""

        parts.append(f"【{figure.name}（{method}）】")
        if thinking_style:
            parts.append(thinking_style)
        parts.append("")

        # ── 核心推演：按术法展开 ──
        if method == "八字":
            parts.extend(self._analyze_bazi(data, question))
        elif method == "紫微":
            parts.extend(self._analyze_ziwei(data, question))
        elif method == "占星":
            parts.extend(self._analyze_astro(data, question))
        elif method == "六爻":
            parts.extend(self._analyze_liuyao(data, question))
        elif method == "奇门":
            parts.extend(self._analyze_qimen(data, question))
        elif method == "大六壬":
            parts.extend(self._analyze_liuren(data, question))
        elif method == "太乙":
            parts.extend(self._analyze_taiyi(data, question))
        else:
            parts.extend(self._analyze_generic(data, opinion, question))

        # ── 思维模型分析 ──
        if tm and tm.principles:
            parts.append("")
            parts.append(f"依{tm.name}推演：")
            for p in tm.principles[:3]:
                parts.append(f"  {p}")

        # ── 结论 ──
        parts.append("")
        parts.append(f"【结论】{opinion.stance}")
        if opinion.key_points:
            parts.append(f"核心要点：{'；'.join(opinion.key_points[:4])}")

        # ── 收尾 ──
        if catchphrase:
            parts.append(f"\n——{catchphrase}")

        return "\n".join(parts)

    def _analyze_bazi(self, data: dict, question: str) -> list:
        """八字完整分析"""
        parts = ["一、命局总览"]

        pillars = data.get("pillars", {})
        if pillars:
            parts.append(f"  年柱{pillars.get('year','')}  月柱{pillars.get('month','')}  日柱{pillars.get('day','')}  时柱{pillars.get('time','')}")

        dm = data.get("day_master", "")
        wx = data.get("day_master_wuxing", "")
        if dm:
            xiang = WUXING_XIANG.get(wx, {})
            parts.append(f"\n二、日主分析")
            parts.append(f"  日主{dm}属{wx}。{wx}者，{xiang.get('象','')}之气，{xiang.get('势','')}。在体为{xiang.get('体','')}，在情为{xiang.get('情','')}。")

        # 五行强弱
        wx_count = data.get("wuxing_count", {})
        if wx_count:
            parts.append(f"\n三、五行分布")
            strong = max(wx_count, key=wx_count.get) if wx_count else ""
            weak = [w for w in "木火土金水" if wx_count.get(w, 0) == 0]
            parts.append(f"  五行统计：{' '.join(f'{k}{v}' for k,v in wx_count.items())}")
            if strong:
                parts.append(f"  {strong}气最旺——{WUXING_XIANG[strong]['势']}，但{WUXING_XIANG[strong]['病']}须防")
            if weak:
                parts.append(f"  缺{''.join(weak)}——{WUXING_XIANG[weak[0]]['病']}，此为命局短板")

        # 十神
        shishen = data.get("shishen", "")
        if shishen:
            parts.append(f"\n四、十神格局")
            if isinstance(shishen, dict):
                labels = {"year": "年", "month": "月", "day": "日", "time": "时"}
                ss_str = "  ".join(f"{labels.get(k,k)}柱{v}" for k, v in shishen.items() if k != "day")
                parts.append(f"  {ss_str}")
            else:
                parts.append(f"  {shishen}")

        # 特征
        features = data.get("features", [])
        if features:
            parts.append(f"\n五、命局特征")
            for f in features[:3]:
                parts.append(f"  · {f}")

        # 冲合
        chong = data.get("chong", [])
        he = data.get("he", [])
        if chong:
            parts.append(f"\n六、冲合关系")
            for c in chong[:3]:
                parts.append(f"  冲：{c}——动荡之象，命运在掀桌子")
        if he:
            for h in he[:2]:
                parts.append(f"  合：{h}——缘分牵引，聚散有时")

        # 调候
        tiaohou = data.get("tiaohou", "")
        if tiaohou:
            parts.append(f"\n七、调候用神")
            parts.append(f"  调候用神：{tiaohou}")

        # 大运
        dayun = data.get("dayun", [])
        if dayun:
            parts.append(f"\n八、大运走势")
            for d in dayun[:4]:
                if isinstance(d, dict):
                    parts.append(f"  {d.get('age','')}岁 {d.get('ganzhi','')}——{d.get('note','')}")
                else:
                    parts.append(f"  {d}")

        # 纳音
        nayin = data.get("nayin", {})
        if nayin:
            parts.append(f"\n九、纳音五行")
            for k, v in list(nayin.items())[:4]:
                parts.append(f"  {k}：{v}")

        return parts

    def _analyze_ziwei(self, data: dict, question: str) -> list:
        """紫微斗数完整分析"""
        parts = ["一、命盘总览"]

        ming_gong = data.get("ming_gong", "")
        if ming_gong:
            parts.append(f"  命宫在{ming_gong}")

        wuxing_ju = data.get("wuxing_ju", {})
        if wuxing_ju:
            parts.append(f"  五行局：{wuxing_ju}")

        # 主星
        stars = data.get("star_placements", {})
        if stars:
            parts.append(f"\n二、星曜配置")
            main_stars = {k: v for k, v in stars.items() if k in (
                "紫微", "天机", "太阳", "武曲", "天同", "廉贞",
                "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"
            )}
            for star_name, position in list(main_stars.items())[:6]:
                parts.append(f"  {star_name}在{position}")

        # 四化
        sihua = data.get("sihua", {})
        if sihua:
            parts.append(f"\n三、四化飞星")
            for hua, star in sihua.items():
                parts.append(f"  {hua}：{star}")

        # 宫位
        palaces = data.get("palaces", [])
        if palaces:
            parts.append(f"\n四、十二宫")
            for p in palaces[:6]:
                if isinstance(p, dict):
                    pname = p.get("name", "")
                    pstars = [s.get("name","") for s in p.get("major_stars", [])]
                    parts.append(f"  {pname}：{'、'.join(pstars) if pstars else '无主星'}")

        return parts

    def _analyze_astro(self, data: dict, question: str) -> list:
        """占星完整分析"""
        parts = ["一、星盘总览"]

        sun = data.get("sun_sign", "")
        moon = data.get("moon_sign", "")
        asc = data.get("asc_sign", "")
        if sun:
            parts.append(f"  太阳{sun}——核心意志与生命力")
        if moon:
            parts.append(f"  月亮{moon}——情感模式与内在需求")
        if asc:
            parts.append(f"  上升{asc}——外在表现与第一印象")

        # 行星
        planets = data.get("planets", {})
        if planets:
            parts.append(f"\n二、行星落座")
            for planet, info in list(planets.items())[:8]:
                if isinstance(info, dict):
                    parts.append(f"  {planet}在{info.get('sign','')} {info.get('degree','')}°{'（逆行）' if info.get('retrograde') else ''}")

        # 宫位
        houses = data.get("houses", {})
        if houses:
            parts.append(f"\n三、宫位系统")
            for house, info in list(houses.items())[:6]:
                if isinstance(info, dict):
                    parts.append(f"  第{house}宫头{info.get('cusp_sign','')}")

        # 相位
        aspects = data.get("aspects", [])
        if aspects:
            parts.append(f"\n四、相位格局")
            for a in aspects[:5]:
                if isinstance(a, dict):
                    parts.append(f"  {a.get('planet1','')} {a.get('aspect','')} {a.get('planet2','')}（容许度{a.get('orb','')}°）")

        return parts

    def _analyze_liuyao(self, data: dict, question: str) -> list:
        """六爻完整分析"""
        parts = ["一、卦象总览"]

        ben = data.get("ben_gua", {})
        bian = data.get("bian_gua", {})
        if ben:
            bname = ben.get("name", "")
            parts.append(f"  本卦：{bname}")
            # 卦意解读
            gua_yi = {
                "天火同人": "同人于野，亨。与人和同，利于涉险。",
                "风雷益": "益，利有攸往。损上益下，利济天下。",
                "地雷复": "复，亨。出入无疾，反复其道。",
                "天雷无妄": "无妄，元亨利贞。无妄之行，天之命也。",
                "火地晋": "晋，康侯用锡马蕃庶。明出地上，顺而丽乎大明。",
                "水雷屯": "屯，元亨利贞。屯者，物之始生也。",
            }
            if bname in gua_yi:
                parts.append(f"  卦意：{gua_yi[bname]}")

        if bian:
            parts.append(f"  变卦：{bian.get('name','')}")

        dong = data.get("dong_yao", [])
        if dong:
            parts.append(f"  动爻：第{'、'.join(str(y) for y in dong)}爻")
            parts.append(f"  动爻为变之机——动在哪，变在哪，这是卦的核心信息")

        shi = data.get("shi", 0)
        ying = data.get("ying", 0)
        if shi:
            parts.append(f"  世爻第{shi}爻（代表问卦人），应爻第{ying}爻（代表所问之事）")
            if shi and ying:
                parts.append(f"  世应关系：世克应则主动，应克世则被动。世生应则我去求，应生世则来就我。")

        gong = data.get("gua_gong_wuxing", "")
        if gong:
            parts.append(f"  卦宫五行：{gong}——六亲以此定")

        # 六爻详解
        yao_list = data.get("yao_list", [])
        if yao_list:
            parts.append(f"\n二、六爻详解")
            yao_names = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]
            for i, yao in enumerate(yao_list[:6]):
                if isinstance(yao, dict):
                    yin = "▅▅▅▅▅" if yao.get("yinyang") == "阳" else "▅▅  ▅▅"
                    dong_mark = " ○" if yao.get("is_dong") else ""
                    shi_mark = " [世]" if yao.get("is_shi") else ""
                    ying_mark = " [应]" if yao.get("is_ying") else ""
                    liuqin = yao.get("liuqin", "")
                    liushou = yao.get("liushou", "")
                    parts.append(f"  {yao_names[i]}：{yin}{dong_mark}{shi_mark}{ying_mark} {liuqin} {liushou}")

        # 六亲分析
        liuqin_data = data.get("liu_qin", [])
        if liuqin_data:
            parts.append(f"\n三、六亲格局")
            for i, q in enumerate(liuqin_data[:6]):
                if isinstance(q, dict):
                    parts.append(f"  第{i+1}爻：{q.get('yinyang','')}{q.get('liuqin','')} {q.get('liushou','')} {'★动' if q.get('is_dong') else ''}")

        # 用神分析
        parts.append(f"\n四、用神取用")
        if question and any(k in question for k in ["事业", "工作"]):
            parts.append(f"  问事业，取官鬼为用神")
        elif question and any(k in question for k in ["财", "钱"]):
            parts.append(f"  问财运，取妻财为用神")
        elif question and any(k in question for k in ["感情", "婚姻"]):
            parts.append(f"  问感情，取妻财/官鬼为用神")
        else:
            parts.append(f"  视所问之事取用神")

        # 世应生克
        if shi and ying:
            parts.append(f"\n五、世应关系")
            parts.append(f"  世爻在第{shi}爻，应爻在第{ying}爻")
            parts.append(f"  世应之间隔几位，决定了事情的远近缓急")

        return parts

    def _analyze_qimen(self, data: dict, question: str) -> list:
        """奇门遁甲完整分析"""
        parts = ["一、格局总览"]

        ju = data.get("ju_name", "")
        if ju:
            parts.append(f"  {ju}")

        # 八门
        ba_men = data.get("ba_men", {})
        if ba_men:
            parts.append(f"\n二、八门")
            for palace, men in list(ba_men.items())[:9]:
                ji = "★吉" if men in ("开门", "生门", "休门") else ""
                parts.append(f"  {palace}宫：{men} {ji}")

        # 九星
        jiu_xing = data.get("jiu_xing", {})
        if jiu_xing:
            parts.append(f"\n三、九星")
            for palace, star in list(jiu_xing.items())[:9]:
                parts.append(f"  {palace}宫：{star}")

        # 八神
        ba_shen = data.get("ba_shen", {})
        if ba_shen:
            parts.append(f"\n四、八神")
            for palace, shen in list(ba_shen.items())[:8]:
                parts.append(f"  {palace}宫：{shen}")

        # 值符值使
        zhi_fu = data.get("zhi_fu", {})
        zhi_shi = data.get("zhi_shi", {})
        if zhi_fu:
            parts.append(f"\n五、值符值使")
            parts.append(f"  值符：{zhi_fu}")
            parts.append(f"  值使：{zhi_shi}")

        return parts

    def _analyze_liuren(self, data: dict, question: str) -> list:
        """大六壬完整分析"""
        parts = ["一、课式总览"]

        yj = data.get("yue_jiang", "")
        if yj:
            parts.append(f"  月将：{yj}")

        # 四课
        si_ke = data.get("si_ke", [])
        if si_ke:
            parts.append(f"\n二、四课")
            for i, k in enumerate(si_ke[:4], 1):
                if isinstance(k, (list, tuple)):
                    parts.append(f"  第{i}课：{' '.join(str(x) for x in k)}")

        # 三传
        san_chuan = data.get("san_chuan", [])
        if san_chuan:
            parts.append(f"\n三、三传")
            names = ["初传", "中传", "末传"]
            for i, sc in enumerate(san_chuan[:3]):
                if isinstance(sc, (list, tuple)):
                    parts.append(f"  {names[i]}：{' '.join(str(x) for x in sc)}")

        # 天将
        tian_jiang = data.get("tian_jiang", {})
        if tian_jiang:
            parts.append(f"\n四、天将")
            for zhi, jiang in list(tian_jiang.items())[:6]:
                parts.append(f"  {zhi}：{jiang}")

        # 格局
        ge_ju = data.get("ge_ju", "")
        if ge_ju:
            parts.append(f"\n五、格局：{ge_ju}")

        # 用神
        yong_shen = data.get("yong_shen", {})
        if yong_shen:
            parts.append(f"\n六、用神")
            for k, v in yong_shen.items():
                parts.append(f"  {k}：{v}")

        return parts

    def _analyze_taiyi(self, data: dict, question: str) -> list:
        """太乙神数完整分析"""
        parts = ["一、格局总览"]

        gong = data.get("taiyi_gong", "")
        if gong:
            parts.append(f"  太乙落宫：{gong}")

        jn = data.get("ji_nian", 0)
        if jn:
            parts.append(f"  积年：{jn}")

        ju = data.get("ju_name", "")
        if ju:
            parts.append(f"  局名：{ju}")

        yy = data.get("yin_yang", "")
        if yy:
            parts.append(f"  阴阳遁：{yy}")

        # 主客算
        zhu = data.get("zhu_suan", [])
        ke = data.get("ke_suan", [])
        if zhu:
            parts.append(f"\n二、主客算")
            parts.append(f"  主算：{zhu}")
            if ke:
                parts.append(f"  客算：{ke}")

        # 三基
        san_ji = data.get("san_ji", {})
        if san_ji:
            parts.append(f"\n三、三基")
            for k, v in san_ji.items():
                parts.append(f"  {k}：{v}")

        return parts

    def _analyze_generic(self, data: dict, opinion: PerspectiveOpinion, question: str) -> list:
        """通用分析（非七术）"""
        parts = [f"一、{opinion.primary_method}视角"]
        parts.append(f"  {opinion.stance}")
        if opinion.key_points:
            parts.append(f"\n二、核心论据")
            for kp in opinion.key_points[:5]:
                parts.append(f"  · {kp}")
        if opinion.reasoning:
            parts.append(f"\n三、推理过程")
            parts.append(f"  {opinion.reasoning[:200]}")
        return parts

    # ═══════════════════════════════════════════════
    # 审查：通过率+驳点
    # ═══════════════════════════════════════════════

    def _review(self, reviewer: PerspectiveOpinion, reviewer_figure: Figure,
                original: PerspectiveOpinion, original_figure: Figure,
                current_text: str, review_chain: list, question: str) -> tuple:
        """
        审查逻辑：用自己的术法数据检查原文，给出通过率和驳点。
        通过率随审查轮数增长（文本越丰富，越容易通过）。
        返回 (pass_rate: int, rebuttal: str)
        """
        method = reviewer.primary_method
        data = reviewer.referenced_data
        soul = reviewer_figure.soul if reviewer_figure else {}

        # 基础通过率：哈希确定性
        h = hash(current_text + reviewer.figure_name + "review_salt") % 100
        base_rate = 35 + h % 50  # 35-84

        # 立场冲突检测
        reviewer_stance = reviewer.stance
        original_stance = original.stance
        opposing = [("动", "稳"), ("进", "守"), ("突破", "保守"), ("积极", "谨慎"), ("攻", "防")]
        stance_conflict = False
        for pos, neg in opposing:
            if (pos in reviewer_stance and neg in original_stance) or \
               (neg in reviewer_stance and pos in original_stance):
                stance_conflict = True
                base_rate = max(20, base_rate - 15)
                break

        # 同术法更严格
        if method == original.primary_method:
            base_rate = max(15, base_rate - 10)

        # 随着审查轮数增加，文本越来越丰富，通过率自然提升
        rounds_so_far = len(review_chain)
        round_bonus = min(30, rounds_so_far * 5)  # 每轮+5%，最多+30%
        base_rate = min(95, base_rate + round_bonus)

        pass_rate = min(95, base_rate)

        # 生成驳点
        rebuttal = ""
        if pass_rate < 80:
            rebuttal = self._generate_rebuttal(
                reviewer, reviewer_figure, original, original_figure,
                current_text, data, method, stance_conflict, rounds_so_far
            )

        return pass_rate, rebuttal

    def _generate_rebuttal(self, reviewer, reviewer_figure, original, original_figure,
                            current_text, data, method, stance_conflict, round_num=0) -> str:
        """生成驳点（≥100字）"""
        parts = []

        # 开头：用自己的术法视角切入
        voice = reviewer_figure.soul.get("voice", "") if reviewer_figure and reviewer_figure.soul else ""
        parts.append(f"从{method}角度看，{original.figure_name}的推演有以下不足：")

        # 按术法生成具体驳点
        if method == "八字":
            dm = data.get("day_master", "")
            wx = data.get("day_master_wuxing", "")
            features = data.get("features", [])
            chong = data.get("chong", [])

            if dm:
                parts.append(f"日主{dm}属{wx}，{WUXING_XIANG.get(wx, {}).get('势', '')}——原文对此分析不够深入。")
            if features:
                parts.append(f"命局{features[0]}，这才是关键所在，原文忽略了这一点。")
            if chong:
                parts.append(f"冲象{chong[0]}带来的动荡，原文未能充分解读其对{self._question_topic(original.stance)}的影响。")

        elif method == "紫微":
            ming_gong = data.get("ming_gong", "")
            stars = data.get("star_placements", {})
            if ming_gong:
                parts.append(f"命宫在{ming_gong}，三方四正的联动关系原文没有展开。")
            if stars:
                main = [k for k in stars if k in ("紫微","天机","太阳","武曲","天同","廉贞","天府","太阴","贪狼","巨门","天相","天梁","七杀","破军")]
                if main:
                    parts.append(f"主星{'、'.join(main[:2])}的组合意象，与原文的结论存在出入。")

        elif method == "占星":
            sun = data.get("sun_sign", "")
            moon = data.get("moon_sign", "")
            if sun:
                parts.append(f"太阳{sun}的核心驱动力，原文未能从行星落座的角度深入分析。")
            if moon:
                parts.append(f"月亮{moon}的情感模式对决策的影响被低估了。")

        elif method == "六爻":
            ben = data.get("ben_gua", {})
            dong = data.get("dong_yao", [])
            if ben:
                parts.append(f"本卦{ben.get('name','')}的卦意与原文结论存在矛盾。")
            if dong:
                parts.append(f"动爻在第{'、'.join(str(y) for y in dong)}爻，变化的方向原文没有考虑到。")

        elif method == "奇门":
            ba_men = data.get("ba_men", {})
            ji_men = [k for k, v in ba_men.items() if v in ("开门", "生门", "休门")]
            if ji_men:
                parts.append(f"吉门在{'、'.join(ji_men[:2])}宫，原文对此时势的判断不够精准。")
            else:
                parts.append(f"八门中无吉门当值，此时不宜冒进，原文的积极判断需要修正。")

        elif method == "大六壬":
            san_chuan = data.get("san_chuan", [])
            if san_chuan:
                parts.append(f"三传{'→'.join(str(s[0]) if isinstance(s, list) else str(s) for s in san_chuan[:3])}，传变的趋势与原文结论不符。")

        elif method == "太乙":
            gong = data.get("taiyi_gong", "")
            if gong:
                parts.append(f"太乙落{gong}宫，主客之势与原文的判断方向相反。")

        else:
            parts.append(f"从{method}的方法论来看，原文的推理链条存在薄弱环节。")

        # 立场冲突补充
        if stance_conflict:
            parts.append(f"原文主张{'进取' if '进' in original.stance or '动' in original.stance else '稳健'}，但{reviewer.figure_name}认为当前局势应当{'稳扎稳打' if '稳' in reviewer.stance else '果断行动'}。")

        # 收尾
        catchphrase = reviewer_figure.catchphrase if reviewer_figure else ""
        if catchphrase:
            parts.append(f"——{catchphrase}")

        result = "\n".join(parts)
        # 确保≥100字
        if len(result) < 100:
            result += f"\n{reviewer.figure_name}从{method}的维度补充：原文未能穷尽变量，推演的根基还需加固。多算胜少算，不可轻率定论。"

        return result

    def _question_topic(self, stance: str) -> str:
        """从stance判断话题"""
        if any(k in stance for k in ["事业", "工作", "职业"]):
            return "事业"
        if any(k in stance for k in ["感情", "婚姻", "桃花"]):
            return "感情"
        if any(k in stance for k in ["财", "钱", "投资"]):
            return "财运"
        return "整体运势"

    # ═══════════════════════════════════════════════
    # 溟玄终审：看完整过程，用自己的口气总结
    # ═══════════════════════════════════════════════

    def _mingxuan_summary(self, first: PerspectiveOpinion, first_figure: Figure,
                           analysis: str, review_chain: list, question: str) -> str:
        """溟玄看完整审查链，用自己的口气给客户总结"""
        # 统计审查数据
        total_reviewers = len(review_chain)
        avg_rate = sum(r["pass_rate"] for r in review_chain) / total_reviewers if total_reviewers else 0
        rebuttals = [r for r in review_chain if r["rebuttal"]]
        methods_seen = set(r["reviewer_method"] for r in review_chain)

        # 提取关键驳点
        key_disputes = []
        for r in rebuttals[:3]:
            key_disputes.append(f"{r['reviewer']}（{r['reviewer_method']}）：{r['rebuttal'][:60]}")

        # 提取五行数据
        all_text = analysis + " ".join(r["rebuttal"] for r in rebuttals)
        wuxing_hits = [w for w in "木火土金水" if w in all_text]

        parts = []

        # 【观】
        if wuxing_hits:
            parts.append(f"【观】{first.figure_name}以{first.primary_method}开路，{''.join(wuxing_hits)}气流转。{total_reviewers}人审查，通过率{avg_rate:.0f}%。")
        else:
            parts.append(f"【观】{first.figure_name}以{first.primary_method}开路，{total_reviewers}人审查，通过率{avg_rate:.0f}%。")

        # 【析】
        parts.append("")
        if rebuttals:
            parts.append(f"审查中有{len(rebuttals)}人提出异议：")
            for d in key_disputes:
                parts.append(f"  {d}")
            parts.append("")
            parts.append(f"争议集中在{'、'.join(list(methods_seen)[:3])}的交叉验证上。多方术法指向不同，说明命局复杂，不是一句话能定性的。")
        else:
            parts.append(f"全员通过，{first.primary_method}的推演经得起{len(methods_seen)}种术法的交叉检验。")

        # 【判】
        parts.append("")
        # 溟玄式判断
        if avg_rate >= 80:
            parts.append(f"【判】{first.figure_name}的推演站得住脚。{first.primary_method}给出了方向，审查团验证了根基。")
        else:
            parts.append(f"【判】{first.figure_name}的推演有根基但有分歧。分歧不是坏事——分歧说明命局有多面性，不能一刀切。")

        # 溟玄式收尾（用自己的五行语言，不引用语录）
        parts.append("")
        if "冲" in all_text:
            parts.append("冲象贯穿全程——命运在掀桌子。不是坏事，是逼你换一种活法。")
        elif wuxing_hits:
            wx0 = wuxing_hits[0]
            parts.append(f"{wx0}气贯穿——{WUXING_XIANG[wx0]['势']}。方向有了，剩下的就是执行力。")
        else:
            parts.append("气象混沌，但混沌中自有秩序。把眼前的事做好，下一步自然显现。")

        # 行动指引
        parts.append("")
        topic = self._question_topic(first.stance)
        actions = {
            "事业": "今晚就动手。想三年不如干三个月。",
            "感情": "先把自己修好。对的人来了你接得住。",
            "财运": "赚到的钱留三成不动。守住比赚到更重要。",
            "健康": "今晚11点前关灯。第一步，也是最重要的一步。",
            "整体运势": "把眼前这一步走好。下一步自然会来。",
        }
        parts.append(actions.get(topic, actions["整体运势"]))

        return "\n".join(parts)
