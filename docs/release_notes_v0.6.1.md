# Release notes — v0.6.1

Version 0.6.1 adds reproducible official-history acquisition without committing official data.

Key additions:

- HEnEx 2020-2025 annual archive retrieval;
- incremental unarchived HEnEx daily results retrieval;
- multi-workbook latest-revision normalization;
- ADMIE file catalog and download support;
- delivery/publication/retrieval time provenance;
- raw and parent archive SHA-256 manifests;
- provider host and archive extraction safety checks; and
- a manual private GitHub history-retrieval workflow.

The new clients are covered by deterministic synthetic HTTP, ZIP, HTML, JSON and XLSX tests. No
official file, credential or market-derived result is part of the package.

Live complete-history acceptance, ENTSO-E reconciliation and ADMIE feature-format/timing
validation remain pending. This release does not change the project's research-only status or
expand it beyond Greek Day-Ahead Market arbitrage.
