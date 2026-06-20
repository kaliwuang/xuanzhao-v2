"""
Qi Men Dun Jia (奇门遁甲) Engine for XuanZhao v2.0
"""
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from .base import DivinationEngine
from .time_engine import CorrectedTime


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
    EIGHT_GODS = ['值符', '腾蛇', '太阴', '六合', '白虎', '玄武', '九地', '九天']

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
        solar_dt = time.true_solar or time.original

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
        zhi_fu_gong = self._find_gong_for_gan(di_pan, hour_gan_zhi)
        zhi_fu_star = jiu_xing.get(zhi_fu_gong, '天蓬')
        zhi_shi_door = ba_men.get(zhi_fu_gong, '休门')

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
            'gender': gender,
            'xun_kong': xun_kong,
            # 天地人三盘摘要（便于前端快速展示）
            'san_pan_summary': self._build_san_pan_summary(palaces),
            'ge_ju_analysis': self._analyze_ge_ju(palaces, ba_men, jiu_xing, ba_shen, xun_kong),
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
        except Exception:
            pass

        # 回退：按月日近似节气分界
        m, d = solar_dt.month, solar_dt.day

        # 按月日近似节气分界
        jieqi_table = [
            (1, 6, '小寒'), (1, 20, '大寒'),
            (2, 4, '立春'), (2, 19, '雨水'),
            (3, 6, '惊蛰'), (3, 21, '春分'),
            (4, 5, '清明'), (4, 20, '谷雨'),
            (5, 6, '立夏'), (5, 21, '小满'),
            (6, 6, '芒种'), (6, 21, '夏至'),
            (7, 7, '小暑'), (7, 23, '大暑'),
            (8, 7, '立秋'), (8, 23, '处暑'),
            (9, 8, '白露'), (9, 23, '秋分'),
            (10, 8, '寒露'), (10, 23, '霜降'),
            (11, 7, '立冬'), (11, 22, '小雪'),
            (12, 7, '大雪'), (12, 22, '冬至'),
        ]

        current_jieqi = '冬至'
        for jm, jd, name in jieqi_table:
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
        except Exception:
            hour = solar_dt.hour
            zhi_idx = ((hour + 1) % 24) // 2
            # 晚子时(23:xx)日柱用次日，但时支仍为子时
            from datetime import timedelta
            calc_dt = solar_dt + timedelta(days=1) if hour == 23 else solar_dt
            day_gan_idx = (calc_dt.toordinal() + 9) % 10
            gan_idx = (day_gan_idx * 2 + zhi_idx) % 10
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
        except Exception:
            # 晚子时(23:xx)日柱用次日
            from datetime import timedelta
            calc_dt = solar_dt + timedelta(days=1) if solar_dt.hour == 23 else solar_dt
            ga = (calc_dt.toordinal() + 9) % 10
            zi = (calc_dt.toordinal() + 1) % 12
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

    def _build_tian_pan(self, di_pan: dict, hour_gan_zhi: str, ju: int, yin_yang: str):
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
            # 中宫5不在洛书飞宫序列中，寄坤二宫处理
            if gong_int == 5:
                gong_int = 2
            # ju=5 也需寄坤二宫
            ju_lookup = 2 if ju == 5 else ju
            if gong_int in luo8:
                # 找到值符（ju对应的星）在洛书中的位置
                zhi_fu_idx = luo8.index(ju_lookup) if ju_lookup in luo8 else 0
                # 时干宫在洛书中的位置
                target_idx = luo8.index(gong_int)
                # 计算旋转偏移
                offset = target_idx - zhi_fu_idx

                # 天盘 = 地盘元素按offset旋转
                n = len(luo8)
                tian_pan = {}
                for i, palace in enumerate(luo8):
                    src_idx = (i - offset) % n
                    src_palace = luo8[src_idx]
                    tian_pan[palace] = di_pan.get(src_palace, '')
                # 中宫寄坤二宫（天盘跟随坤二宫，非保持地盘原值）
                tian_pan[5] = tian_pan.get(2, di_pan.get(5, ''))

                # 九星也按同样偏移旋转
                new_jiu_xing = {}
                for i, palace in enumerate(luo8):
                    src_idx = (i - offset) % n
                    new_jiu_xing[palace] = jiu_xing[luo8[src_idx]]
                new_jiu_xing[5] = jiu_xing.get(5, '天禽')
                jiu_xing = new_jiu_xing

                # 八门也按同样偏移旋转
                new_ba_men = {}
                for i, palace in enumerate(luo8):
                    src_idx = (i - offset) % n
                    new_ba_men[palace] = ba_men[luo8[src_idx]]
                new_ba_men[5] = ''
                ba_men = new_ba_men
            else:
                tian_pan = dict(di_pan)
        else:
            tian_pan = dict(di_pan)

        return tian_pan, ba_men, jiu_xing

    def _build_ba_shen(self, yin_yang: str, zhi_fu_gong: int) -> dict:
        """分配八神（阳遁顺排，阴遁逆排）"""
        luo8 = self.LUO_SHU_8
        # 中宫5寄坤二宫（传统规则）
        effective_gong = 2 if zhi_fu_gong == 5 else zhi_fu_gong
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
        ba_shen[5] = ''  # 中宫5不排八神，显式设置空值确保key一致
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
        # 旬首对应的奇仪（甲子→戊, 甲戌→己, 甲申→庚, 甲午→辛, 甲辰→壬, 甲寅→癸）
        XUN_HIDDEN_YI = {'子': '戊', '戌': '己', '申': '庚', '午': '辛', '辰': '壬', '寅': '癸'}
        if len(day_gan_zhi) < 2:
            return {'xun_shou': '', 'kong_wang': [], 'hidden_yi': ''}
        gan_idx = TIANGAN.index(day_gan_zhi[0]) if day_gan_zhi[0] in TIANGAN else 0
        zhi_idx = DIZHI.index(day_gan_zhi[1]) if day_gan_zhi[1] in DIZHI else 0
        xun_start_zhi = (zhi_idx - gan_idx) % 12
        xun_shou_zhi = DIZHI[xun_start_zhi]
        xun_shou = TIANGAN[0] + xun_shou_zhi
        kong1 = DIZHI[(xun_start_zhi + 10) % 12]
        kong2 = DIZHI[(xun_start_zhi + 11) % 12]
        hidden_yi = XUN_HIDDEN_YI.get(xun_shou_zhi, '戊')
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

    def _analyze_ge_ju(self, palaces: list, ba_men: dict, jiu_xing: dict, ba_shen: dict, xun_kong: dict) -> dict:
        """奇门格局判断：识别吉格和凶格"""
        ji_ge = []   # 吉格
        xiong_ge = []  # 凶格

        # ---- 吉格检测 ----

        # 1. 天遁：生门+天辅星同宫
        for p in palaces:
            g = p['gong']
            if p['men'] == '生门' and p['xing'] == '天辅':
                ji_ge.append({'name': '天遁', 'gong': g, 'desc': '生门配天辅，谋事大吉'})

        # 2. 地遁：开门+天心星同宫
        for p in palaces:
            g = p['gong']
            if p['men'] == '开门' and p['xing'] == '天心':
                ji_ge.append({'name': '地遁', 'gong': g, 'desc': '开门配天心，百事可为'})

        # 3. 人遁：休门+天任星同宫
        for p in palaces:
            g = p['gong']
            if p['men'] == '休门' and p['xing'] == '天任':
                ji_ge.append({'name': '人遁', 'gong': g, 'desc': '休门配天任，贵人相助'})

        # 4. 龙遁：开门/休门+九天同宫
        for p in palaces:
            g = p['gong']
            if p['men'] in ('开门', '休门') and p['shen'] == '九天':
                ji_ge.append({'name': '龙遁', 'gong': g, 'desc': f"{p['men']}配九天，飞龙在天"})

        # 5. 虎遁：开门/生门+白虎同宫
        for p in palaces:
            g = p['gong']
            if p['men'] in ('开门', '生门') and p['shen'] == '白虎':
                ji_ge.append({'name': '虎遁', 'gong': g, 'desc': f"{p['men']}配白虎，威猛有力"})

        # ---- 凶格检测 ----

        # 1. 朱雀投江：景门落坎宫(1)
        for p in palaces:
            if p['men'] == '景门' and p['gong'] == 1:
                xiong_ge.append({'name': '朱雀投江', 'gong': 1, 'desc': '景门入坎，文书有失'})

        # 2. 螣蛇夭矫：死门落巽宫(4)
        for p in palaces:
            if p['men'] == '死门' and p['gong'] == 4:
                xiong_ge.append({'name': '螣蛇夭矫', 'gong': 4, 'desc': '死门入巽，虚惊怪异'})

        # 3. 太白入荧：庚+丙（天盘庚，地盘丙）
        for p in palaces:
            if p.get('tian_pan') == '庚' and p.get('di_pan') == '丙':
                xiong_ge.append({'name': '太白入荧', 'gong': p['gong'], 'desc': '庚加丙，贼来为患'})

        # 4. 荧入太白：丙+庚
        for p in palaces:
            if p.get('tian_pan') == '丙' and p.get('di_pan') == '庚':
                xiong_ge.append({'name': '荧入太白', 'gong': p['gong'], 'desc': '丙加庚，贼去平安'})

        # 5. 击刑：天盘天干落地盘相刑之宫
        # 六仪击刑规则：甲子戊→震三(子刑卯)、甲戌己→坤二(戌刑未)、
        # 甲申庚→艮八(申刑寅)、甲午辛→离九(午自刑)、
        # 甲辰壬→巽四(辰自刑)、甲寅癸→巽四(寅刑巳)
        XING_MAP = {1: '子', 8: '丑', 3: '卯', 4: '辰', 9: '午', 2: '未', 7: '酉', 6: '戌'}
        GAN_XING = {'戊': 3, '己': 2, '庚': 8, '辛': 9, '壬': 4, '癸': 4}
        # 六仪击刑：每个天干所刑之地支（巽四宫有辰巳两支，壬用辰、癸用巳）
        GAN_XING_BRANCH = {'戊': '卯', '己': '未', '庚': '寅', '辛': '午', '壬': '辰', '癸': '巳'}
        for p in palaces:
            g = p['gong']
            tp = p.get('tian_pan', '')
            if tp in GAN_XING and GAN_XING[tp] == g:
                branch_name = GAN_XING_BRANCH.get(tp, XING_MAP.get(g, '中'))
                gong_name = self.PALACE_NAMES.get(g, f'{branch_name}宫')
                xiong_ge.append({'name': '击刑', 'gong': g, 'desc': f'{tp}落{gong_name}，刑伤之象'})

        # 6. 入墓：天干落墓宫（排除三奇乙丙丁，由下方三奇入墓专项检测）
        # 天干入墓表（五行墓库法）：乙木→未(坤二=2)，丙丁火→戌(乾六=6)，庚辛金→丑(艮八=8)，戊己壬癸→辰(巽四=4)
        # 注：甲遁于六仪，不直接出现在天盘，故不列入
        GAN_MU = {'乙': 2, '丙': 6, '丁': 6, '戊': 4, '己': 4, '庚': 8, '辛': 8, '壬': 4, '癸': 4}
        SAN_QI = {'乙', '丙', '丁'}  # 三奇，由专项检测处理
        for p in palaces:
            g = p['gong']
            tp = p.get('tian_pan', '')
            if tp in SAN_QI:
                continue  # 三奇入墓由下方专项检测，避免重复
            if tp in GAN_MU and GAN_MU[tp] == g:
                xiong_ge.append({'name': '入墓', 'gong': g, 'desc': f'{tp}入墓，事有阻碍'})

        # 7. 欢怡：天盘丙+地盘辛（丙辛合化水，谋事有成）
        for p in palaces:
            if p.get('tian_pan') == '丙' and p.get('di_pan') == '辛':
                ji_ge.append({'name': '欢怡', 'gong': p['gong'], 'desc': '丙辛合化水，谋事有成'})

        # 8. 奇合：天盘乙+地盘庚（乙庚合化金，合作有利）
        for p in palaces:
            if p.get('tian_pan') == '乙' and p.get('di_pan') == '庚':
                ji_ge.append({'name': '奇合', 'gong': p['gong'], 'desc': '乙庚合化金，合作有利'})

        # 9. 小格：庚+癸
        for p in palaces:
            if p.get('tian_pan') == '庚' and p.get('di_pan') == '癸':
                xiong_ge.append({'name': '小格', 'gong': p['gong'], 'desc': '庚加癸，格局不通'})

        # 10. 飞鸟跌穴：天盘丙+地盘戊（丙奇到位，大吉格局）
        for p in palaces:
            if p.get('tian_pan') == '丙' and p.get('di_pan') == '戊':
                ji_ge.append({'name': '飞鸟跌穴', 'gong': p['gong'], 'desc': '丙加戊，百事吉昌，如飞鸟归巢'})

        # 11. 青龙返首：天盘戊+地盘丙（戊丙相合，大吉格局）
        for p in palaces:
            if p.get('tian_pan') == '戊' and p.get('di_pan') == '丙':
                ji_ge.append({'name': '青龙返首', 'gong': p['gong'], 'desc': '戊加丙，贵人相助，逢凶化吉'})

        # 12. 白虎猖狂：天盘辛+地盘乙（辛金克乙木，大凶格局）
        for p in palaces:
            if p.get('tian_pan') == '辛' and p.get('di_pan') == '乙':
                xiong_ge.append({'name': '白虎猖狂', 'gong': p['gong'], 'desc': '辛加乙，金木相克，主伤灾破败'})

        # 13. 三奇入墓：乙(木)入未(坤二=2)、丙(火)入戌(乾六=6)、丁(火)入戌(乾六=6)
        # 三奇为乙丙丁，入墓则奇不显灵，百事不顺
        # 五行墓库：木墓在未(坤二=2)，火墓在戌(乾六=6)
        SAN_QI_MU = {'乙': 2, '丙': 6, '丁': 6}
        for p in palaces:
            g = p['gong']
            tp = p.get('tian_pan', '')
            if tp in SAN_QI_MU and SAN_QI_MU[tp] == g:
                xiong_ge.append({'name': '三奇入墓', 'gong': g, 'desc': f'{tp}奇入墓，奇不显灵，百事不顺'})

        # 14. 悖格：天盘天干五行克制地盘天干五行（排除已检测的特殊格局）
        # 天克地为"悖"，行事多阻，进退维谷
        WUXING = {'甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
                   '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'}
        KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}
        ALREADY_CHECKED = {('庚', '丙'), ('丙', '庚'), ('庚', '癸'), ('戊', '丙'),
                           ('丙', '戊'), ('辛', '乙'), ('丙', '辛'), ('乙', '庚'),
                           # 天干五合（合不为悖）：甲己、乙庚、丙辛、丁壬、戊癸
                           ('甲', '己'), ('己', '甲'), ('庚', '乙'),
                           ('丁', '壬'), ('壬', '丁'), ('辛', '丙'),
                           ('戊', '癸'), ('癸', '戊')}
        for p in palaces:
            tp = p.get('tian_pan', '')
            dp = p.get('di_pan', '')
            if tp and dp and (tp, dp) not in ALREADY_CHECKED:
                tp_wx = WUXING.get(tp, '')
                dp_wx = WUXING.get(dp, '')
                if tp_wx and dp_wx and KE.get(tp_wx) == dp_wx:
                    xiong_ge.append({'name': '悖格', 'gong': p['gong'],
                                     'desc': f'{tp}({tp_wx})克{dp}({dp_wx})，天克地，行事多阻'})

        # 15. 玉女守门：天盘丁奇与门同宫（丁为玉女，守门则百事皆宜）
        for p in palaces:
            if p.get('tian_pan') == '丁' and p.get('men') and p['men'] != '':
                ji_ge.append({'name': '玉女守门', 'gong': p['gong'],
                              'desc': f'丁奇守{p["men"]}，百事皆宜，利于文书'})

        # 16. 天地合德：天盘地盘天干相合（排除已有专用名称的组合）
        # 甲己、丁壬、戊癸 合（乙庚→奇合、丙辛→欢怡已有独立条目，不重复）
        GAN_HE = {'甲': '己', '己': '甲', '丁': '壬', '壬': '丁',
                   '戊': '癸', '癸': '戊'}
        for p in palaces:
            tp = p.get('tian_pan', '')
            dp = p.get('di_pan', '')
            if tp and dp and GAN_HE.get(tp) == dp:
                ji_ge.append({'name': '天地合德', 'gong': p['gong'],
                              'desc': f'{tp}{dp}合，天地和合，谋事易成'})

        # 旬空宫
        kong_wang = xun_kong.get('kong_wang', []) if xun_kong else []
        kong_gongs = []
        for zhi in kong_wang:
            if zhi in self.ZHI_TO_GONG_NUM:
                kong_gongs.append(self.ZHI_TO_GONG_NUM[zhi])

        return {
            'ji_ge': ji_ge,
            'xiong_ge': xiong_ge,
            'kong_wang_gongs': kong_gongs,
            'summary': (
                f"吉格{len(ji_ge)}个，凶格{len(xiong_ge)}个"
                + (f"，旬空宫：{kong_gongs}" if kong_gongs else "")
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
            now = datetime.now()
            solar = Solar.fromYmdHms(now.year, now.month, now.day, now.hour, now.minute, 0)
            lunar = solar.getLunar()
            year_gan = lunar.getYearGan()
            year_zhi = lunar.getYearZhi()
            year_ganzhi = f'{year_gan}{year_zhi}'

            # 太岁地支→宫位
            tai_sui_gong = self.ZHI_TO_GONG_NUM.get(year_zhi, 0)

            # 找到太岁宫的信息
            tai_sui_palace = None
            for p in palaces:
                if p.get('gong') == tai_sui_gong:
                    tai_sui_palace = p
                    break

            return {
                'year': now.year,
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
        except Exception:
            return {}

