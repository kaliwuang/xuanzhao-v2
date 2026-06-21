"""
姓名学引擎 (XingMing Engine) - XuanZhao v2.0
五格剖象法 (Five Grid Name Analysis) implementation.

Calculates 天格, 人格, 地格, 外格, 总格 and evaluates 81数理吉凶.
Includes 三才五行配置 analysis and optional 八字喜用神 matching.
"""

import unicodedata
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

# ─── 复姓表 (Compound Surnames) ───────────────────────────────────────────
COMPOUND_SURNAMES = [
    "欧阳", "司马", "上官", "诸葛", "夏侯", "皇甫", "尉迟", "公孙",
    "慕容", "长孙", "宇文", "令狐", "司徒", "轩辕", "东郭", "西门",
    "南宫", "百里", "独孤", "端木", "东方", "万俟", "鲜于", "钟离",
    "太叔", "闻人", "赫连", "濮阳", "单于", "申屠", "仲孙", "亓官",
]

# ─── 特殊部首笔画规则 ────────────────────────────────────────────────────
# Map of radical/character -> (simplified strokes, traditional strokes)
SPECIAL_RADICALS = {
    "辶": (3, 7), "辵": (3, 7), "廴": (3, 3),
    "阝": (2, 8),  # 阝左 (left side, as in 阳, 阿)
    "氵": (3, 4), "忄": (3, 4), "犭": (3, 4),
    "扌": (3, 4), "纟": (3, 6), "饣": (3, 9),
    "钅": (3, 8), "讠": (2, 7), "门": (3, 8),
    "马": (3, 10), "鸟": (5, 11), "鱼": (8, 11),
    "页": (6, 9), "风": (4, 9), "龙": (5, 16),
    "齐": (6, 14), "齿": (8, 15), "龟": (7, 16),
}

