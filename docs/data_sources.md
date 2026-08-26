# Official data source register

The repository stores source locations and provenance evidence, not the downloaded datasets.
Review each provider's current terms before use or redistribution.

| Source | Intended use | Current status | Repository evidence |
| --- | --- | --- | --- |
| HEnEx Day-Ahead Market results | Primary official Greek DAM prices and publication metadata | Parser implemented; 24 and 25 August 2026 English v01 workbooks accepted | `docs/official_data_acceptance_2026-08-25.md` |
| ENTSO-E Transparency Platform A44 | Independent official price retrieval and reconciliation | Client implemented; private-token acceptance pending | `docs/entsoe_github_retrieval.md` |
| IPTO/ADMIE publications | Future demand, generation, renewable and system context | Candidate source; not integrated or publication-timing validated | Future data-ingestion decision |
| HEnEx market/rule publications | Market definitions, products and rule changes | Research input; not encoded as project-specific legal advice | Future legal/market-access review |

## Primary locations

- HEnEx website: <https://www.enexgroup.gr/>
- HEnEx terms: <https://www.enexgroup.gr/web/guest/terms-of-use>
- ENTSO-E Transparency Platform: <https://transparency.entsoe.eu/>
- ENTSO-E legal terms: <https://transparencyplatform.zendesk.com/hc/en-us/articles/40921911218961-Legal-Terms-and-Conditions>
- IPTO/ADMIE: <https://www.admie.gr/en>

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
