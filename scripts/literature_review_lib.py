#!/usr/bin/env python3
"""公共库：限速 HTTP、TSV 账本、状态块、路径骨架、通用工具。

被 literature_review_* 各脚本共同依赖，非命令行入口；离线自检：
  python literature_review_lib.py --selftest

走廊编号（与 SKILL.md 一致）：
  C1 定方向 / C2 首轮推荐 / C3 滚动与扩圈 / C5 下载入库与加工 / C6 修改 / C7 助理交接

网络纪律（既定决策"极低安全速率"）：
  每请求默认间隔 3.0 秒 + 0~2.0 秒随机抖动；可用环境变量
  LITERATURE_REVIEW_MIN_INTERVAL / LITERATURE_REVIEW_JITTER（秒，数值）覆盖。
  仅用标准库 urllib；网络错误与 429/5xx 最多重试 2 次（退避 5s/15s）；
  403/404 立即失败（付费墙语义，不重试不绕过）。

LIBRARY_FIELDS（source/papers/library.tsv 的 22 列，篇级唯一真相源）：
  paper_id        论文编号，R<轮>-<序号>，扩圈批次记 RX-<序号>
  title / authors / year / venue / volume / issue / pages   书目信息
  doi / url       身份与全文链接
  oa              是否开放获取（1/0）
  round           入库轮次（整数；扩圈批次记 X）
  source          下载通道（openalex / unpaywall / arxiv-mirror / manual / abstract…）
  pdf_path / md_path   相对工作根目录的文件路径（未取到为空）
  fetch_status    ok / abstract_only / manual_needed（唯一事实，不谎报）
  parse_quality   待定 pending / high / mid / low（convert 脚本评估）
  is_read         AI 是否精读（1/0）
  contribution    一句话贡献（精读后写）
  evidence        证据级：A=全文精读 / B=摘要级（仅支撑非核心论点）
  xref_verified   是否经核验（OpenAlex/CrossRef 词表归一后过白名单）
  added_at        入库时间

排除账（notes/history/excluded.tsv）为追加式账本，不删不改：
  同一 DOI 复核通过需回库时，追加一行 reason 以 withdrawn 开头的逆转行
  （撤销该 DOI 此前的排除状态，旧行保留留痕）；check --full 回灌断言
  按“同 DOI 最后一行”判定是否仍处于排除状态。
  排除记录允许 DOI 为空（如 arXiv 线索未查到正式版）；此类记录以
  归一化题名为备用键，回灌断言按 DOI + 题名双键检查（2026-09-05 评审决策）。

错误约定：本模块内文件/网络操作失败一律抛 RuntimeError（带路径与原因），
调用方按需要捕获；绝不静默吞错。
"""

import copy
import csv
import datetime
import difflib
import json
import os
import random
import re
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request as _urlreq

# ---------- 常量 ----------

LIBRARY_FIELDS = [
    "paper_id",
    "title",
    "authors",
    "year",
    "venue",
    "volume",
    "issue",
    "pages",
    "doi",
    "url",
    "oa",
    "round",
    "source",
    "pdf_path",
    "md_path",
    "fetch_status",
    "parse_quality",
    "is_read",
    "contribution",
    "evidence",
    "xref_verified",
    "added_at",
]
EXCLUDED_FIELDS = ["excluded_at", "title", "doi", "reason"]
RUNLOG_FIELDS = ["ts", "corridor", "action", "detail"]

LIBRARY_REL = os.path.join("source", "papers", "library.tsv")
EXCLUDED_REL = os.path.join("notes", "history", "excluded.tsv")
RUNLOG_REL = os.path.join("notes", "history", "run-log.tsv")
PROGRESS_REL = "progress.md"
STATE_BEGIN = "<!--LITERATURE-REVIEW-WORKFLOW:STATE:BEGIN-->"
STATE_END = "<!--LITERATURE-REVIEW-WORKFLOW:STATE:END-->"

DIRS = [
    os.path.join("source", "papers"),
    os.path.join("source", "manual"),
    os.path.join("source", "jiaozi"),
    os.path.join("artifacts", "01-topic"),
    os.path.join("artifacts", "02-recommend"),
    os.path.join("artifacts", "03-library"),
    os.path.join("artifacts", "04-knowledge-base"),
    os.path.join("artifacts", "05-outline"),
    os.path.join("artifacts", "06-writing-req"),
    os.path.join("artifacts", "07-draft"),
    os.path.join("artifacts", "08-jiaozi"),
    os.path.join("artifacts", "09-deliver"),
    os.path.join("notes", "history"),
]

