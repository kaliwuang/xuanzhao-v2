#!/usr/bin/env python3
"""
玄照 v2.0 - 太乙神数引擎（kintaiyi后端版）

基于 kintaiyi 库实现标准太乙神数排盘。
kintaiyi 是经过验证的开源太乙神数库。

支持：年計/月計/日計/時計、太乙統宗/金鏡/淘金歌等多種紀法、
      三基、五福、八門、主客算、二十八宿等完整系統。
"""
from .base import DivinationEngine
from .time_engine import CorrectedTime
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# 模块级别预导入kintaiyi（避免在HTTP线程中延迟导入失败）
try:
    from kintaiyi.kintaiyi import Taiyi as _TaiyiClass
    _TAIYI_AVAILABLE = True
except Exception:
    _TAIYI_AVAILABLE = False


# 地支→九宫映射
ZHI_TO_GONG = {
    '子': '坎一宫', '丑': '艮八宫', '寅': '艮八宫',
    '卯': '震三宫', '辰': '巽四宫', '巳': '巽四宫',
    '午': '离九宫', '未': '坤二宫', '申': '坤二宫',
    '酉': '兑七宫', '戌': '乾六宫', '亥': '乾六宫',
}

# 数字→九宫映射
NUM_TO_GONG = {
    1: '坎一宫', 2: '坤二宫', 3: '震三宫', 4: '巽四宫',
    5: '中五宫', 6: '乾六宫', 7: '兑七宫', 8: '艮八宫', 9: '离九宫',
}

# 八卦→地支映射
GUA_TO_ZHI = {
    '坎': '子', '坤': '未', '震': '卯', '巽': '辰',
    '中': '中', '乾': '戌', '兑': '酉', '艮': '丑', '离': '午',
}


