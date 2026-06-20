#!/usr/bin/env python3
"""
玄照 v2.0 - 知识库索引引擎

扫描本地知识库，按命盘特征建立倒排索引。
支持关键词：日主、五行、十神、格局、冲合、宫位、术法等。
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

# 知识库根目录（本地）
KNOWLEDGE_BASE = Path(__file__).parent / "data"
INDEX_FILE = Path(__file__).parent / "knowledge_index.json"

# 索引关键词词典
KEYWORDS = {
    # 日主天干
    "day_master": ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"],
    # 五行
    "wuxing": ["木", "火", "土", "金", "水"],
    # 十神
    "shishen": ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"],
    # 地支
    "zhi": ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"],
    # 冲合
    "relation": ["冲", "合", "刑", "害", "破"],
    # 格局
    "pattern": ["正官格", "七杀格", "正印格", "偏印格", "正财格", "偏财格", "食神格", "伤官格", "建禄格", "月刃格"],
    # 宫位（紫微）
    "palace": ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "奴仆", "官禄", "田宅", "福德", "父母"],
    # 主星（紫微）
    "star": ["紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"],
    # 星座（占星）
    "sign": ["白羊", "金牛", "双子", "巨蟹", "狮子", "处女", "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼"],
    # 术法分类
    "method": ["八字", "紫微", "占星", "六爻", "奇门", "大六壬", "太乙", "风水", "面相", "手相", "塔罗"],
    # 人生主题
    "theme": ["事业", "感情", "婚姻", "财运", "健康", "学业", "人际", "子女", "父母", "贵人"],
    # 八门（奇门）
    "gate": ["开门", "休门", "生门", "伤门", "杜门", "景门", "死门", "惊门"],
    # 九星（奇门）
    "star9": ["天蓬", "天芮", "天冲", "天辅", "天禽", "天心", "天柱", "天任", "天英"],
    # 六神（六爻）
    "god6": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
    # 十二天将（六壬）
    "general12": ["贵人", "螣蛇", "朱雀", "六合", "勾陈", "青龙", "天空", "白虎", "太常", "玄武", "太阴", "天后"],
    # 四化（紫微）
    "hua": ["化禄", "化权", "化科", "化忌"],
    # 面相部位
    "face": ["额头", "眉毛", "眼睛", "鼻子", "嘴巴", "耳朵", "印堂", "山根"],
    # 姓名学
    "name": ["天格", "人格", "地格", "外格", "总格", "三才", "五格"],
}


def _extract_keywords(text: str) -> Dict[str, Set[str]]:
    """从文本中提取命盘相关关键词"""
    found = defaultdict(set)

    for category, words in KEYWORDS.items():
        for word in words:
            if word in text:
                found[category].add(word)

    return dict(found)


def _scan_knowledge_base() -> List[Dict]:
    """扫描本地知识库目录，返回所有文档信息"""
    docs = []

    if not KNOWLEDGE_BASE.exists():
        return docs

    for root, dirs, files in os.walk(KNOWLEDGE_BASE):
        # 跳过隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        rel_root = Path(root).relative_to(KNOWLEDGE_BASE)
        category = str(rel_root).replace("\\", "/").split("/")[0] if rel_root != Path(".") else "其他"
        subcategory = str(rel_root).replace("\\", "/").split("/")[1] if len(str(rel_root).replace("\\", "/").split("/")) > 1 else ""

        for filename in files:
            if not filename.endswith((".md", ".txt")):
                continue

            filepath = Path(root) / filename
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue

            # 提取关键词
            keywords = _extract_keywords(text)
            if not any(keywords.values()):
                continue  # 跳过无关文件

            doc = {
                "path": str(filepath),
                "category": category,
                "subcategory": subcategory,
                "filename": filename,
                "title": filename.replace(".md", "").replace(".txt", ""),
                "size": len(text),
                "keywords": {k: list(v) for k, v in keywords.items()},
            }
            docs.append(doc)

    return docs


def build_index(force: bool = False) -> Dict:
    """构建知识库倒排索引"""
    if not force and INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    docs = _scan_knowledge_base()

    # 倒排索引
    inverted_index = defaultdict(lambda: defaultdict(list))

    for doc in docs:
        for category, words in doc["keywords"].items():
            for word in words:
                inverted_index[category][word].append({
                    "path": doc["path"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "subcategory": doc["subcategory"],
                })

    # 统计
    stats = {
        "total_docs": len(docs),
        "total_categories": len(set(d["category"] for d in docs)),
        "keyword_coverage": {cat: len(words) for cat, words in inverted_index.items()},
    }

    index = {
        "version": "2.0",
        "stats": stats,
        "docs": docs,
        "inverted_index": {k: dict(v) for k, v in inverted_index.items()},
    }

    # 保存
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return index


def search_by_features(features: Dict[str, List[str]], top_n: int = 5) -> List[Dict]:
    """
    根据命盘特征搜索相关知识。

    features: {
        "day_master": ["甲"],
        "wuxing": ["木"],
        "shishen": ["正官"],
        "zhi": ["子", "午"],
        ...
    }
    """
    index = build_index()
    inv = index.get("inverted_index", {})

    # 计分
    scores = defaultdict(float)
    doc_info = {}

    for category, words in features.items():
        if category not in inv:
            continue
        for word in words:
            for doc in inv[category].get(word, []):
                key = doc["path"]
                scores[key] += 1.0
                if key not in doc_info:
                    doc_info[key] = doc

    # 排序
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

    results = []
    for path, score in ranked:
        info = doc_info[path]
        # 读取片段
        snippet = _get_snippet(path, features)
        results.append({
            "path": path,
            "title": info["title"],
            "category": info["category"],
            "subcategory": info["subcategory"],
            "score": round(score, 2),
            "snippet": snippet,
        })

    return results


def search_by_query(query: str, top_n: int = 5) -> List[Dict]:
    """用自然语言查询知识库"""
    # 从查询中提取关键词
    features = defaultdict(list)

    for category, words in KEYWORDS.items():
        for word in words:
            if word in query:
                features[category].append(word)

    if not features:
        return []

    return search_by_features(dict(features), top_n)


def _get_snippet(filepath: str, features: Dict[str, List[str]], max_chars: int = 300) -> str:
    """从文档中提取包含关键词的片段"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return ""

    # 找第一个包含关键词的句子
    all_keywords = [w for words in features.values() for w in words]

    for i in range(0, len(text), 50):
        window = text[i:i + max_chars]
        if any(kw in window for kw in all_keywords):
            return window.strip()

    return text[:max_chars].strip()


