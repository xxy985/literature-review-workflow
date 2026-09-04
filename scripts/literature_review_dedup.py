#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选去重与库内自检报告（综述半自动工作流，走廊 C5：库管理与去重）。

输入：
  <thread_dir> --candidates <tsv>
    —— 候选去重（对库内+候选内部 doi/归一化标题），输出 <原名>.去重后.tsv 并打印计数；
       原候选文件不改动。
  <thread_dir>（无 --candidates 时默认；或加 --report 与候选去重同时输出）
    —— 库内自检报告：artifacts/03-library/去重报告-<日期>.md。
       列 DOI 相同组、标题归一化相同组、arXiv 镜像与正式版同题组；只报告不删行。

依赖：同目录公共库脚本；无第三方依赖。
退出码：0 成功；1 运行失败；2 参数错误。
"""
import argparse
import csv
import datetime
import os
import sys


def _parse_args(argv):
    p = argparse.ArgumentParser(description='候选去重；或库内重复自检报告（只报告不删行）')
    p.add_argument('thread_dir', help='工作线程根目录')
    p.add_argument('--candidates', default='',
                   help='候选 TSV 路径（相对 thread_dir 或绝对路径）')
    p.add_argument('--report', action='store_true',
                   help='同时输出库内自检报告（无 --candidates 时默认执行）')
    return p.parse_args(argv)


def _fix_encoding():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


def _read_rows(path):
    with open(path, encoding='utf-8', newline='') as fh:
        rd = csv.DictReader(fh, delimiter='\t')
        return rd.fieldnames or [], [dict(r) for r in rd]


def _write_rows(path, cols, rows):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh, delimiter='\t', lineterminator='\n')
        wr.writerow(cols)
        for r in rows:
            wr.writerow([r.get(k, '') for k in cols])


def _dedup_candidates(thread_dir, cand_path, lib):
    if not os.path.isabs(cand_path):
        cand_path = os.path.join(thread_dir, cand_path)
    if not os.path.isfile(cand_path):
        print('候选文件不存在：%s' % cand_path, file=sys.stderr)
        return 1
    cols, rows = _read_rows(cand_path)
    if 'doi' not in cols or 'title' not in cols:
        print('候选文件缺少 doi/title 列，无法去重', file=sys.stderr)
        return 1
    lib_db = lib.load_library(thread_dir)
    lib_dois = {(p.get('doi') or '').strip().lower() for p in lib_db
                if (p.get('doi') or '').strip()}
    lib_titles = {lib.normalize_title(p.get('title') or '') for p in lib_db
                  if (p.get('title') or '').strip()}
    seen_dois, seen_titles = set(), set()
    out, n_lib, n_dup, dropped_lib = [], 0, 0, []
    for r in rows:
        doi = (r.get('doi') or '').strip().lower()
        t = lib.normalize_title(r.get('title') or '')
        if (doi and doi in lib_dois) or (t and t in lib_titles):
            n_lib += 1
            if len(dropped_lib) < 20:
                dropped_lib.append('%s（%s）' % ((r.get('title') or ''), doi or '无DOI'))
            continue
        if (doi and doi in seen_dois) or (t and t in seen_titles):
            n_dup += 1
            continue
        if doi:
            seen_dois.add(doi)
        if t:
            seen_titles.add(t)
        out.append(r)
    stem = cand_path[:-4] if cand_path.lower().endswith('.tsv') else cand_path
    out_path = stem + '.去重后.tsv'
    _write_rows(out_path, cols, out)
    lib.log_run(thread_dir, 'C5', 'dedup-candidates', '%d->%d' % (len(rows), len(out)))
    print('候选去重：输入 %d 行，库内已有 %d 行，文件内重复 %d 行，去重后保留 %d 行'
          % (len(rows), n_lib, n_dup, len(out)))
    if dropped_lib:
        print('库内已有示例：' + '；'.join(dropped_lib))
    print('已写入 %s' % out_path)
    return 0


def _fmt_row(p):
    return '- %s | %s | fetch=%s | source=%s | xref=%s' % (
        p.get('paper_id') or '?',
        (p.get('title') or '')[:60].replace('\n', ' '),
        p.get('fetch_status') or '',
        p.get('source') or '',
        p.get('xref_verified') or '')


def _doi_groups(lib_db):
    groups = {}
    for p in lib_db:
        k = (p.get('doi') or '').strip().lower()
        if k:
            groups.setdefault(k, []).append(p)
    out = ['## 一、DOI 完全相同', '']
    found = False
    for k in sorted(groups):
        g = groups[k]
        if len(g) < 2:
            continue
        found = True
        out.append('### %s' % (g[0].get('doi') or k))
        out.extend(_fmt_row(p) for p in g)
        out.append('')
    if not found:
        out += ['未发现 DOI 相同的行。', '']
    return out


def _title_groups(lib_db, lib):
    groups = {}
    for p in lib_db:
        t = lib.normalize_title(p.get('title') or '')
        if t:
            groups.setdefault(t, []).append(p)
    out = ['## 二、标题归一化后相同（DOI 不同或无 DOI）', '']
    found = False
    for t in sorted(groups):
        g = groups[t]
        if len(g) < 2 or len({(p.get('doi') or '') for p in g}) < 2:
            continue
        found = True
        out.append('### %s' % (g[0].get('title') or '')[:60])
        out.extend(_fmt_row(p) for p in g)
        out.append('')
    if not found:
        out += ['未发现标题相同、DOI 不同的行。', '']
    return out


def _mirror_groups(lib_db, lib):
    out = ['## 三、arXiv 镜像与正式版同题', '']
    mirrors, formals = {}, {}
    for p in lib_db:
        t = lib.normalize_title(p.get('title') or '')
        if not t:
            continue
        if (p.get('source') or '') == 'arxiv-mirror':
            mirrors.setdefault(t, []).append(p)
        else:
            formals.setdefault(t, []).append(p)
    found = False
    for t in sorted(mirrors):
        if t not in formals:
            continue
        found = True
        mlist = mirrors[t]
        out.append('### %s' % (mlist[0].get('title') or '')[:60])
        out.extend(_fmt_row(p) for p in mlist + formals[t])
        out.append('建议：镜像行复核后归档；正式版行（xref_verified=True）优先保留。')
        out.append('')
    if not found:
        out += ['未发现 arXiv 镜像与正式版同题的记录。', '']
    out += ['## 建议', '',
            '- 同一 DOI 多行时保留 xref_verified=True 且数据最全的一行，其余人工复核。',
            '- 本工具红线：只报告，不自动删除任何行。',
            '']
    return out


def _library_report(thread_dir, lib):
    lib_db = lib.load_library(thread_dir)
    today = datetime.date.today()
    lines = ['# 库内去重自检报告（%s）' % today.strftime('%Y-%m-%d'), '',
             '说明：本报告只列疑似重复，不自动删除、不修改任何行；仅作人工复核依据。', '']
    lines += _doi_groups(lib_db)
    lines += _title_groups(lib_db, lib)
    lines += _mirror_groups(lib_db, lib)
    out_path = os.path.join(thread_dir, 'artifacts', '03-library',
                            '去重报告-%s.md' % today.strftime('%Y%m%d'))
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    lib.log_run(thread_dir, 'C5', 'dedup-report', '库内 %d 行自检' % len(lib_db))
    print('库内 %d 行自检完成，报告：%s' % (len(lib_db), out_path))
    return 0


def main(argv=None):
    args = _parse_args(argv)
    _fix_encoding()
    if not os.path.isdir(args.thread_dir):
        print('线程目录不存在：%s' % args.thread_dir, file=sys.stderr)
        return 1
    try:
        import literature_review_lib as lib
    except ImportError as e:
        print('缺少公共库 literature_review_lib.py（需与脚本同目录）：%s' % e, file=sys.stderr)
        return 1
    lib.ensure_paths(args.thread_dir)
    do_report = args.report or not args.candidates
    if args.candidates:
        rc = _dedup_candidates(args.thread_dir, args.candidates, lib)
        if rc:
            return rc
    if do_report:
        return _library_report(args.thread_dir, lib)
    return 0


if __name__ == '__main__':
    sys.exit(main())