class TaiYiEngine(DivinationEngine):
    # 八门名称
    BA_MEN_NAMES = ['休门', '生门', '伤门', '杜门', '景门', '死门', '惊门', '开门']

    # 太乙神数吉凶判断表
    TAIYI_JIXIONG = {
        1: '吉', 2: '凶', 3: '吉', 4: '凶', 5: '吉',
        6: '吉', 7: '吉', 8: '吉', 9: '凶', 10: '凶',
        11: '吉', 12: '凶', 13: '吉', 14: '凶', 15: '吉',
    }

    # 三基关系表
    SANJI_RELATIONS = {
        '君基': '主管国运、领导运势',
        '臣基': '主管辅佐、合作关系',
        '民基': '主管基础、民生运势',
    }

    # 五福解释表
    WUFU_INTERPRETATIONS = {
        '坎一宫': '福在北方，水运旺盛',
        '坤二宫': '福在西南，土运亨通',
        '震三宫': '福在东方，木运发达',
        '巽四宫': '福在东南，木运顺利',
        '中五宫': '福在中央，统摄四方',
        '乾六宫': '福在西北，金运强盛',
        '兑七宫': '福在西方，金运兴旺',
        '艮八宫': '福在东北，土运稳固',
        '离九宫': '福在南方，火运光明',
    }

    """太乙神数引擎（kintaiyi后端）"""

    # 八卦→九宫名映射
    GUA_TO_GONG = {
        '坎': '坎一宫', '坤': '坤二宫', '震': '震三宫', '巽': '巽四宫',
        '中': '中五宫', '乾': '乾六宫', '兑': '兑七宫', '艮': '艮八宫', '离': '离九宫',
    }

    # 主客算强弱阈值（算数通常1-15范围）
    SUAN_STRONG = 7   # >=7为强
    SUAN_MEDIUM = 4   # 4-6为中，<4为弱

    @property
    def name(self) -> str:
        return "太乙"

    @property
    def name_en(self) -> str:
        return "taiyi"

    @property
    def priority(self) -> int:
        return 7

    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        """太乙神数排盘分析

        Args:
            time: 校正后的时间对象
            gender: 性别 (1=男, 0=女)

        Returns:
            dict: 包含太乙神数完整排盘结果
        """
        # 输入校验
        if not time:
            return {"error": "时间对象不能为空"}
        if gender not in (0, 1):
            logger.warning(f"太乙引擎：性别参数异常 gender={gender}，默认为男")
            gender = 1

        # 使用真太阳时排盘，同时处理晚子时（与其他引擎保持一致）
        # 晚子时(23:xx)：日柱用次日日期，时辰用子时(hour=0)
        orig = time.true_solar
        pillar_date = time.bazi_day_pillar_date
        bazi_hour = time.bazi_hour
        year = pillar_date.year
        month = pillar_date.month
        day = pillar_date.day
        hour = bazi_hour

        try:
            if _TAIYI_AVAILABLE:
                t = _TaiyiClass(year, month, day, hour, orig.minute)
            else:
                from kintaiyi.kintaiyi import Taiyi
                t = Taiyi(year, month, day, hour, orig.minute)
        except Exception as e:
            logger.error(f"太乙引擎：kintaiyi初始化失败: {e}")
            return {"error": f"kintaiyi初始化失败: {str(e)}"}

        # 年計太乙統宗（最常用的纪法）
        try:
            result = t.pan(0, 0)
        except Exception as e:
            logger.error(f"太乙引擎：kintaiyi排盘失败: {e}")
            return {"error": f"kintaiyi排盘失败: {str(e)}"}

        converted = self._convert_result(result, year)
        # 添加详细解读
        converted['interpretations'] = self._generate_interpretations(converted)
        return converted

    def _convert_result(self, r, year: int) -> dict:
        """将kintaiyi结果转换为玄照API格式"""
        if not r or not isinstance(r, dict):
            return {"error": "kintaiyi返回数据格式异常（非字典类型）"}

        # 太乙落宫
        try:
            taiyi_num = int(r.get('太乙落宮', 0))
        except (ValueError, TypeError):
            taiyi_num = 0
        taiyi_gua = r.get('太乙', '')
        taiyi_gong = NUM_TO_GONG.get(taiyi_num, f'{taiyi_gua}宫' if taiyi_gua else '')

        # 三基
        san_ji = {
            '君基': self._zhi_to_gong(r.get('君基', '')),
            '臣基': self._zhi_to_gong(r.get('臣基', '')),
            '民基': self._zhi_to_gong(r.get('民基', '')),
        }

        # 五福/帝符/太尊
        wu_fu_gua = r.get('五福', '')
        wu_fu_gong = self._gua_to_gong(wu_fu_gua) if wu_fu_gua else ''

        # 大游/小游（防御numpy类型和非数字值）
        da_you_raw = r.get('大游', 0)
        xiao_you_raw = r.get('小游', 0)
        try:
            da_you = int(da_you_raw) if da_you_raw is not None else 0
        except (ValueError, TypeError):
            da_you = 0
        try:
            xiao_you = int(xiao_you_raw) if xiao_you_raw is not None else 0
        except (ValueError, TypeError):
            xiao_you = 0

        # 局式
        ju_shi = r.get('局式', {}) or {}
        if not isinstance(ju_shi, dict):
            ju_shi = {}
        ju_name = ju_shi.get('文', '')
        ju_num = ju_shi.get('數', 0)
        ji_nian = ju_shi.get('積年數', 0)

        # 阴阳遁（兼容繁简体）
        yin_yang = '阳遁' if ('陽遁' in ju_name or '阳遁' in ju_name) else '阴遁'

        # 天乙/地乙/四神
        tian_yi = r.get('天乙', '')
        di_yi = r.get('地乙', '')
        si_shen = r.get('四神', '')

        # 直符
        zhi_fu = r.get('直符', '')

        # 文昌/始击
        wen_chang = r.get('文昌') or []
        shi_ji = r.get('始擊', '')

        # 主算/客算/定算
        def _native_list(lst):
            """Convert numpy types to native Python types for JSON serialization.
            Handles numpy scalars (.item()), numpy bools, and fallback via type coercion."""
            if not isinstance(lst, list):
                return []
            result = []
            for x in lst:
                if hasattr(x, 'item'):
                    # numpy scalar (int64, float64, bool_, etc.)
                    result.append(x.item())
                elif hasattr(x, '__int__') and hasattr(x, '__float__'):
                    # numpy array-like or custom numeric type
                    try:
                        result.append(int(x))
                    except (ValueError, TypeError):
                        result.append(x)
                else:
                    result.append(x)
            return result

        zhu_suan = _native_list(r.get('主算') or [])
        ke_suan = _native_list(r.get('客算') or [])
        ding_suan = _native_list(r.get('定算') or [])

        # 八门
        ba_men = r.get('八門值事', '')
        ba_men_dist = r.get('八門分佈', {})

        # 干支（安全处理None值）
        ganzhi = r.get('干支') or []
        year_gz = ganzhi[0] if isinstance(ganzhi, (list, tuple)) and len(ganzhi) > 0 else ''
        month_gz = ganzhi[1] if isinstance(ganzhi, (list, tuple)) and len(ganzhi) > 1 else ''
        day_gz = ganzhi[2] if isinstance(ganzhi, (list, tuple)) and len(ganzhi) > 2 else ''
        hour_gz = ganzhi[3] if isinstance(ganzhi, (list, tuple)) and len(ganzhi) > 3 else ''

        # 纪元
        ji_yuan = r.get('紀元', '')

        # 预测
        taisui_su = r.get('太歲值宿斷事', '')
        shiji_su = r.get('始擊值宿斷事', '')
        tian_gan_yu = r.get('十天干歲始擊落宮預測', '')

        # 主客胜负
        zhu_ke = r.get('推主客相闗法', '')
        sheng_fu = r.get('推多少以占勝負', '')

        return {
            'engine': self.name,
            'engine_en': self.name_en,
            'taiyi_gong': taiyi_gong,
            'taiyi_num': taiyi_num,
            'taiyi_gua': taiyi_gua,
            'ju_name': ju_name,
            'ju_num': ju_num,
            'yin_yang': yin_yang,
            'ji_nian': ji_nian,
            'ji_yuan': ji_yuan,
            'year_ganzhi': year_gz,
            'month_ganzhi': month_gz,
            'day_ganzhi': day_gz,
            'hour_ganzhi': hour_gz,
            'san_ji': san_ji,
            'wu_fu': wu_fu_gong,
            'da_you': da_you,
            'xiao_you': xiao_you,
            'tian_yi': self._gua_to_gong(tian_yi) if isinstance(tian_yi, str) and tian_yi else str(tian_yi),
            'di_yi': self._gua_to_gong(di_yi) if isinstance(di_yi, str) and di_yi else str(di_yi),
            'si_shen': si_shen,
            'zhi_fu': zhi_fu,
            'wen_chang': wen_chang,
            'shi_ji': shi_ji,
            'zhu_suan': zhu_suan,
            'ke_suan': ke_suan,
            'ding_suan': ding_suan,
            'ba_men': ba_men,
            'ba_men_dist': self._safe_convert_ba_men_dist(ba_men_dist),
            'tai_su_su': taisui_su,
            'shi_ji_su': shiji_su,
            'tian_gan_yu': tian_gan_yu,
            'zhu_ke': zhu_ke,
            'sheng_fu': sheng_fu,
            'suan_analysis': self._analyze_suan(zhu_suan, ke_suan, ding_suan),
        }

    def _analyze_suan(self, zhu_suan, ke_suan, ding_suan) -> dict:
        """主客算解读分析 - 将主算、客算、定算数值解读为人类可读的判断"""
        analysis = {}

        # 太乙主客算强弱阈值（复用类级常量）

        # 主算解读
        if zhu_suan and isinstance(zhu_suan, list) and len(zhu_suan) > 0:
            zhu_val = zhu_suan[0]
            try:
                zhu_num = int(zhu_val) if not isinstance(zhu_val, int) else zhu_val
                if zhu_num >= self.SUAN_STRONG:
                    analysis['zhu_ji'] = '主算强盛（{}），自身实力雄厚'.format(zhu_num)
                elif zhu_num >= self.SUAN_MEDIUM:
                    analysis['zhu_ji'] = '主算中平（{}），守中有进'.format(zhu_num)
                else:
                    analysis['zhu_ji'] = '主算较弱（{}），宜守不宜攻'.format(zhu_num)
            except (ValueError, TypeError):
                analysis['zhu_ji'] = f'主算：{zhu_val}'

        # 客算解读
        if ke_suan and isinstance(ke_suan, list) and len(ke_suan) > 0:
            ke_val = ke_suan[0]
            try:
                ke_num = int(ke_val) if not isinstance(ke_val, int) else ke_val
                if ke_num >= self.SUAN_STRONG:
                    analysis['ke_ji'] = '客算强盛（{}），外部压力大'.format(ke_num)
                elif ke_num >= self.SUAN_MEDIUM:
                    analysis['ke_ji'] = '客算中平（{}），外力平和'.format(ke_num)
                else:
                    analysis['ke_ji'] = '客算较弱（{}），外部阻力小'.format(ke_num)
            except (ValueError, TypeError):
                analysis['ke_ji'] = f'客算：{ke_val}'

        # 定算综合（与主算/客算相同的强弱解读逻辑）
        if ding_suan and isinstance(ding_suan, list) and len(ding_suan) > 0:
            ding_val = ding_suan[0]
            try:
                ding_num = int(ding_val) if not isinstance(ding_val, int) else ding_val
                if ding_num >= self.SUAN_STRONG:
                    analysis['ding_ji'] = '定算强盛（{}），局势明朗，定数有力'.format(ding_num)
                elif ding_num >= self.SUAN_MEDIUM:
                    analysis['ding_ji'] = '定算中平（{}），局势平稳，守中有进'.format(ding_num)
                else:
                    analysis['ding_ji'] = '定算较弱（{}），局势不明，宜静观其变'.format(ding_num)
            except (ValueError, TypeError):
                analysis['ding_ji'] = f'定算：{ding_val}'

        # 主客对比（安全转换，处理numpy类型和非数字值）
        try:
            zhu_num_safe = int(zhu_suan[0]) if zhu_suan and isinstance(zhu_suan, list) and len(zhu_suan) > 0 else 0
        except (ValueError, TypeError, IndexError):
            zhu_num_safe = 0
        try:
            ke_num_safe = int(ke_suan[0]) if ke_suan and isinstance(ke_suan, list) and len(ke_suan) > 0 else 0
        except (ValueError, TypeError, IndexError):
            ke_num_safe = 0
        # 两个算数都有效时才对比（0表示数据缺失，不参与对比）
        if zhu_num_safe > 0 and ke_num_safe > 0:
            if zhu_num_safe > ke_num_safe:
                analysis['pan_duan'] = f'主强客弱（{zhu_num_safe}>{ke_num_safe}），宜主动出击'
            elif ke_num_safe > zhu_num_safe:
                analysis['pan_duan'] = f'客强主弱（{ke_num_safe}>{zhu_num_safe}），宜以守为攻'
            else:
                analysis['pan_duan'] = f'主客均势（{zhu_num_safe}={ke_num_safe}），随机应变'

        return analysis

    def _zhi_to_gong(self, zhi: str) -> str:
        """地支→九宫名"""
        if not zhi:
            return ''
        return ZHI_TO_GONG.get(zhi, f'{zhi}宫')

    @staticmethod
    def _safe_convert_ba_men_dist(ba_men_dist) -> dict:
        """安全转换八门分布，处理非数字key和numpy类型"""
        if not ba_men_dist or not isinstance(ba_men_dist, dict):
            return {}
        result = {}
        for k, v in ba_men_dist.items():
            try:
                gong = NUM_TO_GONG.get(int(k), str(k))
            except (ValueError, TypeError):
                gong = str(k)
            # Convert numpy types
            if hasattr(v, 'item'):
                v = v.item()
            result[gong] = v
        return result

    def _gua_to_gong(self, gua: str) -> str:
        """八卦→九宫名"""
        if not gua:
            return ''
        return self.GUA_TO_GONG.get(gua, f'{gua}宫')

    def _generate_interpretations(self, data: dict) -> dict:
        """生成太乙神数各要素的详细解读"""
        interpretations = {}

        # 太乙落宫解读
        taiyi_gong = data.get('taiyi_gong', '')
        if taiyi_gong:
            interpretations['taiyi'] = self._interpret_taiyi_position(taiyi_gong, data.get('yin_yang', ''))

        # 三基解读
        san_ji = data.get('san_ji', {})
        if san_ji:
            interpretations['sanji'] = self._interpret_sanji(san_ji)

        # 五福解读
        wu_fu = data.get('wu_fu', '')
        if wu_fu:
            interpretations['wufu'] = self._interpret_wufu(wu_fu)

        # 主客算解读
        zhu_suan = data.get('zhu_suan', [])
        ke_suan = data.get('ke_suan', [])
        if zhu_suan or ke_suan:
            interpretations['suan'] = self._interpret_suan_detail(zhu_suan, ke_suan)

        # 八门解读
        ba_men = data.get('ba_men', '')
        ba_men_dist = data.get('ba_men_dist', {})
        if ba_men or ba_men_dist:
            interpretations['bamen'] = self._interpret_bamen(ba_men, ba_men_dist)

        # 大游小游解读
        da_you = data.get('da_you', 0)
        xiao_you = data.get('xiao_you', 0)
        if da_you or xiao_you:
            interpretations['you'] = self._interpret_you(da_you, xiao_you)

        # 天乙地乙四神解读
        tian_yi = data.get('tian_yi', '')
        di_yi = data.get('di_yi', '')
        si_shen = data.get('si_shen', '')
        if tian_yi or di_yi or si_shen:
            interpretations['sishen'] = self._interpret_sishen(tian_yi, di_yi, si_shen)

        # 局式解读
        ju_name = data.get('ju_name', '')
        ju_num = data.get('ju_num', 0)
        if ju_name or ju_num:
            interpretations['jushi'] = self._interpret_jushi(ju_name, ju_num, data.get('yin_yang', ''))

        # 文昌始击解读
        wen_chang = data.get('wen_chang', [])
        shi_ji = data.get('shi_ji', '')
        if wen_chang or shi_ji:
            interpretations['wenshang'] = self._interpret_wenchang_shiji(wen_chang, shi_ji)

        return interpretations

    def _interpret_taiyi_position(self, gong: str, yin_yang: str) -> dict:
        """解读太乙落宫"""
        gong_meanings = {
            '坎一宫': {'element': '水', 'nature': '智慧、变通', 'advice': '宜深思熟虑，以智取胜'},
            '坤二宫': {'element': '土', 'nature': '包容、厚德', 'advice': '宜厚德载物，稳扎稳打'},
            '震三宫': {'element': '木', 'nature': '奋发、进取', 'advice': '宜积极行动，把握时机'},
            '巽四宫': {'element': '木', 'nature': '顺达、通达', 'advice': '宜顺势而为，灵活应变'},
            '中五宫': {'element': '土', 'nature': '统摄、中枢', 'advice': '宜居中调度，统筹全局'},
            '乾六宫': {'element': '金', 'nature': '刚健、决断', 'advice': '宜果断决策，刚健有力'},
            '兑七宫': {'element': '金', 'nature': '喜悦、和合', 'advice': '宜和气生财，人际和谐'},
            '艮八宫': {'element': '土', 'nature': '稳固、止定', 'advice': '宜稳守待机，厚积薄发'},
            '离九宫': {'element': '火', 'nature': '光明、文明', 'advice': '宜光明正大，以德服人'},
        }
        info = gong_meanings.get(gong, {'element': '未知', 'nature': '待查', 'advice': '宜静观其变'})
        return {
            '落宫': gong,
            '五行': info['element'],
            '性质': info['nature'],
            '建议': info['advice'],
            '遁式': yin_yang,
        }

    def _interpret_sanji(self, san_ji: dict) -> dict:
        """解读三基"""
        result = {}
        for name, gong in san_ji.items():
            if gong:
                relation = self.SANJI_RELATIONS.get(name, '')
                wufu_interp = self.WUFU_INTERPRETATIONS.get(gong, '')
                result[name] = {
                    '落宫': gong,
                    '职能': relation,
                    '宫位含义': wufu_interp,
                }
        return result

    def _interpret_wufu(self, wu_fu: str) -> dict:
        """解读五福"""
        return {
            '落宫': wu_fu,
            '含义': self.WUFU_INTERPRETATIONS.get(wu_fu, '五福临门，吉祥如意'),
            '建议': '五福所在之宫为吉位，宜在此方位行事',
        }

    def _interpret_suan_detail(self, zhu_suan: list, ke_suan: list) -> dict:
        """解读主客算详细信息"""
        result = {'主算': [], '客算': []}

        for i, val in enumerate(zhu_suan):
            try:
                num = int(val)
                jixiong = self.TAIYI_JIXIONG.get(num, '平')
                result['主算'].append({
                    '数值': num,
                    '吉凶': jixiong,
                    '含义': f'主算第{i+1}位：{num}，{jixiong}',
                })
            except (ValueError, TypeError):
                pass

        for i, val in enumerate(ke_suan):
            try:
                num = int(val)
                jixiong = self.TAIYI_JIXIONG.get(num, '平')
                result['客算'].append({
                    '数值': num,
                    '吉凶': jixiong,
                    '含义': f'客算第{i+1}位：{num}，{jixiong}',
                })
            except (ValueError, TypeError):
                pass

        return result

    def _interpret_bamen(self, ba_men: str, ba_men_dist: dict) -> dict:
        """解读八门"""
        bamen_meanings = {
            '休门': {'吉凶': '吉', '含义': '休养生息，宜休息、养生'},
            '生门': {'吉凶': '吉', '含义': '生机勃勃，宜求财、开业'},
            '伤门': {'吉凶': '凶', '含义': '伤损之象，宜诉讼、讨债'},
            '杜门': {'吉凶': '凶', '含义': '闭塞不通，宜隐藏、保密'},
            '景门': {'吉凶': '吉', '含义': '光明景象，宜考试、文书'},
            '死门': {'吉凶': '凶', '含义': '死气沉沉，宜丧葬、破土'},
            '惊门': {'吉凶': '凶', '含义': '惊恐不安，宜诉讼、争斗'},
            '开门': {'吉凶': '吉', '含义': '开放通达，宜开业、出行'},
        }
        result = {'值事门': ba_men}
        if ba_men in bamen_meanings:
            result['值事门含义'] = bamen_meanings[ba_men]

        if ba_men_dist:
            result['八门分布'] = {}
            for gong, men in ba_men_dist.items():
                if men in bamen_meanings:
                    result['八门分布'][gong] = {
                        '门': men,
                        '吉凶': bamen_meanings[men]['吉凶'],
                        '含义': bamen_meanings[men]['含义'],
                    }
        return result

    def _interpret_you(self, da_you: int, xiao_you: int) -> dict:
        """解读大游小游"""
        result = {}
        if da_you:
            gong = NUM_TO_GONG.get(da_you, '')
            result['大游'] = {
                '数值': da_you,
                '落宫': gong,
                '含义': f'大游星落{gong}，主管大势变迁',
            }
        if xiao_you:
            gong = NUM_TO_GONG.get(xiao_you, '')
            result['小游'] = {
                '数值': xiao_you,
                '落宫': gong,
                '含义': f'小游星落{gong}，主管小事变化',
            }
        return result

    def _interpret_sishen(self, tian_yi: str, di_yi: str, si_shen: str) -> dict:
        """解读天乙、地乙、四神"""
        result = {}
        if tian_yi:
            result['天乙'] = {
                '落宫': tian_yi,
                '含义': f'天乙贵人落{tian_yi}，主贵人相助',
            }
        if di_yi:
            result['地乙'] = {
                '落宫': di_yi,
                '含义': f'地乙贵人落{di_yi}，主地理优势',
            }
        if si_shen:
            result['四神'] = {
                '落宫': si_shen,
                '含义': f'四神落{si_shen}，主四方护佑',
            }
        return result

    def _interpret_jushi(self, ju_name: str, ju_num: int, yin_yang: str) -> dict:
        """解读局式"""
        return {
            '局名': ju_name,
            '局数': ju_num,
            '遁式': yin_yang,
            '含义': f'{yin_yang}{ju_name}，第{ju_num}局',
            '建议': '阳遁宜主动出击，阴遁宜静守待机' if '阳' in yin_yang else '阴遁宜韬光养晦，静待时机',
        }

    def _interpret_wenchang_shiji(self, wen_chang: list, shi_ji: str) -> dict:
        """解读文昌、始击"""
        result = {}
        if wen_chang:
            result['文昌'] = {
                '位置': wen_chang,
                '含义': '文昌所在为文运亨通之处，宜读书考试',
            }
        if shi_ji:
            result['始击'] = {
                '位置': shi_ji,
                '含义': '始击所在为行动发起之处，宜主动出击',
            }
        return result

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if data.get('error'):
            return False, data['error']
        if not data.get('taiyi_gong'):
            return False, "太乙宫位为空"
        return True, None
