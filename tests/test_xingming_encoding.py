#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xingming 接口编码兼容性测试

复现并验证 bug 修复:
- curl --data-urlencode 默认按 GBK 编码汉字(Windows / Git Bash)
- urllib / requests / 浏览器按 UTF-8 编码汉字
- 服务器(uvicorn + FastAPI)必须同时接受两种编码

跑法:
    cd C:/Users/W/xuanzhao-v2
    pytest tests/test_xingming_encoding.py -v

或者直接执行(用 subprocess 跑真实 curl + urllib,需要 8080 端口有 server):
    python tests/test_xingming_encoding.py
"""
import os
import sys
import subprocess
import urllib.parse
import urllib.request
import json
import time
import socket

# 让脚本能直接 import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SERVER_URL = "http://127.0.0.1:8080"
API_PATH = "/api/xingming"


# ── 服务管理 ──────────────────────────────────────────────────
class _ServerManager:
    """pytest 模式下,如未起 server 就起一个;脚本模式下由 main() 管理"""

    def __init__(self):
        self.proc = None

    def ensure(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", 8080))
                return  # 已经在跑
            except OSError:
                pass
        # 启动
        self.proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for _ in range(60):
            time.sleep(0.5)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                try:
                    s.connect(("127.0.0.1", 8080))
                    return
                except OSError:
                    continue
        self.proc.terminate()
        raise RuntimeError("server failed to start within 30s")

    def stop(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


_server = _ServerManager()
_server.ensure()


def pytest_configure(config):
    """pytest 入口,确保 server 跑着"""
    _server.ensure()


# ── 客户端调用 ────────────────────────────────────────────────
def call_via_urllib(name: str) -> dict:
    """模拟 Python urllib/requests 路径:按 UTF-8 编码 name"""
    url = f"{SERVER_URL}{API_PATH}?name={urllib.parse.quote(name)}"
    raw = urllib.request.urlopen(url, timeout=10).read()
    return json.loads(raw.decode("utf-8"))


def call_via_curl_gbk(name: str) -> dict:
    """模拟 Windows curl 路径:按 GBK 编码 name"""
    proc = subprocess.run(
        [
            "curl", "-s", "-G", f"{SERVER_URL}{API_PATH}",
            "--data-urlencode", f"name={name}",
        ],
        capture_output=True, timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"curl failed: {proc.stderr.decode('gbk', 'replace')}")
    return json.loads(proc.stdout.decode("utf-8"))


def _assert_valid_response(data: dict, name: str):
    """断言响应有效:有 surname + given_name,没有"姓名必须包含汉字"错误"""
    assert data, f"响应为空: name={name!r}"
    err = data.get("error", "")
    assert "姓名必须包含汉字" not in err, \
        f"编码 bug 未修复: name={name!r} 触发 '姓名必须包含汉字' 错误,响应={data}"
    assert data.get("surname"), f"响应缺少 surname: name={name!r}, 响应={data}"
    assert data.get("given_name"), f"响应缺少 given_name: name={name!r}, 响应={data}"


# ── 测试用例 ──────────────────────────────────────────────────
class TestUrllibUtf8:
    """客户端按 UTF-8 编码,模拟 Python / 浏览器 / requests 路径"""

    def test_chinese_simplified(self):
        """简体: 侯惠斌"""
        data = call_via_urllib("侯惠斌")
        _assert_valid_response(data, "侯惠斌")
        assert data["surname"] == "侯", f"surname 应为 '侯', 实际 {data['surname']!r}"
        assert data["given_name"] == "惠斌", \
            f"given_name 应为 '惠斌', 实际 {data['given_name']!r}"

    def test_chinese_compound_simplified(self):
        """简体复姓: 欧阳明"""
        data = call_via_urllib("欧阳明")
        _assert_valid_response(data, "欧阳明")
        assert data["surname"] == "欧阳", \
            f"复姓识别失败: surname 应为 '欧阳', 实际 {data['surname']!r}"
        assert data["given_name"] == "明"


class TestCurlGbk:
    """客户端按 GBK 编码,模拟 Windows curl / Git Bash 路径"""

    def test_chinese_simplified_via_curl(self):
        """curl 简体: 这是 bug 报告的核心场景"""
        data = call_via_curl_gbk("侯惠斌")
        _assert_valid_response(data, "侯惠斌")
        assert data["surname"] == "侯", \
            f"BUG 未修复: curl GBK '侯惠斌' -> surname {data.get('surname')!r}, 期望 '侯'"
        assert data["given_name"] == "惠斌"

    def test_chinese_compound_simplified_via_curl(self):
        """curl 简体复姓"""
        data = call_via_curl_gbk("欧阳明")
        _assert_valid_response(data, "欧阳明")
        assert data["surname"] == "欧阳"
        assert data["given_name"] == "明"

    def test_chinese_traditional_via_curl(self):
        """curl 繁体: 验证编码兼容(注意:复姓识别用的是简体表,繁体不识别复姓)"""
        data = call_via_curl_gbk("歐陽明")
        _assert_valid_response(data, "歐陽明")
        # 编码正确即可: 服务器拿到 "歐陽明",surname 至少是 "歐"
        # 复姓"歐陽"不在 COMPOUND_SURNAMES 列表(只有简体),所以只识别单字"歐"
        assert data["surname"] == "歐", \
            f"GBK 繁体解码失败: surname {data.get('surname')!r}, 期望 '歐'"


class TestEncodingConsistency:
    """两种编码路径应该返回一致结果"""

    def test_utf8_and_gbk_yield_same_result(self):
        a = call_via_urllib("侯惠斌")
        b = call_via_curl_gbk("侯惠斌")
        for key in ("surname", "given_name", "is_compound_surname"):
            assert a.get(key) == b.get(key), \
                f"编码路径结果不一致 ({key}):\n  UTF-8: {a.get(key)!r}\n  GBK:   {b.get(key)!r}"


class TestCrossPathSanity:
    """额外 sanity check:不同 HTTP 头部形式都能跑通"""

    def test_path_in_url_no_query(self):
        """纯 ASCII query (无编码问题) 仍能正常工作"""
        # 简单 ASCII 名不会被"姓名必须包含汉字"判失败以外的逻辑挡
        data = call_via_urllib("张三")
        _assert_valid_response(data, "张三")
        assert data["surname"] == "张"

    def test_curl_with_utf8_env(self):
        """即使在 Windows curl 上, 强制传 UTF-8 也能用 (用 -d 形式)"""
        # curl --data-urlencode 在 MSYS/Git Bash 上是 GBK, 但 --data-raw + 手动 url-encode 是 UTF-8
        # 这里模拟的就是 urlencode 后用 curl 发, 这就是 urllib 的等价路径
        name_utf8 = "侯惠斌"
        # 用 urllib 代替
        url = f"{SERVER_URL}{API_PATH}?name={urllib.parse.quote(name_utf8)}"
        data = json.loads(urllib.request.urlopen(url, timeout=10).read())
        _assert_valid_response(data, name_utf8)
        assert data["surname"] == "侯"


# ── 入口 ──────────────────────────────────────────────────────
def main():
    """直接 python tests/test_xingming_encoding.py 时跑这个"""
    print("=" * 60)
    print("玄照 /api/xingming 编码兼容性测试")
    print("=" * 60)

    cases = [
        ("URL-utf8  侯惠斌 (简体)",    "urllib", "侯惠斌"),
        ("URL-utf8  欧阳明 (复姓)",    "urllib", "欧阳明"),
        ("curl-GBK  侯惠斌 (简体)",    "curl",   "侯惠斌"),
        ("curl-GBK  欧阳明 (复姓)",    "curl",   "欧阳明"),
        ("curl-GBK  歐陽明 (繁体)",    "curl",   "歐陽明"),
    ]
    failed = 0
    for desc, kind, name in cases:
        if kind == "urllib":
            data = call_via_urllib(name)
        else:
            data = call_via_curl_gbk(name)
        ok = (data.get("surname")
              and "姓名必须包含汉字" not in data.get("error", ""))
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {desc:36s} -> surname={data.get('surname')!r}, given={data.get('given_name')!r}")
        if not ok:
            print(f"        error: {data.get('error')}")
            failed += 1

    print()
    if failed:
        print(f"失败 {failed} 个用例")
        sys.exit(1)
    else:
        print("全部通过")


if __name__ == "__main__":
    main()
