#!/usr/bin/env python3
"""验收与审计（多子命令）：状态、轮报告、库体检、稿 diff、引用审计、改读、重置。

用法（<工作根目录> 必填，子命令择一）：
  python literature_review_check.py <根> --corridor            # 状态块+计数+下一步提示（只读）
  python literature_review_check.py <根> --advance C2         # 门通过后推进走廊（清 gate/blocked_on）
  python literature_review_check.py <根> --at-gate 门2        # 停门登记（写 gate + blocked_on=user）
  python literature_review_check.py <根> --round N|X           # 轮验收报告（stdout+落盘 03-library）
  python literature_review_check.py <根> --full                # 库体检（字段/重复/孤儿/核验断言）
  python literature_review_check.py <根> --diff <旧md> <新md>   # 修改日志（落在新文件旁）
  python literature_review_check.py <根> --cite-audit <md> [--strict]
  python literature_review_check.py <根> --mark-read <pid> --contribution "一句话" [--evidence A|B]
  python literature_review_check.py <根> --reset-attempt       # 抛弃重来：attempt+1，回 C1
状态写入：--checkpoint FILE / --at-gate / --advance / --reset-attempt。
引用审计可加 --report FILE 保存新版本报告。--round 未通过返回2。
--full 核验断言（exit 1 失败）：全库 xref_verified=true；排除账无回灌
（DOI+题名双键，逆转行不计）；库内预印本信号独立扫描零命中。
退出码：0 正常；1 输入/数据错误；2 --strict 审计不通过（未知引用）。
"""

import argparse
import datetime
import difflib
import json
import os
import re
import sys
from urllib.parse import urlparse

PID_RE = re.compile(r"\[doi:([^\]\s]+)\]", re.I)

NEXT_HINT = {
    "C1": "C1（定方向）：设计 3-5 组检索式 → literature_review_search → 候选池报告 → 停 门1（检索方案确认）",
    "C2": "C2（首轮推荐）：推荐 10 篇 → fetch 下载 → convert 转 md → 逐篇精读 → 判断总轮数与主题漂移 → 停 门2（首轮语料批准）",
    "C3": "C3（滚动+扩圈+建库+提纲）：滚动轮至 40 → cite 扩圈 20 → 精读补齐 → check --round/--full 常规汇报 → 拟提纲（提纲意见并入门3）",
    "C4": "C4（写作要求）：拟写作要求文档（结构/长度/引用密度/时态）→ 随初稿一并交门3",
    "C5": "C5（初稿）：按提纲与 60 篇库写初稿，每节 ≥3 篇支撑 → 引用边界报告 → 停 门3（初稿与引用边界确认）",
    "C6": "C6（多轮修改）：意见清单 → 改后稿 vN → check --diff 出修改日志 → 逐条销项 → 每轮结束自然汇报",
    "C7": "C7（助理交接）：to_docx 转出 + 交接说明 → 等助理回件（blocked_on=jiaozi，无门）",
    "C8": "C8（终稿）：from_docx 回转 → 审内容 → 指定格式成稿 → cite-audit --strict → 交付包 → 停 门4（终稿验收）",
}


def _parse_args(argv):
    p = argparse.ArgumentParser(description="literature-review-workflow 验收与审计")
    p.add_argument("work_dir", help="工作根目录")
    p.add_argument("--corridor", action="store_true", help="状态+计数+下一步提示")
    p.add_argument(
        "--advance", default="", metavar="C#", help="门通过后推进到走廊 C1-C8（清 gate/blocked_on）"
    )
    p.add_argument(
        "--at-gate", default="", metavar="GATE", help="停门登记：写 gate 与 blocked_on=user"
    )
    p.add_argument("--round", default="", help="轮次编号（1-8 或 X）")
    p.add_argument("--full", action="store_true", help="库体检")
    p.add_argument(
        "--diff", nargs=2, metavar=("OLD", "NEW"), help="新旧稿对比出修改日志"
    )
    p.add_argument("--cite-audit", default="", metavar="FILE", help="引用审计")
    p.add_argument("--strict", action="store_true", help="未知引用即失败（exit 2）")
    p.add_argument("--mark-read", default="", metavar="PID", help="标记精读")
    p.add_argument("--contribution", default="", help="一句话贡献（--mark-read 必填）")
    p.add_argument(
        "--evidence", default="A", choices=["A", "B"], help="证据级（默认 A 全文）"
    )
    p.add_argument("--reset-attempt", action="store_true", help="抛弃重来")
    p.add_argument("--checkpoint", metavar="JSON", help="合并检查点文件（相对工作根目录）")
    p.add_argument("--report", metavar="FILE", help="引用审计报告落盘路径（相对工作根目录）")
    p.add_argument("--require-fulltext", type=int, default=0, help="轮验收所需全文数")
    args = p.parse_args(argv)
    actions = [args.corridor, args.advance, args.at_gate, args.round, args.full,
               args.diff, args.cite_audit, args.mark_read, args.reset_attempt, args.checkpoint]
    if sum(bool(x) for x in actions) != 1:
        p.error("必须且只能选择一个子命令")
    if args.require_fulltext < 0:
        p.error("--require-fulltext 不可为负数")
    return args


