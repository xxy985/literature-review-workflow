#!/usr/bin/env python3
"""Build two standalone language packages from one source tree."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOC_DIRS = ("references", "templates", "examples")


def payload(language, version):
    edition = ROOT if language == "zh-CN" else ROOT / "en"
    files = {}
    paths = [edition / name for name in ("README.md", "SKILL.md", "CHANGELOG.md")]
    for directory in DOC_DIRS:
        paths.extend(p for p in (ROOT / directory).rglob("*") if p.is_file())
    for path in paths:
        relative = path.relative_to(edition) if path.parent == edition else path.relative_to(ROOT)
        source = edition / relative
        if not source.is_file():
            raise RuntimeError("Missing paired resource: " + str(source))
        files[relative.as_posix()] = source.read_bytes()
    files["evals/README.md"] = (edition / "evals/README.md").read_bytes()
    files["agents/openai.yaml"] = (edition / "agents/openai.yaml").read_bytes()
    files["requirements.txt"] = (ROOT / "requirements.txt").read_bytes()
    for path in sorted((ROOT / "scripts").glob("*.py")):
        files["scripts/" + path.name] = path.read_bytes()
    files["evals/test_workflow.py"] = (ROOT / "evals/test_workflow.py").read_bytes()
    # Normalize text so Git's Windows line-ending conversion cannot change releases.
    files = {name: data.replace(b"\r\n", b"\n") for name, data in files.items()}
    digest = hashlib.sha256()
    for name, data in sorted(files.items()):
        digest.update(name.encode("utf-8") + b"\0" + data)
    files["VERSION.json"] = (json.dumps({"release": version, "language": language,
        "content_sha256": digest.hexdigest()}, indent=2) + "\n").encode("utf-8")
    return files


def build(output, version):
    output.mkdir(parents=True, exist_ok=True)
    archives = {}
    # Validate both editions before writing either archive.
    editions = {language: payload(language, version) for language in ("zh-CN", "en")}
    for language, files in editions.items():
        target = output / ("literature-review-workflow-" + language + ".zip")
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 9, 9, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        archives[target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text("".join(
        digest + "  " + name + "\n" for name, digest in sorted(archives.items())), encoding="utf-8")
    return archives


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--version", default="2026.09.09.1")
    args = parser.parse_args()
    for name, digest in build(args.output, args.version).items():
        print(name + "  " + digest)
