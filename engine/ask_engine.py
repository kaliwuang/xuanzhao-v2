"""
玄照 · AI 提问引擎 (Ask Engine)
=================================

客户/梧提问,玄照 AI 基于以下数据回答:
1. 八术结构化数据(可选 — 客户提问时才有)
2. 反向案例库(knowledge/cases/counter/)
3. 规则库(knowledge/rules/)
4. 108 视角人物解读(可指定)

设计原则(2026-07-11 梧指令):
1. 规则拼接,不用 LLM — 保持离线可跑 + 不幻觉
2. 支持两种模式:
   - 客户提问(传 birth) → 叠加命盘背景
   - 知识问答(不传 birth) → 纯玄学概念回答
3. 支持换视角(传 figures 参数指定 1-N 人)
4. 答案诚实:不能精确预测的标"无法预测"
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
RULES_DIR = KNOWLEDGE_DIR / "rules"
COUNTER_DIR = KNOWLEDGE_DIR / "cases" / "counter"
CASES_DIR = KNOWLEDGE_DIR / "cases"

# ============== 玄学概念知识库(精简版) ==============
# 来源:玄照 engine + 知识库校勘本 + 反向案例库
# 这些是"概念-解读"对,提问时关键词命中就用

CONCEPT_KB = {
    # 五行
    "身弱": {
        "definition": "日主(出生日天干)力量弱于命局整体,需要印星(帮身)或比劫(同帮)扶持",
        "evidence_pattern": "月令失令/克泄耗多",
        "strategy": ["借势", "合作", "不独立扛事", "找贵人"],
        "wrong_strategy": ["单打独斗", "硬扛"],
        "viewpoint_munger": "身弱的人把风险留给别人,把稳的部分留给自己,这是能力圈的智慧",
        "viewpoint_naval": "身弱的人需要好搭子,本质是承认自己不是万能的",
        "viewpoint_laozi": "身弱是道,不强为才能避开陷阱",
        "viewpoint_sunzi": "身弱者善用兵法,借势作战",
        "viewpoint_socrates": "承认自己不知道,就是知道的第一步",
        "viewpoint_kahneman": "身弱的人更容易被认知偏误影响,投资时更要慢决策",
        "viewpoint_jung": "身弱不是缺陷,是阴影,整合它反而成为独特优势",
        "viewpoint_feynman": "身弱说明你的载体有限,要在有限上做加法而非追多",
        "counter_cases": ["002-bazi-failure-yangren", "026-cv-taidou-evolution"],
        "confidence": 80,
    },
    "身强": {
        "definition": "日主力量强于命局整体,有足够精力泄耗,适合独立做事",
        "strategy": ["创业", "领导", "主动输出", "食伤生财"],
        "viewpoint_munger": "身强的人有资本犯错,本钱是稀缺资源",
        "viewpoint_naval": "身强配自由职业/创业,专注专长",
        "confidence": 75,
    },
    "食神制杀": {
        "definition": "食神(泄秀之神)克制七杀(压力之煞),是经典贵格,代表有化压力为动力的能力",
        "viewpoint_feynman": "杀是问题,食是答案,有答案的人能承压",
        "viewpoint_naval": "食神制杀 = 用真本事化解恶意,这是独立生存能力",
        "viewpoint_munger": "凡杀不死我的让我更强,前提是我有解药",
        "confidence": 70,
    },
    "伤官见官": {
        "definition": "伤官(叛逆表达)克正官(规范),古代认为大凶,现代则要看具体格局",
        "viewpoint_laozi": "伤官见官是反者道之动,不一定是坏事",
        "viewpoint_munger": "反传统的创新者,要么成大事要么进监狱",
        "counter_cases": ["003-bazi-shangguan-yingzai"],
        "warning": "伤官见官为祸百端,要看是否有印制化",
        "confidence": 60,
    },
    "财格": {
        "definition": "月令藏财或天干透财,以财星为用神",
        "viewpoint_naval": "财格身弱扛不动,合作 > 单干",
        "viewpoint_munger": "财富是认知的变现,命理只是开局的牌",
        "counter_cases": ["009-bazi-must-rich"],
        "warning": "财格 + 身弱 = 有财难守",
        "confidence": 65,
    },
    "七杀": {
        "definition": "偏官,克我者异性,代表压力/竞争/权威",
        "viewpoint_sunzi": "杀是敌,能化敌为我用,就是大才",
        "viewpoint_socrates": "未经省察的人生不值得过,杀让你被迫省察",
        "confidence": 70,
    },
    "桃花": {
        "definition": "异性缘/感情机遇的神煞,根据日支查桃花位",
        "viewpoint_kahneman": "桃花是注意力偏差,你关注某个方向就会高估",
        "viewpoint_jung": "桃花 = 阿尼玛/阿尼姆斯原型投射",
        "counter_cases": ["013-bazi-spouse-death"],
        "warning": "有桃花不等于有婚姻,要区分缘分和实际",
        "confidence": 50,  # 算法偏置中等
    },
    "真太阳时": {
        "definition": "出生地经度校正后的真实太阳时间,东八区标准时可能差 30+ 分钟",
        "evidence_pattern": "出生地经度 ÷ 15 = 时区差",
        "warning": "差 5 分钟可能跨时辰,影响时柱+日主+大运起算",
        "advice": "医院出生证明通常用东八区标准时,需核对",
        "confidence": 95,
    },
    "时辰": {
        "definition": "12 时辰划分,每个时辰 2 小时,边界在奇数小时(子丑寅卯辰巳午未申酉戌亥)",
        "evidence_pattern": "23:00-01:00 子时,01:00-03:00 丑时,以此类推",
        "warning": "真太阳时校正后接近时辰边界 ±5 分钟,需要客户确认",
        "confidence": 90,
    },
    "流年": {
        "definition": "当年的天干地支对命局的影响",
        "warning": "流年判断只看当年,流月流日细颗粒度更准",
        "confidence": 65,
    },
    "大运": {
        "definition": "十年一运,基于月柱和阴阳年排布,影响整十年的趋势",
        "viewpoint_sunzi": "大运是大势,顺势者昌",
        "confidence": 80,
    },
    "格局": {
        "definition": "月令透出的十神结构,反映命局核心趋势",
        "warning": "格局只是骨架,具体路径看用神配合",
        "confidence": 75,
    },
    "用神": {
        "definition": "对日主最有利的神,决定喜用方向",
        "warning": "用神随大运变化,中年用神和青年可能不同",
        "confidence": 80,
    },
    "喜用神": {
        "definition": "命局最需要的五行,喜神+用神合并",
        "viewpoint_munger": "在能力圈内做事,喜用神就是你的能力圈",
        "confidence": 85,
    },
    "忌神": {
        "definition": "对日主不利的五行,需要规避",
        "warning": "忌神不是绝对不能碰,只是要少碰或转化",
        "confidence": 80,
    },
    "华盖": {
        "definition": "艺术/宗教/哲学天赋的神煞,主孤高",
        "viewpoint_jung": "华盖 = 内倾直觉,艺术家标配",
        "confidence": 75,
    },
    "驿马": {
        "definition": "出行/迁移的神煞,代表奔波",
        "viewpoint_naval": "驿马星 = 全球流动性的命理版本",
        "confidence": 75,
    },
    "国印贵人": {
        "definition": "代表官方背景/公职适合的神煞",
        "confidence": 80,
    },
    "羊刃": {
        "definition": "五行阳刃,代表刚强/极端/冲动",
        "warning": "羊刃 + 七杀 = 血光之灾,古代最忌",
        "counter_cases": ["002-bazi-failure-yangren"],
        "confidence": 60,
    },
    "十恶大败": {
        "definition": "破财败业的大凶神煞,古代最忌",
        "warning": "命中带不一定会应验,要看整体配合",
        "confidence": 50,
    },
    "紫微": {
        "definition": "紫微斗数,星曜派命理,以星曜组合论命",
        "viewpoint_jung": "紫微 = 原型理论的命理版本",
        "confidence": 80,
    },
    "占星": {
        "definition": "西洋占星术,以出生时刻行星位置论命",
        "viewpoint_jung": "占星是集体无意识的命理投射",
        "viewpoint_kahneman": "巴纳姆效应让人感觉占星很准",
        "counter_cases": ["018-cv-emotion-actually-happy"],
        "confidence": 50,  # 算法偏置中等
    },
    "六壬": {
        "definition": "大六壬,占卜类命理,以月将加时起课",
        "confidence": 70,
    },
    "奇门": {
        "definition": "奇门遁甲,时空类占卜,以局数+九星+八门论事",
        "viewpoint_sunzi": "奇门是兵法的时空应用",
        "confidence": 70,
    },
    "太乙": {
        "definition": "太乙神数,古代皇室专用占卜,以积年+局数论事",
        "confidence": 65,
    },
    "六爻": {
        "definition": "六爻纳甲,以卦象+爻辞论事",
        "viewpoint_feynman": "六爻的概率论本质 — 64 卦 × 6 爻 = 384 状态",
        "confidence": 65,
    },
    "姓名学": {
        "definition": "通过汉字笔画+五行推算命运",
        "viewpoint_munger": "起名是心理学锚定效应,姓名影响自我认知",
        "counter_cases": ["011-yimu-tengluo-jiayi"],
        "confidence": 40,  # 算法偏置较大
    },
    "玄学": {
        "definition": "中国传统命理/占卜/预测学的统称",
        "viewpoint_kahneman": "玄学是叙事自我对随机事件的因果解释",
        "viewpoint_jung": "玄学是集体无意识的语言化表达",
        "viewpoint_socrates": "认识你自己比认识宇宙更重要",
        "warning": "玄学不是科学,但不是完全没有心理/文化价值",
        "confidence": 60,
    },
    "大运换运": {
        "definition": "每 10 年换一次大运,转折点",
        "viewpoint_sunzi": "换运是战机,该动则动,该守则守",
        "warning": "换运前后 1-2 年是震荡期,不宜大动",
        "confidence": 70,
    },
    "流月": {
        "definition": "当月的天干地支对命局的影响,颗粒度比流年更细",
        "warning": "流月判断是启发式,准确度有限",
        "confidence": 30,  # agent 自承启发式
    },
    # ========== 神煞类(8) ==========
    "天乙贵人": {
        "definition": "命中最重要贵人星,遇险呈祥,坐于日干所喜之位",
        "evidence_pattern": "以日干查其他天干,甲戊见丑未,乙己见子申等",
        "strategy": ["关键事找贵人", "借力居中协调", "合作大于独立"],
        "wrong_strategy": ["事必躬亲", "拒绝他人帮助"],
        "viewpoint_munger": "贵人不是来替你做事的,是来赋能的",
        "viewpoint_laozi": "天道无亲,常与善人,贵人即善缘",
        "viewpoint_naval": "专长 + 贵人 = 杠杆放大",
        "viewpoint_sunzi": "善用兵者,求之于势,不责于人,贵人是势",
        "confidence": 50,
    },
    "文昌贵人": {
        "definition": "学业/文书贵人,主功名考试,利于读书学习",
        "evidence_pattern": "以日干查,甲见乙,乙见文昌属",
        "viewpoint_kahneman": "文昌是系统性学习 + 重复带来的认知优势",
        "viewpoint_feynman": "文昌贵人 = 喜欢学习的人的概率分布",
        "viewpoint_kongzi": "学而时习之,不亦说乎,文昌本质是学习之力",
        "confidence": 40,
    },
    "太极贵人": {
        "definition": "哲学/宗教/玄学天赋的主星,主悟性",
        "viewpoint_jung": "太极 = 整合阴阳对立面的个体化倾向",
        "viewpoint_laozi": "万物负阴而抱阳,太极是中",
        "viewpoint_socrates": "未经省察的人生不值得过,太极人天然爱省察",
        "confidence": 45,
    },
    "天德贵人": {
        "definition": "月德合,化解凶煞的吉星,主一生少灾",
        "strategy": ["遇难呈祥", "心怀善念", "低调内敛"],
        "viewpoint_naval": "天德 = 长期复利 + 提前规划带来的护城河",
        "viewpoint_stoic": "能控制的只有自己,天德是自控的护身符",
        "confidence": 40,
    },
    "月德贵人": {
        "definition": "月内吉星,主逢凶化吉,做事有长辈/师长相助",
        "viewpoint_munger": "月德是善良的复利,长期会变成安全边际",
        "viewpoint_kongzi": "德不孤,必有邻,月德者有邻",
        "confidence": 40,
    },
    "将星": {
        "definition": "权力/领导/统帅之煞,主掌权能力,可成大将",
        "strategy": ["掌舵", "任主帅", "控全局"],
        "wrong_strategy": ["幕后", "从属"],
        "viewpoint_sunzi": "将星是帅才,能聚人而战",
        "viewpoint_nietzsche": "将星是权力意志,驾驭他人而非被驾驭",
        "viewpoint_hanfeizi": "将星者势也,抱法处势则治",
        "counter_cases": ["012-bazi-career-gi-failure"],
        "warning": "将星无制易独断,要配印星护身",
        "confidence": 45,
    },
    "亡神": {
        "definition": "损耗/失物/失踪之煞(凶煞之一),主破耗",
        "strategy": ["稳守", "不冒进", "守好现金流"],
        "wrong_strategy": ["投资", "合伙", "远行"],
        "viewpoint_stoic": "亡神提醒你什么不是你能控制的",
        "viewpoint_munger": "避开亡神 = 知道自己的盲区",
        "counter_cases": ["022-cv-wealth-low-income"],
        "warning": "亡神逢冲更凶,大运流年触发要特别小心",
        "confidence": 40,
    },
    "劫煞": {
        "definition": "劫掠/破财/官非之煞,主突发性破财或纷争",
        "strategy": ["低调", "不露财", "远离是非"],
        "wrong_strategy": ["借钱给人", "合伙", "出头"],
        "viewpoint_naval": "劫煞 = 别人的嫉妒成本,要会隐形",
        "viewpoint_hanfeizi": "事以密成,语以泄败,劫煞之人宜密",
        "counter_cases": ["022-cv-wealth-low-income"],
        "warning": "劫煞 + 财星 = 财来财去,留不住",
        "confidence": 40,
    },
    # ========== 十神类(5) ==========
    "枭神(偏印)": {
        "definition": "偏印也叫枭神,主孤独/特殊才能/非主流学习方式",
        "evidence_pattern": "克我者异性,如甲见辛",
        "strategy": ["研究", "专业深耕", "独自打磨技艺"],
        "wrong_strategy": ["强行社交", "照搬主流路径"],
        "viewpoint_jung": "偏印 = 内倾直觉型,远离世俗智慧",
        "viewpoint_feynman": "偏印人是少数能走第一性原理的人",
        "viewpoint_nietzsche": "偏印 = 高级的孤独,天才的代价",
        "counter_cases": ["004-bazi-shishen-failure-1"],
        "confidence": 70,
    },
    "倒食": {
        "definition": "偏印夺食的具体表现,枭神克食神,伤食神之气",
        "viewpoint_munger": "倒食 = 想输出的冲动被内在压抑",
        "viewpoint_laozi": "大音希声,倒食者言迟而智深",
        "warning": "倒食多主孤独,表达渠道受阻",
        "confidence": 65,
    },
    "比肩": {
        "definition": "同我者同性,代表竞争/同辈/合作,也是独立意识",
        "evidence_pattern": "同五行同性,如甲见甲",
        "strategy": ["平等合作", "团队作战", "独立决策"],
        "wrong_strategy": ["过度依赖", "占人便宜"],
        "viewpoint_naval": "比肩 = 同辈竞争,要在同质中做出差异",
        "viewpoint_sunzi": "知彼知己,比肩者知己最难",
        "confidence": 75,
    },
    "劫财": {
        "definition": "异性比肩,主争夺/破财/合伙风险,不利父亲和妻子",
        "evidence_pattern": "同五行异性,如甲见乙",
        "strategy": ["独立", "不合伙大钱", "契约清晰"],
        "wrong_strategy": ["合伙", "借钱出去", "混账经营"],
        "viewpoint_munger": "劫财是合伙的天坑,大多数合伙死于劫财",
        "viewpoint_hanfeizi": "利出一孔,劫财者利出多孔则败",
        "counter_cases": ["022-cv-wealth-low-income"],
        "warning": "劫财 + 财星 = 财来财去,合伙尤其慎",
        "confidence": 75,
    },
    "正印": {
        "definition": "生我者异性,主贵人/学业/保护/名声,母亲也主此",
        "evidence_pattern": "生日干之异性五行,如甲见癸",
        "strategy": ["借势", "拜师", "求推荐", "沉淀学习"],
        "wrong_strategy": ["冒进", "独立闯荡"],
        "viewpoint_munger": "正印是真正的能力圈,长期复利",
        "viewpoint_kongzi": "师友之益,正印是良师",
        "viewpoint_kahneman": "正印是慢决策的护栏,不全靠系统1",
        "confidence": 80,
    },
    # ========== 长生 12 阶段(6) ==========
    "长生": {
        "definition": "五行 12 阶段第一阶段,初生之气,如婴儿初生",
        "viewpoint_laozi": "含德之厚,比如赤子,长生之气",
        "viewpoint_feynman": "长生阶段好奇,什么都要试",
        "confidence": 60,
    },
    "帝旺": {
        "definition": "巅峰,五行最强阶段,阳气极盛",
        "strategy": ["主动出击", "承担要职", "最大化输出"],
        "wrong_strategy": ["已处巅峰强求持续", "轻视复利"],
        "viewpoint_munger": "帝旺之后是衰,知道顶峰在哪就要布局下坡",
        "viewpoint_naval": "巅峰是相对概念,持续创新才能延续",
        "viewpoint_nietzsche": "永恒轮回,要能再活一次",
        "warning": "帝旺极盛,过刚易折,要配扶抑",
        "confidence": 65,
    },
    "墓(库)": {
        "definition": "入墓,收藏,五行转化阶段,主积蓄与沉淀",
        "strategy": ["囤积", "学习", "修身", "低调"],
        "viewpoint_laozi": "虚而不屈,动而愈出,库是潜能蓄势",
        "viewpoint_stoic": "区分能控制与不能控制的,库是控内的修炼",
        "warning": "墓库不开等于浪费,要找到冲开墓库的钥匙",
        "confidence": 60,
    },
    "绝": {
        "definition": "生气断绝,转折点,绝处逢生或彻底消亡",
        "strategy": ["守静", "内省", "重新定位"],
        "wrong_strategy": ["硬撑", "老路重走"],
        "viewpoint_nietzsche": "绝境是必经之路,杀不死你的让你更强",
        "viewpoint_stoic": "绝是命运,你的反应才定义你",
        "warning": "绝之后是胎,不要在绝处放弃",
        "confidence": 60,
    },
    "胎": {
        "definition": "受胎阶段,新一轮开始,胚芽已成形未现",
        "viewpoint_jung": "胎是新可能性的种子,阴阳交感的开始",
        "viewpoint_feynman": "胎 = 假设,还没被检验的可能性",
        "confidence": 60,
    },
    "养": {
        "definition": "成形阶段,胎之后长养,接近临官(出仕)",
        "strategy": ["学习", "打磨", "积累"],
        "viewpoint_munger": "养是复利前的积累期,长期主义者最看重",
        "viewpoint_kongzi": "君子务本,养是扎根",
        "confidence": 60,
    },
    # ========== 杂(2) ==========
    "纳音": {
        "definition": "60 甲子对应五行(海中金/炉中火等),古代合婚常用",
        "viewpoint_munger": "纳音是简化模型,粗看可以,细看要回到五行",
        "viewpoint_kahneman": "纳音是过度简化,信息流失大",
        "warning": "纳音只是粗分类,不能代替四柱八字分析",
        "confidence": 55,
    },
    "六亲": {
        "definition": "父母/兄弟/子嗣/夫妻,十神对应六亲关系,反映家庭伦理",
        "evidence_pattern": "正印=母,偏财=父,比肩=兄弟,正官=女,七杀=男",
        "viewpoint_kongzi": "孝悌也者,其为仁之本与,六亲是人伦之本",
        "viewpoint_munger": "六亲关系是文化模型的命理投射",
        "warning": "六亲是古代映射,现代家庭结构不同,不可机械套用",
        "confidence": 70,
    },
    # ========== 八字十神补全(4) ==========
    "正官": {
        "definition": "克我者异性,主规矩/名声/上司/约束力,女命代表丈夫",
        "evidence_pattern": "克日干之异性,如甲见辛",
        "strategy": ["守规矩", "求名声", "走正路"],
        "wrong_strategy": ["投机取巧", "对抗权威"],
        "viewpoint_kongzi": "正官是克己复礼,守规矩的人走得远",
        "viewpoint_munger": "正官是制度化思维,在规则内找到最大空间",
        "confidence": 80,
    },
    "食神": {
        "definition": "我生者同性,主才华/口福/子女(女命),温和的输出",
        "evidence_pattern": "日干所生同性,如甲见丙",
        "strategy": ["展示才华", "创作输出", "享受生活"],
        "wrong_strategy": ["压抑表达", "过度内敛"],
        "viewpoint_feynman": "食神是好奇心的外化,做你真正觉得有趣的事",
        "viewpoint_naval": "食神 = 专长的自然输出,不费力",
        "confidence": 75,
    },
    "伤官": {
        "definition": "我生者异性,主叛逆/才华/口才/创新,也主是非口舌",
        "evidence_pattern": "日干所生异性,如甲见丁",
        "strategy": ["创新", "技术深耕", "走非主流路线"],
        "wrong_strategy": ["服从", "走体制内"],
        "viewpoint_nietzsche": "伤官是超越善恶的创造力,规则是给庸人设的",
        "viewpoint_sunzi": "伤官者出奇,兵无常势水无常形",
        "counter_cases": ["004-bazi-shishen-failure-1"],
        "warning": "伤官见官为祸百端,要注意与正官的冲突",
        "confidence": 75,
    },
    "正财": {
        "definition": "我克者异性,主正当收入/妻子(男命)/务实,靠劳动得财",
        "evidence_pattern": "日干所克异性,如甲见己",
        "strategy": ["踏实赚钱", "稳定收入", "量入为出"],
        "wrong_strategy": ["投机", "一夜暴富心态"],
        "viewpoint_munger": "正财是复利思维,慢慢来比较快",
        "confidence": 75,
    },
    # ========== 六爻核心(5) ==========
    "世爻": {
        "definition": "六爻中代表求测者自己的爻位,卦的核心坐标",
        "viewpoint_munger": "世爻是你的能力圈,看它旺衰就知道你当下的状态",
        "confidence": 70,
    },
    "应爻": {
        "definition": "六爻中代表所问之人/事/对方的爻位",
        "viewpoint_sunzi": "知彼知己,应爻就是'彼'",
        "confidence": 70,
    },
    "动爻": {
        "definition": "老阳或老阴变化产生的爻,是卦中信息最活跃的点",
        "viewpoint_laozi": "动爻是命运的变数,静中有动才是关键",
        "confidence": 65,
    },
    "变卦": {
        "definition": "动爻变化后形成的新卦,代表事情的走向和结果",
        "viewpoint_feynman": "变卦是假设被检验后的修正,不是推翻",
        "confidence": 65,
    },
    "六爻用神": {
        "definition": "六爻中根据所问之事选取的关键爻,求财看妻财/求官看官鬼等",
        "viewpoint_munger": "用神选取是第一性原理,选错了全盘皆错",
        "confidence": 70,
    },
    # ========== 奇门核心(5) ==========
    "八门": {
        "definition": "奇门遁甲八门:休生伤杜景死惊开,代表人事吉凶",
        "strategy": ["开/休/生三吉门为用", "避死/惊/伤三凶门"],
        "viewpoint_sunzi": "八门是地形,知门者知进退",
        "confidence": 60,
    },
    "九星": {
        "definition": "奇门九星:蓬芮冲辅禽心柱任英,代表天时因素",
        "viewpoint_laozi": "九星是天运,人力有时尽天运不可违",
        "confidence": 55,
    },
    "三奇六仪": {
        "definition": "奇门遁甲的天干排列:乙丙丁三奇+戊己庚辛壬癸六仪",
        "confidence": 50,
    },
    "值符": {
        "definition": "奇门中统领一局的核心神,值符所在之宫最重要",
        "viewpoint_munger": "值符是这一局的'龙头',抓住它就抓住全局",
        "confidence": 55,
    },
    "奇门格局": {
        "definition": "奇门中天盘地盘天干组合形成的吉凶格局,如天遁/地遁/飞鸟跌穴等",
        "confidence": 50,
    },
    # ========== 大六壬核心(5) ==========
    "四课": {
        "definition": "大六壬由日干日支推导出的四层关系,是判断的基础",
        "viewpoint_munger": "四课是问题的四个切面,缺一个就看不全",
        "confidence": 55,
    },
    "三传": {
        "definition": "大六壬由四课推导出的初传/中传/末传,代表事情的发展过程",
        "viewpoint_sunzi": "三传是战局的推演,初传发用/中传转折/末传结局",
        "confidence": 55,
    },
    "十二天将": {
        "definition": "大六壬十二天将:贵人腾蛇朱雀六合勾陈青龙天空白虎太常玄武太阴天后",
        "confidence": 50,
    },
    "贵人(六壬)": {
        "definition": "六壬十二天将之首,贵人所在决定其他天将顺逆排列",
        "viewpoint_kongzi": "贵人是德行的外化,有德者必有邻",
        "confidence": 55,
    },
    "六壬类神": {
        "definition": "六壬断课时根据所问之事选取的关键天将/地支,如求财看财爻/求官看贵人",
        "confidence": 50,
    },
    # ========== 太乙核心(4) ==========
    "主客算": {
        "definition": "太乙神数中主方和客方的数理,通过太乙/天目/地目位置推算",
        "viewpoint_sunzi": "主客算就是兵力对比,知己知彼百战不殆",
        "confidence": 45,
    },
    "太乙落宫": {
        "definition": "太乙星在九宫中的位置,决定一局的核心格局",
        "confidence": 40,
    },
    "三基五福": {
        "definition": "太乙中三基(天基/地基/人基)和五福(寿/富/康宁/好德/善终)的评估体系",
        "confidence": 40,
    },
    "太乙阴阳遁": {
        "definition": "太乙冬至后用阳遁72局/夏至后用阴遁72局,共144局循环",
        "confidence": 40,
    },
    # ========== 占星核心(10) ==========
    "上升星座": {
        "definition": "出生时东方地平线升起的星座,代表外在形象和第一印象",
        "viewpoint_jung": "上升是人格面具,你给世界看到的样子",
        "confidence": 65,
    },
    "太阳星座": {
        "definition": "太阳所在的星座,代表核心自我和人生目标",
        "viewpoint_naval": "太阳星座是你的使命,做你该做的事",
        "confidence": 70,
    },
    "月亮星座": {
        "definition": "月亮所在的星座,代表内在情感和潜意识需求",
        "viewpoint_jung": "月亮是阴影面,了解它才能整合自我",
        "confidence": 65,
    },
    "水星逆行": {
        "definition": "占星中水星看起来倒退运行的时期,传统认为影响沟通/交通/电子设备",
        "viewpoint_kahneman": "水逆是确认偏误,你只记住了出问题的时候",
        "warning": "水逆更多是心理暗示,实际天文影响微乎其微",
        "confidence": 30,
    },
    "星盘相位": {
        "definition": "行星之间的角度关系:合相0°/对冲180°/三分120°/四分90°/六分60°",
        "confidence": 55,
    },
    "第七宫": {
        "definition": "占星中的伴侣宫,代表婚姻/合伙/公开的敌人",
        "viewpoint_munger": "第七宫是你的镜子,从对手身上看到自己",
        "confidence": 60,
    },
    "第十宫": {
        "definition": "占星中的事业宫(MC),代表社会地位/职业/公众形象",
        "viewpoint_naval": "第十宫是你的作品,世界通过它认识你",
        "confidence": 60,
    },
    "金星": {
        "definition": "占星中代表爱情/美感/价值/和谐的行星",
        "viewpoint_jung": "金星是阿尼玛/阿尼姆斯,你被什么吸引就暴露了你的潜意识",
        "confidence": 55,
    },
    "火星": {
        "definition": "占星中代表行动力/欲望/冲突/勇气的行星",
        "viewpoint_nietzsche": "火星是权力意志的驱动力,不行动就消亡",
        "confidence": 55,
    },
    "土星回归": {
        "definition": "约29.5年一次土星回到出生时的位置,传统认为是人生重大考验期",
        "viewpoint_munger": "土星回归是命运的压力测试,扛过去就升级",
        "warning": "土星回归不一定都是坏事,也可能是成熟的标志",
        "confidence": 50,
    },
    # ========== 紫微核心(6) ==========
    "紫微星": {
        "definition": "紫微斗数中最重要的主星,代表帝王/尊贵/领导力",
        "viewpoint_munger": "紫微是能力圈的核心,你天生擅长什么",
        "confidence": 65,
    },
    "四化": {
        "definition": "紫微斗数中化禄/化权/化科/化忌四种变化,代表运势的加减分",
        "viewpoint_laozi": "四化是福祸相依,化禄未必全吉/化忌未必全凶",
        "confidence": 60,
    },
    "命宫": {
        "definition": "紫微斗数中最重要的宫位,代表先天性格和命运基调",
        "viewpoint_jung": "命宫是人格原型,你的出厂设置",
        "confidence": 65,
    },
    "大限(紫微)": {
        "definition": "紫微斗数中每十年一个大限,代表人生不同阶段的运势",
        "viewpoint_munger": "大限是人生的十年周期,顺势而为",
        "confidence": 55,
    },
    "天机星": {
        "definition": "紫微斗数主星,代表智慧/谋略/变化,兄弟主",
        "viewpoint_feynman": "天机星是第一性原理思维,拆解问题的能力",
        "confidence": 55,
    },
    "七杀星": {
        "definition": "紫微斗数主星,代表冲劲/开创/冒险,将军星",
        "viewpoint_nietzsche": "七杀是权力意志,不破不立",
        "confidence": 55,
    },
    # ========== 姓名学核心(3) ==========
    "五格": {
        "definition": "姓名学五格:天格/人格/地格/外格/总格,通过笔画数计算吉凶",
        "viewpoint_munger": "五格是简化模型,参考可以但别迷信",
        "confidence": 45,
    },
    "三才配置": {
        "definition": "姓名学中天格/人格/地格的五行组合,代表天时地利人和",
        "confidence": 40,
    },
    "81数理": {
        "definition": "姓名学中1-81的数理吉凶,总格笔画数对应不同含义",
        "warning": "81数理是现代姓名学体系,古代无此说法",
        "confidence": 35,
    },
    # ========== 通用概念(3) ==========
    "五行缺水": {
        "definition": "八字中水元素不足,可能影响肾/膀胱/血液/智慧",
        "strategy": ["多接触水", "北方发展", "黑色/蓝色"],
        "viewpoint_munger": "五行缺失是提醒,不是判决",
        "confidence": 60,
    },
    "冲": {
        "definition": "地支六冲:子午/丑未/寅申/卯酉/辰戌/巳亥,代表冲突/变动/分离",
        "strategy": ["主动求变", "以动制冲", "搬家/换工作/旅行"],
        "viewpoint_laozi": "冲不是坏事,冲是命运在掀桌子逼你换活法",
        "confidence": 70,
    },
    "合": {
        "definition": "地支六合/三合,代表合作/吸引/稳定/化解",
        "strategy": ["合作", "借力", "顺势而为"],
        "viewpoint_sunzi": "合是联盟,合则强分则弱",
        "confidence": 70,
    },
}


# ============== 视角人物解读库 ==============
# 每个视角对常见概念的简短解读,1-2 句话

VIEWPOINT_KB = {
    "munger": {
        "title": "查理·芒格",
        "domain": "投资哲学",
        "core_stance": "逆向思维 + 多元模型",
        "wisdom": [
            "反过来想,总是反过来想",
            "在能力圈内做事",
            "避免蠢事比追求聪明更重要",
            "知识不是力量,知识是潜在力量,只有把它用出来才是",
        ],
    },
    "naval": {
        "title": "Naval Ravikant",
        "domain": "硅谷哲学",
        "core_stance": "专长 + 杠杆 + 长期主义",
        "wisdom": [
            "专长是你无法被培训出来的能力",
            "三种杠杆:资本/代码/媒体",
            "短期博弈是负和游戏",
            "判断力比埋头苦干重要",
        ],
    },
    "taleb": {
        "title": "纳西姆·塔勒布",
        "domain": "反脆弱",
        "core_stance": "不对称风险 + 杠铃策略",
        "wisdom": [
            "反脆弱:从波动中获益",
            "皮肤在摩擦中变厚,不是玻璃球",
            "黑天鹅无法预测,要为它留余地",
            "如果一件事失败了你就完了,它就不是好策略",
        ],
    },
    "feynman": {
        "title": "理查德·费曼",
        "domain": "物理学",
        "core_stance": "第一性原理 + 简单到能讲给孩子",
        "wisdom": [
            "我不能创造的,就是我不懂的",
            "第一性原理:从最基本事实出发",
            "科学诚实:我可能错了",
            "做事的乐趣胜过做事的成果",
        ],
    },
    "kahneman": {
        "title": "丹尼尔·卡尼曼",
        "domain": "行为经济学",
        "core_stance": "认知偏误 + 系统1/系统2",
        "wisdom": [
            "损失厌恶:失去 100 的痛苦 > 得到 100 的快乐",
            "锚定效应:第一印象支配后续判断",
            "可得性偏误:容易想到的事被认为更可能",
            "巴纳姆效应:模糊描述让人觉得准",
        ],
    },
    "sunzi": {
        "title": "孙子",
        "domain": "兵法",
        "core_stance": "知己知彼,不战而屈人之兵",
        "wisdom": [
            "上兵伐谋,其次伐交,其次伐兵",
            "善战者,先为不可胜",
            "知彼知己,百战不殆",
            "兵无常势,水无常形",
        ],
    },
    "laozi": {
        "title": "老子",
        "domain": "道家",
        "core_stance": "无为而治 + 道法自然",
        "wisdom": [
            "无为而无不为",
            "反者道之动,弱者道之用",
            "上善若水,水善利万物而不争",
            "知人者智,自知者明",
        ],
    },
    "zhuangzi": {
        "title": "庄子",
        "domain": "道家",
        "core_stance": "逍遥 + 齐物",
        "wisdom": [
            "逍遥游:无所待而游于无穷",
            "齐物论:万物一齐,是非难辨",
            "吾生也有涯,而知也无涯",
            "子非鱼,焉知鱼之乐",
        ],
    },
    "kongzi": {
        "title": "孔子",
        "domain": "儒家",
        "core_stance": "中庸 + 仁义",
        "wisdom": [
            "中庸之为德也,其至矣哉",
            "己所不欲,勿施于人",
            "学而不思则罔,思而不学则殆",
            "知之为知之,不知为不知",
        ],
    },
    "jung": {
        "title": "卡尔·荣格",
        "domain": "分析心理学",
        "core_stance": "集体无意识 + 原型 + 个体化",
        "wisdom": [
            "你所讨厌的人,是你自己阴影的一部分",
            "个体化进程:整合人格分裂面",
            "同步性:有意义的巧合",
            "中年危机的本质是自我整合",
        ],
    },
    "socrates": {
        "title": "苏格拉底",
        "domain": "哲学",
        "core_stance": "知道自己不知道 + 产婆术",
        "wisdom": [
            "未经省察的人生不值得过",
            "我唯一知道的,就是我什么都不知道",
            "智慧始于承认无知",
            "提问比答案更重要",
        ],
    },
    "nietzsche": {
        "title": "弗里德里希·尼采",
        "domain": "哲学",
        "core_stance": "超人 + 权力意志 + 永恒轮回",
        "wisdom": [
            "那些杀不死我的,使我更强大",
            "上帝已死,价值重估",
            "知道自己为什么而活的人,能忍受任何怎样的活",
            "成为你自己",
        ],
    },
    "hanfeizi": {
        "title": "韩非子",
        "domain": "法家",
        "core_stance": "制度 + 势 + 法",
        "wisdom": [
            "法不阿贵,绳不挠曲",
            "抱法处势则治,背法去势则乱",
            "事以密成,语以泄败",
        ],
    },
    "mason": {  # 麦克斯韦/穆勒 - 凑数,实际无
        "title": "N/A",
        "wisdom": [],
    },
    "i_ching": {
        "title": "周易",
        "domain": "易经",
        "core_stance": "变易 + 简易 + 不易",
        "wisdom": [
            "穷则变,变则通,通则久",
            "一阴一阳之谓道",
            "君子见几而作,不俟终日",
        ],
    },
    "dante": {
        "title": "但丁",
        "domain": "神学诗学",
        "core_stance": "地狱-炼狱-天堂三境",
        "wisdom": [
            "走自己的路,让别人说去",
            "地狱里最热的地方,是为有德者保留的",
        ],
    },
    "stoic": {
        "title": "斯多葛",
        "domain": "古希腊罗马哲学",
        "core_stance": "控制二分法 + 接受命运",
        "wisdom": [
            "区分你能控制的和不能控制的",
            "接受命运的安排,专注于反应",
            "障碍是机会的另一面",
        ],
    },
    "sagan": {
        "title": "卡尔·萨根",
        "domain": "宇宙学",
        "core_stance": "宇宙公民 + 科学谦卑",
        "wisdom": [
            "我们都是星尘",
            "非凡的主张需要非凡的证据",
            "在某个地方,某些难以置信的事情在等着被我们知道",
        ],
    },
    "einstein": {
        "title": "爱因斯坦",
        "domain": "物理学",
        "core_stance": "相对论 + 想象力",
        "wisdom": [
            "想象力比知识更重要",
            "我没有特殊的才能,只有强烈的好奇心",
            "疯狂:用同样的方式做事,期待不同的结果",
        ],
    },
}


# ============== 工具函数 ==============

def _keyword_match(text: str, concepts: List[str]) -> List[str]:
    """关键词匹配"""
    hits = []
    text_lower = text.lower()
    for concept in concepts:
        if concept in text or concept.lower() in text_lower:
            hits.append(concept)
    return hits


def _extract_evidence_from_chart(chart_result: Dict) -> Dict[str, Any]:
    """从 chart_result 提取客户命盘证据"""
    bazi = chart_result.get("bazi", {})
    return {
        "day_master": bazi.get("day_master"),
        "strength": bazi.get("strength"),
        "xi_yong": (bazi.get("xi_yong") or {}).get("xi", []),
        "ji_shen": (bazi.get("xi_yong") or {}).get("ji", []),
        "geju": (bazi.get("geju") or {}).get("geju_type"),
        "shensha_count": len(bazi.get("shensha", []) or []),
        "current_dayun": next((d for d in bazi.get("dayun", []) if d.get("is_current")), {}),
        "liunian": bazi.get("liunian", {}),
        "pillars": {
            "year": bazi.get("year"),
            "month": bazi.get("month"),
            "day": bazi.get("day"),
            "time": bazi.get("time"),
        },
    }


def _load_counter_cases_for_topic(topic: str) -> List[str]:
    """加载反向案例"""
    if not COUNTER_DIR.exists():
        return []
    matches = []
    topic_kw = {
        "健康": ["health", "健"],
        "事业": ["career", "事业", "shangguan"],
        "财运": ["wealth", "money", "rich", "fortune", "财"],
        "学业": ["study", "学业"],
        "感情": ["spouse", "感情", "emotion"],
        "性格": ["shishen", "gender", "yangren", "shayin"],
    }
    keywords = topic_kw.get(topic, [])
    for f in COUNTER_DIR.glob("*.md"):
        name = f.stem.lower()
        if any(kw in name for kw in keywords):
            title_m = re.search(r"^#\s+(.+)$", f.read_text(encoding="utf-8"), re.MULTILINE)
            title = title_m.group(1) if title_m else f.stem
            matches.append(f"{f.stem}: {title[:80]}")
    return matches[:5]


def _build_viewpoint_response(concept: str, viewpoint_id: str) -> Optional[str]:
    """从概念知识库拿某视角的解读"""
    concept_data = CONCEPT_KB.get(concept, {})
    viewpoint_key = f"viewpoint_{viewpoint_id}"
    return concept_data.get(viewpoint_key)


def _resolve_viewpoints(figures: Optional[str]) -> List[str]:
    """把 figures 字符串切成 list,默认返回综合视角"""
    if not figures:
        return []  # 空 = 用默认综合
    # figures 可能是 "munger,naval" 或 "munger naval"
    raw = re.split(r"[,\s]+", figures.strip())
    return [f.lower() for f in raw if f]


def _match_concepts(question: str) -> List[str]:
    """从问题里匹配玄学概念"""
    matches = []
    q_lower = question.lower()
    for concept in CONCEPT_KB.keys():
        if concept in question or concept.lower() in q_lower:
            matches.append(concept)
    # 同义词 / 变体
    syn = {
        "身弱": ["我身弱", "身弱", "弱命"],
        "身强": ["身强", "我身强"],
        "食神制杀": ["食神制杀"],
        "财格": ["财格"],
        "七杀": ["七杀", "杀星"],
        "桃花": ["桃花", "异性缘"],
        "真太阳时": ["真太阳时", "太阳时"],
        "时辰": ["时辰", "时柱"],
        "流年": ["流年", "今年"],
        "大运": ["大运"],
        "格局": ["格局"],
        "用神": ["用神"],
        "喜用神": ["喜用神", "喜神"],
        "忌神": ["忌神"],
        "华盖": ["华盖"],
        "驿马": ["驿马"],
        "羊刃": ["羊刃"],
        "国印贵人": ["国印"],
        "十恶大败": ["十恶"],
        "紫微": ["紫微"],
        "占星": ["占星"],
        "六壬": ["六壬"],
        "奇门": ["奇门"],
        "太乙": ["太乙"],
        "六爻": ["六爻"],
        "姓名学": ["姓名", "起名"],
        "玄学": ["玄学", "命理", "占卜"],
        "大运换运": ["换运", "大运交接"],
        "流月": ["流月", "本月", "这个月"],
        # 7-27 扩充:21 个新概念(神煞 8 + 十神 5 + 长生 6 + 杂 2)
        "长生": ["长生", "长生位"],
        "帝旺": ["帝旺"],
        "墓(库)": ["墓", "墓库", "入墓", "库"],
        "绝": ["绝"],
        "胎": ["胎"],
        "养": ["养"],
        "纳音": ["纳音"],
        "六亲": ["六亲", "六亲关系"],
        "天乙贵人": ["天乙", "天乙贵人"],
        "文昌贵人": ["文昌", "文昌贵人"],
        "太极贵人": ["太极", "太极贵人"],
        "天德贵人": ["天德", "天德贵人"],
        "月德贵人": ["月德", "月德贵人"],
        "将星": ["将星"],
        "亡神": ["亡神"],
        "劫煞": ["劫煞"],
        "枭神(偏印)": ["枭神", "偏印", "枭神夺食"],
        "倒食": ["倒食", "偏印夺食"],
        "比肩": ["比肩"],
        "劫财": ["劫财"],
        "正印": ["正印"],
    }
    for concept, variants in syn.items():
        for v in variants:
            if v in question and concept not in matches:
                matches.append(concept)
                break
    return matches


# ============== 主入口 ==============

def ask(
    question: str,
    chart_result: Optional[Dict[str, Any]] = None,
    figures: Optional[str] = None,
) -> Dict[str, Any]:
    """
    主入口:客户/梧提问,玄照 AI 回答

    Args:
        question: 客户问题(中文)
        chart_result: 客户 chart 数据(可选 — 客户提问时传,知识问答时不传)
        figures: 视角人物 ids,逗号分隔(可选 — 不传 = 综合 108 视角)

    Returns:
        {
          "question": 原始问题,
          "answer_mode": "client" | "knowledge",
          "concepts_matched": ["身弱", "财格"],
          "answer_blocks": [
            {"type": "definition", "text": "..."},
            {"type": "evidence", "text": "...", "source": "客户命盘" 或 "知识库"},
            {"type": "counter", "text": "...", "cases": [...]},
            {"type": "viewpoint", "figure": "munger", "text": "..."},
            {"type": "warning", "text": "..."}
          ],
          "viewpoints_used": ["munger", "naval"],
          "disclosure": [...],
          "confidence": 0-100
        }
    """
    # 1. 判断模式
    has_chart = bool(chart_result)
    answer_mode = "client" if has_chart else "knowledge"

    # 2. 匹配玄学概念
    concepts = _match_concepts(question)

    # 3. 解析视角
    viewpoints = _resolve_viewpoints(figures)

    # 4. 构建回答块
    answer_blocks = []

    # 4.1 定义块(每个匹配的概念)
    for concept in concepts:
        c_data = CONCEPT_KB.get(concept, {})
        if c_data.get("definition"):
            answer_blocks.append({
                "type": "definition",
                "concept": concept,
                "text": c_data["definition"],
            })
        if c_data.get("strategy"):
            answer_blocks.append({
                "type": "strategy",
                "concept": concept,
                "text": "策略: " + "、".join(c_data["strategy"]),
            })
        if c_data.get("warning"):
            answer_blocks.append({
                "type": "warning",
                "concept": concept,
                "text": c_data["warning"],
            })

    # 4.2 客户命盘证据块
    if has_chart and chart_result:
        evidence = _extract_evidence_from_chart(chart_result)
        answer_blocks.append({
            "type": "evidence",
            "source": "客户命盘",
            "text": (
                f"基于你给的出生信息,你四柱 {evidence['pillars']['year']} {evidence['pillars']['month']} "
                f"{evidence['pillars']['day']} {evidence['pillars']['time']},日主 {evidence['day_master']},"
                f"{evidence['strength']},喜用神 {evidence['xi_yong']},忌神 {evidence['ji_shen']}。"
                + (f"当前走 {evidence['current_dayun'].get('ganzhi','')} 大运。" if evidence['current_dayun'] else "")
                + (f"流年(2026)是 {evidence['liunian'].get('ganzhi','')}。" if evidence['liunian'] else "")
            ),
        })

    # 4.3 视角块
    if not viewpoints:
        # 默认:用玄学 + 现代综合视角
        default_views = ["munger", "laozi", "sunzi", "kahneman", "jung"]
        viewpoints = default_views

    for vp in viewpoints:
        vp_data = VIEWPOINT_KB.get(vp, {})
        if not vp_data:
            continue
        # 该视角对每个匹配概念的解读
        for concept in concepts:
            insight = _build_viewpoint_response(concept, vp)
            if insight:
                answer_blocks.append({
                    "type": "viewpoint",
                    "concept": concept,
                    "figure": vp,
                    "figure_title": vp_data.get("title", vp),
                    "text": insight,
                })
        # 该视角的核心立场(如果没有匹配概念)
        if not concepts and vp_data.get("wisdom"):
            answer_blocks.append({
                "type": "viewpoint",
                "figure": vp,
                "figure_title": vp_data.get("title", vp),
                "text": vp_data.get("core_stance", ""),
            })
            # 加 1-2 个 wisdom 引用
            for w in vp_data["wisdom"][:2]:
                answer_blocks.append({
                    "type": "wisdom",
                    "figure": vp,
                    "text": w,
                })

    # 4.4 反向案例块
    topics_for_counter = []
    if "身弱" in concepts or "身强" in concepts:
        topics_for_counter.append("性格")
    if "七杀" in concepts or "食神制杀" in concepts or "伤官见官" in concepts or "格局" in concepts:
        topics_for_counter.append("事业")
    if "财格" in concepts or "喜用神" in concepts or "忌神" in concepts:
        topics_for_counter.append("财运")
    if "桃花" in concepts:
        topics_for_counter.append("感情")
    if "驿马" in concepts:
        topics_for_counter.append("事业")

    for topic in set(topics_for_counter):
        cases = _load_counter_cases_for_topic(topic)
        if cases:
            answer_blocks.append({
                "type": "counter",
                "topic": topic,
                "text": f"反向案例({topic}):以下命盘出现相反情况,说明这判断不能绝对化",
                "cases": cases,
            })

    # 4.5 通用 warning 块
    q_lower = question.lower()
    if any(w in q_lower or w in question for w in ["财富", "钱", "赚", "资产", "a 级", "a级", "亿万", "千万", "几级", "多少", "多少级"]):
        answer_blocks.append({
            "type": "warning",
            "text": "⚠️ 命理无法预测具体财富数字 — 只识别趋势。能到几级取决于行业 / 努力 / 时机,不是命里写死的。",
        })

    # 5. 置信度
    if concepts:
        confs = [CONCEPT_KB[c].get("confidence", 50) for c in concepts if c in CONCEPT_KB]
        confidence = int(sum(confs) / len(confs)) if confs else 50
    else:
        confidence = 40  # 没匹配到概念,低信心

    # 6. 披露
    disclosure = [
        "回答基于玄照规则引擎(8 术法 + 反向案例 + 108 视角),非 LLM 生成",
        "具体数字(财富/职业/资产)无法预测,只给方向性建议",
        "客户提问时叠加命盘背景,知识问答时只用通用规则",
        "反向案例已自动列出 — 任何判断都有反例",
    ]

    return {
        "question": question,
        "answer_mode": answer_mode,
        "concepts_matched": concepts,
        "answer_blocks": answer_blocks,
        "viewpoints_used": viewpoints,
        "disclosure": disclosure,
        "confidence": confidence,
    }