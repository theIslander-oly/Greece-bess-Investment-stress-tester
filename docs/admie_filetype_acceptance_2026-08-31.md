# ADMIE day-ahead forecast filetype acceptance — 31 August 2026

## Scope

This record settles which live ADMIE Operation & Market Files catalog identifiers retrieve the
day-ahead load and RES forecast publications. It records catalog metadata and aggregate discovery
counts only. No downloaded file content was inspected, parsed or committed.

This is **not** publication-timing acceptance, file-format acceptance or permission to build a
forecast feature. It does not declare the HEnEx day-ahead gate closure. The 26 August 2026
forecast-feature quarantine remains in force.

## Live catalog evidence

The English `getFiletypeInfoEN` endpoint was retrieved on 31 August 2026 and returned 74 entries.
The day-ahead-relevant candidates reported by that catalog were:

| Filetype | Process | Data type | Period | Publication frequency | Catalog time gate |
|---|---|---|---|---|---|
| `DayAheadLoadForecast` | DAM | Load Forecast | DAY | Twice a day and on demand | 09:00 and 11:00 |
| `DayAheadRESForecast` | DAM | RES Forecast | DAY | Twice a day and on demand | 09:00 and 11:00 |
| `ISP1DayAheadLoadForecast` | ISP | ISP Forecast | DAY | not populated | not populated |
| `ISP1DayAheadRESForecast` | ISP | ISP Forecast | DAY | not populated | not populated |
| `ISP2DayAheadLoadForecast` | ISP | ISP Forecast | DAY | not populated | not populated |
| `ISP2DayAheadRESForecast` | ISP | ISP Forecast | DAY | not populated | not populated |

The catalog descriptions were empty for all six. Its `time_gate` metadata is recorded as catalog
metadata only and is not treated as the HEnEx auction gate closure or as evidence of when a file
was reachable.

## Confirming retrieval

All candidates were queried with overlap discovery and all revisions over delivery days
26-28 August 2026. The combined request refused because the DAM pair had no records, so the ISP
pairs were retrieved separately and produced manifests with these counts:

| Filetype | Discovered files |
|---|---:|
| `ISP1DayAheadLoadForecast` | 6 |
| `ISP1DayAheadRESForecast` | 6 |
| `ISP2DayAheadLoadForecast` | 3 |
| `ISP2DayAheadRESForecast` | 3 |
| **Total** | **18** |

The same-window query confirmed that `DayAheadLoadForecast` and `DayAheadRESForecast` are valid
catalog identifiers but returned zero files. Of the four previously declared names, those two
DAM names were therefore wrong for the live retrieval target; the two ISP1 names were confirmed.
The ISP2 load and RES names replace the non-retrieving DAM pair.

## Remaining blockers

- Re-run the publication-timing audit over all four confirmed ISP1/ISP2 filetypes.
- Supply a gate-closure schedule backed by a verified HEnEx Spot Trading Rulebook section and
  effective dates; the repository placeholder must not be used.
- Capture witnessed pre-gate evidence prospectively where possible.
- Accept each real file-format regime separately before parsing any value or building a feature.
