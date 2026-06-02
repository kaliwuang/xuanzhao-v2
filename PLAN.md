# 玄照 v2.0 实施计划

## 项目定位
专业级多玄术命理分析系统：三术排盘（八字+紫微+占星）+ 交叉验证 + 人物-术法绑定辩论

---

## 技术选型

| 层级 | 技术 |
|------|------|
| 后端框架 | Python FastAPI |
| 前端 | 纯 HTML/CSS/JS（不引入React，减少复杂度） |
| 数据库 | SQLite（轻量，单机部署） |
| 排盘引擎 | lunar-python（八字）+ pyswisseph（占星）+ 自研紫微 |
| LLM | Claude API（视角推理） |
| 部署 | 单机运行，python main.py 启动 |

---

## 项目结构

```
xuanzhao-v2/
├── main.py                 # 入口：启动 FastAPI + 前端
├── config.py               # 全局配置（API Key、路径等）
│
├── engine/                 # 核心引擎层
│   ├── __init__.py
│   ├── time_engine.py      # 时空修正（真太阳时、早晚子时）
│   ├── udm.py              # 统一数据模型
│   ├── base.py             # 术法引擎基类
│   ├── bazi_engine.py      # 八字引擎（封装 lunar-python + 修正）
│   ├── ziwei_engine.py     # 紫微引擎（自研）
│   ├── astro_engine.py     # 占星引擎（封装 pyswisseph）
│   ├── cross_validator.py  # 交叉验证
│   ├── perspective_engine.py # 108视角推理
│   ├── debate_engine.py    # 辩论引擎
│   └── knowledge_base.py   # 玄学泰斗知识库接口
│
├── data/                   # 数据文件
│   ├── cities.json         # 城市经纬度数据库
│   ├── tiaohou.yaml        # 调候用神表
│   ├── shensha.yaml        # 神煞表
│   └── ziwei/              # 紫微星曜数据
│       ├── stars.json      # 主星定义
│       ├── palace_map.json # 十二宫排布规则
│       └── big_limit.json  # 大限规则
│
├── perspectives/           # 108人物定义
│   ├── __init__.py
│   ├── figures.yaml        # 108人物元数据
│   ├── zhuge_liang.yaml    # 诸葛亮：奇门视角
│   ├── ni_haixia.yaml      # 倪海厦：紫微视角
│   ├── yuan_tiangang.yaml  # 袁天罡：八字视角
│   └── ...                 # 其余105人
│
├── knowledge/              # 玄学泰斗知识库索引
│   ├── index.py            # 倒排索引构建
│   └── search.py           # 检索接口
│
├── api/                    # FastAPI 路由
│   ├── __init__.py
│   ├── chart.py            # 排盘接口 /api/chart
│   ├── analyze.py          # 分析接口 /api/analyze
│   ├── debate.py           # 辩论接口 /api/debate
│   └── ask.py              # 问答接口 /api/ask
│
├── frontend/               # 前端界面
│   ├── index.html          # 主页面：输入+排盘展示
│   ├── chart.html          # 命盘可视化页面
│   ├── debate.html         # 辩论台页面
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── chart.js        # 命盘绘制
│       ├── api.js          # API调用封装
│       └── debate.js       # 辩论交互
│
├── tests/                  # 测试
│   ├── test_time_engine.py
│   ├── test_bazi.py
│   ├── test_ziwei.py
│   └── test_cross_validator.py
│
└── requirements.txt
```

---

## 阶段计划

### Stage 1：地基（Day 1-3）

目标：排盘100%准确，项目骨架搭好

**Day 1：时空修正层**
- engine/time_engine.py
  - 解析出生时间（支持多种格式）
  - 城市经纬度查询（内置500+城市）
  - 真太阳时修正（经度+均时差）
  - 早晚子时判定
  - 夏令时回退
- tests/test_time_engine.py
  - 10个边界测试用例（临界时辰、跨节气、晚子时等）

