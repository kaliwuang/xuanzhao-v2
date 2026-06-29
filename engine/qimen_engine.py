"""
Qi Men Dun Jia (奇门遁甲) Engine for XuanZhao v2.0
"""
from typing import Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

from .base import DivinationEngine
from .time_engine import CorrectedTime, JIEQI_APPROX_TABLE


class QiMenEngine(DivinationEngine):
    """奇门遁甲排盘引擎"""

    # 九宫基础信息
    PALACE_NAMES = {1: '坎一宫', 2: '坤二宫', 3: '震三宫', 4: '巽四宫',
                    5: '中五宫', 6: '乾六宫', 7: '兑七宫', 8: '艮八宫', 9: '离九宫'}
    PALACE_DIRECTIONS = {1: '北', 2: '西南', 3: '东', 4: '东南',
                         5: '中', 6: '西北', 7: '西', 8: '东北', 9: '南'}

    # 九星
    NINE_STARS = ['天蓬', '天芮', '天冲', '天辅', '天禽', '天心', '天柱', '天任', '天英']

    # 地盘三奇六仪
    DI_PAN_YI = ['戊', '己', '庚', '辛', '壬', '癸', '丁', '丙', '乙']

    # 天干 / 地支
    TIAN_GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    DI_ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

    # 八神
    EIGHT_GODS = ['值符', '螣蛇', '太阴', '六合', '白虎', '玄武', '九地', '九天']

    # 甲隐遁六仪映射（六甲旬首→所遁之仪）
    # 甲子旬→戊, 甲戌旬→己, 甲申旬→庚, 甲午旬→辛, 甲辰旬→壬, 甲寅旬→癸
    # 仅六个甲的对应地支有映射，其余地支不应出现在此表中
    JIA_HIDE = {
        '子': '戊', '戌': '己', '申': '庚', '午': '辛', '辰': '壬', '寅': '癸',
    }

    # 洛书八宫顺序（不含中宫5）
    LUO_SHU_8 = [1, 8, 3, 4, 9, 2, 7, 6]

    # 地支→九宫映射
    ZHI_TO_GONG_NUM = {
        '子': 1, '丑': 8, '寅': 8, '卯': 3, '辰': 4, '巳': 4,
        '午': 9, '未': 2, '申': 2, '酉': 7, '戌': 6, '亥': 6,
    }

    # 阳遁局数（节气 -> 局）
    YANG_JU = {
        '冬至': 1, '小寒': 2, '大寒': 3,
        '立春': 8, '雨水': 9, '惊蛰': 1,
        '春分': 3, '清明': 4, '谷雨': 5,
        '立夏': 4, '小满': 5, '芒种': 6,
    }
    # 阴遁局数
    YIN_JU = {
        '夏至': 9, '小暑': 8, '大暑': 7,
        '立秋': 2, '处暑': 1, '白露': 9,
        '秋分': 7, '寒露': 6, '霜降': 5,
        '立冬': 6, '小雪': 5, '大雪': 4,
    }

    # 洛书飞宫顺序（中五寄坤二）
    LUO_SHU_ORDER = [1, 8, 3, 4, 9, 2, 7, 6, 5]

    # 九宫→九星直接映射（标准洛书配九星：1蓬2芮3冲4辅5禽6心7柱8任9英）
    GONG_TO_STAR = {1: '天蓬', 2: '天芮', 3: '天冲', 4: '天辅', 5: '天禽', 6: '天心', 7: '天柱', 8: '天任', 9: '天英'}

    # 八门原始宫位（后天八卦标准配门：坎休、艮生、震伤、巽杜、离景、坤死、兑惊、乾开）
    # 值使门判定需用原始位，不可用旋转后的 ba_men
    DOOR_ORIGINAL = {1: '休门', 8: '生门', 3: '伤门', 4: '杜门', 9: '景门', 2: '死门', 7: '惊门', 6: '开门'}

    # 天干五行映射（悖格判断用）
    GAN_WUXING = {'甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
                   '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'}
    # 五行相克（我克）
    WUXING_KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}
    # 五行相生（我生）
    WUXING_SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}

    # 天干阴阳
    GAN_YINYANG = {'甲': '阳', '乙': '阴', '丙': '阳', '丁': '阴', '戊': '阳',
                   '己': '阴', '庚': '阳', '辛': '阴', '壬': '阳', '癸': '阴'}

    # 天干五合（合化五行）
    GAN_HE = {('甲', '己'): '土', ('己', '甲'): '土',
              ('乙', '庚'): '金', ('庚', '乙'): '金',
              ('丙', '辛'): '水', ('辛', '丙'): '水',
              ('丁', '壬'): '木', ('壬', '丁'): '木',
              ('戊', '癸'): '火', ('癸', '戊'): '火'}

    # 天干相冲
    GAN_CHONG = {'甲': '庚', '庚': '甲', '乙': '辛', '辛': '乙',
                 '丙': '壬', '壬': '丙', '丁': '癸', '癸': '丁'}

    # 地支六合
    ZHI_LIUHE = {'子': '丑', '丑': '子', '寅': '亥', '亥': '寅',
                 '卯': '戌', '戌': '卯', '辰': '酉', '酉': '辰',
                 '巳': '申', '申': '巳', '午': '未', '未': '午'}

    # 地支六冲
    ZHI_LIUCHONG = {'子': '午', '午': '子', '丑': '未', '未': '丑',
                    '寅': '申', '申': '寅', '卯': '酉', '酉': '卯',
                    '辰': '戌', '戌': '辰', '巳': '亥', '亥': '巳'}

    # 地支三合
    ZHI_SANHE = {
        '申': ('水', ('申', '子', '辰')), '子': ('水', ('申', '子', '辰')), '辰': ('水', ('申', '子', '辰')),
        '亥': ('木', ('亥', '卯', '未')), '卯': ('木', ('亥', '卯', '未')), '未': ('木', ('亥', '卯', '未')),
        '寅': ('火', ('寅', '午', '戌')), '午': ('火', ('寅', '午', '戌')), '戌': ('火', ('寅', '午', '戌')),
        '巳': ('金', ('巳', '酉', '丑')), '酉': ('金', ('巳', '酉', '丑')), '丑': ('金', ('巳', '酉', '丑')),
    }

    # 地支三刑
    ZHI_SANXING = {
        '寅': '巳', '巳': '申', '申': '寅',  # 无恩之刑
        '丑': '戌', '戌': '未', '未': '丑',  # 恃势之刑
        '子': '卯', '卯': '子',  # 无礼之刑
        '辰': '辰', '午': '午', '酉': '酉', '亥': '亥',  # 自刑
    }

    # 地支相害
    ZHI_HAI = {'子': '未', '未': '子', '丑': '午', '午': '丑',
               '寅': '巳', '巳': '寅', '卯': '辰', '辰': '卯',
               '申': '亥', '亥': '申', '酉': '戌', '戌': '酉'}

    # ---- 格局检测常量（提升到类级别，避免每次 _analyze_ge_ju 调用重建）----

    # 击刑宫位映射
    XING_MAP = {1: '子', 8: '丑', 3: '卯', 4: '辰', 9: '午', 2: '未', 7: '酉', 6: '戌'}
    # 天干击刑对应宫位
    GAN_XING = {'戊': 3, '己': 2, '庚': 8, '辛': 9, '壬': 4, '癸': 4}
    # 天干击刑对应地支名
    GAN_XING_BRANCH = {'戊': '卯', '己': '未', '庚': '寅', '辛': '午', '壬': '辰', '癸': '巳'}
    # 入墓（不含三奇，三奇由 SAN_QI_MU 专项处理）
    # 传统规则（《奇门遁甲元灵经》《遁甲符应经》）：
    # 戊墓在辰(巽四宫), 己墓在戌(乾六宫), 庚墓在丑(艮八宫)
    # 辛墓在戌(乾六宫), 壬墓在辰(巽四宫), 癸墓在戌(乾六宫)
    GAN_MU = {'戊': 4, '己': 6, '庚': 8, '辛': 6, '壬': 4, '癸': 6}
    # 三奇入墓（乙入坤宫未墓=2，丙入乾宫戌墓=6，丁入艮宫丑墓=8）
    SAN_QI_MU = {'乙': 2, '丙': 6, '丁': 8}
    # 悖格排除集（已有专用名称的天地盘组合 + 天干五合）
    ALREADY_CHECKED = {('庚', '丙'), ('丙', '庚'), ('庚', '癸'), ('戊', '丙'),
                       ('丙', '戊'), ('辛', '乙'), ('丙', '辛'), ('乙', '庚'),
                       ('庚', '乙'), ('丁', '壬'), ('壬', '丁'),
                       ('辛', '丙'), ('戊', '癸'), ('癸', '戊'),
                       ('甲', '己'), ('己', '甲'),
                       # 六庚完整克应（新增）
                       ('庚', '丁'), ('庚', '己'), ('庚', '辛'), ('庚', '壬'), ('庚', '庚'),
                       # 丁癸干支级克应（新增）
                       ('丁', '癸'), ('癸', '丁')}
    # 天地合德（排除乙庚→奇合、丙辛→欢怡）
    GAN_HE_GEDE = {'甲': '己', '己': '甲', '丁': '壬', '壬': '丁',
                    '戊': '癸', '癸': '戊'}

    # 八门五行
    MEN_WUXING = {'休门': '水', '生门': '土', '伤门': '木', '杜门': '木',
                  '景门': '火', '死门': '土', '惊门': '金', '开门': '金'}

    # 九星五行
    STAR_WUXING = {'天蓬': '水', '天芮': '土', '天冲': '木', '天辅': '木',
                   '天禽': '土', '天心': '金', '天柱': '金', '天任': '土', '天英': '火'}

    # 八门旺衰（所落宫位五行→旺/相/休/囚/死）
    # 门五行→旺的宫位五行
    MEN_WANG_GONG = {'水': 1, '木': [3, 4], '火': 9, '土': [2, 5, 8], '金': [6, 7]}
    # 九星旺衰
    STAR_WANG_GONG = {'水': 1, '木': [3, 4], '火': 9, '土': [2, 5, 8], '金': [6, 7]}

    # 宫位五行（洛书九宫配五行）
    GONG_WUXING = {1: '水', 2: '土', 3: '木', 4: '木', 5: '土',
                   6: '金', 7: '金', 8: '土', 9: '火'}

    # 八门吉凶属性
    MEN_JIXIONG = {'开门': '吉', '休门': '吉', '生门': '吉', '景门': '中',
                   '伤门': '凶', '杜门': '凶', '死门': '凶', '惊门': '凶'}

    # 九星吉凶属性
    STAR_JIXIONG = {'天心': '吉', '天任': '吉', '天冲': '吉', '天辅': '吉',
                    '天禽': '吉', '天蓬': '凶', '天芮': '凶', '天柱': '凶', '天英': '中'}

    # 天干长生十二宫（天干→长生所在宫位）
    # 阳干顺行，阴干逆行
    CHANGSHENG_GONG = {
        '甲': {'长生': 8, '沐浴': 9, '冠带': 1, '临官': 2, '帝旺': 3,
               '衰': 4, '病': 5, '死': 6, '墓': 7, '绝': 8, '胎': 9, '养': 1},
        '丙': {'长生': 4, '沐浴': 3, '冠带': 2, '临官': 1, '帝旺': 9,
               '衰': 8, '病': 7, '死': 6, '墓': 5, '绝': 4, '胎': 3, '养': 2},
        '戊': {'长生': 4, '沐浴': 3, '冠带': 2, '临官': 1, '帝旺': 9,
               '衰': 8, '病': 7, '死': 6, '墓': 5, '绝': 4, '胎': 3, '养': 2},
        '庚': {'长生': 8, '沐浴': 9, '冠带': 1, '临官': 2, '帝旺': 3,
               '衰': 4, '病': 5, '死': 6, '墓': 7, '绝': 8, '胎': 9, '养': 1},
        '壬': {'长生': 4, '沐浴': 3, '冠带': 2, '临官': 1, '帝旺': 9,
               '衰': 8, '病': 7, '死': 6, '墓': 5, '绝': 4, '胎': 3, '养': 2},
    }

    # 格局等级分类
    GE_JU_LEVEL = {
        '天遁': '大吉', '地遁': '大吉', '人遁': '大吉',
        '龙遁': '大吉', '虎遁': '吉', '风遁': '吉', '云遁': '吉',
        '飞鸟跌穴': '大吉', '青龙返首': '大吉', '玉女守门': '大吉',
        '三奇得使': '大吉', '天地合德': '吉', '欢怡': '吉', '奇合': '吉',
        '丁壬合': '吉', '戊癸合': '吉',
        '太白入荧': '大凶', '荧入太白': '凶', '小格': '凶',
        '大格': '凶', '刑格': '凶', '白虎出力': '凶', '上格': '凶',
        '太白同宫': '大凶', '白虎猖狂': '大凶',
        '朱雀投江（门级）': '凶', '螣蛇夭矫（门级）': '凶',
        '朱雀投江（干支级）': '凶', '螣蛇夭矫（干支级）': '凶',
        '五不遇时': '大凶', '击刑': '凶', '入墓': '凶', '三奇入墓': '凶',
        '悖格': '凶', '值使落空': '凶',
        # 新增格局等级
        '天辅杜门': '吉', '天心开门': '大吉', '天冲伤门': '中',
        '天蓬休门': '凶', '天芮死门': '大凶', '天柱惊门': '凶', '天英景门': '凶',
        '值符开门': '大吉', '九天吉门': '大吉', '九地凶门': '凶',
        '白虎凶门': '大凶', '玄武休门': '吉', '太阴杜门': '吉', '六合开门': '大吉',
        '日奇入墓': '凶', '丙奇入墓': '凶', '星奇入墓': '凶',
        '地户埋光': '凶', '狱神得奇': '吉', '水蛇入火': '凶', '天网四张': '大凶',
        # 新增格局 #37-46：天干克应扩展
        '辛加丁': '吉', '丁加辛': '吉', '乙加丙': '吉', '丙加乙': '吉',
        '壬加乙': '凶', '乙加壬': '中', '癸加乙': '凶', '乙加癸': '中',
        '戊加丁': '吉', '丁加戊': '吉', '己加乙': '凶', '乙加己': '中',
        '庚加戊': '凶', '戊加庚': '凶', '辛加丙': '中', '壬加丁': '凶',
        '癸加丙': '凶', '丙加癸': '凶', '辛加壬': '凶', '壬加辛': '凶',
        # Q1: 补全剩余十干克应格局等级
        '乙加丁': '吉', '丁加乙': '中', '丙加丁': '吉', '丁加丙': '中',
        '戊加乙': '中', '乙加戊': '中', '己加丁': '凶', '丁加己': '中',
        '己加丙': '中', '丙加己': '吉', '己加辛': '凶', '辛加己': '中',
        '庚加甲': '凶', '壬加庚': '凶', '庚加壬': '凶',
        '癸加辛': '凶', '辛加癸': '中', '癸加己': '凶', '己加癸': '凶',
        '壬加戊': '凶', '戊加壬': '凶', '壬加己': '凶', '己加壬': '凶',
        # Q3: 六仪特殊格局等级
        '甲加甲': '大吉', '甲加己': '吉', '己加甲': '吉',
        # Q4: 天干克应补充分类
        '丙加壬': '凶', '乙加辛': '凶', '辛加乙': '凶',
        '癸加庚': '凶', '庚加癸': '凶', '壬加癸': '凶', '癸加壬': '凶',
    }

    # Q9: 十干克应分类表（吉凶分类速查）
    GAN_KE_CLASSIFY = {
        '大吉': ['飞鸟跌穴', '青龙返首', '玉女守门', '天遁', '地遁', '人遁', '龙遁'],
        '吉': ['虎遁', '风遁', '云遁', '三奇得使', '天地合德', '欢怡', '奇合',
               '狱神得奇', '丁壬合', '戊癸合', '玄武休门', '太阴杜门', '六合开门'],
        '凶': ['白虎出力', '上格', '日奇入墓', '丙奇入墓', '星奇入墓', '地户埋光',
               '水蛇入火', '朱雀投江', '螣蛇夭矫', '击刑', '入墓', '悖格'],
        '大凶': ['太白入荧', '太白同宫', '白虎猖狂', '五不遇时', '天网四张', '天芮死门'],
    }

    # Q8: 天干克应详细解读（含类象、应期提示）
    GAN_KE_DETAIL = {
        ('丙', '戊'): {'name': '飞鸟跌穴', '类象': '飞鸟归巢，百事吉昌', '应期': '丙戊日时'},
        ('戊', '丙'): {'name': '青龙返首', '类象': '贵人相助，逢凶化吉', '应期': '戊丙日时'},
        ('丁', '辛'): {'name': '狱神得奇变格', '类象': '文书有救，阴中得利', '应期': '丁辛日时'},
        ('辛', '丁'): {'name': '狱神得奇', '类象': '囚人获释，讼事有利', '应期': '辛丁日时'},
        ('乙', '庚'): {'name': '奇合', '类象': '乙庚合化金，合作有利', '应期': '乙庚日时'},
        ('庚', '乙'): {'name': '奇合', '类象': '庚乙合化金，刚柔相济', '应期': '庚乙日时'},
        ('庚', '丙'): {'name': '太白入荧', '类象': '贼来为患，外患内忧', '应期': '庚丙日时'},
        ('丙', '庚'): {'name': '荧入太白', '类象': '门户破败，宜守不宜进', '应期': '丙庚日时'},
        ('丁', '癸'): {'name': '朱雀投江', '类象': '文书遗失，音信杳然', '应期': '丁癸日时'},
        ('癸', '丁'): {'name': '螣蛇夭矫', '类象': '虚惊怪异，文书有灾', '应期': '癸丁日时'},
        ('乙', '丙'): {'name': '奇仪顺遂', '类象': '乙木生丙火，谋事顺遂', '应期': '乙丙日时'},
        ('丙', '乙'): {'name': '日月并行', '类象': '丙火配乙木，光明正大', '应期': '丙乙日时'},
    }

    # Q15: 门迫/门制/门墓详细分类
    MEN_PO_DETAIL = {
        '休门': {'迫宫': '离(火)', '制宫': '坤艮(土)', '墓宫': '坤(土)', 'desc': '休门属水，迫火宫，制土宫'},
        '生门': {'迫宫': '坎(水)', '制宫': '震巽(木)', '墓宫': '坎(水)', 'desc': '生门属土，迫水宫，制木宫'},
        '伤门': {'迫宫': '坤艮(土)', '制宫': '离(火)', '墓宫': '坤(土)', 'desc': '伤门属木，迫土宫，制火宫'},
        '杜门': {'迫宫': '坤艮(土)', '制宫': '离(火)', '墓宫': '坤(土)', 'desc': '杜门属木，迫土宫，制火宫'},
        '景门': {'迫宫': '兑乾(金)', '制宫': '坤艮(土)', '墓宫': '乾(金)', 'desc': '景门属火，迫金宫，制土宫'},
        '死门': {'迫宫': '坎(水)', '制宫': '震巽(木)', '墓宫': '坎(水)', 'desc': '死门属土，迫水宫，制木宫'},
        '惊门': {'迫宫': '震巽(木)', '制宫': '坎(水)', '墓宫': '震(木)', 'desc': '惊门属金，迫木宫，制水宫'},
        '开门': {'迫宫': '震巽(木)', '制宫': '坎(水)', '墓宫': '震(木)', 'desc': '开门属金，迫木宫，制水宫'},
    }

    # Q16: 九星到宫详细吉凶
    STAR_TO_GONG = {
        '天蓬': {1: '旺', 2: '死', 3: '休', 4: '休', 6: '囚', 7: '囚', 8: '死', 9: '相'},
        '天芮': {1: '囚', 2: '旺', 3: '死', 4: '死', 6: '相', 7: '相', 8: '旺', 9: '囚'},
        '天冲': {1: '相', 2: '囚', 3: '旺', 4: '旺', 6: '死', 7: '死', 8: '囚', 9: '休'},
        '天辅': {1: '相', 2: '囚', 3: '旺', 4: '旺', 6: '死', 7: '死', 8: '囚', 9: '休'},
        '天禽': {1: '囚', 2: '旺', 3: '死', 4: '死', 6: '相', 7: '相', 8: '旺', 9: '囚'},
        '天心': {1: '休', 2: '相', 3: '死', 4: '死', 6: '旺', 7: '旺', 8: '相', 9: '囚'},
        '天柱': {1: '休', 2: '相', 3: '死', 4: '死', 6: '旺', 7: '旺', 8: '相', 9: '囚'},
        '天任': {1: '囚', 2: '旺', 3: '死', 4: '死', 6: '相', 7: '相', 8: '旺', 9: '囚'},
        '天英': {1: '死', 2: '休', 3: '囚', 4: '囚', 6: '相', 7: '相', 8: '休', 9: '旺'},
    }

    # Q17: 八神到宫详细吉凶
    SHEN_TO_GONG = {
        '值符': {1: '吉', 2: '吉', 3: '吉', 4: '吉', 6: '大吉', 7: '大吉', 8: '吉', 9: '吉'},
        '螣蛇': {1: '凶', 2: '凶', 3: '凶', 4: '凶', 6: '凶', 7: '凶', 8: '凶', 9: '大凶'},
        '太阴': {1: '吉', 2: '吉', 3: '中', 4: '吉', 6: '大吉', 7: '大吉', 8: '中', 9: '中'},
        '六合': {1: '吉', 2: '中', 3: '大吉', 4: '大吉', 6: '中', 7: '中', 8: '中', 9: '吉'},
        '白虎': {1: '大凶', 2: '凶', 3: '凶', 4: '凶', 6: '大凶', 7: '大凶', 8: '凶', 9: '凶'},
        '玄武': {1: '凶', 2: '凶', 3: '中', 4: '中', 6: '凶', 7: '凶', 8: '凶', 9: '凶'},
        '九地': {1: '中', 2: '吉', 3: '中', 4: '中', 6: '中', 7: '中', 8: '吉', 9: '中'},
        '九天': {1: '吉', 2: '中', 3: '大吉', 4: '大吉', 6: '吉', 7: '吉', 8: '中', 9: '大吉'},
    }

    # Q20: 天德月德分析表
    TIANYUE_DE = {
        '甲': {'天德': '丁', '月德': '丙', '天德方位': '南', '月德方位': '南'},
        '乙': {'天德': '申', '月德': '壬', '天德方位': '西南', '月德方位': '北'},
        '丙': {'天德': '壬', '月德': '庚', '天德方位': '北', '月德方位': '西'},
        '丁': {'天德': '甲', '月德': '丙', '天德方位': '东', '月德方位': '南'},
        '戊': {'天德': '丙', '月德': '甲', '天德方位': '南', '月德方位': '东'},
        '己': {'天德': '壬', '月德': '庚', '天德方位': '北', '月德方位': '西'},
        '庚': {'天德': '丙', '月德': '丙', '天德方位': '南', '月德方位': '南'},
        '辛': {'天德': '甲', '月德': '甲', '天德方位': '东', '月德方位': '东'},
        '壬': {'天德': '丙', '月德': '壬', '天德方位': '南', '月德方位': '北'},
        '癸': {'天德': '壬', '月德': '庚', '天德方位': '北', '月德方位': '西'},
    }

    # Q21: 月将分析表
    YUEJIANG_QIMEN = {
        '子': '神后', '丑': '大吉', '寅': '功曹', '卯': '太冲',
        '辰': '天罡', '巳': '太乙', '午': '胜光', '未': '小吉',
        '申': '传送', '酉': '从魁', '戌': '河魁', '亥': '登明',
    }

    # Q22: 天喜地煞表
    TIANXI_DISHA = {
        '甲': {'天喜': '申', '地煞': '酉'},
        '乙': {'天喜': '酉', '地煞': '戌'},
        '丙': {'天喜': '戌', '地煞': '亥'},
        '丁': {'天喜': '亥', '地煞': '子'},
        '戊': {'天喜': '子', '地煞': '丑'},
        '己': {'天喜': '丑', '地煞': '寅'},
        '庚': {'天喜': '寅', '地煞': '卯'},
        '辛': {'天喜': '卯', '地煞': '辰'},
        '壬': {'天喜': '辰', '地煞': '巳'},
        '癸': {'天喜': '巳', '地煞': '午'},
    }

    # Q24: 悖格详细分类
    BEI_GE_DETAIL = {
        '戊克壬': '戊土克壬水，财源受阻',
        '戊克癸': '戊土克癸水，暗财有失',
        '己克壬': '己土克壬水，暗昧阻滞',
        '己克癸': '己土克癸水，田宅有失',
        '庚克甲': '庚金克甲木，首领有灾',
        '庚克乙': '庚金克乙木，日奇受制',
        '辛克甲': '辛金克甲木，变革不利',
        '辛克乙': '辛金克乙木，阴柔受损',
        '壬克丙': '壬水克丙火，月奇受难',
        '壬克丁': '壬水克丁火，星奇入墓',
        '癸克丙': '癸水克丙火，丙奇暗昧',
        '癸克丁': '癸水克丁火，文书有灾',
    }

    # Q25: 事类判断参考表
    SHILEI_REFERENCE = {
        '求财': {'吉门': ['生门', '开门', '休门'], '吉星': ['天心', '天任', '天冲'],
                 '吉神': ['值符', '六合', '九天'], '吉格': ['飞鸟跌穴', '青龙返首', '天遁']},
        '出行': {'吉门': ['开门', '休门', '生门'], '吉星': ['天心', '天冲', '天辅'],
                 '吉神': ['值符', '九天', '六合'], '吉格': ['龙遁', '虎遁', '风遁']},
        '疾病': {'吉门': ['天心开门', '休门', '生门'], '吉星': ['天心', '天任'],
                 '凶门': ['死门', '惊门'], '凶星': ['天芮', '天柱']},
        '婚姻': {'吉门': ['休门', '景门'], '吉星': ['天辅', '天心'],
                 '吉神': ['六合', '太阴'], '凶神': ['白虎', '玄武']},
        '官司': {'吉门': ['开门', '惊门'], '吉星': ['天心', '天柱'],
                 '凶格': ['太白入荧', '太白同宫'], '吉格': ['狱神得奇']},
        '考试': {'吉门': ['景门', '杜门'], '吉星': ['天辅', '天心'],
                 '吉神': ['值符', '太阴'], '吉格': ['天地合德', '玉女守门']},
    }

    # ---- abstract property implementations ----

    @property
    def name(self) -> str:
        return '奇门'

    @property
    def name_en(self) -> str:
        return 'qimen'

    @property
    def priority(self) -> int:
        return 5

    # ---- core methods ----

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        """校验排盘数据"""
        if data.get('error'):
            return False, data['error']
        if 'ju_shu' not in data or not (1 <= data['ju_shu'] <= 9):
            return False, '局数必须在1-9之间'
        if 'palaces' not in data or len(data.get('palaces', [])) != 9:
            return False, '必须包含9个宫位'
        return True, None

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        """执行奇门遁甲排盘

        Args:
            time: 校正后的时间信息
            gender: 性别 (1=男, 0=女)

        Returns:
            dict: 奇门排盘结果
        """
        # 统一使用八字引擎的晚子时处理（与八字/六壬/六爻保持一致）
        # 晚子时(23:xx)：日柱用次日日期，时辰用子时(hour=0)
        # 避免各helper方法内部重复做晚子时判定导致不一致
        pillar_date = time.bazi_day_pillar_date
        bazi_hour = time.bazi_hour
        solar_dt = datetime(pillar_date.year, pillar_date.month, pillar_date.day,
                            bazi_hour, time.true_solar.minute, 0)

        # 1. 节气 & 局数
        jieqi, ju, yin_yang = self._get_jieqi_info(solar_dt)

        # 2. 干支
        hour_gan_zhi = self._calc_hour_gan_zhi(solar_dt)
        day_gan_zhi = self._get_day_gan_zhi(solar_dt)
        time_gan = hour_gan_zhi[0] if hour_gan_zhi else '甲'

        # 获取年干支（用于年命落宫、太岁分析）
        year_gan_zhi = ''
        try:
            from lunar_python import Solar
            lunar = Solar.fromYmdHms(
                solar_dt.year, solar_dt.month, solar_dt.day,
                solar_dt.hour, solar_dt.minute, 0
            ).getLunar()
            year_gan_zhi = lunar.getYearGan() + lunar.getYearZhi()
        except Exception:
            year_gan_zhi = ''

        # 3. 地盘
        di_pan = self._build_di_pan(ju, yin_yang)

        # 4. 天盘、八门、九星
        tian_pan, ba_men, jiu_xing = self._build_tian_pan(di_pan, hour_gan_zhi, ju, yin_yang)

        # 5. 值符 & 值使
        # 值符 = 时干在地盘所临之宫的原始九星（不可用旋转后的天盘星）
        # 值使 = 时干在地盘所临之宫的原始八门（不可用旋转后的人盘门）
        zhi_fu_gong = self._find_gong_for_gan(di_pan, hour_gan_zhi)
        zhi_fu_star = self.GONG_TO_STAR.get(zhi_fu_gong, '天蓬')
        zhi_shi_door = self.DOOR_ORIGINAL.get(zhi_fu_gong, '休门')

        # 6. 八神
        ba_shen = self._build_ba_shen(yin_yang, zhi_fu_gong)

        # 7. 宫位汇总
        palaces = self._build_palaces(di_pan, tian_pan, ba_men, jiu_xing, ba_shen)

        # 旬空
        xun_kong = self._calc_xun_kong(day_gan_zhi)

        # 7. 格局分析（提前计算，供后续使用）
        ge_ju_analysis = self._analyze_ge_ju(palaces, ba_men, jiu_xing, ba_shen, xun_kong, day_gan_zhi, hour_gan_zhi, zhi_shi_door)

        yong_shen = self._analyze_yong_shen(palaces, hour_gan_zhi, day_gan_zhi)
        liunian = self._build_liunian(solar_dt, di_pan, tian_pan, palaces)

        result = {
            'engine': self.name,
            'engine_en': self.name_en,
            'ju_name': f'{yin_yang}{ju}局',
            'yin_yang': yin_yang,
            'ju_shu': ju,
            'jieqi': jieqi,
            'day_gan_zhi': day_gan_zhi,
            'time_gan_zhi': hour_gan_zhi,
            'time_gan': time_gan,
            'di_pan': {str(k): v for k, v in di_pan.items()},
            'tian_pan': {str(k): v for k, v in tian_pan.items()},
            'ba_men': {str(k): v for k, v in ba_men.items()},
            'jiu_xing': {str(k): v for k, v in jiu_xing.items()},
            'ba_shen': {str(k): v for k, v in ba_shen.items()},
            'palaces': palaces,
            'zhi_fu': {'star': zhi_fu_star, 'gong': zhi_fu_gong},
            'zhi_fu_gong': zhi_fu_gong,
            'zhi_shi': {'door': zhi_shi_door, 'gong': zhi_fu_gong},
            'solar_time': solar_dt.isoformat(),
            'gender': '男' if gender == 1 else '女',
            'xun_kong': xun_kong,
            # 天地人三盘摘要（便于前端快速展示）
            'san_pan_summary': self._build_san_pan_summary(palaces),
            'ge_ju_analysis': ge_ju_analysis,
            # 流年分析
            'liunian': liunian,
            # #47: 马星（驿马）分析
            'ma_xing': self._analyze_ma_xing(day_gan_zhi, palaces),
            # #48: 天乙贵人落宫
            'tianyi_guiren': self._analyze_tianyi(day_gan_zhi, palaces),
            # #49: 桃花落宫
            'taohua': self._analyze_taohua(day_gan_zhi, palaces),
            # #50: 空亡详细解读
            'kong_wang_detail': self._analyze_kong_wang_detail(xun_kong, palaces),
            # 宫位详细分析
            'palace_details': self._analyze_palace_details(palaces),
            # 伏吟反吟
            'fu_fan_yin': self._analyze_fuyin_fanyin(di_pan, tian_pan),
            # 门迫分析
            'men_po': self._analyze_men_po(palaces),
            # 三奇六仪位置
            'san_qi_positions': self._find_sanqi_positions(di_pan, tian_pan),
            # 用神落宫
            'yong_shen': yong_shen,
            # 格局力量统计
            'ge_ju_strength': self._calc_ge_ju_strength(ge_ju_analysis),
            # #41: 门星神组合详细解读
            'men_xing_shen_combo': self._analyze_men_xing_shen_combo(palaces),
            # #51: 时干落宫详细分析
            'hour_palace_detail': self._analyze_hour_palace_detail(palaces, hour_gan_zhi),
            # #52: 日干落宫详细分析
            'day_palace_detail': self._analyze_day_palace_detail(palaces, day_gan_zhi),
            # #56: 宫位综合评分
            'palace_scores': self._calc_palace_score(palaces),
            # Q5: 年命落宫分析
            'nian_ming_gong': self._analyze_nian_ming_gong(palaces, day_gan_zhi, year_gan_zhi),
            # Q6: 月干落宫分析（需要月干支）
            'yue_gan_gong': {},
            # Q11: 用神旺衰等级
            'yong_shen_wang_shuai': self._calc_yong_shen_wang_shuai(yong_shen),
            # Q12: 用神与太岁关系
            'yong_shen_taisui': self._analyze_yong_shen_taisui(yong_shen, liunian),
            # Q14: 伏吟反吟详细分类
            'fuyin_fanyin_detail': self._analyze_fuyin_fanyin_detail(di_pan, tian_pan),
            # Q18: 宫位综合评分V2
            'palace_scores_v2': self._calc_palace_score_v2(palaces),
            # Q19: 天地人三盘综合判断
            'san_pan_composite': self._analyze_san_pan_composite(palaces),
            # Q23: 天显时格
            'tianxian_shi': self._analyze_tianxian_shi(day_gan_zhi, hour_gan_zhi),
            # Q25: 事类判断参考
            'shilei_ref': self.SHILEI_REFERENCE,
        }

        valid, err = self.validate(result)
        if not valid:
            raise ValueError(f'奇门排盘数据校验失败: {err}')

        return result

    # ---- internal helpers ----

    def _get_jieqi_info(self, solar_dt: datetime) -> tuple[str, int, str]:
        """根据阳历日期计算当前节气、局数和阴阳遁

        优先使用 lunar_python 精确节气，回退到近似日期表。

        Returns:
            (节气名, 局数, '阳遁'/'阴遁')
        """
        # 优先使用 lunar_python 精确节气
        try:
            from lunar_python import Solar
            solar = Solar.fromYmdHms(
                solar_dt.year, solar_dt.month, solar_dt.day,
                solar_dt.hour, solar_dt.minute, solar_dt.second
            )
            lunar = solar.getLunar()
            prev_jieqi = lunar.getPrevJieQi()
            if prev_jieqi:
                jq_name = prev_jieqi.getName()
                # 转换简繁体（lunar_python返回简体）
                if jq_name in self.YANG_JU:
                    return jq_name, self.YANG_JU[jq_name], '阳遁'
                elif jq_name in self.YIN_JU:
                    return jq_name, self.YIN_JU[jq_name], '阴遁'
                else:
                    logger.warning(f"lunar_python返回的节气'{jq_name}'不在阴阳遁局数表中，回退到近似计算")
        except Exception as e:
            logger.debug(f"lunar_python精确节气查询异常，回退到近似计算: {e}")

        # 回退：按月日近似节气分界
        m, d = solar_dt.month, solar_dt.day

        current_jieqi = '冬至'
        for name, jm, jd in JIEQI_APPROX_TABLE:
            if (m > jm) or (m == jm and d >= jd):
                current_jieqi = name

        if current_jieqi in self.YANG_JU:
            return current_jieqi, self.YANG_JU[current_jieqi], '阳遁'
        elif current_jieqi in self.YIN_JU:
            return current_jieqi, self.YIN_JU[current_jieqi], '阴遁'
        else:
            # 最终回退：冬至阳遁1局（最安全的默认值）
            logger.warning(f"节气'{current_jieqi}'不在阴阳遁局数表中，回退到冬至阳遁1局")
            return '冬至', 1, '阳遁'

    def _calc_hour_gan_zhi(self, solar_dt: datetime) -> str:
        """计算时柱天干地支"""
        try:
            from lunar_python import Solar
            lunar = Solar.fromYmdHms(
                solar_dt.year, solar_dt.month, solar_dt.day,
                solar_dt.hour, solar_dt.minute, solar_dt.second
            ).getLunar()
            return lunar.getTimeInGanZhi()
        except Exception as e:
            logger.debug(f"lunar_python时柱计算异常，使用近似: {e}")
            hour = solar_dt.hour
            zhi_idx = ((hour + 1) % 24) // 2
            # 晚子时(23:xx)日柱用次日，但时支仍为子时
            calc_dt = solar_dt + timedelta(days=1) if hour == 23 else solar_dt
            day_gan_idx = (calc_dt.toordinal() + 4) % 10
            # 五鼠遁元（时干起法）：日干→时干基准 = (日干%5+1)*2，甲己→丙,乙庚→戊,丙辛→庚,丁壬→壬,戊癸→甲
            gan_idx = ((day_gan_idx % 5 + 1) * 2 + zhi_idx) % 10
            return f'{self.TIAN_GAN[gan_idx]}{self.DI_ZHI[zhi_idx]}'

    def _get_day_gan_zhi(self, solar_dt: datetime) -> str:
        """获取日柱干支"""
        try:
            from lunar_python import Solar
            lunar = Solar.fromYmdHms(
                solar_dt.year, solar_dt.month, solar_dt.day,
                solar_dt.hour, solar_dt.minute, solar_dt.second
            ).getLunar()
            return lunar.getDayInGanZhi()
        except Exception as e:
            logger.debug(f"lunar_python日柱计算异常，使用近似: {e}")
            calc_dt = solar_dt + timedelta(days=1) if solar_dt.hour == 23 else solar_dt
            ga = (calc_dt.toordinal() + 4) % 10
            zi = (calc_dt.toordinal() + 2) % 12
            return f'{self.TIAN_GAN[ga]}{self.DI_ZHI[zi]}'

    def _build_di_pan(self, ju: int, yin_yang: str) -> dict:
        """构建地盘（九宫对应的三奇六仪）

        阳遁: 戊落在第 ju 宫，洛书飞宫顺序顺排
        阴遁: 戊落在第 ju 宫，逆排
        """
        yi_order = self.DI_PAN_YI  # 戊己庚辛壬癸丁丙乙
        luo = self.LUO_SHU_ORDER   # 1 8 3 4 9 2 7 6 5

        start = luo.index(ju) if ju in luo else 0
        di_pan = {}
        for i, palace in enumerate(luo):
            if yin_yang == '阳遁':
                yi_idx = (i - start) % 9
            else:
                yi_idx = (start - i) % 9
            di_pan[palace] = yi_order[yi_idx]
        return di_pan

    def _build_tian_pan(self, di_pan: dict, hour_gan_zhi: str, ju: int, yin_yang: str = '阳遁'):
        """构建天盘、八门、九星

        天盘旋转规则：值符随时干转。
        值符（时干在地盘对应的星）从原宫位转到时干所在宫位，
        其余八星按洛书飞宫顺序跟随转动。
        """
        hour_gan = hour_gan_zhi[0] if hour_gan_zhi else '甲'

        # 九星按标准洛书配九星直接映射（1蓬2芮3冲4辅5禽6心7柱8任9英）
        jiu_xing = dict(self.GONG_TO_STAR)

        # 八门按洛书顺序（中宫5不排门，仅8门对应8宫）
        luo8 = self.LUO_SHU_8
        doors = ['休门', '生门', '伤门', '杜门', '景门', '死门', '惊门', '开门']
        ba_men = {}
        for i, palace in enumerate(luo8):
            ba_men[palace] = doors[i]
        ba_men[5] = ''  # 中宫5不排门，显式设置空值确保key存在

        # 天盘旋转：找到时干在地盘中的宫位
        # 甲不直接出现在地盘（三奇六仪），需查找其隐遁的六仪
        lookup_gan = hour_gan
        if hour_gan == '甲' and len(hour_gan_zhi) > 1:
            lookup_gan = self.JIA_HIDE.get(hour_gan_zhi[1], '戊')
        hour_gan_gong = None
        for gong, yi in di_pan.items():
            if yi == lookup_gan:
                hour_gan_gong = gong
                break

        if hour_gan_gong:
            gong_int = int(hour_gan_gong)
            # 中宫5不在洛书飞宫序列中，需寄宫处理
            # 阳遁寄坤二宫，阴遁寄巽四宫（传统规则）
            _zhong_gong_ji = 4 if yin_yang == '阴遁' else 2
            if gong_int == 5:
                gong_int = _zhong_gong_ji
            ju_lookup = _zhong_gong_ji if ju == 5 else ju
            if gong_int in luo8:
                # 找到值符（ju对应的星）在洛书中的位置
                zhi_fu_idx = luo8.index(ju_lookup) if ju_lookup in luo8 else 0
                # 时干宫在洛书中的位置
                target_idx = luo8.index(gong_int)
                # 计算旋转偏移（阳遁顺飞，阴遁逆飞）
                if yin_yang == '阳遁':
                    offset = target_idx - zhi_fu_idx
                else:
                    offset = zhi_fu_idx - target_idx  # 阴遁逆飞

                # 天盘 = 地盘元素按offset旋转
                n = len(luo8)
                tian_pan = {}
                for i, palace in enumerate(luo8):
                    src_idx = (i - offset) % n
                    src_palace = luo8[src_idx]
                    tian_pan[palace] = di_pan.get(src_palace, '')
                # 中宫寄宫（阳遁寄坤二宫，阴遁寄巽四宫，与八神/值符寄宫规则一致）
                tian_pan[5] = tian_pan.get(_zhong_gong_ji, di_pan.get(5, ''))

                # 九星也按同样偏移旋转
                new_jiu_xing = {}
                for i, palace in enumerate(luo8):
                    src_idx = (i - offset) % n
                    new_jiu_xing[palace] = jiu_xing[luo8[src_idx]]
                new_jiu_xing[5] = '天禽'  # 中宫天禽不参与旋转，始终居中
                jiu_xing = new_jiu_xing

                # 八门也按同样偏移旋转
                new_ba_men = {}
                for i, palace in enumerate(luo8):
                    src_idx = (i - offset) % n
                    new_ba_men[palace] = ba_men[luo8[src_idx]]
                new_ba_men[5] = ''
                ba_men = new_ba_men
            else:
                logger.warning(f"_build_tian_pan: 时干'{hour_gan}'所在宫位{gong_int}不在洛书飞宫序列中，天盘不做旋转")
                tian_pan = dict(di_pan)
        else:
            logger.warning(f"_build_tian_pan: 时干'{hour_gan}'(查找'{lookup_gan}')未在地盘中找到对应宫位，天盘=地盘")
            tian_pan = dict(di_pan)

        return tian_pan, ba_men, jiu_xing

    def _build_ba_shen(self, yin_yang: str, zhi_fu_gong: int) -> dict:
        """分配八神（阳遁顺排，阴遁逆排）"""
        luo8 = self.LUO_SHU_8
        # 中宫5寄坤二宫（传统规则）
        effective_gong = (4 if yin_yang == '阴遁' else 2) if zhi_fu_gong == 5 else zhi_fu_gong
        start = luo8.index(effective_gong) if effective_gong in luo8 else 0
        gods = self.EIGHT_GODS

        ba_shen = {}
        for i, palace in enumerate(luo8):
            if yin_yang == '阳遁':
                god_idx = (i - start) % len(gods)
            else:
                # 阴遁：八神逆排（值符起始反向旋转）
                god_idx = (start - i) % len(gods)
            ba_shen[palace] = gods[god_idx]
        ba_shen[5] = ba_shen.get(4, '') if yin_yang == '阴遁' else ba_shen.get(2, '')  # 中五宫：阳遁寄坤二，阴遁寄巽四
        return ba_shen

    def _find_gong_for_gan(self, di_pan: dict, gan_zhi: str) -> int:
        """在地盘中找到天干所在宫位（甲需查找隐遁的六仪）"""
        gan = gan_zhi[0] if gan_zhi else ''
        zhi = gan_zhi[1] if len(gan_zhi) > 1 else ''
        lookup = self.JIA_HIDE.get(zhi, '戊') if gan == '甲' else gan
        for gong, yi in di_pan.items():
            if yi == lookup:
                return gong
        logger.warning(f"_find_gong_for_gan: 天干'{gan_zhi}'（查找'{lookup}'）未在地盘中找到，回退到坎一宫")
        return 1  # fallback

    def _calc_xun_kong(self, day_gan_zhi: str) -> dict:
        """计算日柱旬空（空亡地支）和旬首奇仪"""
        TIANGAN = self.TIAN_GAN
        DIZHI = self.DI_ZHI
        # 旬首对应的奇仪复用类级 JIA_HIDE 常量（消除重复定义）
        if len(day_gan_zhi) < 2:
            return {'xun_shou': '', 'kong_wang': [], 'hidden_yi': ''}
        gan_idx = TIANGAN.index(day_gan_zhi[0]) if day_gan_zhi[0] in TIANGAN else 0
        zhi_idx = DIZHI.index(day_gan_zhi[1]) if day_gan_zhi[1] in DIZHI else 0
        xun_start_zhi = (zhi_idx - gan_idx) % 12
        xun_shou_zhi = DIZHI[xun_start_zhi]
        xun_shou = TIANGAN[0] + xun_shou_zhi
        kong1 = DIZHI[(xun_start_zhi + 10) % 12]
        kong2 = DIZHI[(xun_start_zhi + 11) % 12]
        hidden_yi = self.JIA_HIDE.get(xun_shou_zhi, '戊')
        return {'xun_shou': xun_shou, 'kong_wang': [kong1, kong2], 'hidden_yi': hidden_yi}

    def _build_palaces(self, di_pan, tian_pan, ba_men, jiu_xing, ba_shen) -> list:
        """合并生成 9 宫数据列表"""
        palaces = []
        for gong in range(1, 10):
            palaces.append({
                'gong': gong,
                'name': self.PALACE_NAMES.get(gong, ''),
                'direction': self.PALACE_DIRECTIONS.get(gong, ''),
                'di_pan': di_pan.get(gong, ''),
                'tian_pan': tian_pan.get(gong, ''),
                'men': ba_men.get(gong, ''),
                'xing': jiu_xing.get(gong, ''),
                'shen': ba_shen.get(gong, ''),
            })
        return palaces

    def _analyze_ge_ju(self, palaces: list, ba_men: dict, jiu_xing: dict, ba_shen: dict, xun_kong: dict, day_gan_zhi: str = '', hour_gan_zhi: str = '', zhi_shi_door: str = '') -> dict:
        """奇门格局判断：识别吉格和凶格"""
        ji_ge = []   # 吉格
        xiong_ge = []  # 凶格

        # 防御：palaces为空时直接返回空结果
        if not palaces:
            return {'ji_ge': [], 'xiong_ge': [], 'kong_wang_gongs': [], 'zhi_shi_kong': False, 'summary': '无宫位数据'}

        # ---- 时运凶格（全局性，不依赖宫位） ----

        # 五不遇时：时干克日干，百事不宜，是奇门最基础的时运凶格之一
        # 规则：时干五行 克 日干五行（如日甲木时庚金→金克木）
        if day_gan_zhi and hour_gan_zhi:
            day_gan = day_gan_zhi[0]
            hour_gan = hour_gan_zhi[0]
            day_wx = self.GAN_WUXING.get(day_gan, '')
            hour_wx = self.GAN_WUXING.get(hour_gan, '')
            if hour_wx and day_wx and self.WUXING_KE.get(hour_wx) == day_wx:
                xiong_ge.append({'name': '五不遇时', 'gong': 0,
                                 'desc': f'时干{hour_gan}({hour_wx})克日干{day_gan}({day_wx})，百事不宜，谋事难成'})

        # ---- 格局检测常量已提升到类级别（见 QiMenEngine.XING_MAP 等）----

        # ---- 吉格/凶格检测（单次遍历9宫）----
        for p in palaces:
            g = p['gong']
            men = p.get('men', '')
            xing = p.get('xing', '')
            shen = p.get('shen', '')
            tp = p.get('tian_pan', '')
            dp = p.get('di_pan', '')

            # 吉格：三奇+八门组合（传统三遁格局：天遁丙+生门、地遁乙+开门、人遁丁+休门）
            # 天遁：丙奇+生门（天盘丙临地盘生门，谋事大吉，上天护佑）
            if tp == '丙' and men == '生门':
                ji_ge.append({'name': '天遁', 'gong': g, 'desc': f'丙奇临{men}，天遁大吉，上天护佑，谋事顺遂'})
            # 地遁：乙奇+开门（天盘乙临地盘开门，百事可为，地利人和）
            if tp == '乙' and men == '开门':
                ji_ge.append({'name': '地遁', 'gong': g, 'desc': f'乙奇临{men}，地遁大吉，百事可为，地利人和'})
            # 人遁：丁奇+休门（天盘丁临地盘休门，贵人相助，人事和谐）
            if tp == '丁' and men == '休门':
                ji_ge.append({'name': '人遁', 'gong': g, 'desc': f'丁奇临{men}，人遁大吉，贵人相助，人事和谐'})
            # 龙遁：乙奇+开门/休门+九天
            if tp == '乙' and men in ('开门', '休门') and shen == '九天':
                ji_ge.append({'name': '龙遁', 'gong': g, 'desc': f'乙奇+{men}+九天，飞龙在天，大吉'})
            # 虎遁：乙奇+开门/生门+白虎
            if tp == '乙' and men in ('开门', '生门') and shen == '白虎':
                ji_ge.append({'name': '虎遁', 'gong': g, 'desc': f'乙奇+{men}+白虎，威猛有力，利武事'})
            # 风遁：乙奇+休门/开门+天辅/天冲
            if tp == '乙' and men in ('休门', '开门') and xing in ('天辅', '天冲'):
                ji_ge.append({'name': '风遁', 'gong': g, 'desc': f'乙奇+{men}+{xing}，顺风得利，事遂心愿'})
            # 云遁：乙奇+生门+天芮/天柱
            if tp == '乙' and men == '生门' and xing in ('天芮', '天柱'):
                ji_ge.append({'name': '云遁', 'gong': g, 'desc': f'乙奇+生门+{xing}，云起龙骧，暗中有助'})

            # 凶格：门宫组合（门级格局，区别于下方干支级同名格局）
            if men == '景门' and g == 1:
                xiong_ge.append({'name': '朱雀投江（门级）', 'gong': g, 'desc': '景门入坎，文书有失'})
            if men == '死门' and g == 4:
                xiong_ge.append({'name': '螣蛇夭矫（门级）', 'gong': g, 'desc': '死门入巽，虚惊怪异'})

            # 天盘+地盘格局（十干克应）
            # ---- 六庚克应（庚为天乙飞符，奇门最重要凶干）----
            if tp == '庚' and dp == '丙':
                xiong_ge.append({'name': '太白入荧', 'gong': g, 'desc': '庚加丙，贼来为患，主外患内忧'})
            if tp == '丙' and dp == '庚':
                xiong_ge.append({'name': '荧入太白', 'gong': g, 'desc': '丙加庚，贼去门户破败，宜守不宜进'})
            if tp == '庚' and dp == '癸':
                xiong_ge.append({'name': '小格', 'gong': g, 'desc': '庚加癸，格局不通，谋事受阻'})
            # 庚加丁：大格（庚丁相刑，出行大凶）
            if tp == '庚' and dp == '丁':
                xiong_ge.append({'name': '大格', 'gong': g, 'desc': '庚加丁，大格出行凶，谋事不成'})
            # 庚加己：刑格（庚入己墓，主刑狱诉讼）
            if tp == '庚' and dp == '己':
                xiong_ge.append({'name': '刑格', 'gong': g, 'desc': '庚加己，刑格主官司刑狱，暗昧不明'})
            # 庚加辛：白虎出力（庚辛同类金气相搏，主刀刃伤灾）
            if tp == '庚' and dp == '辛':
                xiong_ge.append({'name': '白虎出力', 'gong': g, 'desc': '庚加辛，白虎出力，主刀刃相残，不可强为'})
            # 庚加壬：上格（庚壬相冲，主变动不安）
            if tp == '庚' and dp == '壬':
                xiong_ge.append({'name': '上格', 'gong': g, 'desc': '庚加壬，上格主变动不安，出行迷路'})
            # 庚加庚：太白同宫（庚庚自刑，战格，主兄弟失和、官灾横祸）
            if tp == '庚' and dp == '庚':
                xiong_ge.append({'name': '太白同宫', 'gong': g, 'desc': '庚加庚，太白同宫，官灾横祸，兄弟失和'})
            if tp == '丙' and dp == '辛':
                ji_ge.append({'name': '欢怡', 'gong': g, 'desc': '丙辛合化水，谋事有成'})
            if tp == '辛' and dp == '丙':
                ji_ge.append({'name': '欢怡', 'gong': g, 'desc': '辛丙合化水，以柔克刚'})
            if tp == '乙' and dp == '庚':
                ji_ge.append({'name': '奇合', 'gong': g, 'desc': '乙庚合化金，合作有利'})
            if tp == '庚' and dp == '乙':
                ji_ge.append({'name': '奇合', 'gong': g, 'desc': '庚乙合化金，刚柔相济'})
            # 天干五合：丁壬合化木、戊癸合化火（甲己为天地合德，见下方）
            if tp == '丁' and dp == '壬':
                ji_ge.append({'name': '丁壬合', 'gong': g, 'desc': '丁壬合化木，阴阳相合，和合之象'})
            if tp == '壬' and dp == '丁':
                ji_ge.append({'name': '丁壬合', 'gong': g, 'desc': '壬丁合化木，以阳配阴，相得益彰'})
            if tp == '戊' and dp == '癸':
                ji_ge.append({'name': '戊癸合', 'gong': g, 'desc': '戊癸合化火，刚柔互济，合作有利'})
            if tp == '癸' and dp == '戊':
                ji_ge.append({'name': '戊癸合', 'gong': g, 'desc': '癸戊合化火，以柔配刚，化险为夷'})
            if tp == '丙' and dp == '戊':
                ji_ge.append({'name': '飞鸟跌穴', 'gong': g, 'desc': '丙加戊，百事吉昌，如飞鸟归巢'})
            if tp == '戊' and dp == '丙':
                ji_ge.append({'name': '青龙返首', 'gong': g, 'desc': '戊加丙，贵人相助，逢凶化吉'})
            if tp == '辛' and dp == '乙':
                xiong_ge.append({'name': '白虎猖狂', 'gong': g, 'desc': '辛加乙，金木相克，主伤灾破败'})

            # ---- 丁癸干支级克应（区别于门级同名格局）----
            # 丁加癸：朱雀投江（干支级）——丁火入癸水，文书遗失，音信杳然
            if tp == '丁' and dp == '癸':
                xiong_ge.append({'name': '朱雀投江（干支级）', 'gong': g, 'desc': '丁加癸，朱雀投江，文书遗失，音信不通'})
            # 癸加丁：螣蛇夭矫（干支级）——癸水克丁火，虚惊怪异，文书官司
            if tp == '癸' and dp == '丁':
                xiong_ge.append({'name': '螣蛇夭矫（干支级）', 'gong': g, 'desc': '癸加丁，螣蛇夭矫，虚惊怪异，文书有灾'})

            # 击刑
            if tp in self.GAN_XING and self.GAN_XING[tp] == g:
                branch_name = self.GAN_XING_BRANCH.get(tp, self.XING_MAP.get(g, '中'))
                gong_name = self.PALACE_NAMES.get(g, f'{branch_name}宫')
                xiong_ge.append({'name': '击刑', 'gong': g, 'desc': f'{tp}落{gong_name}，刑伤之象'})

            # 入墓（排除三奇，三奇由 SAN_QI_MU 处理）
            if tp not in self.SAN_QI_MU and tp in self.GAN_MU and self.GAN_MU[tp] == g:
                xiong_ge.append({'name': '入墓', 'gong': g, 'desc': f'{tp}入墓，事有阻碍'})

            # 三奇入墓
            if tp in self.SAN_QI_MU and self.SAN_QI_MU[tp] == g:
                xiong_ge.append({'name': '三奇入墓', 'gong': g, 'desc': f'{tp}奇入墓，奇不显灵，百事不顺'})

            # 悖格：天盘克地盘（排除已有专用名称的组合）
            if tp and dp and (tp, dp) not in self.ALREADY_CHECKED:
                tp_wx = self.GAN_WUXING.get(tp, '')
                dp_wx = self.GAN_WUXING.get(dp, '')
                if tp_wx and dp_wx and self.WUXING_KE.get(tp_wx) == dp_wx:
                    xiong_ge.append({'name': '悖格', 'gong': g,
                                     'desc': f'{tp}({tp_wx})克{dp}({dp_wx})，天克地，行事多阻'})

            # 玉女守门：丁奇加值使门所在宫位（传统规则：丁奇落在值使门宫位）
            if zhi_shi_door and men == zhi_shi_door and tp == '丁':
                ji_ge.append({'name': '玉女守门', 'gong': g,
                              'desc': f'丁奇守值使{men}，百事皆宜，利于文书'})

            # 三奇得使：天盘乙/丙丁落在值使门所在宫位，为奇门大吉之格
            # 规则：天盘为三奇（乙丙丁）之一 + 该宫八门恰好是值使门
            # 含义：三奇得使，天地人三才相合，主凡事有贵人暗助，谋事易成
            # 注意：丁奇+值使门已由上方"玉女守门"单独判断，此处排除避免重复
            if zhi_shi_door and men == zhi_shi_door and tp in ('乙', '丙'):
                ji_ge.append({'name': '三奇得使', 'gong': g,
                              'desc': f'{tp}奇得值使{men}，三才相合，贵人暗助，百事可为'})

            # 天地合德
            if tp and dp and self.GAN_HE_GEDE.get(tp) == dp:
                ji_ge.append({'name': '天地合德', 'gong': g,
                              'desc': f'{tp}{dp}合，天地和合，谋事易成'})

            # ---- 新增格局：星门组合 ----
            # 天辅+杜门：文书有利
            if xing == '天辅' and men == '杜门':
                ji_ge.append({'name': '天辅杜门', 'gong': g, 'desc': '天辅星+杜门，利学业文书'})
            # 天心+开门：医疗大吉
            if xing == '天心' and men == '开门':
                ji_ge.append({'name': '天心开门', 'gong': g, 'desc': '天心星+开门，利医疗治病，百病消除'})
            # 天冲+伤门：武事大吉
            if xing == '天冲' and men == '伤门':
                ji_ge.append({'name': '天冲伤门', 'gong': g, 'desc': '天冲星+伤门，利武事征伐'})
            # 天蓬+休门：谋略大吉
            if xing == '天蓬' and men == '休门':
                xiong_ge.append({'name': '天蓬休门', 'gong': g, 'desc': '天蓬星+休门，主盗贼暗昧，利藏匿'})
            # 天芮+死门：疾病大凶
            if xing == '天芮' and men == '死门':
                xiong_ge.append({'name': '天芮死门', 'gong': g, 'desc': '天芮星+死门，主疾病缠身，大凶'})
            # 天柱+惊门：口舌凶
            if xing == '天柱' and men == '惊门':
                xiong_ge.append({'name': '天柱惊门', 'gong': g, 'desc': '天柱星+惊门，口舌官非，惊恐不安'})
            # 天英+景门：文书虚花
            if xing == '天英' and men == '景门':
                xiong_ge.append({'name': '天英景门', 'gong': g, 'desc': '天英星+景门，文书虚花不实，血光之灾'})

            # ---- 新增格局：八神特殊组合 ----
            # 值符+开门：大吉
            if shen == '值符' and men == '开门':
                ji_ge.append({'name': '值符开门', 'gong': g, 'desc': '值符临开门，百事大吉，贵人扶持'})
            # 九天+开门/休门：大吉
            if shen == '九天' and men in ('开门', '休门'):
                ji_ge.append({'name': '九天吉门', 'gong': g, 'desc': f'九天临{men}，飞黄腾达，大吉'})
            # 九地+死门/杜门：暗中阻滞
            if shen == '九地' and men in ('死门', '杜门'):
                xiong_ge.append({'name': '九地凶门', 'gong': g, 'desc': f'九地临{men}，暗中阻滞，事多不顺'})
            # 白虎+伤门/死门：血光大凶
            if shen == '白虎' and men in ('伤门', '死门'):
                xiong_ge.append({'name': '白虎凶门', 'gong': g, 'desc': f'白虎临{men}，主血光伤灾，大凶'})
            # 玄武+休门：暗中得利
            if shen == '玄武' and men == '休门':
                ji_ge.append({'name': '玄武休门', 'gong': g, 'desc': '玄武临休门，暗中得利，投机有利'})
            # 太阴+杜门：谋划有利
            if shen == '太阴' and men == '杜门':
                ji_ge.append({'name': '太阴杜门', 'gong': g, 'desc': '太阴临杜门，暗中谋划有利'})
            # 六合+开门：合作大吉
            if shen == '六合' and men == '开门':
                ji_ge.append({'name': '六合开门', 'gong': g, 'desc': '六合临开门，合作谈判大吉'})

            # ---- 新增格局：天盘地盘特殊组合 ----
            # 乙+辛：日奇入墓（乙木入辛金墓）
            if tp == '乙' and dp == '辛':
                xiong_ge.append({'name': '日奇入墓', 'gong': g, 'desc': '乙加辛，日奇入墓，主暗昧不明'})
            # 丙+己：丙奇入墓
            if tp == '丙' and dp == '己':
                xiong_ge.append({'name': '丙奇入墓', 'gong': g, 'desc': '丙加己，月奇入墓，主事受困'})
            # 丁+庚：星奇入墓
            if tp == '丁' and dp == '庚':
                xiong_ge.append({'name': '星奇入墓', 'gong': g, 'desc': '丁加庚，星奇入墓，文书受阻'})
            # 己+丙：地户埋光
            if tp == '己' and dp == '丙':
                xiong_ge.append({'name': '地户埋光', 'gong': g, 'desc': '己加丙，地户埋光，暗昧不明'})
            # 辛+丁：狱神得奇
            if tp == '辛' and dp == '丁':
                ji_ge.append({'name': '狱神得奇', 'gong': g, 'desc': '辛加丁，狱神得奇，囚人获释，讼事有利'})
            # 壬+丙：水蛇入火
            if tp == '壬' and dp == '丙':
                xiong_ge.append({'name': '水蛇入火', 'gong': g, 'desc': '壬加丙，水蛇入火，官灾刑禁'})
            # 癸+戊：天网四张
            if tp == '癸' and dp == '戊':
                xiong_ge.append({'name': '天网四张', 'gong': g, 'desc': '癸加戊，天网四张，出行大凶，百事不利'})

            # ---- #37-46: 天干克应扩展 ----
            # 辛加丁：狱神得奇扩展（辛金见丁火，以柔制刚）
            if tp == '辛' and dp == '丁':
                if not any(ge['name'] == '狱神得奇' and ge['gong'] == g for ge in ji_ge):
                    ji_ge.append({'name': '辛加丁', 'gong': g, 'desc': '辛加丁，狱神得奇，囚人获释'})
            # 丁加辛：朱雀投江变格（丁火入辛金，文书有利）
            if tp == '丁' and dp == '辛':
                ji_ge.append({'name': '丁加辛', 'gong': g, 'desc': '丁加辛，星奇入墓变格，文书有救'})
            # 乙加丙：奇仪顺遂（乙木生丙火，谋事顺遂）
            if tp == '乙' and dp == '丙':
                ji_ge.append({'name': '乙加丙', 'gong': g, 'desc': '乙加丙，奇仪顺遂，谋事有利'})
            # 丙加乙：日月并行（丙火配乙木，光明正大）
            if tp == '丙' and dp == '乙':
                ji_ge.append({'name': '丙加乙', 'gong': g, 'desc': '丙加乙，日月并行，光明正大'})
            # 壬加乙：天罡阻路（壬水克乙木，谋事受阻）
            if tp == '壬' and dp == '乙':
                xiong_ge.append({'name': '壬加乙', 'gong': g, 'desc': '壬加乙，天罡阻路，谋事受阻'})
            # 癸加乙：华盖逢星变格（癸水克乙木，暗昧不明）
            if tp == '癸' and dp == '乙':
                xiong_ge.append({'name': '癸加乙', 'gong': g, 'desc': '癸加乙，华盖逢星，暗昧不明'})
            # 戊加丁：青龙耀明（戊土配丁火，贵人相助）
            if tp == '戊' and dp == '丁':
                ji_ge.append({'name': '戊加丁', 'gong': g, 'desc': '戊加丁，青龙耀明，贵人相助'})
            # 丁加戊：星奇临门（丁火生戊土，文书有利）
            if tp == '丁' and dp == '戊':
                ji_ge.append({'name': '丁加戊', 'gong': g, 'desc': '丁加戊，星奇临门，文书有利'})
            # 己加乙：地户逢星变格（己土克乙木，暗昧阻滞）
            if tp == '己' and dp == '乙':
                xiong_ge.append({'name': '己加乙', 'gong': g, 'desc': '己加乙，地户逢星，暗昧阻滞'})
            # 庚加戊：太白入戊（庚金克戊土，大格凶）
            if tp == '庚' and dp == '戊':
                xiong_ge.append({'name': '庚加戊', 'gong': g, 'desc': '庚加戊，太白入戊，官灾横祸'})
            # 戊加庚：戊入庚位（戊土逢庚金，值符飞宫凶）
            if tp == '戊' and dp == '庚':
                xiong_ge.append({'name': '戊加庚', 'gong': g, 'desc': '戊加庚，值符飞宫，主变动凶'})
            # 壬加丁：天罡克星奇（壬水克丁火，文书凶）
            if tp == '壬' and dp == '丁':
                xiong_ge.append({'name': '壬加丁', 'gong': g, 'desc': '壬加丁，天罡克星奇，文书有灾'})
            # 癸加丙：华盖入丙（癸水克丙火，凶）
            if tp == '癸' and dp == '丙':
                xiong_ge.append({'name': '癸加丙', 'gong': g, 'desc': '癸加丙，华盖悖师，主凶'})
            # 辛加壬：天牢自刑（辛金壬水，凶）
            if tp == '辛' and dp == '壬':
                xiong_ge.append({'name': '辛加壬', 'gong': g, 'desc': '辛加壬，天牢自刑，凶'})
            # 壬加辛：天罡自刑（壬水辛金，凶）
            if tp == '壬' and dp == '辛':
                xiong_ge.append({'name': '壬加辛', 'gong': g, 'desc': '壬加辛，螣蛇相缠，凶'})

        # 旬空宫
        kong_wang = xun_kong.get('kong_wang', []) if xun_kong else []
        kong_gongs = []
        for zhi in kong_wang:
            if zhi in self.ZHI_TO_GONG_NUM:
                kong_gongs.append(self.ZHI_TO_GONG_NUM[zhi])

        # 标注落在空亡宫的格局（奇门传统：空亡宫格局效力减半或无效）
        for ge in ji_ge:
            if ge.get('gong') in kong_gongs:
                ge['in_kong_wang'] = True
                ge['desc'] += '【落空亡，效力减半】'
        for ge in xiong_ge:
            if ge.get('gong') in kong_gongs:
                ge['in_kong_wang'] = True
                ge['desc'] += '【落空亡，凶性减轻】'

        # 值使门遇空亡
        zhi_shi_kong = False
        if zhi_shi_door and kong_gongs:
            # 值使门所在宫如在空亡中，谋事不利
            zhi_shi_gong = None
            for p in palaces:
                if p.get('men') == zhi_shi_door:
                    zhi_shi_gong = p.get('gong')
                    break
            if zhi_shi_gong in kong_gongs:
                zhi_shi_kong = True
                xiong_ge.append({'name': '值使落空', 'gong': zhi_shi_gong,
                                 'in_kong_wang': True,
                                 'desc': f'值使门{zhi_shi_door}落空亡宫，谋事难成，虚花不实'})

        return {
            'ji_ge': ji_ge,
            'xiong_ge': xiong_ge,
            'kong_wang_gongs': kong_gongs,
            'zhi_shi_kong': zhi_shi_kong,
            'summary': (
                f"吉格{len(ji_ge)}个，凶格{len(xiong_ge)}个"
                + (f"，旬空宫：{kong_gongs}" if kong_gongs else "")
                + (f"，值使门落空" if zhi_shi_kong else "")
            ),
        }

    def _build_san_pan_summary(self, palaces: list) -> dict:
        """天地人三盘摘要：每宫的天盘/地盘/八门/九星/八神一句话"""
        summary = {}
        for p in palaces:
            gong = p['gong']
            if gong == 5:  # 中宫跳过
                continue
            name = p.get('name', '')
            direction = p.get('direction', '')
            di = p.get('di_pan', '')
            tian = p.get('tian_pan', '')
            men = p.get('men', '')
            xing = p.get('xing', '')
            shen = p.get('shen', '')
            summary[str(gong)] = {
                'name': name,
                'direction': direction,
                'tian_di': f'天{tian}地{di}',  # 天盘+地盘
                'men_xing_shen': f'{men}/{xing}/{shen}',  # 门/星/神
            }
        return summary

    def _build_liunian(self, solar_dt: datetime, di_pan: dict, tian_pan: dict, palaces: list) -> dict:
        """流年太岁分析 — 当前年份太岁落在哪个宫，与各宫的关系"""
        try:
            from lunar_python import Solar
            # 使用查询时间而非系统当前时间，确保历史/未来日期排盘准确
            solar = Solar.fromYmdHms(solar_dt.year, solar_dt.month, solar_dt.day, solar_dt.hour, solar_dt.minute, solar_dt.second)
            lunar = solar.getLunar()
            year_gan = lunar.getYearGan()
            year_zhi = lunar.getYearZhi()
            year_ganzhi = f'{year_gan}{year_zhi}'

            # 太岁地支→宫位（默认坎一宫，确保gong始终为有效宫号1-9）
            tai_sui_gong = self.ZHI_TO_GONG_NUM.get(year_zhi, 1)

            # 找到太岁宫的信息
            tai_sui_palace = None
            for p in palaces:
                if p.get('gong') == tai_sui_gong:
                    tai_sui_palace = p
                    break

            return {
                'year': solar_dt.year,
                'year_ganzhi': year_ganzhi,
                'year_gan': year_gan,
                'year_zhi': year_zhi,
                'tai_sui_gong': tai_sui_gong,
                'tai_sui_palace_name': tai_sui_palace.get('name', '') if tai_sui_palace else '',
                'tai_sui_direction': tai_sui_palace.get('direction', '') if tai_sui_palace else '',
                'tai_sui_men': tai_sui_palace.get('men', '') if tai_sui_palace else '',
                'tai_sui_xing': tai_sui_palace.get('xing', '') if tai_sui_palace else '',
                'tai_sui_shen': tai_sui_palace.get('shen', '') if tai_sui_palace else '',
            }
        except Exception as e:
            logger.debug(f"流年太岁分析异常: {e}")
            return {}

    def _analyze_palace_details(self, palaces: list) -> list:
        """宫位详细分析：每个宫的门星神五行、旺衰、吉凶"""
        details = []
        for p in palaces:
            g = p['gong']
            men = p.get('men', '')
            xing = p.get('xing', '')
            shen = p.get('shen', '')
            di = p.get('di_pan', '')
            tian = p.get('tian_pan', '')

            men_wx = self.MEN_WUXING.get(men, '')
            star_wx = self.STAR_WUXING.get(xing, '')
            gong_wx = self.GONG_WUXING.get(g, '')

            # 门旺衰
            men_wang = self._calc_wang_shuai(men_wx, gong_wx)
            # 星旺衰
            star_wang = self._calc_wang_shuai(star_wx, gong_wx)

            # 门宫关系（门五行克宫五行=门迫，宫五行克门五行=门制）
            men_gong_relation = ''
            if men_wx and gong_wx:
                if self.WUXING_KE.get(men_wx) == gong_wx:
                    men_gong_relation = '门迫'
                elif self.WUXING_KE.get(gong_wx) == men_wx:
                    men_gong_relation = '门制'

            # 天盘地盘五行关系
            di_wx = self.GAN_WUXING.get(di, '')
            tian_wx = self.GAN_WUXING.get(tian, '')
            tiandi_relation = ''
            if tian_wx and di_wx:
                if tian_wx == di_wx:
                    tiandi_relation = '比和'
                elif self.WUXING_SHENG.get(tian_wx) == di_wx:
                    tiandi_relation = '天盘生地盘'
                elif self.WUXING_SHENG.get(di_wx) == tian_wx:
                    tiandi_relation = '地盘生天盘'
                elif self.WUXING_KE.get(tian_wx) == di_wx:
                    tiandi_relation = '天盘克地盘'
                elif self.WUXING_KE.get(di_wx) == tian_wx:
                    tiandi_relation = '地盘克天盘'

            details.append({
                'gong': g,
                'men_wuxing': men_wx,
                'star_wuxing': star_wx,
                'gong_wuxing': gong_wx,
                'men_wang_shuai': men_wang,
                'star_wang_shuai': star_wang,
                'men_gong_relation': men_gong_relation,
                'tiandi_relation': tiandi_relation,
                'men_jixiong': self.MEN_JIXIONG.get(men, ''),
                'star_jixiong': self.STAR_JIXIONG.get(xing, ''),
            })
        return details

    def _calc_wang_shuai(self, wuxing: str, gong_wuxing: str) -> str:
        """计算五行在宫位的旺衰状态"""
        if not wuxing or not gong_wuxing:
            return ''
        if wuxing == gong_wuxing:
            return '旺'
        if self.WUXING_SHENG.get(gong_wuxing) == wuxing:
            return '相'  # 宫生门/星
        if self.WUXING_SHENG.get(wuxing) == gong_wuxing:
            return '休'  # 门/星生宫（泄气）
        if self.WUXING_KE.get(wuxing) == gong_wuxing:
            return '囚'  # 门/星克宫
        if self.WUXING_KE.get(gong_wuxing) == wuxing:
            return '死'  # 宫克门/星
        return ''

    def _analyze_fuyin_fanyin(self, di_pan: dict, tian_pan: dict) -> dict:
        """判断伏吟/反吟
        伏吟：天盘=地盘（不动）
        反吟：天盘地支冲地盘地支
        """
        if not di_pan or not tian_pan:
            return {'type': '', 'desc': ''}

        # 统计天盘地支与地盘地支的关系
        match_count = 0
        chong_count = 0
        total = 0
        for gong in range(1, 10):
            dp = di_pan.get(gong, '')
            tp = tian_pan.get(gong, '')
            if not dp or not tp:
                continue
            total += 1
            if dp == tp:
                match_count += 1
            # 检查天干相冲
            if dp in self.GAN_CHONG and self.GAN_CHONG[dp] == tp:
                chong_count += 1

        if match_count >= 6:
            return {'type': '伏吟', 'desc': f'天盘地盘相同{match_count}宫，伏吟局，主静守、不动'}
        if chong_count >= 6:
            return {'type': '反吟', 'desc': f'天盘地盘相冲{chong_count}宫，反吟局，主动荡、变动'}
        if match_count >= 4:
            return {'type': '半伏吟', 'desc': f'天盘地盘相同{match_count}宫，半伏吟，主犹豫不决'}
        if chong_count >= 4:
            return {'type': '半反吟', 'desc': f'天盘地盘相冲{chong_count}宫，半反吟，主事有反复'}

        return {'type': '', 'desc': ''}

    def _analyze_men_po(self, palaces: list) -> list:
        """门迫分析：八门五行克所落宫位五行"""
        men_po_list = []
        for p in palaces:
            g = p['gong']
            men = p.get('men', '')
            if not men or g == 5:
                continue
            men_wx = self.MEN_WUXING.get(men, '')
            gong_wx = self.GONG_WUXING.get(g, '')
            if men_wx and gong_wx and self.WUXING_KE.get(men_wx) == gong_wx:
                men_po_list.append({
                    'gong': g,
                    'men': men,
                    'men_wuxing': men_wx,
                    'gong_wuxing': gong_wx,
                    'desc': f'{men}({men_wx})迫{self.PALACE_NAMES.get(g, "")}({gong_wx})，门克宫，主事受阻'
                })
        return men_po_list

    def _find_sanqi_positions(self, di_pan: dict, tian_pan: dict) -> dict:
        """找出三奇六仪在天地盘的位置"""
        result = {'di_pan': {}, 'tian_pan': {}}
        for gong, yi in di_pan.items():
            if yi in ('乙', '丙', '丁'):
                result['di_pan'][yi] = gong
            elif yi in ('戊', '己', '庚', '辛', '壬', '癸'):
                result['di_pan'][yi] = gong
        for gong, yi in tian_pan.items():
            if yi in ('乙', '丙', '丁'):
                result['tian_pan'][yi] = gong
            elif yi in ('戊', '己', '庚', '辛', '壬', '癸'):
                result['tian_pan'][yi] = gong
        return result

    def _analyze_yong_shen(self, palaces: list, hour_gan_zhi: str, day_gan_zhi: str) -> dict:
        """用神落宫分析：时干落宫为用神宫，分析其门星神组合"""
        if not palaces:
            return {}

        # 时干落宫
        hour_gan = hour_gan_zhi[0] if hour_gan_zhi else ''
        day_gan = day_gan_zhi[0] if day_gan_zhi else ''

        # 找时干落宫
        hour_gong = None
        for p in palaces:
            if p.get('tian_pan') == hour_gan or p.get('di_pan') == hour_gan:
                hour_gong = p
                break

        # 找日干落宫
        day_gong = None
        for p in palaces:
            if p.get('tian_pan') == day_gan or p.get('di_pan') == day_gan:
                day_gong = p
                break

        result = {
            'hour_gan': hour_gan,
            'day_gan': day_gan,
        }

        if hour_gong:
            result['hour_gong'] = {
                'gong': hour_gong['gong'],
                'name': hour_gong.get('name', ''),
                'men': hour_gong.get('men', ''),
                'xing': hour_gong.get('xing', ''),
                'shen': hour_gong.get('shen', ''),
                'tian_pan': hour_gong.get('tian_pan', ''),
                'di_pan': hour_gong.get('di_pan', ''),
                # #37: 用神宫旺衰分析
                'men_jixiong': self.MEN_JIXIONG.get(hour_gong.get('men', ''), ''),
                'star_jixiong': self.STAR_JIXIONG.get(hour_gong.get('xing', ''), ''),
                'men_wuxing': self.MEN_WUXING.get(hour_gong.get('men', ''), ''),
                'star_wuxing': self.STAR_WUXING.get(hour_gong.get('xing', ''), ''),
                'gong_wuxing': self.GONG_WUXING.get(hour_gong['gong'], ''),
            }
        if day_gong:
            result['day_gong'] = {
                'gong': day_gong['gong'],
                'name': day_gong.get('name', ''),
                'men': day_gong.get('men', ''),
                'xing': day_gong.get('xing', ''),
                'shen': day_gong.get('shen', ''),
                'tian_pan': day_gong.get('tian_pan', ''),
                'di_pan': day_gong.get('di_pan', ''),
                # #38: 日干宫旺衰分析
                'men_jixiong': self.MEN_JIXIONG.get(day_gong.get('men', ''), ''),
                'star_jixiong': self.STAR_JIXIONG.get(day_gong.get('xing', ''), ''),
                'men_wuxing': self.MEN_WUXING.get(day_gong.get('men', ''), ''),
                'star_wuxing': self.STAR_WUXING.get(day_gong.get('xing', ''), ''),
                'gong_wuxing': self.GONG_WUXING.get(day_gong['gong'], ''),
            }

        # #39: 时干日干关系分析
        if hour_gong and day_gong:
            hg = hour_gong['gong']
            dg = day_gong['gong']
            hg_wx = self.GONG_WUXING.get(hg, '')
            dg_wx = self.GONG_WUXING.get(dg, '')
            relation = ''
            if hg_wx and dg_wx:
                if hg_wx == dg_wx:
                    relation = '比和'
                elif self.WUXING_SHENG.get(hg_wx) == dg_wx:
                    relation = '时干宫生日干宫'
                elif self.WUXING_SHENG.get(dg_wx) == hg_wx:
                    relation = '日干宫生时干宫'
                elif self.WUXING_KE.get(hg_wx) == dg_wx:
                    relation = '时干宫克日干宫'
                elif self.WUXING_KE.get(dg_wx) == hg_wx:
                    relation = '日干宫克时干宫'
            result['hour_day_relation'] = relation
            # #40: 时干日干是否同宫
            result['same_palace'] = hg == dg

        return result

    def _calc_ge_ju_strength(self, ge_ju_analysis: dict) -> dict:
        """计算格局力量统计"""
        if not ge_ju_analysis:
            return {'ji_score': 0, 'xiong_score': 0, 'level': '中', 'summary': ''}

        ji_ge = ge_ju_analysis.get('ji_ge', [])
        xiong_ge = ge_ju_analysis.get('xiong_ge', [])

        ji_score = 0
        xiong_score = 0

        for ge in ji_ge:
            name = ge.get('name', '')
            level = self.GE_JU_LEVEL.get(name, '中')
            if level == '大吉':
                ji_score += 3
            elif level == '吉':
                ji_score += 2
            else:
                ji_score += 1
            # 空亡减半
            if ge.get('in_kong_wang'):
                ji_score -= 1

        for ge in xiong_ge:
            name = ge.get('name', '')
            level = self.GE_JU_LEVEL.get(name, '中')
            if level == '大凶':
                xiong_score += 3
            elif level == '凶':
                xiong_score += 2
            else:
                xiong_score += 1
            # 空亡减轻
            if ge.get('in_kong_wang'):
                xiong_score -= 1

        net = ji_score - xiong_score
        if net >= 6:
            level = '大吉'
        elif net >= 3:
            level = '吉'
        elif net >= 0:
            level = '中'
        elif net >= -3:
            level = '凶'
        else:
            level = '大凶'

        return {
            'ji_score': ji_score,
            'xiong_score': xiong_score,
            'net_score': net,
            'level': level,
            'ji_count': len(ji_ge),
            'xiong_count': len(xiong_ge),
            'summary': f'吉{len(ji_ge)}格(+{ji_score})/凶{len(xiong_ge)}格(-{xiong_score})=净值{net}，{level}'
        }

    # ---- #41-46: 门星神组合详细解读 ----
    def _analyze_men_xing_shen_combo(self, palaces: list) -> list:
        """#41: 门星神组合详细解读：每个宫位的门/星/神三者组合含义"""
        combos = []
        for p in palaces:
            g = p['gong']
            men = p.get('men', '')
            xing = p.get('xing', '')
            shen = p.get('shen', '')
            if g == 5 or not men:
                continue

            men_jx = self.MEN_JIXIONG.get(men, '')
            star_jx = self.STAR_JIXIONG.get(xing, '')
            # 八神吉凶
            SHEN_JIXIONG = {
                '值符': '吉', '螣蛇': '凶', '太阴': '吉', '六合': '吉',
                '白虎': '凶', '玄武': '凶', '九地': '中', '九天': '吉'
            }
            shen_jx = SHEN_JIXIONG.get(shen, '')

            # 综合评分
            score = 0
            if men_jx == '吉': score += 1
            elif men_jx == '凶': score -= 1
            if star_jx == '吉': score += 1
            elif star_jx == '凶': score -= 1
            if shen_jx == '吉': score += 1
            elif shen_jx == '凶': score -= 1

            if score >= 2:
                level = '大吉'
            elif score == 1:
                level = '吉'
            elif score == 0:
                level = '中'
            elif score == -1:
                level = '凶'
            else:
                level = '大凶'

            combos.append({
                'gong': g, 'men': men, 'xing': xing, 'shen': shen,
                'men_jixiong': men_jx, 'star_jixiong': star_jx,
                'shen_jixiong': shen_jx, 'score': score, 'level': level,
            })
        return combos

    # #42: 天干阴阳属性分析
    GAN_YINYANG_DETAIL = {
        '甲': {'阴阳': '阳', '五行': '木', '方位': '东', '类象': '栋梁、头领、贵人'},
        '乙': {'阴阳': '阴', '五行': '木', '方位': '东', '类象': '花草、女人、柔顺'},
        '丙': {'阴阳': '阳', '五行': '火', '方位': '南', '类象': '太阳、权威、光明'},
        '丁': {'阴阳': '阴', '五行': '火', '方位': '南', '类象': '星火、文书、希望'},
        '戊': {'阴阳': '阳', '五行': '土', '方位': '中', '类象': '大地、稳固、资本'},
        '己': {'阴阳': '阴', '五行': '土', '方位': '中', '类象': '田园、私有、暗昧'},
        '庚': {'阴阳': '阳', '五行': '金', '方位': '西', '类象': '刀剑、阻碍、敌人'},
        '辛': {'阴阳': '阴', '五行': '金', '方位': '西', '类象': '珠宝、错误、变革'},
        '壬': {'阴阳': '阳', '五行': '水', '方位': '北', '类象': '大海、流动、天牢'},
        '癸': {'阴阳': '阴', '五行': '水', '方位': '北', '类象': '雨露、天网、暗昧'},
    }

    # #43: 八门详细含义
    MEN_DETAIL = {
        '休门': {'五行': '水', '吉凶': '吉', '类象': '休息、安逸、贵人', '求财': '利', '出行': '吉', '疾病': '可愈'},
        '生门': {'五行': '土', '吉凶': '吉', '类象': '生长、利润、田宅', '求财': '大利', '出行': '吉', '疾病': '可愈'},
        '伤门': {'五行': '木', '吉凶': '凶', '类象': '伤灾、争斗、索取', '求财': '凶', '出行': '不利', '疾病': '凶'},
        '杜门': {'五行': '木', '吉凶': '凶', '类象': '闭塞、隐藏、保密', '求财': '不利', '出行': '阻滞', '疾病': '暗疾'},
        '景门': {'五行': '火', '吉凶': '中', '类象': '文书、考试、血光', '求财': '中平', '出行': '中平', '疾病': '血光'},
        '死门': {'五行': '土', '吉凶': '凶', '类象': '死亡、终结、坟墓', '求财': '大凶', '出行': '大凶', '疾病': '凶'},
        '惊门': {'五行': '金', '吉凶': '凶', '类象': '惊恐、口舌、官司', '求财': '不利', '出行': '惊恐', '疾病': '惊悸'},
        '开门': {'五行': '金', '吉凶': '吉', '类象': '开始、公开、事业', '求财': '利', '出行': '大吉', '疾病': '可愈'},
    }

    # #44: 九星详细含义
    STAR_DETAIL = {
        '天蓬': {'五行': '水', '吉凶': '凶', '类象': '盗贼、暗昧、大智慧', '求财': '凶', '疾病': '暗疾'},
        '天芮': {'五行': '土', '吉凶': '凶', '类象': '疾病、阴柔、学习', '求财': '不利', '疾病': '大凶'},
        '天冲': {'五行': '木', '吉凶': '吉', '类象': '冲击、武勇、征伐', '求财': '中平', '疾病': '可愈'},
        '天辅': {'五行': '木', '吉凶': '吉', '类象': '文采、教育、辅佐', '求财': '利', '疾病': '可愈'},
        '天禽': {'五行': '土', '吉凶': '吉', '类象': '中央、统领、正位', '求财': '利', '疾病': '中平'},
        '天心': {'五行': '金', '吉凶': '吉', '类象': '医卜、领导、决策', '求财': '大利', '疾病': '可愈'},
        '天柱': {'五行': '金', '吉凶': '凶', '类象': '口舌、惊恐、破损', '求财': '不利', '疾病': '凶'},
        '天任': {'五行': '土', '吉凶': '吉', '类象': '田宅、厚德、承载', '求财': '利', '疾病': '中平'},
        '天英': {'五行': '火', '吉凶': '中', '类象': '光明、文化、血光', '求财': '中平', '疾病': '血光'},
    }

    # #45: 八神详细含义
    SHEN_DETAIL = {
        '值符': {'五行': '土', '吉凶': '大吉', '类象': '贵人、首领、权柄', '出行': '大吉', '求财': '利'},
        '螣蛇': {'五行': '火', '吉凶': '凶', '类象': '惊恐、怪异、缠绕', '出行': '不利', '求财': '虚花'},
        '太阴': {'五行': '金', '吉凶': '吉', '类象': '阴私、谋划、暗助', '出行': '暗中吉', '求财': '暗财'},
        '六合': {'五行': '木', '吉凶': '吉', '类象': '合作、婚姻、交易', '出行': '同行吉', '求财': '合作利'},
        '白虎': {'五行': '金', '吉凶': '凶', '类象': '凶伤、血光、丧服', '出行': '大凶', '求财': '破财'},
        '玄武': {'五行': '水', '吉凶': '凶', '类象': '盗贼、暗昧、欺骗', '出行': '失物', '求财': '被骗'},
        '九地': {'五行': '土', '吉凶': '中', '类象': '坤地、暗中、守旧', '出行': '迟缓', '求财': '慢得'},
        '九天': {'五行': '金', '吉凶': '大吉', '类象': '乾天、光明、远行', '出行': '大吉', '求财': '大利'},
    }

    # #46: 天干长生十二宫详细解读
    CHANGSHENG_DETAIL = {
        '长生': {'含义': '万物初生，欣欣向荣', '吉凶': '吉'},
        '沐浴': {'含义': '初生洗礼，桃花之象', '吉凶': '中'},
        '冠带': {'含义': '渐趋成熟，学业有成', '吉凶': '吉'},
        '临官': {'含义': '事业初成，出仕为官', '吉凶': '大吉'},
        '帝旺': {'含义': '鼎盛之极，物极必反', '吉凶': '吉'},
        '衰': {'含义': '由盛转衰，力不从心', '吉凶': '凶'},
        '病': {'含义': '衰弱有病，困难重重', '吉凶': '凶'},
        '死': {'含义': '生机断绝，诸事不利', '吉凶': '大凶'},
        '墓': {'含义': '入库收藏，暗昧不明', '吉凶': '凶'},
        '绝': {'含义': '生机全无，但可绝处逢生', '吉凶': '凶'},
        '胎': {'含义': '孕育新生，暗中发展', '吉凶': '中'},
        '养': {'含义': '滋养成长，蓄势待发', '吉凶': '吉'},
    }

    # ---- #47-56: 神煞分析扩展 ----

    # #47: 马星（驿马）分析 - 基于日支三合
    MA_XING_MAP = {
        '申': '寅', '子': '寅', '辰': '寅',  # 申子辰→寅
        '寅': '申', '午': '申', '戌': '申',  # 寅午戌→申
        '亥': '巳', '卯': '巳', '未': '巳',  # 亥卯未→巳
        '巳': '亥', '酉': '亥', '丑': '亥',  # 巳酉丑→亥
    }

    def _analyze_ma_xing(self, day_gan_zhi: str, palaces: list) -> dict:
        """#47: 马星（驿马）落宫分析"""
        if len(day_gan_zhi) < 2:
            return {}
        day_zhi = day_gan_zhi[1]
        ma_zhi = self.MA_XING_MAP.get(day_zhi, '')
        if not ma_zhi:
            return {}
        ma_gong = self.ZHI_TO_GONG_NUM.get(ma_zhi, 0)
        ma_palace = None
        for p in palaces:
            if p['gong'] == ma_gong:
                ma_palace = p
                break
        return {
            'ma_zhi': ma_zhi,
            'ma_gong': ma_gong,
            'ma_palace_name': ma_palace.get('name', '') if ma_palace else '',
            'ma_men': ma_palace.get('men', '') if ma_palace else '',
            'ma_xing': ma_palace.get('xing', '') if ma_palace else '',
            'ma_shen': ma_palace.get('shen', '') if ma_palace else '',
            'desc': f'日支{day_zhi}马星在{ma_zhi}，落{ma_gong}宫',
        }

    # #48: 天乙贵人落宫分析
    TIANYI_MAP = {
        '甲': ['丑', '未'], '乙': ['子', '申'], '丙': ['亥', '酉'], '丁': ['亥', '酉'],
        '戊': ['丑', '未'], '己': ['子', '申'], '庚': ['丑', '未'], '辛': ['寅', '午'],
        '壬': ['卯', '巳'], '癸': ['卯', '巳'],
    }

    def _analyze_tianyi(self, day_gan_zhi: str, palaces: list) -> dict:
        """#48: 天乙贵人落宫分析"""
        if len(day_gan_zhi) < 1:
            return {}
        day_gan = day_gan_zhi[0]
        guiren_zhi_list = self.TIANYI_MAP.get(day_gan, [])
        result = {'day_gan': day_gan, 'guiren_positions': []}
        for gz in guiren_zhi_list:
            gong = self.ZHI_TO_GONG_NUM.get(gz, 0)
            palace = None
            for p in palaces:
                if p['gong'] == gong:
                    palace = p
                    break
            result['guiren_positions'].append({
                'zhi': gz, 'gong': gong,
                'men': palace.get('men', '') if palace else '',
                'xing': palace.get('xing', '') if palace else '',
                'shen': palace.get('shen', '') if palace else '',
            })
        return result

    # #49: 桃花落宫分析
    TAOHUA_MAP = {
        '申': '酉', '子': '酉', '辰': '酉',
        '寅': '卯', '午': '卯', '戌': '卯',
        '亥': '子', '卯': '子', '未': '子',
        '巳': '午', '酉': '午', '丑': '午',
    }

    def _analyze_taohua(self, day_gan_zhi: str, palaces: list) -> dict:
        """#49: 桃花落宫分析"""
        if len(day_gan_zhi) < 2:
            return {}
        day_zhi = day_gan_zhi[1]
        th_zhi = self.TAOHUA_MAP.get(day_zhi, '')
        if not th_zhi:
            return {}
        th_gong = self.ZHI_TO_GONG_NUM.get(th_zhi, 0)
        th_palace = None
        for p in palaces:
            if p['gong'] == th_gong:
                th_palace = p
                break
        return {
            'th_zhi': th_zhi,
            'th_gong': th_gong,
            'th_palace_name': th_palace.get('name', '') if th_palace else '',
            'th_men': th_palace.get('men', '') if th_palace else '',
            'th_xing': th_palace.get('xing', '') if th_palace else '',
            'th_shen': th_palace.get('shen', '') if th_palace else '',
            'desc': f'日支{day_zhi}桃花在{th_zhi}，落{th_gong}宫',
        }

    # #50: 空亡详细解读
    def _analyze_kong_wang_detail(self, xun_kong: dict, palaces: list) -> dict:
        """#50: 空亡详细解读"""
        if not xun_kong:
            return {}
        kong_wang = xun_kong.get('kong_wang', [])
        kong_detail = []
        for zhi in kong_wang:
            gong = self.ZHI_TO_GONG_NUM.get(zhi, 0)
            palace = None
            for p in palaces:
                if p['gong'] == gong:
                    palace = p
                    break
            kong_detail.append({
                'zhi': zhi, 'gong': gong,
                'palace_name': palace.get('name', '') if palace else '',
                'men': palace.get('men', '') if palace else '',
                'xing': palace.get('xing', '') if palace else '',
                'shen': palace.get('shen', '') if palace else '',
                'tian_pan': palace.get('tian_pan', '') if palace else '',
                'di_pan': palace.get('di_pan', '') if palace else '',
            })
        return {
            'xun_shou': xun_kong.get('xun_shou', ''),
            'hidden_yi': xun_kong.get('hidden_yi', ''),
            'kong_wang_zhi': kong_wang,
            'kong_detail': kong_detail,
            'desc': f'旬首{xun_kong.get("xun_shou", "")}，空亡{kong_wang}，遁{xun_kong.get("hidden_yi", "")}',
        }

    # ---- #51-56: 落宫分析扩展 ----

    # #51: 时干落宫详细分析
    def _analyze_hour_palace_detail(self, palaces: list, hour_gan_zhi: str) -> dict:
        """#51: 时干落宫详细分析 - 时干天盘/地盘分别在哪"""
        if not hour_gan_zhi or len(hour_gan_zhi) < 1:
            return {}
        hour_gan = hour_gan_zhi[0]
        tian_pos = None
        di_pos = None
        for p in palaces:
            if p.get('tian_pan') == hour_gan:
                tian_pos = p
            if p.get('di_pan') == hour_gan:
                di_pos = p
        result = {'hour_gan': hour_gan}
        if tian_pos:
            result['tian_pan_gong'] = {
                'gong': tian_pos['gong'], 'name': tian_pos.get('name', ''),
                'men': tian_pos.get('men', ''), 'xing': tian_pos.get('xing', ''),
                'shen': tian_pos.get('shen', ''),
            }
        if di_pos:
            result['di_pan_gong'] = {
                'gong': di_pos['gong'], 'name': di_pos.get('name', ''),
                'men': di_pos.get('men', ''), 'xing': di_pos.get('xing', ''),
                'shen': di_pos.get('shen', ''),
            }
        return result

    # #52: 日干落宫详细分析
    def _analyze_day_palace_detail(self, palaces: list, day_gan_zhi: str) -> dict:
        """#52: 日干落宫详细分析"""
        if not day_gan_zhi or len(day_gan_zhi) < 1:
            return {}
        day_gan = day_gan_zhi[0]
        tian_pos = None
        di_pos = None
        for p in palaces:
            if p.get('tian_pan') == day_gan:
                tian_pos = p
            if p.get('di_pan') == day_gan:
                di_pos = p
        result = {'day_gan': day_gan}
        if tian_pos:
            result['tian_pan_gong'] = {
                'gong': tian_pos['gong'], 'name': tian_pos.get('name', ''),
                'men': tian_pos.get('men', ''), 'xing': tian_pos.get('xing', ''),
                'shen': tian_pos.get('shen', ''),
            }
        if di_pos:
            result['di_pan_gong'] = {
                'gong': di_pos['gong'], 'name': di_pos.get('name', ''),
                'men': di_pos.get('men', ''), 'xing': di_pos.get('xing', ''),
                'shen': di_pos.get('shen', ''),
            }
        return result

    # #53: 三奇六仪组合吉凶
    SANQI_COMBO = {
        ('乙', '丙'): {'name': '奇仪顺遂', '吉凶': '吉', 'desc': '乙木生丙火，谋事顺遂'},
        ('乙', '丁'): {'name': '奇仪相合', '吉凶': '吉', 'desc': '乙丁相见，文书有利'},
        ('丙', '丁'): {'name': '星月交辉', '吉凶': '大吉', 'desc': '丙丁同见，光明正大'},
        ('乙', '戊'): {'name': '奇门合格', '吉凶': '吉', 'desc': '乙戊相见，合作有利'},
        ('丙', '壬'): {'name': '奇仪相冲', '吉凶': '凶', 'desc': '丙壬相冲，水火不容'},
        ('丁', '癸'): {'name': '奇仪相克', '吉凶': '凶', 'desc': '丁癸相克，文书有灾'},
    }

    # #54: 八门旺衰详细解读
    MEN_WANGSHUAI_DETAIL = {
        '旺': {'含义': '门气正旺，力量最强', '吉凶加成': '吉门更吉，凶门更凶'},
        '相': {'含义': '门气得助，力量较强', '吉凶加成': '吉门增吉，凶门增凶'},
        '休': {'含义': '门气休息，力量一般', '吉凶加成': '吉门减吉，凶门减凶'},
        '囚': {'含义': '门气受制，力量较弱', '吉凶加成': '吉门无力，凶门减力'},
        '死': {'含义': '门气死绝，力量最弱', '吉凶加成': '吉门无效，凶门无效'},
    }

    # #55: 九星旺衰详细解读
    STAR_WANGSHUAI_DETAIL = {
        '旺': {'含义': '星气正旺，力量最强', '吉凶加成': '吉星更吉，凶星更凶'},
        '相': {'含义': '星气得助，力量较强', '吉凶加成': '吉星增吉，凶星增凶'},
        '休': {'含义': '星气休息，力量一般', '吉凶加成': '吉星减吉，凶星减凶'},
        '囚': {'含义': '星气受制，力量较弱', '吉凶加成': '吉星无力，凶星减力'},
        '死': {'含义': '星气死绝，力量最弱', '吉凶加成': '吉星无效，凶星无效'},
    }

    # #56: 宫位综合评分
    def _calc_palace_score(self, palaces: list) -> list:
        """#56: 每个宫位综合评分（门+星+神+天地盘）"""
        scores = []
        for p in palaces:
            g = p['gong']
            if g == 5:
                continue
            men = p.get('men', '')
            xing = p.get('xing', '')
            shen = p.get('shen', '')
            tp = p.get('tian_pan', '')
            dp = p.get('di_pan', '')
            score = 0
            men_jx = self.MEN_JIXIONG.get(men, '')
            if men_jx == '吉': score += 2
            elif men_jx == '凶': score -= 2
            star_jx = self.STAR_JIXIONG.get(xing, '')
            if star_jx == '吉': score += 1
            elif star_jx == '凶': score -= 1
            SHEN_JX = {'值符': 2, '九天': 2, '太阴': 1, '六合': 1,
                       '九地': 0, '螣蛇': -1, '白虎': -2, '玄武': -1}
            score += SHEN_JX.get(shen, 0)
            if (tp, dp) in self.GAN_HE:
                score += 2
            if score >= 4: level = '大吉'
            elif score >= 2: level = '吉'
            elif score >= 0: level = '中'
            elif score >= -2: level = '凶'
            else: level = '大凶'
            scores.append({
                'gong': g, 'score': score, 'level': level,
                'men': men, 'xing': xing, 'shen': shen,
            })
        return scores

    def _analyze_tianmen_dihu(self, di_pan: dict, tian_pan: dict, solar_dt: datetime) -> dict:
        """天三门/地四户分析（传统奇门辅助占法）"""
        # 天三门：月将加时后，太冲/小吉/天罡所临之宫
        # 地四户：月建加时后，除/定/执/危 所临之地支
        # 简化实现：返回地支→宫位映射
        result = {'tian_sanmen': {}, 'di_sihu': {}}

        # 天三门对应地支
        # 太冲=卯, 小吉=未, 天罡=辰
        tianmen_zhi = {'太冲': '卯', '小吉': '未', '天罡': '辰'}
        for name, zhi in tianmen_zhi.items():
            gong = self.ZHI_TO_GONG_NUM.get(zhi, 0)
            result['tian_sanmen'][name] = {'zhi': zhi, 'gong': gong}

        return result

    # ---- Q5-Q6: 年命/月干落宫分析 ----
    def _analyze_nian_ming_gong(self, palaces: list, day_gan_zhi: str, year_gan_zhi: str) -> dict:
        """Q5: 年命落宫分析 - 年干所在宫位的门星神组合"""
        if not year_gan_zhi or not palaces:
            return {}
        year_gan = year_gan_zhi[0] if year_gan_zhi else ''
        year_gong = None
        for p in palaces:
            if p.get('tian_pan') == year_gan or p.get('di_pan') == year_gan:
                year_gong = p
                break
        if not year_gong:
            return {}
        men = year_gong.get('men', '')
        xing = year_gong.get('xing', '')
        shen = year_gong.get('shen', '')
        return {
            'year_gan': year_gan,
            'gong': year_gong['gong'],
            'name': year_gong.get('name', ''),
            'men': men, 'xing': xing, 'shen': shen,
            'men_jixiong': self.MEN_JIXIONG.get(men, ''),
            'star_jixiong': self.STAR_JIXIONG.get(xing, ''),
            'desc': f'年干{year_gan}落{year_gong.get("name", "")}，{men}/{xing}/{shen}',
        }

    def _analyze_yue_gan_gong(self, palaces: list, month_gan_zhi: str) -> dict:
        """Q6: 月干落宫分析"""
        if not month_gan_zhi or not palaces:
            return {}
        yue_gan = month_gan_zhi[0] if month_gan_zhi else ''
        yue_gong = None
        for p in palaces:
            if p.get('tian_pan') == yue_gan or p.get('di_pan') == yue_gan:
                yue_gong = p
                break
        if not yue_gong:
            return {}
        men = yue_gong.get('men', '')
        xing = yue_gong.get('xing', '')
        shen = yue_gong.get('shen', '')
        return {
            'yue_gan': yue_gan,
            'gong': yue_gong['gong'],
            'name': yue_gong.get('name', ''),
            'men': men, 'xing': xing, 'shen': shen,
            'men_jixiong': self.MEN_JIXIONG.get(men, ''),
            'star_jixiong': self.STAR_JIXIONG.get(xing, ''),
            'desc': f'月干{yue_gan}落{yue_gong.get("name", "")}，{men}/{xing}/{shen}',
        }

    # Q7: 全量十干克应（补充_analyze_ge_ju中未覆盖的组合）
    # Q10: 飞宫格/合格判断增强（已在_analyze_ge_ju中通过GAN_KE_DETAIL覆盖）

    # Q11: 用神旺衰等级判定
    def _calc_yong_shen_wang_shuai(self, yong_shen: dict) -> dict:
        """Q11: 用神落宫旺衰等级判定"""
        if not yong_shen or 'hour_gong' not in yong_shen:
            return {}
        hg = yong_shen['hour_gong']
        men_wx = hg.get('men_wuxing', '')
        star_wx = hg.get('star_wuxing', '')
        gong_wx = hg.get('gong_wuxing', '')
        men_wang = self._calc_wang_shuai(men_wx, gong_wx)
        star_wang = self._calc_wang_shuai(star_wx, gong_wx)
        men_jx = hg.get('men_jixiong', '')
        star_jx = hg.get('star_jixiong', '')
        # 综合等级
        score = 0
        if men_wang == '旺': score += 3
        elif men_wang == '相': score += 2
        elif men_wang == '休': score += 1
        elif men_wang == '死': score -= 2
        if star_wang == '旺': score += 2
        elif star_wang == '相': score += 1
        elif star_wang == '死': score -= 1
        if men_jx == '吉': score += 2
        elif men_jx == '凶': score -= 2
        if star_jx == '吉': score += 1
        elif star_jx == '凶': score -= 1
        if score >= 5: level = '大旺'
        elif score >= 3: level = '旺'
        elif score >= 0: level = '平'
        elif score >= -3: level = '衰'
        else: level = '大衰'
        return {
            'men_wang_shuai': men_wang, 'star_wang_shuai': star_wang,
            'score': score, 'level': level,
            'desc': f'用神宫门{men_wang}星{star_wang}，综合{level}(分{score})',
        }

    # Q12: 用神与太岁关系分析
    def _analyze_yong_shen_taisui(self, yong_shen: dict, liunian: dict) -> dict:
        """Q12: 用神落宫与太岁宫的关系"""
        if not yong_shen or 'hour_gong' not in yong_shen or not liunian:
            return {}
        hg = yong_shen['hour_gong']
        hg_gong = hg.get('gong', 0)
        ts_gong = liunian.get('tai_sui_gong', 0)
        hg_wx = self.GONG_WUXING.get(hg_gong, '')
        ts_wx = self.GONG_WUXING.get(ts_gong, '')
        relation = ''
        if hg_wx and ts_wx:
            if hg_wx == ts_wx: relation = '比和'
            elif self.WUXING_SHENG.get(hg_wx) == ts_wx: relation = '用神生太岁'
            elif self.WUXING_SHENG.get(ts_wx) == hg_wx: relation = '太岁生用神（大吉）'
            elif self.WUXING_KE.get(hg_wx) == ts_wx: relation = '用神克太岁（犯太岁）'
            elif self.WUXING_KE.get(ts_wx) == hg_wx: relation = '太岁克用神（不利）'
        return {
            'hour_gong': hg_gong, 'tai_sui_gong': ts_gong,
            'relation': relation,
            'desc': f'用神宫{hg_gong}({hg_wx})与太岁宫{ts_gong}({ts_wx})：{relation}',
        }

    # Q14: 伏吟/反吟详细分类
    def _analyze_fuyin_fanyin_detail(self, di_pan: dict, tian_pan: dict) -> dict:
        """Q14: 伏吟/反吟详细分类 - 门伏吟/星伏吟/神伏吟"""
        if not di_pan or not tian_pan:
            return {}
        fu_count = 0
        fan_count = 0
        fu_gongs = []
        fan_gongs = []
        for gong in range(1, 10):
            dp = di_pan.get(gong, '')
            tp = tian_pan.get(gong, '')
            if not dp or not tp:
                continue
            if dp == tp:
                fu_count += 1
                fu_gongs.append(gong)
            if dp in self.GAN_CHONG and self.GAN_CHONG[dp] == tp:
                fan_count += 1
                fan_gongs.append(gong)
        result = {'fu_count': fu_count, 'fan_count': fan_count}
        if fu_count >= 6:
            result['type'] = '全局伏吟'
            result['desc'] = f'{fu_count}宫伏吟，主静守不动，宜等待'
            result['level'] = '凶'
        elif fu_count >= 4:
            result['type'] = '局部伏吟'
            result['desc'] = f'{fu_count}宫伏吟，事有犹豫'
            result['level'] = '中'
        elif fan_count >= 6:
            result['type'] = '全局反吟'
            result['desc'] = f'{fan_count}宫反吟，主动荡变动'
            result['level'] = '凶'
        elif fan_count >= 4:
            result['type'] = '局部反吟'
            result['desc'] = f'{fan_count}宫反吟，事有反复'
            result['level'] = '中'
        else:
            result['type'] = '无'
            result['desc'] = '无伏吟反吟'
            result['level'] = '平'
        result['fu_gongs'] = fu_gongs
        result['fan_gongs'] = fan_gongs
        return result

    # Q18: 宫位综合评分改进（加入旺衰权重）
    def _calc_palace_score_v2(self, palaces: list) -> list:
        """Q18: 宫位综合评分V2 - 加入门星旺衰权重"""
        scores = []
        for p in palaces:
            g = p['gong']
            if g == 5:
                continue
            men = p.get('men', '')
            xing = p.get('xing', '')
            shen = p.get('shen', '')
            tp = p.get('tian_pan', '')
            dp = p.get('di_pan', '')
            score = 0
            men_jx = self.MEN_JIXIONG.get(men, '')
            if men_jx == '吉': score += 2
            elif men_jx == '凶': score -= 2
            star_jx = self.STAR_JIXIONG.get(xing, '')
            if star_jx == '吉': score += 1
            elif star_jx == '凶': score -= 1
            SHEN_JX = {'值符': 2, '九天': 2, '太阴': 1, '六合': 1,
                       '九地': 0, '螣蛇': -1, '白虎': -2, '玄武': -1}
            score += SHEN_JX.get(shen, 0)
            if (tp, dp) in self.GAN_HE:
                score += 2
            # 旺衰加权
            men_wx = self.MEN_WUXING.get(men, '')
            star_wx = self.STAR_WUXING.get(xing, '')
            gong_wx = self.GONG_WUXING.get(g, '')
            men_wang = self._calc_wang_shuai(men_wx, gong_wx)
            star_wang = self._calc_wang_shuai(star_wx, gong_wx)
            WANG_BONUS = {'旺': 2, '相': 1, '休': 0, '囚': -1, '死': -2}
            score += WANG_BONUS.get(men_wang, 0)
            score += WANG_BONUS.get(star_wang, 0)
            if score >= 6: level = '大吉'
            elif score >= 3: level = '吉'
            elif score >= 0: level = '中'
            elif score >= -3: level = '凶'
            else: level = '大凶'
            scores.append({
                'gong': g, 'score': score, 'level': level,
                'men': men, 'xing': xing, 'shen': shen,
                'men_wang': men_wang, 'star_wang': star_wang,
            })
        return scores

    # Q19: 天地人三盘综合判断
    def _analyze_san_pan_composite(self, palaces: list) -> dict:
        """Q19: 天地人三盘综合判断 - 统计全局吉凶"""
        ji_count = 0
        xiong_count = 0
        best_gong = 0
        worst_gong = 0
        best_score = -99
        worst_score = 99
        for p in palaces:
            g = p['gong']
            if g == 5:
                continue
            men_jx = self.MEN_JIXIONG.get(p.get('men', ''), '')
            star_jx = self.STAR_JIXIONG.get(p.get('xing', ''), '')
            s = 0
            if men_jx == '吉': s += 1; ji_count += 1
            elif men_jx == '凶': s -= 1; xiong_count += 1
            if star_jx == '吉': s += 1; ji_count += 1
            elif star_jx == '凶': s -= 1; xiong_count += 1
            if s > best_score:
                best_score = s
                best_gong = g
            if s < worst_score:
                worst_score = s
                worst_gong = g
        return {
            'ji_count': ji_count, 'xiong_count': xiong_count,
            'best_gong': best_gong, 'worst_gong': worst_gong,
            'desc': f'全局吉{ji_count}凶{xiong_count}，最佳宫{best_gong}，最差宫{worst_gong}',
        }

    # Q23: 天显时格判断
    def _analyze_tianxian_shi(self, day_gan_zhi: str, hour_gan_zhi: str) -> dict:
        """Q23: 天显时格判断 - 甲/己日遇特定时辰"""
        if not day_gan_zhi or not hour_gan_zhi:
            return {}
        day_gan = day_gan_zhi[0]
        hour_gan = hour_gan_zhi[0]
        # 天显时格：甲/己日遇甲子时/甲戌时等
        tianxian_combos = {
            ('甲', '甲'): '甲甲天显，大吉大利',
            ('己', '甲'): '己甲天显，贵人相助',
            ('甲', '己'): '甲己天显，天地合德',
            ('己', '己'): '己己天显，比和自得',
        }
        combo = (day_gan, hour_gan)
        if combo in tianxian_combos:
            return {
                'is_tianxian': True,
                'day_gan': day_gan, 'hour_gan': hour_gan,
                'desc': tianxian_combos[combo],
            }
        return {'is_tianxian': False}

    # ---- Q26-Q30: 奇门深度分析 ----

    # Q26: 天干入墓详解
    GAN_MU_DETAIL = {
        '戊': {'墓宫': '辰(巽四)', '含义': '资本入库，财源受阻', '化解': '见丙奇冲开'},
        '己': {'墓宫': '戌(乾六)', '含义': '田宅入墓，暗昧不明', '化解': '见乙奇解围'},
        '庚': {'墓宫': '丑(艮八)', '含义': '敌人入墓，暂可安枕', '化解': '不宜冲开'},
        '辛': {'墓宫': '戌(乾六)', '含义': '错误入墓，暂时隐藏', '化解': '见丁奇化解'},
        '壬': {'墓宫': '辰(巽四)', '含义': '天牢入墓，困顿不安', '化解': '见丙奇破局'},
        '癸': {'墓宫': '戌(乾六)', '含义': '天网入墓，暗中有险', '化解': '见乙奇遮掩'},
        '乙': {'墓宫': '未(坤二)', '含义': '日奇入墓，光明被掩', '化解': '见丙丁冲开'},
        '丙': {'墓宫': '戌(乾六)', '含义': '月奇入墓，权威受损', '化解': '见乙奇相助'},
        '丁': {'墓宫': '丑(艮八)', '含义': '星奇入墓，文书受阻', '化解': '见丙奇照亮'},
    }

    # Q27: 八门落宫详解
    MEN_LUOGONG_DETAIL = {
        '休门': {1: '休门本宫，安逸得所', 2: '休门入坤，休息得地',
                 3: '休门入震，水生木吉', 4: '休门入巽，水生木吉',
                 6: '休门入乾，金生水利', 7: '休门入兑，金生水利',
                 8: '休门入艮，水土相克', 9: '休门入离，水火相冲'},
        '生门': {1: '生门入坎，土克水凶', 2: '生门本宫，田宅有利',
                 3: '生门入震，木克土凶', 4: '生门入巽，木克土凶',
                 6: '生门入乾，土生金泄', 7: '生门入兑，土生金泄',
                 8: '生门本宫，厚德载物', 9: '生门入离，火生土吉'},
        '开门': {1: '开门入坎，金生水利', 2: '开门入坤，土生金吉',
                 3: '开门入震，金克木凶', 4: '开门入巽，金克木凶',
                 6: '开门本宫，事业大吉', 7: '开门本宫，正位得所',
                 8: '开门入艮，土生金吉', 9: '开门入离，火克金凶'},
        '死门': {1: '死门入坎，土克水凶', 2: '死门本宫，疾病大凶',
                 3: '死门入震，木克土凶', 4: '死门入巽，螣蛇夭矫',
                 6: '死门入乾，土生金泄', 7: '死门入兑，土生金泄',
                 8: '死门本宫，坟墓之象', 9: '死门入离，火生土凶'},
    }

    # Q28: 九星落宫详解
    STAR_LUOGONG_DETAIL = {
        '天蓬': {1: '天蓬本宫，盗贼旺相', 6: '天蓬入乾，水受金生',
                 9: '天蓬入离，水火相冲'},
        '天芮': {2: '天芮本宫，疾病大凶', 8: '天芮入艮，病符加重',
                 1: '天芮入坎，土克水病'},
        '天冲': {3: '天冲本宫，武勇冲撞', 4: '天冲入巽，木气旺盛',
                 2: '天冲入坤，木克土凶'},
        '天辅': {4: '天辅本宫，文采辅佐', 3: '天辅入震，文运亨通',
                 2: '天辅入坤，木克土不利'},
        '天心': {6: '天心本宫，医卜决策', 7: '天心入兑，金气得助',
                 3: '天心入震，金克木凶'},
        '天英': {9: '天英本宫，光明文化', 2: '天英入坤，火生土泄',
                 1: '天英入坎，水火相克'},
    }

    # Q29: 奇门用神分类（不同事类取不同用神）
    YONGSHEN_CLASSIFY = {
        '求财': {'主用神': '生门', '辅助': '甲子戊', '参考': '天盘时干'},
        '求官': {'主用神': '开门', '辅助': '值符', '参考': '年干'},
        '疾病': {'主用神': '天芮星', '辅助': '天心星', '参考': '乙奇'},
        '婚姻': {'主用神': '六合', '辅助': '乙奇/庚', '参考': '休门'},
        '出行': {'主用神': '时干', '辅助': '景门', '参考': '马星'},
        '诉讼': {'主用神': '惊门', '辅助': '开门', '参考': '辛/壬'},
        '考试': {'主用神': '景门', '辅助': '天辅星', '参考': '丁奇'},
        '失物': {'主用神': '时干', '辅助': '玄武', '参考': '日干'},
        '行人': {'主用神': '时干', '辅助': '年命', '参考': '马星'},
    }

    # Q30: 格局叠加分析
    def _analyze_ge_ju_overlay(self, ge_ju_analysis: dict) -> dict:
        """Q30: 格局叠加分析 - 多个格局同时出现时的综合判断"""
        if not ge_ju_analysis:
            return {}
        ji_ge = ge_ju_analysis.get('ji_ge', [])
        xiong_ge = ge_ju_analysis.get('xiong_ge', [])

        # 吉格叠加
        ji_names = [g['name'] for g in ji_ge]
        xiong_names = [g['name'] for g in xiong_ge]

        overlay = []
        # 三遁同现
        san_dun = [n for n in ji_names if n in ('天遁', '地遁', '人遁')]
        if len(san_dun) >= 2:
            overlay.append({'name': '三遁并现', 'desc': f'{"+".join(san_dun)}同现，大吉大利'})

        # 飞鸟跌穴+青龙返首
        if '飞鸟跌穴' in ji_names and '青龙返首' in ji_names:
            overlay.append({'name': '龙鸟呈祥', 'desc': '飞鸟跌穴+青龙返首，至吉之象'})

        # 凶格叠加
        if '太白入荧' in xiong_names and '五不遇时' in xiong_names:
            overlay.append({'name': '双重凶格', 'desc': '太白入荧+五不遇时，大凶，诸事不宜'})

        if '击刑' in xiong_names and '入墓' in xiong_names:
            overlay.append({'name': '刑墓并见', 'desc': '击刑+入墓同现，事有大阻'})

        return {
            'overlays': overlay,
            'count': len(overlay),
            'desc': f'格局叠加{len(overlay)}组' if overlay else '无特殊叠加',
        }

    # Q31: 天干长生十二宫详细落宫
    def _analyze_changsheng_detail(self, palaces: list, day_gan_zhi: str) -> dict:
        """Q31: 日干长生十二宫详细落宫分析"""
        if not day_gan_zhi or len(day_gan_zhi) < 1:
            return {}
        day_gan = day_gan_zhi[0]
        if day_gan not in self.CHANGSHENG_GONG:
            return {}
        cs_map = self.CHANGSHENG_GONG[day_gan]
        result = {}
        for stage, gong in cs_map.items():
            palace = None
            for p in palaces:
                if p['gong'] == gong:
                    palace = p
                    break
            detail = self.CHANGSHENG_DETAIL.get(stage, {})
            result[stage] = {
                'gong': gong,
                'palace_name': palace.get('name', '') if palace else '',
                'men': palace.get('men', '') if palace else '',
                'xing': palace.get('xing', '') if palace else '',
                '含义': detail.get('含义', ''),
                '吉凶': detail.get('吉凶', ''),
            }
        return {'day_gan': day_gan, 'stages': result}

    # Q32: 门星神综合断语
    def _generate_palace_summary(self, p: dict) -> str:
        """Q32: 单宫综合断语生成"""
        men = p.get('men', '')
        xing = p.get('xing', '')
        shen = p.get('shen', '')
        tp = p.get('tian_pan', '')
        dp = p.get('di_pan', '')
        parts = []
        men_jx = self.MEN_JIXIONG.get(men, '')
        star_jx = self.STAR_JIXIONG.get(xing, '')
        if men_jx == '吉' and star_jx == '吉':
            parts.append('门星皆吉')
        elif men_jx == '凶' and star_jx == '凶':
            parts.append('门星皆凶')
        if tp == dp:
            parts.append('天地同干(伏吟)')
        if (tp, dp) in self.GAN_HE:
            parts.append('天地合德')
        if men:
            men_wx = self.MEN_WUXING.get(men, '')
            gong_wx = self.GONG_WUXING.get(p.get('gong', 0), '')
            ws = self._calc_wang_shuai(men_wx, gong_wx)
            if ws:
                parts.append(f'门{ws}')
        return '，'.join(parts) if parts else '平'

    # Q33: 八门迫墓详细分析
    def _analyze_men_po_mu(self, palaces: list) -> list:
        """Q33: 八门迫墓详细分析 - 区分门迫和门墓"""
        result = []
        for p in palaces:
            g = p['gong']
            men = p.get('men', '')
            if not men or g == 5:
                continue
            men_wx = self.MEN_WUXING.get(men, '')
            gong_wx = self.GONG_WUXING.get(g, '')
            if not men_wx or not gong_wx:
                continue
            if self.WUXING_KE.get(men_wx) == gong_wx:
                detail = self.MEN_PO_DETAIL.get(men, {})
                result.append({
                    'gong': g, 'men': men, 'type': '门迫',
                    'men_wuxing': men_wx, 'gong_wuxing': gong_wx,
                    'detail': detail.get('desc', ''),
                    'desc': f'{men}({men_wx})迫{self.PALACE_NAMES.get(g, "")}({gong_wx})',
                })
        return result

    # Q34: 天地盘十干克应完整速查
    def _get_gan_ke_full(self, tp: str, dp: str) -> dict:
        """Q34: 天盘地盘十干克应完整速查"""
        key = f'{tp}加{dp}'
        level = self.GE_JU_LEVEL.get(key, '')
        detail = self.GAN_KE_DETAIL.get((tp, dp), {})
        return {
            'key': key, 'level': level,
            'name': detail.get('name', key),
            '类象': detail.get('类象', ''),
            '应期': detail.get('应期', ''),
        }

    # Q35: 奇门综合断语
    def _generate_qimen_summary(self, ge_ju_analysis: dict, yong_shen: dict,
                                 fu_fan_yin: dict, ge_ju_strength: dict) -> str:
        """Q35: 奇门综合断语生成"""
        parts = []
        # 格局力量
        if ge_ju_strength:
            parts.append(ge_ju_strength.get('summary', ''))
        # 伏吟反吟
        if fu_fan_yin and fu_fan_yin.get('type'):
            parts.append(fu_fan_yin.get('desc', ''))
        # 用神状态
        if yong_shen and 'hour_gong' in yong_shen:
            hg = yong_shen['hour_gong']
            parts.append(f'用神落{hg.get("name", "")}')
        return '；'.join(filter(None, parts))
