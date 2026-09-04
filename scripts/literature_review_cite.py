#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引用扩圈：沿库内种子文献的引用/被引边发现新候选（走廊 C3：扩圈检索）。

输入：<thread_dir> --target 20 [--mode refs|cited|both] [--year-min 2000]
      [--per-page-cap 200]
种子：库内 xref_verified 且 fetch_status∈{ok, abstract_only} 的行。
输出：artifacts/03-library/扩圈候选-<日期>.tsv
      （search 列 + score,cooccur,in_related；来源边统计打印到 stdout）。
不自动入库：后续用下载管线 --candidates 处理同一文件。

依赖：同目录公共库脚本与校验模块（白名单类型）；无第三方依赖。
退出码：0 成功；1 运行失败；2 参数错误。
"""
import argparse
import csv
import datetime
import math
import os
import sys

OA_BASE = 'https://api.openalex.org/works'
SEL_ID = 'id,referenced_works,related_works'
SEL_META = ('id,doi,title,publication_year,cited_by_count,type,'
            'primary_location,open_access,authorships')
OUT_COLS = ['title', 'authors', 'year', 'venue', 'doi', 'url', 'oa', 'abstract',
            'source_db', 'native_id', 'type', 'score', 'cooccur', 'in_related']
WEIGHTS = {'cooccur': 0.4, 'cited': 0.3, 'year': 0.2, 'related': 0.1}
PREPRINT_HOSTS = ('arxiv.org', 'biorxiv.org', 'medrxiv.org', 'ssrn.com',
                  'chemrxiv.org', 'researchsquare.com', 'psyarxiv.com',
                  'preprints.org', 'osf.io')


def _parse_args(argv):
    p = argparse.ArgumentParser(description='引用扩圈：沿引用/被引边发现候选文献')
    p.add_argument('thread_dir', help='工作线程根目录')
    p.add_argument('--target', type=int, required=True, help='输出 top N 条候选')
    p.add_argument('--mode', default='refs', choices=['refs', 'cited', 'both'],
                   help='扩圈通道（默认 refs）')
    p.add_argument('--year-min', type=int, default=2000, dest='year_min',
                   help='出版年下限（默认 2000）')
    p.add_argument('--per-page-cap', type=int, default=200, dest='per_page_cap',
                   help='cited 通道每种子的最大取回条数（默认 200）')
    args = p.parse_args(argv)
    if args.target < 1:
        p.error('--target 需为正整数')
    if args.per_page_cap < 1:
        p.error('--per-page-cap 需为正整数')
    return args


def _fix_encoding():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


def _flag(v):
    return v in (True, 1, '1', 'true', 'True', 'yes')


def _first3(names):
    names = [str(n).strip() for n in names if n]
    head = ', '.join(names[:3])
    return head + (' 等' if len(names) > 3 else '')


def _seeds(lib_db):
    return [p for p in lib_db
            if _flag(p.get('xref_verified'))
            and (p.get('fetch_status') or '') in ('ok', 'abstract_only')
            and (p.get('doi') or '').strip()]


def _whitelist(verify):
    wl = getattr(verify, 'WHITELIST_TYPES', None) or []
    if not wl:
        wl = ['article']  # 白名单缺失时退守最保守的 article
    return {str(x).lower() for x in wl}


def _seed_record(lib, limiter, doi):
    """取种子的 OpenAlex 记录：W-id、referenced_works、related_works。"""
    try:
        data = lib.http_get_json(OA_BASE, params={
            'filter': 'doi:' + doi, 'select': SEL_ID}, limiter=limiter)
    except (RuntimeError, ValueError):
        return '', [], []
    results = data.get('results') or []
    if not results:
        return '', [], []
    w = results[0]
    wid = str(w.get('id') or '').rsplit('/', 1)[-1]
    refs = [str(x).rsplit('/', 1)[-1] for x in (w.get('referenced_works') or [])]
    rel = [str(x).rsplit('/', 1)[-1] for x in (w.get('related_works') or [])]
    return wid, [r for r in refs if r], [r for r in rel if r]


def _gather_cited(lib, limiter, wid, pid, cap, edges, meta):
    """cited 通道：works?filter=cites:W<id> 游标翻页，每种子最多 cap 条。"""
    cursor, got = '*', 0
    while cursor and got < cap:
        try:
            data = lib.http_get_json(OA_BASE, params={
                'filter': 'cites:' + wid, 'select': SEL_META,
                'per-page': min(25, cap), 'cursor': cursor}, limiter=limiter)
        except (RuntimeError, ValueError):
            break
        res = data.get('results') or []
        if not res:
            break
        cursor = (data.get('meta') or {}).get('next_cursor') or ''
        for w in res:
            child = str(w.get('id') or '').rsplit('/', 1)[-1]
            if not child:
                continue
            edges.setdefault(child, set()).add(pid)
            meta.setdefault(child, w)
            got += 1
            if got >= cap:
                break
    return got


def _batch_meta(lib, limiter, wids, meta):
    """refs 通道补元数据：W-id 按 50/批批量取。

    filter 参数先试 openalex_id:W1|W2...（任务指定口径），
    失败时退回 ids.openalex:W1|W2...（文档备选写法）。
    """
    missing = [w for w in wids if w not in meta]
    got = 0
    for i in range(0, len(missing), 50):
        chunk = missing[i:i + 50]
        joined = '|'.join(chunk)
        data = None
        for fk in ('openalex_id:' + joined, 'ids.openalex:' + joined):
            try:
                data = lib.http_get_json(OA_BASE, params={
                    'filter': fk, 'select': SEL_META}, limiter=limiter)
                break
            except (RuntimeError, ValueError):
                continue
        if data is None:
            continue
        for w in (data.get('results') or []):
            wid = str(w.get('id') or '').rsplit('/', 1)[-1]
            if wid:
                meta[wid] = w
                got += 1
    return got


def _parse_work(w, lib, ctx):
    """过滤并解析一条 OpenAlex 作品；命中过滤规则返回 None。"""
    wid = str(w.get('id') or '').rsplit('/', 1)[-1]
    doi = (w.get('doi') or '').replace('https://doi.org/', '').strip()
    dkey = doi.lower()
    if dkey and (dkey in ctx['lib_dois'] or dkey in ctx['excl_dois']):
        return None
    title = (w.get('title') or '').strip()
    tkey = lib.normalize_title(title)
    if tkey and (tkey in ctx['lib_titles'] or tkey in ctx['excl_titles']):
        return None
    if str(w.get('type') or '').lower() not in ctx['whitelist']:
        return None
    year = w.get('publication_year') or 0
    if not year or year < ctx['year_min']:
        return None
    loc = w.get('primary_location') or {}
    src = loc.get('source') or {}
    venue = src.get('display_name') or ''
    url = loc.get('landing_page_url') or ''
    comb = ('%s %s %s' % (venue, url, title)).lower()
    if any(h in comb for h in PREPRINT_HOSTS):
        return None
    names = [((a.get('author') or {}).get('display_name') or '')
             for a in (w.get('authorships') or [])]
    return {
        'title': title,
        'authors': _first3(names),
        'year': str(year),
        'venue': venue,
        'doi': doi,
        'url': url,
        'oa': '1' if (w.get('open_access') or {}).get('is_oa') else '0',
        'abstract': '',
        'source_db': 'openalex',
        'native_id': wid,
        'type': w.get('type') or '',
        'cited_by_count': w.get('cited_by_count') or 0,
    }


def score_work(co_norm, cit_norm, year_norm, related, weights=None):
    """可调评分：0.4*共引归一 + 0.3*被引对数归一 + 0.2*新近归一 + 0.1*related 命中。"""
    w = weights or WEIGHTS
    return round(w['cooccur'] * co_norm + w['cited'] * cit_norm
                 + w['year'] * year_norm + w['related'] * related, 4)


def _apply_scores(rows):
    if not rows:
        return
    cur = datetime.date.today().year
    cmax = max(r['cooccur'] for r in rows) or 1
    citmax = max(math.log10(r['cited_by_count'] + 1) for r in rows) or 1.0
    recs = [1.0 / (1.0 + max(0, cur - int(r['year']))) for r in rows]
    ymax = max(recs) or 1.0
    for r, rec in zip(rows, recs):
        r['score'] = score_work(r['cooccur'] / cmax,
                                math.log10(r['cited_by_count'] + 1) / citmax,
                                rec / ymax,
                                1.0 if r['in_related'] == '1' else 0.0)


def _write_rows(path, cols, rows):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh, delimiter='\t', lineterminator='\n')
        wr.writerow(cols)
        for r in rows:
            wr.writerow([r.get(k, '') for k in cols])


def run(args, lib, verify):
    lib_db = lib.load_library(args.thread_dir)
    seeds = _seeds(lib_db)
    if not seeds:
        print('库内没有可用种子（需 xref_verified 且 fetch_status 为 ok/abstract_only）',
              file=sys.stderr)
        return 1
    excluded = lib.load_excluded(args.thread_dir)
    ctx = {
        'lib_dois': {(p.get('doi') or '').strip().lower() for p in lib_db
                     if (p.get('doi') or '').strip()},
        'lib_titles': {lib.normalize_title(p.get('title') or '') for p in lib_db
                       if (p.get('title') or '').strip()},
        'excl_dois': {(e.get('doi') or '').strip().lower() for e in excluded
                      if (e.get('doi') or '').strip()},
        'excl_titles': {lib.normalize_title(e.get('title') or '') for e in excluded
                        if (e.get('title') or '').strip()},
        'whitelist': _whitelist(verify),
        'year_min': args.year_min,
    }
    limiter = lib.RateLimiter()
    refs_edges, cited_edges, related_set, meta = {}, {}, set(), {}
    seed_miss = 0
    for p in seeds:
        wid, refs, rel = _seed_record(lib, limiter, (p.get('doi') or '').strip())
        if not wid:
            seed_miss += 1
            continue
        if args.mode in ('refs', 'both'):
            for r in refs:
                refs_edges.setdefault(r, set()).add(p.get('paper_id'))
            related_set.update(rel)
        if args.mode in ('cited', 'both'):
            _gather_cited(lib, limiter, wid, p.get('paper_id'),
                          args.per_page_cap, cited_edges, meta)
    if args.mode in ('refs', 'both') and refs_edges:
        _batch_meta(lib, limiter, list(refs_edges), meta)
    rows = []
    for wid, w in meta.items():
        row = _parse_work(w, lib, ctx)
        if row is None:
            continue
        row['cooccur'] = max(len(refs_edges.get(wid, ())),
                             len(cited_edges.get(wid, ())))
        row['in_related'] = '1' if wid in related_set else '0'
        rows.append(row)
    _apply_scores(rows)
    rows.sort(key=lambda r: r['score'], reverse=True)
    top = rows[:args.target]
    out_path = os.path.join(args.thread_dir, 'artifacts', '03-library',
                            '扩圈候选-%s.tsv' % datetime.date.today().strftime('%Y%m%d'))
    _write_rows(out_path, OUT_COLS, top)
    refcnt = sum(len(v) for v in refs_edges.values())
    citcnt = sum(len(v) for v in cited_edges.values())
    print('种子 %d 行（OpenAlex 未命中 %d）' % (len(seeds), seed_miss))
    if args.mode in ('refs', 'both'):
        print('refs 通道：唯一 W-id %d 个，种子->文献边 %d 条' % (len(refs_edges), refcnt))
    if args.mode in ('cited', 'both'):
        print('cited 通道：唯一 W-id %d 个，文献->种子边 %d 条' % (len(cited_edges), citcnt))
    print('过滤后候选 %d 条，输出 top %d -> %s' % (len(rows), len(top), out_path))
    lib.log_run(args.thread_dir, 'C3', 'cite',
                'mode=%s seed=%d out=%d' % (args.mode, len(seeds), len(top)))
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
    try:
        import literature_review_verify as verify
    except ImportError as e:
        print('缺少校验模块 literature_review_verify.py（需与脚本同目录）：%s' % e, file=sys.stderr)
        return 1
    return run(args, lib, verify)


if __name__ == '__main__':
    sys.exit(main())

