# Checkpoints and Recovery

Save a checkpoint after each verifiable unit: three reading notes, a recommendation batch, a chapter, or a revision. Continue without adding a human gate.

1. Use [checkpoint.json](../templates/checkpoint.json) to create notes/history/checkpoint-vN.json. artifacts lists existing current-version relative paths. completed lists verified units, not merely commands run.
2. Run `python <skill>/scripts/literature_review_check.py <work> --checkpoint <absolute-checkpoint>`. Update theme boundaries, gaps, round plan, pending decisions, blockers, and checkpoint. Do not alter stage/gate/attempt or fabricate counts. Partial top-level updates are allowed, but a supplied checkpoint object must be complete.
3. In prose outside the state block record research decisions, DOIs selected for this attempt, current draft, and next step. Record the date and content of user gate decisions. Avoid conflicting state documents.

## Resume order

Read state/latest checkpoint → verify listed files and contents → compare library, reading notes, and draft versions → resume the smallest unfinished unit. If artifacts exist but state lags, verify before updating. If state claims completion but artifacts are absent, record the discrepancy and restore that unit. Existence alone is not acceptance.

fetch --limit counts new eligible papers for this run. Before retrying, calculate the round's existing qualifying count and request only the remainder; do not rerun a fulfilled quota. Conversion/reading also skip verified units and preserve versions.

While waiting for copyediting set blocked_on=jiaozi and record the expected return. Clear it after review. Use environment for capability blockers and user for research decisions. An existing gate requires approval before --advance; a checkpoint cannot grant approval.

## Restart and retained library

Only use --reset-attempt after explicit Gate 2 approval. Preserve the global library and files. Its counts are total assets, not the new attempt's selected corpus. Maintain a DOI inclusion list for the current attempt and reassess relevance before counting toward 40+20. Reuse DOIs without downloading again. Prefix new reports with attemptN and version them; prior reading may be reused but relevance and synthesis must be reconsidered.

Stop state writes and report unreadable state, damaged JSON, or missing tools. Recover from verified artifacts/backups, not guesses. Only one operator writes ledgers at a time; atomic state replacement is not multi-writer transaction control. Legacy numbered ledgers require re-verification into a separate DOI-based work root.
