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
    """太乙神数引擎（kintaiyi后端）"""

    # 八卦→九宫名映射
    GUA_TO_GONG = {
        '坎': '坎一宫', '坤': '坤二宫', '震': '震三宫', '巽': '巽四宫',
        '中': '中五宫', '乾': '乾六宫', '兑': '兑七宫', '艮': '艮八宫', '离': '离九宫',
    }

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
            return {"error": f"kintaiyi初始化失败: {str(e)}"}

        # 年計太乙統宗（最常用的纪法）
        try:
            result = t.pan(0, 0)
        except Exception as e:
            return {"error": f"kintaiyi排盘失败: {str(e)}"}

        return self._convert_result(result, year)

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
            """Convert numpy types to native Python types for JSON serialization"""
            if not isinstance(lst, list):
                return []
            return [int(x) if hasattr(x, 'item') else x for x in lst]

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

        # 太乙主客算强弱阈值（算数通常1-15范围）
        SUAN_STRONG = 7   # ≥7为强
        SUAN_MEDIUM = 4   # 4-6为中，<4为弱

        # 主算解读
        if zhu_suan:
            zhu_val = zhu_suan[0] if isinstance(zhu_suan, list) and zhu_suan else zhu_suan
            try:
                zhu_num = int(zhu_val) if not isinstance(zhu_val, int) else zhu_val
                if zhu_num >= SUAN_STRONG:
                    analysis['zhu_ji'] = '主算强盛（{}），自身实力雄厚'.format(zhu_num)
                elif zhu_num >= SUAN_MEDIUM:
                    analysis['zhu_ji'] = '主算中平（{}），守中有进'.format(zhu_num)
                else:
                    analysis['zhu_ji'] = '主算较弱（{}），宜守不宜攻'.format(zhu_num)
            except (ValueError, TypeError):
                analysis['zhu_ji'] = f'主算：{zhu_val}'

        # 客算解读
        if ke_suan:
            ke_val = ke_suan[0] if isinstance(ke_suan, list) and ke_suan else ke_suan
            try:
                ke_num = int(ke_val) if not isinstance(ke_val, int) else ke_val
                if ke_num >= SUAN_STRONG:
                    analysis['ke_ji'] = '客算强盛（{}），外部压力大'.format(ke_num)
                elif ke_num >= SUAN_MEDIUM:
                    analysis['ke_ji'] = '客算中平（{}），外力平和'.format(ke_num)
                else:
                    analysis['ke_ji'] = '客算较弱（{}），外部阻力小'.format(ke_num)
            except (ValueError, TypeError):
                analysis['ke_ji'] = f'客算：{ke_val}'

        # 定算综合
        if ding_suan:
            ding_val = ding_suan[0] if isinstance(ding_suan, list) and ding_suan else ding_suan
            analysis['ding_ji'] = f'定算：{ding_val}'

        # 主客对比（安全转换，处理numpy类型和非数字值）
        try:
            zhu_num_safe = int(zhu_suan[0]) if zhu_suan and isinstance(zhu_suan, list) else 0
        except (ValueError, TypeError, IndexError):
            zhu_num_safe = 0
        try:
            ke_num_safe = int(ke_suan[0]) if ke_suan and isinstance(ke_suan, list) else 0
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

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        if data.get('error'):
            return False, data['error']
        if not data.get('taiyi_gong'):
            return False, "太乙宫位为空"
        return True, None
