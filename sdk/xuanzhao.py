"""
玄照 SDK - 让任何 agent 立即具备玄学泰斗能力
"""
import urllib.request
import urllib.parse
import json
from typing import Optional, Dict, List


class XuanzhaoArmor:
    """
    钢铁侠式玄学装甲
    用法:
        armor = XuanzhaoArmor(base_url="http://localhost:8080")
        result = armor.chart("2005-06-09", "11:50", "呼和浩特", "男")
        advice = armor.advise(result)
    """

    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url.rstrip("/")

    def _get(self, path, **params):
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base_url}{path}?{qs}"
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())

    def chart(self, birth_date: str, birth_time: str, location: str = "北京", gender: str = "男", name: str = "") -> dict:
        """
        八术排盘(八字/紫微/占星/六爻/奇门/大六壬/太乙/姓名学)
        birth_date: "YYYY-MM-DD"
        birth_time: "HH:MM"
        """
        return self._get("/api/chart",
                         birth=f"{birth_date} {birth_time}",
                         location=location,
                         gender=gender,
                         name=name)

    def score(self, birth_date: str, birth_time: str, location: str = "北京", gender: str = "男") -> dict:
        """7维度评分 + 可执行 advice"""
        return self._get("/api/bazi/score",
                         birth=f"{birth_date} {birth_time}",
                         location=location,
                         gender=gender)

    def cross_validate(self, birth_date: str, birth_time: str, location: str = "北京", gender: str = "男",
                       aspects: List[str] = None) -> dict:
        """8术交叉验证"""
        params = {
            "birth": f"{birth_date} {birth_time}",
            "location": location,
            "gender": gender,
        }
        if aspects:
            params["aspects"] = ",".join(aspects)
        return self._get("/api/cross-validate", **params)

    def debate(self, birth_date: str, birth_time: str, location: str = "北京", gender: str = "男",
               topic: str = "") -> dict:
        """108人物辩论"""
        return self._get("/api/debate",
                         birth=f"{birth_date} {birth_time}",
                         location=location,
                         gender=gender,
                         topic=topic)

    def figures(self) -> List[dict]:
        """108人物列表"""
        return self._get("/api/figures")

    def wise(self, question: str, birth_date: str, birth_time: str, location: str = "北京", gender: str = "男") -> dict:
        """玄照 wisdom API - 一针见血的答案"""
        return self._get("/api/ask",
                         q=question,
                         birth=f"{birth_date} {birth_time}",
                         location=location,
                         gender=gender)

    # === 高阶 API: 主动守护 ===

    def advise(self, chart_result: dict, question: str = None) -> Dict[str, str]:
        """从排盘结果提取 actionable advice"""
        bazi = chart_result.get("bazi", {})
        advice = {}

        # 来自评分系统的 advice
        score = self.score(bazi.get('original_birth', ''), '', location=bazi.get('location', ''), gender=bazi.get('gender', '男'))
        for item in score.get("details", []):
            advice[item["title"]] = item.get("advice", "")

        if question:
            advice["用户提问"] = self.wise(question, '', '', '', '')
        return advice

    def watch(self, birth_date: str, birth_time: str, location: str = "北京", gender: str = "男",
              on_event: callable = None) -> None:
        """
        主动守护模式 - 持续监控命盘变化
        on_event: 回调函数,接 (event_type, message)
        """
        import time
        from datetime import datetime
        last_known_year = datetime.now().year

        while True:
            now = datetime.now()
            # 每年大运换运,主动通知
            if now.year != last_known_year:
                last_known_year = now.year
                result = self.chart(birth_date, birth_time, location, gender)
                msg = f"🔄 新年 {now.year} 已到,你的流年运势:"
                msg += f"\n大运:{result.get('bazi', {}).get('dayun', [{}])[0].get('ganzhi', '?')}"
                if on_event:
                    on_event("year_change", msg)

            # 每月初一通知
            if now.day == 1:
                if on_event:
                    on_event("month_start", f"📅 {now.year}-{now.month:02d} 新月开始,本月运势详情可调用 armor.chart()")

            time.sleep(3600)  # 1小时检查一次


# === 快速使用 ===
if __name__ == "__main__":
    armor = XuanzhaoArmor()
    print("=== 玄照装甲 v1.0 ===")
    print(f"可用API: chart, score, cross_validate, debate, figures, wise, advise, watch")
    print()
    result = armor.chart("2005-06-09", "11:50", "呼和浩特", "男")
    print(f"八字: {result.get('bazi', {}).get('year', '')} "
          f"{result.get('bazi', {}).get('month', '')} "
          f"{result.get('bazi', {}).get('day', '')} "
          f"{result.get('bazi', {}).get('time', '')}")
    print(f"紫微命宫: {result.get('ziwei', {}).get('ming_gong', '')}")
    print(f"占星太阳: {result.get('astro', {}).get('sun_sign', '')}")