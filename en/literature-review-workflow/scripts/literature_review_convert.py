#!/usr/bin/env python3
"""PDF 转 Markdown（C3）：source/papers/roundNN/<doi>.pdf → 同名 .md。

用法：python literature_review_convert.py <工作根目录> --round N [--papers id1,id2] [--force]
- 依赖 pymupdf（缺它时明确报错并给安装命令，不静默降级）；
- 已有 md 且未 --force 则跳过；
- 文本量评分：页均字符 ≥800 high / ≥300 mid / 其余 low / 0 字符 failed（扫描版）；
- low 与 failed 如实写库（parse_quality），不谎报；
- 写回库行 md_path + parse_quality，并留运行日志。
退出码：0 全部处理（含如实记录的 low/failed）；1 环境或输入错误。
"""

import argparse
import os
import sys


def _parse_args(argv):
    p = argparse.ArgumentParser(description="PDF 批量转 Markdown（C3）")
    p.add_argument("work_dir", help="工作根目录")
    p.add_argument("--round", required=True, help="轮次编号 N（1-99）或 X（扩圈批次）")
    p.add_argument(
        "--papers", default="", help="只处理指定 doi，逗号分隔；缺省处理整轮"
    )
    p.add_argument("--force", action="store_true", help="已有 md 也重转")
    return p.parse_args(argv)


def _grade(pages_text):
    """页均字符评分：high/mid/low/failed。"""
    n = len(pages_text)
    total = sum(len(t) for t in pages_text)
    if n == 0 or total == 0:
        return "failed", 0
    per = total / n
    if per >= 800:
        return "high", per
    if per >= 300:
        return "mid", per
    return "low", per


def convert_one(fitz, pdf_path, md_path, doi, header_lines):
    """转换单个 PDF，返回 (parse_quality, 页均字符)。失败抛 RuntimeError。"""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:  # pymupdf 的打开失败类型不稳定，统一包 RuntimeError
        raise RuntimeError(f"打开 PDF 失败 {pdf_path}: {e}") from e
    try:
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text("text"))
        quality, per = _grade(pages_text)
        try:
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write("---\n")
                fh.write("\n".join(header_lines) + "\n")
                fh.write("---\n\n")
                if quality == "failed":
                    fh.write(
                        "<!-- 文本提取失败：可能是扫描版 PDF，"
                        "需人工阅读或 OCR，(parse_quality=failed) -->\n"
                    )
                for i, text in enumerate(pages_text, 1):
                    fh.write(f"\n<!-- page {i} -->\n")
                    fh.write(text.strip() + "\n")
        except OSError as e:
            raise RuntimeError(f"写入 md 失败 {md_path}: {e}") from e
        return quality, per
    finally:
        doc.close()


def main(argv=None):
    args = _parse_args(argv)
    import literature_review_lib as lib

    lib.fix_encoding()
    try:
        import fitz
    except ImportError:
        print("缺少 pymupdf：请先运行  pip install pymupdf  再重试。", file=sys.stderr)
        return 1
    work_dir = args.work_dir
    r = str(args.round).strip().upper()
    try:
        round_no = "X" if r == "X" else int(r)
        tag = lib.round_tag(round_no)
    except (ValueError, RuntimeError) as e:
        print(f"--round 需为 1-99 的整数或 X（扩圈批次）：{e}", file=sys.stderr)
        return 1
    try:
        rows = lib.load_library(work_dir)
        rows_by_id = {r.get("doi"): r for r in rows}
        round_dir = os.path.join(work_dir, "source", "papers", "round" + tag)
        if not os.path.isdir(round_dir):
            print(f"轮目录不存在：{round_dir}", file=sys.stderr)
            return 1
        pdfs = sorted(f for f in os.listdir(round_dir) if f.lower().endswith(".pdf"))
    except (OSError, RuntimeError) as e:
        print(f"读取库或目录失败：{e}", file=sys.stderr)
        return 1
    want = [x.strip() for x in args.papers.split(",") if x.strip()]
    done, skipped, failed_files = [], [], []
    for name in pdfs:
        from urllib.parse import unquote
        pid = lib.normalize_doi(unquote(name[:-4]))
        row = rows_by_id.get(pid)
        if want and pid not in [lib.normalize_doi(d) for d in want]:
            continue
        if row is None:
            print(f"! {pid}：库中无行，先由 fetch 入库再转换（跳过）", file=sys.stderr)
            skipped.append(pid)
            continue
        pdf_path = os.path.join(round_dir, name)
        md_path = pdf_path[:-4] + ".md"
        if os.path.isfile(md_path) and not args.force:
            skipped.append(pid)
            continue
        header = [
            f"title: {row.get('title') or ''}",
            f"doi: {row.get('doi') or ''}",
            f"url: {row.get('url') or ''}",
            f"round: {row.get('round') or round_no}",
        ]
        try:
            quality, _per = convert_one(fitz, pdf_path, md_path, pid, header)
        except RuntimeError as e:
            print(f"✗ {pid}: {e}", file=sys.stderr)
            failed_files.append(pid)
            continue
        rel_md = os.path.relpath(md_path, work_dir).replace("\\", "/")
        try:
            lib.update_library_row(work_dir, pid, md_path=rel_md, parse_quality=quality)
            lib.log_run(work_dir, "C3", "convert", f"{pid} parse_quality={quality}")
        except RuntimeError as e:
            print(f"✗ {pid}：写库失败：{e}", file=sys.stderr)
            return 1
        done.append((pid, quality))
    print(f"== convert round {tag} ==")
    for pid, quality in done:
        print(f"✓ {pid} → md，parse_quality={quality}")
    if skipped:
        print(f"跳过 {len(skipped)} 个（未选/已有 md/无库行）：{','.join(skipped)}")
    if failed_files:
        print(
            f"✗ 失败 {len(failed_files)} 个（见上），可 --papers 单独重试："
            f"{','.join(failed_files)}"
        )
        return 1
    n_high = sum(1 for _p, q in done if q == "high")
    print(
        f"共转换 {len(done)} 篇（high={n_high}）；low/failed 如实入账，"
        "请按 SKILL.md 决定是否人工采样复核。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
