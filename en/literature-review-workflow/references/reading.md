# Reading and Evidence Extraction

Inputs: verified library entries and the actual full text or abstract. Output a versioned note for each paper using [the template](../templates/reading-note.md).

Confirm the material matches the DOI/title, then extract questions, methods, conditions, results, and limitations. Numbers require units, sample/dataset, comparator, evaluation setting, and a source location; otherwise record “not reported”. For mathematical papers record assumptions, propositions, and proof boundaries rather than imposing experimental metrics.

The converted text's `<!-- page N -->` markers locate PDF pages; distinguish them from printed page numbers. Reopen the PDF for suspect tables, equations, or scans. If unreadable, mark the item unverified rather than inferring results from incomplete extraction.

Separate author-reported facts, author interpretations, and Agent inferences. State what key results support and what they do not establish, retaining limitations and counterexamples. A/B describes access; bias, external validity, and support strength require separate judgment.

Completion requires source locations, at least one usable finding with limits, and visible unverified items. Only then run `python <skill>/scripts/literature_review_check.py <work> --mark-read <doi> --contribution "one sentence" --evidence A|B`. A marker is not proof of close reading and must agree with the note.

Process 3–5 papers, checkpoint, and continue. Update synthesis when new dimensions emerge rather than waiting for all 60 papers. B notes contain only what the abstract reports; never invent experimental details or use B for core claims.
