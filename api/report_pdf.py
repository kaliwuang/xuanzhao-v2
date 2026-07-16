"""
玄照 · 客户报告 PDF 生成 (2026-07-10 梧指令)

技术路线: 复盘数据(JSON) -> HTML -> Playwright Chromium -> PDF

为什么选 Playwright 而不是 reportlab / weasyprint / xhtml2pdf:
1. reportlab 中文需要 CIDFont 或注册 TTF,跨平台字体加载繁琐
2. weasyprint 在 Windows 上需要 GTK3 + Pango,装包链经常断
3. xhtml2pdf 中文支持弱,缺字体就空白
4. Playwright 用系统 Chromium,中文字体自动识别,3 秒一份 PDF,稳定
"""
from __future__ import annotations

import io
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("xuanzhao.pdf")

# HTML 转义
_HTML_ESCAPE = str.maketrans({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
})


def _esc(s: Any) -> str:
    """HTML 转义 + None 安全"""
    if s is None:
        return ""
    return str(s).translate(_HTML_ESCAPE)


def _topic_color(topic: str) -> str:
    """维度配色 — 每个维度的徽章颜色"""
    return {
        "性格": "#6366f1",  # indigo
        "事业": "#0ea5e9",  # sky
        "健康": "#ef4444",  # red
        "感情": "#ec4899",  # pink
        "财运": "#f59e0b",  # amber
        "学业": "#10b981",  # emerald
    }.get(topic, "#6b7280")


def _confidence_badge(conf: int) -> str:
    """信心分徽章"""
    if conf >= 80:
        return f'<span class="confidence high">{conf} · 高</span>'
    if conf >= 60:
        return f'<span class="confidence mid">{conf} · 中</span>'
    return f'<span class="confidence low">{conf} · 低</span>'


def _confidence_level_text(conf: int) -> str:
    if conf >= 85:
        return "高(斩钉截铁)"
    if conf >= 60:
        return "中(参考档)"
    return "低(仅参考)"


