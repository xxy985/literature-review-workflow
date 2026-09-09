# Formatting and Final Consistency Checklist

Use this checklist during C6's format round and before C8 delivery. Scripts cover only the listed automated checks; inspect every remaining item explicitly.

## 1. Automated checks

| Item | Tool | Acceptance |
|---|---|---|
| Working-draft citations | check --cite-audit <DOI-tagged-draft> --strict | Nonzero recognizable citations, all present/read; not semantic support |
| Basic delimiter pairing | to_docx preflight | Paired curly quotes/bold markers; inspect straight-quote warnings before --force |

The Agent checks final DOIs, continuous numbering, dangling references, placeholders, and claim support using [claim review](claim-review.md). cite-audit does not automate these. Do not alter valid quotes in code or identifiers blindly.

## 2. Quotations and symbols

- [ ] Match quotation marks correctly. For Chinese prose use paired Chinese curly quotes; do not blindly replace each character. For English prose follow the chosen style while preserving quotations and code.
- [ ] Escape literal Markdown asterisks, e.g. `N\*`, so separate symbols do not accidentally italicize intervening prose.
- [ ] Preserve valid chemical/numbering apostrophes such as `4,4',4''`.
- [ ] Use language-appropriate dash/ellipsis styles consistently; Chinese prose uses `——`/`……`.

## 3. DOCX italic regression

- [ ] Check for accidental italic spans, particularly Chinese text. The converter does not provide an italic inventory. Trace problems to Markdown/rendering and generate a corrected version.
- [ ] Apply the writing-requirements style sheet to bold values and italic variables.

## 4. Numbering and correspondence

- [ ] Every figure/table reference points to an existing numbered item.
- [ ] Captions are complete and units stated.
- [ ] Define terms on first use and use consistent terminology, checked against a glossary.

## 5. Citation and data discipline

- [ ] Use one agreed citation style throughout.
- [ ] Data-table values come only from A-level full-text sources, never B-level abstracts.
- [ ] Report all cited B-level sources and uses to the reviewer; do not put B labels or this instruction in final prose.
- [ ] Support both sides of disputed claims rather than asserting one side without context.

## 6. Final package

- [ ] Preserve version history and diff reports without overwriting earlier versions.
- [ ] Resolve every revision item with action and version references.
- [ ] Include final MD/resources, DOCX, LaTeX/PDF, logs, DOI map, audit, library snapshot, and consistency record. Reserve source-data checks, final DOI checks, authorship, and plagiarism review for human confirmation where required.
- [ ] No AI self-reference in manuscript prose, in accordance with writing requirements.
