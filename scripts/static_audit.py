#!/usr/bin/env python3
"""
玄照 v2 — 真实静态扫描脚本

替代旧版 BUG_LIST.md(108 个 bug 多数行号是 -4/-8 占位符)

扫描规则:
- `except Exception: pass` 静默吞异常(最容易藏 bug 的模式)
- `except:` bare clause
- 未来可扩展: ruff / mypy / bandit

输出: Markdown 表格 + 真实文件:行号
"""
import ast
import os
import sys
from pathlib import Path


def scan_file(path: str):
    """返回文件中的所有 (行号, 规则, 描述) 元组"""
    issues = []
    try:
        source = open(path, encoding="utf-8").read()
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        issues.append((e.lineno or 0, "SYNTAX", f"语法错误: {e.msg}"))
        return issues

    for node in ast.walk(tree):
        # 规则 1: except Exception: pass (静默吞异常)
        if isinstance(node, ast.ExceptHandler):
            if node.body and len(node.body) == 1:
                inner = node.body[0]
                if isinstance(inner, ast.Pass):
                    # 如果 except 白名单具体类型,可能合理(输入校验)
                    if node.type is not None and isinstance(node.type, ast.Tuple):
                        type_str = ast.unparse(node.type)
                        issues.append((node.lineno, "INPUT_GUARD",
                                      f"except ({type_str}): pass — 输入校验白名单,通常合理"))
                    elif node.type is not None:
                        type_str = ast.unparse(node.type)
                        issues.append((node.lineno, "MAYBE_OK",
                                      f"except {type_str}: pass — 静默吞具体类型,需确认"))
                    else:
                        issues.append((node.lineno, "SWALLOW",
                                      "`except Exception: pass` — 静默吞掉异常,可能掩盖真实错误"))

        # 规则 2: bare except: clause
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append((node.lineno, "BARE_EXCEPT",
                          "bare `except:` — 不指定异常类型,可能捕获 KeyboardInterrupt"))

        # 规则 3: 函数体只有 pass
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if (len(node.body) == 1 and
                isinstance(node.body[0], ast.Pass) and
                not node.decorator_list):
                # 排除 __init__ 等可能合法的空函数
                if not node.name.startswith("__"):
                    issues.append((node.lineno, "EMPTY_FUNC",
                                  f"函数 `{node.name}` 体只有 pass"))

    return issues


