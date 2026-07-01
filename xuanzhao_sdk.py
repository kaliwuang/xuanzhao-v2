#!/usr/bin/env python3
"""
玄照 SDK — 让任何 agent 立即变成玄学泰斗
用法:
    from xuanzhao import Xuanzhao
    xz = Xuanzhao()
    result = xz.chart("2006-10-24 11:50", "北京", gender="女")
    print(result.summary())
"""
import urllib.request
import urllib.parse
import json
from typing import Optional, Dict, Any, List


class Xuanzhao:
    """玄照主动 agent 装甲"""

    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url.rstrip("/")

    def _call(self, path, params=None, timeout=30):
        if params:
            qs = urllib.parse.urlencode(params)
            url = f"{self.base_url}{path}?{qs}"
        else:
            url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def chart(self, birth: str, location: str, gender: str = "男") -> Dict[str, Any]:
        """完整排盘(8术合一)"""
        return self._call("/api/chart", {
            "birth": birth, "location": location, "gender": gender
        })

    def bazi(self, birth: str, location: str, gender: str = "男") -> Dict[str, Any]:
        """八字排盘"""
        return self.chart(birth, location, gender).get("bazi", {})

    def score(self, birth: str, location: str, gender: str = "男") -> Dict[str, Any]:
        """评分 + advice"""
        return self._call("/api/bazi/score", {
            "birth": birth, "location": location, "gender": gender
        })

    def debate(self, birth: str, location: str, gender: str = "男", topic: str = "") -> Dict[str, Any]:
        """108 视角辩论"""
        return self._call("/api/debate", {
            "birth": birth, "location": location, "gender": gender, "topic": topic
        })

    def cross_validate(self, birth: str, location: str, gender: str = "男") -> Dict[str, Any]:
        """8术交叉验证"""
        return self._call("/api/cross-validate", {
            "birth": birth, "location": location, "gender": gender
        })

    def summary(self, birth: str, location: str, gender: str = "男") -> str:
        """白话总结 (溟玄风格)"""
        score = self.score(birth, location, gender)
        advice_lines = []
        for item in score.get("details", []):
            title = item.get("title", "")
            score_v = item.get("score", 0)
            max_v = item.get("max", 20)
            advice = item.get("advice", "")
            if score_v < max_v * 0.5:
                advice_lines.append(f"⚠️ {title} ({score_v}/{max_v}): {advice}")
            else:
                advice_lines.append(f"✅ {title} ({score_v}/{max_v})")
        return "\n".join(advice_lines)

    def health(self) -> bool:
        """健康检查"""
        try:
            r = self._call("/", timeout=5)
            return True
        except Exception:
            return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m xuanzhao_sdk chart '2006-10-24 11:50' 北京 女")
        print("  python -m xuanzhao_sdk score '2006-10-24 11:50' 北京 女")
        print("  python -m xuanzhao_sdk summary '2006-10-24 11:50' 北京 女")
        print("  python -m xuanzhao_sdk health")
        sys.exit(1)

    cmd = sys.argv[1]
    xz = Xuanzhao()

    if cmd == "health":
        print("✅ 健康" if xz.health() else "❌ 不健康")
    elif cmd == "chart":
        birth = sys.argv[2]
        loc = sys.argv[3]
        gender = sys.argv[4] if len(sys.argv) > 4 else "男"
        d = xz.chart(birth, loc, gender)
        print(f"日主: {d['bazi'].get('day_master','')} ({d['bazi'].get('day_master_wuxing','')})")
        print(f"喜: {d['bazi'].get('xi_yong',{}).get('xi','')}")
        print(f"忌: {d['bazi'].get('xi_yong',{}).get('ji','')}")
    elif cmd == "score":
        birth = sys.argv[2]
        loc = sys.argv[3]
        gender = sys.argv[4] if len(sys.argv) > 4 else "男"
        d = xz.score(birth, loc, gender)
        print(f"总分: {d.get('total_score',0)} ({d.get('grade','')})")
        print(f"\n{d.get('summary','')}\n")
        for item in d.get("details", []):
            print(f"{item['title']}: {item['score']}/{item['max']}")
            print(f"  {item.get('text','')[:80]}")
            print(f"  → {item.get('advice','')[:120]}")
            print()
    elif cmd == "summary":
        birth = sys.argv[2]
        loc = sys.argv[3]
        gender = sys.argv[4] if len(sys.argv) > 4 else "男"
        print(xz.summary(birth, loc, gender))
    else:
        print(f"未知命令: {cmd}")