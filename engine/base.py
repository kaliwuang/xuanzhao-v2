#!/usr/bin/env python3
"""
玄照 v2.0 - 术法引擎基类

所有术法（八字、紫微、奇门等）必须实现这个接口。
"""
from abc import ABC, abstractmethod
from typing import Optional
from .udm import DestinyModel
from .time_engine import CorrectedTime


class DivinationEngine(ABC):
    """术法引擎基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """术法名称"""
        pass

    @property
    @abstractmethod
    def name_en(self) -> str:
        """术法英文名"""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """
        优先级：八字最核心(1)，紫微次之(2)，其他依次。
        优先级影响交叉验证时的权重。
        """
        pass

    @abstractmethod
    def analyze(self, time: CorrectedTime, gender: int) -> dict:
        """
        分析命盘，返回术法特定的结构化数据。
        由调度器写入 UDM。
        """
        pass

    @abstractmethod
    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        """
        验证排盘结果是否合理。
        返回 (是否有效, 错误信息)。
        """
        pass


class EngineOrchestrator:
    """
    引擎调度器。
    管理所有术法引擎的运行顺序和依赖关系。
    """

    def __init__(self):
        self._engines: list[DivinationEngine] = []

    def register(self, engine: DivinationEngine):
        self._engines.append(engine)
        self._engines.sort(key=lambda e: e.priority)

    def run_all(self, time: CorrectedTime, gender: int) -> DestinyModel:
        """运行所有术法引擎，生成完整的UDM"""
        from .udm import DestinyModel
        udm = DestinyModel(corrected_time=time)

        for engine in self._engines:
            try:
                result = engine.analyze(time, gender)
                valid, error = engine.validate(result)

                if not valid:
                    udm.engine_errors[engine.name] = error or "验证失败"
                    continue

                # 写入UDM
                self._write_to_udm(udm, engine.name, result)

            except Exception as e:
                udm.engine_errors[engine.name] = str(e)

        return udm

    def _write_to_udm(self, udm: DestinyModel, engine_name: str, data: dict):
        """将术法结果写入UDM对应字段"""
        if engine_name == "八字":
            udm.bazi_year = data.get("year")
            udm.bazi_month = data.get("month")
            udm.bazi_day = data.get("day")
            udm.bazi_time = data.get("time")
            udm.day_master = data.get("day_master")
            udm.day_master_wuxing = data.get("day_master_wuxing")
            udm.hidden_gans = data.get("hidden_gans", {})
            udm.shishen_gan = data.get("shishen_gan", {})
            udm.shishen_zhi = data.get("shishen_zhi", {})
            udm.nayin = data.get("nayin", {})
            udm.xunkong = data.get("xunkong", {})
            udm.dayun = data.get("dayun", [])
            udm.dayun_start_year = data.get("dayun_start_year", 0)
            udm.dayun_start_age = data.get("dayun_start_age", 0)
            udm.tiaohou = data.get("tiaohou")
            udm.features = data.get("features", [])
        elif engine_name == "紫微":
            udm.ziwei_chart = data
        elif engine_name == "六爻":
            udm.liuyao_chart = data
        elif engine_name == "奇门":
            udm.qimen_chart = data
        elif engine_name == "大六壬":
            udm.liuren_chart = data
        elif engine_name == "太乙":
            udm.taiyi_chart = data
        elif engine_name == "占星":
            udm.astro_chart = data
