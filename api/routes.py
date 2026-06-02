#!/usr/bin/env python3
"""
玄照 v2.0 - FastAPI 路由
"""
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional

from engine.time_engine import get_time_engine
from engine.base import EngineOrchestrator
from engine.bazi_engine import BaziEngine
from engine.astro_engine import AstroEngine
from engine.ziwei_engine import ZiWeiEngine
from engine.liuyao_engine import LiuYaoEngine
from engine.qimen_engine import QiMenEngine
from engine.liuren_engine import LiuRenEngine
from engine.taiyi_engine import TaiYiEngine
from engine.cross_validator import CrossValidator
from engine.perspective_engine import PerspectiveEngine
from engine.debate_engine import DebateEngine
from engine.qa_engine import QAEngine

router = APIRouter()

# 初始化引擎调度器
_orchestrator = None

def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = EngineOrchestrator()
        _orchestrator.register(BaziEngine())
        _orchestrator.register(AstroEngine())
        _orchestrator.register(ZiWeiEngine())
        _orchestrator.register(LiuYaoEngine())
        _orchestrator.register(QiMenEngine())
        _orchestrator.register(LiuRenEngine())
        _orchestrator.register(TaiYiEngine())
    return _orchestrator


@router.get("/")
def root():
    return {"message": "玄照 v2.0 API", "version": "2.0.0"}


