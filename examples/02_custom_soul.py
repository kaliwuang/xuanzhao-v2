"""
示例2：自定义灵魂 — 只保留你需要的视角

场景：你只想用传统中国玄学的视角，不要西方神秘学
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shell import XuanzhaoShell, Soul


# === 方法1：从默认灵魂筛选 ===
shell = XuanzhaoShell()

# 只保留中国玄学类
soul = Soul.default().subset(category="中国玄学")
shell.load_soul(soul)
print(f"中国玄学视角: {soul.count}个")

# 只保留特定人物
soul2 = Soul.default().subset(ids=["zhuge-liang", "gui-gu-zi", "liu-bo-wen"])
shell.load_soul(soul2)
print(f"指定人物: {soul2.count}个")
for f in soul2.list_figures():
    print(f"  {f['name']}({f['title']})")


# === 方法2：完全自定义灵魂 ===
my_soul = Soul.minimal([
    {
        "id": "my-master",
        "name": "我的大师",
        "title": "自定义玄学导师",
        "category": "自定义",
        "faction": "综合",
        "expertise": ["八字", "奇门"],
        "primary_method": "八字",
        "thinking_model": {
            "name": "我的思维模型",
            "principles": ["以事实为依据", "不夸大"],
            "steps": ["看日主", "看旺衰", "看喜忌"],
            "key_concepts": {"用神": "最需要的五行"},
        },
        "catchphrase": "命由己造",
        "bio": "一个务实的玄学分析者",
    }
])
shell.load_soul(my_soul)
print(f"\n自定义灵魂: {my_soul.count}个")


# === 方法3：合并灵魂 ===
default_soul = Soul.default()
my_extra = Soul.minimal([{
    "id": "custom-1",
    "name": "自定义视角",
    "title": "额外视角",
    "category": "自定义",
    "faction": "综合",
    "expertise": ["综合"],
    "primary_method": "八字",
    "thinking_model": {},
    "catchphrase": "",
    "bio": "",
}])

# 合并：默认108个 + 自定义1个 = 109个
merged = default_soul.merge(my_extra)
print(f"\n合并后: {merged.count}个")
