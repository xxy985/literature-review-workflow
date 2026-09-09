# C7–C8 Copyeditor Handoff and Final Delivery

Inputs: revised draft, claim-evidence table, citation map, and Gate 3 formatting decisions.

## C7: Copyeditor handoff

Retain the internal DOI-tagged draft. Create a clean handoff with normal citations and preserve the map separately. Run `python <skill>/scripts/literature_review_to_docx.py <absolute-handoff-md> <absolute-new-docx>`. Inspect figures, formulas, and citations; the converter does not guarantee complex academic layout fidelity.

Ask only for prose edits saved under source/jiaozi/ or a list of comments. Set blocked_on=jiaozi through a checkpoint, record the sent version and expected return, and wait. This is a dependency, not an additional decision gate.

## C8: Returned edits and final manuscript

For a returned DOCX, use from_docx.py with its two absolute path arguments to create a new MD and run `check --diff` against the handoff; save written comments as an issue list instead. Use the map to check whether wording changed claim strength, conditions, numbers, or citations. Restore internal DOI associations without asking the copyeditor to maintain them. Clear the checkpoint blocker after review and run `check --advance C8`.

Merge into a new version, recheck changed claims using [claim review](../claim-review.md), and audit the internal draft with --strict and --report. Freeze one final baseline and follow [multi-format delivery](../latex-delivery.md) to produce clean MD, final DOCX, complete LaTeX, and compiled PDF. Gate 3 selects templates and styles, not which required formats may be omitted.

Verify content and DOI targets across all three formats: prose, claims, numbers, formulas, figures, and references. Check Markdown resources, open or render DOCX, and compile and inspect the LaTeX PDF page by page. The PDF is the typesetting reference. Missing artifacts, inconsistent content, or inability to check are delivery blockers.

Under artifacts/09-deliver/ deliver one version containing MD/resources, final DOCX, LaTeX, PDF, build log, consistency record, mechanical audit, claim review, citation map, library export, and human-check list. Describe B-level uses and remaining limitations in the reports, not as internal labels in final prose. Run `check --at-gate 门4` and await acceptance of the complete set.