def _write_report(path, lines):
    body = "\n".join(lines) + "\n"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "x", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
    except OSError as e:
        raise RuntimeError(f"写报告失败 {path}: {e}") from e


def _report_path(path):
    """保留历次验收依据，恢复时不能用新报告替换旧检查点的目标。"""
    stem, ext = os.path.splitext(path)
    version = 2
    candidate = path
    while os.path.exists(candidate):
        candidate = f"{stem}-v{version}{ext}"
        version += 1
    return candidate


def _read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"读取失败 {path}: {e}") from e


def _dist(rows, field):
    counts = {}
    for r in rows:
        k = r.get(field) or ""
        counts[k] = counts.get(k, 0) + 1
    return counts


def _fmt_dist(dist):
    if not dist:
        return "（空）"
    return "，".join(
        f"{k or '空'}={v}" for k, v in sorted(dist.items(), key=lambda x: -x[1])
    )


# 预印本 DOI 注册前缀（独立扫描信号，2026-09-05 评审 R2-B1）
PREPRINT_DOI_PREFIXES = (
    "10.48550/",  # arXiv
    "10.1101/",  # bioRxiv / medRxiv
    "10.20944/",  # Preprints.org
    "10.21203/",  # Research Square
    "10.26434/",  # ChemRxiv
    "10.31219/",  # PsyArXiv
)


def _preprint_hits(rows, lib):
    """独立扫描库内预印本信号：DOI 注册前缀 + venue/URL 预印本域名。

    不再依赖“核验管线挡入+无回灌”的推断链（2026-09-05 评审 R2-B1）。命中即出
    每篇定位与信号来源，供人工复核；空 DOI 的记录不跳过。
    """
    import literature_review_verify as verify

    hits = []
    for r in rows:
        d = (r.get("doi") or "").strip().lower()
        if d.startswith(PREPRINT_DOI_PREFIXES):
            hits.append(f"{r.get('doi', '?')}（DOI 前缀 {d.split('/')[0]}）")
            continue
        url = (r.get("url") or "").lower()
        host = urlparse(url).hostname or ""
        verified = str(r.get("xref_verified") or "").lower() in ("true", "1")
        # 正式DOI的全文可托管在arXiv；出版场所仍独立检查。
        formal_mirror = bool(d and verified and (host == "arxiv.org" or host.endswith(".arxiv.org")))
        hay = f"{r.get('venue') or ''} {'' if formal_mirror else url}".lower()
        matched = [h for h in verify.PREPRINT_HOSTS if h in hay]
        if matched:
            hits.append(
                f"{r.get('doi', '?')}（venue/URL 命中 {'、'.join(matched)}）"
            )
    return hits


def corridor(args, lib):
    state = lib.read_state(args.work_dir)
    if not state:
        print("progress.md 无状态块：先 literature_review_new.py 自举。", file=sys.stderr)
        return 1
    counts = lib.paper_counts(args.work_dir)
    print("== 状态 ==")
    print(f"theme: {state.get('theme', '')}")
    print(
        f"attempt: {state.get('attempt')}  corridor: {state.get('corridor')}  "
        f"gate: {state.get('gate') or '-'}  blocked_on: {state.get('blocked_on') or '-'}"
    )
    rp = state.get("rounds", {})
    pp = state.get("papers", {})
    print(f"rounds: planned={rp.get('planned')} completed={rp.get('completed')}")
    print(
        f"papers: ok={counts.get('fulltext', 0)} abstract_only={counts.get('abstract_only', 0)} "
        f"manual_needed={counts.get('manual_needed', 0)} excluded={counts.get('excluded', 0)} "
        f"(库计数=事实，状态块快照 target={pp.get('target')} expand={pp.get('expand_target')})"
    )
    hint = NEXT_HINT.get(state.get("corridor", ""))
    if state.get("blocked_on"):
        print(f"⛔ blocked_on={state.get('blocked_on')}（恢复流程见状态快照）")
    elif hint:
        print(f"下一步：{hint}")
    return 0


