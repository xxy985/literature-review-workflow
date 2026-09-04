#!/usr/bin/env python3
"""核对模块：verify_batch（DOI 核验）与 resolve_formal（预印本找正式版）。

被 literature_review_fetch / literature_review_cite 依赖，不直接作为命令行入口使用。

既定决策（预印本一律排除；会议论文正当）：
- 类型归一：OpenAlex 词表（article/review/book/...）与 CrossRef 词表
  （journal-article/posted-content/...）各自映射到统一归一空间再过白名单，
  避免两套词汇语义错位（OpenAlex article 其实涵盖期刊与会议论文）；
- 核验顺序：OpenAlex 批量（每批 ≤50 个 DOI）为主，未命中者逐个 CrossRef 兜底；
- 只按 type 与仓库域判，不看期刊名（防误伤）；
- 标题相似度 ≥0.8 方认可确认为同一论文（防串号）。

词表对照（供 cite 直接使用）：
  WHITELIST_TYPES —— OpenAlex 原生词表（小写），供 cite 等脚本对
  OpenAlex 返回的 type 字段直接比对。

返回约定：
  verify_batch(dois) -> list[dict]，按输入顺序对齐，每条：
    doi / verdict / type / norm_type / title / year / venue / volume / issue /
    pages / source_db（openalex|crossref）
  verdict ∈ {accept, not_found, preprint, out_of_scope}
  resolve_formal(title) -> str：正式版 DOI，未找到返回 ''。
"""

import urllib.parse

import literature_review_lib as lib

OA_BASE = "https://api.openalex.org/works"
CR_BASE = "https://api.crossref.org/works"

# OpenAlex 原生词表（cite 等对 OpenAlex type 直接比对用）
WHITELIST_TYPES = frozenset(
    {"article", "review", "book", "book-chapter", "proceedings-article"}
)
# 归一空间（对齐 CrossRef 白名单词）
WHITELIST_NORM = frozenset(
    {"journal-article", "proceedings-article", "book-chapter", "book"}
)
# OpenAlex -> 归一
_OA_TYPE_NORM = {
    "article": "journal-article",
    "review": "journal-article",
    "book": "book",
    "book-chapter": "book-chapter",
    "proceedings-article": "proceedings-article",
    "preprint": "preprint",
    "dissertation": "dissertation",
    "report": "report",
    "standard": "standard",
    "dataset": "dataset",
    "other": "other",
}
# CrossRef -> 归一
_CR_TYPE_NORM = {
    "journal-article": "journal-article",
    "proceedings-article": "proceedings-article",
    "book-chapter": "book-chapter",
    "book": "book",
    "posted-content": "preprint",
    "report": "report",
    "dissertation": "dissertation",
    "dataset": "dataset",
    "standard": "standard",
}
PREPRINT_HOSTS = (
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "ssrn.com",
    "chemrxiv.org",
    "researchsquare.com",
    "psyarxiv.com",
    "preprints.org",
    "osf.io",
)
SIMILARITY_THRESHOLD = 0.8
BATCH_SIZE = 50
_SEL_VERIFY = "id,doi,title,publication_year,type,biblio,primary_location"
_SEL_RESOLVE = "id,doi,title,publication_year,type,primary_location"


def _norm_doi(doi):
    return (
        (doi or "")
        .replace("https://doi.org/", "")
        .replace("http://dx.doi.org/", "")
        .strip()
        .lower()
    )


def _host_is_preprint(w):
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    for field in ("landing_page_url", "url", "pdf_url"):
        v = loc.get(field) or ""
        if v:
            host = urllib.parse.urlsplit(v).netloc.lower()
            if any(host == h or host.endswith("." + h) for h in PREPRINT_HOSTS):
                return True
    host = (src.get("host") or "") or ""
    if host:
        host = str(host).lower()
        if any(host == h or host.endswith("." + h) for h in PREPRINT_HOSTS):
            return True
    return False


