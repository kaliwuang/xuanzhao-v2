# 玄照 v2 改进记录

## 2026-06-30 - Soul v2 自动发现改进点

**Soul v2 自动扫描发现的真实改进点（不是凑数）：**

### 改进 #201: 评分系统加"补救建议"字段
- **现状**: `api/routes.py:1488` 评分详情只有 title/icon/score/max/text
- **缺失**: 低分维度只有"是什么"，没有"怎么办"
- **建议实现**: 
  - 对每个评分 ≤ 10/20 的维度，根据命理给 actionable advice
  - 比如"格局清纯 6/20" → "建议从事技术/手艺类工作，避免从政；多与印星旺的人合作"
- **预期效果**: API 返回多一个 `advice` 字段
- **验证**: 测试从 4 → 5 维度

### 改进 #202: Soul notify 加发送成功日志
- **现状**: notify 函数不记录是否成功
- **缺失**: 不知道自己有没有真发出（之前用 origin target 静默失败）
- **建议实现**: notify 成功后 state["last_notify"] = {target, success, msg}
- **预期效果**: Soul 可以自检

### 改进 #203: 真太阳时计算加城市无法找到时的精确回退
- **现状**: time_engine.py:257 fallback 北京坐标，但日志显示同义词都查不到
- **缺失**: 应该有拼音/英文名 fallback
- **建议实现**: 加 `from pypinyin import lazy_pinyin` 模糊匹配
- **预期效果**: 城市识别率 +10%

### 改进 #204: 启动时自动检查 GitHub 是否有新 Issues/PR
- **现状**: Soul 没有主动跟外界联系
- **缺失**: 用户不问我就不主动看 GitHub
- **建议实现**: daemon 加 GitHub 检查 + notify

### 改进 #205: 跑测试时记录历史，识别 flaky 测试
- **现状**: 偶尔跑测试，不记录
- **缺失**: 不知道哪些测试不稳定
- **建议实现**: `logs/test_history.json` 记录每次结果

---

**不做的（避免 overreach）：**
- ❌ 改核心算法（risky）
- ❌ 大规模重构（破坏 stable 状态）
- ❌ 装新依赖（可能 break）

## 验证方法

每个改进完成后：
1. 跑 `pytest tests/test_engines.py` 确认测试过
2. curl 测试 endpoint 确认 API 正常
3. git commit + push
4. Soul 通过 weixin 通知用户
