# 玄照 v2.0

七术排盘 × 交叉验证 × 108视角群体智能

## 一键启动

```bash
git clone https://github.com/kaliwuang/xuanzhao-v2.git
cd xuanzhao-v2
python run.py
```

打开 http://localhost:8000 即可使用。无需任何额外配置。

Windows 用户也可以双击 `start.bat`。

## 功能

- 七术排盘：八字、紫微斗数、西洋占星、六爻、奇门遁甲、大六壬、太乙神数
- 交叉验证：多术法比对，找出共识和冲突，计算置信度
- 108视角：每人有Soul（基于著作的灵魂定义）、思维模型、推理风格、代表性著作
- 群体辩论：多个视角围绕一个问题展开辩论，最终给出玄照综合视角
- 命理问答：针对具体问题给出多术法交叉分析

## 技术栈

- Python 3.10+ / FastAPI / Uvicorn
- 纯 HTML/CSS/JS 前端（无框架依赖）
- LLM API（可选，离线时自动回退规则引擎）

## API 端点

- GET /api/chart - 七术排盘
- GET /api/cross-validate - 交叉验证
- GET /api/perspectives - 108视角（含Soul）
- GET /api/figures - 人物列表
- GET /api/debate - 辩论
- GET /api/ask - 命理问答
- GET /api/xuanzhao - 玄照综合视角
