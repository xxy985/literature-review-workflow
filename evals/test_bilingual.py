"""Release checks for independent Chinese and English skill packages."""
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_packages", ROOT / "maintenance/build_packages.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BilingualPackages(unittest.TestCase):
    def test_standalone_resource_parity(self):
        zh, en = builder.payload("zh-CN", "test"), builder.payload("en", "test")
        self.assertEqual(set(zh), set(en))
        self.assertIn("templates/checkpoint.json", en)
        self.assertIn("evals/test_workflow.py", en)
        for path in en:
            if path.startswith("scripts/") or path == "evals/test_workflow.py":
                self.assertEqual(zh[path], en[path], path)

    def test_links_resolve_inside_each_package(self):
        import posixpath
        for language in ("zh-CN", "en"):
            files = builder.payload(language, "test")
            for name, data in files.items():
                if not name.endswith(".md"):
                    continue
                for link in re.findall(r"\]\(([^)]+)\)", data.decode("utf-8")):
                    if "://" in link or link.startswith("#"):
                        continue
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), link.split("#")[0]))
                    self.assertIn(target, files, (language, name, link))

    def test_templates_and_state_structure(self):
        zh, en = builder.payload("zh-CN", "test"), builder.payload("en", "test")
        for name in zh:
            if name.startswith("templates/") and name.endswith(".md"):
                tables = lambda data: [line.count("|") for line in data.decode("utf-8").splitlines() if line.startswith("|")]
                self.assertEqual(tables(zh[name]), tables(en[name]), name)
        a = json.loads(zh["templates/checkpoint.json"])
        b = json.loads(en["templates/checkpoint.json"])
        a["checkpoint"]["next_action"] = b["checkpoint"]["next_action"]
        self.assertEqual(a, b)

    def test_changelog_dates_stay_synchronized(self):
        dates = lambda path: re.findall(r"^## (\d{4}-\d{2}-\d{2})", path.read_text(encoding="utf-8"), re.M)
        self.assertEqual(dates(ROOT / "CHANGELOG.md"), dates(ROOT / "en/CHANGELOG.md"))

    def test_archives_match_current_sources(self):
        import hashlib
        import zipfile
        sums = (ROOT / "dist/SHA256SUMS.txt").read_text(encoding="utf-8")
        for language in ("zh-CN", "en"):
            path = ROOT / "dist" / ("literature-review-workflow-" + language + ".zip")
            with zipfile.ZipFile(path) as archive:
                release = json.loads(archive.read("VERSION.json"))["release"]
                expected = builder.payload(language, release)
                self.assertEqual(set(archive.namelist()), set(expected))
                for name, data in expected.items():
                    self.assertEqual(archive.read(name), data, (language, name))
            self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name, sums)


if __name__ == "__main__":
    unittest.main()
