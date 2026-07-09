# 玄照 Bug 清单 — 真实静态扫描版

**生成方式**: `python scripts/static_audit.py --write`

**对比旧版**: 原 `BUG_LIST.md` 已归档为 `.deprecated`,因为 108 个 bug 里 5 个行号为负数占位符。

## 严重程度分布

- 🔴 真问题: 15
- 🟡 灰带: 0
- 🟢 已废弃: 0

旧版'108 个潜在 bug'无真实依据,**本清单只列真实问题**。

## 全部 Bug 列表

### B001: engine\bazi_engine.py:434 — except ImportError: pass
- 类型: MAYBE_OK
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except ImportError: pass — 静默吞具体类型,需确认

### B002: engine\bazi_engine.py:693 — except Exception: pass
- 类型: MAYBE_OK
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except Exception: pass — 静默吞具体类型,需确认

### B003: engine\llm_client.py:160 — except json.JSONDecodeError: pass
- 类型: MAYBE_OK
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except json.JSONDecodeError: pass — 静默吞具体类型,需确认

### B004: engine\taiyi_engine.py:652 — except ((ValueError, TypeError)): pass
- 类型: INPUT_GUARD
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except ((ValueError, TypeError)): pass — 输入校验白名单,通常合理

### B005: engine\taiyi_engine.py:664 — except ((ValueError, TypeError)): pass
- 类型: INPUT_GUARD
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except ((ValueError, TypeError)): pass — 输入校验白名单,通常合理

### B006: engine\time_engine.py:102 — except Exception: pass
- 类型: MAYBE_OK
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except Exception: pass — 静默吞具体类型,需确认

### B007: engine\time_engine.py:114 — except Exception: pass
- 类型: MAYBE_OK
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except Exception: pass — 静默吞具体类型,需确认

### B008: engine\ziwei_engine.py:686 — except Exception: pass
- 类型: MAYBE_OK
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except Exception: pass — 静默吞具体类型,需确认

### B009: api\divine_lottery_routes.py:464 — except ((ValueError, TypeError)): pass
- 类型: INPUT_GUARD
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except ((ValueError, TypeError)): pass — 输入校验白名单,通常合理

### B010: api\divine_lottery_routes.py:475 — except ((ValueError, TypeError)): pass
- 类型: INPUT_GUARD
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except ((ValueError, TypeError)): pass — 输入校验白名单,通常合理

### B011: api\divine_lottery_routes.py:486 — except ((ValueError, TypeError)): pass
- 类型: INPUT_GUARD
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except ((ValueError, TypeError)): pass — 输入校验白名单,通常合理

### B012: api\divine_lottery_routes.py:501 — except ((ValueError, TypeError)): pass
- 类型: INPUT_GUARD
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except ((ValueError, TypeError)): pass — 输入校验白名单,通常合理

### B013: api\divine_lottery_routes.py:518 — except ((ValueError, TypeError)): pass
- 类型: INPUT_GUARD
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except ((ValueError, TypeError)): pass — 输入校验白名单,通常合理

### B014: api\lottery_routes.py:146 — bare `except:`
- 类型: BARE_EXCEPT
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: bare `except:` — 不指定异常类型,可能捕获 KeyboardInterrupt

### B015: api\score_engine.py:776 — except ((ValueError, TypeError)): pass
- 类型: INPUT_GUARD
- 严重程度: 🟡 P1
- 状态: 待人工 review
- 描述: except ((ValueError, TypeError)): pass — 输入校验白名单,通常合理


## 旧版归档

- `BUG_LIST.md.deprecated`
- `BUG_FIX_REPORT.md.deprecated`

## 教训

旧版用装饰数字和占位符行号制造'已审计'假象,实际上放大了工程风险。
修法: 让真实工具(ruff / mypy / ast)生成清单,不让人工判断行号。