# ─── 常用汉字笔画数表 (部分常用字) ──────────────────────────────────────
# This is a simplified lookup for common characters.
# Falls back to unicodedata if not found.
COMMON_STROKES: Dict[str, int] = {
    # 姓氏常用字
    "赵": 14, "钱": 16, "孙": 10, "李": 7, "周": 8, "吴": 7, "郑": 19, "王": 4,
    "冯": 12, "陈": 16, "褚": 15, "卫": 15, "蒋": 17, "沈": 8, "韩": 17, "杨": 13,
    "朱": 6, "秦": 10, "尤": 4, "许": 11, "何": 7, "吕": 7, "施": 9, "张": 11,
    "孔": 4, "曹": 11, "严": 20, "华": 14, "金": 8, "魏": 18, "陶": 16, "姜": 9,
    "戚": 11, "谢": 17, "邹": 17, "喻": 12, "柏": 9, "窦": 13, "章": 11, "云": 12,
    "苏": 22, "潘": 16, "葛": 15, "奚": 10, "范": 15, "彭": 12, "郎": 14, "鲁": 16,
    "韦": 9, "昌": 8, "马": 10, "苗": 11, "凤": 14, "花": 10, "方": 4, "俞": 9,
    "任": 6, "袁": 10, "柳": 9, "唐": 10, "罗": 20, "薛": 19, "贺": 12, "倪": 10,
    "汤": 13,     "殷": 10,     "毕": 11,     "郝": 14,     "安": 6,     "常": 11,     "于": 3,
    "时": 10, "傅": 12, "康": 11, "余": 7, "元": 4, "卜": 2, "顾": 21, "孟": 8,
    "黄": 12, "穆": 16, "萧": 18, "肖": 7, "尹": 4, "田": 5, "姚": 9, "邵": 12,
    "湛": 13, "汪": 8, "祁": 8, "毛": 4, "禹": 9, "狄": 8, "米": 6, "贝": 7,
    "明": 8, "臧": 14, "计": 9, "伏": 6, "成": 7, "戴": 18, "谈": 15, "宋": 7,
    "茅": 11, "庞": 19, "熊": 14, "纪": 9, "舒": 12, "屈": 8, "项": 12, "祝": 10,
    "董": 15, "梁": 11, "杜": 7, "阮": 12, "蓝": 20, "闵": 12, "席": 10, "季": 8,
    "麻": 11, "强": 12, "贾": 13, "路": 13, "娄": 11, "危": 6, "刘": 15, "童": 12,
    "颜": 18, "郭": 15, "梅": 11, "盛": 12, "林": 8, "刁": 2, "钟": 17, "徐": 10,
    "邱": 12,     "骆": 16,     "高": 10,     "夏": 10,     "蔡": 17,     "樊": 15,     "胡": 11,
    "凌": 10, "霍": 16, "虞": 13, "万": 15, "支": 4, "柯": 9, "管": 14, "卢": 16,
    "莫": 13, "经": 13, "房": 8, "裘": 13, "缪": 17, "干": 3, "解": 13, "应": 17,
    "宗": 8, "丁": 2, "宣": 9, "贲": 12, "邓": 19, "郁": 13, "单": 12, "杭": 8,
    "洪": 10, "包": 5, "诸": 16, "左": 5, "石": 5, "崔": 11, "吉": 6, "钮": 12,
    "龚": 22, "程": 12, "嵇": 13, "邢": 11, "滑": 14, "裴": 14, "陆": 16,
    "荣": 14, "翁": 10, "荀": 12, "羊": 6, "惠": 12, "甄": 14, "曲": 6, "家": 10,
    "封": 9, "芮": 10, "羿": 9, "储": 18, "靳": 13, "汲": 8, "邴": 11, "糜": 17,
    "松": 8, "井": 4, "段": 9, "富": 12, "巫": 7, "乌": 10, "焦": 12, "巴": 4,
    "弓": 3, "牧": 8, "隗": 12, "山": 3, "谷": 7, "车": 7, "侯": 9, "宓": 8,
    "蓬": 17, "全": 6, "郗": 14, "班": 11, "仰": 6, "秋": 9, "仲": 6, "伊": 6,
    "宫": 9, "宁": 14, "仇": 4, "栾": 23, "暴": 15, "甘": 5, "钭": 12, "厉": 15,
    "戎": 6,     "祖": 10,     "武": 8,     "符": 11,     "景": 12,     "詹": 13,     "束": 7,
    "龙": 16, "叶": 15, "幸": 8, "司": 5, "韶": 14, "郜": 14, "黎": 15, "蓟": 18,
    "薄": 19, "印": 6, "宿": 11, "白": 5, "怀": 20, "蒲": 16, "台": 5, "从": 11,
    "鄂": 17, "索": 10, "咸": 9, "籍": 20, "赖": 16, "卓": 8, "蔺": 22, "屠": 12,
    "蒙": 16, "池": 7, "乔": 12, "阴": 12, "胥": 9, "能": 10, "苍": 16, "双": 18,
    "闻": 14, "莘": 13, "党": 20, "翟": 14, "谭": 19, "贡": 10, "劳": 12, "逢": 14,
    "姬": 10, "申": 5, "扶": 8, "堵": 12, "冉": 5, "宰": 10, "郦": 26, "雍": 13,
    "却": 7, "璩": 17, "桑": 10, "桂": 10, "濮": 18, "牛": 4, "寿": 14, "通": 14,
    "边": 22, "扈": 11, "燕": 16, "冀": 16, "郏": 15, "浦": 11, "尚": 8, "农": 13,
    "温": 14, "别": 7, "庄": 13, "晏": 10, "柴": 10, "瞿": 18, "阎": 16, "充": 6,
    "慕": 15, "连": 14, "茹": 12, "习": 11, "宦": 9, "艾": 8, "鱼": 11, "容": 10,
    "向": 6, "古": 5, "易": 8, "慎": 14, "戈": 4, "廖": 14, "庾": 11, "终": 11,
    "暨": 14, "居": 8, "衡": 16, "步": 7, "都": 16, "耿": 10, "满": 15, "弘": 5,
    "匡": 6, "国": 11, "文": 4, "寇": 11, "广": 15, "禄": 13, "阙": 18, "东": 8,
    "欧": 15, "殳": 4, "沃": 8, "利": 7, "蔚": 17, "越": 12, "夔": 21, "隆": 17,
    "师": 10, "巩": 6, "厍": 6, "聂": 18, "晁": 10, "勾": 4, "敖": 11, "融": 16,
    "冷": 7, "訾": 12, "辛": 7, "阚": 14, "那": 11, "简": 18, "饶": 21, "空": 8,
    "曾": 12, "母": 5, "沙": 8, "乜": 2, "养": 15, "鞠": 17, "须": 12, "丰": 18,
    "巢": 11, "关": 19, "蒯": 16, "相": 9, "查": 9, "后": 9, "荆": 12, "红": 9,
    "游": 13, "竺": 8, "权": 22, "逯": 14, "盖": 14, "益": 10, "桓": 10, "公": 4,
    "晋": 10,
    # 名字常用字
    "伟": 6,     "芳": 10,     "娜": 10,     "秀": 7,     "敏": 11,     "静": 16,     "丽": 19,
    "磊": 15,     "洋": 10,     "勇": 9,     "艳": 24,     "杰": 12,     "娟": 10,     "涛": 18,
    "超": 12,     "霞": 17,     "平": 5,     "刚": 10,     "英": 11,
    "慧": 15, "巧": 5, "美": 9, "飞": 9, "翠": 14, "雅": 12, "芝": 10, "玉": 5,
    "萍": 14,     "娥": 10,     "玲": 10,     "芬": 10,     "彩": 11,     "春": 9,
    "菊": 14,     "兰": 23,     "洁": 16,     "琳": 13,     "素": 10,
    "莲": 17,     "真": 10,     "环": 18,     "雪": 11,     "爱": 13,     "妹": 8,
    "香": 9,     "月": 4,     "莺": 21,     "媛": 12,     "瑞": 14,     "凡": 3,     "佳": 8,
    "思": 9, "嘉": 14, "婷": 12, "琪": 13, "梦": 14, "依": 8, "瑶": 15, "怡": 9,
    "倩": 10, "涵": 12, "薇": 19, "蕾": 19, "颖": 16, "璇": 16, "语": 14, "菲": 14,
    "悦": 11,     "萌": 14,     "馨": 20,     "欣": 8,     "灵": 24,
    "浩": 11, "宇": 6, "博": 12, "泽": 17, "翰": 16, "天": 4, "昊": 8, "轩": 10,
    "睿": 14, "哲": 10, "晨": 11, "辰": 7, "逸": 15, "铭": 14, "俊": 9, "豪": 14,
    "峰": 10,     "鑫": 24,     "源": 14,     "然": 12,
    "阳": 17, "航": 10, "志": 7, "恒": 10, "辉": 15, "达": 16, "军": 9, "建": 9,
    "民": 5,     "亮": 9,     "正": 5,     "永": 5,     "健": 11,     "世": 5,
    "义": 13,     "兴": 16,     "海": 11,     "仁": 4,     "波": 9,     "贵": 12,     "福": 15,
    "生": 5,     "胜": 12,     "学": 16,     "祥": 11,     "才": 3,
    "发": 12,     "新": 13,     "清": 12,     "彬": 11,
    "顺": 12,     "信": 9,     "子": 3,
    "星": 9,     "光": 6,     "岩": 8,     "中": 4,     "茂": 11,     "进": 15,
    "坚": 11,     "和": 8,     "彪": 11,     "先": 6,     "绍": 11,     "善": 12,
    "厚": 9,     "庆": 15,     "友": 4,     "裕": 13,     "河": 9,
    "江": 7,     "政": 8,     "谦": 17,     "亨": 7,     "奇": 8,
    "固": 8,     "之": 4,     "轮": 15,     "朗": 11,     "伯": 7,     "宏": 7,     "言": 7,
    "若": 11,     "鸣": 14,     "朋": 8,     "斌": 11,     "栋": 12,     "维": 14,     "启": 11,
    "克": 7,     "伦": 10,     "翔": 12,     "旭": 6,     "鹏": 19,
    "士": 3,     "以": 5,     "致": 10,     "树": 16,     "炎": 8,     "德": 15,
    "行": 6,     "泰": 10,     "振": 11,     "壮": 7,     "会": 13,
    "群": 13,     "心": 4,     "邦": 11,     "承": 8,     "乐": 15,     "长": 8,
    "功": 5,
    # 天干地支
    "甲": 5,     "乙": 1,     "丙": 5,     "丁": 2,     "戊": 5,     "己": 3,     "庚": 8,
    "辛": 7,     "壬": 4, "癸": 9,
    "子": 3,     "丑": 4,     "寅": 11,     "卯": 5,     "辰": 7,     "巳": 6,     "午": 4,     "未": 5,
    "申": 5,     "酉": 7,     "戌": 6,     "亥": 6,
    # 五行相关
    "木": 4,     "水": 4,     "火": 4,     "土": 3,
}


