# Citation Expansion and Coverage Gaps

## 1. Why expand beyond recommendations?

Keywords set the initial pool; citation-heavy recommendations then reinforce familiar communities. The risk in collecting 40 papers is a whole missing method family, period, or data tradition. Citation links and related work reach beyond the original wording.

## 2. Script discovery routes

1. Backward references: recurring references identify foundations shared by seed papers.
2. Forward citations: enable cited-by for older seeds; short citation windows can hide recent work.
3. Related works: neighboring papers may reveal community boundaries.

literature_review_cite.py performs these routes and scoring. It outputs candidate TSV files, never automatic admission. Consult --mode; the example below explicitly enables both citation directions.

## 3. Agent-led discovery

1. Review-reference mining: choose representative reviews already in the library, inspect their references, and select papers relevant to the topic and gaps. Do not import whole bibliographies.
2. Keyword-cooccurrence search: extract recurring, discriminative phrases from titles, abstracts, and notes; use literature_review_search.py for supplemental searches. Record queries and added coverage.

These are Agent activities, not automatic cite.py features. If source material is insufficient, record “not performed” and why. Selected leads still require the common TSV verification/download pipeline.

## 4. Selection judgment

Review typical batches of 40–100 candidates rather than cutting rankings mechanically. Select representatives of an author community or benchmark series, not its fifth near-duplicate. Aim for 20 papers that address structural gaps across older/middle/recent work, method families, and publishing communities. Explain the value of recent low-citation papers that introduce a new dimension; rankings undervalue them.

Use [selection record](../templates/expansion-selection.md) under artifacts/03-library/ to document include/exclude decisions and a reason per paper. Five-dimension scoring may support the explanation.

## 5. Coverage-gap audit

Audit after every round and again after expansion. All five dimensions are mandatory:

| Dimension | Question | Typical gap |
|---|---|---|
| Time window | Are sources concentrated in one five-year period? | A family appears only before 2015 or after 2022 |
| Methods | Balance quantitative/qualitative/mixed work and method families | Variants of only one family |
| Source structure | Concentration of publishing/conference communities | More than half from one publishing system |
| Research communities | Author overlap and opposing schools | Only one side of a dispute |
| Language/region | Is English mainstream indexing the only source? | Important non-English traditions absent |

Use [audit template](../templates/blind-spot-audit.md) for a versioned report under artifacts/03-library/. Record confirmed coverage, explicit uncovered dimensions with reasons, and when to revisit each gap. A gap with no return condition is a decision to abandon it and needs user agreement.

One round of 10 papers adding no coverage, or a low expansion gap-fill rate, signals possible saturation. It never waives 40/20 targets. Report evidence and shortages for a decision; where counts suffice but core support does not, search further or narrow claims. A 30% rate is an uncalibrated reference, not an acceptance threshold.

## 6. Unacceptable shortcuts

- Filling the 20-paper target with repeated community variants.
- Using the script's top 20 as the final decision without review.
- Claiming a comprehensive search without dimension-specific audit findings.
- Citing outside-library papers before they pass fetch, verification, and reading.

## 7. Minimal sequence

1. Run `python <skill>/scripts/literature_review_cite.py <work> --target 40 --mode both`.
2. Read the generated artifacts/03-library/扩圈候选-<date>.tsv and apply the selection rules; fill the selection record.
3. Fill the audit template, including reasons and return conditions for gaps.
4. Export selected candidates, run `fetch --candidates <selected-tsv> --round X --review-field <confirmed-field>`, then `convert --round X` and `check --full`, using full script/work paths.
