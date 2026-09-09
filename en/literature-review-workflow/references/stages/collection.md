# C1–C3 Collection and Reading

The shorthands search/fetch/convert/cite/check mean `python <skill>/scripts/literature_review_<name>.py <work>`. Consult --help before calling; use absolute artifact paths.

## C1: Research brief and candidate pool

At Gate 1 record `computer-science` or `other` and the reason. Only the former admits conference papers; ambiguous interdisciplinary topics default to other pending the decision. Pass `--review-field <confirmed-value>` to every fetch. Finding a candidate is not admission: CrossRef must verify the publication type; OpenAlex article is not proof of journal publication.

Use the topic, existing material, and intended use to write a research brief under artifacts/01-topic/: question, review type (narrative/scoping/systematic), audience, scope, contribution. Label reasonable assumptions. If direction is genuinely ambiguous, propose 2–3 options at Gate 1. Do not call the result a systematic review without explicit eligibility criteria, complete search records, and the relevant methods.

Design 3–5 search groups with synonyms, broader/narrower terms, and time windows; run `search --query "..."` for each. Merge candidates by date and retain versioned snapshots for selection and collection. A deduplicated pool of 60 is a soft minimum; explain shortfalls. Record official statistics and standards separately with source, date, and use; do not disguise them as papers.

Output the brief, queries, pool, and search report. Check scope fit, traceability, counts, and gaps. Run `check --at-gate 门1`; after approval run `check --advance C2`.

## C2: Initial corpus and direction

Use Gate 1's decision and the pool. Filter relevance first, then assess foundational importance, methodological representation, recent progress, debate, and data support. Five 1–5 scores may aid ranking but require reasons. Select 10 papers plus reserves, save recommendations, and export ordered rows to round01-selected-v1.tsv without changing candidate fields. Do not pass the entire unsorted pool to fetch.

Run `fetch --candidates <selected-tsv> --round 1 --limit 10 --fulltext-only`, also passing the confirmed field. Abstracts remain in the ledger but do not count toward the ten full texts; list them for manual retrieval. Use reserves for shortfalls, passing only the remaining new quota on retries. Do not invent candidates when the pool runs out.

Run `convert --round 1`, then [read](../reading.md), write notes, and mark-read. Report B-level items separately. Produce the first [synthesis](../synthesis.md), proposed contribution, and topic adjustments. Save theme_boundary, weak_dimensions, rounds.planned (4–8, default 4), and completed rounds through a checkpoint.

Run `check --round 1 --require-fulltext 10`. Exit 2 means failure: resolve it, or report the shortfall and implications at Gate 2 without claiming the requirement passed.

Present the selection, achieved full-text count, notes, synthesis, topic, and round plan. Gate 2 confirms the corpus and direction. Follow [recovery](../recovery.md) for an approved restart; otherwise advance with `check --advance C3` after approval.

## C3: Forty core papers and twenty expansion papers

Each round: recommend against gaps → selected TSV → fetch → convert → notes/mark-read → synthesis → `check --round N` → checkpoint. Aim for roughly 10 papers per round and 40 core papers (A+B; B cannot replace core evidence). Distinguish global library counts from papers selected for the current attempt.

If the planned rounds finish short, report the missing count, reasons, remaining candidates, and attempted routes. Request a decision to continue up to 8 rounds, narrow the topic, or change the target. Never exceed 8 automatically. Even with enough papers, fill core evidence gaps or narrow claims before writing.

After the core corpus, use [expansion](../expansion-and-coverage.md): automated discovery, manual selection, and a coverage-gap audit. Target 20 expansion papers. `cite --target 40 --mode both` outputs candidates only. Export include rows, then run `fetch --candidates <selected-tsv> --round X --limit 20` with the confirmed field, `convert --round X`, reading, synthesis, `check --round X`, and `check --full`.

Acceptance: current-attempt 40/20 counts and A/B split are clear; core questions have evidence; uncovered dimensions have reasons and decisions; no unverified papers, active excluded re-entry, or preprints. Mechanical reports do not establish research quality. Continue with `check --advance C4` without another gate.

## Manual retrieval and existing material

Use the DOI-encoded filename in the retrieval checklist under source/manual/roundNN or roundXX, run `fetch --collect-manual --round N|X`, then convert and update reading records. Example: `10.1234/example` becomes `10.1234%2Fexample.pdf`. Manual retrieval does not mark a source as read A.

Existing collections still enter through a title/DOI candidate TSV and fetch verification; associate PDFs through manual retrieval. Convert does not create library rows. An already confirmed direction can start with first-round preparation; otherwise use Gate 1. Unverified or DOI-less inputs remain leads, never a shortcut around admission.
