#!/usr/bin/env python3
"""
玄照 v2.0 - 紫微斗数引擎（iztro-py后端版）

基于 iztro-py 库实现标准紫微斗数排盘。
iztro-py 是经过验证的开源紫微斗数库，安星准确。

支持：命宫、身宫、五行局、十四主星、六吉六煞、杂耀、四化、十二宫、长生十二博士等。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional, Dict
from datetime import datetime
import calendar
import logging

logger = logging.getLogger(__name__)


# 地支英文→中文映射
BRANCH_MAP = {
    'ziEarthly': '子', 'chouEarthly': '丑', 'yinEarthly': '寅', 'maoEarthly': '卯',
    'chenEarthly': '辰', 'siEarthly': '巳', 'wuEarthly': '午', 'weiEarthly': '未',
    'shenEarthly': '申', 'youEarthly': '酉', 'xuEarthly': '戌', 'haiEarthly': '亥',
}

# 天干英文→中文映射
STEM_MAP = {
    'jiaHeavenly': '甲', 'yiHeavenly': '乙', 'bingHeavenly': '丙', 'dingHeavenly': '丁',
    'wuHeavenly': '戊', 'jiHeavenly': '己', 'gengHeavenly': '庚', 'xinHeavenly': '辛',
    'renHeavenly': '壬', 'guiHeavenly': '癸',
}

# 宫位英文→中文映射
PALACE_NAME_MAP = {
    'soulPalace': '命宫', 'spiritPalace': '身宫',
    'siblingsPalace': '兄弟', 'spousePalace': '夫妻',
    'childrenPalace': '子女', 'wealthPalace': '财帛',
    'healthPalace': '疾厄', 'surfacePalace': '迁移',
    'friendsPalace': '交友', 'careerPalace': '官禄',
    'propertyPalace': '田宅', 'fortunePalace': '福德',
    'parentsPalace': '父母',
}

# 星曜英文→中文映射（主星）
MAJOR_STAR_MAP = {
    'ziweiMaj': '紫微', 'tianjiMaj': '天机', 'taiyangMaj': '太阳',
    'wuquMaj': '武曲', 'tiantongMaj': '天同', 'lianzhenMaj': '廉贞',
    'tianfuMaj': '天府', 'taiyinMaj': '太阴', 'tanlangMaj': '贪狼',
    'jumenMaj': '巨门', 'tianxiangMaj': '天相', 'tianliangMaj': '天梁',
    'qishaMaj': '七杀', 'pojunMaj': '破军',
}

# 辅星英文→中文映射
MINOR_STAR_MAP = {
    'lucunMin': '禄存', 'qingyangMin': '擎羊', 'tuoluoMin': '陀罗',
    'tiankuiMin': '天魁', 'tianyueMin': '天钺',
    'zuofuMin': '左辅', 'youbiMin': '右弼',
    'wenchangMin': '文昌', 'wenquMin': '文曲',
    'huoxingMin': '火星', 'lingxingMin': '铃星',
    'dikongMin': '地空', 'dijieMin': '地劫',
    'tianmaMin': '天马',
}

# 杂耀英文→中文映射
ADJECTIVE_STAR_MAP = {
    'tianxi': '天喜', 'taifu': '台辅', 'jieshen': '解神',
    'tianxu': '天虚', 'tianku': '天哭', 'longchi': '龙池',
    'fengge': '凤阁', 'huagai': '华盖', 'tianyao': '天姚',
    'tiande': '天德', 'yuede': '月德', 'tiancai': '天才',
    'tianshou': '天寿', 'santai': '三台', 'bazuo': '八座',
    'enguang': '恩光', 'tiangui': '天贵', 'tianwu': '天巫',
    'tianshi': '天史', 'posui': '破碎', 'guchen': '孤辰',
    'guasu': '寡宿', 'feilian': '蜚廉', 'tianxing': '天刑',
    'tianshang': '天伤', 'hongluan': '红鸾', 'xianchi': '咸池',
    'tianchu': '天厨', 'jielu': '截路', 'kongwang': '空亡',
    'xunkong': '旬空', 'fenggao': '封诰', 'nianjie': '年解',
    'yinsha': '阴煞',    'tianfuAdj': '天福', 'tiankong': '天空',
    'tianguan': '天官', 'tianyue': '天月',
}

# 亮度映射
BRIGHTNESS_MAP = {
    '庙': '庙', '旺': '旺', '得': '得', '利': '利', '平': '平',
    '不': '不', '陷': '陷',
}

# 天干四化表（完整版，用于计算自化）
# {天干: {禄星, 权星, 科星, 忌星}}
TIAN_GAN_SIHUA = {
    '甲': {'禄': '廉贞', '权': '破军', '科': '武曲', '忌': '太阳'},
    '乙': {'禄': '天机', '权': '天梁', '科': '紫微', '忌': '太阴'},
    '丙': {'禄': '天同', '权': '天机', '科': '文昌', '忌': '廉贞'},
    '丁': {'禄': '太阴', '权': '天同', '科': '天机', '忌': '巨门'},
    '戊': {'禄': '贪狼', '权': '太阴', '科': '右弼', '忌': '天机'},
    '己': {'禄': '武曲', '权': '贪狼', '科': '天梁', '忌': '文曲'},
    '庚': {'禄': '太阳', '权': '武曲', '科': '太阴', '忌': '天同'},
    '辛': {'禄': '巨门', '权': '太阳', '科': '文曲', '忌': '文昌'},
    '壬': {'禄': '天梁', '权': '紫微', '科': '左辅', '忌': '武曲'},
    '癸': {'禄': '破军', '权': '巨门', '科': '太阴', '忌': '贪狼'},
}

# 天干英文→中文映射（复用 STEM_MAP，消除重复定义）
STEM_EN_TO_CN = STEM_MAP

# 天干拼音→中文映射（iztro horoscope返回格式）
PINYIN_STEM_MAP = {
    'jia': '甲', 'yi': '乙', 'bing': '丙', 'ding': '丁',
    'wu': '戊', 'ji': '己', 'geng': '庚', 'xin': '辛',
    'ren': '壬', 'gui': '癸',
}

# 地支拼音→中文映射（iztro horoscope返回格式）
PINYIN_BRANCH_MAP = {
    'zi': '子', 'chou': '丑', 'yin': '寅', 'mao': '卯',
    'chen': '辰', 'si': '巳', 'wu': '午', 'wei': '未',
    'shen': '申', 'you': '酉', 'xu': '戌', 'hai': '亥',
}

# 中文数字→阿拉伯数字映射（五行局解析用，模块级常量）
CN_DIGITS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}

# 五行→局数标准映射（水二局、木三局、金四局、土五局、火六局）
WUXING_TO_JU = {'水':2, '木':3, '金':4, '土':5, '火':6}

# 五行局→起运虚岁（简化映射，实际起运年龄由iztro精确计算）
# 注：简化模型下起运年龄=局数（水二局→2岁、木三局→3岁、…火六局→6岁）


def _cn_branch(en: str) -> str:
    """英文地支→中文"""
    return BRANCH_MAP.get(en, en)


def _cn_stem(en: str) -> str:
    """英文天干→中文"""
    return STEM_MAP.get(en, en)


def _cn_palace_name(en: str) -> str:
    """英文宫名→中文"""
    return PALACE_NAME_MAP.get(en, en)


def _cn_star(en: str, star_type: str = 'major') -> str:
    """英文星名→中文"""
    if star_type == 'major':
        return MAJOR_STAR_MAP.get(en, en)
    elif star_type == 'minor':
        return MINOR_STAR_MAP.get(en, en)
    elif star_type == 'adjective':
        return ADJECTIVE_STAR_MAP.get(en, en)
    return en


class ZiWeiEngine(DivinationEngine):
    """紫微斗数引擎（iztro-py后端）"""

    @property
    def name(self) -> str:
        return "紫微"

    @property
    def name_en(self) -> str:
        return "ziwei"

    @property
    def priority(self) -> int:
        return 2

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        # 使用真太阳时排盘（时辰应基于出生地的真太阳时）
        orig = time.true_solar
        hour = orig.hour

        # 计算时辰索引（iztro格式：0=早子,1=丑,...,11=亥,12=晚子）
        # ⚠️ hour=23 是晚子时，必须返回12而非0
        if hour == 23:
            time_index = 12  # 晚子时
        else:
            time_index = (hour + 1) // 2 % 12

        gender_str = '男' if gender == 1 else '女'

        try:
            from iztro_py.astro import astro
            result = astro.by_solar(
                f'{orig.year}-{orig.month:02d}-{orig.day:02d}',
                time_index,
                gender_str
            )
        except Exception as e:
            return {"error": f"iztro排盘失败: {str(e)}"}

        # 转换为玄照格式
        return self._convert_result(result, gender_str, orig, time_index)

    def _convert_result(self, iztro_result, gender_str: str, birth_dt=None, time_index: int = 6) -> dict:
        """将iztro结果转换为玄照API格式（文墨天机专业版级别）"""
        r = iztro_result

        # 基础信息
        ming_gong_branch = _cn_branch(r.earthly_branch_of_soul_palace)
        shen_gong_branch = _cn_branch(r.earthly_branch_of_body_palace)

        # 五行局
        wuxing_ju_str = r.five_elements_class  # 如 "木三局"
        # 五行→局数标准映射（水二局、木三局、金四局、土五局、火六局）
        # NOTE: CN_DIGITS, WUXING_TO_JU, JU_START_AGE 已提升为模块级常量
        wuxing = wuxing_ju_str[0] if wuxing_ju_str else "木"
        if wuxing_ju_str and len(wuxing_ju_str) > 1:
            ju_shu = CN_DIGITS.get(wuxing_ju_str[1], WUXING_TO_JU.get(wuxing, 3))
        else:
            # 解析失败时用五行→局数映射保证一致性，回退到木三局
            ju_shu = WUXING_TO_JU.get(wuxing, 3)
            wuxing = wuxing if wuxing in WUXING_TO_JU else "木"

        # 起运年龄（简化模型：起运虚岁=局数）
        start_age = ju_shu

        # 四柱
        ganzhi = r.chinese_date.split()  # "乙酉 壬午 甲子 庚午"

        # 排十二宫
        palaces = []
        star_placements = {}

        for p in r.palaces:
            palace_name = _cn_palace_name(p.name)
            branch = _cn_branch(p.earthly_branch)
            stem = _cn_stem(p.heavenly_stem)

            # 主星
            major_stars = []
            for s in p.major_stars:
                star_cn = _cn_star(s.name, 'major')
                brightness = BRIGHTNESS_MAP.get(s.brightness, s.brightness) if s.brightness else ''
                mutagen = s.mutagen or ''
                major_stars.append({
                    'name': star_cn,
                    'brightness': brightness,
                    'mutagen': mutagen,
                })
                star_placements[star_cn] = palace_name

            # 辅星（完整列表，含亮度）
            minor_stars = []
            for s in p.minor_stars:
                star_cn = _cn_star(s.name, 'minor')
                minor_stars.append({
                    'name': star_cn,
                    'brightness': BRIGHTNESS_MAP.get(s.brightness, s.brightness) if s.brightness else '',
                    'mutagen': s.mutagen or '',
                })
                star_placements[star_cn] = palace_name

            # 杂耀
            adj_stars = []
            for s in p.adjective_stars:
                star_cn = _cn_star(s.name, 'adjective')
                adj_stars.append({'name': star_cn})
                star_placements[star_cn] = palace_name

            # 大限信息（每个宫位自身的大限数据）
            dai_xian_palace = {}
            if p.decadal:
                dx_range = p.decadal.range  # (start_age, end_age)
                dx_stem_cn = _cn_stem(p.decadal.heavenly_stem)
                dx_branch_cn = _cn_branch(p.decadal.earthly_branch)
                dai_xian_palace = {
                    'start_age': dx_range[0] if dx_range else 0,
                    'end_age': dx_range[1] if dx_range else 0,
                    'ganzhi': f'{dx_stem_cn}{dx_branch_cn}',
                    'stem': dx_stem_cn,
                    'branch': dx_branch_cn,
                }

            # 该宫位所有大限年龄列表（虚岁，每个年龄对应一次大限进入此宫）
            ages = p.ages if hasattr(p, 'ages') and p.ages else []

            # 自化计算：该宫天干引发的四化，是否影响到同宫的星
            self_hua = []
            if stem and stem in TIAN_GAN_SIHUA:
                palace_sihua = TIAN_GAN_SIHUA[stem]
                palace_star_names = set()
                for s in p.major_stars:
                    palace_star_names.add(_cn_star(s.name, 'major'))
                for s in p.minor_stars:
                    palace_star_names.add(_cn_star(s.name, 'minor'))
                for hua_type, star_name in palace_sihua.items():
                    if star_name in palace_star_names:
                        self_hua.append({'hua': hua_type, 'star': star_name})

            palaces.append({
                'name': palace_name,
                'zhi': branch,
                'stem': stem,
                'is_body_palace': p.is_body_palace,
                'is_original_palace': p.is_original_palace if hasattr(p, 'is_original_palace') else False,
                'major_stars': major_stars,
                'minor_stars': minor_stars,
                'adjective_stars': adj_stars,
                # 长生十二神
                'changsheng': p.changsheng12 if hasattr(p, 'changsheng12') else '',
                # 博士十二神
                'boshi': p.boshi12 if hasattr(p, 'boshi12') else '',
                # 将前十二神
                'jiangqian': p.jiangqian12 if hasattr(p, 'jiangqian12') else '',
                # 岁前十二神
                'suiqian': p.suiqian12 if hasattr(p, 'suiqian12') else '',
                # 大限标注（该宫对应的大限干支+年龄范围）
                'dai_xian': dai_xian_palace,
                # 大限年龄列表（该宫被哪些虚岁大限所入）
                'dai_xian_ages': ages,
                # 自化
                'self_hua': self_hua,
            })

        # 年干四化（生年四化）
        # 注意：四化不仅限于主星——丙年文昌化科、戊年右弼化科、己年文曲化忌、
        # 辛年文曲化科/文昌化忌、壬年左辅化科 均为辅星（minor_stars）四化
        sihua = {}
        soul_star = _cn_star(r.soul, 'major') if r.soul else ''
        body_star = _cn_star(r.body, 'major') if r.body else ''

        for p in r.palaces:
            for s in p.major_stars:
                if s.mutagen:
                    mutagen_map = {'禄': '禄', '权': '权', '科': '科', '忌': '忌'}
                    if s.mutagen in mutagen_map:
                        sihua[mutagen_map[s.mutagen]] = _cn_star(s.name, 'major')
            for s in p.minor_stars:
                if s.mutagen:
                    mutagen_map = {'禄': '禄', '权': '权', '科': '科', '忌': '忌'}
                    if s.mutagen in mutagen_map:
                        sihua[mutagen_map[s.mutagen]] = _cn_star(s.name, 'minor')

        # 自化汇总（哪些宫位有自化禄/权/科/忌）
        self_hua_map = {'禄': [], '权': [], '科': [], '忌': []}
        for pal in palaces:
            for sh in pal['self_hua']:
                self_hua_map[sh['hua']].append({
                    'palace': pal['name'],
                    'star': sh['star'],
                })

        # 大限完整序列（保留原有逻辑用于dai_xian顶层字段）
        dai_xian = []

        def _safe_date_str(year: int, month: int, day: int) -> str:
            """安全构造日期字符串，自动回退到合法日期"""
            # 月份防御
            month = max(1, min(12, month))
            _, last_day = calendar.monthrange(year, month)
            # 日期防御（clamp到1~月末）
            day = max(1, min(day, last_day))
            return f'{year}-{month:02d}-{day:02d}'

        # 计算当前年份（供大限和流年共用，避免重复调用 datetime.now()）
        current_year = datetime.now().year
        birth_year = birth_dt.year if birth_dt else current_year

        try:
            seen_palaces = set()
            for test_age in range(start_age, 100, 10):
                test_year = birth_year + test_age - 1  # 虚岁
                try:
                    if not birth_dt:
                        break
                    h = r.horoscope(_safe_date_str(test_year, birth_dt.month, birth_dt.day), time_index)
                    dx = h.decadal
                    stem_en = (dx.heavenly_stem or '').replace('Heavenly', '').strip()
                    branch_en = (dx.earthly_branch or '').replace('Earthly', '').strip()
                    # 防御：pinyin解析失败时跳过该大限，避免产生空干支条目
                    if not stem_en or not branch_en:
                        logger.debug(f"大限{test_age}岁: pinyin解析为空(stem='{dx.heavenly_stem}', branch='{dx.earthly_branch}')，跳过")
                        continue
                    s = PINYIN_STEM_MAP.get(stem_en, stem_en)
                    b = PINYIN_BRANCH_MAP.get(branch_en, branch_en)
                    # 防御：解析结果不是合法天干地支时跳过
                    if len(s) != 1 or len(b) != 1:
                        logger.debug(f"大限{test_age}岁: 干支解析异常(gz='{s}{b}')，跳过")
                        continue
                    gz = f'{s}{b}'
                    if gz not in seen_palaces:
                        seen_palaces.add(gz)
                        pal_name = ''
                        if dx.palace_names:
                            pal_name = PALACE_NAME_MAP.get(dx.palace_names[0], dx.palace_names[0])

                        # 大限四化
                        dx_sihua = {}
                        if dx.mutagen:
                            MUTAGEN_LABELS = ['禄', '权', '科', '忌']
                            for i, star_en in enumerate(dx.mutagen):
                                if i < 4:
                                    star_cn = _cn_star(star_en, 'major') if star_en in MAJOR_STAR_MAP else _cn_star(star_en, 'minor')
                                    dx_sihua[MUTAGEN_LABELS[i]] = star_cn

                        # 优先使用iztro库提供的精确年龄范围
                        dx_range = getattr(dx, 'range', None)
                        actual_start = dx_range[0] if dx_range and len(dx_range) >= 2 else test_age
                        actual_end = dx_range[1] if dx_range and len(dx_range) >= 2 else test_age + 9

                        dai_xian.append({
                            'start_age': actual_start,
                            'end_age': actual_end,
                            'ganzhi': gz,
                            'palace_name': pal_name,
                            'palace_index': dx.index,
                            'sihua': dx_sihua,
                        })
                except Exception as e:
                    logger.debug(f"大限{test_age}岁计算异常: {e}")
        except Exception as e:
            logger.warning(f"大限序列计算异常: {e}")
            dai_xian = []

        # 子斗（斗君）计算
        # 传统规则：寅宫起正月，逆数到出生月份，再从该宫起子时，顺数到出生时辰
        # 正月→寅(2), 二月→丑(1), 三月→子(0), 四月→亥(11), ...
        # 月宫索引 = (2 - (month - 1)) % 12 = (3 - month) % 12
        zi_dou = ''
        if birth_dt:
            BRANCH_ORDER = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
            # 逆数到出生月份所在宫位
            month_palace_idx = (3 - birth_dt.month) % 12
            # 从该宫起子时，顺数到出生时辰（晚子时time_index=12需取模12归零）
            dou_jun_idx = (month_palace_idx + time_index % 12) % 12
            zi_dou = BRANCH_ORDER[dou_jun_idx]

        # 流年分析（当年太岁四化、流年命宫等）
        liunian_info = {}
        if birth_dt:
            try:
                h = r.horoscope(_safe_date_str(current_year, birth_dt.month, birth_dt.day), time_index)
                liunian_palace_names = []
                if hasattr(h, 'palace_names') and h.palace_names:
                    liunian_palace_names = [PALACE_NAME_MAP.get(n, n) for n in h.palace_names]
                liunian_stars = []
                if hasattr(h, 'mutagen') and h.mutagen:
                    MUTAGEN_LABELS = ['禄', '权', '科', '忌']
                    for i, star_en in enumerate(h.mutagen):
                        if i < 4:
                            star_cn = _cn_star(star_en, 'major') if star_en in MAJOR_STAR_MAP else _cn_star(star_en, 'minor')
                            liunian_stars.append({'hua': MUTAGEN_LABELS[i], 'star': star_cn})
                liunian_info = {
                    'year': current_year,
                    'palace_names': liunian_palace_names,
                    'sihua': liunian_stars,
                }
            except Exception as e:
                logger.debug(f"流年分析异常: {e}")

        return {
            'engine': self.name,
            'engine_en': self.name_en,
            'ming_gong': ming_gong_branch,
            'shen_gong': shen_gong_branch,
            'soul_star': soul_star,
            'body_star': body_star,
            'wuxing_ju': {'wuxing': wuxing, 'ju_shu': ju_shu},
            'start_age': start_age,
            'palaces': palaces,
            'star_placements': star_placements,
            'sihua': sihua,
            'self_hua_map': self_hua_map,
            'gender': gender_str,
            'lunar_date': r.lunar_date if hasattr(r, 'lunar_date') else '',
            'chinese_date': r.chinese_date if hasattr(r, 'chinese_date') else '',
            'zodiac': r.zodiac if hasattr(r, 'zodiac') else '',
            'dai_xian': dai_xian,
            'nominal_age': current_year - birth_dt.year + 1 if birth_dt else 0,
            'zi_dou': zi_dou,
            'liunian': liunian_info,
        }

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if data.get('error'):
            return False, data['error']
        if not data.get('ming_gong'):
            return False, "命宫为空"
        if not data.get('palaces'):
            return False, "宫位数据为空"
        return True, None
