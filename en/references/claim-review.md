# Claim Review and Citation Mapping

Inputs: current draft, notes, original sources, and [claim template](../templates/claim-evidence.md). Outputs: version-matched claim-evidence table, citation map, and review report.

Working drafts cite `[doi:10.1234/example]`. For numeric or author-year styles keep a final-marker-to-DOI map. Internal markers stay outside final prose. Update the map whenever citation order changes.

## Two levels of acceptance

- Mechanical: `check --cite-audit <absolute-working-draft> --strict --report <absolute-new-report>` checks DOI identity, reading state, and A/B. Zero recognizable citations fail. It does not understand claims or validate final numeric citations.
- Semantic: individually verify core, numeric, comparative, causal, and research-gap claims. Background claims also need traceable sources and risk-based spot checks. Return to originals, not just prior summaries. Check direction, conditions, strength, and counterevidence. B cannot support core claims or unreported details.

Use supported / supported with qualifications / unsupported / unverified. Unsupported or unverified core claims must be revised, removed, supplemented, or explicitly referred for a decision. User approval is not evidence of truth.

Record the reasoning behind cross-paper inferences so a single citation does not appear to establish the entire synthesis. Check every chart/table value against original data, units, and comparison conditions.

Save a separate versioned citation-boundary report: scope checked, unresolved core claims, B count and specific uses, and human decisions needed. Keep internal audit procedures out of manuscript prose.

Check final citations against the map and bibliography: no unknown entries, repeated numbers, numbering gaps, or dangling references. Recheck prose and figures after DOCX/LaTeX export. Working-draft acceptance does not establish export acceptance.