DEFAULT_STATE = {
    "attempt": 1,
    "corridor": "C1",
    "gate": "",
    "theme": "",
    "theme_boundary": "",
    "weak_dimensions": [],
    "rounds": {"planned": 4, "completed": 0},
    "papers": {
        "target": 40,
        "expand_target": 20,
        "fulltext": 0,
        "abstract_only": 0,
        "manual_needed": 0,
    },
    "pending_decisions": [],
    "blocked_on": "",
}


def fix_encoding():
    """尽力把 stdout/stderr 切到 UTF-8（Windows 控制台防乱码；无该能力则忽略）。"""
    import contextlib

    for stream in (sys.stdout, sys.stderr):
        rec = getattr(stream, "reconfigure", None)
        if callable(rec):
            with contextlib.suppress(OSError, ValueError):
                rec(encoding="utf-8")


def _env_float(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        print(
            f"WARNING: 环境变量 {name}={raw!r} 非数值，使用默认 {default}",
            file=sys.stderr,
        )
        return default


def _to_float(val, fallback):
    try:
        return float(val)
    except (TypeError, ValueError):
        return fallback


MIN_INTERVAL = _env_float("LITERATURE_REVIEW_MIN_INTERVAL", 3.0)
JITTER = _env_float("LITERATURE_REVIEW_JITTER", 2.0)
HTTP_TIMEOUT = 30
MAX_RETRIES = 2
RETRY_BACKOFF = (5, 15)
UA = (
    "literature-review-workflow/1.0 (academic-review pipeline; polite single-threaded; "
    "contact via LITERATURE_REVIEW_CONTACT env)"
)


# ---------- 限速 ----------


class RateLimiter:
    """单线程极简限速：每次请求前调 wait()。"""

    def __init__(self, min_interval=None, jitter=None):
        self.min_interval = (
            MIN_INTERVAL
            if min_interval is None
            else _to_float(min_interval, MIN_INTERVAL)
        )
        self.jitter = JITTER if jitter is None else _to_float(jitter, JITTER)
        self._last = 0.0

    def wait(self):
        now = time.monotonic()
        due = self._last + self.min_interval
        if now < due:
            time.sleep(due - now + random.uniform(0, self.jitter))
        self._last = time.monotonic()


# ---------- HTTP（仅标准库） ----------


def _build_url(url, params):
    if not params:
        return url
    return url + "?" + urllib.parse.urlencode(params)


def _gzip_decode(data):
    """尝试 gzip 解压；解不开时原样返回字节（部分服务器误报 Content-Encoding）。"""
    try:
        import gzip

        return gzip.decompress(data)
    except (OSError, ValueError):
        return data


def _http_body(url, params=None, limiter=None, accept="application/json"):
    """GET 并返回响应字节。失败抛 RuntimeError；坏 JSON 由上层转 ValueError。"""
    full = _build_url(url, params)
    scheme = urllib.parse.urlsplit(full).scheme.lower()
    if scheme not in ("http", "https"):
        raise RuntimeError(f"仅允许 http/https，拒绝 {scheme!r}: {full[:120]}")
    headers = {"User-Agent": UA, "Accept": accept, "Accept-Encoding": "gzip"}
    contact = os.environ.get("LITERATURE_REVIEW_CONTACT", "")
    if contact:
        headers["User-Agent"] += " " + contact
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        if limiter is not None:
            limiter.wait()
        try:
            req = _urlreq.Request(full, headers=headers)
            with _urlreq.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                body = resp.read()
                enc = resp.headers.get("Content-Encoding") or ""
                if enc.strip().lower() == "gzip":
                    body = _gzip_decode(body)
                return body
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise RuntimeError(f"HTTP {e.code}（不重试）: {full}") from e
            last_err = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])
    raise RuntimeError(f"请求失败（{MAX_RETRIES + 1} 次尝试）: {full} :: {last_err}")


def http_get_text(url, params=None, limiter=None, accept="text/plain"):
    raw = _http_body(url, params=params, limiter=limiter, accept=accept)
    return raw.decode("utf-8", errors="replace")


