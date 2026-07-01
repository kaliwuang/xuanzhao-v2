#!/usr/bin/env python3
"""彩票预测接口模块 — 独立文件，避免污染routes.py

支持: fc3d / pl3 / ssq / dlt
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

LOTTERY_DATA_PATHS = {
    "fc3d": "D:/lottery-data/fc3d-history.csv",
    "pl3": "D:/lottery-data/pl3-history.csv",
    "dlt": "D:/lottery-data/dlt-history.csv",
    "ssq": "D:/lottery-data/ssq-history.csv",
}
_LOTTERY_DATA_CACHE = {}
_COLUMNS = {
    "fc3d": ["date", "period", "digit1", "digit2", "digit3", "sum", "span"],
    "pl3": ["date", "period", "digit1", "digit2", "digit3", "sum", "span"],
    "dlt": ["date", "period", "f1", "f2", "f3", "f4", "f5", "b1", "b2"],
    "ssq": ["date", "period", "red1", "red2", "red3", "red4", "red5", "red6", "blue"],
}

_LOTTERY_BALLS = {
    "fc3d": {"type": "3d", "main_range": (0, 10), "count": 3},
    "pl3": {"type": "3d", "main_range": (0, 10), "count": 3},
    "dlt": {"type": "lotto", "front_range": (1, 35), "front_count": 5, "back_range": (1, 12), "back_count": 2},
    "ssq": {"type": "lotto", "front_range": (1, 33), "front_count": 6, "back_range": (1, 16), "back_count": 1},
}

WX_MAP = {0: '土', 1: '木', 2: '火', 3: '火', 4: '木', 5: '土',
          6: '金', 7: '金', 8: '木', 9: '火'}

# 完整1-35的五行映射 (用于大乐透/双色球)
# 1-9按先天数, 10以后每10循环 (尾数决定五行)
WX_FULL = {}
for n in range(1, 36):
    base = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    wx_for_9 = ['木', '火', '火', '木', '土', '金', '金', '木', '火']
    base_map = {b: w for b, w in zip(base, wx_for_9)}
    WX_FULL[n] = base_map.get(n if n <= 9 else ((n - 1) % 9) + 1, '土')


def _error_response(e):
    return JSONResponse(
        status_code=500,
        content={"error": f"操作失败: {str(e)}", "error_type": type(e).__name__}
    )


def _get_main_numbers(item, lottery_type):
    if lottery_type in ('fc3d', 'pl3'):
        return [item.get(f'digit{i}', 0) for i in range(1, 4)]
    elif lottery_type == 'dlt':
        return [item.get(f'f{i}', 0) for i in range(1, 6)]
    elif lottery_type == 'ssq':
        return [item.get(f'red{i}', 0) for i in range(1, 7)]
    return []


def load_lottery_data(lottery_type='fc3d'):
    if lottery_type in _LOTTERY_DATA_CACHE:
        return _LOTTERY_DATA_CACHE[lottery_type]
    path = LOTTERY_DATA_PATHS.get(lottery_type)
    if not path:
        return []
    cache = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            cols = _COLUMNS.get(lottery_type, [])
            for row in reader:
                item = {'date': row.get('date', ''), 'period': row.get('period', '')}
                for col in cols:
                    if col in row and col not in ('date', 'period'):
                        try:
                            item[col] = int(row[col])
                        except (ValueError, TypeError):
                            item[col] = 0
                if lottery_type in ('fc3d', 'pl3'):
                    digits = [item.get(f'digit{i}', 0) for i in range(1, 4)]
                    item['sum'] = sum(digits)
                    item['span'] = max(digits) - min(digits) if digits else 0
                elif lottery_type == 'dlt':
                    front = [item.get(f'f{i}', 0) for i in range(1, 6)]
                    item['sum'] = sum(front)
                    item['span'] = max(front) - min(front) if front else 0
                elif lottery_type == 'ssq':
                    front = [item.get(f'red{i}', 0) for i in range(1, 7)]
                    item['sum'] = sum(front)
                    item['span'] = max(front) - min(front) if front else 0
                cache.append(item)
        cache.sort(key=lambda x: x['period'])
        _LOTTERY_DATA_CACHE[lottery_type] = cache
    except Exception as e:
        logger.warning(f"加载{lottery_type}数据失败: {e}")
    return cache


def _analyze_lottery(data, lottery_type):
    if not data:
        return {}
    cfg = _LOTTERY_BALLS[lottery_type]

    freq_wx = Counter()
    wx_table = WX_MAP if cfg['type'] == '3d' else WX_FULL
    for d in data:
        for n in _get_main_numbers(d, lottery_type):
            freq_wx[wx_table.get(n, '土')] += 1
    total_wx = sum(freq_wx.values()) or 1
    wx_pct = {w: round(freq_wx[w] / total_wx * 100, 1) for w in ['木', '火', '土', '金', '水']}
    sorted_wx = sorted(freq_wx.items(), key=lambda x: x[1])
    deficient_wx = sorted_wx[0][0] if sorted_wx else ''
    if cfg['type'] == '3d':
        candidate_range_start = cfg['main_range'][0]
        candidate_range_end = cfg['main_range'][1] - 1  # 0-9,不含10
        deficient_range_start = cfg['main_range'][0]
        deficient_range_end = cfg['main_range'][1] - 1
    else:
        candidate_range_start = cfg['front_range'][0]
        candidate_range_end = cfg['front_range'][1]
        deficient_range_start = cfg['front_range'][0]
        deficient_range_end = cfg['front_range'][1]
    main_max = candidate_range_end
    deficient_nums = sorted([n for n in range(deficient_range_start, deficient_range_end + 1) if wx_table.get(n) == deficient_wx])

    sum_freq = Counter(d.get('sum', 0) for d in data)
    top_sums = [s for s, _ in sum_freq.most_common(5)]
    recent10_avg = sum(d.get('sum', 0) for d in data[-10:]) / 10
    overall_avg = sum(d.get('sum', 0) for d in data) / len(data)

    weekday = datetime.now().weekday()
    weekday_freq = defaultdict(Counter)
    for d in data:
        try:
            wd = datetime.strptime(d['date'], '%Y-%m-%d').weekday()
        except:
            continue
        for n in _get_main_numbers(d, lottery_type):
            weekday_freq[wd][n] += 1
    weekday_hot = [n for n, _ in weekday_freq[weekday].most_common(8)]

    last20 = data[-20:]
    last20_freq = Counter()
    for d in last20:
        for n in _get_main_numbers(d, lottery_type):
            last20_freq[n] += 1
    kill_list = sorted([n for n in range(candidate_range_start, candidate_range_end + 1)
                        if last20_freq[n] <= 1])

    prev = data[-1]
    prev_nums = set(_get_main_numbers(prev, lottery_type))
    transitions = defaultdict(Counter)
    for i in range(len(data) - 1):
        prev_set = set(_get_main_numbers(data[i], lottery_type))
        cur_set = set(_get_main_numbers(data[i + 1], lottery_type))
        for n in prev_set:
            for c in cur_set:
                transitions[n][c] += 1
    prev_hot = []
    for n in prev_nums:
        top = transitions[n].most_common(5)
        for c, _ in top:
            if c not in prev_hot:
                prev_hot.append(c)
    prev_hot = prev_hot[:8]

    return {
        'five_elements': {
            'percentages': wx_pct,
            'deficient': deficient_wx,
            'remedy_numbers': deficient_nums,
        },
        'sum_channel': {
            'top_sums': top_sums,
            'recent_10_avg': round(recent10_avg, 1),
            'overall_avg': round(overall_avg, 1),
        },
        'weekday_pattern': {'hot_numbers': weekday_hot, 'target_weekday': weekday},
        'kill_list': kill_list,
        'neighbor_relation': {
            'last_period': prev.get('period', ''),
            'last_numbers': sorted(list(prev_nums)),
            'predicted_next': prev_hot,
        },
    }


def _build_recommendations(data, analysis, lottery_type):
    cfg = _LOTTERY_BALLS[lottery_type]
    kill_list = analysis.get('kill_list', [])
    rng = random.Random(int(datetime.now().timestamp()) // 86400)
    recommendations = []
    weekday_names = ['一', '二', '三', '四', '五', '六', '日']

    if lottery_type in ('fc3d', 'pl3'):
        # 3D范围是0-9（不包含10）
        candidates = [n for n in range(0, 10) if n not in kill_list]
        must = list(set(analysis['five_elements']['remedy_numbers'] + analysis['weekday_pattern']['hot_numbers'][:2]))
        must = [n for n in must if n in candidates]
        if len(must) >= 3:
            nums = sorted(rng.sample(must, 3))
        else:
            needed = 3 - len(must)
            more = [n for n in candidates if n not in must]
            nums = sorted(must + rng.sample(more, min(needed, len(more))))
        recommendations.append({
            'rank': 1, 'numbers': nums, 'sum': sum(nums), 'span': max(nums) - min(nums),
            'score': 0.85, 'reason': f"五行补{analysis['five_elements']['deficient']} + 星期{weekday_names[analysis['weekday_pattern']['target_weekday']]}热号"
        })
        cand2 = [n for n in candidates if n not in nums]
        nums2 = sorted(rng.sample(cand2 if len(cand2) >= 3 else candidates, 3))
        recommendations.append({
            'rank': 2, 'numbers': nums2, 'sum': sum(nums2), 'span': max(nums2) - min(nums2),
            'score': 0.75, 'reason': '邻号关联 + 杀号过滤'
        })
        cand3 = [n for n in candidates if n not in nums and n not in nums2]
        nums3 = sorted(rng.sample(cand3 if len(cand3) >= 3 else candidates, 3))
        target_sum = round((analysis['sum_channel']['recent_10_avg'] + analysis['sum_channel']['overall_avg']) / 2)
        recommendations.append({
            'rank': 3, 'numbers': nums3, 'sum': sum(nums3), 'span': max(nums3) - min(nums3),
            'score': 0.70, 'reason': f"和值锁定{target_sum}区间"
        })
    else:
        front_count = cfg['front_count']
        back_count = cfg['back_count']
        front_range = cfg['front_range']
        back_range = cfg['back_range']
        front_candidates = [n for n in range(front_range[0], front_range[1] + 1) if n not in kill_list]
        back_candidates = list(range(back_range[0], back_range[1] + 1))
        must = list(set(analysis['five_elements']['remedy_numbers'] + analysis['weekday_pattern']['hot_numbers'][:3]))
        must = [n for n in must if n in front_candidates]
        if len(must) >= front_count:
            front = sorted(rng.sample(must, front_count))
        else:
            needed = front_count - len(must)
            more = [n for n in front_candidates if n not in must]
            front = sorted(must + rng.sample(more, min(needed, len(more))))
        back = sorted(rng.sample(back_candidates, back_count))
        recommendations.append({
            'rank': 1, 'numbers': front + back, 'front': front, 'back': back,
            'sum': sum(front), 'span': max(front) - min(front),
            'score': 0.85, 'reason': f"五行补{analysis['five_elements']['deficient']} + 星期{weekday_names[analysis['weekday_pattern']['target_weekday']]}热号"
        })
        prev_hot = analysis['neighbor_relation']['predicted_next'][:front_count]
        front2 = sorted([n for n in prev_hot if n in front_candidates and n not in front])[:front_count]
        if len(front2) < front_count:
            back_fill = [n for n in front_candidates if n not in front]
            front2 = sorted(back_fill[:front_count])
        back2 = sorted(rng.sample(back_candidates, back_count))
        recommendations.append({
            'rank': 2, 'numbers': front2 + back2, 'front': front2, 'back': back2,
            'sum': sum(front2), 'span': max(front2) - min(front2),
            'score': 0.75, 'reason': '邻号关联 + 杀号过滤'
        })
        target_sum = round((analysis['sum_channel']['recent_10_avg'] + analysis['sum_channel']['overall_avg']) / 2)
        candidates3 = [n for n in front_candidates if n not in front and n not in front2]
        if len(candidates3) >= front_count:
            front3 = sorted(rng.sample(candidates3, front_count))
            attempts = 0
            while abs(sum(front3) - target_sum) > 5 and attempts < 8:
                front3 = sorted(rng.sample(candidates3, front_count))
                attempts += 1
        else:
            front3 = sorted(rng.sample(front_candidates, front_count))
        back3 = sorted(rng.sample(back_candidates, back_count))
        recommendations.append({
            'rank': 3, 'numbers': front3 + back3, 'front': front3, 'back': back3,
            'sum': sum(front3), 'span': max(front3) - min(front3),
            'score': 0.70, 'reason': f"和值锁定{target_sum}区间"
        })

    return recommendations


@router.get("/api/lottery/predict")
def predict_lottery(
    lottery_type: str = Query("fc3d", description="彩票类型: fc3d/pl3/ssq/dlt"),
    target_date: str = Query(None, description="目标日期 YYYY-MM-DD, 默认今天"),
):
    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        lottery_type = lottery_type.lower()
        if lottery_type not in _LOTTERY_BALLS:
            return JSONResponse(status_code=400, content={"error": f"不支持的彩票类型: {lottery_type}"})
        data = load_lottery_data(lottery_type)
        if not data:
            return JSONResponse(status_code=503, content={"error": f"{lottery_type}数据未加载"})
        analysis = _analyze_lottery(data, lottery_type)
        recommendations = _build_recommendations(data, analysis, lottery_type)
        weekday_names = ['一', '二', '三', '四', '五', '六', '日']
        return {
            "date": target_date,
            "weekday": weekday_names[analysis['weekday_pattern']['target_weekday']],
            "lottery_type": lottery_type,
            "data_range": f"{data[0]['date']} ~ {data[-1]['date']}",
            "data_count": len(data),
            "five_elements": analysis['five_elements'],
            "sum_channel": analysis['sum_channel'],
            "weekday_pattern": analysis['weekday_pattern'],
            "kill_list": analysis['kill_list'],
            "neighbor_relation": analysis['neighbor_relation'],
            "recommendations": recommendations,
            "disclaimer": "基于真实历史数据的统计推断，中奖仍是小概率事件。仅供娱乐参考。",
        }
    except Exception as e:
        return _error_response(e)


@router.get("/api/lottery/data")
def get_lottery_data(
    lottery_type: str = Query("fc3d", description="彩票类型"),
    limit: int = Query(50, description="返回最近N期"),
):
    try:
        data = load_lottery_data(lottery_type)
        if not data:
            return JSONResponse(status_code=503, content={"error": "数据未加载"})
        return {
            "lottery_type": lottery_type,
            "total": len(data),
            "records": data[-limit:],
        }
    except Exception as e:
        return _error_response(e)