**Day 2：UDM + 八字引擎**
- engine/udm.py：统一数据模型（四柱、藏干、十神、纳音、大运）
- engine/bazi_engine.py
  - 封装 lunar-python
  - 应用 time_engine 修正后的时间
  - 输出完整八字数据到 UDM
- tests/test_bazi.py
  - 20个已知八字验证（对比问真八字/文墨天机）

**Day 3：占星引擎 + API骨架**
- engine/astro_engine.py：封装 pyswisseph
- api/chart.py：/api/chart 接口（返回八字+占星排盘结果）
- frontend/index.html + css/style.css：输入界面
- frontend/chart.html：命盘展示（表格形式，非可视化）

**Stage 1 交付**：
- 输入出生信息 → 输出准确的八字+占星排盘
- Web界面可访问
- 所有排盘结果经过20+测试用例验证

---

### Stage 2：紫微斗数（Day 4-8）

目标：自研紫微斗数排盘引擎，三术齐全

**Day 4-5：紫微排盘核心算法**
- data/ziwei/stars.json：主星定义（14主星+6吉星+6煞星）
- data/ziwei/palace_map.json：十二宫排布规则
- engine/ziwei_engine.py
  - 安命宫：从寅宫起正月，顺数到生月，逆数到生时
  - 安十二宫：从命宫起，逆时针布兄弟、夫妻、子女...
  - 定五行局：根据命宫天干地支定局数
  - 起紫微：根据五行局+生日数安紫微星
  - 安主星：紫微定位后，按固定顺序布其他主星
  - 安辅星：左辅右弼、文昌文曲等
  - 安四化：根据生年天干定禄权科忌
  - 起大限：阳男阴女顺行，阴男阳女逆行

**Day 6：紫微数据模型**
- UDM扩展：紫微十二宫、主星分布、四化、大限
- api/chart.py 扩展：返回紫微排盘结果
- frontend/chart.html 扩展：显示紫微十二宫表格

**Day 7：紫微验证**
- tests/test_ziwei.py
  - 10个已知命盘验证（对比文墨天机/紫微斗数排盘APP）
- 修复排盘差异

**Day 8：三术展示界面**
- frontend/chart.html：三术并排展示
  - 左栏：八字四柱+十神+大运
  - 中栏：紫微十二宫+主星
  - 右栏：占星行星+宫位

**Stage 2 交付**：
- 八字+紫微+占星三术排盘全部准确
- Web界面三术并排展示

---

### Stage 3：交叉验证 + 问答（Day 9-12）

目标：三术结果互相印证，回答用户问题

**Day 9：交叉验证引擎**
- engine/cross_validator.py
  - 五行属性交叉（八字日主 vs 紫微主星 vs 占星太阳星座）
  - 性格特质交叉（三术对性格的判定是否一致）
  - 事业方向交叉
  - 婚姻感情交叉
  - 健康体质交叉
  - 输出：共识列表 + 冲突列表 + 置信度评分
- tests/test_cross_validator.py

**Day 10：问答引擎**
- engine/qa_engine.py
  - 接收用户问题
  - 解析问题类型（事业/感情/健康/财运/性格）
  - 从UDM提取相关数据
  - 用三术交叉验证结果生成回答
  - 标注置信度（高/中/低）
- api/ask.py：/api/ask 接口

**Day 11：问答界面**
- frontend/chart.html 添加问答区域
- 用户输入问题 → 显示三术交叉验证回答
- 显示置信度标签

**Day 12：整合测试**
- 10组真实命盘测试
- 每个命盘问5个标准问题
- 人工判定回答质量

**Stage 3 交付**：
- 输入问题 → 三术交叉验证回答
- 回答带置信度标签
- 共识和冲突清晰展示

---

### Stage 4：人物-术法绑定 + 12核心视角（Day 13-17）

目标：12个核心人物，每人用自己擅长的术法发言

