# 玄照装甲壳子 (XuanzhaoShell)

**任何AI agent装载进去，都能当玄学大师。**

## 快速开始

### 1. 一行代码排盘

```python
from shell import quick_paipan

result = quick_paipan("2005-06-09 11:50", "呼和浩特", "男")
print(result['bazi'])  # 八字数据
print(result['qimen']) # 奇门数据
```

### 2. 完整预测（需要LLM）

```python
from shell import quick_analyze

result = quick_analyze(
    birth="2005-06-09 11:50",
    location="呼和浩特",
    gender="男",
    question="事业如何",
    llm_config={
        "api_key": "your-api-key",
        "base_url": "https://your-llm.com/v1",
        "model": "your-model",
    }
)
```

### 3. 自定义灵魂

```python
from shell import XuanzhaoShell, Soul

# 只保留中国玄学视角
soul = Soul.default().subset(category="中国玄学")

# 或者完全自定义
my_soul = Soul.minimal([{
    "id": "my-master",
    "name": "我的大师",
    "title": "自定义玄学导师",
    "expertise": ["八字", "奇门"],
    "primary_method": "八字",
    "catchphrase": "命由己造",
}])

shell = XuanzhaoShell()
shell.load_soul(my_soul)
```

### 4. 自定义Agent接入

```python
from shell import XuanzhaoShell, AnalysisContext, Thought

class MyAgent:
    def think(self, context: AnalysisContext) -> Thought:
        # 接收排盘数据，返回你的分析
        bazi = context.bazi
        day_master = bazi.get('day_master', {})
        wuxing = day_master.get('wuxing', '')
        
        return Thought(
            figure_id="my-agent",
            stance="支持",
            confidence=0.8,
            reasoning=f"日主{wuxing}，...",
            key_points=[f"日主{wuxing}"],
        )
    
    def speak(self, opinion) -> str:
        # 以你的风格表达观点
        return f"我的分析：{opinion.thought.reasoning}"
    
    def judge(self, opinions) -> dict:
        # 综合所有意见，给出最终判断
        return {"conclusion": "综合判断..."}

# 使用
agent = MyAgent()
shell = XuanzhaoShell()
shell.mount(agent)

ctx = shell.analyze("2005-06-09 11:50", "呼和浩特", "男")
thought = agent.think(ctx)
```

## 架构

```
XuanzhaoShell（装甲壳子）
├── Soul（灵魂配置层）
│   ├── figures.json（108视角定义）
│   └── 自定义灵魂（YAML/JSON）
├── AgentAdapter（标准接口）
│   ├── think() — 思考
│   ├── speak() — 发言
│   └── judge() — 裁决
└── 引擎层（七术排盘）
    ├── BaziEngine（八字）
    ├── ZiWeiEngine（紫微）
    ├── QiMenEngine（奇门）
    ├── LiuRenEngine（六壬）
    ├── TaiYiEngine（太乙）
    ├── LiuYaoEngine（六爻）
    └── AstroEngine（占星）
```

## 核心概念

### Soul（灵魂）
定义"谁在说话"。可以是108视角的默认配置，也可以是完全自定义的人物。

### Agent（代理）
定义"怎么思考"。任何AI只要实现think/speak/judge三个方法就能接入。

### Shell（壳子）
统一入口。封装七术排盘、视角推理、交叉验证、辩论流程。

## 示例

- `examples/01_simple_usage.py` — 最简用法
- `examples/02_custom_soul.py` — 自定义灵魂
- `examples/03_custom_agent.py` — 自定义Agent接入

## 依赖

- Python 3.8+
- 玄照v2引擎（engine/目录）
- 可选：LLM API（用于视角推理和辩论）
