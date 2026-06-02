#!/usr/bin/env python3
"""
玄照 v2.0 - 知识库检索接口

高层封装，为视角引擎和问答引擎提供知识检索服务。
"""
from typing import List, Dict, Optional
from .index import (
    search_by_features,
    search_by_bazi,
    search_by_ziwei,
    search_by_astro,
    search_by_query,
)


class KnowledgeSearch:
    """知识库检索器"""

    def search_for_perspective(
        self,
        udm,
        figure_name: str,
        question: str,
        top_n: int = 3,
    ) -> List[Dict]:
        """
        为特定人物视角检索相关知识。

        根据人物擅长的术法，从UDM提取特征，检索最相关的知识片段。
        """
        from engine.udm import DestinyModel

        features = {}

        # 根据人物术法提取特征
        if "八字" in figure_name or figure_name in ("袁天罡", "邵雍", "张仲景", "老子"):
            # 八字视角
            if udm.bazi_year:
                features["day_master"] = [udm.day_master] if udm.day_master else []
                features["wuxing"] = [udm.day_master_wuxing] if udm.day_master_wuxing else []
                features["zhi"] = udm.zhis

                # 十神
                ss = list(set(udm.shishen_gan.values())) if udm.shishen_gan else []
                if ss:
                    features["shishen"] = [s for s in ss if s != "日元"]

                # 冲合
                chong = udm.get_chong()
                if chong:
                    features["relation"] = ["冲"]

        elif "紫微" in figure_name or figure_name == "倪海厦":
            # 紫微视角
            if udm.ziwei_chart:
                features["palace"] = [udm.ziwei_chart.get("ming_gong", "")]
                stars = list(udm.ziwei_chart.get("star_placements", {}).keys())
                if stars:
                    features["star"] = stars[:5]

        elif "占星" in figure_name or figure_name in ("李淳风", "费曼", "荣格"):
            # 占星视角
            if udm.astro_chart:
                features["sign"] = [udm.astro_chart.get("sun_sign", "")]
                if udm.astro_chart.get("moon_sign"):
                    features["sign"].append(udm.astro_chart["moon_sign"])

        elif "奇门" in figure_name or figure_name in ("诸葛亮", "姜子牙", "孙子"):
            # 奇门视角
            features["method"] = ["奇门"]

        elif "六爻" in figure_name or figure_name == "鬼谷子":
            # 六爻视角
            features["method"] = ["六爻"]

        # 问题主题
        theme_keywords = {
            "事业": ["事业", "职业", "工作"],
            "感情": ["感情", "婚姻", "恋爱"],
            "健康": ["健康", "体质", "养生"],
            "财运": ["财运", "财富", "理财"],
        }
        for theme, keywords in theme_keywords.items():
            if any(kw in question for kw in keywords):
                features.setdefault("theme", []).append(theme)

        # 过滤空值
        features = {k: v for k, v in features.items() if v}

        if not features:
            return []

        return search_by_features(features, top_n)

    def search_for_qa(
        self,
        udm,
        question: str,
        top_n: int = 3,
    ) -> List[Dict]:
        """为问答引擎检索相关知识"""
        # 提取八字特征
        features = {}

        if udm.bazi_year:
            features["day_master"] = [udm.day_master] if udm.day_master else []
            features["wuxing"] = [udm.day_master_wuxing] if udm.day_master_wuxing else []
            features["zhi"] = udm.zhis

        if udm.ziwei_chart:
            features.setdefault("palace", []).append(udm.ziwei_chart.get("ming_gong", ""))

        if udm.astro_chart:
            features.setdefault("sign", []).append(udm.astro_chart.get("sun_sign", ""))

        # 问题主题
        if any(kw in question for kw in ["事业", "工作", "职业"]):
            features.setdefault("theme", []).append("事业")
        if any(kw in question for kw in ["感情", "婚姻", "恋爱"]):
            features.setdefault("theme", []).append("感情")
        if any(kw in question for kw in ["健康", "体质", "养生"]):
            features.setdefault("theme", []).append("健康")
        if any(kw in question for kw in ["财", "钱", "富"]):
            features.setdefault("theme", []).append("财运")

        features = {k: v for k, v in features.items() if v}

        if not features:
            return search_by_query(question, top_n)

        return search_by_features(features, top_n)

    def get_knowledge_summary(self, snippets: List[Dict]) -> str:
        """将检索结果汇总为文本片段"""
        parts = []
        for s in snippets:
            parts.append(f"【{s['category']}】{s['title']}")
            parts.append(s.get("snippet", "")[:200])
            parts.append("")
        return "\n".join(parts)
