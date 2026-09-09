# Evaluation

## Offline regression

Run `python -m unittest discover -s evals -p "test_*.py" -v` from the package root. Tests use isolated temporary directories and network substitutes; they do not download, commit, or change production sources. Cover zero citations, evidence state, full-text quotas, checkpoint recovery, and failed-write protection.

DOI/field tests cover CrossRef failure, duplicates, reversible filenames, manual retrieval, real PDF conversion, reading markers, and LaTeX failure gates. LaTeX subprocess tests use a substitute, not a real TeX build. Final manuscripts require actual compilation and page review.

## Behavioral evaluation

| Task | Minimal input | Acceptance |
|---|---|---|
| Resume | Research brief, three read papers, checkpoint/artifacts | Resume unfinished work without duplicate download or file-existence assumptions |
| Evidence limits | Results from two different settings | No unsupported ranking, causality, or significance; identify evidence needed |
| Abstract fallback | Abstract-only paper and core claim | B marking, reject core support, seek full text or narrow claim |
| Format handoff | Numeric-citation draft, map, returned edits | Recheck changed claims, clean final prose, stable mappings |

The worked example is for learning the rules. Repeating it does not demonstrate independent research ability.

## Real small-loop evaluation

Obtain a topic, audience/journal, source papers, and an accepted review example. Use a separate test work root and explicitly smaller counts, e.g. 6–10 core and 2–3 expansion papers, without changing production 40+20. Complete a source-verified section and exports, and interrupt/resume at least once.

Record model/environment, retrieval/download results, duplicated recovery work, source support for core claims, whether synthesis goes beyond summaries, and reasons for user rework. Offline success does not establish these outcomes; Windows tests do not establish macOS/Linux support.