def _parse_openalex(w):
    bib = w.get("biblio") or {}
    src = (w.get("primary_location") or {}).get("source") or {}
    doi = (w.get("doi") or "").replace("https://doi.org/", "").strip()
    raw_type = str(w.get("type") or "").strip().lower()
    norm_type = _OA_TYPE_NORM.get(raw_type, raw_type if not raw_type else "other")
    if raw_type == "":
        norm_type = ""
    venue = src.get("display_name") or ""
    volume = bib.get("volume") or ""
    issue = bib.get("issue") or ""
    pages = ""
    if bib.get("first_page"):
        pages = str(bib.get("first_page") or "")
        if bib.get("last_page"):
            pages = pages + "-" + str(bib.get("last_page") or "")
    return {
        "doi": doi,
        "type": raw_type,
        "norm_type": norm_type,
        "title": w.get("title") or "",
        "year": str(w.get("publication_year") or ""),
        "venue": venue,
        "volume": str(volume) if volume else "",
        "issue": str(issue) if issue else "",
        "pages": pages,
        "source_db": "openalex",
        "is_preprint_host": _host_is_preprint(w),
    }


def _parse_crossref(msg):
    doi = (msg.get("DOI") or "").strip()
    raw = str(msg.get("type") or "").strip().lower()
    norm_type = _CR_TYPE_NORM.get(raw, raw if raw else "")
    titles = msg.get("title") or []
    containers = msg.get("container-title") or []
    year = ""
    parts = (msg.get("issued") or {}).get("date-parts") or []
    if parts and parts[0] and parts[0][0]:
        year = str(parts[0][0])
    return {
        "doi": doi,
        "type": raw,
        "norm_type": norm_type,
        "title": titles[0] if titles else "",
        "year": year,
        "venue": containers[0] if containers else "",
        "volume": msg.get("volume") or "",
        "issue": msg.get("issue") or "",
        "pages": msg.get("page") or "",
        "source_db": "crossref",
        "is_preprint_host": False,
    }


def _verdict_from(rec):
    if rec is None:
        return "not_found"
    if rec.get("norm_type") == "preprint" or rec.get("is_preprint_host"):
        return "preprint"
    if rec.get("norm_type") in WHITELIST_NORM:
        return "accept"
    return "out_of_scope"


def _crossref_single(doi, limiter):
    url = CR_BASE + "/" + urllib.parse.quote(doi)
    try:
        data = lib.http_get_json(url, None, limiter=limiter)
    except (RuntimeError, ValueError):
        return None
    msg = data.get("message") if isinstance(data, dict) else None
    return _parse_crossref(msg) if msg else None


def verify_batch(dois):
    """核验一批 DOI：OpenAlex 批量为主，CrossRef 兜底未命中者。

    返回按输入顺序对齐的 list[dict]（字段见模块 docstring）；网络异常时
    对应条目记 verdict='lookup_failed'（不谎报成功）。
    """
    limiter = lib.RateLimiter()
    clean = []
    for d in dois or []:
        nd = _norm_doi(d)
        if nd:
            clean.append(nd)
    out = dict.fromkeys(range(len(clean)), None)
    # 1) OpenAlex 批量
    for start in range(0, len(clean), BATCH_SIZE):
        chunk = clean[start : start + BATCH_SIZE]
        f = "|".join("doi:" + d for d in chunk)
        try:
            data = lib.http_get_json(
                OA_BASE, {"filter": f, "select": _SEL_VERIFY}, limiter=limiter
            )
        except (RuntimeError, ValueError):
            data = None
        if not data:
            continue
        found = {}
        for w in data.get("results") or []:
            rec = _parse_openalex(w)
            kd = _norm_doi(rec.get("doi"))
            if kd:
                found[kd] = rec
        for i, d in enumerate(chunk):
            if d in found:
                out[start + i] = found[d]
    # 2) CrossRef 兜底（仅未命中）
    for i, d in enumerate(clean):
        if out.get(i) is None:
            out[i] = _crossref_single(d, limiter)
    # 3) 定 verdict
    results = []
    for i, d in enumerate(clean):
        rec = out.get(i)
        verdict = _verdict_from(rec)
        if rec is None:
            results.append(
                {
                    "doi": d,
                    "verdict": "lookup_failed",
                    "type": "",
                    "norm_type": "",
                    "title": "",
                    "year": "",
                    "venue": "",
                    "volume": "",
                    "issue": "",
                    "pages": "",
                    "source_db": "",
                }
            )
        else:
            row = dict(rec)
            row["verdict"] = verdict
            results.append(row)
    return results


