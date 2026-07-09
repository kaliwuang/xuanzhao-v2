#!/usr/bin/env python3
"""
玄照 v2.0 - 一键启动
自动安装依赖 + 启动服务器
"""
import subprocess, sys, os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS = os.path.join(PROJECT_ROOT, "requirements.txt")


def install_deps():
    missing = []
    # 已知映射: pip 包名 -> Python import 名不一致的情况
    # pyswisseph 是常见的"包名带 py 前缀但 import 名不带"
    PKG_TO_IMPORT_OVERRIDE = {
        "pyswisseph": ["swisseph"],
        "python-multipart": ["multipart"],
    }
    with open(REQUIREMENTS, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg = line.split(">=")[0].split("==")[0].split("[")[0].strip()
            # 候选名: 原名 / 替换连字符 / 替换下划线 / 已知覆盖
            candidates = [pkg, pkg.replace("-", "_"), pkg.replace("_", "-")]
            candidates += PKG_TO_IMPORT_OVERRIDE.get(pkg, [])
            found = False
            for candidate in candidates:
                try:
                    __import__(candidate)
                    found = True
                    break
                except ImportError:
                    continue
            if not found:
                missing.append(line)
    if missing:
        print(f"Installing {len(missing)} dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", REQUIREMENTS])
        print("Done.")
    else:
        print("All dependencies ready.")


def main():
    os.chdir(PROJECT_ROOT)
    print("=" * 50)
    print("   玄照 v2.0 - 八术排盘 x 108视角")
    print("=" * 50)
    try:
        install_deps()
    except Exception as e:
        print(f"Failed: {e}")
        print(f"Run manually: pip install -r requirements.txt")
        return
    # 与 config.py 一致: 默认端口 8080, 环境变量 XUANZHAO_PORT 可覆盖
    # 修复前: 这里用 PORT / 8000, 但 main.py 用 XUANZHAO_PORT / 8080, 显示的 URL 是错的
    port = int(os.environ.get("XUANZHAO_PORT", "8080"))
    host = os.environ.get("XUANZHAO_HOST", "0.0.0.0")
    print(f"Starting http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        import uvicorn
        uvicorn.run("main:app", host=host, port=port, reload=False)
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
