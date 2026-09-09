# C4–C6 Outline, Draft, and Revisions

Inputs: the research brief and Gate 2 decision, current-attempt corpus, reading notes, and synthesis.

## C4: Outline and writing requirements

Organize a versioned outline under artifacts/05-outline/ around questions and disagreements in the synthesis. Each section lists its central question, claim, supporting and opposing sources, applicability limits, and length. Plan at least 3 useful figures, tables, or pseudocode displays. Explain unsupported visuals rather than inventing data.

Use [writing requirements](../../templates/writing-req.md) to carry forward the positioning, scope, and contribution from Gates 1/2, adding language, length, citations, figures, formulas, and delivery formats. Label defaults for minor unconfirmed items and present them with the draft at Gate 3. Resolve gaps that would materially change direction before drafting a knowingly off-target manuscript. Run `check --advance C5` when ready.

## C5: First draft

Write section by section from the relevant synthesis and notes; do not load all 60 full texts at once. Organize comparisons, explanations, and limits around questions and cite `[doi:...]`. Follow [claim review](../claim-review.md). Save checkpoints after sections, then review terminology, section balance, and argument continuity.

Produce a versioned draft, claim-evidence table, and citation-boundary report. Review each core, numeric, comparative, causal, and gap claim against the source. Then run `check --cite-audit <absolute-draft> --strict --report <absolute-new-report>`. Background claims also require traceable sources; mechanical checks do not replace source review.

At Gate 3 present the draft, outline, requirements, B-level uses, unresolved claims, and decisions needed. Obtain logic revision feedback. Record `check --at-gate 门3`; after approval run `check --advance C6`.

## C6: Three revision rounds

The logic round checks structure, argument progression, section weight, and evidence links. The content round checks facts, coverage, disagreements, and conditions. The formatting round uses [the checklist](../formatting-checklist.md) for numbering, terminology, visuals, and language.

For each round: issue list → new draft version → `check --diff <absolute-old> <absolute-new>` → item-by-item resolution. Record locations and reasons; a line diff does not prove resolution. The Agent may raise issues for the later two rounds and continue after successful resolution without adding mandatory human gates.

Recheck new or changed core claims against original sources and update citation mappings. If an outside paper is needed, explain why, save the current checkpoint, return through collection/verification/reading, and resume the draft without replaying the entire corpus.

Acceptance: issues from all three rounds are resolved or explicitly await a decision; the draft and citation map agree; the mechanical audit passes; no unresolved core factual error remains. Run `check --advance C7`.