def round_report(args, lib):
    rw = args.round.strip().upper()
    try:
        rw = "X" if rw == "X" else str(int(rw))
        lib.round_tag(rw)
    except (ValueError, RuntimeError):
        raise RuntimeError("--round 需为1-99或X")
    rows = lib.load_library(args.work_dir)
    picked = [r for r in rows if (r.get("round") or "").strip().upper() == rw]
    lines = [
        f"# 轮验收报告 round {rw}",
        f"生成：{datetime.date.today().isoformat()}",
        f"库内本批篇数：{len(picked)}",
        "",
    ]
    lines += [
        f"- fetch_status：{_fmt_dist(_dist(picked, 'fetch_status'))}",
        f"- parse_quality：{_fmt_dist(_dist(picked, 'parse_quality'))}",
        f"- is_read：{sum(1 for r in picked if r.get('is_read') == '1')}/{len(picked)}",
        f"- 证据级：{_fmt_dist(_dist(picked, 'evidence'))}",
        "",
    ]
    missing_md = [
        r["doi"]
        for r in picked
        if r.get("fetch_status") == "ok" and (
            not r.get("md_path") or not os.path.isfile(os.path.join(args.work_dir, r["md_path"])))
    ]
    if missing_md:
        lines.append(f"⚠ ok 但无 md（convert 未跑？）：{'、'.join(missing_md)}")
    eligible = [r for r in picked if r.get("fetch_status") in ("ok", "abstract_only")]
    unread = [r["doi"] for r in eligible if r.get("is_read") != "1"]
    if unread:
        lines.append(f"○ 未精读：{len(unread)} 篇")
    lines.append("")
    gate_ok = (
        len(eligible) > 0
        and not missing_md
        and not unread
        and all(r.get("evidence") in ("A", "B") for r in eligible)
        and not any(r.get("parse_quality") in ("low", "failed", "pending", "")
                    for r in picked if r.get("fetch_status") == "ok")
        and sum(r.get("fetch_status") == "ok" for r in picked) >= args.require_fulltext
    )
    lines.append(
        f"结论：轮验收{'通过' if gate_ok else '未通过'}（有效条目的精读、解析与所需全文数）"
        f"（当前 {sum(1 for r in picked if r.get('fetch_status') == 'ok')}/{len(picked)}）"
    )
    name = f"round{rw.upper()}-验收.md"
    lines.append("待人工补缺条目单列，不占有效语料名额；A/B比例供判断，不设隐藏比例门槛。")
    out = _report_path(os.path.join(args.work_dir, "artifacts", "03-library", name))
    try:
        _write_report(out, lines)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    print("\n".join(lines))
    print(f"报告落盘：{out}")
    return 0 if gate_ok else 2


