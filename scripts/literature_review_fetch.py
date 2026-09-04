#!/usr/bin/env python3
"""候选文献核验下载入库，或人工补缺配对（综述半自动工作流，走廊 C5：原文获取）。

输入：
  <thread_dir> --candidates <tsv> --round N|X [--limit 10] [--email x@y.z]
    —— 依次核验并下载候选（tsv 为相对 thread_dir 或绝对路径）。
  <thread_dir> --collect-manual --round N|X
    —— 扫描 source/manual/roundNN|XX/ 下 R02-03.pdf / RX-01.pdf 命名的文件，
       复制进 source/papers/roundNN|XX/ 并更新库行。
输出：
  PDF：source/papers/roundNN|XX/<paper_id>.pdf
  库：source/papers/library.tsv 新增/更新行
  清单：source/manual/人工补缺-roundNN|XX.tsv（manual_needed 行）
  日志：notes/history/run-log.tsv

依赖：同目录公共库脚本与校验模块；无第三方依赖。
规则：预印本/核验不通过/无正式版者排除；不绕过付费墙；以实际落盘为准。
退出码：0 成功；1 运行失败；2 参数错误。
"""

import argparse
import csv
import os
import re
import shutil
import sys

OA_BASE = "https://api.openalex.org/works"
UP_BASE = "https://api.unpaywall.org/v2"
PDF_RE = re.compile(r"^[Rr](?:\d{2}|[Xx])-\d{2,}\.pdf$")
EXTRA_FIELDS = ("volume", "issue", "pages")


def _parse_args(argv):
    p = argparse.ArgumentParser(description="候选文献核验、下载入库；或人工补缺配对")
    p.add_argument("thread_dir", help="工作线程根目录")
    p.add_argument(
        "--round",
        required=True,
        help="轮次编号 N（1-99）或 X（扩圈批次），文件放入 roundNN/roundXX 目录",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--candidates", default="", help="候选 TSV 路径（相对 thread_dir 或绝对路径）"
    )
    g.add_argument(
        "--collect-manual",
        action="store_true",
        help="仅做人工补缺配对（扫描 source/manual/roundNN|XX/）",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="本批成功名额：仅 ok 与 abstract_only 计入（默认 10）",
    )
    p.add_argument(
        "--email", default="", help="Unpaywall 优先请求邮箱（不填则跳过 Unpaywall）"
    )
    args = p.parse_args(argv)
    r = str(args.round).strip().upper()
    if r == "X":
        args.round = "X"
    else:
        try:
            args.round = int(r)
        except ValueError:
            p.error("--round 需为 1-99 的整数或 X（扩圈批次）")
        if not 1 <= args.round <= 99:
            p.error("--round 需在 1-99 之间")
    if args.collect_manual and (args.candidates or args.email):
        p.error("--candidates / --email 不能与 --collect-manual 同用")
    return args


def _verify_outcome(res):
    """解读校验模块 verify_batch 的返回，取出（是否通过, verdict, 卷期页）。

    约定返回 dict（含 verdict/volume/issue/pages）或单元素列表包 dict；
    其他形状退化为字符串判断。verdict=='accept' 视为核验通过。
    """
    if isinstance(res, list):
        item = res[0] if res else None
    elif isinstance(res, dict):
        item = res
    else:
        item = None
    if item is None:
        return False, "verify_empty", {"volume": "", "issue": "", "pages": ""}
    if isinstance(item, dict):
        verdict = str(item.get("verdict") or item.get("status") or "")
        extra = {k: item.get(k) or "" for k in EXTRA_FIELDS}
        return (verdict == "accept"), verdict, extra
    return False, str(res)[:40], {"volume": "", "issue": "", "pages": ""}


def _resolve(verify, title):
    try:
        return verify.resolve_formal(title)
    except Exception as e:
        print(f"正式版解析失败（{title[:40]}）：{e}")
        return ""


