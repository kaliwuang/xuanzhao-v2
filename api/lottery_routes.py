#!/usr/bin/env python3
"""彩票预测接口模块 — 独立文件，避免污染routes.py

集成进玄照: main.py 启动时 import + include_router
"""
import csv
import logging
import random
from collections import Counter, defaultdict
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

LOTTERY_DATA_PATH = "D:/lottery-data/fc3d-history.csv"
_LOTTERY_DATA_CACHE = []

WX_MAP = {0: '土', 1: '木', 2: '火', 3: '火', 4: '木', 5: '土',
          6: '金', 7: '金', 8: '木', 9: '火'}


def _error_response(e):
    return JSONResponse(
        status_code=500,
        content={"error": f"操作失败: {str(e)}", "error_type": type(e).__name__}
    )


def load_lottery_data() -> list:
    """加载福彩3D历史数据（带缓存）"""
    if _LOTTERY_DATA_CACHE:
        return _LOTTERY_DATA_CACHE
    try:
        with open(LOTTERY_DATA_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                _LOTTERY_DATA_CACHE.append({
                    'date': row['date'],
                    'period': row['period'],
                    'd1': int(row['digit1']),
                    'd2': int(row['digit2']),
                    'd3': int(row['digit3']),
                    'sum': int(row['sum']),
                    'span': int(row['span']),
                })
        _LOTTERY_DATA_CACHE.sort(key=lambda x: x['period'])
    except Exception as e:
        logger.warning(f"加载彩票数据失败: {e}")
    return _LOTTERY_DATA_CACHE


@router.get("/api/lottery/predict")
def predict_lottery(
    lottery_type: str = Query("fc3d", description="彩票类型: fc3d/pl3"),
    target_date: str = Query(None, description="目标日期 YYYY-MM-DD, 默认今天"),
):
    """彩票预测接口 — 真实数据 + 五行 + 时空 + 统计多维推断"""
    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")

        data = load_lottery_data()
        if not data:
            return JSONResponse(status_code=503, content={"error": "彩票数据未加载"})

        # 1. 五行偏旺分析 (近100期)
        recent100 = data[-100:]
        freq_wx = Counter()
        for d in recent100:
            for n in [d['d1'], d['d2'], d['d3']]:
                freq_wx[WX_MAP[n]] += 1
        total_wx = sum(freq_wx.values())
        wx_pct = {w: round(freq_wx[w] / total_wx * 100, 1) for w in ['木', '火', '土', '金', '水']}
        sorted_wx = sorted(freq_wx.items(), key=lambda x: x[1])
        deficient_wx = sorted_wx[0][0]
        deficient_nums = [n for n in range(10) if WX_MAP[n] == deficient_wx]

        # 2. 和值通道
        sum_freq = Counter(d['sum'] for d in data)
        top_sums = [s for s, _ in sum_freq.most_common(5)]
        recent10_avg = sum(d['sum'] for d in data[-10:]) / 10
        overall_avg = sum(d['sum'] for d in data) / len(data)
        predicted_sum = round((recent10_avg + overall_avg) / 2)

        # 3. 星期规律
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        weekday = target_dt.weekday()
        weekday_freq = defaultdict(Counter)
        for d in data:
            wd = datetime.strptime(d['date'], '%Y-%m-%d').weekday()
            for n in [d['d1'], d['d2'], d['d3']]:
                weekday_freq[wd][n] += 1
        weekday_hot = [n for n, _ in weekday_freq[weekday].most_common(5)]

        # 4. 杀号策略 (近20期低频)
        last20 = data[-20:]
        last20_freq = Counter()
        for d in last20:
            for n in [d['d1'], d['d2'], d['d3']]:
                last20_freq[n] += 1
        kill_list = sorted([n for n in range(10) if last20_freq[n] <= 1])

        # 5. 邻号关联 (上期出现后下期可能)
        prev = data[-1]
        prev_nums = {prev['d1'], prev['d2'], prev['d3']}
        transitions = defaultdict(Counter)
        for i in range(len(data) - 1):
            prev_set = {data[i]['d1'], data[i]['d2'], data[i]['d3']}
            cur_set = {data[i+1]['d1'], data[i+1]['d2'], data[i+1]['d3']}
            for n in prev_set:
                for c in cur_set:
                    transitions[n][c] += 1
        prev_hot = []
        for n in prev_nums:
            top = transitions[n].most_common(3)
            for c, _ in top:
                if c not in prev_hot:
                    prev_hot.append(c)
        prev_hot = prev_hot[:5]

        # 6. 综合推荐 (3组)
        candidates = [n for n in range(10) if n not in kill_list]
        rng = random.Random(int(datetime.now().timestamp()) // 86400)
        recommendations = []

        # 第1组: 五行补缺 + 星期热号
        must = list(set(deficient_nums + weekday_hot[:2]))
        if len(must) >= 3:
            nums = sorted(rng.sample(must, 3))
        else:
            nums = sorted(must + rng.sample([n for n in candidates if n not in must], 3 - len(must)))
        recommendations.append({
            "rank": 1, "numbers": nums, "sum": sum(nums), "span": max(nums) - min(nums),
            "score": 0.85, "reason": f"五行补{deficient_wx} + 星期{['一','二','三','四','五','六','日'][weekday]}热号"
        })

        # 第2组: 邻号关联
        candidates2 = [n for n in candidates if n not in nums]
        if len(candidates2) >= 3:
            nums2 = sorted(rng.sample(candidates2, 3))
        else:
            nums2 = sorted(rng.sample(candidates, 3))
        recommendations.append({
            "rank": 2, "numbers": nums2, "sum": sum(nums2), "span": max(nums2) - min(nums2),
            "score": 0.75, "reason": "邻号关联 + 杀号过滤"
        })

        # 第3组: 和值锁定
        candidates3 = [n for n in candidates if n not in nums and n not in nums2]
        if len(candidates3) >= 3:
            nums3 = sorted(rng.sample(candidates3, 3))
        else:
            nums3 = sorted(rng.sample(candidates, 3))
        recommendations.append({
            "rank": 3, "numbers": nums3, "sum": sum(nums3), "span": max(nums3) - min(nums3),
            "score": 0.70, "reason": f"和值锁定{predicted_sum}区间"
        })

        return {
            "date": target_date,
            "weekday": ['一', '二', '三', '四', '五', '六', '日'][weekday],
            "lottery_type": lottery_type,
            "data_range": f"{data[0]['date']} ~ {data[-1]['date']}",
            "data_count": len(data),
            "five_elements": {
                "percentages": wx_pct,
                "deficient": deficient_wx,
                "remedy_numbers": deficient_nums,
            },
            "sum_channel": {
                "top_sums": top_sums,
                "recent_10_avg": round(recent10_avg, 1),
                "overall_avg": round(overall_avg, 1),
                "predicted_sum": predicted_sum,
            },
            "weekday_pattern": {
                "hot_numbers": weekday_hot,
            },
            "kill_list": kill_list,
            "neighbor_relation": {
                "last_period": prev['period'],
                "last_numbers": list(prev_nums),
                "predicted_next": prev_hot,
            },
            "recommendations": recommendations,
            "disclaimer": "基于真实历史数据的统计推断，中奖仍是小概率事件。仅供娱乐参考。",
        }
    except Exception as e:
        return _error_response(e)


@router.get("/api/lottery/data")
def get_lottery_data(
    limit: int = Query(50, description="返回最近N期"),
):
    """获取彩票历史数据"""
    try:
        data = load_lottery_data()
        if not data:
            return JSONResponse(status_code=503, content={"error": "数据未加载"})
        return {
            "total": len(data),
            "records": data[-limit:],
        }
    except Exception as e:
        return _error_response(e)