def full_exam(args, lib):
    rows = lib.load_library(args.work_dir)
    lines = [
        "# 库体检报告",
        f"生成：{datetime.date.today().isoformat()}",
        f"库内总数：{len(rows)}",
        "空库不能通过体检。" if not rows else "核验范围：当前全局库。",
        "",
    ]
    for field in ("doi", "year", "venue", "title", "authors"):
        empty = sum(1 for r in rows if not (r.get(field) or "").strip())
        pct = 100 * (len(rows) - empty) / len(rows) if rows else 0
        lines.append(f"- {field} 非空率：{pct:.0f}%（空 {empty}）")
    doi_map = {}
    title_map = {}
    for r in rows:
        d = (r.get("doi") or "").strip().lower()
        if d:
            doi_map.setdefault(d, []).append(r["doi"])
        t = lib.normalize_title(r.get("title") or "")
        if t:
            title_map.setdefault(t, []).append(r["doi"])
    dup_doi = {k: v for k, v in doi_map.items() if len(v) > 1}
    dup_title = {k: v for k, v in title_map.items() if len(v) > 1}
    lines += [
        "",
        f"- DOI 重复组：{len(dup_doi)}"
        + (
            "；" + "；".join(f"{k}: {'、'.join(v)}" for k, v in dup_doi.items())
            if dup_doi
            else ""
        ),
        f"- 标题重复组：{len(dup_title)}"
        + (
            "；" + "；".join(f"{'、'.join(v)}" for _k, v in dup_title.items())
            if dup_title
            else ""
        ),
        f"- fetch_status：{_fmt_dist(_dist(rows, 'fetch_status'))}",
        f"- 证据级：{_fmt_dist(_dist(rows, 'evidence'))}",
        f"- 精读率：{sum(1 for r in rows if r.get('is_read') == '1')}/{len(rows)}",
        "",
    ]
    # 核验断言（决策记录 2026-09-04）：全库 xref_verified=true 且预印本零入库
    unverified = [
        r["doi"]
        for r in rows
        if (r.get("xref_verified") or "").strip().lower() not in ("1", "true")
    ]
    try:
        excluded = lib.load_excluded(args.work_dir)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    # 排除账为追加式账本：同一键后写的 withdrawn 侧行撤销先前排除（旧行不删）。
    # 键 = DOI（有 DOI 为先）；DOI 为空的排除记录以归一化题名为备用键
    # （2026-09-05 评审 R2-B2：仅按 DOI 检回漏掉“无 DOI 排除后回库”路径）。
    ex_doi_state = {}
    ex_title_state = {}
    for e in excluded:
        wd = str(e.get("reason") or "").strip().lower().startswith("withdrawn")
        d = (e.get("doi") or "").strip().lower()
        t = lib.normalize_title(e.get("title") or "")
        if d:
            ex_doi_state[d] = wd
        elif t:
            ex_title_state[t] = wd
    active_doi = {d for d, wd in ex_doi_state.items() if not wd}
    active_title = {t for t, wd in ex_title_state.items() if not wd}
    backflow = []
    for r in rows:
        d = (r.get("doi") or "").strip().lower()
        t = lib.normalize_title(r.get("title") or "")
        keys = []
        if d and d in active_doi:
            keys.append("DOI")
        if t and t in active_title:
            keys.append("题名")
        if keys:
            backflow.append(f"{r.get('doi', '?')}（{'、'.join(keys)}）")
    pp_hits = _preprint_hits(rows, lib)
    lines += [
        "",
        "## 核验断言（全库已核验 / 排除账无回灌 / 预印本零入库）",
        "- xref_verified 全库通过："
        + ("✓" if not unverified else "⛔ 未核验：" + "、".join(unverified)),
        "- 排除账回灌（DOI+题名双键，逆转行不计）："
        + (
            "✓ 无（排除后未回库）"
            if not backflow
            else "⛔ 排除后回灌：" + "、".join(backflow)
        ),
        "- 预印本零入库（独立扫描：DOI 注册前缀 + venue/URL 预印本域名）："
        + (
            "✓ 无命中"
            if not pp_hits
            else "⛔ 疑似命中（人工复核）：" + "、".join(pp_hits)
        ),
    ]
    orphans = []
    base = os.path.join(args.work_dir, "source", "papers")
    try:
        for sub in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            subp = os.path.join(base, sub)
            if not os.path.isdir(subp) or not sub.startswith("round"):
                continue
            for f in os.listdir(subp):
                from urllib.parse import unquote
                pid = lib.normalize_doi(unquote(os.path.splitext(f)[0]))
                if pid not in {r["doi"] for r in rows}:
                    orphans.append(f"{sub}/{f}")
    except OSError as e:
        print(f"扫描论文目录失败：{e}", file=sys.stderr)
        return 1
    if orphans:
        lines.append(
            f"⚠ 无库行文件（{len(orphans)}）："
            + "、".join(orphans[:20])
            + ("…" if len(orphans) > 20 else "")
        )
    else:
        lines.append("- 无孤儿文件（PDF 目录与库一致）")
    out = _report_path(os.path.join(
        args.work_dir,
        "artifacts",
        "03-library",
        f"库体检-{datetime.date.today().strftime('%Y%m%d')}.md",
    ))
    policy_bad = [r.get("doi", "?") for r in rows if
                  not lib.normalize_doi(r.get("doi")) or
                  r.get("norm_type") not in ("journal-article", "proceedings-article", "book", "book-chapter") or
                  r.get("review_field") not in ("computer-science", "other") or
                  (r.get("norm_type") == "proceedings-article" and r.get("review_field") != "computer-science")]
    lines.append("- DOI/领域准入：" + ("失败：" + "、".join(policy_bad) if policy_bad else "通过"))
    try:
        _write_report(out, lines)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    print("\n".join(lines))
    print(f"报告落盘：{out}")
    if not rows or unverified or backflow or pp_hits or policy_bad or dup_doi:
        print(
            "⛔ 核验断言未通过（见报告“核验断言”节），以退出码 1 失败。",
            file=sys.stderr,
        )
        return 1
    return 0


