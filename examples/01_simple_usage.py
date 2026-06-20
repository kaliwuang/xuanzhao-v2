"""
示例1：最简用法 — 一行代码排盘

任何agent只要会import就能用，不需要懂玄学。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shell import quick_paipan, quick_analyze


# === 1. 纯排盘（不调LLM，零成本） ===
print("=== 排盘 ===")
result = quick_paipan("2005-06-09 12:00", "呼和浩特", "男")

print(f"八字: {result.get('bazi', {})}")
print(f"紫微: {result.get('ziwei', {})}")
print(f"奇门: {result.get('qimen', {})}")


# === 2. 完整预测（需要LLM配置） ===
# result = quick_analyze(
#     birth="2005-06-09 12:00",
#     location="呼和浩特",
#     gender="男",
#     question="事业如何",
#     llm_config={
#         "api_key": "your-api-key",
#         "base_url": "https://your-llm-endpoint.com/v1",
#         "model": "your-model",
#     }
# )
# print(result)
