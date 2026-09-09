# Literature Review Workflow

Standalone English Agent skill for recoverable, evidence-first literature reviews. Register this directory directly and read [SKILL.md](SKILL.md). It includes all scripts, references, templates, tests, and requirements needed for deployment; the Chinese package is not required.

Setup prompt:

```text
Use the literature-review-workflow skill.
Read <skill-path>/SKILL.md first. My review work root is <work-root>.
When I ask you to start, advance, or resume the review, follow that guide.
Respond in English and confirm the manuscript language separately.
```

Run `python scripts/literature_review_env_check.py` from this directory. Final delivery requires one frozen baseline rendered as clean Markdown, DOCX, a complete LaTeX project, and the PDF compiled from it. Conference papers are admitted only for confirmed computer-science reviews; DOI is the sole paper identifier. LaTeX requires `latexmk` and `xelatex`.

This package is developed and released synchronously with `zh/literature-review-workflow-zh/` using the same scripts and data contract. It is a first-class English edition, not a later translation.