def diff_report(args, lib, old, new):
    try:
        a = _read_text(old).splitlines()
        b = _read_text(new).splitlines()
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    added = deleted = changed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag in ("insert",):
            added += j2 - j1
        elif tag in ("delete",):
            deleted += i2 - i1
        else:
            changed += max(i2 - i1, j2 - j1)
    today = datetime.date.today().isoformat()
    lines = [
        f"# 修改日志：{os.path.basename(new)}",
        f"基线：{os.path.basename(old)}   生成：{today}",
        "",
        f"- 新增行：{added}",
        f"- 删除行：{deleted}",
        f"- 改动行（对齐后较大侧）：{changed}",
        "",
        "## 统一 diff（前 400 行）",
        "",
    ]
    diff_lines = list(
        difflib.unified_diff(
            a,
            b,
            fromfile=os.path.basename(old),
            tofile=os.path.basename(new),
            lineterm="",
        )
    )
    lines += diff_lines[:400]
    if len(diff_lines) > 400:
        lines.append(f"…（截断，共 {len(diff_lines)} 行 diff）")
    out = _report_path(os.path.join(
        os.path.dirname(os.path.abspath(new)),
        os.path.splitext(os.path.basename(new))[0] + "-修改日志.md",
    ))
    try:
        _write_report(out, lines)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    print("\n".join(lines[:20]))
    print(f"…修改日志落盘：{out}")
    print("注意：日志是事实记录；逐条销项判断由 AI 按 SKILL.md 执行，不凭记忆。")
    return 0


def cite_audit(args, lib, path):
    target = path if os.path.isabs(path) else os.path.join(args.work_dir, path)
    try:
        text = _read_text(target)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    found = [lib.normalize_doi(d) or d for d in PID_RE.findall(text)]
    counts = {}
    for pid in found:
        counts[pid] = counts.get(pid, 0) + 1
    rows = lib.load_library(args.work_dir)
    known = {r["doi"]: r for r in rows}
    unknown = sorted(p for p in counts if p not in known)
    b_used = sorted(
        p for p, r in known.items() if p in counts and (r.get("evidence") or "A") == "B"
    )
    print(f"== 引用审计：{os.path.basename(target)} ==")
    print(
        f"引用的库内论文：{len(counts) - len(unknown)} 种，总出现 {sum(counts.values())} 次"
    )
    if unknown:
        print(f"✗ 未知 doi（库中无行）{len(unknown)} 个：{'、'.join(unknown)}")
    if b_used:
        print(f"! 摘要级（B）引用 {len(b_used)} 种：{'、'.join(b_used)}")
        print(
            "  提醒：B 级仅可支撑非核心论点（D2 拍板）；是否合规由 AI/用户判断，"
            "最终文章不出现标记。"
        )
    unready = sorted(p for p in counts if p in known and (
        known[p].get("is_read") != "1" or known[p].get("evidence") not in ("A", "B")
        or (known[p].get("evidence") == "A" and known[p].get("fetch_status") != "ok")))
    lines = [f"# 引用机械审计：{os.path.basename(target)}",
             f"识别引用种类：{len(counts)}", f"未知编号：{', '.join(unknown) or '无'}",
             f"未完成阅读或证据状态不完整：{', '.join(unready) or '无'}",
             f"摘要级引用：{', '.join(b_used) or '无'}",
             "本检查只验证编号与阅读状态，不证明论文支持对应论断。"]
    if not counts:
        lines.append("未识别到 doi，不能认定引用通过；请审计保留编号的工作稿。")
    if not unknown and not unready and counts:
        lines.append("编号与阅读状态检查通过；仍需按 claim-review.md 核回原文。")
    print("\n".join(lines))
    if args.report:
        report = args.report if os.path.isabs(args.report) else os.path.join(args.work_dir, args.report)
        if os.path.exists(report):
            raise RuntimeError("报告已存在，请使用新版本文件名：" + report)
        _write_report(report, lines)
    if (unknown or unready or not counts) and args.strict:
        return 2
    return 0