**Day 13：人物定义框架**
- perspectives/figures.yaml：12人物元数据
  - 诸葛亮：奇门遁甲
  - 倪海厦：紫微斗数
  - 袁天罡：八字
  - 李淳风：星象占星
  - 鬼谷子：纵横捭阖（综合分析）
  - 老子：道家自然（无为视角）
  - 孙子：兵家策略（竞争视角）
  - 费曼：科学思维（质疑视角）
  - 荣格：心理分析（阴影视角）
  - 袁天罡：面相骨相（相术视角）
  - 张仲景：医理体质（健康视角）
  - 邵雍：象数推演（数理视角）
- perspectives/zhuge_liang.yaml 等：每个人物的思维模型、术法专长、知识库关联

**Day 14：视角推理引擎**
- engine/perspective_engine.py
  - 读取人物定义
  - 根据人物术法专长，从UDM提取对应数据
  - 构建推理上下文（命盘数据+思维模型+知识库）
  - 调用 Claude API 生成观点
  - 输出：立场+置信度+推理过程+要点

**Day 15：辩论引擎**
- engine/debate_engine.py
  - 观点聚类（相近观点归一组）
  - 冲突检测（找出立场对立的人物）
  - 自动生成交锋（每人用自己的术法数据反驳对方）
  - 共识提取
- api/debate.py：/api/debate 接口

**Day 16：辩论界面**
- frontend/debate.html：辩论台
  - 显示12人物头像/阵营
  - 第一轮：每人独白（用自己的术法分析）
  - 第二轮：交锋（对立观点互相反驳）
  - 第三轮：共识总结
  - 显示每个人物引用的术法数据

**Day 17：整合测试**
- 5组命盘 × 3个问题 × 12人物
- 人工判定：人物是否用了正确的术法？反驳是否有逻辑？

**Stage 4 交付**：
- 12人物按术法专长发言
- 辩论台可视化展示
- 每人发言引用具体的术法数据

---

### Stage 5：知识库整合 + 质量提升（Day 18-21）

目标：接入玄学泰斗知识库，提升内容深度

**Day 18：知识库索引**
- knowledge/index.py
  - 读取玄学泰斗 _full_v7.md 文件
  - 按命盘特征（日主、格局、冲合等）建立倒排索引
- knowledge/search.py
  - 输入命盘特征 → 返回最相关的知识片段

**Day 19：视角知识注入**
- 修改 perspective_engine.py
  - 推理前先从知识库检索相关案例
  - 将知识片段加入推理上下文
  - LLM基于真实命理知识生成观点

**Day 20：内容质量检查**
- 禁用词检查（首先/其次/因此等）
- 句子长度检查（每句不超过25字）
- 比喻数量检查（至少3种）
- 七段结构检查

**Day 21：端到端测试**
- 10组命盘完整流程测试
- 排盘 → 交叉验证 → 问答 → 辩论
- 输出质量人工评分

**Stage 5 交付**：
- 知识库接入
- 输出内容符合玄学泰斗写作规范
- 端到端流程稳定

---

## 总计

| 阶段 | 天数 | 交付物 |
|------|------|--------|
| Stage 1：地基 | 3天 | 八字+占星准确排盘 + Web界面 |
| Stage 2：紫微 | 5天 | 三术齐全 + 并排展示 |
| Stage 3：交叉验证+问答 | 4天 | 问答系统 + 置信度 |
| Stage 4：12视角辩论 | 5天 | 人物-术法绑定 + 辩论台 |
| Stage 5：知识库整合 | 4天 | 知识注入 + 质量提升 |
| **总计** | **21天** | **完整产品** |

---

## 风险点

1. **紫微斗数自研难度**：排盘算法复杂，如果Day 4-5卡壳，可能延期2-3天。预案：先实现简化版（只排主星，不排辅星和四化）。

2. **Claude API 成本**：12人物 × 每轮辩论调用1次API，单次问答成本约0.1-0.5美元。需要设置用量限制。

3. **知识库格式**：玄学泰斗知识库是 Markdown，需要解析提取结构化内容。如果格式不统一，索引构建会困难。

---

计划如上。确认后从 Stage 1 Day 1 开始执行。
