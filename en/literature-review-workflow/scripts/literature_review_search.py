#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选文献检索并合并为候选池（综述半自动工作流，走廊 C2：候选检索）。

输入：<thread_dir> --query 检索式（可重复）[--source openalex|crossref|s2|arxiv]
      [--limit N] [--pool-target N] [--out 输出相对路径]
输出：单个 TSV 候选文件；多检索式时合并为一个候选池并增加 origin 列。
      默认路径 artifacts/01-topic/候选-<source>-<日期>.tsv，
      合并时默认 artifacts/01-topic/候选池-<日期>.tsv。
      列：title,authors,year,venue,doi,url,oa,abstract,source_db,native_id,type

依赖：同目录公共库脚本（限速 HTTP、标题归一化）；无第三方依赖。
退出码：0 成功；1 运行失败；2 参数错误。
"""
import argparse
import csv
import datetime
import html
import os
import re
import sys
import xml.etree.ElementTree as ET

OA_BASE = 'https://api.openalex.org/works'
CR_BASE = 'https://api.crossref.org/works'
S2_BASE = 'https://api.semanticscholar.org/graph/v1/paper/search'
ARX_BASE = 'https://export.arxiv.org/api/query'
ATOM_NS = {'a': 'http://www.w3.org/2005/Atom', 'ar': 'http://arxiv.org/schemas/atom'}
OUT_COLS = ['title', 'authors', 'year', 'venue', 'doi', 'url', 'oa',
            'abstract', 'source_db', 'native_id', 'type']


def _parse_args(argv):
    p = argparse.ArgumentParser(
        description='检索候选文献并合并为候选池（OpenAlex/CrossRef/S2/arXiv）')
    p.add_argument('thread_dir', help='工作线程根目录')
    p.add_argument('--query', action='append', required=True, dest='queries',
                   help='检索式；可重复传多次，多次结果合并为一个候选池')
    p.add_argument('--source', default='openalex',
                   choices=['openalex', 'crossref', 's2', 'arxiv'],
                   help='检索数据源（默认 openalex）')
    p.add_argument('--limit', type=int, default=30,
                   help='每个检索式最多取回条数（默认 30）')
    p.add_argument('--pool-target', type=int, default=60, dest='pool_target',
                   help='候选池软下限；合并去重后不足则警告（默认 60）')
    p.add_argument('--out', default='', help='输出路径（相对 thread_dir；默认自动命名）')
    return p.parse_args(argv)


def _fix_encoding():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


def _clean(s):
    if not s:
        return ''
    s = re.sub(r'<[^>]+>', '', str(s))
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def _first3(names):
    names = [str(n).strip() for n in names if n]
    head = ', '.join(names[:3])
    return head + (' 等' if len(names) > 3 else '')


def _oa_abstract(w):
    """重建 OpenAlex abstract_inverted_index：按位置数组排序拼接。"""
    inv = w.get('abstract_inverted_index') or {}
    if not inv:
        return ''
    maxpos = 0
    for positions in inv.values():
        for i in positions:
            if i > maxpos:
                maxpos = i
    buf = [''] * (maxpos + 1)
    for word, positions in inv.items():
        for i in positions:
            buf[i] = word
    return ' '.join(buf)


def _openalex_work(w):
    loc = w.get('best_oa_location') or {}
    src = (w.get('primary_location') or {}).get('source') or {}
    names = [((a.get('author') or {}).get('display_name') or '')
             for a in (w.get('authorships') or [])]
    return {
        'title': _clean(w.get('title') or ''),
        'authors': _first3(names),
        'year': str(w.get('publication_year') or ''),
        'venue': _clean(src.get('display_name') or ''),
        'doi': (w.get('doi') or '').replace('https://doi.org/', ''),
        'url': loc.get('pdf_url') or '',
        'oa': '1' if (w.get('open_access') or {}).get('is_oa') else '0',
        'abstract': _oa_abstract(w),
        'source_db': 'openalex',
        'native_id': str(w.get('id') or '').rsplit('/', 1)[-1],
        'type': w.get('type') or '',
    }


def _crossref_work(it):
    titles = it.get('title') or ['']
    names = []
    for a in (it.get('author') or [])[:3]:
        seg = ' '.join(x for x in [(a.get('given') or ''), (a.get('family') or '')] if x)
        if seg:
            names.append(seg)
    year = ''
    parts = (it.get('issued') or {}).get('date-parts') or []
    if parts and parts[0] and parts[0][0]:
        year = str(parts[0][0])
    return {
        'title': _clean(titles[0] if titles else ''),
        'authors': _first3(names),
        'year': year,
        'venue': _clean((it.get('container-title') or [''])[0] or ''),
        'doi': it.get('DOI') or '',
        'url': it.get('URL') or '',
        'oa': '0',
        'abstract': _clean(it.get('abstract') or ''),
        'source_db': 'crossref',
        'native_id': '',
        'type': it.get('type') or '',
    }


def _s2_work(p):
    ext = p.get('externalIds') or {}
    pts = p.get('publicationTypes') or ['']
    return {
        'title': _clean(p.get('title') or ''),
        'authors': _first3([a.get('name') or '' for a in (p.get('authors') or [])]),
        'year': str(p.get('year') or ''),
        'venue': _clean(p.get('venue') or ''),
        'doi': (ext.get('DOI') or '').replace('https://doi.org/', ''),
        'url': p.get('url') or '',
        'oa': '1' if p.get('isOpenAccess') else '0',
        'abstract': _clean(p.get('abstract') or ''),
        'source_db': 's2',
        'native_id': p.get('paperId') or '',
        'type': pts[0] or '',
    }


def _arxiv_work(e):
    eid = _clean(e.findtext('a:id', default='', namespaces=ATOM_NS) or '')
    doi = (e.findtext('ar:doi', default='', namespaces=ATOM_NS) or '').replace('https://doi.org/', '')
    names = [_clean(a.findtext('a:name', default='', namespaces=ATOM_NS) or '')
             for a in e.findall('a:author', ATOM_NS)]
    return {
        'title': _clean(e.findtext('a:title', default='', namespaces=ATOM_NS) or ''),
        'authors': _first3(names),
        'year': _clean(e.findtext('a:published', default='', namespaces=ATOM_NS) or '')[:4],
        'venue': 'arXiv',
        'doi': doi,
        'url': eid,
        'oa': '1',
        'abstract': _clean(e.findtext('a:summary', default='', namespaces=ATOM_NS) or ''),
        'source_db': 'arxiv',
        'native_id': eid,
        'type': 'preprint',
    }


def _search_openalex(lib, limiter, q, limit):
    data = lib.http_get_json(OA_BASE, params={'search': q, 'per-page': limit},
                             limiter=limiter)
    return [_openalex_work(w) for w in (data.get('results') or [])]


def _search_crossref(lib, limiter, q, limit):
    data = lib.http_get_json(CR_BASE, params={'query': q, 'rows': limit},
                             limiter=limiter)
    items = (data.get('message') or {}).get('items') or []
    return [_crossref_work(it) for it in items]


def _search_s2(lib, limiter, q, limit):
    data = lib.http_get_json(S2_BASE, params={
        'query': q, 'limit': limit,
        'fields': 'title,authors,year,venue,externalIds,abstract,isOpenAccess,'
                  'publicationTypes,url',
    }, limiter=limiter)
    rows = data.get('data') if isinstance(data, dict) else []
    return [_s2_work(p) for p in (rows or [])]


def _search_arxiv(lib, limiter, q, limit):
    text = lib.http_get_text(ARX_BASE, params={
        'search_query': 'all:' + q, 'max_results': limit}, limiter=limiter)
    root = ET.fromstring(text)
    return [_arxiv_work(e) for e in root.findall('a:entry', ATOM_NS)]


_SEARCHERS = {
    'openalex': _search_openalex,
    'crossref': _search_crossref,
    's2': _search_s2,
    'arxiv': _search_arxiv,
}


def _try_openalex_title(lib, limiter, title):
    """摘要回退链第 1 站：OpenAlex 按标题检索。"""
    try:
        data = lib.http_get_json(OA_BASE, params={
            'filter': 'title.search:' + title[:180], 'per-page': 5}, limiter=limiter)
    except (RuntimeError, ValueError):
        return ''
    nt = lib.normalize_title(title)
    results = data.get('results') or []
    for w in results:
        if lib.normalize_title(w.get('title') or '') == nt:
            ab = _oa_abstract(w)
            if ab:
                return ab
    for w in results:
        ab = _oa_abstract(w)
        if ab:
            return ab
    return ''


def _try_s2_title(lib, limiter, title):
    try:
        data = lib.http_get_json(S2_BASE, params={
            'query': title[:180], 'limit': 3, 'fields': 'title,abstract'},
            limiter=limiter)
    except (RuntimeError, ValueError):
        return ''
    for p in (data.get('data') or []):
        ab = _clean(p.get('abstract') or '')
        if ab:
            return ab
    return ''


def _try_crossref_title(lib, limiter, title):
    try:
        data = lib.http_get_json(CR_BASE, params={
            'query.bibliographic': title[:180], 'rows': 3}, limiter=limiter)
    except (RuntimeError, ValueError):
        return ''
    for it in ((data.get('message') or {}).get('items') or []):
        ab = _clean(it.get('abstract') or '')
        if ab:
            return ab
    return ''


def _fill_abstract(lib, limiter, row):
    """摘要回退链：OpenAlex 标题检索 -> S2 -> CrossRef；仍无则空串，绝不编造。"""
    if (row.get('abstract') or '').strip():
        return row.get('abstract')
    title = row.get('title') or ''
    if not title:
        return ''
    for fn in (_try_openalex_title, _try_s2_title, _try_crossref_title):
        ab = fn(lib, limiter, title)
        if ab:
            return ab
    return ''


def _merge(groups, multiple, lib):
    """按 doi / 归一化标题去重合并多组检索结果；首见保留，origin 记录来源检索式。"""
    seen_doi, seen_title, out_rows, stats = set(), set(), [], []
    for gno, q, rows in groups:
        kept = 0
        for r in rows:
            doi = lib.normalize_doi(r.get('doi'))
            r['doi'] = doi
            t = lib.normalize_title(r.get('title') or '')
            if doi and doi in seen_doi:
                continue
            if doi:
                seen_doi.add(doi)
            if t:
                seen_title.add(t)
            if multiple:
                r['origin'] = '检索式%d:%s' % (gno + 1, q[:50])
            out_rows.append(r)
            kept += 1
        stats.append((gno + 1, q, len(rows), kept))
    return out_rows, stats


def main(argv=None):
    args = _parse_args(argv)
    _fix_encoding()
    if not os.path.isdir(args.thread_dir):
        print('线程目录不存在：%s' % args.thread_dir, file=sys.stderr)
        return 1
    if args.limit < 1 or args.limit > 200:
        print('--limit 需在 1-200 之间', file=sys.stderr)
        return 2
    if args.pool_target < 1:
        print('--pool-target 需为正整数', file=sys.stderr)
        return 2
    try:
        import literature_review_lib as lib
    except ImportError as e:
        print('缺少公共库 literature_review_lib.py（需与脚本同目录）：%s' % e, file=sys.stderr)
        return 1
    lib.ensure_paths(args.thread_dir)
    limiter = lib.RateLimiter()
    groups = []
    try:
        for i, q in enumerate(args.queries):
            rows = _SEARCHERS[args.source](lib, limiter, q, args.limit)
            groups.append((i, q, rows))
    except (RuntimeError, ValueError) as e:
        print('检索失败（%s）：%s' % (args.source, e), file=sys.stderr)
        return 1
    multiple = len(args.queries) > 1
    pool, stats = _merge(groups, multiple, lib)
    for gno, q, got, kept in stats:
        print('检索式 %d（%s）：返回 %d 条，去重后保留 %d 条' % (gno, q[:40], got, kept))
    missing = 0
    for r in pool:
        if not (r.get('abstract') or '').strip():
            r['abstract'] = _fill_abstract(lib, limiter, r)
            if not (r['abstract'] or '').strip():
                missing += 1
    if missing:
        print('无摘要 %d 篇（已尝试 OpenAlex/S2/CrossRef 回退链，未编造）' % missing)
    if len(pool) < args.pool_target:
        print('WARNING：候选池共 %d 条，不足软下限 %d，主题过窄或检索式需扩'
              % (len(pool), args.pool_target))
    today = datetime.date.today().strftime('%Y%m%d')
    if args.out:
        out_path = os.path.join(args.thread_dir, args.out)
    elif multiple:
        out_path = os.path.join(args.thread_dir, 'artifacts', '01-topic',
                                '候选池-%s.tsv' % today)
    else:
        out_path = os.path.join(args.thread_dir, 'artifacts', '01-topic',
                                '候选-%s-%s.tsv' % (args.source, today))
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    cols = OUT_COLS + (['origin'] if multiple else [])
    try:
        with open(out_path, 'w', encoding='utf-8', newline='') as fh:
            wr = csv.writer(fh, delimiter='\t', lineterminator='\n')
            wr.writerow(cols)
            for r in pool:
                wr.writerow([r.get(k, '') for k in cols])
    except OSError as e:
        print('写入候选文件失败：%s' % e, file=sys.stderr)
        return 1
    lib.log_run(args.thread_dir, 'C2', 'search',
                '%s x%d 检索，合并 %d 条' % (args.source, len(args.queries), len(pool)))
    print('候选池共 %d 条，已写入 %s' % (len(pool), out_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
