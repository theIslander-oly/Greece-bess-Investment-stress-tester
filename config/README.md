# Configuration policy

Place version-controlled, non-secret configuration templates here when a future milestone needs
shared configuration. Project-specific commercial values should be stored outside Git or in a
clearly illustrative example.

Existing illustrative battery, degradation and finance configurations remain in `examples/` to
avoid breaking documented commands. They are not project estimates.

`official_sources.json` is the reviewed, non-secret source and leakage-classification register.
It records provider roles and stable landing/API endpoints; execution-specific URLs, hashes and
timestamps belong in ignored retrieval manifests.

`admie_gate_closure.example.json`, `decision_cutoff.example.json`,
`fundamentals_geography.example.json` and `decision_lead_minutes.example.txt` are illustrative
formats, not declarations. Each carries placeholder text that must be replaced before use, and
`tests/test_config_examples.py` keeps them parseable by the code that will read the real
declaration and recognisable as examples. There is no default gate closure, decision lead or
sampling geography: the tooling reports whatever is declared and cannot check a declaration
against the market rules.

The v0.9 point-in-time feature path reads its declarations through
`greek_bess.data.decision_cutoff.read_decision_cutoff_schedule` and
`greek_bess.data.point_in_time.read_sampling_geography`, both of which **refuse the committed
example by name**. Copying an example into `config/decision_cutoff.json`,
`config/fundamentals_geography.json` or `config/decision_lead_minutes.txt` without replacing its
placeholder therefore stops the run rather than turning a placeholder into evidence.


The operator-approved v0.9 declarations are `decision_cutoff.json`,
`decision_lead_minutes.txt` and `fundamentals_geography.json`. Their basis, limitations and
pre-registered benchmark choices are recorded in
`docs/fundamentals_declarations_2026-09-03.md`. Committing a declaration does not accept a feature
table or validate its cited primary evidence; those are separate v0.9.5 gates.