@router.get("/api/chart")
def get_chart(
    birth: str = Query(..., description="出生时间，如 2005-06-09 11:50"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别: 男/女"),
):
    """七术排盘接口"""
    try:
        time_engine = get_time_engine()
        corrected = time_engine.correct(birth, location)

        gender_code = 1 if gender in ("男", "male", "m") else 0

        orch = get_orchestrator()
        udm = orch.run_all(corrected, gender_code)

        # 构建返回数据
        result = {
            "input": {
                "birth": birth,
                "location": location,
                "gender": gender,
            },
            "corrected_time": {
                "original": corrected.original.isoformat(),
                "true_solar": corrected.true_solar.isoformat(),
                "longitude": corrected.longitude,
                "latitude": corrected.latitude,
                "is_late_zi": corrected.is_late_zi,
            },
            "methods": udm.get_available_methods(),
            "errors": udm.engine_errors,
        }

        # 八字
        if udm.bazi_year:
            result["bazi"] = {
                "year": udm.bazi_year.ganzhi,
                "month": udm.bazi_month.ganzhi if udm.bazi_month else "",
                "day": udm.bazi_day.ganzhi if udm.bazi_day else "",
                "time": udm.bazi_time.ganzhi if udm.bazi_time else "",
                "day_master": udm.day_master,
                "day_master_wuxing": udm.day_master_wuxing,
                "shishen": udm.shishen_gan,
                "nayin": udm.nayin,
                "features": udm.features,
                "tiaohou": udm.tiaohou,
            }

        # 占星
        if udm.astro_chart:
            result["astro"] = {
                "sun_sign": udm.astro_chart.get("sun_sign"),
                "sun_element": udm.astro_chart.get("sun_element"),
                "moon_sign": udm.astro_chart.get("moon_sign"),
                "moon_element": udm.astro_chart.get("moon_element"),
                "ascendant": udm.astro_chart.get("ascendant"),
                "ascendant_sign": udm.astro_chart.get("ascendant_sign"),
                "mc": udm.astro_chart.get("mc"),
                "houses": udm.astro_chart.get("houses"),
                "planets": udm.astro_chart.get("planets"),
                "aspects": udm.astro_chart.get("aspects"),
            }

        # 紫微
        if udm.ziwei_chart:
            result["ziwei"] = {
                "ming_gong": udm.ziwei_chart.get("ming_gong"),
                "wuxing_ju": udm.ziwei_chart.get("wuxing_ju"),
                "star_placements": udm.ziwei_chart.get("star_placements"),
                "sihua": udm.ziwei_chart.get("sihua"),
                "palaces": udm.ziwei_chart.get("palaces"),
            }

        # 六爻
        if udm.liuyao_chart:
            result["liuyao"] = {
                "ben_gua": udm.liuyao_chart.get("ben_gua"),
                "dong_yao": udm.liuyao_chart.get("dong_yao"),
            }

        # 奇门
        if udm.qimen_chart:
            result["qimen"] = {
                "ju_name": udm.qimen_chart.get("ju_name"),
                "di_pan": udm.qimen_chart.get("di_pan"),
                "ba_men": udm.qimen_chart.get("ba_men"),
            }

        # 大六壬
        if udm.liuren_chart:
            result["liuren"] = {
                "yue_jiang": udm.liuren_chart.get("yue_jiang"),
                "si_ke": udm.liuren_chart.get("si_ke"),
                "san_chuan": udm.liuren_chart.get("san_chuan"),
            }

        # 太乙
        if udm.taiyi_chart:
            result["taiyi"] = {
                "taiyi_gong": udm.taiyi_chart.get("taiyi_gong"),
                "ji_nian": udm.taiyi_chart.get("ji_nian"),
            }

        return result

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/cross-validate")
def cross_validate(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
):
    """交叉验证接口"""
    try:
        time_engine = get_time_engine()
        corrected = time_engine.correct(birth, location)
        gender_code = 1 if gender in ("男", "male", "m") else 0

        orch = get_orchestrator()
        udm = orch.run_all(corrected, gender_code)

        validator = CrossValidator(udm)
        result = validator.validate()

        # 序列化
        return {
            "method_count": result["method_count"],
            "available_methods": result["available_methods"],
            "overall_confidence": result["overall_confidence"].value,
            "consensus": [
                {
                    "aspect": c.aspect,
                    "finding": c.finding,
                    "supporting_methods": c.supporting_methods,
                    "confidence": c.confidence.value,
                }
                for c in result["consensus"]
            ],
            "conflicts": [
                {
                    "aspect": c.aspect,
                    "method_a": c.method_a,
                    "finding_a": c.finding_a,
                    "method_b": c.method_b,
                    "finding_b": c.finding_b,
                    "suggestion": c.suggestion,
                }
                for c in result["conflicts"]
            ],
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/debate")
def get_debate(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
    question: str = Query("此人命运如何？", description="问题"),
    figures: Optional[str] = Query(None, description="人物ID，逗号分隔，默认全部"),
):
    """辩论接口"""
    try:
        time_engine = get_time_engine()
        corrected = time_engine.correct(birth, location)
        gender_code = 1 if gender in ("男", "male", "m") else 0

        orch = get_orchestrator()
        udm = orch.run_all(corrected, gender_code)

        # 视角推理
        pe = PerspectiveEngine()
        figure_ids = figures.split(",") if figures else None
        opinions = pe.analyze(udm, question, figure_ids)

        # 辩论
        de = DebateEngine()
        debate_result = de.debate(opinions, question)

        return debate_result

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/ask")
def ask_question(
    birth: str = Query(..., description="出生时间"),
    location: str = Query("北京", description="出生地点"),
    gender: str = Query("男", description="性别"),
    question: str = Query(..., description="问题"),
):
    """问答接口"""
    try:
        time_engine = get_time_engine()
        corrected = time_engine.correct(birth, location)
        gender_code = 1 if gender in ("男", "male", "m") else 0

        orch = get_orchestrator()
        udm = orch.run_all(corrected, gender_code)

        qa = QAEngine()
        answer = qa.ask(udm, question)

        return {
            "question": question,
            "question_type": answer.question_type.value,
            "answer": answer.answer,
            "confidence": answer.confidence.value,
            "supporting_methods": answer.supporting_methods,
            "key_points": answer.key_points,
            "warnings": answer.warnings,
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/figures")
def get_figures():
    """获取所有可用人物"""
    from engine.perspective_engine import FIGURES
    return {
        fid: {
            "name": f.name,
            "title": f.title,
            "category": f.category,
            "faction": f.faction,
            "expertise": f.expertise,
            "primary_method": f.primary_method,
            "catchphrase": f.catchphrase,
            "bio": f.bio,
        }
        for fid, f in FIGURES.items()
    }