def render_report_html(report: Dict[str, Any]) -> str:
    """把 report dict 渲染成 HTML"""
    identity = report.get("identity", {})
    sections: List[Dict[str, Any]] = report.get("sections", [])
    overall = report.get("confidence_overall", 0)
    disclosures: List[str] = report.get("disclosures", [])
    question = report.get("question", "")
    method_cov = report.get("method_coverage", {})
    next_qs: List[str] = report.get("next_questions", [])

    # 方法覆盖概况
    method_names = {
        "bazi": "八字", "ziwei": "紫微", "astro": "占星",
        "liuyao": "六爻", "qimen": "奇门", "liuren": "六壬",
        "taiyi": "太乙", "xingming": "姓名",
    }
    methods_used = [name for key, name in method_names.items() if method_cov.get(key)]
    methods_str = " · ".join(methods_used) if methods_used else "无"

    # 真太阳时差
    diff_min = identity.get("true_solar_diff_min")
    diff_text = f"({diff_min:+.1f} 分钟)" if diff_min is not None else ""

    # 当前大运
    cur_dy = identity.get("current_dayun_focus", "") or ""

    # ── 头部 ──
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── 6 维度卡片 ──
    sections_html = []
    for sec in sections:
        topic = sec.get("topic", "")
        verdict = sec.get("verdict", "")
        conf = sec.get("confidence", 0)
        evidence: List[str] = sec.get("evidence", [])
        actions: List[str] = sec.get("actions", [])
        counter: List[str] = sec.get("counter_cases", []) or []
        methods: List[str] = sec.get("method_sources", []) or []
        disclosure = sec.get("disclosure", "")

        color = _topic_color(topic)
        level_text = _confidence_level_text(conf)

        # 证据列表
        evidence_items = "".join(
            f'<li>{_esc(e)}</li>' for e in evidence if e
        ) or '<li class="empty">(无显著证据)</li>'

        # 行动指引
        actions_items = "".join(
            f'<li>{_esc(a)}</li>' for a in actions if a
        ) or '<li class="empty">(暂无)</li>'

        # 反向案例
        if counter:
            counter_items = "".join(f'<li>{_esc(c)}</li>' for c in counter)
            counter_html = f'''
            <div class="counter">
              <div class="section-label">反向案例</div>
              <ul>{counter_items}</ul>
            </div>'''
        else:
            counter_html = ""

        # 方法来源
        methods_html = ""
        if methods:
            methods_html = f'<div class="methods">来源:{_esc(" · ".join(methods))}</div>'

        disclosure_html = ""
        if disclosure:
            disclosure_html = f'<div class="disclosure">⚠ {_esc(disclosure)}</div>'

        sections_html.append(f'''
        <div class="section-card">
          <div class="section-header" style="border-left-color:{color}">
            <div class="section-title">
              <span class="topic-badge" style="background:{color}">{_esc(topic)}</span>
              <span class="confidence-text">{_esc(level_text)}</span>
            </div>
            <div class="confidence-meter">
              <div class="confidence-bar" style="width:{conf}%;background:{color}"></div>
            </div>
          </div>

          <div class="verdict">{_esc(verdict)}</div>
          {disclosure_html}

          <div class="section-block">
            <div class="section-label">证据</div>
            <ul>{evidence_items}</ul>
          </div>

          <div class="section-block">
            <div class="section-label">行动</div>
            <ul>{actions_items}</ul>
          </div>

          {counter_html}
          {methods_html}
        </div>
        ''')

    # ── 诚实声明 ──
    disclosures_html = "".join(
        f'<li>{_esc(d)}</li>' for d in disclosures
    )

    # ── 下一步提问 ──
    next_qs_html = "".join(
        f'<li>{_esc(q)}</li>' for q in next_qs
    )

    # ── 文件名 ──
    name_safe = re.sub(r'[^一-鿿\w]', '', identity.get("name", "") or "未填") or "未填"

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>玄照 · 客户报告</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 15mm 18mm 15mm;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    font-family: "Noto Sans SC", "Microsoft YaHei", "SimHei", "SimSun", sans-serif;
    font-size: 11pt;
    line-height: 1.7;
    color: #1f2937;
    background: #fff;
  }}

  /* ── 头部 ── */
  .header {{
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
    color: #fff;
    padding: 24px 28px;
    border-radius: 8px;
    margin-bottom: 18px;
  }}
  .header h1 {{
    font-size: 22pt;
    font-weight: 700;
    letter-spacing: 4px;
    margin-bottom: 4px;
  }}
  .header .subtitle {{
    font-size: 9.5pt;
    opacity: 0.85;
    letter-spacing: 1px;
  }}

  /* ── 身份信息卡片 ── */
  .identity {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 14px 18px;
    margin-bottom: 14px;
  }}
  .identity-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px 18px;
    font-size: 10.5pt;
  }}
  .identity-grid .field {{
    display: flex;
  }}
  .identity-grid .label {{
    color: #64748b;
    width: 56px;
    flex-shrink: 0;
  }}
  .identity-grid .value {{
    color: #0f172a;
    font-weight: 600;
  }}

  /* ── 信心分大数字 ── */
  .overall {{
    text-align: center;
    background: #fafafa;
    border: 2px solid #e0e7ff;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }}
  .overall-label {{
    font-size: 10pt;
    color: #64748b;
    letter-spacing: 2px;
    margin-bottom: 6px;
  }}
  .overall-num {{
    font-size: 36pt;
    font-weight: 700;
    color: #312e81;
    line-height: 1;
  }}
  .overall-num .pct {{ font-size: 16pt; color: #6366f1; }}
  .overall-meta {{
    font-size: 9.5pt;
    color: #475569;
    margin-top: 8px;
  }}

  /* ── 章节标题 ── */
  .h2 {{
    font-size: 13pt;
    font-weight: 700;
    color: #1e1b4b;
    border-bottom: 2px solid #c7d2fe;
    padding-bottom: 4px;
    margin: 18px 0 12px 0;
    letter-spacing: 1px;
  }}

  /* ── 6 维度卡片 ── */
  .section-card {{
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 14px 16px;
    margin-bottom: 12px;
    page-break-inside: avoid;
  }}
  .section-header {{
    border-left: 4px solid #6366f1;
    padding-left: 10px;
    margin-bottom: 8px;
  }}
  .section-title {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }}
  .topic-badge {{
    color: #fff;
    padding: 3px 12px;
    border-radius: 4px;
    font-size: 10pt;
    font-weight: 700;
    letter-spacing: 1px;
  }}
  .confidence-text {{
    font-size: 9.5pt;
    color: #475569;
    background: #e2e8f0;
    padding: 2px 8px;
    border-radius: 3px;
  }}
  .confidence-meter {{
    height: 4px;
    background: #e5e7eb;
    border-radius: 2px;
    overflow: hidden;
  }}
  .confidence-bar {{
    height: 100%;
    border-radius: 2px;
  }}

  .verdict {{
    background: #fef3c7;
    border: 1px solid #fde68a;
    border-radius: 4px;
    padding: 10px 12px;
    font-size: 10.5pt;
    color: #451a03;
    margin: 8px 0;
    line-height: 1.6;
  }}

  .disclosure {{
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 4px;
    padding: 8px 10px;
    font-size: 9pt;
    color: #991b1b;
    margin: 6px 0;
  }}

  .section-block {{
    margin-top: 8px;
  }}
  .section-label {{
    font-size: 9pt;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 1px;
    margin-bottom: 4px;
  }}
  .section-block ul {{
    list-style: none;
    padding-left: 0;
  }}
  .section-block li {{
    font-size: 10pt;
    line-height: 1.65;
    color: #334155;
    padding: 3px 0 3px 14px;
    position: relative;
  }}
  .section-block li::before {{
    content: "·";
    color: #94a3b8;
    font-weight: 700;
    position: absolute;
    left: 4px;
    top: 2px;
  }}
  .section-block li.empty {{
    color: #94a3b8;
    font-style: italic;
  }}

  .counter {{
    margin-top: 8px;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 4px;
    padding: 8px 12px;
  }}
  .counter ul {{ padding-left: 14px; }}
  .counter li {{
    font-size: 9pt;
    color: #7c2d12;
  }}

  .methods {{
    font-size: 8.5pt;
    color: #94a3b8;
    margin-top: 6px;
    text-align: right;
    font-style: italic;
  }}

  /* ── 诚实声明 ── */
  .disclosures {{
    background: #1f2937;
    color: #f3f4f6;
    padding: 14px 18px;
    border-radius: 6px;
    margin-top: 16px;
    page-break-inside: avoid;
  }}
  .disclosures .h2 {{ color: #fbbf24; border-color: #4b5563; }}
  .disclosures li {{
    font-size: 9.5pt;
    line-height: 1.7;
    padding: 3px 0 3px 14px;
    color: #e5e7eb;
    list-style: none;
    position: relative;
  }}
  .disclosures li::before {{
    content: "·";
    position: absolute;
    left: 4px;
    color: #fbbf24;
  }}

  /* ── 下一步 ── */
  .next-questions {{
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    border-radius: 6px;
    padding: 12px 16px;
    margin-top: 12px;
  }}
  .next-questions .h2 {{
    color: #065f46;
    border-color: #6ee7b7;
  }}
  .next-questions li {{
    font-size: 10pt;
    color: #064e3b;
    padding: 3px 0 3px 14px;
    list-style: none;
    position: relative;
  }}
  .next-questions li::before {{
    content: "→";
    position: absolute;
    left: 0;
    color: #10b981;
  }}

  /* ── 页脚 ── */
  .footer {{
    margin-top: 18px;
    padding-top: 10px;
    border-top: 1px solid #e5e7eb;
    font-size: 8pt;
    color: #94a3b8;
    text-align: center;
  }}

  /* ── 屏幕装饰背景 ── */
  .decor {{
    position: absolute;
    width: 200px;
    height: 200px;
    border-radius: 50%;
    opacity: 0.04;
    pointer-events: none;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>玄照 · 客户报告</h1>
  <div class="subtitle">八术联读 · 反向案例校准 · 行为验证 · 概率论诚实声明</div>
</div>

<div class="identity">
  <div class="identity-grid">
    <div class="field"><span class="label">姓名</span><span class="value">{_esc(identity.get("name") or "未填")}</span></div>
    <div class="field"><span class="label">性别</span><span class="value">{_esc(identity.get("gender") or "?")}</span></div>
    <div class="field"><span class="label">出生</span><span class="value">{_esc(identity.get("birth") or "?")} {_esc(diff_text)}</span></div>
    <div class="field"><span class="label">地点</span><span class="value">{_esc(identity.get("location") or "?")}</span></div>
    <div class="field"><span class="label">日主</span><span class="value">{_esc(identity.get("day_master") or "?")} · {_esc(identity.get("strength") or "?")}</span></div>
    <div class="field"><span class="label">大运</span><span class="value">{_esc(cur_dy) or "—"}</span></div>
  </div>
</div>

<div class="overall">
  <div class="overall-label">总 体 信 心 分</div>
  <div class="overall-num">{overall}<span class="pct"> / 100</span></div>
  <div class="overall-meta">覆盖术法:{methods_str} · 问题:{_esc(question)}</div>
</div>

<div class="h2">六 维 度 判 断</div>
{"".join(sections_html)}

<div class="disclosures">
  <div class="h2">🔓 玄 学 诚 实 声 明</div>
  <ul>{disclosures_html}</ul>
</div>

<div class="next-questions">
  <div class="h2">下 一 步 追 问</div>
  <ul>{next_qs_html}</ul>
</div>

<div class="footer">
  玄照 v2.0 · 由 {today} 生成 · 本报告为概率论推演,不构成人生决策 · 命中注定占 30%,后天努力占 70%
</div>

</body>
</html>'''
    return html


def generate_pdf(report: Dict[str, Any], name_safe: str | None = None) -> bytes:
    """
    把 report dict 生成 PDF bytes

    Args:
        report: build_report() 返回的 dict
        name_safe: 文件名用的安全姓名,None 时自动从 report 里取

    Returns:
        PDF 二进制数据
    """
    from playwright.sync_api import sync_playwright

    html = render_report_html(report)

    logger.info("开始生成 PDF, HTML length=%d chars", len(html))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "14mm", "left": "12mm", "right": "12mm"},
                prefer_css_page_size=True,
            )
        finally:
            browser.close()

    logger.info("PDF 生成完成, size=%d bytes", len(pdf_bytes))
    return pdf_bytes


def make_filename(name: str | None, date: datetime | None = None) -> str:
    """生成文件名: 玄照报告_{name}_{date}.pdf"""
    if date is None:
        date = datetime.now()
    date_str = date.strftime("%Y%m%d")

    if name:
        safe = re.sub(r'[^一-鿿\w]', '', name)
        if not safe:
            safe = "未填"
    else:
        safe = "未填"

    return f"玄照报告_{safe}_{date_str}.pdf"
