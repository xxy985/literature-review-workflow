# Changelog

Chinese and English packages are maintained, built, and validated together in each release, using shared scripts, data contracts, and a common version. This log records product changes without a separate translation-patch version. Historical entries describe the actual commits; the current two-package distribution is not attributed retroactively to earlier commits.

## 2026-09-09

- Shipped synchronized Chinese and English entry points, stage guides, templates, and evaluation documents. Each language package is independently deployable and uses the same deterministic scripts and machine-readable contracts.
- Defined the final package as one frozen manuscript delivered in clean Markdown, final DOCX, a complete LaTeX project, and the PDF compiled from it. The PDF is the typesetting acceptance reference.
- Added content-baseline, clean-output, resource, cross-format consistency, and actual-check requirements.
- This supersedes the September 8 delivery wording that treated MD/DOCX only as intermediate files. Both packages use the same current contract.

## 2026-09-08 · d26b917

- Restricted conference-paper admission to computer-science-related review topics; other and unconfirmed fields reject proceedings papers. CrossRef verifies formal publication type.
- Made normalized DOI the only paper identifier; removed legacy paper-number compatibility; added DOI deduplication, reversible filenames, DOI citations, and DOI-based reading/audit operations.
- Made LaTeX source plus compiled PDF mandatory, with environment gates, build logging, and unresolved-reference checks.
- Established the changelog and expanded admission, DOI, and delivery failure-path regression coverage.

## 2026-09-07 · 43e1abb

- Added stage-based operating guidance, close-reading evidence, cross-paper synthesis, claim review, checkpoints, recovery, and citation audit.
- Fixed quotas, formal-paper/preprint mirror handling, expansion candidates, audit traceability, and report versioning. Added 13 offline regression tests.

## 2026-09-04 · c2034c7

- Rewrote the public repository README with deployment, registration, capability, and boundary guidance.

## 2026-09-04 · b9b3fb6 (first commit)

- Delivered the self-contained literature-review skill: operating guide, deployment README, templates, references, requirements, and 12 Python tools.
- Added search, formal-publication verification, full-text retrieval, conversion, citation expansion, ledgers, audits, and Markdown/DOCX copyeditor handoff.
- Established manual triggering, four human decision gates, checkpoints, and manual retrieval fallback.

The historical commits above are real repository commits. Offline tests and documentation do not establish research quality, target-journal compliance, or cross-platform/real-TeX validation.