def _verify_safe(verify, doi):
    try:
        return _verify_outcome(verify.verify_batch([doi]))
    except Exception as e:
        return (
            False,
            f"verify_failed({str(e)[:60]})",
            {"volume": "", "issue": "", "pages": ""},
        )


def _arxiv_id(native_id, url):
    """从 arXiv native_id/URL 提取 arXiv 编号（去 pdf 后缀与版本号）。"""
    s = native_id or url or ""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([^?\s#]+)", s, re.IGNORECASE)
    if not m:
        return ""
    tail = re.sub(r"\.pdf$", "", m.group(1), flags=re.IGNORECASE)
    return re.sub(r"v\d+$", "", tail)


def _in_library(row, lib_db, lib):
    doi = (row.get("doi") or "").strip().lower()
    t = lib.normalize_title(row.get("title") or "")
    for p in lib_db:
        if doi and doi == (p.get("doi") or "").strip().lower():
            return True
        if t and t == lib.normalize_title(p.get("title") or ""):
            return True
    return False


def _make_entry(row, pid, rnd, tag, doi, url, src, extra, oa_flag, status, evidence):
    """构造一条符合库字段约定的行（tag = round_tag，目录名用）。"""
    return {
        "paper_id": pid,
        "title": row.get("title") or "",
        "authors": row.get("authors") or "",
        "year": row.get("year") or "",
        "venue": row.get("venue") or "",
        "volume": extra.get("volume") or "",
        "issue": extra.get("issue") or "",
        "pages": extra.get("pages") or "",
        "doi": doi,
        "url": url or row.get("url") or "",
        "oa": oa_flag,
        "round": rnd,
        "source": src or row.get("source_db") or "",
        "pdf_path": os.path.join("source", "papers", "round" + tag, pid + ".pdf")
        if status == "ok"
        else "",
        "md_path": "",
        "fetch_status": status,
        "parse_quality": "pending",
        "is_read": 0,
        "contribution": "",
        "evidence": evidence,
        "xref_verified": True,
        "added_at": "",
    }


def _download(dest_dir, pid, doi, row, email, lib, limiter):
    """下载链：OpenAlex best_oa_location.pdf_url -> Unpaywall -> 已核验正式版的 arXiv 镜像。"""
    dest = os.path.join(dest_dir, pid + ".pdf")
    try:
        data = lib.http_get_json(
            OA_BASE, params={"filter": "doi:" + doi}, limiter=limiter
        )
        for w in data.get("results") or []:
            if (w.get("doi") or "").replace("https://doi.org/", "") == doi:
                url = (w.get("best_oa_location") or {}).get("pdf_url") or ""
                if url and lib.http_download(url, dest, limiter=limiter):
                    return url, "openalex"
                break
    except (RuntimeError, ValueError) as e:
        print(f"OpenAlex 下载链失败（降级下一源）：{e}", file=sys.stderr)
    if email:
        try:
            data = lib.http_get_json(
                f"{UP_BASE}/{doi}", params={"email": email}, limiter=limiter
            )
            url = (data.get("best_oa_location") or {}).get("url_for_pdf") or ""
            if url and lib.http_download(url, dest, limiter=limiter):
                return url, "unpaywall"
        except (RuntimeError, ValueError) as e:
            print(f"Unpaywall 失败（降级下一源）：{e}", file=sys.stderr)
    aid = _arxiv_id(row.get("native_id") or "", row.get("url") or "")
    if aid:
        url = "https://arxiv.org/pdf/" + aid
        if lib.http_download(url, dest, limiter=limiter):
            return url, "arxiv-mirror"
    return "", ""


def _write_rows(path, cols, rows):
    try:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            wr = csv.writer(fh, delimiter="\t", lineterminator="\n")
            wr.writerow(cols)
            for r in rows:
                wr.writerow([r.get(k, "") for k in cols])
    except OSError as e:
        raise RuntimeError(f"写出文件失败 {path}: {e}") from e


def _process(args, cand_path, lib, verify):
    limiter = lib.RateLimiter()
    lib_db = lib.load_library(args.thread_dir)
    working = [dict(p) for p in lib_db]  # next_paper_id 用的递增镜像
    try:
        with open(cand_path, encoding="utf-8", newline="") as fh:
            cands = [dict(r) for r in csv.DictReader(fh, delimiter="\t")]
    except OSError as e:
        print(f"读取候选文件失败：{e}", file=sys.stderr)
        return 1
    tag = lib.round_tag(args.round)
    c = {
        "ok": 0,
        "abstract_only": 0,
        "manual_needed": 0,
        "excluded": 0,
        "skipped_dup": 0,
    }
    manual_rows = []
    manual_path = ""
    for row in cands:
        if c["ok"] + c["abstract_only"] >= args.limit:
            break
        if _in_library(row, lib_db, lib):
            c["skipped_dup"] += 1
            continue
        pid = lib.next_paper_id(working, args.round)
        doi = (row.get("doi") or "").strip()
        is_arx = (row.get("source_db") or "").strip().lower() == "arxiv"
        is_pp = (row.get("type") or "").strip().lower() == "preprint"
        # 1) 身份解析：arXiv 来源或预印本且无正式 DOI -> 找正式版
        if (is_arx or is_pp) and not doi:
            formal = _resolve(verify, row.get("title") or "")
            if not formal:
                lib.append_excluded(
                    args.thread_dir, row.get("title") or "", "", "preprint_no_formal"
                )
                lib.log_run(
                    args.thread_dir,
                    "C5",
                    "excluded",
                    f"preprint_no_formal：{(row.get('title') or '')[:60]}",
                )
                c["excluded"] += 1
                continue
            doi = str(formal).strip()
        if not doi:
            lib.append_excluded(args.thread_dir, row.get("title") or "", "", "no_doi")
            lib.log_run(
                args.thread_dir,
                "C5",
                "excluded",
                f"no_doi：{(row.get('title') or '')[:60]}",
            )
            c["excluded"] += 1
            continue
        # 2) 核验：verdict != accept -> 排除（预印本一律排除为既定决策）
        acc, verdict, extra = _verify_safe(verify, doi)
        if not acc:
            lib.append_excluded(args.thread_dir, row.get("title") or "", doi, verdict)
            lib.log_run(
                args.thread_dir,
                "C5",
                "excluded",
                f"核验拒绝（{verdict}）：{(row.get('title') or '')[:60]}",
            )
            c["excluded"] += 1
            continue
        # 3) 下载（不绕过付费墙/403；重试由公共库统一管理）
        dest_dir = os.path.join(args.thread_dir, "source", "papers", "round" + tag)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError as e:
            print(f"创建目录失败 {dest_dir}: {e}", file=sys.stderr)
            return 1
        url, src = _download(dest_dir, pid, doi, row, args.email, lib, limiter)
        # 4) 分状态入库；manual_needed 另出人工补缺清单
        if url:
            status, evidence = "ok", ""
        elif (row.get("abstract") or "").strip():
            status, evidence = "abstract_only", "B"
        else:
            status, evidence = "manual_needed", ""
        oa_flag = True if url else (row.get("oa") == "1")
        entry = _make_entry(
            row, pid, args.round, tag, doi, url, src, extra, oa_flag, status, evidence
        )
        lib.append_library(args.thread_dir, [entry])
        working.append(entry)
        c[status] += 1
        if status == "manual_needed":
            manual_rows.append(
                {
                    "paper_id": pid,
                    "title": row.get("title") or "",
                    "authors": row.get("authors") or "",
                    "year": row.get("year") or "",
                    "venue": row.get("venue") or "",
                    "doi": doi,
                    "url": row.get("url") or "",
                    "说明": f"请手动下载后命名为 {pid}.pdf 放入 "
                    f"source/manual/round{tag}/ 目录",
                }
            )
        lib.log_run(
            args.thread_dir,
            "C5",
            "fetch",
            f"{pid} {status} {(row.get('title') or '')[:60]}",
        )
        print(f"{pid} [{status}] {(row.get('title') or '')[:60]}")
    if manual_rows:
        manual_path = os.path.join(
            args.thread_dir, "source", "manual", f"人工补缺-round{tag}.tsv"
        )
        try:
            _write_rows(
                manual_path,
                ["paper_id", "title", "authors", "year", "venue", "doi", "url", "说明"],
                manual_rows,
            )
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 1
    print(
        f"采集汇总：ok={c['ok']} abstract_only={c['abstract_only']} "
        f"manual_needed={c['manual_needed']} excluded={c['excluded']} "
        f"库内跳过={c['skipped_dup']}"
    )
    print(
        "PDF 目录：" + os.path.join(args.thread_dir, "source", "papers", "round" + tag)
    )
    if manual_rows:
        print(f"人工补缺清单：{manual_path}")
    return 0


def _collect_manual(args, lib):
    tag = lib.round_tag(args.round)
    src_dir = os.path.join(args.thread_dir, "source", "manual", "round" + tag)
    dst_dir = os.path.join(args.thread_dir, "source", "papers", "round" + tag)
    if not os.path.isdir(src_dir):
        print(f"未找到目录 {src_dir}，无待配对文件。")
        return 0
    try:
        os.makedirs(dst_dir, exist_ok=True)
        files = sorted(f for f in os.listdir(src_dir) if PDF_RE.match(f))
    except OSError as e:
        print(f"扫描目录失败 {src_dir}: {e}", file=sys.stderr)
        return 1
    lib_db = lib.load_library(args.thread_dir)
    matched, no_row, upd_fail = [], [], []
    for f in files:
        pid = f[:-4].upper()
        row = next(
            (p for p in lib_db if (p.get("paper_id") or "").upper() == pid), None
        )
        if row is None:
            no_row.append(f)
            continue
        shutil.copy2(os.path.join(src_dir, f), os.path.join(dst_dir, pid + ".pdf"))
        rel = os.path.join("source", "papers", "round" + tag, pid + ".pdf")
        if lib.update_library_row(
            args.thread_dir,
            pid,
            pdf_path=rel,
            fetch_status="ok",
            parse_quality="pending",
        ):
            matched.append(pid)
        else:
            upd_fail.append(f)
    print(f"人工补缺配对：扫描 {len(files)} 个 PDF，配对成功 {len(matched)} 个")
    if no_row:
        print("库中无对应 paper_id（未处理）：" + ", ".join(no_row))
    if upd_fail:
        print("更新库失败：" + ", ".join(upd_fail))
    lib.log_run(
        args.thread_dir,
        "C5",
        "collect-manual",
        f"round{tag} 配对 {len(matched)}/{len(files)}",
    )
    return 0


def main(argv=None):
    args = _parse_args(argv)
    if not os.path.isdir(args.thread_dir):
        print(f"线程目录不存在：{args.thread_dir}", file=sys.stderr)
        return 1
    try:
        import literature_review_lib as lib
    except ImportError as e:
        print(f"缺少公共库 literature_review_lib.py（需与脚本同目录）：{e}", file=sys.stderr)
        return 1
    lib.fix_encoding()
    lib.ensure_paths(args.thread_dir)
    if args.collect_manual:
        return _collect_manual(args, lib)
    cand_path = args.candidates
    if cand_path and not os.path.isabs(cand_path):
        cand_path = os.path.join(args.thread_dir, cand_path)
    if not cand_path or not os.path.isfile(cand_path):
        print(f"候选文件不存在：{cand_path}", file=sys.stderr)
        return 1
    try:
        import literature_review_verify as verify
    except ImportError as e:
        print(f"缺少校验模块 literature_review_verify.py（需与脚本同目录）：{e}", file=sys.stderr)
        return 1
    return _process(args, cand_path, lib, verify)


if __name__ == "__main__":
    sys.exit(main())