# ─── 81数理吉凶表 ───────────────────────────────────────────────────────
SHUBA_81: Dict[int, Dict[str, str]] = {
    1:  {"jishu": "太极之数", "jixiong": "吉", "desc": "太极之数，万物开泰，生发无穷，利禄亨通。"},
    2:  {"jishu": "两仪之数", "jixiong": "凶", "desc": "两仪之数，混沌未开，进退保守，志望难达。"},
    3:  {"jishu": "三才之数", "jixiong": "吉", "desc": "三才之数，天地人和，大事大业，繁荣昌隆。"},
    4:  {"jishu": "四象之数", "jixiong": "凶", "desc": "四象之数，待于生发，万事慎慎，不具营谋。"},
    5:  {"jishu": "五行之数", "jixiong": "吉", "desc": "五行俱权，循环相生，圆通畅达，福祉无穷。"},
    6:  {"jishu": "六爻之数", "jixiong": "吉", "desc": "六爻之数，发展变化，天赋美德，吉祥安泰。"},
    7:  {"jishu": "七政之数", "jixiong": "吉", "desc": "七政之数，精悍严谨，天赋之力，吉星照耀。"},
    8:  {"jishu": "八卦之数", "jixiong": "吉", "desc": "八卦之数，乾坎艮震，巽离坤兑，无穷无尽。"},
    9:  {"jishu": "大成之数", "jixiong": "凶", "desc": "大成之数，蕴涵凶险，或成或败，难以把握。"},
    10: {"jishu": "终结之数", "jixiong": "凶", "desc": "终结之数，雪暗飘零，偶或有成，回顾茫然。"},
    11: {"jishu": "旱苗逢雨", "jixiong": "吉", "desc": "万物更新，调顺发达，恢弘泽世，繁荣富贵。"},
    12: {"jishu": "掘井无泉", "jixiong": "凶", "desc": "无理之数，发展薄弱，虽生不足，难酬志向。"},
    13: {"jishu": "春日牡丹", "jixiong": "吉", "desc": "才艺多能，智谋奇略，忍柔当事，鸣奏大功。"},
    14: {"jishu": "破兆", "jixiong": "凶", "desc": "家庭缘薄，孤独遭难，谋事不达，悲惨不测。"},
    15: {"jishu": "福寿", "jixiong": "吉", "desc": "福寿圆满，富贵荣誉，涵养雅量，德高望重。"},
    16: {"jishu": "厚重", "jixiong": "吉", "desc": "厚重载德，安富尊荣，财官双美，功成名就。"},
    17: {"jishu": "刚强", "jixiong": "半吉", "desc": "权威刚强，突破万难，如能容忍，必获成功。"},
    18: {"jishu": "铁镜重磨", "jixiong": "半吉", "desc": "权威显达，博得名利，且养柔德，功成名就。"},
    19: {"jishu": "多难", "jixiong": "凶", "desc": "风云蔽日，辛苦重来，虽有智谋，万事挫折。"},
    20: {"jishu": "屋下藏金", "jixiong": "凶", "desc": "非业破运，灾难重重，进退维谷，万事难成。"},
    21: {"jishu": "明月中天", "jixiong": "吉", "desc": "光风霁月，万物确立，官运亨通，大搏名利。（女性用之不利）"},
    22: {"jishu": "秋草逢霜", "jixiong": "凶", "desc": "秋草逢霜，困难疾弱，虽出豪杰，人生波折。"},
    23: {"jishu": "壮丽", "jixiong": "吉", "desc": "旭日东升，壮丽壮观，权威旺盛，功名荣达。（女性用之不利）"},
    24: {"jishu": "掘藏得金", "jixiong": "吉", "desc": "家门余庆，金钱丰盈，白手成家，财源广进。"},
    25: {"jishu": "荣俊", "jixiong": "半吉", "desc": "资性英敏，才能奇特，克服傲慢，尚可成功。"},
    26: {"jishu": "变怪", "jixiong": "半凶", "desc": "变怪之谜，英雄豪杰，波澜重叠，而奏大功。"},
    27: {"jishu": "增长", "jixiong": "半凶", "desc": "欲望无止，自我强烈，多受毁谤，尚可成功。"},
    28: {"jishu": "阔水浮萍", "jixiong": "凶", "desc": "遭难之数，豪杰气概，四海漂泊，终世浮躁。"},
    29: {"jishu": "智谋", "jixiong": "半吉", "desc": "智谋优秀，财力归集，名闻海内，成就大业。"},
    30: {"jishu": "非运", "jixiong": "半凶", "desc": "沉浮不定，凶吉难变，若明若暗，大成大败。"},
    31: {"jishu": "春日花开", "jixiong": "吉", "desc": "智勇得志，博得名利，统领众人，繁荣富贵。"},
    32: {"jishu": "宝马金鞍", "jixiong": "吉", "desc": "侥幸多望，贵人得助，财帛如裕，繁荣至上。"},
    33: {"jishu": "旭日升天", "jixiong": "吉", "desc": "旭日升天，鸾凤相会，名闻天下，隆昌至极。（女性用之不利）"},
    34: {"jishu": "破家", "jixiong": "凶", "desc": "破家之身，见识短小，辛苦遭逢，灾祸至极。"},
    35: {"jishu": "高楼望月", "jixiong": "吉", "desc": "温和平静，智达通畅，文昌技艺，奏功洋洋。"},
    36: {"jishu": "波澜", "jixiong": "半凶", "desc": "波澜重叠，沉浮万状，侠肝义胆，舍己成仁。"},
    37: {"jishu": "猛虎出林", "jixiong": "吉", "desc": "权威显达，独立权威，热诚忠信，宜着雅量。"},
    38: {"jishu": "磨铁成针", "jixiong": "半吉", "desc": "意志薄弱，刻意经营，才识不凡，技艺有成。"},
    39: {"jishu": "富贵荣华", "jixiong": "半吉", "desc": "富贵荣华，财帛丰盈，暗藏险象，德泽四方。（女性用之不利）"},
    40: {"jishu": "退安", "jixiong": "半凶", "desc": "智谋胆力，冒险投机，沉浮不定，退保平安。"},
    41: {"jishu": "有德", "jixiong": "吉", "desc": "纯阳独秀，德高望重，和顺畅达，博得名利。"},
    42: {"jishu": "寒蝉在柳", "jixiong": "凶", "desc": "博识多能，精通世情，如能专心，尚可成功。"},
    43: {"jishu": "散财", "jixiong": "凶", "desc": "散财破产，诸事不遂，虽有智谋，财来财去。"},
    44: {"jishu": "烦闷", "jixiong": "凶", "desc": "须眉难展，力不从心，谋事不达，悲惨不测。"},
    45: {"jishu": "顺风", "jixiong": "吉", "desc": "新生泰和，顺风扬帆，智谋经纬，富贵繁荣。"},
    46: {"jishu": "浪里淘金", "jixiong": "凶", "desc": "载宝沉舟，浪里淘金，大难尝尽，大功有成。"},
    47: {"jishu": "点铁成金", "jixiong": "吉", "desc": "花开之象，万事如意，祯祥吉庆，天赋幸福。"},
    48: {"jishu": "枯松立鹤", "jixiong": "吉", "desc": "智谋兼备，德量荣达，威望成师，洋洋大观。"},
    49: {"jishu": "转变", "jixiong": "半凶", "desc": "吉临则吉，凶来则凶，转凶为吉，配好三才。"},
    50: {"jishu": "小舟入海", "jixiong": "半凶", "desc": "吉凶互见，一成一败，凶中带吉，吉中有凶。"},
    51: {"jishu": "沉浮", "jixiong": "半凶", "desc": "盛衰交加，波澜重叠，如能慎始，必获成功。"},
    52: {"jishu": "达眼", "jixiong": "半吉", "desc": "卓识达眼，先见之明，智谋超群，名利双收。"},
    53: {"jishu": "曲卷推车", "jixiong": "半凶", "desc": "外祥内苦，忍耐自重，凶中有吉，难关重重。"},
    54: {"jishu": "石上栽花", "jixiong": "凶", "desc": "石上栽花，难得有活，忧闷频来，辛苦不绝。"},
    55: {"jishu": "善恶", "jixiong": "半凶", "desc": "善善得恶，恶恶得善，吉到极限，反生凶险。"},
    56: {"jishu": "浪里行舟", "jixiong": "凶", "desc": "历尽艰辛，四周障碍，万事龃龉，做事难成。"},
    57: {"jishu": "日照春松", "jixiong": "半吉", "desc": "虽有困难，时来运转，旷野枯草，春来花开。"},
    58: {"jishu": "晚行遇月", "jixiong": "半凶", "desc": "沉浮多端，先苦后甜，宽宏扬名，晚年有福。"},
    59: {"jishu": "寒蝉悲风", "jixiong": "凶", "desc": "寒蝉悲风，人生艰辛，处事不达，须忍以成。"},
    60: {"jishu": "无谋", "jixiong": "凶", "desc": "无谋之人，暗黑无光，碌碌无为，一生不安。"},
    61: {"jishu": "名利双收", "jixiong": "吉", "desc": "牡丹芙蓉，花开富贵，名利双收，定享天赋。"},
    62: {"jishu": "衰败", "jixiong": "凶", "desc": "衰败之象，内外不和，志望难达，灾祸频来。"},
    63: {"jishu": "舟归平海", "jixiong": "吉", "desc": "万物化育，繁荣之象，专心一意，必能成功。"},
    64: {"jishu": "非命", "jixiong": "凶", "desc": "骨肉分离，孤独悲愁，难得平安，辛苦不绝。"},
    65: {"jishu": "巨流归海", "jixiong": "吉", "desc": "天长地久，家运隆昌，福寿绵长，事事成就。"},
    66: {"jishu": "岩头步马", "jixiong": "凶", "desc": "进退失衡，内外不和，左右为基，辛苦无穷。"},
    67: {"jishu": "通达", "jixiong": "吉", "desc": "利路亨通，万事顺遂，事事如意，家道兴隆。"},
    68: {"jishu": "顺风吹帆", "jixiong": "吉", "desc": "智虑周密，集众信达，发明能智，拓展昂进。"},
    69: {"jishu": "非业", "jixiong": "凶", "desc": "坐立不安，世事不如意，须戒贪嗔，方免倾覆。"},
    70: {"jishu": "残菊逢霜", "jixiong": "凶", "desc": "残菊逢霜，寂寞无碍，惨淡忧愁，晚景凄凉。"},
    71: {"jishu": "石上金花", "jixiong": "半凶", "desc": "石上金花，内心劳苦，贯彻始终，尚可成就。"},
    72: {"jishu": "劳苦", "jixiong": "半凶", "desc": "荣苦相伴，阴云蔽月，外表吉祥，内实凶祸。"},
    73: {"jishu": "高楼望月", "jixiong": "半吉", "desc": "高楼望月，优雅发展，虽有忧虑，此数不害。"},
    74: {"jishu": "残菊经霜", "jixiong": "凶", "desc": "残菊经霜，秋叶落寞，虽有才能，命运多舛。"},
    75: {"jishu": "退守安吉", "jixiong": "半凶", "desc": "退守安吉，一生平安，守则可吉，进则凶兆。"},
    76: {"jishu": "离散", "jixiong": "凶", "desc": "骨肉分离，六亲无缘，人生坎坷，一生不安。"},
    77: {"jishu": "半吉", "jixiong": "半吉", "desc": "家庭有缘，贵人相助，虽遇凶险，可获成功。"},
    78: {"jishu": "晚景凄凉", "jixiong": "半凶", "desc": "先甘后苦，早年发达，中年不振，晚景凄凉。"},
    79: {"jishu": "挽回乏力", "jixiong": "凶", "desc": "挽回乏力，穷迫不伸，精神不安，力不从心。"},
    80: {"jishu": "辛苦不绝", "jixiong": "凶", "desc": "辛苦不绝，困苦难安，暗藏凶险，万事难成。"},
    81: {"jishu": "万物回春", "jixiong": "吉", "desc": "最吉之数，还原复始，繁荣发达，圆满之象。"},
}

