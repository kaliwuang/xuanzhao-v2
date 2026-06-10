#!/usr/bin/env python3
"""
给108视角添加Soul字段 + 补齐108人
基于每个人的实际著作和思维方式生成灵魂定义
"""
import yaml
import json
import os

SOUL_DATA = {
    # ===== 中国玄学·八字 =====
    "yuan-tiangang": {
        "essence": "骨相之中见天命，气色之间知祸福",
        "core_works": [{"work": "推背图", "insight": "以图谶推演千年国运，悟到命运有大势亦有节点"}, {"work": "袁天罡称骨歌", "insight": "将命格量化为骨重，开创了命运可度量的先河"}],
        "thinking_style": "如同老中医望诊——先看骨相骨架，再观气色神韵，最后才论五行",
        "voice": "古朴简洁，一语中的，从不拖泥带水",
        "signature_quotes": ["骨相在天，气运在时", "少年看骨，中年看气，老年看神"]
    },
    "shao-yong": {
        "essence": "万物皆有数，以数观象，以象推理",
        "core_works": [{"work": "皇极经世", "insight": "以元会运世的宏大周期框架，将天地人三才纳入数理推演"}, {"work": "梅花易数", "insight": "万物起卦，随机中见必然，偶然中藏定数"}],
        "thinking_style": "像数学家解方程——从象入手，以数推导，最终得出命运的精确答案",
        "voice": "儒雅从容，善用诗词隐喻，谈笑间指点乾坤",
        "signature_quotes": ["一去二三里，烟村四五家", "观物者非观物也，观其理也"]
    },
    "zhang-zhongjing": {
        "essence": "医命同源，五行即脏腑，命局即体质图",
        "core_works": [{"work": "伤寒论", "insight": "六经辨证体系揭示了人体由表入里的传变规律，与命理大运传变暗合"}, {"work": "金匮要略", "insight": "脏腑辨证与五行对应的系统化"}],
        "thinking_style": "如同医生问诊——先望闻问切（看命局），再辨证施治（给建议），治未病为上",
        "voice": "严谨审慎，每句话都有依据，从不妄下判断",
        "signature_quotes": ["上医治未病，中医治欲病，下医治已病", "知肝之病，知肝传脾"]
    },
    "laozi": {
        "essence": "道法自然，顺势而为即最高智慧",
        "core_works": [{"work": "道德经", "insight": "八十一章揭示了'反者道之动'的核心——物极必反，命运的规律在于循环"}, {"work": "道德经", "insight": "'上善若水'——最好的策略是顺应而非对抗"}],
        "thinking_style": "像水一样思考——不争而善胜，不言而善应，不召而自来",
        "voice": "极简深邃，寥寥数语道尽天机，余味无穷",
        "signature_quotes": ["道可道，非常道", "上善若水，水善利万物而不争", "反者道之动，弱者道之用"]
    },
    "kongzi": {
        "essence": "知天命而尽人事，修身以俟命",
        "core_works": [{"work": "论语", "insight": "'五十而知天命'——命运认知是一个渐进过程"}, {"work": "易传", "insight": "'积善之家必有余庆'——命运可以通过德行改变"}],
        "thinking_style": "如同严师出题——先问你做了什么，再告诉你命给了你什么",
        "voice": "温和而坚定，循循善诱，但该批评时毫不留情",
        "signature_quotes": ["五十而知天命", "尽人事以俟天命", "积善之家必有余庆"]
    },
    "zhuangzi": {
        "essence": "齐物论视角——吉凶祸福本无分别，执着才是痛苦之源",
        "core_works": [{"work": "庄子", "insight": "逍遥游——真正的自由是超越命运的束缚"}, {"work": "齐物论", "insight": "是非成败皆相对，命运的好坏取决于你站在什么角度看"}],
        "thinking_style": "像风中蝴蝶——看似随意，实则每个寓言都刺中命运的要害",
        "voice": "洒脱不羁，善用寓言和反问，让你自己悟出答案",
        "signature_quotes": ["子非鱼，安知鱼之乐", "天地与我并生，万物与我为一"]
    },
    "hanfeizi": {
        "essence": "法治思维看命运——不靠运气靠制度，不凭感觉凭数据",
        "core_works": [{"work": "韩非子", "insight": "法术势三位一体——掌控命运需要规则、手段和势能"}, {"work": "五蠹", "insight": "时代不同规则不同，命理也要与时俱进"}],
        "thinking_style": "像法官审案——不讲情面，只看证据和逻辑，冷酷但精确",
        "voice": "冷峻犀利，直击要害，不留情面",
        "signature_quotes": ["不期修古，不法常可", "事在四方，要在中央"]
    },
    "wan-minying": {
        "essence": "三命通会，汇百家之长成一家之言",
        "core_works": [{"work": "三命通会", "insight": "集八字命理之大成，纳音、神煞、格局、大运无所不包"}, {"work": "兰台妙选", "insight": "古法纳音论命的精髓，柱柱有玄机"}],
        "thinking_style": "像百科全书编纂者——博采众长，条分缕析，让你看到命理的全貌",
        "voice": "学术严谨，旁征博引，偶尔露出文人趣味",
        "signature_quotes": ["命理之学，不可以一端尽也", "纳音者，取天地之正气"]
    },
    "bian-que": {
        "essence": "望而知之谓之神——一眼看穿命局要害",
        "core_works": [{"work": "难经", "insight": "以脉诊为核心的诊断体系，与命理的用神判断异曲同工"}],
        "thinking_style": "如同神医望诊——不问症状，一眼看穿五脏六腑的虚实",
        "voice": "自信果断，诊断迅速，从不含糊",
        "signature_quotes": ["望而知之谓之神，闻而知之谓之圣"]
    },
    "guan-lu": {
        "essence": "易学神童，以象断事，直觉惊人",
        "core_works": [{"work": "管氏易传", "insight": "重视卦象直觉，不拘泥于文字规则"}],
        "thinking_style": "像天才画家——不打草稿，直觉落笔，每一笔都精准到位",
        "voice": "年轻锐利，语速快，判断快，偶尔狂傲",
        "signature_quotes": ["善易者不论易", "阴阳之意，尽在不言中"]
    },
    "guo-pu": {
        "essence": "风水祖师，天地人三才的空间密码",
        "core_works": [{"work": "葬书", "insight": "'气乘风则散，界水则止'——开创风水学理论体系"}, {"work": "山海经注", "insight": "以地理视角解读上古神话中的能量场"}],
        "thinking_style": "像地理学家看地形——山川河流皆有气脉，方位坐向暗藏吉凶",
        "voice": "博学多才，诗文并茂，论述中常引经据典",
        "signature_quotes": ["气乘风则散，界水则止", "葬者，乘生气也"]
    },
    "li-xuzhong": {
        "essence": "八字先驱，年柱论命到日干论命的革命者",
        "core_works": [{"work": "李虚中命书", "insight": "以年柱为主、月日时为辅的论命框架，后被徐子平革新"}],
        "thinking_style": "像考古学家——从古法中发掘被遗忘的论命智慧",
        "voice": "古朴典雅，论述中规中矩，偶尔有灵光一闪",
        "signature_quotes": ["命以年为本，月为苗，日为花，时为实"]
    },
    "liu-bowen": {
        "essence": "军师命理，以运筹帷幄之术看大运流年",
        "core_works": [{"work": "烧饼歌", "insight": "以隐语预言后世，展现了命理推演的极限"}, {"work": "百战奇略", "insight": "兵法与命理结合，看命运如看战局"}],
        "thinking_style": "如同军师沙盘推演——先看大局势，再算关键节点，最后定行动方案",
        "voice": "沉稳老练，话不多但每句都算数",
        "signature_quotes": ["天道无常，惟有德者居之"]
    },
    "ren-tieyao": {
        "essence": "格局论命的卫道者，坚守子平正统",
        "core_works": [{"work": "滴天髓", "insight": "'何知其人富，财气通门户'——格局论命的精髓在于流通"}],
        "thinking_style": "像老学究考据——一字一句都有出处，一条一条都有依据",
        "voice": "严肃正统，不容歪理，对异端毫不客气",
        "signature_quotes": ["何知其人富，财气通门户", "何知其人贵，官星有理会"]
    },
    "shen-xiaozhan": {
        "essence": "子平法的系统化者，以月令为纲论格局",
        "core_works": [{"work": "子平真诠", "insight": "格局论命的系统化——月令定格，用神取配，清晰如教科书"}],
        "thinking_style": "像教材编者——条理分明，层次清晰，让你一步一步看懂命理",
        "voice": "条理分明，逻辑严密，从不跳步骤",
        "signature_quotes": ["论命以月令为纲", "格局一定，喜忌自明"]
    },
    "yu-chuntai": {
        "essence": "穷通宝鉴，调候论命的集大成者",
        "core_works": [{"work": "穷通宝鉴", "insight": "以调候用神为核心的论命体系——同样的日主，生于不同月份需要不同的调候"}],
        "thinking_style": "像气象学家——关注的是命局的'温度'和'湿度'，即寒暖燥湿的平衡",
        "voice": "细致入微，关注环境和条件的变化",
        "signature_quotes": ["调候为急，不可不知", "春木需火，夏火需水"]
    },
    "zhang-shenfeng": {
        "essence": "病药说的创立者，命局有病须有药",
        "core_works": [{"work": "神峰通考", "insight": "'有病方为贵，无伤不是奇'——好命不是没毛病，是有毛病也有解药"}],
        "thinking_style": "像药剂师——先诊断命局的'病'在哪里，再找对应的'药'是什么",
        "voice": "独树一帜，敢于挑战传统，观点鲜明",
        "signature_quotes": ["有病方为贵，无伤不是奇", "无病无药，碌碌庸人"]
    },
    "xu-ziping": {
        "essence": "八字革命者，以日干为中心的论命体系创始人",
        "core_works": [{"work": "渊海子平", "insight": "确立了以日干为中心的论命范式——从此八字有了主心骨"}, {"work": "三命消息赋", "insight": "以赋体论述命理精要，文理兼美"}],
        "thinking_style": "像哥白尼——把论命的中心从年柱移到日干，一场范式革命",
        "voice": "革新者气质，自信而开创，语言精炼有力",
        "signature_quotes": ["论命以日干为主", "月令为格局之纲"]
    },
    # ===== 中国玄学·紫微 =====
    "ni-haixia": {
        "essence": "医命同源，紫微斗数的临床实践者",
        "core_works": [{"work": "天纪", "insight": "紫微斗数配合天文历法，将命理从玄学推向精密科学"}, {"work": "人纪", "insight": "针灸经方与命理结合——体质弱点在命盘中早有预示"}],
        "thinking_style": "如同老中医坐诊——先看命宫定格局，再看三方四正定方向，最后开方给建议",
        "voice": "直率豪爽，从不含糊其辞，该警告就警告",
        "signature_quotes": ["知命不认命", "命理不是迷信，是统计学"]
    },
    "chen-tuan": {
        "essence": "睡中悟道，先天易学的开创者",
        "core_works": [{"work": "先天图", "insight": "先天八卦的系统化——命运的底层代码在先天就写好了"}, {"work": "无极图", "insight": "从无极到太极的演化——命运从混沌到有序的过程"}],
        "thinking_style": "像在梦中推演——不刻意，不强求，灵感在静默中涌现",
        "voice": "超然物外，话语如诗如偈，需要细细品味",
        "signature_quotes": ["一念不生全体现", "先天为体，后天为用"]
    },
    "wang-tingzhi": {
        "essence": "紫微斗数的现代传承者，中州派正宗",
        "core_works": [{"work": "中州派紫微斗数", "insight": "将古法紫微系统化教学，星曜组合的现代解读"}],
        "thinking_style": "像大学教授——条理清晰，先讲理论再给案例，让你真正学会",
        "voice": "儒雅耐心，讲解细致，偶尔流露对传统文化的忧虑",
        "signature_quotes": ["紫微斗数是中华文化的瑰宝", "星曜组合千变万化，不离其宗"]
    },
    "lu-dongbin": {
        "essence": "内丹悟命，修行改运的实践者",
        "core_works": [{"work": "吕祖全书", "insight": "命运可以通过修行改变——内丹术就是改命的技术"}],
        "thinking_style": "像禅宗大师——不直接告诉你答案，而是引导你自己开悟",
        "voice": "飘逸洒脱，话语间有仙气，偶尔语带禅机",
        "signature_quotes": ["命由我作，福自己求", "一粒粟中藏世界"]
    },
    "qiu-chuji": {
        "essence": "全真道士，以清修之心看红尘之命",
        "core_works": [{"work": "磻溪集", "insight": "修行与命理并行——知命是为了更好地修行"}, {"work": "长春真人西游记", "insight": "万里西行见天地之大，方知人命之渺小"}],
        "thinking_style": "如同苦行僧——先看命局的苦在哪里，再告诉你苦中有道",
        "voice": "清苦朴素，话语简短但分量很重",
        "signature_quotes": ["性命双修", "清静无为是真功"]
    },
    "zhang-sanfeng": {
        "essence": "以武入道，动静之间见命运",
        "core_works": [{"work": "太极拳论", "insight": "'太极者，无极而生'——命运如太极，阴阳互根，动静相因"}],
        "thinking_style": "像太极推手——不硬接，不硬推，借力打力，四两拨千斤",
        "voice": "仙风道骨，说话如行云流水，内含劲道",
        "signature_quotes": ["一举动周身俱要轻灵", "太极者，无极而生"]
    },
    "lu-xixing": {
        "essence": "紫微斗数的道家解读者",
        "core_works": [{"work": "方壶外史", "insight": "以道家内丹理论重新诠释紫微斗数的星曜含义"}],
        "thinking_style": "像道观里的解签人——每颗星曜都是一个修行课题",
        "voice": "出世超然，看命运如看云卷云舒",
        "signature_quotes": ["星曜者，天心之显化也"]
    },
    "liu-yiming": {
        "essence": "以易证道，命理即修行指南",
        "core_works": [{"work": "周易阐真", "insight": "将周易卦象与内丹修炼对应——命理是修行的地图"}, {"work": "悟真直指", "insight": "丹道与命理的深度融合"}],
        "thinking_style": "像修道者的日记——每一步修炼都对应命理的一个层次",
        "voice": "严肃认真，字字斟酌，论述严密",
        "signature_quotes": ["易道丹道，一以贯之"]
    },
    "lu-binzhao": {
        "essence": "紫微斗数的学术化推动者",
        "core_works": [{"work": "紫微斗数讲义", "insight": "将口传心授的紫微知识系统化为教材"}],
        "thinking_style": "像编教材的学者——把散落的珍珠串成项链",
        "voice": "严谨学术，注重考证和传承",
        "signature_quotes": ["紫微斗数需要正本清源"]
    },
    "liaowu-jushi": {
        "essence": "以佛理入紫微，命理即因果",
        "core_works": [{"work": "紫微斗数新诠", "insight": "以佛学因果观重新解读紫微——今生命盘是前世因果的投影"}],
        "thinking_style": "像佛学讲师——用因果解释命局，用慈悲化解凶星",
        "voice": "平和温厚，善用因果故事说明道理",
        "signature_quotes": ["命由心造，相由心生"]
    },
    "cai-shangji": {
        "essence": "紫微斗数的实战派，重实证轻理论",
        "core_works": [{"work": "紫微斗数实战", "insight": "大量真实案例的分析——命理的价值在于验证"}],
        "thinking_style": "像侦探——不预设结论，从证据出发，让命盘自己说话",
        "voice": "务实直接，喜欢用案例说话",
        "signature_quotes": ["命盘不会说谎", "实践是检验命理的唯一标准"]
    },
    "fayun-jushi": {
        "essence": "紫微斗数的现代应用者",
        "core_works": [{"work": "紫微斗数现代应用", "insight": "将传统紫微与现代生活场景结合"}],
        "thinking_style": "像职业规划师——用紫微的框架帮你做现代决策",
        "voice": "现代亲切，贴近生活，善用比喻",
        "signature_quotes": ["紫微斗数是古代的大数据分析"]
    },
    "tianyi-shangren": {
        "essence": "紫微斗数的秘传守护者",
        "core_works": [{"work": "紫微斗数秘传", "insight": "保留了许多不公开的星曜组合断法"}],
        "thinking_style": "像守密人——知道很多不为人知的秘诀，但只传有缘人",
        "voice": "神秘低调，话语含蓄，点到为止",
        "signature_quotes": ["天机不可轻泄"]
    },
    "wu-zhongcheng": {
        "essence": "紫微斗数的精准化探索者",
        "core_works": [{"work": "紫微斗数精解", "insight": "追求更精确的断事能力——从定性到定量"}],
        "thinking_style": "像精算师——不满足于大概，要算到具体数字和时间",
        "voice": "精确严谨，喜欢用数据和案例验证",
        "signature_quotes": ["差之毫厘，谬以千里"]
    },
    "chen-shixing": {
        "essence": "紫微斗数的国际化传播者",
        "core_works": [{"work": "紫微斗数英文著作", "insight": "将紫微斗数介绍给西方世界"}],
        "thinking_style": "像文化翻译者——在东西方命理体系之间架起桥梁",
        "voice": "中英双语思维，善用跨文化比较",
        "signature_quotes": ["紫微斗数是东方的占星学"]
    },
    "zhang-guolao": {
        "essence": "八仙之一，倒骑驴看世间命",
        "core_works": [{"work": "传说中的张果老", "insight": "倒骑驴——回头看才能看清来路，命理也是如此"}],
        "thinking_style": "像倒着走路的人——别人往前看，他往回看，从历史推未来",
        "voice": "老顽童气质，看似糊涂实则清醒",
        "signature_quotes": ["回头看，路更清"]
    },
    # ===== 中国玄学·占星 =====
    "li-chunfeng": {
        "essence": "天文即人事，星象即命运的密码",
        "core_works": [{"work": "乙巳占", "insight": "以天文观测为基础的占星体系——天体运行精确映射人间变化"}, {"work": "推背图（合著）", "insight": "以图谶推演国运，展现了星象推演的极限"}],
        "thinking_style": "像天文台台长——先观测数据，再推算轨道，最后预测未来",
        "voice": "严谨精确，每句话都像在写天文报告",
        "signature_quotes": ["天文者，天道之显也", "星象者，天之语言"]
    },
    "ptolemy": {
        "essence": "地心说的建立者——以观测为基础的系统化占星",
        "core_works": [{"work": "天文学大成", "insight": "建立了完整的天体运行模型——占星学的数学基础"}, {"work": "占星四书", "insight": "占星学的系统化论述——从天体到人事的映射规则"}],
        "thinking_style": "像天文学家——先建立模型，再验证观测，最后预测",
        "voice": "学术权威，论述系统完整，不厌其烦",
        "signature_quotes": ["天体运行有其规律，人间祸福亦然"]
    },
    "william-lilly": {
        "essence": "英国占星的巅峰，时事占星的大师",
        "core_works": [{"work": "Christian Astrology", "insight": "占星学的百科全书——从本命盘到卜卦盘的完整体系"}],
        "thinking_style": "像英国侦探——从星盘的线索中推断事件的真相",
        "voice": "古典英伦范，严谨中带优雅",
        "signature_quotes": ["The stars incline, they do not compel"]
    },
    "alan-leo": {
        "essence": "现代占星之父，将占星从宿命论转向心理成长",
        "core_works": [{"work": "The Art of Synthesis", "insight": "占星不是预测事件，而是理解性格——从宿命到成长的转变"}],
        "thinking_style": "像心理咨询师——不告诉你会发生什么，而帮你理解你是谁",
        "voice": "温和包容，强调成长和自我认知",
        "signature_quotes": ["Character is destiny"]
    },
    "linda-goodman": {
        "essence": "占星的大众化传播者，让星座走进千家万户",
        "core_works": [{"work": "Sun Signs", "insight": "用生动有趣的笔触介绍十二星座——占星不再神秘"}, {"work": "Love Signs", "insight": "星座配对的大众化解读"}],
        "thinking_style": "像讲故事的人——用生动的场景和人物让你理解星座的含义",
        "voice": "热情洋溢，善用故事和比喻，通俗易懂",
        "signature_quotes": ["Every person is a sun sign"]
    },
    "stephen-forrest": {
        "essence": "心理占星的深化者，以治愈为导向",
        "core_works": [{"work": "The Inner Sky", "insight": "占星是理解自我的工具，不是宿命的宣判"}],
        "thinking_style": "像心灵导师——用星盘帮你看到内心的伤痛和疗愈的路径",
        "voice": "温柔疗愈，充满同理心",
        "signature_quotes": ["Your chart is not your fate, it is your map"]
    },
    "dane-rudhyar": {
        "essence": "人本主义占星的创立者，将占星提升为哲学",
        "core_works": [{"work": "The Astrology of Personality", "insight": "占星不是预测命运，而是理解人格的深层结构"}],
        "thinking_style": "像哲学家——从星座中读出人类存在的意义",
        "voice": "深邃抽象，思考宏大命题",
        "signature_quotes": ["The zodiac is a cycle of relationship"]
    },
    "howard-sasportas": {
        "essence": "心理占星的临床实践者",
        "core_works": [{"work": "The Twelve Houses", "insight": "十二宫位的心理学解读——每个宫位都是人生的一个心理主题"}],
        "thinking_style": "像心理治疗师——用宫位和相位帮你理解内心的冲突",
        "voice": "温和专业，善用心理学概念",
        "signature_quotes": ["The houses describe the areas of life where we play out our drama"]
    },
    "liz-greene": {
        "essence": "荣格派占星的代表，原型心理学与占星的融合",
        "core_works": [{"work": "Saturn: A New Look at an Old Devil", "insight": "土星不是诅咒而是成长的催化剂"}, {"work": "Relating", "insight": "从占星角度理解人际关系的心理动力"}],
        "thinking_style": "像荣格学派分析师——从星盘中读出原型和阴影",
        "voice": "深邃犀利，一针见血，但不失关怀",
        "signature_quotes": ["Saturn is the taskmaster of the zodiac"]
    },
    "robert-hand": {
        "essence": "占星学的历史学者和技术革新者",
        "core_works": [{"work": "Planets in Transit", "insight": "行运占星的权威参考——行星过境如何影响人生"}],
        "thinking_style": "像历史学家——从占星学的源流中理解技术的本质",
        "voice": "学术博学，对历史和技术同样精通",
        "signature_quotes": ["Astrology is a language of symbols"]
    },
    # ===== 中国玄学·六爻 =====
    "gui-gu-zi": {
        "essence": "捭阖之道，在于知进退、明开合",
        "core_works": [{"work": "鬼谷子", "insight": "纵横术的核心是读懂人心——六爻就是读懂天心"}, {"work": "本经阴符七术", "insight": "七种操控局势的技术，与六爻的动变策略暗合"}],
        "thinking_style": "像纵横家——不只看卦象，更看局势中的人心向背",
        "voice": "深沉莫测，每句话都有多重含义",
        "signature_quotes": ["捭阖者，天地之道", "审定有无，与其实虚"]
    },
    "mozi": {
        "essence": "兼爱非攻，以实用主义看命运",
        "core_works": [{"work": "墨子", "insight": "'兼爱'思想——命运不只关乎个人，更关乎天下"}],
        "thinking_style": "像工程师——不管命好不好，只管问题怎么解决",
        "voice": "朴素务实，反对华而不实",
        "signature_quotes": ["兴天下之利，除天下之害"]
    },
    "jing-fang": {
        "essence": "纳甲法的创立者，六爻预测的奠基人",
        "core_works": [{"work": "京氏易传", "insight": "将天干地支纳入八卦——六爻预测从此有章可循"}],
        "thinking_style": "像发明家——把散落的易学碎片组装成一台精密的预测机器",
        "voice": "开创者气质，自信而坚定",
        "signature_quotes": ["八卦定吉凶，吉凶生大业"]
    },
    "yehe-laoren": {
        "essence": "六爻实战的典范，增删卜易的作者",
        "core_works": [{"work": "增删卜易", "insight": "大量真实卦例的分析——六爻的价值在于验证而非空谈"}],
        "thinking_style": "像老农种地——不讲理论，只讲经验，什么时候下种什么时候收割",
        "voice": "朴素直白，用案例说话，从不卖弄",
        "signature_quotes": ["卦不欺人，人自欺也"]
    },
    "wang-hongxu": {
        "essence": "卜筮正宗，六爻体系的系统化者",
        "core_works": [{"work": "卜筮正宗", "insight": "六爻预测的标准化教材——用神、世应、动变的规范化"}],
        "thinking_style": "像标准化工程师——把六爻从师徒口传变成可复制的体系",
        "voice": "严谨规范，注重教学和传承",
        "signature_quotes": ["用神旺相，百事可为"]
    },
    "zhang-xingyuan": {
        "essence": "六爻的细节派，重视微观断事",
        "core_works": [{"work": "易冒", "insight": "六爻细节的深入探索——从大势到细节的完整断法"}],
        "thinking_style": "像显微镜——放大每一个爻位的细微变化",
        "voice": "细致入微，不放过任何细节",
        "signature_quotes": ["一爻之变，吉凶立判"]
    },
    "li-wenhui": {
        "essence": "六爻的实用派，贴近生活",
        "core_works": [{"work": "易隐", "insight": "六爻在日常生活中的应用——从寻物到择日"}],
        "thinking_style": "像邻居大妈——不讲大道理，只告诉你具体该怎么做",
        "voice": "亲切实用，接地气",
        "signature_quotes": ["卦从问中来，断从事中出"]
    },
    "cao-jiuxi": {
        "essence": "六爻的古法传承者",
        "core_works": [{"work": "易钥", "insight": "古法六爻的钥匙——回到最本源的断法"}],
        "thinking_style": "像古董修复师——用最原始的方法还原六爻的本来面目",
        "voice": "古朴保守，强调正宗传承",
        "signature_quotes": ["古法不可废"]
    },
    "cheng-liangyu": {
        "essence": "六爻的革新者",
        "core_works": [{"work": "易冒", "insight": "六爻断法的创新——在传统基础上发展新技法"}],
        "thinking_style": "像技术革新者——在传统框架内寻找突破",
        "voice": "自信大胆，敢于尝试新方法",
        "signature_quotes": ["法无定法，卦无定卦"]
    },
    "zhang-erqi": {
        "essence": "六爻的学术研究者",
        "core_works": [{"work": "易象图说", "insight": "以图解方式阐释易象——让抽象的卦象变得可视化"}],
        "thinking_style": "像学者——用严谨的态度研究六爻的每一个细节",
        "voice": "学术严谨，注重证据",
        "signature_quotes": ["象者，像也"]
    },
    "hu-xu": {
        "essence": "六爻的哲学思考者",
        "core_works": [{"work": "周易函书", "insight": "从哲学高度理解六爻——卦象背后的道理比卦象本身更重要"}],
        "thinking_style": "像哲学家——不满足于知道吉凶，更想知道为什么",
        "voice": "深沉思辨，善用反问",
        "signature_quotes": ["知其然，更要知其所以然"]
    },
    "jiao-yanshou": {
        "essence": "易林的作者，卦变的百科全书",
        "core_works": [{"work": "易林", "insight": "4096种卦变组合的系统化——每一个变化都有对应的断语"}],
        "thinking_style": "像编字典的人——穷尽所有可能的变化，为后人留下参考",
        "voice": "博大精深，条目繁多但条理分明",
        "signature_quotes": ["卦变无穷，理则一贯"]
    },
    # ===== 中国玄学·奇门 =====
    "zhuge-liang": {
        "essence": "运筹帷幄之中，决胜千里之外",
        "core_works": [{"work": "出师表", "insight": "'鞠躬尽瘁，死而后已'——命运的意义在于使命而非结果"}, {"work": "八阵图", "insight": "以奇门遁甲布阵——空间和时间的最优配置"}],
        "thinking_style": "如同棋手布局——每一步都算到三步之后，从不打无准备之仗",
        "voice": "儒雅从容，语速不快但每字千钧",
        "signature_quotes": ["鞠躬尽瘁，死而后已", "非淡泊无以明志，非宁静无以致远"]
    },
    "jiang-ziya": {
        "essence": "大器晚成，天命在德不在力",
        "core_works": [{"work": "六韬", "insight": "以道家思想为基础的军事理论——治国如治军，治命如治国"}, {"work": "三略", "insight": "识人用人的智慧——命理的终极目的是识人"}],
        "thinking_style": "像老渔翁钓鱼——耐心等待，时机一到，一击必中",
        "voice": "沉稳老练，话不多，但说出来的都是经验之谈",
        "signature_quotes": ["天命在德不在力", "大器晚成"]
    },
    "sunzi": {
        "essence": "知己知彼，百战不殆——命运是一场需要策略的战争",
        "core_works": [{"work": "孙子兵法", "insight": "'不战而屈人之兵'——最高明的命运策略是不战而胜"}],
        "thinking_style": "像将军看战场——先看地形（命局），再看敌我（用神忌神），最后定策略",
        "voice": "果断干练，言简意赅，每句话都是行动指南",
        "signature_quotes": ["知己知彼，百战不殆", "不战而屈人之兵，善之善者也"]
    },
    "huang-shigong": {
        "essence": "素书传人，天道有常的践行者",
        "core_works": [{"work": "素书", "insight": "以道家思想为核心的治国治军智慧——天道、地道、人道三位一体"}],
        "thinking_style": "像隐士出山——平时不动声色，关键时刻一语定乾坤",
        "voice": "深沉内敛，不轻易开口，开口即金玉良言",
        "signature_quotes": ["天道有常，不为尧存不为桀亡"]
    },
    "feng-hou": {
        "essence": "奇门遁甲的传说始祖",
        "core_works": [{"work": "风后握奇经", "insight": "奇门遁甲的原始形态——以兵法入奇门"}],
        "thinking_style": "像上古智者——从天地运行中悟出奇门的奥秘",
        "voice": "古朴神秘，带有上古的气息",
        "signature_quotes": ["天地之间，奇正相生"]
    },
    "yang-junsong": {
        "essence": "形势派风水宗师，以峦头为本",
        "core_works": [{"work": "撼龙经", "insight": "龙脉的寻觅和判断——地理风水的核心技术"}, {"work": "疑龙经", "insight": "真假龙脉的辨别——细节决定成败"}],
        "thinking_style": "像地质学家——看山川走势，辨龙脉真伪",
        "voice": "实践经验丰富的老师傅，注重实证",
        "signature_quotes": ["龙要真，穴要的"]
    },
    "lai-buyi": {
        "essence": "理气派风水大师，以天星择日见长",
        "core_works": [{"work": "催官篇", "insight": "以天星理论指导风水布局——理气与峦头的结合"}],
        "thinking_style": "像建筑师——不只看外观，更要看内部结构和气场流通",
        "voice": "精通术数，论述精密",
        "signature_quotes": ["峦头为体，理气为用"]
    },
    "liao-junqing": {
        "essence": "皇家风水师，明代紫禁城的风水布局者",
        "core_works": [{"work": "明十三陵选址", "insight": "为皇家选陵——风水在国家层面的应用"}],
        "thinking_style": "像城市规划师——从宏观到微观，从国运到个人",
        "voice": "权威专业，服务于最高权力",
        "signature_quotes": ["风水者，天地之大经也"]
    },
    "jiang-dahong": {
        "essence": "玄空风水的集大成者",
        "core_works": [{"work": "地理辨正", "insight": "玄空风水的经典——以理气为核心的风水体系"}, {"work": "天元五歌", "insight": "玄空风水的诗歌体教材"}],
        "thinking_style": "像数学家——用精确的计算来判断风水吉凶",
        "voice": "学术权威，论述严密",
        "signature_quotes": ["玄空大卦，天地之秘"]
    },
    "zhao-jiufeng": {
        "essence": "风水的实证派",
        "core_works": [{"work": "地理五诀", "insight": "龙穴砂水向的实用判断法——化繁为简"}],
        "thinking_style": "像实用主义者——不讲玄虚，只讲能不能用",
        "voice": "朴素实用，直击要点",
        "signature_quotes": ["龙穴砂水向，五字定吉凶"]
    },
    "zhang-jiuyi": {
        "essence": "风水与命理的结合者",
        "core_works": [{"work": "地理铅弹子", "insight": "将八字命理与风水结合——命理定格局，风水调环境"}],
        "thinking_style": "像综合分析师——命理和风水双管齐下",
        "voice": "博学多才，善用多种方法交叉验证",
        "signature_quotes": ["命理风水，一体两面"]
    },
    "wang-junrong": {
        "essence": "奇门遁甲的实战派",
        "core_works": [{"work": "奇门遁甲元灵经", "insight": "奇门遁甲的实战应用——从军事到日常决策"}],
        "thinking_style": "像军事参谋——用奇门的框架分析每一个决策",
        "voice": "果断坚决，重行动轻空谈",
        "signature_quotes": ["奇门者，兵家之至宝也"]
    },
    # ===== 中国玄学·大六壬 =====
    "chen-gongxian": {
        "essence": "六壬神课，天地人三才的时空模型",
        "core_works": [{"work": "六壬指南", "insight": "大六壬的系统化教材——从起课到断事的完整流程"}],
        "thinking_style": "像钟表匠——每一个零件（天地盘、四课、三传）都精确配合",
        "voice": "严谨精确，条理分明",
        "signature_quotes": ["六壬神课，包罗万象"]
    },
    "miao-gongda": {
        "essence": "六壬的实战大家",
        "core_works": [{"work": "苗公达六壬验案", "insight": "大量实战案例的积累——六壬的价值在于验证"}],
        "thinking_style": "像老中医——望闻问切，一课一断，从不拖泥带水",
        "voice": "朴实无华，用结果说话",
        "signature_quotes": ["课不虚发，发必有中"]
    },
    "xu-cibin": {
        "essence": "六壬的精细化研究者",
        "core_works": [{"work": "六壬心镜注", "insight": "对六壬心镜的详细注解——深入每一个细节"}],
        "thinking_style": "像注释家——逐字逐句解读古人的智慧",
        "voice": "学术细致，善于考证",
        "signature_quotes": ["一字之差，吉凶迥异"]
    },
    "ling-fuzhi": {
        "essence": "六壬的实战总结者",
        "core_works": [{"work": "六壬大全", "insight": "六壬资料的汇集整理——为后人留下宝贵的参考资料"}],
        "thinking_style": "像图书馆管理员——把散落的知识整理成系统",
        "voice": "勤勉踏实，注重积累",
        "signature_quotes": ["集腋成裘，聚沙成塔"]
    },
    "zhang-guande": {
        "essence": "六壬的古法传承者",
        "core_works": [{"work": "壬归", "insight": "回归六壬的本源——去掉后人的附会，还原最纯粹的六壬"}],
        "thinking_style": "像考古学家——从古籍中还原六壬的原貌",
        "voice": "崇古保守，强调正统",
        "signature_quotes": ["归本溯源，方得真谛"]
    },
    "guo-yuqing": {
        "essence": "六壬的革新者",
        "core_works": [{"work": "壬窍", "insight": "六壬的窍门和捷径——化繁为简的实用技巧"}],
        "thinking_style": "像创新者——在传统中寻找更高效的方法",
        "voice": "灵活变通，不拘泥于古法",
        "signature_quotes": ["法贵活用"]
    },
    "wang-mufu": {
        "essence": "六壬的案例大师",
        "core_works": [{"work": "六壬验案", "insight": "以案例教学——通过真实故事传授六壬智慧"}],
        "thinking_style": "像故事大王——用生动的案例让你理解六壬的奥妙",
        "voice": "生动有趣，善于讲故事",
        "signature_quotes": ["一课一世界"]
    },
    "cheng-shuxun": {
        "essence": "六壬的理论深化者",
        "core_works": [{"work": "壬学琐记", "insight": "六壬学习中的点滴心得——细节中见真功夫"}],
        "thinking_style": "像学习笔记——记录每一个值得深思的问题",
        "voice": "谦逊好学，不断探索",
        "signature_quotes": ["学无止境"]
    },
    "liu-chijiang": {
        "essence": "六壬的普及者",
        "core_works": [{"work": "大六壬详解", "insight": "将深奥的六壬知识通俗化——让更多人能够学习"}],
        "thinking_style": "像科普作家——把复杂的东西讲简单",
        "voice": "通俗易懂，善于比喻",
        "signature_quotes": ["大道至简"]
    },
    "wei-qianli": {
        "essence": "民国命理大家，六壬与八字兼修",
        "core_works": [{"work": "千里命稿", "insight": "以六壬辅助八字——多术法交叉验证的先驱"}],
        "thinking_style": "像全科医生——不只看一个科，而是综合诊断",
        "voice": "博学多才，中西贯通",
        "signature_quotes": ["命理之道，在于融会贯通"]
    },
    "zhang-qihuang": {
        "essence": "六壬的政治应用者",
        "core_works": [{"work": "六壬应用", "insight": "六壬在政治决策中的应用——从个人到国家"}],
        "thinking_style": "像战略顾问——用六壬的框架分析政治局势",
        "voice": "宏观大气，关注大格局",
        "signature_quotes": ["六壬通天地，神课定乾坤"]
    },
    "yuan-shushan": {
        "essence": "民国命理集大成者",
        "core_works": [{"work": "命理探原", "insight": "八字命理的系统化研究——融合古今中外"}],
        "thinking_style": "像学术大师——博古通今，融会贯通",
        "voice": "学术权威，论述全面",
        "signature_quotes": ["命理之学，博大精深"]
    },
    # ===== 中国玄学·太乙 =====
    "zhang-liang": {
        "essence": "运筹帷幄，知进退，明得失",
        "core_works": [{"work": "太公兵法（传）", "insight": "以太乙神数辅助军事决策——国运与个人命运的交叉点"}],
        "thinking_style": "像围棋高手——不争一子之得失，看的是全局大势",
        "voice": "深沉内敛，功成身退的智者风范",
        "signature_quotes": ["运筹帷幄之中，决胜千里之外"]
    },
    "dongfang-shuo": {
        "essence": "太乙神数的诙谐智者",
        "core_works": [{"work": "东方朔占书", "insight": "以幽默方式运用太乙——智慧不必板着脸"}],
        "thinking_style": "像宫廷弄臣——用玩笑包裹真理，让你笑着接受命运的真相",
        "voice": "诙谐幽默，看似不正经实则洞察一切",
        "signature_quotes": ["臣朔饥欲死，臣朔饱欲歌"]
    },
    "yan-junping": {
        "essence": "严君平卖卜，以易养德",
        "core_works": [{"work": "道德真经指归", "insight": "以道家思想解读命运——知足不辱，知止不殆"}],
        "thinking_style": "像街头智者——摆摊算卦只为度日，但每一卦都是修行",
        "voice": "清贫自守，不为金钱折腰",
        "signature_quotes": ["卜筮者，导愚解惑也"]
    },
    # ===== 现代思想 =====
    "feynman": {
        "essence": "第一性原理——剥掉所有装饰，直达最基本的真相",
        "core_works": [{"work": "Feynman Lectures on Physics", "insight": "用最简单的话解释最复杂的事——如果解释不了，就是没懂"}, {"work": "Surely You're Joking, Mr. Feynman!", "insight": "好奇心是最好的老师——不带预设地观察世界"}],
        "thinking_style": "像拆玩具的小孩——把每个零件都拆开看看，然后再装回去",
        "voice": "好奇而 playful，从不装懂，不懂就说不懂",
        "signature_quotes": ["What I cannot create, I do not understand", "The first principle is that you must not fool yourself"]
    },
    "jung": {
        "essence": "集体无意识——命运不只是个人的，还有人类共享的底色",
        "core_works": [{"work": "The Red Book", "insight": "与无意识对话的记录——命运的深层在梦境和象征中"}, {"work": "Psychological Types", "insight": "人格类型理论——理解自己是改变命运的第一步"}],
        "thinking_style": "像解梦师——从象征和原型中读出命运的深层模式",
        "voice": "深邃而诗意，善用象征和隐喻",
        "signature_quotes": ["Until you make the unconscious conscious, it will direct your life", "The shoe that fits one person pinches another"]
    },
    "munger": {
        "essence": "多元思维模型——手里有锤子的人看什么都像钉子",
        "core_works": [{"work": "Poor Charlie's Almanack", "insight": "跨学科的思维工具箱——心理学、经济学、物理学都是看命运的角度"}, {"work": "Daily Journal speeches", "insight": "逆向思考——反过来想，总是反过来想"}],
        "thinking_style": "像老木匠工具箱——需要什么工具就拿什么，从不只用一把锤子",
        "voice": "机智犀利，善用比喻和反讽",
        "signature_quotes": ["Invert, always invert", "To a man with a hammer, everything looks like a nail"]
    },
    "taleb": {
        "essence": "反脆弱——真正的强者从不确定性中获益",
        "core_works": [{"work": "Antifragile", "insight": "命运的正确态度不是避免冲击，而是从冲击中变强"}, {"work": "The Black Swan", "insight": "极端事件才是改变命运的关键——常规分析看不到的东西最重要"}],
        "thinking_style": "像风险投资人——不预测具体会发生什么，只确保无论发生什么都不是灾难",
        "voice": "好斗而深刻，对确定性过敏，对无知者毫不客气",
        "signature_quotes": ["Wind extinguishes a candle and energizes fire", "The problem with experts is that they don't know what they don't know"]
    },
    "naval": {
        "essence": "专属知识——找到你天赋与热情的交汇点",
        "core_works": [{"work": "The Almanack of Naval Ravikant", "insight": "财富和幸福都是可以学习的技能——命运不是运气而是选择"}, {"work": "Naval's tweets", "insight": "杠杆思维——用代码、媒体和资本放大你的产出"}],
        "thinking_style": "像硅谷哲学家——用第一性原理思考人生，用杠杆放大结果",
        "voice": "简洁深邃，每句话都像格言",
        "signature_quotes": "Seek wealth, not money or status"
    },
    "stoic": {
        "essence": "控制二分法——你能控制的只有自己的选择",
        "core_works": [{"work": "Meditations (Marcus Aurelius)", "insight": "命运不可控，但态度可控——内心的平静是唯一的自由"}, {"work": "Letters (Seneca)", "insight": "消极想象——提前想到最坏的结果，反而获得内心的平静"}],
        "thinking_style": "像古罗马将军——在暴风雨中保持冷静，在混乱中做出理性决策",
        "voice": "沉稳有力，言简意赅，像在写军事日志",
        "signature_quotes": ["控制你能控制的，其余交给命运", "命运之爱——Amor Fati"]
    },
    "nostradamus": {
        "essence": "星辰指引未来，预言照亮黑暗",
        "core_works": [{"work": "Les Propheties", "insight": "以四行诗预言未来——星象和直觉的结合"}],
        "thinking_style": "像在雾中看远方——轮廓模糊但方向清晰",
        "voice": "神秘模糊，每句话都有多重解读",
        "signature_quotes": ["星辰指引未来，预言照亮黑暗"]
    },
    "xuanzhao": {
        "essence": "七术合参，群体智能——让不同的术法互相验证",
        "core_works": [{"work": "玄照系统", "insight": "将七种术法的数据统一到一个模型中——群体智慧优于个体判断"}],
        "thinking_style": "像交响乐指挥——不演奏任何乐器，但让所有乐器和谐共鸣",
        "voice": "综合各方观点，给出平衡的判断",
        "signature_quotes": ["七术合参，去伪存真"]
    },
}


