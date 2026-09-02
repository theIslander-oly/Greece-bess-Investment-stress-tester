# Official data source register

The repository stores source locations and provenance evidence, not the downloaded datasets.
Review each provider's current terms before use or redistribution.

| Source | Intended use | Current status | Repository evidence |
| --- | --- | --- | --- |
| HEnEx Day-Ahead Market results | Primary official Greek DAM prices and publication metadata | Accepted end to end: parser, 2020-2025 archives, incremental 2026 daily retrieval, and operational dispatch/forecast acceptance over the complete history | `docs/official_data_acceptance_2026-08-25.md`, `docs/official_history_acceptance_2026-08-26.md`, `docs/official_multiyear_operational_acceptance_2026-08-27.md`, `docs/official_data_retrieval.md` |
| ENTSO-E Transparency Platform A44 | Independent official price retrieval and reconciliation | Client implemented; private-token acceptance pending | `docs/entsoe_github_retrieval.md` |
| IPTO/ADMIE publications | Future demand, generation, renewable and system context | Public catalog/download client implemented; feature parsing and publication-timing acceptance pending | `docs/official_data_retrieval.md` |
| NOAA GFS 0.25° forecast vintages | Point-in-time exogenous forecast features for the v0.9 benchmark: surface downward shortwave radiation, 2 m temperature and 10 m wind speed | Source chosen 2026-09-02; ingestion, availability audit and synthetic-only point-in-time join implemented; **not accepted** — availability audit and a dated data-acceptance document precede any use | `docs/fundamentals_source_assessment_2026-09-02.md`, `docs/point_in_time_feature_contract.md` |
| HEnEx market/rule publications | Market definitions, products and rule changes | Research input; not encoded as project-specific legal advice | Future legal/market-access review |

## Primary locations

- HEnEx website: <https://www.enexgroup.gr/>
- HEnEx terms: <https://www.enexgroup.gr/web/guest/terms-of-use>
- ENTSO-E Transparency Platform: <https://transparency.entsoe.eu/>
- ENTSO-E legal terms: <https://transparencyplatform.zendesk.com/hc/en-us/articles/40921911218961-Legal-Terms-and-Conditions>
- IPTO/ADMIE: <https://www.admie.gr/en>
- HEnEx DAM/IDM archive: <https://www.enexgroup.gr/dam-idm-archive>
- ADMIE file API: <https://www.admie.gr/en/market/market-statistics/file-download-api>
- NOAA GFS on AWS Open Data: <https://registry.opendata.aws/noaa-gfs-bdp-pds/>
- NOAA GFS objects: `https://noaa-gfs-bdp-pds.s3.amazonaws.com/` (anonymous `GET`, `HEAD` and
  `Range`; no credential is involved)

The NOAA licence requires attribution, forbids implying NOAA endorsement, and forbids presenting
derived values as unaltered NOAA data. All three are carried in `config/official_sources.json`
and restated verbatim in every retrieval summary this project writes, so the obligation travels
with the evidence.

Machine-readable source roles and leakage classifications are versioned in
`config/official_sources.json`. Annual HEnEx archive URLs are pinned in
`src/greek_bess/data/henex_archive.py`; every execution records the exact URLs and hashes in a
private retrieval manifest.

## Accepted HEnEx hashes

| Delivery day | Filename | SHA-256 |
| --- | --- | --- |
| 2026-08-24 | `20260824_EL-DAM_Results_EN_v01.xlsx` | `7fe79629bb8afcaa64bdb22b8de600f5659cd92a942b71b3d91f5411bac97970` |
| 2026-08-25 | `20260825_EL-DAM_Results_EN_v01.xlsx` | `b1e6d44eb504a6acd01f4d187bfc7aa8fcde8ceae085a033e90b0159c0f5abf1` |

These hashes identify user-retrieved files; the workbooks are not redistributed.

## Required provenance for future datasets

Record provider, landing-page URL, exact download URL or API request (without credentials),
delivery period, publication/revision identifier, retrieval timestamp, raw SHA-256, parser
version, normalized row count, UTC coverage, resolution and quality-check result.

ADMIE manifests keep publication time separate from delivery coverage. Forecast candidate files
remain classified `requires_pre_auction_timing_validation` until their historical publication
sequence is proven to precede the relevant HEnEx bid deadline.
