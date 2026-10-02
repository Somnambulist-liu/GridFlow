"""极简 Markdown → HTML（零依赖）。

只覆盖发布说明里实际会出现的语法：标题、粗体/斜体、行内代码、代码块、无序/有序列表、
GFM 表格、引用、分隔线、链接；并且**先剥掉 HTML 注释**——发布说明模板开头的维护注释
曾经被原样显示在“更新说明”里。

不追求完整 Markdown 兼容：无法识别的行按段落原样输出（已转义），不会丢内容。
"""
import html
import re

_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_ULIST_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_OLIST_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_HR_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


def strip_comments(text: str) -> str:
    """去掉 HTML 注释块（含跨行）。"""
    return _COMMENT_RE.sub("", text or "")


def _inline(text: str) -> str:
    """行内标记：先转义，再套用标记，避免注入。"""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<!\*)\*([^*\s][^*]*)\*(?!\*)", r"<i>\1</i>", out)
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', out)
    return out


def _cells(line: str) -> list:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _table(header: list, rows: list) -> str:
    parts = ["<table cellspacing='0' cellpadding='6' border='0'>", "<tr>"]
    parts += [f"<th>{_inline(c)}</th>" for c in header]
    parts.append("</tr>")
    for row in rows:
        parts.append("<tr>")
        parts += [f"<td>{_inline(c)}</td>" for c in row]
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def to_html(markdown: str) -> str:
    """把 Markdown 子集转成 HTML 片段（可直接交给 QTextBrowser.setHtml）。"""
    lines = strip_comments(markdown).splitlines()
    out = []
    paragraph = []
    list_kind = None
    i = 0

    def flush_paragraph():
        if paragraph:
            out.append("<p>" + "<br>".join(_inline(x) for x in paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append(f"</{list_kind}>")
            list_kind = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            close_list()
            i += 1
            continue

        # 代码块
        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(html.escape(lines[i]))
                i += 1
            i += 1
            out.append("<pre><code>" + "\n".join(block) + "</code></pre>")
            continue

        # 表格（本行含 |，下一行是分隔行）
        if "|" in line and i + 1 < len(lines) and _TABLE_SEP_RE.match(lines[i + 1]):
            flush_paragraph()
            close_list()
            header = _cells(line)
            i += 2
            body = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                body.append(_cells(lines[i]))
                i += 1
            out.append(_table(header, body))
            continue

        # 分隔线
        if _HR_RE.match(line):
            flush_paragraph()
            close_list()
            out.append("<hr>")
            i += 1
            continue

        # 标题
        heading = _HEADING_RE.match(stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = min(len(heading.group(1)), 6)
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        # 引用
        if stripped.startswith(">"):
            flush_paragraph()
            close_list()
            out.append(f"<blockquote>{_inline(stripped[1:].strip())}</blockquote>")
            i += 1
            continue

        # 列表
        ulist = _ULIST_RE.match(line)
        olist = _OLIST_RE.match(line)
        if ulist or olist:
            flush_paragraph()
            kind = "ul" if ulist else "ol"
            if list_kind != kind:
                close_list()
                out.append(f"<{kind}>")
                list_kind = kind
            out.append(f"<li>{_inline((ulist or olist).group(1))}</li>")
            i += 1
            continue

        close_list()
        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    close_list()
    return "\n".join(out)
