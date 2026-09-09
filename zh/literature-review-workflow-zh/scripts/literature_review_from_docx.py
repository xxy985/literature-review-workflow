#!/usr/bin/env python3
"""docx → Markdown（C8 饺子回件）：按文档流顺序回转，保留标题/列表/表格/加粗。

用法：python literature_review_from_docx.py <src.docx> [dst.md]
- dst 缺省：与 src 同名 .md；
- 段落与表格按原文档顺序输出（不丢表格、不乱序）；
- 标题样式 → # 层级；List Bullet → - ；加粗 run → **；
- 依赖 python-docx（缺它时明确报错并给安装命令）。
返回后接 check --diff 出助理改动日志（C8 流程）。
退出码：0 成功；1 环境或输入失败。
"""

import argparse
import os
import sys


def _parse_args(argv):
    p = argparse.ArgumentParser(description="docx 转 Markdown（C8 回件）")
    p.add_argument("src", help="源 docx 文件（助理回件）")
    p.add_argument("dst", nargs="?", default="", help="目标 md（缺省同名 .md）")
    return p.parse_args(argv)


def _para_md(para):
    """段落 → md 文本（加粗 run 包 **，其余按原文）。"""
    parts = []
    bold_open = False
    for run in para.runs:
        t = run.text or ""
        if not t:
            continue
        if run.bold:
            if not bold_open:
                parts.append("**")
                bold_open = True
            parts.append(t)
        else:
            if bold_open:
                parts.append("**")
                bold_open = False
            parts.append(t)
    if bold_open:
        parts.append("**")
    return "".join(parts)


def _table_md(table):
    """表格 → md 管道表（首行做表头 + 分隔行）。"""
    lines = []
    for i, row in enumerate(table.rows):
        cells = []
        for cell in row.cells:
            cells.append(cell.text.replace("|", "\\|").replace("\n", " ").strip())
        lines.append("| " + " | ".join(cells) + " |")
        if i == 0:
            lines.append("|" + "---|" * len(cells))
    return lines


def docx_to_md_lines(doc):
    """按 body 顺序遍历段落/表格 → md 行列表。"""
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    out = []
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            para = Paragraph(child, doc)
            style = (para.style.name if para.style is not None else "") or ""
            text = _para_md(para)
            if not text.strip():
                out.append("")
                continue
            if style.startswith("Heading"):
                try:
                    level = min(int(style.split()[-1]), 6)
                except ValueError:
                    level = 2
                out.append("#" * level + " " + text)
            elif style == "List Bullet":
                out.append("- " + text)
            else:
                out.append(text)
        elif tag == "tbl":
            out.extend(_table_md(Table(child, doc)))
            out.append("")
    return out


def main(argv=None):
    args = _parse_args(argv)
    import literature_review_lib as lib

    lib.fix_encoding()
    try:
        from docx import Document
    except ImportError:
        print(
            "缺少 python-docx：请先运行  pip install python-docx  再重试。",
            file=sys.stderr,
        )
        return 1
    if not os.path.isfile(args.src):
        print(f"源文件不存在：{args.src}", file=sys.stderr)
        return 1
    try:
        doc = Document(args.src)
    except Exception as e:
        print(f"打开 docx 失败（可能不是 docx 格式）{args.src}: {e}", file=sys.stderr)
        return 1
    dst = args.dst or os.path.splitext(args.src)[0] + ".md"
    lines = docx_to_md_lines(doc)
    body = "\n".join(lines).rstrip() + "\n"
    n_head = sum(1 for ln in lines if ln.startswith("#"))
    n_tbl = body.count("|---")
    n_bold = body.count("**") // 2
    try:
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        with open(dst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
    except OSError as e:
        print(f"写出 md 失败 {dst}: {e}", file=sys.stderr)
        return 1
    print(f"✓ 回转完成：{args.src} → {dst}")
    print(
        f"  段落风格统计：标题 {n_head} 个，表格约 {n_tbl} 个，加粗 run 约 {n_bold} 处"
    )
    print(
        "下一步：python literature_review_check.py <工作根目录> --diff <转出稿> <回转稿> 出助理改动日志。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

