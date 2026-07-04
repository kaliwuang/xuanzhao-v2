#!/usr/bin/env python3
"""
玄照 v2.0 - 时空修正引擎

核心功能：
1. 解析出生时间（支持多种格式）
2. 城市经纬度查询（内置500+城市）
3. 真太阳时修正（经度修正 + 均时差修正）
4. 早晚子时判定（23:00-24:00用次日日柱）
5. 夏令时回退（中国1986-1991）
6. 节气上下文（月柱判定用）

这是整个系统的根基。所有术法排盘必须通过这个引擎获取修正后的时间。
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
import json
import logging
import math

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CorrectedTime:
    """修正后的精确出生时间"""
    original: datetime          # 用户输入的原始时间
    utc: datetime               # UTC时间
    true_solar: datetime        # 真太阳时
    longitude: float            # 出生地经度
    latitude: float             # 出生地纬度
    location_name: str          # 地点名称
    is_late_zi: bool            # 是否晚子时 (23:00-24:00)
    jieqi_context: dict         # 前后节气信息

    @property
    def bazi_hour(self) -> int:
        """八字用的小时（考虑早晚子时）"""
        if self.is_late_zi:
            return 0  # 子时
        return self.true_solar.hour

    @property
    def bazi_day_pillar_date(self) -> datetime:
        """日柱对应的日期（晚子时算下一天）"""
        if self.is_late_zi:
            return self.true_solar + timedelta(days=1)
        return self.true_solar

    @property
    def hour_zhi(self) -> str:
        """时支（基于真太阳时）"""
        h = self.bazi_hour
        zhi_map = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
        # 23-1 子时, 1-3 丑时, ..., 21-23 亥时
        idx = (h + 1) // 2 % 12
        return zhi_map[idx]


class TimeEngine:
    """时间修正引擎。所有术法排盘必须通过这个引擎获取修正后的时间。"""

    # 中国夏令时历史 (1986-1991)
    # 每年4月中旬第x个周日2:00开始，9月中旬第x个周日2:00结束
    DST_PERIODS = [
        (1986, 5, 4, 9, 14),
        (1987, 4, 12, 9, 13),
        (1988, 4, 17, 9, 11),
        (1989, 4, 16, 9, 17),
        (1990, 4, 15, 9, 16),
        (1991, 4, 14, 9, 15),
    ]

    def __init__(self):
        self._cities = self._load_cities()

    def _load_cities(self) -> dict:
        """加载城市经纬度数据库，优先从 data/cities.json 读取"""
        import json
        cities_file = Path(__file__).parent.parent / "data" / "cities.json"
        if cities_file.exists():
            try:
                with open(cities_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {name: (info["lat"], info["lon"]) for name, info in data.items()}
            except Exception as e:
                logger.debug(f"城市数据库加载失败，回退到内置城市: {e}")

        # 回退：硬编码核心城市
        return {
            "北京": (39.9042, 116.4074),
            "上海": (31.2304, 121.4737),
            "天津": (39.1252, 117.1904),
            "重庆": (29.5630, 106.5516),
            "哈尔滨": (45.8038, 126.5349),
            "长春": (43.8171, 125.3235),
            "沈阳": (41.8057, 123.4315),
            "呼和浩特": (40.8414, 111.7519),
            "通辽": (43.6173, 122.2657),  # B66 修复: 内蒙古
            "包头": (40.6574, 109.8403),  # B66 修复
            "赤峰": (42.2576, 118.8889),  # B66 修复
            "鄂尔多斯": (39.6087, 109.7813),  # B66 修复
            "石家庄": (38.0428, 114.5149),
            "太原": (37.8706, 112.5489),
            "济南": (36.6512, 117.1201),
            "郑州": (34.7466, 113.6253),
            "西安": (34.3416, 108.9398),
            "兰州": (36.0611, 103.8343),
            "银川": (38.4872, 106.2309),
            "西宁": (36.6171, 101.7782),
            "乌鲁木齐": (43.8256, 87.6168),
            "合肥": (31.8206, 117.2272),
            "南京": (32.0603, 118.7969),
            "杭州": (30.2741, 120.1551),
            "南昌": (28.6820, 115.8579),
            "福州": (26.0745, 119.2965),
            "台北": (25.0330, 121.5654),
            "长沙": (28.2280, 112.9388),
            "武汉": (30.5928, 114.3055),
            "广州": (23.1291, 113.2644),
            "海口": (20.0440, 110.1999),
            "南宁": (22.8170, 108.3665),
            "成都": (30.5728, 104.0668),
            "贵阳": (26.6470, 106.6302),
            "昆明": (25.0389, 102.7183),
            "拉萨": (29.6500, 91.1000),
            "深圳": (22.5431, 114.0579),
            "苏州": (31.2989, 120.5853),
            "青岛": (36.0671, 120.3826),
            "大连": (38.9140, 121.6147),
            "宁波": (29.8683, 121.5440),
            "厦门": (24.4798, 118.0894),
            "无锡": (31.4912, 120.3119),
            "佛山": (23.0218, 113.1219),
            "东莞": (23.0489, 113.7447),
            "温州": (28.0000, 120.7000),
            "香港": (22.3193, 114.1694),
            "澳门": (22.1987, 113.5439),
        }

    def correct(self, birth_str: str, location: str) -> CorrectedTime:
        """主入口：原始时间 -> 修正后的精确时间"""
        # 1. 解析原始时间
        original = self._parse_time(birth_str)
        if original is None:
            raise ValueError(f"无法解析出生时间: {birth_str}")

        # 2. 查经纬度
        lat, lon = self._lookup_location(location)

        # 3. 夏令时回退（在本地时间上检查，DST边界是北京时间）
        original = self._undo_dst_local(original)

        # 4. 时区转换（默认东八区）
        utc = self._to_utc(original)

        # 5. 真太阳时修正
        true_solar = self._true_solar_time(utc, lon)

        # 6. 早晚子时判定（基于真太阳时）
        is_late_zi = self._is_late_zi_hour(true_solar)

        # 7. 节气上下文
        jieqi = self._get_jieqi_context(true_solar)

        return CorrectedTime(
            original=original,
            utc=utc,
            true_solar=true_solar,
            longitude=lon,
            latitude=lat,
            location_name=location,
            is_late_zi=is_late_zi,
            jieqi_context=jieqi
        )

    def _parse_time(self, s: str) -> Optional[datetime]:
        """解析多种时间格式"""
        if not s:
            return None
        # 统一处理：+号和下划线作为空格（URL编码兼容）
        s = s.strip().replace('+', ' ').replace('_', ' ')
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y%m%d %H%M%S",
            "%Y%m%d %H%M",
            "%Y%m%d %H",
            "%Y%m%d",
            "%Y-%m-%d %H",
            "%Y-%m-%d",
            "%Y年%m月%d日 %H:%M:%S",
            "%Y年%m月%d日 %H:%M",
            "%Y年%m月%d日 %H时",
            "%Y年%m月%d日",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s.strip(), fmt)
            except ValueError:
                continue
        return None

    # 英文城市名映射
    EN_CITY_MAP = {
        "beijing": "北京", "shanghai": "上海", "tianjin": "天津", "chongqing": "重庆",
        "harbin": "哈尔滨", "changchun": "长春", "shenyang": "沈阳", "hohhot": "呼和浩特",
        "shijiazhuang": "石家庄", "taiyuan": "太原", "jinan": "济南", "zhengzhou": "郑州",
        "xian": "西安", "lanzhou": "兰州", "yinchuan": "银川", "xining": "西宁",
        "urumqi": "乌鲁木齐", "hefei": "合肥", "nanjing": "南京", "hangzhou": "杭州",
        "fuzhou": "福州", "nanchang": "南昌", "changsha": "长沙", "wuhan": "武汉",
        "guangzhou": "广州", "nanning": "南宁", "haikou": "海口", "chengdu": "成都",
        "guiyang": "贵阳", "kunming": "昆明", "lhasa": "拉萨", "taipei": "台北",
        "hongkong": "香港", "macau": "澳门", "shenzhen": "深圳", "dalian": "大连",
        "qingdao": "青岛", "suzhou": "苏州", "xiamen": "厦门", "dali": "大理",
        "wuxi": "无锡", "changzhou": "常州", "guilin": "桂林", "lijiang": "丽江",
        "xishuangbanna": "西双版纳", "zhuhai": "珠海", "dongguan": "东莞", "foshan": "佛山",
        "ningbo": "宁波", "wenzhou": "温州", "yantai": "烟台", "weihai": "威海",
    }

    def _lookup_location(self, loc: str) -> Tuple[float, float]:
        """查询城市经纬度"""
        loc = loc.strip()
        # 先查中文名
        if loc in self._cities:
            return self._cities[loc]
        # 英文名转中文
        loc_lower = loc.lower()
        if loc_lower in self.EN_CITY_MAP:
            cn = self.EN_CITY_MAP[loc_lower]
            if cn in self._cities:
                return self._cities[cn]
        # 尝试去掉行政区划后缀
        for suffix in ["市", "省", "县", "区", "盟", "州", "地区"]:
            if loc.endswith(suffix) and loc[:-len(suffix)] in self._cities:
                return self._cities[loc[:-len(suffix)]]
        # 尝试去掉省级前缀（如"内蒙古呼和浩特市"→"呼和浩特"）
        province_prefixes = ["内蒙古", "新疆", "西藏", "广西", "宁夏", "黑龙江", "河北", "河南", "湖北", "湖南", "山东", "山西", "广东", "四川", "云南", "贵州", "甘肃", "青海", "吉林", "辽宁", "江苏", "浙江", "安徽", "福建", "江西", "陕西", "海南", "台湾"]
        for prefix in province_prefixes:
            if loc.startswith(prefix):
                rest = loc[len(prefix):]
                # 去掉可能的"自治区"后缀
                for sub_suffix in ["自治区", "市", "盟", "州", "地区"]:
                    if rest.endswith(sub_suffix):
                        rest = rest[:-len(sub_suffix)]
                if rest and rest in self._cities:
                    return self._cities[rest]
        # 尝试取第一个词（如"北京市朝阳区"→"北京"）
        if len(loc) > 2:
            for end in range(2, min(5, len(loc))):
                prefix = loc[:end]
                if prefix in self._cities:
                    return self._cities[prefix]
        # 默认北京
        logger.warning(f"城市 '{loc}' 未找到，回退到北京坐标")
        return (39.9042, 116.4074)

    def _to_utc(self, dt: datetime) -> datetime:
        """东八区转UTC"""
        return dt - timedelta(hours=8)

    def _undo_dst_local(self, dt: datetime) -> datetime:
        """回退夏令时（中国1986-1991），在本地时间上检查"""
        for year, start_month, start_day, end_month, end_day in self.DST_PERIODS:
            if dt.year == year:
                start = datetime(year, start_month, start_day, 2)
                end = datetime(year, end_month, end_day, 2)
                if start <= dt < end:
                    return dt - timedelta(hours=1)
        return dt

    def _true_solar_time(self, utc: datetime, longitude: float) -> datetime:
        """
        真太阳时 = 平太阳时 + 经度修正 + 均时差

        经度修正：每度4分钟。东经为正。
        北京在东经120°，所以如果出生地在东经111.7°（呼和浩特），
        真太阳时比北京时间慢 (120-111.7) x 4 = 33.2分钟。
        """
        # 先转回东八区平太阳时
        beijing_time = utc + timedelta(hours=8)

        # 经度修正（分钟）
        longitude_correction = (longitude - 120.0) * 4.0

        # 均时差（equation of time）——基于UTC日期计算（地球轨道位置与观测者时区无关）
        eot = self._equation_of_time(utc)

        # 总修正（分钟）
        total_minutes = longitude_correction + eot

        return beijing_time + timedelta(minutes=total_minutes)

    def _equation_of_time(self, dt: datetime) -> float:
        """
        均时差：由于地球轨道椭圆和自转轴倾斜导致。
        范围约 -14分钟 到 +16分钟。

        简化公式（精度约+-1分钟，足够命理用）：
        e = 9.87*sin(2B) - 7.53*cos(B) - 1.5*sin(B)
        其中 B = 360*(N-81)/365，N为年积日
        """
        N = dt.timetuple().tm_yday
        B = math.radians(360 * (N - 81) / 365)
        e = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
        return e

    def _is_late_zi_hour(self, dt: datetime) -> bool:
        """晚子时：23:00-24:00"""
        return dt.hour == 23

    def _get_jieqi_context(self, dt: datetime) -> dict:
        """获取前后节气信息，用于月柱判定"""
        try:
            from lunar_python import Solar
            solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
            lunar = solar.getLunar()

            jieqi_list = lunar.getJieQiList()
            current = lunar.getCurrentJieQi()
            prev_jie = lunar.getPrevJie()
            next_jie = lunar.getNextJie()

            return {
                "current": str(current) if current else None,
                "prev_jie": str(prev_jie) if prev_jie else None,
                "next_jie": str(next_jie) if next_jie else None,
                "list": [str(j) for j in jieqi_list if j],
            }
        except Exception as e:
            logger.debug(f"lunar_python节气上下文获取异常，回退到空数据: {e}")
            return {"current": None, "prev_jie": None, "next_jie": None, "list": []}


# ─── 节气近似日期表（供 lunar_python 不可用时的回退计算）───
# 格式：(节气名, 月, 日) — 按时间顺序排列
# 用于奇门遁甲和大六壬引擎的回退路径
JIEQI_APPROX_TABLE = [
    ("小寒", 1, 6), ("大寒", 1, 20), ("立春", 2, 4), ("雨水", 2, 19),
    ("惊蛰", 3, 6), ("春分", 3, 21), ("清明", 4, 5), ("谷雨", 4, 20),
    ("立夏", 5, 6), ("小满", 5, 21), ("芒种", 6, 6), ("夏至", 6, 21),
    ("小暑", 7, 7), ("大暑", 7, 23), ("立秋", 8, 7), ("处暑", 8, 23),
    ("白露", 9, 8), ("秋分", 9, 23), ("寒露", 10, 8), ("霜降", 10, 23),
    ("立冬", 11, 7), ("小雪", 11, 22), ("大雪", 12, 7), ("冬至", 12, 22),
]


# 单例
_time_engine = None

def get_time_engine() -> TimeEngine:
    global _time_engine
    if _time_engine is None:
        _time_engine = TimeEngine()
    return _time_engine
