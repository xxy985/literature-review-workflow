#!/usr/bin/env python3
"""环境自检：部署前逐项体检（不改动任何文件）。

用法：python literature_review_env_check.py [--net]
- 默认离线体检：Python 版本、平台、标准库模块、可选依赖（pymupdf / python-docx）；
- --net 追加连通性探测（OpenAlex / CrossRef 各 1 次，走 lib 限速器）。
按走廊给出「可用 / 缺依赖」结论与安装命令。
退出码：0 顺畅或仅缺可选项；1 核心环境故障（Python<3.8 或标准库缺失）。
"""

import argparse
import platform
import sys
import shutil

OK, WARN, BAD = "✓", "!", "✗"


def main(argv=None):
    p = argparse.ArgumentParser(description="literature-review-workflow 环境自检")
    p.add_argument("--net", action="store_true", help="附加连通性探测（2 次请求）")
    p.add_argument("--delivery", action="store_true", help="LaTeX 交付依赖缺失时失败")
    args = p.parse_args(argv)
    import literature_review_lib as lib

    lib.fix_encoding()
    fatal = [0]

    def row(status, item, note):
        print(f"{status} {item} — {note}")
        if status == BAD:
            fatal[0] += 1

    print("== literature-review-workflow 环境自检 ==")
    print(f"平台：{platform.system()} {platform.release()}")
    ver = sys.version_info
    row(
        OK if (ver.major, ver.minor) >= (3, 8) else BAD,
        f"Python {ver.major}.{ver.minor}.{ver.micro}",
        "满足 ≥3.8" if (ver.major, ver.minor) >= (3, 8) else "需要 ≥3.8，请升级 Python",
    )
    import importlib

    stdlib_names = (
        "urllib.request",
        "json",
        "csv",
        "gzip",
        "unicodedata",
        "argparse",
        "difflib",
        "re",
    )
    for name in stdlib_names:
        try:
            importlib.import_module(name)
            st, note = OK, "标准库可用"
        except ImportError as e:
            st, note = BAD, f"标准库缺失：{e}"
        row(st, name, note)
    try:
        import fitz  # noqa: F401  pymupdf

        row(OK, "pymupdf", "C3 convert（PDF→md）可用")
    except ImportError:
        row(WARN, "pymupdf", "缺：C3 PDF 转 md 不可用 → pip install pymupdf")
    try:
        import docx  # noqa: F401  python-docx

        row(OK, "python-docx", "C7/C8 饺子交接（docx 互转）可用")
    except ImportError:
        row(WARN, "python-docx", "缺：C7/C8 docx 交接不可用 → pip install python-docx")
    if args.net:
        limiter = lib.RateLimiter()
        for label, url in (
            ("OpenAlex", "https://api.openalex.org/works?per-page=1"),
            ("CrossRef", "https://api.crossref.org/works?rows=1"),
        ):
            try:
                data = lib.http_get_json(url, None, limiter=limiter)
                st, note = (OK, "可连通（已出网 1 次）") if data else (WARN, "响应为空")
            except (RuntimeError, ValueError) as e:
                st, note = WARN, f"不可达：{e}"
            row(st, f"网络 {label}", note)
    print("== 结论 ==")
    for executable in ("latexmk", "xelatex"):
        present = shutil.which(executable)
        row(OK if present else (BAD if args.delivery else WARN), executable,
            present or "C8 必需：安装 TeX Live 或 MiKTeX 后重试；MD/DOCX/LaTeX及编译PDF须一并交付")
    if fatal[0]:
        print("核心环境故障：先解决上述 ✗ 项再部署。")
        return 1
    print("核心链路（C1-C5，纯标准库）当前环境即可运行；")
    print(
        "缺 pymupdf/python-docx 只影响 C3 转换与 C7/C8 饺子交接，到该走廊前再装即可。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