def resolve_formal(title):
    """按标题找正式发表版 DOI（预印本线索源用）。找不到返回 ''。"""
    t = (title or "").strip()
    if not t:
        return ""
    limiter = lib.RateLimiter()
    try:
        data = lib.http_get_json(
            OA_BASE,
            {
                "filter": "title.search:" + t[:180].replace("|", " "),
                "select": _SEL_RESOLVE,
                "per-page": 5,
            },
            limiter=limiter,
        )
    except (RuntimeError, ValueError):
        return ""
    results = data.get("results") or []
    if not results:
        return ""
    best, best_sim = None, SIMILARITY_THRESHOLD - 0.001
    for w in results:
        sim = lib.title_similarity(w.get("title") or "", t)
        if sim >= best_sim:
            best, best_sim = w, sim
    if best is None:
        return ""
    rec = _parse_openalex(best)
    if _norm_doi(rec.get("doi")) == "":
        return ""
    if _verdict_from(rec) != "accept":
        return ""
    return rec["doi"]


def _selftest():
    """离线自检（不联网）：词表归一与 verdict 决策逻辑。"""
    ok = [0]

    def check(name, cond):
        ok[0] += 1 if cond else 0
        print(("PASS" if cond else "FAIL") + f"  {name}")

    check(
        "WHITELIST_TYPES 为 OpenAlex 词表",
        "article" in WHITELIST_TYPES and "journal-article" not in WHITELIST_TYPES,
    )
    check("OpenAlex article 归一进白名单", _OA_TYPE_NORM["article"] in WHITELIST_NORM)
    check("OpenAlex review 归一进白名单", _OA_TYPE_NORM["review"] in WHITELIST_NORM)
    check(
        "CrossRef posted-content 归一为 preprint",
        _CR_TYPE_NORM["posted-content"] == "preprint",
    )
    fake_journal = {
        "doi": "10.1/x",
        "type": "article",
        "title": "T",
        "year": "2024",
        "venue": "V",
        "volume": "1",
        "issue": "2",
        "pages": "3-4",
        "source_db": "openalex",
        "is_preprint_host": False,
        "norm_type": _OA_TYPE_NORM["article"],
    }
    fake_preprint = dict(fake_journal, type="preprint", norm_type="preprint")
    fake_data = dict(fake_journal, type="dataset", norm_type="dataset")
    check("verdict：期刊论文 accept", _verdict_from(fake_journal) == "accept")
    check("verdict：预印本拒绝", _verdict_from(fake_preprint) == "preprint")
    check("verdict：数据集越界", _verdict_from(fake_data) == "out_of_scope")
    check("verdict：无记录 not_found", _verdict_from(None) == "not_found")
    rec = _parse_crossref(
        {
            "DOI": "10.2/y",
            "type": "journal-article",
            "title": ["Cross Title"],
            "container-title": ["J"],
            "volume": "9",
            "issue": "8",
            "page": "7-6",
            "issued": {"date-parts": [[2023]]},
        }
    )
    check(
        "CrossRef 解析字段",
        rec["venue"] == "J"
        and rec["year"] == "2023"
        and rec["pages"] == "7-6"
        and rec["norm_type"] == "journal-article",
    )
    check("DOI 归一", _norm_doi("https://doi.org/10.1/X ") == "10.1/x")
    total = 10
    print("SELFTEST " + ("OK" if ok[0] == total else f"FAILED ({ok[0]}/{total})"))
    return 0 if ok[0] == total else 1


def _main(argv=None):
    import sys

    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--selftest":
        return _selftest()
    print(
        "本模块是核对模块，不是命令行入口。离线自检：python literature_review_verify.py --selftest"
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_main())

