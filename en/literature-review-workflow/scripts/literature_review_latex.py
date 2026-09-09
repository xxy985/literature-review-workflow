#!/usr/bin/env python3
"""将 LaTeX 工程复制到新版本目录并编译；不覆盖原稿或已有交付。"""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", help="含 main.tex、参考文献及图表的工程目录")
    parser.add_argument("output", help="尚不存在的新版本交付目录，不能位于源工程内")
    args = parser.parse_args(argv)
    source, output = Path(args.project).resolve(), Path(args.output).resolve()
    if not (source / "main.tex").is_file() or output.exists() or source == output or source in output.parents:
        print("源工程须含 main.tex；输出须为源工程外的新目录。", file=sys.stderr)
        return 1
    if not shutil.which("latexmk") or not shutil.which("xelatex"):
        print("缺少 latexmk/xelatex，LaTeX 交付阻塞。请配置 TeX Live 或 MiKTeX 后重试。", file=sys.stderr)
        return 1
    try:
        shutil.copytree(source, output, ignore=shutil.ignore_patterns(
            "main.pdf", "main.log", "*.aux", "*.fdb_latexmk", "*.fls"))
        result = subprocess.run(
            ["latexmk", "-gg", "-xelatex", "-interaction=nonstopmode", "-halt-on-error",
             "-file-line-error", "-latexoption=-no-shell-escape", "main.tex"],
            cwd=str(output), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            encoding="utf-8", errors="replace", timeout=300, check=False)
        (output / "build-output.txt").write_text(result.stdout, encoding="utf-8")
        log = (output / "main.log").read_text(encoding="utf-8", errors="replace") if (output / "main.log").exists() else ""
        pdf = output / "main.pdf"
        unresolved = re.search(r"(?:Citation|Reference).*undefined|There were undefined|Rerun to get|Please \(re\)run", log, re.I)
        if result.returncode or not log or not pdf.is_file() or pdf.stat().st_size == 0 or unresolved:
            print("编译或引用解析未通过，检查新目录中的日志。", file=sys.stderr)
            return 1
        print("编译通过：" + str(pdf) + "；仍须逐页检查版式并核对 DOI 引文映射。")
        return 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("LaTeX 构建失败：" + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