def http_get_json(url, params=None, limiter=None):
    raw = _http_body(url, params=params, limiter=limiter)
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        raise ValueError(f"非 JSON 响应（接口异常或被限流）: {url}") from e


def http_download(url, dest, limiter=None):
    """下载到 dest（先写临时文件再原子改名）。校验 PDF 魔数与最小体积。

    返回 True/False，绝不抛异常；失败清理临时文件。
    """
    tmp = dest + ".part"
    try:
        raw = _http_body(url, limiter=limiter, accept="application/pdf,*/*")
        if not raw.startswith(b"%PDF-") or len(raw) < 10000:
            return False
        with open(tmp, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, dest)
        return True
    except (RuntimeError, OSError, ValueError):
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError as e:
            # 清理失败不掩盖主错误；残留临时文件会被下次 os.replace 覆盖
            print(f"清理临时文件失败（忽略）：{e}", file=sys.stderr)
        return False


# ---------- 路径与账本 ----------


def ensure_paths(thread_dir):
    """幂等建立目录骨架与三本账的表头（已存在则不动）。"""
    try:
        for d in DIRS:
            os.makedirs(os.path.join(thread_dir, d), exist_ok=True)
        for rel, fields in (
            (LIBRARY_REL, LIBRARY_FIELDS),
            (EXCLUDED_REL, EXCLUDED_FIELDS),
            (RUNLOG_REL, RUNLOG_FIELDS),
        ):
            path = os.path.join(thread_dir, rel)
            if not os.path.isfile(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    csv.writer(fh, delimiter="\t", lineterminator="\n").writerow(fields)
    except OSError as e:
        raise RuntimeError(f"建立目录骨架失败（检查权限）：{thread_dir} :: {e}") from e


def _read_tsv(path, fields):
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            rd = csv.DictReader(fh, delimiter="\t")
            return [dict(r) for r in rd]
    except OSError as e:
        raise RuntimeError(f"读取账本失败：{path} :: {e}") from e


def _canon(value):
    """TSV 值规范化（写库边界统一口径）：布尔→'1'/'0'，None→''，其余→str。"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _append_tsv(path, fields, rows):
    try:
        existed = os.path.isfile(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="") as fh:
            wr = csv.writer(fh, delimiter="\t", lineterminator="\n")
            if not existed:
                wr.writerow(fields)
            for r in rows:
                wr.writerow([_canon(r.get(k, "")) for k in fields])
    except OSError as e:
        raise RuntimeError(f"写入账本失败：{path} :: {e}") from e


def load_library(thread_dir):
    return _read_tsv(os.path.join(thread_dir, LIBRARY_REL), LIBRARY_FIELDS)


def append_library(thread_dir, entries):
    _append_tsv(os.path.join(thread_dir, LIBRARY_REL), LIBRARY_FIELDS, entries)


def update_library_row(thread_dir, paper_id, **fields):
    """按 paper_id（大小写不敏感）更新指定列；找不到行返回 False。"""
    path = os.path.join(thread_dir, LIBRARY_REL)
    rows = _read_tsv(path, LIBRARY_FIELDS)
    target = (paper_id or "").strip().upper()
    hit = False
    for r in rows:
        if (r.get("paper_id") or "").strip().upper() == target:
            hit = True
            for k, v in fields.items():
                if k in LIBRARY_FIELDS:
                    r[k] = _canon(v)
    if not hit:
        return False
    try:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            wr = csv.writer(fh, delimiter="\t", lineterminator="\n")
            wr.writerow(LIBRARY_FIELDS)
            for r in rows:
                wr.writerow([r.get(k, "") for k in LIBRARY_FIELDS])
    except OSError as e:
        raise RuntimeError(f"更新库行失败：{path} :: {e}") from e
    return True


def load_excluded(thread_dir):
    return _read_tsv(os.path.join(thread_dir, EXCLUDED_REL), EXCLUDED_FIELDS)


def append_excluded(thread_dir, title, doi, reason):
    _append_tsv(
        os.path.join(thread_dir, EXCLUDED_REL),
        EXCLUDED_FIELDS,
        [
            {
                "excluded_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "title": title or "",
                "doi": doi or "",
                "reason": reason or "",
            }
        ],
    )


def log_run(thread_dir, corridor, action, detail):
    _append_tsv(
        os.path.join(thread_dir, RUNLOG_REL),
        RUNLOG_FIELDS,
        [
            {
                "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "corridor": corridor or "",
                "action": action or "",
                "detail": (detail or "").replace("\n", " ")[:500],
            }
        ],
    )


# ---------- 编号与标题工具 ----------


def round_tag(round_no):
    """轮次标签（目录名/文件名用）：1-99 → '01'..'99'；'X'（扩圈批次）→ 'XX'。

    严格校验：拒绝 bool、非整数数值（如 1.9）、非十进制字符串——
    int(1.9)=1、int(True)=1 的静默截断属隐患（2026-09-05 评审 R2）。
    """
    if isinstance(round_no, str) and round_no.strip().upper() == "X":
        return "XX"
    if isinstance(round_no, bool) or not isinstance(round_no, (int, str)):
        raise RuntimeError(f'无效轮次编号 {round_no!r}（需整数 1-99 或 "X"）')
    if isinstance(round_no, str):
        s = round_no.strip()
        if not (s.isascii() and s.isdigit()):
            raise RuntimeError(f'无效轮次编号 {round_no!r}（需整数 1-99 或 "X"）')
        try:
            # isdigit 已保证可解析；此处防御式捕获仅为满足静态检查的双保险
            rn = int(s)
        except ValueError:  # pragma: no cover — isascii+isdigit 后不可达
            raise RuntimeError(f"无效轮次编号 {round_no!r}") from None
    else:
        rn = round_no
    if not 1 <= rn <= 99:
        raise RuntimeError(f"轮次编号超出 1-99：{rn}")
    return f"{rn:02d}"


def next_paper_id(rows, round_no):
    """生成下一个 paper_id。round_no 为整数轮次或 'X'（扩圈批次）。

    轮次合法性复用 round_tag 的严格校验（拒绝 bool/1.9/越界，2026-09-05 评审 R2）。
    """
    if isinstance(round_no, str) and round_no.strip().upper() == "X":
        prefix = "RX-"
    else:
        prefix = f"R{round_tag(round_no)}-"  # 校验失败抛 RuntimeError
    max_seq = 0
    for r in rows or []:
        pid = (r.get("paper_id") or "").strip()
        if pid.startswith(prefix):
            try:
                max_seq = max(max_seq, int(pid[len(prefix) :]))
            except ValueError:
                continue
    return f"{prefix}{max_seq + 1:02d}"


def normalize_title(s):
    """标题归一化：NFKC + casefold + 去标点 + 压空白（用于去重与相似度）。"""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).casefold()
    s = re.sub(r"[^\w]+", " ", s, flags=re.UNICODE)
    return " ".join(s.split())


def title_similarity(a, b):
    """归一化标题相似度（0~1）；≥0.8 视为同题（既定阈值）。"""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def paper_counts(thread_dir):
    """按 fetch_status 汇总库内论文计数（喂给状态块 papers.*）。"""
    rows = load_library(thread_dir)
    counts = {
        "fulltext": 0,
        "abstract_only": 0,
        "manual_needed": 0,
        "excluded": len(load_excluded(thread_dir)),
    }
    for r in rows:
        st = r.get("fetch_status") or ""
        if st == "ok":
            counts["fulltext"] += 1
        elif st == "abstract_only":
            counts["abstract_only"] += 1
        elif st == "manual_needed":
            counts["manual_needed"] += 1
    return counts


# ---------- progress.md 状态块 ----------


def read_state(thread_dir):
    """读状态块 JSON；progress.md 或块缺失返回 {}；JSON 损坏抛 RuntimeError。"""
    path = os.path.join(thread_dir, PROGRESS_REL)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        raise RuntimeError(f"读取 progress.md 失败：{path} :: {e}") from e
    m = re.search(
        re.escape(STATE_BEGIN) + r"\s*(\{.*?\})\s*" + re.escape(STATE_END),
        text,
        flags=re.S,
    )
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"状态块 JSON 解析失败（人工修复 progress.md）: {e}") from e


def write_state(thread_dir, **updates):
    """合并更新状态块并重写 progress.md（围栏外自然语言区原样保留）。"""
    state = copy.deepcopy(DEFAULT_STATE)
    state.update(read_state(thread_dir))
    state.update(updates)
    blob = json.dumps(state, ensure_ascii=False, indent=2)
    block = f"{STATE_BEGIN}\n{blob}\n{STATE_END}"
    path = os.path.join(thread_dir, PROGRESS_REL)
    try:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            if STATE_BEGIN in text:
                text = re.sub(
                    re.escape(STATE_BEGIN) + r".*?" + re.escape(STATE_END),
                    lambda _match: block,
                    text,
                    count=1,
                    flags=re.S,
                )
            else:
                text = block + "\n\n" + text
        else:
            text = (
                "# 综述流程进度\n\n" + block + "\n\n"
                "（围栏标记之间的 JSON 区只由脚本维护；"
                "标记以下为自然语言进度区。）\n"
            )
        os.makedirs(thread_dir, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".progress-", dir=thread_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError as e:
        raise RuntimeError(f"写入 progress.md 失败：{path} :: {e}") from e
    return state


# ---------- 离线自检 ----------


def _selftest():
    import tempfile

    ok = [0]

    def check(name, cond):
        ok[0] += 1 if cond else 0
        print(("PASS" if cond else "FAIL") + f"  {name}")

    check(
        "normalize_title 去标点压空白",
        normalize_title("A  Fast, Robust: Method!") == "a fast robust method",
    )
    check(
        "title_similarity 同题≈1.0",
        title_similarity(
            "A Survey of Graph Neural Networks", "a survey of graph neural networks!!"
        )
        >= 0.94,
    )
    check(
        "title_similarity 异题低分",
        title_similarity("Graph Neural Networks Survey", "Transformer Language Models")
        < 0.5,
    )
    with tempfile.TemporaryDirectory() as td:
        ensure_paths(td)
        check(
            "骨架目录与三本账建立",
            os.path.isdir(os.path.join(td, "artifacts", "09-deliver"))
            and os.path.isfile(os.path.join(td, LIBRARY_REL)),
        )
        write_state(td, theme="测试主题", corridor="C1")
        st = read_state(td)
        check(
            "状态块读写往返",
            st.get("theme") == "测试主题" and st.get("papers", {}).get("target") == 40,
        )
        rows = [{"paper_id": "R01-01"}, {"paper_id": "R01-02"}, {"paper_id": "RX-01"}]
        check("next_paper_id 轮内递增", next_paper_id(rows, 1) == "R01-03")
        check("next_paper_id 扩圈 X 批", next_paper_id(rows, "X") == "RX-02")
        strict_rejects = 0
        for bad in (1.9, True, 100, "2.0", ""):
            try:
                round_tag(bad)
            except RuntimeError:
                strict_rejects += 1
        check(
            'round_tag 严格拒绝 1.9/True/100/"2.0"/空串',
            strict_rejects == 5,
        )
        np_rejected = False
        try:
            next_paper_id(rows, 100)
        except RuntimeError:
            np_rejected = True
        check("next_paper_id 越界轮次拒绝", np_rejected)
        append_library(
            td, [{"paper_id": "R01-01", "title": "Paper One", "fetch_status": "ok"}]
        )
        hit = update_library_row(td, "r01-01", is_read=1, contribution="贡献一句话")
        rows = load_library(td)
        check(
            "库行更新往返",
            bool(hit)
            and rows[0]["contribution"] == "贡献一句话"
            and rows[0]["is_read"] == "1",
        )
        append_excluded(td, "Bad Preprint", "10.1/x", "preprint_no_formal")
        check("排除账留痕", load_excluded(td)[0]["reason"] == "preprint_no_formal")
        log_run(td, "C5", "selftest", "行1\n换行截断")
        counts = paper_counts(td)
        check("计数汇总", counts["fulltext"] == 1 and counts["excluded"] == 1)
        prog = os.path.join(td, PROGRESS_REL)
        raised = False
        try:
            with open(prog, "w", encoding="utf-8") as fh:
                fh.write(STATE_BEGIN + "\n{ 坏 JSON }\n" + STATE_END + "\n自然语言\n")
            try:
                read_state(td)
            except RuntimeError:
                raised = True
        except OSError:
            raised = False
        check("坏状态块显式报错", raised)
    rl = RateLimiter(min_interval=0, jitter=0)
    rl.wait()
    check("RateLimiter 零间隔可构造", rl.min_interval == 0)
    total = 14
    print("SELFTEST " + ("OK" if ok[0] == total else f"FAILED ({ok[0]}/{total})"))
    return 0 if ok[0] == total else 1


def _main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--selftest":
        return _selftest()
    print("本模块是公共库，不是命令行入口。离线自检：python literature_review_lib.py --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(_main())

