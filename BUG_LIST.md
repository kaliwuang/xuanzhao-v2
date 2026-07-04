# 玄照 Bug 清单

共 108 个潜在 bug

## 严重程度分布
- 🔴P0: 4
- 🟡P1: 55
- 🟢P2: 49

## 全部 Bug 列表

### B01: 身弱必喜印比，但若印(土/金)已旺(>3分)反而要克
- 文件: bazi_engine.py
- 行号: -4
- 类型: 喜忌逻辑
- 严重程度: 🔴P0

### B02: '不一致时以扶抑为准'，但调候救命时扶抑让位
- 文件: bazi_engine.py
- 行号: -8
- 类型: 调候逻辑
- 严重程度: 🔴P0

### B03: 中和命局喜忌都为空，但中和命也需调候
- 文件: bazi_engine.py
- 行号: -2
- 类型: 喜忌逻辑
- 严重程度: 🟡P1

### B04: STRONG=40% BALANCED=25% 固定，未按月份/日主调整
- 文件: bazi_engine.py
- 行号: -1
- 类型: 身强身弱
- 严重程度: 🟡P1

### B05: ratio = day_score/total,没算藏干权重,实际每个地支含 2-3 个藏干
- 文件: bazi_engine.py
- 行号: -3
- 类型: 五行计算
- 严重程度: 🟡P1

### B06: 月令得分权重 = 1,应该 = 3 (月令最重要)
- 文件: bazi_engine.py
- 行号: wuxing_score calc
- 类型: 五行计算
- 严重程度: 🟡P1

### B07: 神煞表硬编码,未根据日干/支动态计算
- 文件: bazi_engine.py
- 行号: SHENSHA_*_MAP
- 类型: 神煞
- 严重程度: 🟢P2

### B08: getYun(gender) 但 lunar_python 可能忽略 gender 参数
- 文件: bazi_engine.py
- 行号: 653
- 类型: 大运
- 严重程度: 🔴P0

### B09: 流年起始按年算,没按节气切分
- 文件: bazi_engine.py
- 行号: liunian
- 类型: 流年
- 严重程度: 🟢P2

### B10: 时柱用北京时间,未用真太阳时修正(部分修复,需全面)
- 文件: bazi_engine.py
- 行号: 428
- 类型: 时间
- 严重程度: 🟡P1

### B11: 命身同宫特殊组合未区分
- 文件: ziwei_engine.py
- 行号: ming_gong calc
- 类型: 紫微逻辑
- 严重程度: 🟡P1

### B12: 庙旺利陷判断可能缺失
- 文件: ziwei_engine.py
- 行号: star_brightness
- 类型: 紫微逻辑
- 严重程度: 🟡P1

### B13: 四化飞星可能不全(禄权科忌)
- 文件: ziwei_engine.py
- 行号: 四化
- 类型: 紫微逻辑
- 严重程度: 🟡P1

### B14: 三方四正计算可能不准
- 文件: ziwei_engine.py
- 行号: 三合
- 类型: 紫微逻辑
- 严重程度: 🟡P1

### B15: 流年命宫算法
- 文件: ziwei_engine.py
- 行号: 流年
- 类型: 紫微逻辑
- 严重程度: 🟢P2

### B16: 水星逆行可能未标记
- 文件: astro_engine.py
- 行号: planets
- 类型: 占星
- 严重程度: 🟡P1

### B17: 上升星座可能不准(需用经度)
- 文件: astro_engine.py
- 行号: ascendant
- 类型: 占星
- 严重程度: 🔴P0

### B18: 月亮相位计算
- 文件: astro_engine.py
- 行号: moon_phase
- 类型: 占星
- 严重程度: 🟢P2

### B19: 次限推运、三限推运缺失
- 文件: astro_engine.py
- 行号: progressions
- 类型: 占星
- 严重程度: 🟢P2

### B20: 相位容许度固定,未按行星调整
- 文件: astro_engine.py
- 行号: orbs
- 类型: 占星
- 严重程度: 🟡P1

### B21: 阴阳遁判断(冬至夏至)
- 文件: qimen_engine.py
- 严重程度: 🟡P1