# 便捷函数

def search_by_bazi(day_master: str, wuxing: str, shishen: List[str] = None, zhis: List[str] = None) -> List[Dict]:
    """根据八字特征搜索"""
    features = {
        "day_master": [day_master],
        "wuxing": [wuxing],
    }
    if shishen:
        features["shishen"] = shishen
    if zhis:
        features["zhi"] = zhis
    return search_by_features(features)


def search_by_ziwei(ming_gong: str, stars: List[str] = None) -> List[Dict]:
    """根据紫微特征搜索"""
    features = {
        "palace": [ming_gong],
    }
    if stars:
        features["star"] = stars
    return search_by_features(features)


def search_by_astro(sun_sign: str, moon_sign: str = None) -> List[Dict]:
    """根据占星特征搜索"""
    features = {
        "sign": [sun_sign],
    }
    if moon_sign:
        features["sign"].append(moon_sign)
    return search_by_features(features)


if __name__ == "__main__":
    # 构建索引
    idx = build_index(force=True)
    print(f"索引构建完成：{idx['stats']['total_docs']} 篇文档")
    print(f"覆盖分类：{idx['stats']['total_categories']} 个")
    print(f"关键词覆盖：{idx['stats']['keyword_coverage']}")

    # 测试搜索
    print("\n--- 测试：甲木日主 ---")
    results = search_by_bazi(day_master="甲", wuxing="木")
    for r in results[:3]:
        print(f"  [{r['category']}] {r['title']} (score:{r['score']})")
