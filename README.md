# 玄照 · XuanZhao

> 玄学为体，照见为用。

八术排盘 × 交叉验证 × 108视角群体智能 × 溟玄审判者

## 一键启动

```bash
git clone https://github.com/kaliwuang/xuanzhao-v2.git
cd xuanzhao-v2
pip install -r requirements.txt
python run.py
```

打开 http://localhost:8000 即可使用。

## 功能

### 八术排盘
- **八字** — 四柱、十神、纳音、空亡、长生十二宫、调候用神（完整逐月表）、神煞45种、大运流年
- **紫微斗数** — 十二宫、主星辅星杂耀、四化飞星、大限流年、博士十二神、自化
- **西洋占星** — 十大行星（含逆行）、南北交点、传统+现代宫主星双体系、相位、宫位
- **六爻纳甲** — 本卦变卦、动爻、六亲六兽、纳甲干支
- **奇门遁甲** — 阳遁/阴遁、八门九星八神（阴遁逆排）、甲干隐遁、格局检测
- **大六壬** — 四课三传、十二天将、月将
- **太乙神数** — 十六宫间、主客算、阴阳遁
- **姓名学** — 五格剖象、81数理、三才配置

### 真太阳时
所有引擎均使用真太阳时排盘。经度修正 + 均时差修正 + 夏令时回退 + 早晚子时判定。内置500+城市经纬度。

### 108视角群体智能
每个视角有独立 Soul（基于著作的灵魂定义）、思维模型、推理风格。涵盖中国哲学、玄学命理、西方哲学、心理学、科学创新、商业领导力等领域。

### 溟玄审判者
辩论台第109人。以断言式短句、五行万物类象审查辩论结论，不符合即改写。

### 交叉验证
多术法比对，找出共识和冲突，计算置信度。

## 技术栈

- Python 3.10+ / FastAPI / Uvicorn
- 纯 HTML/CSS/JS 前端（无框架依赖）
- lunar-python（八字/紫微基础库）
- iztro-py（紫微斗数排盘）
- swisseph（占星星历表）
- najia（六爻纳甲）
- kinliuren（大六壬）
- kintaiyi（太乙神数）
- LLM API（可选，离线时自动回退规则引擎）

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/chart` | 八术排盘（八字+紫微+占星+六爻+奇门+六壬+太乙+姓名） |
| `GET /api/chart?format=sse` | SSE流式排盘 |
| `GET /api/cross-validate` | 交叉验证 |
| `GET /api/perspectives` | 108视角分析 |
| `GET /api/figures` | 人物列表 |
| `GET /api/debate` | 辩论（串行审判） |
| `GET /api/debate?stream=true` | 辩论SSE流式 |
| `GET /api/ask` | 命理问答 |
| `GET /api/xuanzhao` | 玄照综合视角 |
| `GET /api/health` | 健康检查 |

## 排盘参数

```
GET /api/chart?birth=2005-06-09+11:50&location=呼和浩特&gender=男&name=侯惠斌
```

| 参数 | 说明 |
|------|------|
| birth | 出生时间（支持多种格式） |
| location | 出生地（500+城市） |
| gender | 性别（男/女） |
| name | 姓名（姓名学用） |

## 项目结构

```
xuanzhao/
├── engine/              # 排盘引擎
│   ├── bazi_engine.py   # 八字
│   ├── ziwei_engine.py  # 紫微斗数
│   ├── astro_engine.py  # 占星
│   ├── liuyao_engine.py # 六爻
│   ├── qimen_engine.py  # 奇门遁甲
│   ├── liuren_engine.py # 大六壬
│   ├── taiyi_engine.py  # 太乙神数
│   ├── xingming_engine.py # 姓名学
│   ├── time_engine.py   # 真太阳时修正
│   ├── debate_engine.py # 辩论引擎
│   ├── perspective_engine.py # 视角引擎
│   ├── mingxuan_observer.py # 溟玄审判者
│   ├── cross_validator.py # 交叉验证
│   └── llm_client.py    # LLM客户端
├── frontend/            # 前端
│   ├── index.html       # 排盘页
│   ├── chart.html       # 排盘结果页
│   ├── debate.html      # 辩论台
│   └── perspectives.html # 视角页
├── data/                # 数据文件
│   ├── cities.json      # 城市经纬度
│   ├── tiaohou.json     # 调候用神表
│   ├── shensha.json     # 神煞表（45种）
│   └── ziwei/           # 紫微数据
├── api/routes.py        # API路由
├── main.py              # 启动入口
└── config.py            # 配置
```

## 许可

MIT License