### B22: 局数硬编码 vs 动态
- 文件: qimen_engine.py
- 严重程度: 🟡P1

### B23: 天盘地盘映射
- 文件: qimen_engine.py
- 严重程度: 🟡P1

### B24: 八神排布
- 文件: qimen_engine.py
- 严重程度: 🟡P1

### B25: 十干克应
- 文件: qimen_engine.py
- 严重程度: 🟢P2

### B26: 格局检测
- 文件: qimen_engine.py
- 严重程度: 🟢P2

### B27: 旺衰判断
- 文件: qimen_engine.py
- 严重程度: 🟢P2

### B28: 值符值使
- 文件: qimen_engine.py
- 严重程度: 🟡P1

### B29: 空亡检测
- 文件: qimen_engine.py
- 严重程度: 🟢P2

### B30: 击刑入墓
- 文件: qimen_engine.py
- 严重程度: 🟢P2

### B31: 天盘排布
- 文件: liuren_engine.py
- 严重程度: 🟡P1

### B32: 四课排法
- 文件: liuren_engine.py
- 严重程度: 🟡P1

### B33: 三传取法(贼克/知一/蒿矢)
- 文件: liuren_engine.py
- 严重程度: 🟡P1

### B34: 天将排布(贵人)
- 文件: liuren_engine.py
- 严重程度: 🟡P1

### B35: 课格分类
- 文件: liuren_engine.py
- 严重程度: 🟢P2

### B36: 吉凶判断
- 文件: liuren_engine.py
- 严重程度: 🟢P2

### B37: 月将判断
- 文件: liuren_engine.py
- 严重程度: 🟡P1

### B38: 时辰换日
- 文件: liuren_engine.py
- 严重程度: 🟢P2

### B39: 空亡
- 文件: liuren_engine.py
- 严重程度: 🟢P2

### B40: 神煞
- 文件: liuren_engine.py
- 严重程度: 🟢P2

### B41: 卦序
- 文件: liuyao_engine.py
- 严重程度: 🟢P2

### B42: 动爻
- 文件: liuyao_engine.py
- 严重程度: 🟡P1

### B43: 变卦
- 文件: liuyao_engine.py
- 严重程度: 🟡P1

### B44: 世应
- 文件: liuyao_engine.py
- 严重程度: 🟡P1

### B45: 六亲
- 文件: liuyao_engine.py
- 严重程度: 🟡P1

### B46: 六神
- 文件: liuyao_engine.py
- 严重程度: 🟢P2

### B47: 用神
- 文件: liuyao_engine.py
- 严重程度: 🟡P1

### B48: 旺衰
- 文件: liuyao_engine.py
- 严重程度: 🟡P1

### B49: 月破日破
- 文件: liuyao_engine.py
- 严重程度: 🟢P2

### B50: 伏神
- 文件: liuyao_engine.py
- 严重程度: 🟢P2

### B51: 积年计算
- 文件: taiyi_engine.py
- 严重程度: 🟡P1

### B52: 阳遁阴遁
- 文件: taiyi_engine.py
- 严重程度: 🟡P1

### B53: 局数
- 文件: taiyi_engine.py
- 严重程度: 🟡P1

### B54: 主客算
- 文件: taiyi_engine.py
- 严重程度: 🟡P1

### B55: 三基
- 文件: taiyi_engine.py
- 严重程度: 🟢P2

### B56: 五福
- 文件: taiyi_engine.py
- 严重程度: 🟢P2

### B57: 八门
- 文件: taiyi_engine.py
- 严重程度: 🟢P2

### B58: 天乙地乙
- 文件: taiyi_engine.py
- 严重程度: 🟢P2

### B59: 十六神
- 文件: taiyi_engine.py
- 严重程度: 🟢P2

### B60: 十二运
- 文件: taiyi_engine.py
- 严重程度: 🟢P2

### B61: 五格计算
- 文件: xingming_engine.py
- 严重程度: 🟡P1

### B62: 三才配置
- 文件: xingming_engine.py
- 严重程度: 🟡P1

### B63: 汉字笔画
- 文件: xingming_engine.py
- 严重程度: 🟡P1

### B64: 音韵
- 文件: xingming_engine.py
- 严重程度: 🟢P2

