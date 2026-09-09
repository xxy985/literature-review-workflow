# Literature Review Workflow

**A recoverable, evidence-first workflow for producing literature reviews.**

[English ZIP](https://github.com/xxy985/literature-review-workflow/raw/refs/heads/master/dist/literature-review-workflow-en.zip) · [Chinese ZIP](https://github.com/xxy985/literature-review-workflow/raw/refs/heads/master/dist/literature-review-workflow-zh-CN.zip) · [Operating guide](SKILL.md)

This package is an Agent skill, not an unattended paper generator. The Agent reads sources, compares studies, writes and verifies claims, and stops at four human decision gates. Python scripts handle deterministic retrieval, DOI verification, downloading, conversion, ledgers, and audits.

## Quick start

Download the English ZIP above and extract it. Register the extracted directory containing SKILL.md with your Agent. The package includes its own scripts, references, templates, tests, and requirements; the Chinese package is not required. Install only one language edition in a given skill registry: both use the same skill name. To switch, replace the installed skill directory without changing your separate review work root.

Give the Agent this setup instruction:

```text
Use the installed literature-review-workflow skill.
Read <skill-path>/SKILL.md first. My review work root is <work-root>.
When I ask you to start, advance, or resume the review, follow that guide.
Respond in English, and confirm the manuscript language separately.
```

`<skill-path>` is the extracted package, not the repository's en/ authoring folder. `<work-root>` is a separate directory for one review. From the installed skill directory check the environment; let the Agent initialize a new work root only when you explicitly start the review:

```bash
python scripts/literature_review_env_check.py
python scripts/literature_review_new.py <work-root> --title "Your review topic"
```

Register the package as a skill, then ask the Agent to “start the literature review workflow” or “advance the review”. It will read `progress.md`, run the current stage, and pause only at a decision gate or genuine blocker. Use absolute paths when calling scripts.

## Rules that affect inclusion

All papers must have a normalized DOI. CrossRef must confirm the formal publication type. Preprints are excluded. Conference papers are accepted only when the confirmed review field is `computer-science`; other or unconfirmed fields reject them. Use `--review-field computer-science` only after Gate 1 confirms the topic belongs to computer science.

DOIs are the only paper identifiers. Normalize them to lowercase without `doi:` or `https://doi.org/`. Working drafts cite `[doi:10.1234/example]`. DOI filenames use percent encoding, for example `10.1234%2Fexample.pdf`. This release intentionally does not read legacy paper-number ledgers.

## Final deliverables

Freeze one final content baseline, then deliver all of these from that baseline: a clean Markdown file, a clean DOCX, the complete LaTeX project, and the PDF compiled from that project. Content, claims, numbers, figures, formulas, references, and DOI targets must agree across formats. The PDF is the typesetting acceptance reference; any missing or unsynchronized format blocks completion.

LaTeX requires `latexmk` and `xelatex`. Check with `python scripts/literature_review_env_check.py --delivery`, then build with `python scripts/literature_review_latex.py <latex-project> <new-output-dir>`. See [multi-format delivery](references/latex-delivery.md).

## Package contents

- `SKILL.md`: English operating guide for this standalone package.
- `scripts/`: shared deterministic tools; CLI names and data fields remain stable.
- `references/` and `templates/`: stage rules, evidence, recovery, synthesis, and delivery contracts.
- `CHANGELOG.md`: one synchronized history for both language editions.

Run `python -m unittest discover -s evals -p "test_*.py" -v` before changing the package. Offline tests do not replace a real research run or real LaTeX build.

## Requirements and boundaries

Python 3.8+, a terminal, and local read/write access are required throughout. Search and verification need OpenAlex/CrossRef network access. The core uses only the standard library; install requirements.txt for pymupdf (PDF conversion) and python-docx (DOCX). TeX Live/MiKTeX supplies latexmk/XeLaTeX and template packages; BibLaTeX may require biber. Use `--net` for optional connectivity checks.

This skill suits reviews requiring recoverable sessions, traceable sources, and versioned artifacts across Agent environments. It does not support chat-only hosts without local execution, unattended claims of reliable research, paywall bypasses, or automatic publication. Missing full text is recorded for manual retrieval. Verified formal papers may use preprint mirrors; preprints themselves are excluded. Abstract evidence may support only non-core claims. Original inputs and delivered versions are preserved. Research judgment, fact checking, and authorship remain human responsibilities.

The English Agent interface and documents are localized. Some shared scripts still produce Chinese diagnostics and fixed filenames; the Agent explains results in English and preserves exact machine paths/fields. This is not a fully localized raw CLI. Both packages have byte-identical runtime scripts and the same VERSION.json release identifier. Local source files under en/ are build inputs; use the ZIP for installation.

The package includes 13 runtime scripts for retrieval, verification, conversion, citation expansion, ledgers, checkpoints, and audits. Citation auditing with --strict fails on zero recognized citations, unknown DOIs, or incomplete reading state. --fulltext-only counts only full texts; --limit means new eligible papers on this run. Production remains four decision gates and 40+20 papers.

Real-topic performance, download/selection rates, coverage thresholds, macOS/Linux behavior, and target-template LaTeX compilation still require real-use validation. The previous local environment lacked TeX tools; subprocess test substitutes do not establish compilation success.

## License

No open-source license has been attached to this repository. Public visibility alone does not grant redistribution or modification rights unless the owner states otherwise.
