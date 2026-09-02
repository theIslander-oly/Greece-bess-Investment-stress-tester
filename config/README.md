# Configuration policy

Place version-controlled, non-secret configuration templates here when a future milestone needs
shared configuration. Project-specific commercial values should be stored outside Git or in a
clearly illustrative example.

Existing illustrative battery, degradation and finance configurations remain in `examples/` to
avoid breaking documented commands. They are not project estimates.

`official_sources.json` is the reviewed, non-secret source and leakage-classification register.
It records provider roles and stable landing/API endpoints; execution-specific URLs, hashes and
timestamps belong in ignored retrieval manifests.

`admie_gate_closure.example.json`, `decision_cutoff.example.json` and
`fundamentals_geography.example.json` are illustrative formats, not declarations. Each carries a
placeholder `reference` that must be replaced before use, and `tests/test_config_examples.py`
keeps them parseable by the code that will read the real declaration and recognisable as
examples. There is no default gate closure, decision lead or sampling geography: the tooling
reports whatever is declared and cannot check a declaration against the market rules.
