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
            'ge_ju_analysis': self._analyze_ge_ju(palaces, ba_men, jiu_xing, ba_shen, xun_kong, day_gan_zhi, hour_gan_zhi, zhi_shi_door),
            # 流年分析
            'liunian': self._build_liunian(solar_dt, di_pan, tian_pan, palaces),
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