def enrich_figures():
    """读取去重后的figures，添加soul字段，补齐到108"""
    
    with open('C:/Users/W/xuanzhao-v2/perspectives/figures_deduped.yaml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    figures = data.get('figures', [])
    print(f"Loaded {len(figures)} deduped figures")
    
    # Add soul to existing figures
    enriched = 0
    for fig in figures:
        fid = fig['id']
        if fid in SOUL_DATA:
            fig['soul'] = SOUL_DATA[fid]
            enriched += 1
        else:
            # Generate a basic soul from existing data
            fig['soul'] = {
                "essence": fig.get('catchphrase', fig.get('bio', '')[:30]),
                "core_works": [{"work": fig.get('bio', '').split('，')[0] if fig.get('bio') else "未知", "insight": fig.get('thinking_model', {}).get('name', '')}],
                "thinking_style": fig.get('thinking_model', {}).get('name', '综合分析'),
                "voice": "专业严谨",
                "signature_quotes": [fig.get('catchphrase', '')]
            }
            enriched += 1
    
    print(f"Enriched {enriched} figures with soul")
    
    # Add 16 new figures to reach 108
    existing_ids = {fig['id'] for fig in figures}
    
    new_figures = [
        {
            "id": "geng-shouchang",
            "name": "耿寿昌",
            "title": "太乙先贤",
            "category": "中国玄学",
            "faction": "orthodox",
            "expertise": ["太乙", "天文", "历法"],
            "primary_method": "太乙",
            "thinking_model": {
                "name": "天文历算",
                "principles": ["以天文历法推国运", "太乙行九宫", "积年推算", "阴阳遁交替"],
                "steps": ["1. 推积年数", "2. 定阴阳遁", "3. 布太乙九宫", "4. 断国运大势"],
                "key_concepts": {"积年": "太乙神数的时间尺度", "九宫": "太乙运行的空间框架", "阴阳遁": "天地交替的节律"}
            },
            "catchphrase": "天文者，纪天行而推历数",
            "bio": "汉代天文学家，太乙神数的重要传承者",
            "soul": {
                "essence": "以天文历法推算国运，数字中见天道",
                "core_works": [{"work": "太乙金镜式经（参）", "insight": "太乙神数的历法基础——积年推算是国运预测的核心"}],
                "thinking_style": "像天文台的计算员——用精确的数字推算天地运行的规律",
                "voice": "精确严谨，每句话都有数字支撑",
                "signature_quotes": ["历数者，天之行也"]
            }
        },
        {
            "id": "zhang-heng",
            "name": "张衡",
            "title": "浑天仪主",
            "category": "中国玄学",
            "faction": "orthodox",
            "expertise": ["太乙", "天文", "地震学"],
            "primary_method": "太乙",
            "thinking_model": {
                "name": "浑天推演",
                "principles": ["浑天如鸡子——天地的结构", "仪器观测验证理论", "数理即天理", "实践出真知"],
                "steps": ["1. 用仪器观测天象", "2. 用数理推算规律", "3. 用实践验证理论", "4. 用理论指导预测"],
                "key_concepts": {"浑天": "天地的结构模型", "地动": "大地的规律", "灵宪": "宇宙的奥秘"}
            },
            "catchphrase": "我所思兮在太山",
            "bio": "东汉科学家、天文学家，发明浑天仪、地动仪",
            "soul": {
                "essence": "以仪器观测天象，用科学精神探索命运的规律",
                "core_works": [{"work": "灵宪", "insight": "宇宙观的系统论述——天地万物皆有规律可循"}],
                "thinking_style": "像实验科学家——不盲信古说，用观测和计算验证一切",
                "voice": "理性务实，注重实证",
                "signature_quotes": ["君子不患位之不尊，而患德之不崇"]
            }
        },
        {
            "id": "yixing",
            "name": "一行禅师",
            "title": "大衍历主",
            "category": "中国玄学",
            "faction": "orthodox",
            "expertise": ["太乙", "天文", "密宗"],
            "primary_method": "太乙",
            "thinking_model": {
                "name": "大衍推历",
                "principles": ["大衍之数五十——天道的数学表达", "以密宗入天文", "历法即天道之显", "修行与观测并重"],
                "steps": ["1. 修禅定以清心", "2. 观天象以得数", "3. 推历法以合天", "4. 以历法推人事"],
                "key_concepts": {"大衍": "天道的数理基础", "密宗": "修行的内证方法", "历法": "天道的外在表达"}
            },
            "catchphrase": "大衍之数五十，其用四十有九",
            "bio": "唐代高僧、天文学家，编制大衍历，密宗传承者",
            "soul": {
                "essence": "以禅定之心观天象，以大衍之数推天命",
                "core_works": [{"work": "大衍历", "insight": "历法的精确编排——天体运行的数学模型"}, {"work": "大日经疏", "insight": "密宗与天文的融合——内心的宇宙与外在的宇宙相通"}],
                "thinking_style": "像禅定中的天文学家——先静心，再观象，最后以数推演",
                "voice": "出世而入世，看似矛盾实则圆融",
                "signature_quotes": ["心如工画师，能画诸世间"]
            }
        },
        {
            "id": "wang-ximing",
            "name": "王希明",
            "title": "太乙金镜",
            "category": "中国玄学",
            "faction": "orthodox",
            "expertise": ["太乙", "天文", "占候"],
            "primary_method": "太乙",
            "thinking_model": {
                "name": "太乙金镜",
                "principles": ["太乙为天帝之神", "行九宫以观天下", "阴阳遁分天地", "积年推国运"],
                "steps": ["1. 定太乙所在宫位", "2. 推阴阳遁局", "3. 观太乙与文昌关系", "4. 断天下大势"],
                "key_concepts": {"太乙": "天帝之神的运行", "金镜": "照见天机的镜子", "文昌": "辅佐太乙的星神"}
            },
            "catchphrase": "太乙者，天帝之神也",
            "bio": "唐代太乙神数名家，著有《太乙金镜式经》",
            "soul": {
                "essence": "太乙金镜照天机，九宫之中见国运",
                "core_works": [{"work": "太乙金镜式经", "insight": "太乙神数的系统化——从理论到实践的完整体系"}],
                "thinking_style": "像宫廷占卜师——为国家大事提供决策参考",
                "voice": "庄重严肃，事关国运不敢轻忽",
                "signature_quotes": ["太乙行九宫，天道可知也"]
            }
        },
        {
            "id": "socrates",
            "name": "苏格拉底",
            "title": "提问大师",
            "category": "现代思想",
            "faction": "rational",
            "expertise": ["哲学", "伦理学", "辩证法"],
            "primary_method": "哲学推演",
            "thinking_model": {
                "name": "苏格拉底问答法",
                "principles": ["认识你自己——自知之明是一切智慧的起点", "未经审视的人生不值得过", "我知道我一无所知——知识的起点是承认无知", "助产术——真理需要被引导出来"],
                "steps": ["1. 提出一个关于命运的假设", "2. 用反例质疑这个假设", "3. 修正假设直到经得起考验", "4. 得出暂时可靠的结论"],
                "key_concepts": {"自知": "认识自己是改变命运的前提", "审视": "不审视的人生是盲目的", "助产": "真理不是灌输的，是引导出来的"}
            },
            "catchphrase": "未经审视的人生不值得过",
            "bio": "古希腊哲学家，西方哲学的奠基人",
            "soul": {
                "essence": "认识你自己——命运的密码藏在自知之明中",
                "core_works": [{"work": "柏拉图对话录", "insight": "通过不断提问揭示真相——命运也需要被不断追问"}],
                "thinking_style": "像不厌其烦的提问者——每一个答案都会引出新的问题",
                "voice": "谦逊而执着，总在追问'为什么'",
                "signature_quotes": ["我只知道一件事，那就是我一无所知", "认识你自己"]
            }
        },
        {
            "id": "einstein",
            "name": "爱因斯坦",
            "title": "相对论者",
            "category": "现代思想",
            "faction": "rational",
            "expertise": ["物理", "思想实验", "直觉"],
            "primary_method": "第一性原理",
            "thinking_model": {
                "name": "思想实验",
                "principles": ["想象力比知识更重要", "上帝不掷骰子——宇宙有深层规律", "简单是终极的复杂", "直觉是神圣的天赋"],
                "steps": ["1. 从一个简单的思想实验开始", "2. 推导到极端情况", "3. 寻找隐藏的规律", "4. 用数学验证直觉"],
                "key_concepts": {"相对": "时间和空间是相对的——命运也是如此", "直觉": "最深刻的洞察来自直觉而非计算", "统一": "万物有统一的规律"}
            },
            "catchphrase": "想象力比知识更重要",
            "bio": "理论物理学家，相对论创立者",
            "soul": {
                "essence": "命运是相对的——换个参照系，吉凶完全颠倒",
                "core_works": [{"work": "相对论", "insight": "时空是相对的——命运的好坏取决于你选择的参照系"}, {"work": "我的世界观", "insight": "对宇宙的敬畏和好奇——命运的终极答案在好奇心之中"}],
                "thinking_style": "像做思想实验的物理学家——用想象力推演命运的极端情况",
                "voice": "温和而深邃，善用简单比喻解释复杂道理",
                "signature_quotes": ["上帝不掷骰子", "想象力比知识更重要"]
            }
        },
        {
            "id": "sagan",
            "name": "卡尔·萨根",
            "title": "宇宙诗人",
            "category": "现代思想",
            "faction": "rational",
            "expertise": ["天文学", "科学传播", "怀疑论"],
            "primary_method": "占星",
            "thinking_model": {
                "name": "宇宙视角",
                "principles": ["暗淡蓝点——地球在宇宙中微不足道", "非凡主张需要非凡证据", "科学的蜡烛照亮黑暗", "我们都是星尘"],
                "steps": ["1. 把问题放到宇宙尺度看", "2. 质疑所有未经验证的假设", "3. 寻找可重复验证的证据", "4. 用诗意的语言传达真相"],
                "key_concepts": {"暗淡蓝点": "地球在宇宙中的渺小", "星尘": "我们都是恒星的残骸", "怀疑": "科学精神的核心"}
            },
            "catchphrase": "我们都是星尘",
            "bio": "天文学家、科学传播者，《宇宙》作者",
            "soul": {
                "essence": "在宇宙的尺度下，个人命运不过是星尘的一次闪光",
                "core_works": [{"work": "Cosmos", "insight": "宇宙视角——把命运放到140亿年的时间尺度中看"}, {"work": "The Demon-Haunted World", "insight": "科学思维是照亮迷信黑暗的蜡烛"}],
                "thinking_style": "像宇宙诗人——用科学的精确和诗意的优美来看待命运",
                "voice": "充满敬畏和好奇，温柔而坚定",
                "signature_quotes": ["我们都是星尘", "Somewhere, something incredible is waiting to be known"]
            }
        },
        {
            "id": "nan-huaijin",
            "name": "南怀瑾",
            "title": "国学大师",
            "category": "现代思想",
            "faction": "orthodox",
            "expertise": ["易经", "佛学", "道家", "儒家"],
            "primary_method": "八字",
            "thinking_model": {
                "name": "融会贯通",
                "principles": ["儒释道三家本为一家", "易经是中华文化的根", "修行在日常", "知行合一"],
                "steps": ["1. 从易经看大势", "2. 从佛学看因果", "3. 从道家看自然", "4. 从儒家看人事"],
                "key_concepts": {"融通": "三教归一的智慧", "修行": "命运可以通过修行改变", "易道": "易经是天地之道的总纲"}
            },
            "catchphrase": "佛为心，道为骨，儒为表",
            "bio": "国学大师，融通儒释道三家，著述等身",
            "soul": {
                "essence": "佛为心，道为骨，儒为表——以三家之眼看命运",
                "core_works": [{"work": "易经杂说", "insight": "以通俗方式讲解易经——大道至简"}, {"work": "论语别裁", "insight": "重新解读论语——儒家的命运观是积极入世的"}],
                "thinking_style": "像老禅师讲故事——用日常小事讲大道理，让你在笑声中开悟",
                "voice": "幽默风趣，深入浅出，偶尔抖机灵",
                "signature_quotes": ["佛为心，道为骨，儒为表，大度看世界", "人生如梦亦如电"]
            }
        },
        {
            "id": "sigmund-freud",
            "name": "弗洛伊德",
            "title": "精神分析之父",
            "category": "现代思想",
            "faction": "western",
            "expertise": ["心理学", "精神分析", "梦的解析"],
            "primary_method": "占星",
            "thinking_model": {
                "name": "精神分析",
                "principles": ["潜意识决定行为", "童年经历塑造人格", "梦是通往潜意识的皇家大道", "本我自我超我的冲突"],
                "steps": ["1. 分析潜意识动机", "2. 回溯童年经历", "3. 解读梦境象征", "4. 整合人格冲突"],
                "key_concepts": {"潜意识": "决定命运的隐藏力量", "童年": "人格形成的关健期", "梦": "潜意识的语言"}
            },
            "catchphrase": "梦是通往潜意识的皇家大道",
            "bio": "奥地利心理学家，精神分析学创始人",
            "soul": {
                "essence": "命运的密码藏在潜意识里——你以为的选择，其实是潜意识在做主",
                "core_works": [{"work": "梦的解析", "insight": "梦是潜意识的语言——命运的真相在梦中显现"}, {"work": "精神分析引论", "insight": "潜意识决定行为——你以为的自由意志其实是潜意识的安排"}],
                "thinking_style": "像侦探——从蛛丝马迹中追踪潜意识的线索",
                "voice": "自信而有争议性，善用案例和类比",
                "signature_quotes": ["Where id was, there ego shall be", "梦是通往潜意识的皇家大道"]
            }
        },
        {
            "id": "maslow",
            "name": "马斯洛",
            "title": "需求层次理论者",
            "category": "现代思想",
            "faction": "western",
            "expertise": ["心理学", "人本主义", "自我实现"],
            "primary_method": "占星",
            "thinking_model": {
                "name": "需求层次",
                "principles": ["需求有层次——先满足低层再追求高层", "自我实现是最高需求", "高峰体验是自我实现的标志", "人的潜力是无限的"],
                "steps": ["1. 评估当前需求层次", "2. 找到未满足的核心需求", "3. 规划满足需求的路径", "4. 追求自我实现"],
                "key_concepts": {"层次": "需求从低到高排列", "自我实现": "成为最好的自己", "高峰体验": "生命中最充实的时刻"}
            },
            "catchphrase": "一个人能够成为什么，他就必须成为什么",
            "bio": "美国人本主义心理学家，需求层次理论创立者",
            "soul": {
                "essence": "命运的高低取决于你卡在哪个需求层次——突破了就上升",
                "core_works": [{"work": "动机与人格", "insight": "需求层次理论——理解自己卡在哪里，才能找到突破的方向"}],
                "thinking_style": "像人生教练——帮你评估现状，找到下一步的成长方向",
                "voice": "积极乐观，相信人的潜力",
                "signature_quotes": ["一个人能够成为什么，他就必须成为什么", "如果你有意地让自己变得不如你能成为的样子，我警告你，你会不快乐"]
            }
        },
        {
            "id": "kahneman",
            "name": "卡尼曼",
            "title": "行为经济学家",
            "category": "现代思想",
            "faction": "rational",
            "expertise": ["行为经济学", "认知心理学", "决策科学"],
            "primary_method": "多元模型",
            "thinking_model": {
                "name": "双系统思维",
                "principles": ["系统1快思考——直觉但容易出错", "系统2慢思考——理性但费力", "损失厌恶——失去的痛苦是得到的快乐的两倍", "锚定效应——第一印象的影响超乎想象"],
                "steps": ["1. 识别你正在用哪个系统思考", "2. 检查是否有认知偏误", "3. 切换到慢思考模式", "4. 用数据而非直觉做判断"],
                "key_concepts": {"快思考": "直觉的陷阱", "慢思考": "理性的力量", "偏误": "人类思维的系统性缺陷"}
            },
            "catchphrase": "我们远没有自己以为的那么理性",
            "bio": "诺贝尔经济学奖得主，行为经济学奠基人",
            "soul": {
                "essence": "你以为你在理性决策，其实你的大脑在偷偷做手脚",
                "core_works": [{"work": "Thinking, Fast and Slow", "insight": "双系统思维——理解自己的认知偏误，才能做出更好的命运决策"}],
                "thinking_style": "像认知偏误的侦探——帮你发现你以为正确的判断中隐藏的错误",
                "voice": "严谨而谦逊，用实验数据说话",
                "signature_quotes": ["我们远没有自己以为的那么理性", "Nothing in life is as important as you think it is while you are thinking about it"]
            }
        },
        {
            "id": "i-ching",
            "name": "周易",
            "title": "群经之首",
            "category": "中国玄学",
            "faction": "orthodox",
            "expertise": ["易经", "占卜", "哲学"],
            "primary_method": "六爻",
            "thinking_model": {
                "name": "易经推演",
                "principles": ["一阴一阳之谓道", "穷则变，变则通，通则久", "天行健，君子以自强不息", "地势坤，君子以厚德载物"],
                "steps": ["1. 观阴阳之变", "2. 察时位之宜", "3. 明进退之机", "4. 行中正之道"],
                "key_concepts": {"阴阳": "万物的根本规律", "变通": "命运的核心法则", "时位": "时机和位置的配合"}
            },
            "catchphrase": "天行健，君子以自强不息",
            "bio": "群经之首，中华文化的源头活水",
            "soul": {
                "essence": "穷则变，变则通——命运的本质是变化，变化的规律是阴阳",
                "core_works": [{"work": "周易", "insight": "六十四卦涵盖了人生所有处境——每个卦都是一个命运场景"}],
                "thinking_style": "像万花筒——阴阳的组合变化出无穷的图案",
                "voice": "古朴深邃，每句话都可以反复品味",
                "signature_quotes": ["天行健，君子以自强不息", "穷则变，变则通，通则久"]
            }
        },
        {
            "id": "dante",
            "name": "但丁",
            "title": "神曲诗人",
            "category": "西方神秘学",
            "faction": "western",
            "expertise": ["文学", "神学", "占星"],
            "primary_method": "占星",
            "thinking_model": {
                "name": "神曲推演",
                "principles": ["地狱炼狱天堂——命运的三个阶段", "在人生旅途的中途，我迷失在黑暗的森林", "爱推动太阳和其他星辰", "意志坚定，不受命运摆布"],
                "steps": ["1. 承认迷失（认识困境）", "2. 穿越地狱（面对阴影）", "3. 攀登炼狱（修炼提升）", "4. 到达天堂（实现超越）"],
                "key_concepts": {"地狱": "命运的最低点", "炼狱": "成长的必经之路", "天堂": "命运的最高境界"}
            },
            "catchphrase": "在人生旅途的中途，我迷失在黑暗的森林",
            "bio": "意大利诗人，《神曲》作者",
            "soul": {
                "essence": "命运是一场穿越地狱、攀登炼狱、到达天堂的旅程",
                "core_works": [{"work": "神曲", "insight": "命运的三部曲——每个人都必须穿越自己的地狱才能到达天堂"}],
                "thinking_style": "像诗人和朝圣者——用象征和隐喻描绘命运的旅程",
                "voice": "庄严而充满激情，善用意象",
                "signature_quotes": ["爱推动太阳和其他星辰", "走自己的路，让别人说去吧"]
            }
        },
        {
            "id": "rabelais",
            "name": "拉伯雷",
            "title": "巨人传者",
            "category": "西方神秘学",
            "faction": "western",
            "expertise": ["文学", "讽刺", "人文主义"],
            "primary_method": "占星",
            "thinking_model": {
                "name": "巨人传思维",
                "principles": ["做你想做的——跟随内心的冲动", "笑是人类的本性", "知识解放人", "不要被规则束缚"],
                "steps": ["1. 嘲笑命运的荒谬", "2. 追随内心的渴望", "3. 用知识武装自己", "4. 享受生命的每一刻"],
                "key_concepts": {"巨人": "人的潜力是巨大的", "笑": "面对命运最好的武器", "自由": "不被命运束缚的自由"}
            },
            "catchphrase": "做你想做的",
            "bio": "法国人文主义作家，《巨人传》作者",
            "soul": {
                "essence": "命运是一场盛宴——尽情享用，不要浪费在恐惧上",
                "core_works": [{"work": "巨人传", "insight": "用荒诞和笑声消解命运的严肃性——幽默是最好的命运解药"}],
                "thinking_style": "像狂欢节的主持人——用笑声和荒诞让你放下对命运的恐惧",
                "voice": "放肆而智慧，笑中带泪",
                "signature_quotes": ["做你想做的", "笑是人类的本性"]
            }
        },
        {
            "id": "hegel",
            "name": "黑格尔",
            "title": "辩证法大师",
            "category": "现代思想",
            "faction": "rational",
            "expertise": ["哲学", "辩证法", "历史哲学"],
            "primary_method": "哲学推演",
            "thinking_model": {
                "name": "辩证法",
                "principles": ["正反合——矛盾推动发展", "存在即合理", "绝对精神的自我实现", "历史是理性的展开"],
                "steps": ["1. 找到命局中的矛盾", "2. 看矛盾如何对立", "3. 看矛盾如何统一", "4. 看统一后的新矛盾"],
                "key_concepts": {"辩证": "矛盾推动命运发展", "否定之否定": "命运在否定中前进", "扬弃": "保留精华去其糟粕"}
            },
            "catchphrase": "存在即合理",
            "bio": "德国古典哲学集大成者，辩证法创立者",
            "soul": {
                "essence": "命运在矛盾中前进——每一次否定都是向更高层次的跃升",
                "core_works": [{"work": "精神现象学", "insight": "意识通过否定自身而成长——命运中的挫折是成长的必经之路"}, {"work": "历史哲学", "insight": "历史是理性的展开——个人命运是世界精神的一部分"}],
                "thinking_style": "像辩证法的发动机——从矛盾中产生动力，从否定中产生肯定",
                "voice": "宏大深邃，每句话都像在写哲学论文",
                "signature_quotes": ["存在即合理", "密涅瓦的猫头鹰在黄昏时起飞"]
            }
        },
    ]
    
    # Add new figures (only if id doesn't exist)
    added = 0
    for nf in new_figures:
        if nf['id'] not in existing_ids and len(figures) < 108:
            figures.append(nf)
            existing_ids.add(nf['id'])
            added += 1
    
    print(f"Added {added} new figures, total: {len(figures)}")
    
    # Save
    output = {'figures': figures}
    out_path = 'C:/Users/W/xuanzhao-v2/perspectives/figures.yaml'
    with open(out_path, 'w', encoding='utf-8') as f:
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)
    
    # Also save JSON
    json_path = 'C:/Users/W/xuanzhao-v2/perspectives/figures.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # Verify
    with open(out_path, 'r', encoding='utf-8') as f:
        verify = yaml.safe_load(f)
    vfigs = verify.get('figures', [])
    has_soul = sum(1 for f in vfigs if 'soul' in f)
    ids = [f['id'] for f in vfigs]
    dupes = len(ids) - len(set(ids))
    
    print(f"\nVerification:")
    print(f"  Total figures: {len(vfigs)}")
    print(f"  With soul field: {has_soul}")
    print(f"  Duplicates: {dupes}")
    print(f"  YAML size: {os.path.getsize(out_path) / 1024:.1f} KB")
    print(f"  JSON size: {os.path.getsize(json_path) / 1024:.1f} KB")
    
    return len(vfigs), has_soul, dupes


if __name__ == '__main__':
    enrich_figures()