def mark_read(args, lib):
    if not args.contribution.strip():
        print("--contribution 必填（一句话贡献）", file=sys.stderr)
        return 1
    args.mark_read = lib.normalize_doi(args.mark_read)
    row = next((r for r in lib.load_library(args.work_dir) if r.get("doi") == args.mark_read), None)
    if row and args.evidence == "A":
        md = row.get("md_path") or ""
        if (row.get("fetch_status") != "ok" or not md
                or row.get("parse_quality") in ("low", "failed", "pending", "")
                or not os.path.isfile(os.path.join(args.work_dir, md))):
            print("A 级需已取得全文并有可读转换文件。", file=sys.stderr)
            return 1
    try:
        hit = lib.update_library_row(
            args.work_dir,
            args.mark_read,
            is_read=1,
            contribution=args.contribution.strip(),
            evidence=args.evidence,
        )
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    if not hit:
        print(f"库中无此 doi：{args.mark_read}", file=sys.stderr)
        return 1
    if args.evidence == "B":
        print("注意：B=摘要级引用，仅支撑非核心论点（D2），终稿不加标记。")
    print(f"✓ {args.mark_read} 已标记精读（evidence={args.evidence}）")
    return 0


def at_gate(args, lib):
    gate = args.at_gate.strip()
    if gate not in ("门1", "门2", "门3", "门4"):
        print("--at-gate 只接受 门1 至 门4", file=sys.stderr)
        return 1
    state = lib.read_state(args.work_dir)
    if not state:
        print("progress.md 无状态块：先 literature_review_new.py 自举。", file=sys.stderr)
        return 1
    corridor = state.get("corridor", "")
    try:
        lib.write_state(args.work_dir, gate=gate, blocked_on="user")
        lib.log_run(args.work_dir, corridor, "at-gate", f"停门 {gate}（blocked_on=user）")
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"✓ 已登记停门 {gate}（corridor={corridor}，blocked_on=user）。")
    return 0


def advance(args, lib):
    target = args.advance.strip().upper()
    if target not in NEXT_HINT:
        print(f"未知走廊：{args.advance}（合法值 C1-C8）", file=sys.stderr)
        return 1
    state = lib.read_state(args.work_dir)
    if not state:
        print("progress.md 无状态块：先 literature_review_new.py 自举。", file=sys.stderr)
        return 1
    old = state.get("corridor", "")
    try:
        lib.write_state(args.work_dir, corridor=target, gate="", blocked_on="")
        lib.log_run(args.work_dir, target, "advance", f"{old} -> {target}（门通过）")
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"✓ corridor {old or '-'} → {target}（gate/blocked_on 已清空）。")
    hint = NEXT_HINT.get(target)
    if hint:
        print(f"下一步：{hint}")
    return 0


def reset_attempt(args, lib):
    state = lib.read_state(args.work_dir)
    if not state:
        print("progress.md 无状态块：先 literature_review_new.py 自举。", file=sys.stderr)
        return 1
    old = state.get("attempt", 1)
    try:
        lib.write_state(
            args.work_dir,
            attempt=old + 1,
            corridor="C1",
            gate="",
            blocked_on="",
            weak_dimensions=[], pending_decisions=[],
            checkpoint={}, theme_boundary="",
            rounds={
                "planned": state.get("rounds", {}).get("planned", 4),
                "completed": 0,
            },
        )
        lib.log_run(
            args.work_dir,
            "C1",
            "reset-attempt",
            f"attempt {old} -> {old + 1}（文件不删不移已下载共享）",
        )
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"✓ attempt {old} → {old + 1}，corridor 回 C1。")
    print("已下载 PDF 与库行保留复用（fetch 去重已按 DOI/标题挡掉重复）。")
    return 0


