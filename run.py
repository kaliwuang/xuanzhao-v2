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
    with open(REQUIREMENTS, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg = line.split(">=")[0].split("==")[0].split("[")[0].strip()
            try:
                __import__(pkg.replace("-", "_"))
            except ImportError:
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
    print("   玄照 v2.0 - 七术排盘 x 108视角")
    print("=" * 50)
    try:
        install_deps()
    except Exception as e:
        print(f"Failed: {e}")
        print(f"Run manually: pip install -r requirements.txt")
        return
    port = int(os.environ.get("PORT", "8000"))
    print(f"Starting http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
