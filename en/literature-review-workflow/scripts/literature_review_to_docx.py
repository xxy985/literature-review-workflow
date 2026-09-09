#!/usr/bin/env python3
"""Markdown → docx（C7 饺子交接）：转前自动跑引号配对/加粗污染检查。

用法：python literature_review_to_docx.py <src.md> <dst.docx> [--force]
- 检查项（D2/交付口径）：弯引号 “ ” 必须配对；** 标记必须成对；
  不通过则拒绝转换（--force 强转，风险自负）；
- 支持：标题层级、无序/有序列表、表格、代码块、行内加粗/斜体；
- 依赖 python-docx（缺它时明确报错并给安装命令）。
退出码：0 成功；1 环境或检查失败；2 参数错误。
"""

import argparse
import os
import re
import sys

INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)")


def _parse_args(argv):
    p = argparse.ArgumentParser(description="Markdown 转 docx（C7 交接）")
    p.add_argument("src", help="源 Markdown 文件")
    p.add_argument("dst", help="目标 docx 文件")
    p.add_argument("--force", action="store_true", help="检查不过也强转")
    return p.parse_args(argv)


def _read_lines(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"读取失败 {path}: {e}") from e


def pre_check(text):
    """配对检查，返回 (是否通过, 问题列表)。"""
    problems = []
    open_q, close_q = text.count("\u201c"), text.count("\u201d")
    if open_q != close_q:
        problems.append(f"弯引号不配对：\u201c×{open_q} vs \u201d×{close_q}")
    n_bold = text.count("**")
    if n_bold % 2:
        problems.append(f"加粗标记 ** 数量为奇数（{n_bold}），可能污染句子")
    n_straight = text.count('"')
    if n_straight:
        problems.append(f'提示：正文含直引号 " ×{n_straight}（建议人工确认为有意保留）')
    return (not problems), problems


def _add_runs(para, text):
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if len(part) > 4 and part.startswith("**") and part.endswith("**"):
            run = para.add_run(part[2:-2])
            run.bold = True
        elif len(part) > 2 and part.startswith("*") and part.endswith("*"):
            run = para.add_run(part[1:-1])
            run.italic = True
        else:
            para.add_run(part)


def _add_table(doc, rows):
    """rows: list[list[str]]，渲染为 Table Grid。"""
    n_cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=n_cols)
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        for j in range(n_cols):
            table.cell(i, j).text = row[j] if j < len(row) else ""


def md_to_docx(doc, lines):
    """把 md 行序列写入 python-docx Document。"""
    in_code = False
    code_buf = []
    table_buf = []

    def flush_table():
        if not table_buf:
            return
        rows = []
        for ln in table_buf:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", c or "---") for c in cells):
                continue  # 分隔行
            rows.append(cells)
        if rows:
            _add_table(doc, rows)
        table_buf.clear()

    for line in lines:
        if line.strip().startswith("```"):
            flush_table()
            if in_code:
                for cl in code_buf:
                    para = doc.add_paragraph()
                    run = para.add_run(cl)
                    run.font.name = "Consolas"
                code_buf = []
            in_code = not in_code
            continue
        if in_code:
            code_buf.append(line)
            continue
        if line.strip().startswith("|") and line.strip().endswith("|"):
            table_buf.append(line)
            continue
        flush_table()
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", s)
        if m:
            doc.add_heading(m.group(2), level=min(len(m.group(1)), 4))
            continue
        if re.match(r"^[-*]\s+", s):
            para = doc.add_paragraph(style="List Bullet")
            _add_runs(para, re.sub(r"^[-*]\s+", "", s))
            continue
        m = re.match(r"^(\d+)[.、)]\s+(.*)", s)
        if m:
            para = doc.add_paragraph()
            _add_runs(para, m.group(0))
            continue
        para = doc.add_paragraph()
        _add_runs(para, s)
    flush_table()


def main(argv=None):
    args = _parse_args(argv)
    import literature_review_lib as lib

    lib.fix_encoding()
    try:
        import docx  # noqa: F401  python-docx
    except ImportError:
        print(
            "缺少 python-docx：请先运行  pip install python-docx  再重试。",
            file=sys.stderr,
        )
        return 1
    try:
        lines = _read_lines(args.src)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    text = "\n".join(lines)
    passed, problems = pre_check(text)
    if not passed:
        for p in problems:
            print(f"! {p}", file=sys.stderr)
        if not args.force:
            print("检查未通过，拒绝转换（--force 可强转）。", file=sys.stderr)
            return 1
        print("--force：带问题强转。", file=sys.stderr)
    from docx import Document

    doc = Document()
    md_to_docx(doc, lines)
    dst = args.dst
    try:
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        doc.save(dst)
    except OSError as e:
        print(f"写出 docx 失败 {dst}: {e}", file=sys.stderr)
        return 1
    print(f"✓ 转换完成：{args.src} → {dst}")
    print(
        "同目录请写 交接说明.md 给人类助理（改文字句子；改完存 source/jiaozi/ 或直接回复意见）。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