def checkpoint(args, lib):
    """接收显式白名单字段，数据计数由账本派生，不提供任意状态执行入口。"""
    path = args.checkpoint if os.path.isabs(args.checkpoint) else os.path.join(args.work_dir, args.checkpoint)
    try:
        data = json.loads(_read_text(path))
    except ValueError as e:
        raise RuntimeError(f"检查点 JSON 无效：{e}") from e
    allowed = {"theme", "theme_boundary", "weak_dimensions", "rounds", "pending_decisions", "blocked_on", "checkpoint"}
    if not isinstance(data, dict) or not data or set(data) - allowed:
        raise RuntimeError("检查点为空或含未允许字段；不能改 corridor/gate/attempt/papers。")
    state = lib.read_state(args.work_dir)
    if not state:
        raise RuntimeError("请先自举工作根目录。")
    for key in ("theme", "theme_boundary"):
        if key in data and not isinstance(data[key], str):
            raise RuntimeError(key + " 必须是文本")
    for key in ("weak_dimensions", "pending_decisions"):
        if key in data and (not isinstance(data[key], list) or any(not isinstance(x, str) for x in data[key])):
            raise RuntimeError(key + " 必须是文本列表")
    if "blocked_on" in data and data["blocked_on"] not in ("", "user", "jiaozi", "environment"):
        raise RuntimeError("blocked_on 只允许空/user/jiaozi/environment")
    if "rounds" in data:
        r = data["rounds"]
        if not isinstance(r, dict) or set(r) - {"planned", "completed"} or any(type(v) is not int for v in r.values()):
            raise RuntimeError("rounds 只允许整数 planned/completed")
        r = dict(state.get("rounds", {}), **r)
        if not 4 <= r.get("planned", 0) <= 8 or not 0 <= r.get("completed", -1) <= 8:
            raise RuntimeError("planned 需为4-8，completed 需为0-8")
        data["rounds"] = r
    if "checkpoint" in data:
        c = data["checkpoint"]
        if not isinstance(c, dict) or set(c) != {"unit", "completed", "next_action", "artifacts", "block_reason"}:
            raise RuntimeError("checkpoint 必须含 unit/completed/next_action/artifacts/block_reason")
        if any(not isinstance(c[k], str) for k in ("unit", "next_action", "block_reason")):
            raise RuntimeError("检查点描述必须是文本")
        if any(not isinstance(c[k], list) or any(not isinstance(v, str) for v in c[k]) for k in ("completed", "artifacts")):
            raise RuntimeError("completed/artifacts 必须是文本列表")
        for relative in c["artifacts"]:
            base = os.path.realpath(args.work_dir)
            resolved = os.path.realpath(os.path.join(base, relative))
            if os.path.isabs(relative) or os.path.commonpath([base, resolved]) != base or not os.path.isfile(resolved):
                raise RuntimeError("产物应是工作根目录内已存在文件：" + relative)
    if state.get("gate") and data.get("blocked_on", "user") != "user":
        raise RuntimeError("停门期间不能清除等待；用户批准后使用 --advance。")
    data["papers"] = dict(state.get("papers", {}), **lib.paper_counts(args.work_dir))
    lib.write_state(args.work_dir, **data)
    print("检查点已保存；计数来自全局库，当前尝试纳入范围见恢复清单。")
    return 0


def main(argv=None):
    args = _parse_args(argv)
    import literature_review_lib as lib

    lib.fix_encoding()
    if not os.path.isdir(args.work_dir):
        print(f"工作根目录不存在：{args.work_dir}", file=sys.stderr)
        return 1
    try:
        if args.checkpoint:
            return checkpoint(args, lib)
        if args.corridor:
            return corridor(args, lib)
        if args.round:
            return round_report(args, lib)
        if args.full:
            return full_exam(args, lib)
        if args.diff:
            return diff_report(args, lib, args.diff[0], args.diff[1])
        if args.cite_audit:
            return cite_audit(args, lib, args.cite_audit)
        if args.at_gate:
            return at_gate(args, lib)
        if args.advance:
            return advance(args, lib)
        if args.mark_read:
            return mark_read(args, lib)
        if args.reset_attempt:
            return reset_attempt(args, lib)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(
        "未指定子命令。可选：--corridor / --advance C# / --at-gate GATE / --round N|X / --full / --diff OLD NEW / "
        "--cite-audit FILE [--strict] / --mark-read PID --contribution TXT / --reset-attempt"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