def main():
    target_dirs = ["engine", "api"]
    target_files = ["main.py", "config.py"]

    all_issues = []
    for d in target_dirs:
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in files:
                if f.endswith(".py"):
                    full = os.path.join(root, f)
                    for line, rule, desc in scan_file(full):
                        all_issues.append((full, line, rule, desc, "ast"))

    for f in target_files:
        if os.path.isfile(f):
            for line, rule, desc in scan_file(f):
                all_issues.append((f, line, rule, desc, "ast"))

    # ruff 真实问题 (E/F/W + 重复键 F601)
    # ruff 默认输出 install 可能在,试一下;失败则跳过
    import shutil
    import subprocess
    ruff_bin = shutil.which("ruff")
    if not ruff_bin:
        venv_ruff = os.path.join(os.path.dirname(sys.executable), "ruff.exe" if os.name == "nt" else "ruff")
        if os.path.isfile(venv_ruff):
            ruff_bin = venv_ruff
    if ruff_bin:
        try:
            cmd = [ruff_bin, "check", "--select=E,F,W", "--output-format=concise",
                   "engine", "api", "main.py", "config.py"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            for line in r.stdout.splitlines():
                # 格式: path:line:col: code message
                parts = line.split(":", 4)
                if len(parts) < 5:
                    continue
                path, lineno, col, code, message = parts[0], parts[1], parts[2], parts[3].strip(), parts[4].strip()
                try:
                    lineno_int = int(lineno)
                except ValueError:
                    continue
                all_issues.append((path, lineno_int, code, message[:120], "ruff"))
        except Exception as e:
            print(f"ruff 调用失败: {e}", file=sys.stderr)

    # 输出 markdown
    print(f"# 玄照 静态扫描结果")
    print(f"")
    print(f"扫描范围: {' + '.join(target_dirs)} + {', '.join(target_files)}")
    print(f"扫描时间: {os.popen('echo %date% %time%').read().strip()}")
    print(f"")
    print(f"## 总览")
    print(f"")
    print(f"- 总问题数: **{len(all_issues)}**")
    by_rule = {}
    for _, _, rule, _, _ in all_issues:
        by_rule[rule] = by_rule.get(rule, 0) + 1
    for rule, count in sorted(by_rule.items()):
        print(f"  - {rule}: {count}")
    print(f"")
    print(f"## 详细列表")
    print(f"")
    print(f"| # | 文件 | 行号 | 规则 | 描述 |")
    print(f"|---|---|---|---|---|")
    for i, (path, line, rule, desc, _) in enumerate(all_issues, 1):
        rel = path.replace(os.getcwd() + os.sep, "") if path.startswith(os.getcwd()) else path
        print(f"| {i:03d} | `{rel}` | {line} | {rule} | {desc} |")

    # 同时输出 BUG_LIST.md 格式
    if "--write" in(sys.argv):
        out_path = "BUG_LIST.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# 玄照 Bug 清单 — 真实静态扫描版\n\n")
            f.write("**生成方式**: `python scripts/static_audit.py --write`\n\n")
            f.write("扫描器: `ast`(逻辑问题) + `ruff -E,F,W`(PEP8 风格 + 重复键 F601)\n\n")
            f.write("**对比旧版**: 原 `BUG_LIST.md` 已归档为 `.deprecated`,因为 108 个 bug 里 5 个行号为负数占位符。\n\n")
            f.write("## 严重程度分布\n\n")
            f.write(f"- 🔴 真问题(ast 扫描): {sum(1 for x in all_issues if x[4]=='ast')}\n")
            f.write(f"- 🟡 ruff 问题(风格+重复键): {sum(1 for x in all_issues if x[4]=='ruff')}\n\n")
            f.write("旧版'108 个潜在 bug'无真实依据,**本清单只列真实问题**。\n\n")
            f.write("## 全部 Bug 列表(ast)\n\n")
            n = 0
            for i, (path, line, rule, desc, source) in enumerate(all_issues, 1):
                if source != "ast":
                    continue
                n += 1
                rel = path.replace(os.getcwd() + os.sep, "") if path.startswith(os.getcwd()) else path
                f.write(f"### B{n:03d}: {rel}:{line} — {desc.split(' — ')[0]}\n")
                f.write(f"- 扫描器: ast\n")
                f.write(f"- 类型: {rule}\n")
                f.write(f"- 严重程度: 🟡 P1\n")
                f.write(f"- 状态: 待人工 review\n")
                f.write(f"- 描述: {desc}\n\n")
            f.write("\n## Ruff 风格问题(前 30 条,完整版跑 ruff check)\n\n")
            n = 0
            for i, (path, line, rule, desc, source) in enumerate(all_issues, 1):
                if source != "ruff":
                    continue
                n += 1
                if n > 30:
                    break
                rel = path.replace(os.getcwd() + os.sep, "") if path.startswith(os.getcwd()) else path
                f.write(f"### R{n:03d}: {rel}:{line} — {rule}\n")
                f.write(f"- 扫描器: ruff\n")
                f.write(f"- 类型: {rule}\n")
                f.write(f"- 描述: {desc}\n\n")
            f.write("\n## 旧版归档\n\n")
            f.write("- `BUG_LIST.md.deprecated`\n")
            f.write("- `BUG_FIX_REPORT.md.deprecated`\n\n")
            f.write("## 教训\n\n")
            f.write("旧版用装饰数字和占位符行号制造'已审计'假象,实际上放大了工程风险。\n")
            f.write("修法: 让真实工具(ruff / mypy / ast)生成清单,不让人工判断行号。\n")
        print(f"\n已写入 {out_path}")


if __name__ == "__main__":
    main()