"""确定性回归：离线运行，不把教学材料当成真实文献。"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import literature_review_check as check
import literature_review_fetch as fetch
import literature_review_cite as cite
import literature_review_lib as lib


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        lib.ensure_paths(str(self.root))
        lib.write_state(str(self.root), theme="测试")

    def run_check(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return check.main([str(self.root), *args])

    def write(self, relative, text):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def paper(self, pid="R01-01", **changes):
        row = dict(paper_id=pid, title="Test", doi="10.1000/test", round="1",
                   fetch_status="ok", parse_quality="high", is_read="1",
                   evidence="A", md_path="source/papers/round01/" + pid + ".md",
                   xref_verified="true")
        row.update(changes)
        lib.append_library(str(self.root), [row])
        if row.get("md_path"):
            self.write(row["md_path"], "测试全文")

    def test_zero_citations_fail_and_report_saved(self):
        self.write("draft.md", "无引用文本[1]")
        self.assertEqual(self.run_check("--cite-audit", "draft.md", "--strict", "--report", "audit.md"), 2)
        self.assertIn("未识别到", (self.root / "audit.md").read_text(encoding="utf-8"))
        self.assertEqual(self.run_check("--cite-audit", "draft.md", "--report", "audit.md"), 1)

    def test_unknown_and_unread_fail(self):
        self.paper(is_read="0")
        self.write("draft.md", "R01-01 RX-99")
        self.assertEqual(self.run_check("--cite-audit", "draft.md", "--strict"), 2)

    def test_valid_citations_pass_with_semantic_limit(self):
        self.paper()
        self.write("draft.md", "结果 R01-01")
        self.assertEqual(self.run_check("--cite-audit", "draft.md", "--strict", "--report", "audit.md"), 0)
        self.assertIn("不证明", (self.root / "audit.md").read_text(encoding="utf-8"))

    def test_cannot_mark_missing_fulltext_as_A(self):
        self.paper(fetch_status="abstract_only", evidence="B", md_path="")
        self.assertEqual(self.run_check("--mark-read", "R01-01", "--contribution", "贡献", "--evidence", "A"), 1)

    def test_round_requires_reading_and_requested_count(self):
        self.paper(is_read="0")
        self.assertEqual(self.run_check("--round", "1"), 2)
        self.assertEqual(self.run_check("--mark-read", "R01-01", "--contribution", "贡献"), 0)
        self.assertEqual(self.run_check("--round", "1", "--require-fulltext", "10"), 2)
        self.assertEqual(self.run_check("--round", "1", "--require-fulltext", "1"), 0)

    def test_checkpoint_resume_and_gate_protection(self):
        self.write("notes/note.md", "已完成的证据")
        payload = {"weak_dimensions": ["对照"], "rounds": {"completed": 1},
                   "blocked_on": "jiaozi", "checkpoint": {
                       "unit": "C7", "completed": ["交接"], "next_action": "等回件",
                       "artifacts": ["notes/note.md"], "block_reason": "等回件"}}
        self.write("checkpoint.json", json.dumps(payload))
        self.assertEqual(self.run_check("--checkpoint", "checkpoint.json"), 0)
        state = lib.read_state(str(self.root))
        self.assertEqual(state["rounds"], {"planned": 4, "completed": 1})
        self.assertEqual(state["blocked_on"], "jiaozi")
        self.assertEqual(self.run_check("--at-gate", "门3"), 0)
        self.assertEqual(self.run_check("--checkpoint", "checkpoint.json"), 1)
        self.assertEqual(self.run_check("--advance", "C6"), 0)
        self.assertEqual(lib.read_state(str(self.root))["blocked_on"], "")

    def test_checkpoint_rejects_forgery_and_missing_artifact(self):
        for payload in ({"papers": {"fulltext": 60}}, {"rounds": {"planned": 99}},
                        {"checkpoint": {"unit": "C3", "completed": [], "next_action": "读",
                                         "artifacts": ["missing.md"], "block_reason": ""}}):
            self.write("bad.json", json.dumps(payload))
            self.assertEqual(self.run_check("--checkpoint", "bad.json"), 1)

    def test_atomic_state_failure_keeps_previous_text(self):
        original = (self.root / "progress.md").read_bytes()
        with patch.object(lib.os, "replace", side_effect=OSError("模拟替换失败")):
            with self.assertRaises(RuntimeError):
                lib.write_state(str(self.root), theme="更新")
        self.assertEqual((self.root / "progress.md").read_bytes(), original)
        self.assertEqual(list(self.root.glob(".progress-*")), [])
        lib.write_state(str(self.root), theme=r"path\note")
        self.assertEqual(lib.read_state(str(self.root))["theme"], r"path\note")

    def test_fulltext_quota_skips_abstract_and_deduplicates_batch(self):
        candidates = self.write("candidates.tsv", "title\tdoi\tabstract\nOne\t10.1000/one\t摘要\nOne\t10.1000/one\t摘要\nTwo\t10.1000/two\t摘要\n")
        args = fetch._parse_args([str(self.root), "--candidates", str(candidates),
                                  "--round", "1", "--limit", "1", "--fulltext-only"])
        with patch.object(fetch, "_verify_safe", return_value=(True, "accept", {})), \
             patch.object(fetch, "_download", side_effect=[("", "abstract"), ("https://example.org/two.pdf", "openalex")]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fetch._process(args, str(candidates), lib, object()), 0)
        rows = lib.load_library(str(self.root))
        self.assertEqual([r["fetch_status"] for r in rows], ["abstract_only", "ok"])
        self.assertEqual(len(rows), 2)
        self.assertTrue((self.root / "source/manual/人工补缺-round01.tsv").exists())

    def test_round_excludes_pending_downloads_and_preserves_reports(self):
        self.paper()
        self.paper("R01-02", fetch_status="abstract_only", evidence="B", md_path="")
        self.paper("R01-03", fetch_status="manual_needed", evidence="", is_read="0", md_path="")
        self.assertEqual(self.run_check("--round", "1"), 0)
        first = self.root / "artifacts/03-library/round1-验收.md"
        old = first.read_bytes()
        self.assertEqual(self.run_check("--round", "01"), 0)
        self.assertEqual(first.read_bytes(), old)
        self.assertTrue(first.with_name("round1-验收-v2.md").exists())

    def test_verified_formal_mirror_is_not_preprint(self):
        row = dict(paper_id="R01-01", doi="10.1000/formal", xref_verified="true",
                   venue="Formal Journal", url="https://arxiv.org/pdf/0000.00000")
        self.assertEqual(check._preprint_hits([row], lib), [])
        self.assertTrue(check._preprint_hits([dict(row, doi="10.48550/arxiv.0000")], lib))
        self.assertTrue(check._preprint_hits([dict(row, xref_verified="false")], lib))
        self.assertTrue(check._preprint_hits([dict(row, venue="arxiv.org")], lib))

    def test_round_rejects_stale_file_reference(self):
        self.paper()
        lib.update_library_row(str(self.root), "R01-01", md_path="source/missing.md")
        self.assertEqual(self.run_check("--round", "1"), 2)

    def test_related_only_work_reaches_candidate_output(self):
        self.paper()
        args = cite._parse_args([str(self.root), "--mode", "refs", "--target", "10"])
        def metadata(_lib, _limiter, ids, destination):
            self.assertIn("W999", ids)
            destination["W999"] = {"id": "W999"}
        parsed = dict(title="Related", year="2024", cited_by_count=0, doi="10.1000/related")
        with patch.object(cite, "_seed_record", return_value=("W1", [], ["W999"])), \
             patch.object(cite, "_batch_meta", side_effect=metadata), \
             patch.object(cite, "_parse_work", return_value=parsed), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cite.run(args, lib, object()), 0)
        candidates = list((self.root / "artifacts/03-library").glob("扩圈候选-*.tsv"))
        self.assertIn("10.1000/related", candidates[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