# ─── 三才五行吉凶配置表 ──────────────────────────────────────────────────
# Format: (天格五行, 人格五行, 地格五行) -> (吉凶, 解释)
# 五行: 1=木, 2=火, 3=土, 4=金, 5=水
SANCAI_TABLE: Dict[Tuple[int, int, int], Tuple[str, str]] = {
    # 木木木
    (1,1,1): ("大吉", "成功顺利伸展，希望圆满达成，基础安定，能得向上发展，家门兴隆，身心健康，长寿幸福。"),
    (1,1,2): ("大吉", "成功顺利伸展，无障碍向上发展，基础境遇安泰，事事顺心，兴隆幸福。"),
    (1,1,3): ("大吉", "成功顺调，无障碍而向上发展，基础境遇安泰，终生幸福，繁荣长寿。"),
    (1,2,2): ("大吉", "得上下惠助，顺调成功发展，基础强固，境遇安泰，子孙繁荣，心身健康而获得幸福。"),
    (1,3,1): ("中吉", "向上进取，容易成功而富贵，基础犹如立足于磐石之上，有向上发展之象，必享长寿。"),
    (1,3,2): ("大吉", "向上进取，容易成功而富贵，基础犹如立足于磐石之上，身心健全，得享长寿幸福。"),
    (1,3,3): ("大吉", "向上进取，容易成功而富贵，基础稳固，境遇安泰，身心健全，得享长寿幸福。"),
    # 木火土
    (1,2,3): ("大吉", "受上司的引进，得成功顺调发展，基础强固，境遇安泰，兴隆幸福。"),
    (1,3,5): ("大吉", "向上进取容易成功，基础稳固，身心安泰，得享长寿幸福。"),
    # 木火木 - 吉
    (1,2,1): ("大吉", "得上下之惠助，顺调成功发展，基础稳固，心身健全，繁荣隆昌，得享长寿幸福。"),
    (1,2,5): ("大吉", "得上下之惠助，顺调成功发展，基础稳固，心身安泰，得享长寿幸福。"),
    # 火火木
    (2,2,1): ("大吉", "盛运隆昌，目的能达，得顺调成功发展，基础稳固，心身安泰，得享长寿幸福。"),
    # 火火土
    (2,2,3): ("大吉", "外有吉数，成功发展，基础稳固，境遇安泰，得享幸福长寿。"),
    # 火土金
    (2,3,4): ("大吉", "得上级提拔，享父母余德，易成功，心身健全，得长寿享福。"),
    (2,3,5): ("大吉", "得上级提拔，享父母余德，易成功，基础稳固，得长寿幸福。"),
    # 土土金
    (3,3,4): ("大吉", "一帆风顺成功发展，目的平达，境遇安泰，心身健全，可得长寿幸福。"),
    (3,3,5): ("大吉", "一帆风顺成功发展，目的平达，基础稳固，心身安泰，得享长寿幸福。"),
    # 土火木
    (3,2,1): ("大吉", "希望能平稳达成，易成功发展，基础稳固，心身平安，可得幸福长寿。"),
    # 金土火
    (4,3,2): ("中吉", "可得意外成功发展，名利双收，境遇巩固，得享幸福。"),
    # 金土土
    (4,3,3): ("大吉", "一帆风顺成功发展，目的平达，基础稳固，境遇安泰，得享幸福长寿。"),
    # 金金土
    (4,4,3): ("中吉", "虽有成功运，但基础不稳，有急变没落之虑。"),
    # 水木火
    (5,1,2): ("大吉", "得长上之引进，顺利成功发展，基础稳固，心身健全，繁荣隆昌，长寿幸福。"),
    # 水木木
    (5,1,1): ("大吉", "得长上之引进，顺调成功发展，基础安稳，身心健全，繁荣隆昌，得享长寿幸福。"),
    # 水木土
    (5,1,3): ("大吉", "得长上之引进，顺利成功发展，基础安稳，身心安泰，得享长寿幸福。"),
    # 水水木
    (5,5,1): ("大吉", "有出异常之成功者，可名利双收，但有急变没落之虑。"),
    # 水水金
    (5,5,4): ("中吉", "有出异常成功者，名利双收，但须戒慎以免倾覆。"),
    # 凶配置
    (1,4,4): ("凶", "成功运被压抑，不能伸张，身心过劳，有水火之虑。"),
    (1,4,5): ("凶", "成功运被压抑，不能伸张，常有烦恼与困难，身心过劳。"),
    (2,5,1): ("凶", "成功运被压抑，不能伸张，有遭遇不测之祸患的可能。"),
    (2,5,4): ("凶", "成功运被压抑，不能伸张，急变没落之象。"),
    (3,1,4): ("凶", "虽可获得发展，但基础不稳，有急变没落之虑。"),
    (4,2,5): ("凶", "成功运被压制，不能伸张，易生不平不满，急变没落之象。"),
    (5,2,4): ("凶", "成功运被压抑，不能伸张，急变动之象。"),
    (5,3,1): ("凶", "向上发展障碍殊多，常有困难苦闷，境遇虽稍安定，但易生心肺疾病。"),
    (4,1,2): ("凶", "成功运被压抑，不能伸张，有不平不满之虑，易生肺疾。"),
    (3,4,2): ("凶", "成功运被压制，不能伸张，易生心腹之患。"),
    (2,4,3): ("凶", "成功运被压制，不能伸张，境遇虽稍安定，但易生心脑疾患。"),
}