### B65: 八字喜忌结合
- 文件: xingming_engine.py
- 严重程度: 🟡P1

### B66: 城市数据库不全
- 文件: time_engine.py
- 严重程度: 🟡P1

### B67: 拼音回退
- 文件: time_engine.py
- 严重程度: 🟡P1

### B68: 真太阳时精度
- 文件: time_engine.py
- 严重程度: 🟡P1

### B69: 夏令时
- 文件: time_engine.py
- 严重程度: 🟢P2

### B70: 晚子时处理
- 文件: time_engine.py
- 严重程度: 🟡P1

### B71: 经纬度精度
- 文件: time_engine.py
- 严重程度: 🟢P2

### B72: 市/省/县多级
- 文件: time_engine.py
- 严重程度: 🟢P2

### B73: 经度优先 vs 平均
- 文件: time_engine.py
- 严重程度: 🟢P2

### B74: 时区自动
- 文件: time_engine.py
- 严重程度: 🟡P1

### B75: 均时差
- 文件: time_engine.py
- 严重程度: 🟢P2

### B76: 城市编码问题
- 文件: api/routes.py
- 严重程度: 🟡P1

### B77: 参数验证
- 文件: api/routes.py
- 严重程度: 🟢P2

### B78: 超时处理
- 文件: api/routes.py
- 严重程度: 🟡P1

### B79: 错误信息泄露
- 文件: api/routes.py
- 严重程度: 🟢P2

### B80: 缓存
- 文件: api/routes.py
- 严重程度: 🟢P2

### B81: 并发
- 文件: api/routes.py
- 严重程度: 🟡P1

### B82: 数据校验
- 文件: api/routes.py
- 严重程度: 🟢P2

### B83: 日志
- 文件: api/routes.py
- 严重程度: 🟢P2

### B84: 跨域
- 文件: api/routes.py
- 严重程度: 🟢P2

### B85: 输入清理
- 文件: api/routes.py
- 严重程度: 🟡P1

### B86: 8术权重
- 文件: cross_validator.py
- 严重程度: 🟡P1

### B87: 冲突处理
- 文件: cross_validator.py
- 严重程度: 🟡P1

### B88: 维度覆盖
- 文件: cross_validator.py
- 严重程度: 🟡P1

### B89: 置信度
- 文件: cross_validator.py
- 严重程度: 🟢P2

### B90: 108人物
- 文件: perspective_engine.py
- 严重程度: 🟢P2

### B91: LLM调用
- 文件: perspective_engine.py
- 严重程度: 🟡P1

### B92: 辩论流程
- 文件: debate_engine.py
- 严重程度: 🟢P2

### B93: 溟玄风格
- 文件: mingxuan_observer.py
- 严重程度: 🟢P2

### B94: 禁用词
- 文件: content_checker.py
- 严重程度: 🟢P2

### B95: 问答
- 文件: qa_engine.py
- 严重程度: 🟢P2

### B96: 日主强弱评分
- 文件: api/score_engine.py
- 严重程度: 🟡P1

### B97: 五行评分
- 文件: api/score_engine.py
- 严重程度: 🟡P1

### B98: 十神评分
- 文件: api/score_engine.py
- 严重程度: 🟡P1

### B99: 格局评分
- 文件: api/score_engine.py
- 严重程度: 🟡P1

### B100: 大运评分
- 文件: api/score_engine.py
- 严重程度: 🟡P1

### B101: 总分算法
- 文件: api/score_engine.py
- 严重程度: 🟡P1

### B102: 等级划分
- 文件: api/score_engine.py
- 严重程度: 🟢P2

### B103: 补救建议
- 文件: api/score_engine.py
- 严重程度: 🟢P2

### B104: 白话解析
- 文件: api/score_engine.py
- 严重程度: 🟢P2

### B105: 细节缓存
- 文件: api/score_engine.py
- 严重程度: 🟢P2

### B106: 错误处理
- 文件: api/score_engine.py
- 严重程度: 🟢P2

### B107: 并发
- 文件: api/score_engine.py
- 严重程度: 🟢P2

### B108: 边界情况
- 文件: api/score_engine.py
- 严重程度: 🟡P1
