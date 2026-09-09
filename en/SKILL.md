---
name: literature-review-workflow
description: A recoverable, evidence-first literature review workflow. Use when asked to start, advance, or resume a review. Supports source verification, close reading, cross-paper synthesis, claim review, checkpoints, and four decision gates. Requires Python, terminal access, local files, and research-stage network access.
---

# Literature Review Workflow

This is the English edition of the skill. All paths below are relative to the installed package root, which contains this file and `scripts/`. It does not require the Chinese package. Research judgment belongs to the Agent; scripts perform deterministic operations; humans approve consequential decisions. Discussing the skill does not start paper production.

## Start and resume

1. Identify the installed skill root and the separate work root for this review. Never mix them. Use absolute script and artifact paths in commands.
2. On first deployment run `python <skill>/scripts/literature_review_env_check.py`; add `--net` for network checks. PDF conversion requires pymupdf from C2, and DOCX handoff requires python-docx. Explain missing capabilities and the work that can still proceed.
3. For a new review run `python <skill>/scripts/literature_review_new.py <work> --title "Review topic"`. For an existing review read progress.md, run `python <skill>/scripts/literature_review_check.py <work> --corridor`, and verify artifacts using [recovery](references/recovery.md).
4. Load only the current stage guide. Continue after saving each completed unit; a checkpoint is not a decision gate.
5. Stop at a gate, while awaiting the copyeditor, for missing capabilities, a major evidence gap, or the round limit. “Continue” does not approve an existing gate unless the user's answer resolves its decision.

## Core requirements

- Keep research artifacts local; do not upload, email, publish, or synchronize them automatically.
- Preserve original inputs and delivered versions. Version reports, notes, and drafts. Tools may update machine ledgers and undelivered caches and remove their own temporary files, but must not delete user files.
- Only package tools write library.tsv and excluded.tsv. Exclusions are append-only; reverse one by appending the same key with a reason beginning with withdrawn. Preserve the original exclusion record.
- Only new/check commands write the progress.md state block. Prose outside it may be edited. Counts come from the library; research judgments come from notes.

- CrossRef must verify the formal publication. Exclude preprints. Conference papers are eligible only for confirmed computer-science-related review topics; all other or unconfirmed fields reject them. Merely using computing methods does not make a topic computer science. A verified formal paper may use an arXiv mirror for its full text.
- Use the normalized DOI as the only paper identifier. Remove the doi.org/doi: prefix and lowercase it. Material without a DOI remains a lead. Cite working drafts as `[doi:10.1234/example]`. Rounds are batch labels; filenames percent-encode the DOI, while the ledger retains the DOI and path. Legacy numbered ledgers are not supported: re-verify into a separate work root without overwriting old material.
- Deliver the same final manuscript as clean Markdown, final DOCX, a complete LaTeX project, and the PDF compiled from it. Claims, numbers, formulas, figures, and references must agree. Use the PDF for typesetting acceptance and follow [delivery](references/latex-delivery.md). A copyeditor handoff is not the final DOCX. Any missing or unchecked deliverable blocks completion.
- Use the package's rate limits and bounded retries; do not fetch concurrently.
- A = full text read; B = abstract read. These describe source access, not study quality. B may support only non-core claims. Report its specific uses at gates; do not place evidence-grade labels in final prose.
- Production targets are 40 core papers plus 20 expansion papers, with 4–8 core rounds. Assess count, coverage, and claim support separately; do not fill quotas with irrelevant evidence.
- The copyeditor edits prose or returns comments; they do not maintain technical markers.

## Load by stage

| Stage | Inputs and actions | On completion |
|---|---|---|
| C1 Topic and search | [Collection](references/stages/collection.md): research brief, direction, candidate pool | Gate 1: question, scope, audience, search plan |
| C2 First reading round | Collection + [reading](references/reading.md): ten full texts, notes, initial synthesis | Gate 2: corpus, topic adjustment, rounds, contribution |
| C3 Rolling collection and expansion | Collection + [synthesis](references/synthesis.md) + [expansion](references/expansion-and-coverage.md) | Continue when library and core-question coverage pass |
| C4–C5 Outline and draft | [Writing](references/stages/writing.md) + [claim review](references/claim-review.md) | Gate 3: draft, outline, writing requirements, citation limits |
| C6 Revisions | Writing: resolve logic, content, and formatting issues | Continue automatically |
| C7–C8 Handoff and delivery | [Delivery stage](references/stages/delivery.md) | Gate 4: complete final package |

After gate approval use `check --advance C2|C3|C6`. Between automatic stages use `--advance C4|C5|C7|C8`. To record a gate, use the literal argument `--at-gate 门1|门2|门3|门4` (Gate 1–4). Always include the script path and work root. `--advance` records position; it does not prove approval or quality. Verify the artifacts and the user's decision first.

At a gate report completed work and files, the current gate, evidence gaps and B-level uses, and the exact decision needed. After Gate 4 approval record acceptance and the delivered version in the prose progress log; retain Gate 4 as the final state and do not deliver again.

## Artifacts and paths

Initialization creates source/papers, source/manual, source/jiaozi, notes/history, and artifacts/01-topic through 09-deliver. Use 01-topic for the research brief/search; 02-recommend for ranked recommendations; 03-library for library and expansion audits; 04-knowledge-base for reading evidence; 05-outline for synthesis/outline; 06-writing-req for requirements; 07-draft for drafts/claim review; 08-jiaozi for handoff; 09-deliver for final outputs/audits.

Load templates when needed: [reading note](templates/reading-note.md), [synthesis](templates/synthesis.md), [claim record](templates/claim-evidence.md), [checkpoint](templates/checkpoint.json), [writing requirements](templates/writing-req.md). On the first reading/synthesis/review unit consult the [worked example](examples/evidence-to-synthesis.md). It is fictional and cannot enter a real corpus.

## Validation and capability limits

Scripts establish only their stated mechanical conditions. The Agent checks source support, comparability, and research gaps against original material. Leave unresolved items explicit when judgment is not possible.

For maintenance or migration use [evaluation](evals/README.md). Offline tests and teaching examples do not replace a real review run; tests may use smaller corpora, but production retains 40+20 and the four gates. Manual research can proceed when tools are unavailable, but do not claim the mechanical pipeline is complete.

Use English for interaction, notes, and reports unless the user requests another language. Confirm manuscript language, length unit, and citation style separately. Some raw tool messages and fixed filenames remain Chinese. Explain outcomes in English, link to exact returned files, and preserve CLI values and machine fields. `jiaozi` means waiting for the copyeditor; no particular person is required.