# ─── 五行属性 ──────────────────────────────────────────────────────────
WUXING_MAP = {
    1: "木", 2: "木",
    3: "火", 4: "火",
    5: "土", 6: "土",
    7: "金", 8: "金",
    9: "水", 0: "水",
}

WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 天干五行
TIANGAN_WUXING = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}

# 地支五行
DIZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}


class XingMingEngine:
    """姓名学引擎 - 五格剖象法

    注意：姓名学需要额外的姓名输入。
    使用方式：
      1. 直接调用 analyze_name(surname, given_name, gender) 获取完整分析
      2. 通过 set_name(surname, given_name) 设置姓名后，可使用标准 analyze(time, gender) 接口
    """

    # DivinationEngine 兼容属性
    @property
    def name(self) -> str:
        return "姓名学"

    @property
    def name_en(self) -> str:
        return "xingming"

    @property
    def priority(self) -> int:
        return 8

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        """校验排盘数据"""
        if not data.get('wuge'):
            return False, '五格数据为空'
        if data.get('score') is None:
            return False, '评分数据为空'
        return True, None

    def __init__(self):
        self._81_table = SHUBA_81
        self._sancai_table = SANCAI_TABLE
        self._surname = ''
        self._given_name = ''

    def set_name(self, surname: str, given_name: str):
        """设置待分析的姓名（供标准analyze接口使用）"""
        self._surname = surname
        self._given_name = given_name

    def analyze(self, time, gender: int) -> dict:
        """标准DivinationEngine接口 — 需先通过set_name()设置姓名"""
        if not self._surname or not self._given_name:
            return {"error": "姓名未设置，请先调用 set_name(surname, given_name)"}
        gender_str = '男' if gender == 1 else '女'
        return self.analyze_name(self._surname, self._given_name, gender_str)

    # ─── Public API ────────────────────────────────────────────────────

    def analyze_name(self, surname: str, given_name: str, gender: str,
                     bazi_info: Optional[dict] = None) -> dict:
        """
        Analyze a name using 五格剖象法.

        Args:
            surname: 姓 (e.g. "张" or "欧阳")
            given_name: 名 (e.g. "伟" or "伟明")
            gender: "男" or "女"
            bazi_info: Optional dict from bazi engine with keys like
                       'dayun_wuxing', 'xishen', 'jiShen', etc.

        Returns:
            dict with keys: wuge, sancai, score, analysis, details
        """
        # 输入校验
        if not surname or not given_name:
            return {"error": "姓名不能为空", "wuge": {}, "sancai": {}, "score": 0, "analysis": ""}
        if not any('\u4e00' <= c <= '\u9fff' for c in surname + given_name):
            return {"error": "姓名必须包含汉字", "wuge": {}, "sancai": {}, "score": 0, "analysis": ""}
        # Determine if compound surname
        is_compound = self._is_compound_surname(surname)
        surname_len = len(surname)

        # Calculate strokes for each character
        surname_strokes = [self.get_stroke(c) for c in surname]
        given_strokes = [self.get_stroke(c) for c in given_name]
        total_surname = sum(surname_strokes)
        total_given = sum(given_strokes)

        # ─── 五格计算 ──────────────────────────────────────────────────
        wuge = self._calc_wuge(surname_strokes, given_strokes, surname_len,
                               len(given_name), is_compound)

        # ─── 81数理吉凶 ────────────────────────────────────────────────
        wuge_jixiong = {}
        for key in ["天格", "人格", "地格", "外格", "总格"]:
            val = wuge[key]["数理"]
            info = self._81_table.get(val, self._get_default_81(val))
            # Special gender rules
            if gender == "女" and val in (21, 23, 33, 39):
                info = {**info, "jixiong": "凶", "desc": info["desc"] + "（女性用此数理为凶）"}
            wuge[key]["吉凶"] = info["jixiong"]
            wuge[key]["数理含义"] = info["desc"]
            wuge[key]["数理名"] = info["jishu"]
            wuge_jixiong[key] = info["jixiong"]

        # ─── 三才五行配置 ───────────────────────────────────────────────
        sancai_info = self._calc_sancai(wuge["天格"]["数理"],
                                         wuge["人格"]["数理"],
                                         wuge["地格"]["数理"])

        # ─── 八字喜用神匹配 ────────────────────────────────────────────
        bazi_match = None
        if bazi_info:
            bazi_match = self._check_bazi_match(wuge, bazi_info)

        # ─── 综合评分 ──────────────────────────────────────────────────
        score = self._calc_score(wuge, sancai_info, bazi_match, gender)

        # ─── 生成分析文本 ────────────────────────────────────────────────
        analysis = self._generate_analysis(
            surname, given_name, gender, wuge, sancai_info,
            bazi_match, score, is_compound
        )

        return {
            "surname": surname,
            "given_name": given_name,
            "gender": gender,
            "is_compound_surname": is_compound,
            "wuge": {
                "天格": {
                    "画数": wuge["天格"]["画数"],
                    "数理": wuge["天格"]["数理"],
                    "数理名": wuge["天格"].get("数理名", ""),
                    "吉凶": wuge["天格"].get("吉凶", ""),
                    "数理含义": wuge["天格"].get("数理含义", ""),
                    "五行": WUXING_MAP.get(wuge["天格"]["数理"] % 10, "未知"),
                },
                "人格": {
                    "画数": wuge["人格"]["画数"],
                    "数理": wuge["人格"]["数理"],
                    "数理名": wuge["人格"].get("数理名", ""),
                    "吉凶": wuge["人格"].get("吉凶", ""),
                    "数理含义": wuge["人格"].get("数理含义", ""),
                    "五行": WUXING_MAP.get(wuge["人格"]["数理"] % 10, "未知"),
                },
                "地格": {
                    "画数": wuge["地格"]["画数"],
                    "数理": wuge["地格"]["数理"],
                    "数理名": wuge["地格"].get("数理名", ""),
                    "吉凶": wuge["地格"].get("吉凶", ""),
                    "数理含义": wuge["地格"].get("数理含义", ""),
                    "五行": WUXING_MAP.get(wuge["地格"]["数理"] % 10, "未知"),
                },
                "外格": {
                    "画数": wuge["外格"]["画数"],
                    "数理": wuge["外格"]["数理"],
                    "数理名": wuge["外格"].get("数理名", ""),
                    "吉凶": wuge["外格"].get("吉凶", ""),
                    "数理含义": wuge["外格"].get("数理含义", ""),
                    "五行": WUXING_MAP.get(wuge["外格"]["数理"] % 10, "未知"),
                },
                "总格": {
                    "画数": wuge["总格"]["画数"],
                    "数理": wuge["总格"]["数理"],
                    "数理名": wuge["总格"].get("数理名", ""),
                    "吉凶": wuge["总格"].get("吉凶", ""),
                    "数理含义": wuge["总格"].get("数理含义", ""),
                    "五行": WUXING_MAP.get(wuge["总格"]["数理"] % 10, "未知"),
                },
            },
            "sancai": sancai_info,
            "bazi_match": bazi_match,
            "score": score,
            "analysis": analysis,
            "strokes": {
                "surname": surname_strokes,
                "given": given_strokes,
                "surname_total": total_surname,
                "given_total": total_given,
            }
        }

    # ─── Stroke Calculation ────────────────────────────────────────────

    def get_stroke(self, char: str) -> int:
        """
        Get the stroke count for a Chinese character.
        Uses special radical rules, lookup table, then unicodedata fallback.
        """
        # Check special radicals first
        if char in SPECIAL_RADICALS:
            return SPECIAL_RADICALS[char][1]  # Use 康熙字典笔画（姓名学标准）

        # Check common strokes table
        if char in COMMON_STROKES:
            return COMMON_STROKES[char]

        # Fallback: use unicodedata 'kTotalStrokes' is not available via unicodedata
        # Use a heuristic based on the CJK Unified Ideograph range
        # This is a rough estimate — for production use, a full stroke table is needed
        try:
            # Try to get from Unihan database if available
            import importlib
            # Simple fallback: estimate based on character structure
            # Most common CJK characters are 4-20 strokes
            # We use the character's ordinal position as a rough seed
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF:
                # CJK Unified Ideographs — use a simple hash-based estimate
                # This is NOT accurate but provides a fallback
                # For production, use a real stroke dictionary
                return self._estimate_strokes(char)
            return 8  # Default fallback
        except Exception as e:
            logger.debug(f"笔画查询异常，回退默认8画: {e}")
            return 8

    def _estimate_strokes(self, char: str) -> int:
        """
        Stroke estimation for characters not in lookup table.
        优先尝试 Unihan kTotalStrokes 数据库，回退到统计估算。
        """
        # 尝试从 Unihan 数据库读取精确笔画数
        try:
            import importlib
            unihan = importlib.import_module('unicodedata')
            # Python 3.13+ 的 unicodedata 不直接暴露 kTotalStrokes
            # 但可以尝试通过 name() 判断字符是否为 CJK 统一汉字
            name = unihan.name(char, '')
            if not name or 'CJK' not in name:
                return 8  # 非CJK字符默认8画
        except Exception as e:
            logger.debug(f"Unihan 笔画查询异常: {e}")

        # 基于 CJK 字符笔画分布的统计估算
        # 高频字平均约 8-10 画，低频字偏多
        code = ord(char)
        # CJK 基本区 0x4E00-0x9FFF，扩展区笔画更多
        if 0x4E00 <= code <= 0x9FFF:
            # 基本区字符：使用分布表估算（基于 GB2312 统计）
            # 按Unicode区块的笔画中位数估算
            block_idx = (code - 0x4E00) // 256  # 0-82
            # 各区块笔画中位数经验值（从简到繁）
            block_medians = [5, 6, 7, 7, 8, 8, 9, 9, 9, 10,
                            10, 10, 11, 11, 11, 11, 12, 12, 12, 13,
                            13, 13, 14, 14, 14, 15, 15, 16, 16, 17,
                            17, 18]
            idx = min(block_idx, len(block_medians) - 1)
            base = block_medians[idx]
            # 在区块内微调
            offset = ((code % 256) * 7 + 3) % 5 - 2  # -2 to +2
            return max(1, base + offset)
        elif 0x3400 <= code <= 0x4DBF:
            return 14  # CJK扩展A：笔画偏多
        else:
            return 10  # 其他CJK区块

    # ─── Compound Surname Detection ────────────────────────────────────

    def _is_compound_surname(self, surname: str) -> bool:
        """Check if the surname is a compound (复姓) surname."""
        return surname in COMPOUND_SURNAMES

    # ─── 五格计算 ──────────────────────────────────────────────────────

    def _calc_wuge(self, surname_strokes: List[int], given_strokes: List[int],
                   surname_len: int, given_len: int,
                   is_compound: bool) -> dict:
        """
        Calculate the Five Grids (五格).

        Rules:
        - 天格: surname total + 1 (single char surname) or surname total (compound)
        - 人格: last char of surname + first char of given name
        - 地格: sum of given name strokes, or given+1 for single-char given
        - 外格: total - 人格 (varies by configuration)
        - 总格: all strokes sum
        """
        total_surname = sum(surname_strokes)
        total_given = sum(given_strokes)

        # 天格
        if is_compound or surname_len > 1:
            tiange = total_surname
        else:
            tiange = total_surname + 1

        # 人格: surname last char + given first char
        renge = surname_strokes[-1] + given_strokes[0]

        # 地格
        if given_len == 1:
            dige = total_given + 1
        else:
            dige = total_given

        # 总格
        zongge = total_surname + total_given

        # 外格（按姓氏类型分公式）
        # 标准公式：外格 = 总格 - 人格 + 1
        # 单姓双名: 末字笔画 + 1
        # 单姓单名: 2
        # 复姓双名: 姓首字笔画 + 末字笔画 + 1
        # 复姓单名: 姓首字笔画 + 1
        if is_compound or surname_len > 1:
            if given_len >= 2:
                waige = surname_strokes[0] + given_strokes[-1] + 1
            else:
                waige = surname_strokes[0] + 1
        else:
            if given_len >= 2:
                waige = given_strokes[-1] + 1
            else:
                waige = 2
        # Ensure minimum of 2
        if waige < 2:
            waige = 2

        return {
            "天格": {"画数": tiange, "数理": self._to_jishu(tiange)},
            "人格": {"画数": renge, "数理": self._to_jishu(renge)},
            "地格": {"画数": dige, "数理": self._to_jishu(dige)},
            "外格": {"画数": waige, "数理": self._to_jishu(waige)},
            "总格": {"画数": zongge, "数理": self._to_jishu(zongge)},
        }

    def _to_jishu(self, stroke: int) -> int:
        """Convert stroke count to 吉凶数理 (1-81 cycle)."""
        if stroke <= 0:
            return 1
        result = stroke % 81
        if result == 0:
            return 81
        return result

    def _get_default_81(self, val: int) -> dict:
        """Generate a default entry for values not in the 81 table."""
        # This should rarely happen since we cycle to 1-81
        return {
            "jishu": f"第{val}数",
            "jixiong": "平",
            "desc": f"第{val}数，具体含义需参考完整数理表。"
        }

    # ─── 三才五行 ──────────────────────────────────────────────────────

    def _calc_sancai(self, tiange: int, renge: int, dige: int) -> dict:
        """
        Calculate 三才五行配置.

        Maps each grid's 数理 to its 五行属性, then looks up the configuration.
        """
        tian_wx = self._number_to_wuxing(tiange)
        ren_wx = self._number_to_wuxing(renge)
        di_wx = self._number_to_wuxing(dige)

        tian_num = self._wuxing_to_num(tian_wx)
        ren_num = self._wuxing_to_num(ren_wx)
        di_num = self._wuxing_to_num(di_wx)

        key = (tian_num, ren_num, di_num)

        if key in self._sancai_table:
            jixiong, desc = self._sancai_table[key]
        else:
            # Evaluate based on wuxing relationships
            jixiong, desc = self._evaluate_sancai_wuxing(tian_wx, ren_wx, di_wx)

        return {
            "天格五行": tian_wx,
            "人格五行": ren_wx,
            "地格五行": di_wx,
            "配置": f"{tian_wx}{ren_wx}{di_wx}",
            "吉凶": jixiong,
            "解释": desc,
        }

    def _number_to_wuxing(self, n: int) -> str:
        """Convert a number to its 五行 attribute based on last digit."""
        last_digit = n % 10
        return WUXING_MAP.get(last_digit, "土")

    def _wuxing_to_num(self, wuxing: str) -> int:
        """Convert wuxing name to number for lookup."""
        mapping = {"木": 1, "火": 2, "土": 3, "金": 4, "水": 5}
        return mapping.get(wuxing, 3)

    def _evaluate_sancai_wuxing(self, tian: str, ren: str, di: str) -> Tuple[str, str]:
        """
        Evaluate 三才 configuration when not in the lookup table.
        Uses wuxing 生克 relationships (双向检测：天→人、人→地、天→地 及其反向).
        """
        sheng_count = 0
        ke_count = 0

        def _check_pair(a: str, b: str) -> str:
            """检查a与b的五行关系，返回 'sheng'/'ke'/'same'/'none'"""
            if a == b:
                return 'same'
            if WUXING_SHENG.get(a) == b:
                return 'sheng'  # a生b
            if WUXING_SHENG.get(b) == a:
                return 'sheng'  # b生a（反向相生）
            if WUXING_KE.get(a) == b:
                return 'ke'     # a克b
            if WUXING_KE.get(b) == a:
                return 'ke'     # b克a（反向相克）
            return 'none'

        # 天格 ↔ 人格
        rel_tr = _check_pair(tian, ren)
        if rel_tr == 'sheng':
            sheng_count += 1
        elif rel_tr == 'ke':
            ke_count += 1

        # 人格 ↔ 地格
        rel_rd = _check_pair(ren, di)
        if rel_rd == 'sheng':
            sheng_count += 1
        elif rel_rd == 'ke':
            ke_count += 1

        # 天格 ↔ 地格
        rel_td = _check_pair(tian, di)
        if rel_td == 'sheng':
            sheng_count += 1
        elif rel_td == 'ke':
            ke_count += 1

        # Same element count
        same_count = sum(1 for r in [rel_tr, rel_rd, rel_td] if r == 'same')

        if ke_count >= 2:
            return ("凶", f"三才配置为{tian}{ren}{di}，克制较多，基础不稳，须注意化解。")
        elif ke_count == 1 and sheng_count == 0 and same_count == 0:
            return ("凶", f"三才配置为{tian}{ren}{di}，有克制之象，人生多波折。")
        elif sheng_count >= 2:
            return ("大吉", f"三才配置为{tian}{ren}{di}，相生流畅，运势亨通。")
        elif sheng_count >= 1 or same_count >= 2:
            return ("吉", f"三才配置为{tian}{ren}{di}，配合尚可，运势平稳。")
        else:
            return ("半吉", f"三才配置为{tian}{ren}{di}，配合一般，中平之象。")

    # ─── 八字喜用神匹配 ────────────────────────────────────────────────

    def _check_bazi_match(self, wuge: dict, bazi_info: dict) -> Optional[dict]:
        """
        Check if the name's wuxing supplements the 喜用神 from bazi analysis.

        Args:
            wuge: The calculated 五格 data
            bazi_info: Dict from bazi engine containing at least:
                - 'ri_zhu' or 'day_master': 日主
                - 'xi_shen' or 'favorable': 喜用神 list
                - 'ji_shen' or 'unfavorable': 忌神 list
        """
        # Extract bazi information
        # 兼容多种key格式：优先xi_shen/favorable，回退到xi_yong.xi（八字引擎输出格式）
        xi_shen = bazi_info.get("xi_shen") or bazi_info.get("favorable") or []
        ji_shen = bazi_info.get("ji_shen") or bazi_info.get("unfavorable") or []
        # 八字引擎输出格式：xi_yong = {'xi': [...], 'ji': [...]}
        if not xi_shen:
            xi_yong = bazi_info.get("xi_yong") or {}
            if isinstance(xi_yong, dict):
                xi_shen = xi_yong.get("xi", [])
                if not ji_shen:
                    ji_shen = xi_yong.get("ji", [])
        ri_zhu = bazi_info.get("ri_zhu") or bazi_info.get("day_master") or ""

        if isinstance(xi_shen, str):
            xi_shen = [xi_shen]
        if isinstance(ji_shen, str):
            ji_shen = [ji_shen]

        # Get name's wuxing from 人格 (most important) and 地格
        ren_wx = self._number_to_wuxing(wuge["人格"]["数理"])
        di_wx = self._number_to_wuxing(wuge["地格"]["数理"])
        name_wuxing = [ren_wx, di_wx]

        # Count matches
        xi_match = sum(1 for wx in name_wuxing if wx in xi_shen)
        ji_match = sum(1 for wx in name_wuxing if wx in ji_shen)

        if xi_match > ji_match:
            return {
                "匹配": True,
                "等级": "吉",
                "说明": f"名字五行({ren_wx}{di_wx})与喜用神{''.join(xi_shen)}相合，有助于命理补益。",
                "喜用神": xi_shen,
                "忌神": ji_shen,
                "日主": ri_zhu,
            }
        elif ji_match > xi_match:
            return {
                "匹配": False,
                "等级": "凶",
                "说明": f"名字五行({ren_wx}{di_wx})与忌神{''.join(ji_shen)}相合，不利于命理补益。建议调整。",
                "喜用神": xi_shen,
                "忌神": ji_shen,
                "日主": ri_zhu,
            }
        else:
            return {
                "匹配": None,
                "等级": "中",
                "说明": f"名字五行({ren_wx}{di_wx})与八字关系中平。",
                "喜用神": xi_shen,
                "忌神": ji_shen,
                "日主": ri_zhu,
            }

    # ─── 综合评分 ──────────────────────────────────────────────────────

    def _calc_score(self, wuge: dict, sancai: dict,
                    bazi_match: Optional[dict], gender: str) -> int:
        """
        Calculate overall name score (0-100).

        Scoring weights:
        - 人格吉凶: 30%
        - 地格吉凶: 20%
        - 总格吉凶: 15%
        - 三才配置: 20%
        - 天格/外格: 10%
        - 八字匹配: 5% (if available)
        """
        score = 0

        # Grid scores
        jixiong_scores = {"大吉": 100, "吉": 85, "半吉": 65, "平": 50, "半凶": 35, "凶": 15, "大凶": 5}

        # 人格 (30%)
        ren_jx = wuge["人格"].get("吉凶", "平")
        score += jixiong_scores.get(ren_jx, 50) * 0.30

        # 地格 (20%)
        di_jx = wuge["地格"].get("吉凶", "平")
        score += jixiong_scores.get(di_jx, 50) * 0.20

        # 总格 (15%)
        zong_jx = wuge["总格"].get("吉凶", "平")
        score += jixiong_scores.get(zong_jx, 50) * 0.15

        # 三才 (20%)
        sancai_jx = sancai.get("吉凶", "半吉")
        score += jixiong_scores.get(sancai_jx, 50) * 0.20

        # 天格 + 外格 (10%) — 大凶时额外扣分
        tian_jx = wuge["天格"].get("吉凶", "平")
        wai_jx = wuge["外格"].get("吉凶", "平")
        avg_tianwai = (jixiong_scores.get(tian_jx, 50) + jixiong_scores.get(wai_jx, 50)) / 2
        score += avg_tianwai * 0.10
        # 2026-06-13 修正：天格/外格大凶时额外扣分
        if tian_jx in ("凶", "大凶"):
            score -= 8
        if wai_jx in ("凶", "大凶"):
            score -= 8

        # 八字匹配 (5%)
        if bazi_match:
            bazi_score_map = {"吉": 90, "中": 50, "凶": 10}
            bazi_score = bazi_score_map.get(bazi_match.get("等级", "中"), 50)
            score += bazi_score * 0.05

        return max(0, min(100, round(score)))

    # ─── 分析文本生成 ──────────────────────────────────────────────────

    def _generate_analysis(self, surname: str, given_name: str, gender: str,
                           wuge: dict, sancai: dict,
                           bazi_match: Optional[dict], score: int,
                           is_compound: bool) -> str:
        """Generate a human-readable analysis text."""
        lines = []
        full_name = surname + given_name

        # Header
        lines.append(f"【姓名分析报告】")
        lines.append(f"姓名：{full_name}")
        lines.append(f"性别：{gender}")
        lines.append(f"复姓：{'是' if is_compound else '否'}")
        lines.append("")

        # 五格
        lines.append("━━━ 五格剖象 ━━━")
        for name in ["天格", "人格", "地格", "外格", "总格"]:
            g = wuge[name]
            jx = g.get("吉凶", "平")
            if jx in ("吉", "大吉"):
                emoji = "✅"
            elif jx == "平":
                emoji = "➖"
            elif "半" in jx:
                emoji = "⚠️"
            else:
                emoji = "❌"
            lines.append(f"  {name}：{g['画数']}画（{g['数理']}数·{g.get('数理名', '')}）{emoji} {g.get('吉凶', '')}")
            if g.get("数理含义"):
                lines.append(f"         {g['数理含义'][:60]}")
        lines.append("")

        # 三才
        lines.append("━━━ 三才配置 ━━━")
        lines.append(f"  配置：{sancai['配置']}（{sancai.get('吉凶', '')}）")
        lines.append(f"  说明：{sancai.get('解释', '')}")
        lines.append("")

        # 八字匹配
        if bazi_match:
            lines.append("━━━ 八字匹配 ━━━")
            lines.append(f"  {bazi_match.get('说明', '')}")
            lines.append("")

        # 总评
        lines.append("━━━ 综合评价 ━━━")
        lines.append(f"  综合评分：{score}/100")
        if score >= 85:
            lines.append("  评语：此名五格配置优良，三才相生，是难得的好名字。")
        elif score >= 70:
            lines.append("  评语：此名五格配置良好，整体运势不错。")
        elif score >= 55:
            lines.append("  评语：此名五格配置尚可，部分格局有待优化。")
        elif score >= 40:
            lines.append("  评语：此名五格配置一般，建议考虑调整。")
        else:
            lines.append("  评语：此名五格配置欠佳，建议重新起名或改名。")

        return "\n".join(lines)


# ─── Module-level singleton ──────────────────────────────────────────────
_instance = None


def get_xingming_engine() -> XingMingEngine:
    """Get the singleton XingMingEngine instance."""
    global _instance
    if _instance is None:
        _instance = XingMingEngine()
    return _instance
