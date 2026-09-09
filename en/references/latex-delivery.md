# Multi-format Final Delivery and LaTeX Typesetting

The final package always contains one synchronized final review in Markdown, DOCX, and a complete LaTeX project, plus the PDF compiled from that project. Markdown supports reading and reuse; DOCX supports comments and ordinary document delivery; LaTeX controls formal typesetting; the PDF is the typesetting acceptance reference.

## One final version across formats

After merging all accepted revisions and verifying claims, freeze a final version and record its content baseline and version number. Generate the three formats from it. Internal drafts may retain `[doi:...]`; delivered MD and DOCX must be clean manuscripts with normal citations and complete references. Internal drafts and copyeditor handoffs are not final outputs.

Prose, claim strength, numbers, units, formulas, figures, captions, and references must agree. Fonts, pagination, and citation presentation may differ, but DOI mappings must preserve citation targets. Apply substantive changes to the baseline first, synchronize affected formats, and recheck; never let editions drift independently.

Include Markdown images and other resources with portable relative links. to_docx.py may create an initial DOCX from clean MD, but cannot guarantee complex formulas, tables, or academic layout. Inspect and repair it, or use another available document tool. Do not omit content or substitute the handoff because conversion is limited.

## LaTeX build

1. At Gate 1 record the field and run `python <skill>/scripts/literature_review_env_check.py --delivery` early. Missing TeX does not block collection but does block delivery. TeX Live/MiKTeX must provide latexmk, XeLaTeX, and template packages; BibLaTeX also requires biber.
2. Gate 3 confirms the journal template, language, and reference style. Use a supplied template or an approved generic one, explicitly stating that journal compliance is unverified. Write main.tex, the bibliography, and figures; recheck claims after copyediting.
3. Working citations use `[doi:10.1234/example]`. Each bibliography entry retains its normalized DOI; prefer the DOI as the citation key. If the template cannot accept a DOI character, encode only the key and keep a one-to-one key/DOI/final-citation mapping in doi-map.tsv, not a new paper-number scheme.
4. Place main.tex, every referenced tex/bib/figure, required cls/sty, and doi-map.tsv in an independent versioned project directory. Use relative paths, never author-machine absolute paths. Retain template provenance and license information.
5. Run `python <skill>/scripts/literature_review_latex.py <absolute-project> <absolute-new-output>`. The tool copies the project, builds using latexmk + XeLaTeX, and saves logs. Non-zero exit, absent PDF, or unresolved references fail. Fix the source and retry into a new output version.
6. Render and inspect each PDF page: fonts (including Chinese when relevant), equations, tables, captions, references, and overflow. Compare against the working draft and DOI map. A successful build is not academic or layout acceptance.

## Gate 4 acceptance

Create one versioned directory under artifacts/09-deliver/ containing final MD/resources, final DOCX, the full rebuildable LaTeX project, its PDF, logs, DOI map, library export, mechanical audit, and claim-review report.

Open MD and image links; open or render DOCX to check prose, equations, and figures; actually compile LaTeX and inspect the PDF. Compare content and references section by section across formats. Save a consistency record naming versions, files, results, and unresolved issues. Never mark an unperformed check as passed.

Missing outputs, divergent content, conversion loss, or unavailable compilers/packages/fonts/templates block complete delivery. Report the blocker and existing artifacts. Once all requirements pass, pause at Gate 4 for the user to accept the whole versioned set.
