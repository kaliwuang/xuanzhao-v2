#!/usr/bin/env python3
"""
玄照 v2.0 - 内容质量检查引擎

根据玄学泰斗写作规范，检查输出内容质量。
核心规则：
1. 禁用词检查（首先/其次/因此/然而等）
2. 句子长度检查（每句不超过25字）
3. 比喻数量检查（至少3种）
4. 七段结构检查
"""
from typing import List, Dict, Tuple
import re


class ContentChecker:
    """内容质量检查器"""

    # 禁用词清单（仅限AI写作常见模板词）
    BANNED_WORDS = [
        "首先", "其次", "最后", "综上所述", "值得注意的是",
        "因此", "从而", "由此可见", "本质上", "深入",
        "总的来说", "换言之", "与此同时", "毋庸置疑", "显而易见",
        "不言而喻",
    ]

    # 比喻关键词（避免把"是"当比喻，排除日常用法）
    METAPHOR_PATTERNS = [
        "像", "如同", "犹如", "仿佛", "好比",
        "恰似", "宛如", "好似",
    ]

    def __init__(self):
        pass

    def check(self, text: str) -> Dict:
        """全面检查文本质量"""
        results = {
            "passed": True,
            "score": 100,
            "issues": [],
        }

        # 1. 禁用词检查
        banned = self._check_banned_words(text)
        if banned:
            results["issues"].append({
                "type": "禁用词",
                "severity": "高",
                "details": banned,
            })
            results["score"] -= len(banned) * 5

        # 2. 句子长度检查
        long_sentences = self._check_sentence_length(text)
        if long_sentences:
            results["issues"].append({
                "type": "超长句",
                "severity": "中",
                "details": f"{len(long_sentences)} 句超过25字",
            })
            results["score"] -= len(long_sentences) * 2

        # 3. 比喻检查
        metaphors = self._check_metaphors(text)
        if metaphors < 3:
            results["issues"].append({
                "type": "比喻不足",
                "severity": "中",
                "details": f"仅 {metaphors} 种比喻，要求至少3种",
            })
            results["score"] -= (3 - metaphors) * 5

        # 4. 段落长度检查
        long_paragraphs = self._check_paragraph_length(text)
        if long_paragraphs:
            results["issues"].append({
                "type": "超长段落",
                "severity": "低",
                "details": f"{len(long_paragraphs)} 段超过3句",
            })
            results["score"] -= len(long_paragraphs) * 1

        # 5. 七段结构检查
        structure = self._check_structure(text)
        if structure < 5:
            results["issues"].append({
                "type": "结构不完整",
                "severity": "中",
                "details": f"检测到 {structure}/7 段结构",
            })
            results["score"] -= (7 - structure) * 3

        results["score"] = max(0, results["score"])
        results["passed"] = results["score"] >= 80 and not any(
            i["severity"] == "高" for i in results["issues"]
        )

        return results

    def _check_banned_words(self, text: str) -> List[str]:
        """检查禁用词"""
        found = []
        for word in self.BANNED_WORDS:
            if word in text:
                # 统计出现次数
                count = text.count(word)
                for _ in range(count):
                    found.append(word)
        return found

    def _check_sentence_length(self, text: str, max_len: int = 25) -> List[str]:
        """检查超长句"""
        long_sentences = []
        # 按标点分句
        sentences = re.split(r'[。！？；\.\!\?\;]', text)
        for s in sentences:
            s = s.strip()
            if len(s) > max_len:
                long_sentences.append(s[:50] + "...")
        return long_sentences

    def _check_metaphors(self, text: str) -> int:
        """检查比喻数量"""
        count = 0
        for pattern in self.METAPHOR_PATTERNS:
            if pattern in text:
                count += 1
        return count

    def _check_paragraph_length(self, text: str, max_sentences: int = 3) -> List[str]:
        """检查段落长度"""
        long_paragraphs = []
        paragraphs = text.split("\n\n")
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            sentences = re.split(r'[。！？]', p)
            sentences = [s for s in sentences if s.strip()]
            if len(sentences) > max_sentences:
                long_paragraphs.append(p[:50] + "...")
        return long_paragraphs

    # 七段结构：每段对应的关键词组（任一匹配即算该段存在）
    STRUCTURE_KEYWORD_GROUPS = [
        ["真实场景", "场景", "开场", "引子", "开篇"],
        ["概念解析", "概念", "原理", "本质", "定义"],
        ["四层机制", "机制", "层次", "逻辑", "推演"],
        ["操作", "方法", "步骤", "实践", "行动"],
        ["错误", "误区", "注意", "陷阱", "禁忌"],
        ["应用", "案例", "实例", "实证", "印证"],
        ["顿悟", "溟说", "总结", "归真", "结语"],
    ]

    def _check_structure(self, text: str) -> int:
        """检查七段结构——每段用一组关键词匹配，命中任一即算该段存在"""
        sections_found = 0
        for group in self.STRUCTURE_KEYWORD_GROUPS:
            if any(kw in text for kw in group):
                sections_found += 1
        return sections_found

    def quick_check(self, text: str) -> Tuple[bool, str]:
        """快速检查，返回 (是否通过, 问题摘要)"""
        result = self.check(text)
        if result["passed"]:
            return True, f"通过（{result['score']}分）"

        summary = []
        for issue in result["issues"]:
            summary.append(f"[{issue['severity']}] {issue['type']}")
        return False, f"未通过（{result['score']}分）：{', '.join(summary)}"


def check_text(text: str) -> Dict:
    """便捷函数"""
    checker = ContentChecker()
    return checker.check(text)
