# Retained primary sources behind the fundamentals declarations

The two operator declarations with no default — the day-ahead gate-closure schedule in
`config/decision_cutoff.json` and the sampling geography in `config/fundamentals_geography.json`
— rest on publications this repository's tooling cannot verify. Both declarations require the
primary text to be retained with the acceptance evidence
(`docs/fundamentals_declarations_2026-09-03.md`, sections 1 and 2). This directory is the
citation record of that retention.

**What is here and what is not.** This directory holds citations, digests and short verbatim
quotations. The documents themselves are third-party publications and are not committed; they
are retained as assets of the private release named below, retrieved by the
`Retain primary sources` workflow from the declared set in `config/primary_sources.json`, and
identified by SHA-256 so that any later copy can be proven to be the retained one. A retained copy
is never overwritten by a fresh download: the workflow refuses a differing digest as a finding.

**What this record does and does not establish.** It establishes that the cited passages say
what the declarations say they say. It does not accept a feature value, evaluate a model, or
make any declaration correct beyond what the quoted text supports; where the text supports a
declaration only in part, the entry says so.

## Retention

| Item | Value |
| --- | --- |
| Release | [`primary-sources-2026-09-10`](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/releases/tag/primary-sources-2026-09-10) |
| Retrieval runs | `34517968860` (documents 1–7), `34518723361` (documents 8–9) |
| Retrieved at | 10 September 2026, 19:02 UTC (documents 1–7) and 19:10 UTC (documents 8–9) |
| Artifacts | `primary-sources` on each run (90 days), including `RETRIEVAL.json` |

Asset names carry the publisher's host as a prefix, and characters outside `[A-Za-z0-9._-]`
are replaced by dots, which is the renaming GitHub applies to release assets; two names below
differ from the published filenames in that way only. Documents 8 and 9 are served from a
library endpoint whose URL does not name the file, so their names are declared. Digests are of
the retrieved bytes.

**One refusal, recorded.** Run `34518625198` received a 12,113-byte response that was not a PDF
from the HWEA statistics URL; the release guard compared its digest with the retained copy,
refused to overwrite, and stopped. The next run (`34518723361`) received the document again with
the retained digest. Nothing on the release changed. A transient wrong answer from a publisher is
exactly what the guard exists to stop, and the retained copy is the one whose passages are quoted
below.

## Documents

### 1. HWEA / ELETAEN — Wind Energy Statistics 2023

| Field | Value |
| --- | --- |
| Supports | `config/fundamentals_geography.json`: regions, capacities and weights |
| URL | <https://eletaen.gr/wp-content/uploads/2024/01/2024-01-18-2023-HWEA_Statistics-Greece.pdf> |
| Publisher, date | Hellenic Wind Energy Association (HWEA / ELETAEN); file created 15 January 2024, published 18 January 2024; 10 pages |
| Asset | `eletaen.gr__2024-01-18-2023-HWEA_Statistics-Greece.pdf` |
| Bytes, SHA-256 | 454,105; `3c252f6084dc691dabacf83852de1eb9d480251d0a8cb8349dce05aa5b657fbb` |

Quoted (page 2, "Capacity (MW) per region", and page 1, "Total capacity to the grid (MW) per
year"):

> CENTRAL (STEREA) GREECE 2293 · PELOPONNESE 639 · EASTERN MACEDONIA & THRACE 534 ·
> WESTERN GREECE 413 · WESTERN MACEDONIA 374 · CRETE 203 · CENTRAL MACEDONIA 158 ·
> ATTICA (Trizinia & islands) 148 · IONIAN ISLANDS 120 · SOUTHERN AEGEAN SEA 112 · IPIROS 110 ·
> THESSALIA 46
>
> 2023: 5226

> The HWEA Wind Energy Statistics take into account the wind capacity which is in commercial or
> test operation in Greece and are based on sources from the market actors. HWEA has made
> effort to crosscheck and confirm the data. However, HWEA does not guarantee the accuracy of
> them and do not undertake any relevant liability.

**Reading.** The three largest regions and their capacities are exactly the declared 2,293 MW,
639 MW and 534 MW, and 2,293 / 3,466 = 0.661569…, 639 / 3,466 = 0.184362…, 534 / 3,466 =
0.154068… reproduce the declared weights to the digits recorded. The vintage is 31 December 2023
statistics published January 2024, before the validation block. The declaration's recorded
limitation stands: this is a wind-capacity weighting applied to irradiance and temperature as
well, because the fetch contract admits one common geography; HWEA's own caveat on accuracy is
part of the record.

### 2. NEMO Committee — Extension of Single Day-Ahead Coupling (SDAC) to Greece

| Field | Value |
| --- | --- |
| Supports | `config/decision_cutoff.json`: Greece's coupling from delivery day 2020-12-16, recorded in the regime's reference |
| URL | <https://www.nemo-committee.eu/assets/files/extension-of-single-day-ahead-coupling-(sdac)-to-greece-.pdf> |
| Publisher, date | NEMO Committee press release, 15 December 2020; 1 page |
| Asset | `www.nemo-committee.eu__extension-of-single-day-ahead-coupling-.sdac.-to-greece-.pdf` |
| Bytes, SHA-256 | 93,313; `00d7090d982b90f5d0c323876592762d10aae1a3718c3b22d2d6293d3becb715` |

> The market coupling operations of the Greek bidding zone in SDAC (Multi Regional Coupling)
> were successfully launched today, 15th December 2020 with the 16th December 2020 being the
> first delivery day. HEnEx, the designated single NEMO in Greece is now included in the market
> coupling operational processes as a new operational NEMO, along with IPTO, the Greek TSO.

**Reading.** Confirms the first coupled delivery day. The release does not state the
gate-closure time; documents 5, 8 and 9 do.

### 3. RAE — Decision 1574/2020 on the commencement of coupled day-ahead operation (HEnEx ref. 2506)

| Field | Value |
| --- | --- |
| Supports | `config/decision_cutoff.json`: the national regulatory act behind the coupling go-live |
| URL | <https://www.enexgroup.gr/documents/20126/211889/20201217_RAE_Decision_2506_Commencement_Market_Coupling_EN.pdf> |
| Publisher, date | Regulatory Authority for Energy, decision of 10 December 2020, forwarded 14 December 2020 (HEnEx reg. no. 2506); 11 pages, unofficial English translation |
| Asset | `www.enexgroup.gr__20201217_RAE_Decision_2506_Commencement_Market_Coupling_EN.pdf` |
| Bytes, SHA-256 | 925,641; `7de535593a837ffcf3efe1f51f28c7df84ba2d012fb82c09ddc1c823312606ef` |

> Subject: The No. 1574/2020 RAE Decision as regards the day of commencement of the Day-Ahead
> Market coupled operation on the Greek-Italian border, in accordance with the provisions of
> subsection 7.1.1 of Chapter 7 of the Day-Ahead and Intra-Day Market Trading Rulebook, as
> applying

**Reading.** The regulatory act that switched the Greek DAM from isolated to coupled operation,
consistent with document 2. It is retained for the effective date; the operative time limits
are in the HEnEx timeline decision (documents 5 and 8).

### 4. NEMO Committee — Communication note on new SDAC operational timings, 26 May 2021

| Field | Value |
| --- | --- |
| Supports | `config/decision_cutoff.json`: SDAC operational timings are expressed in CET and the order-book gate was unaffected by the 2021 change |
| URL | <https://www.nemo-committee.eu/assets/files/sdac-communicaton-note-on-new-timings.pdf> |
| Publisher, date | NEMO Committee, 26 May 2021; 1 page |
| Asset | `www.nemo-committee.eu__sdac-communicaton-note-on-new-timings.pdf` |
| Bytes, SHA-256 | 91,039; `bb3c7337e4625858f829d4b278c5c1d9f9f6778e128391c30781b161abb2bda6` |

> For market parties this will result in the following changes in the daily operational
> timings: Preliminary Results publication time: 12:45 CET (instead of 12:42 CET); Partial-
> Decoupling due to missing order books deadline: 12:45 CET (instead of 12:40 CET) …
> Full-Decoupling deadline: 14:00 CET (instead of 13:50 CET)

**Reading.** The 2021 timing change moved result and decoupling deadlines, all after 12:00 CET,
and did not move the order-book closure. It is context for the declared closure, not its source.

### 5. HEnEx — Decision 10, "Timeline Procedures for the Day-Ahead and Intra-Day Market", as of 31 March 2026

| Field | Value |
| --- | --- |
| Supports | `config/decision_cutoff.json`: order gate closure 12:00 CET/CEST on D-1 (13:00 EET/EEST), version in force at retrieval |
| URL | <https://www.enexgroup.gr/documents/20126/0/20260331_HEnEx_DAM_IDM_Technical_Decision_10_EN.pdf> |
| Publisher, date | Hellenic Energy Exchange S.A., HEnEx ref. 700/31.03.2026, unofficial English translation; 17 pages |
| Asset | `www.enexgroup.gr__20260331_HEnEx_DAM_IDM_Technical_Decision_10_EN.pdf` |
| Bytes, SHA-256 | 496,869; `a36c63fd2a1fe08fdf7a7d4d074dc7c8a235a4ef7c10c68250ffae59389ce205` |

> 3. All times in Timeline procedures of this Decision, refer to Central European Time (CET) and
> Eastern European Time (EET).

> 12:00 (CET), D-1 · 13:00 (EET), D-1 — The Day-Ahead Market Gate Closure Time.

**Reading.** The Greek DAM gate closes at 12:00 CET on D-1 under SDAC, which is the declared
closure (`closure_local_time` 12:00 in `Europe/Brussels`, so 10:00 UTC in summer and 11:00 UTC
in winter). This is the version in force at retrieval; the version in force at the November 2020
launch is document 8.

### 6. NEMO Committee — Go-live of the 15-minute MTU confirmed, 12 September 2025

| Field | Value |
| --- | --- |
| Supports | `config/decision_cutoff.json`: the 1 October 2025 resolution change |
| URL | <https://www.nemo-committee.eu/assets/files/market-coupling-steering-committee-confirms-go-live-of-15-minute-mtu-in-sdac-on-trading-day-30-september-2025-for-delivery-day-1-october-2025.pdf> |
| Publisher, date | SDAC press release, 12 September 2025; 2 pages |
| Asset | `www.nemo-committee.eu__market-coupling-steering-committee-confirms-go-live-of-15-minute-mtu-in-sdac-on-trading-day-30-september-2025-for-delivery-day-1-october-2025.pdf` |
| Bytes, SHA-256 | 152,451; `f826d5a0b9f7b3cb6f43ff7437128eff94d62164f371fa23054a0b065bc44aab` |

> Go-live is therefore scheduled for 30 September 2025 (trading day) for delivery day
> 1 October 2025.

### 7. NEMO Committee — Successful implementation of the 15-minute MTU in SDAC, 7 October 2025

| Field | Value |
| --- | --- |
| Supports | `config/decision_cutoff.json`: the 1 October 2025 change happened and changed the market time unit, not the gate |
| URL | <https://www.nemo-committee.eu/assets/files/successful-implementation-of-15-minute-market-time-unit-(mtu)-in-sdac.pdf> |
| Publisher, date | SDAC press release, 7 October 2025; 2 pages |
| Asset | `www.nemo-committee.eu__successful-implementation-of-15-minute-market-time-unit-.mtu.-in-sdac.pdf` |
| Bytes, SHA-256 | 140,215; `c710b9571e81cf60e46ebb392d58ff199f59e1eb495d8c22c89965825fdbc3b6` |

> The SDAC parties are pleased to confirm that the 15-minute MTU in the Single Day-Ahead
> Coupling (SDAC) has successfully gone live on 30 September 2025, for delivery day
> 1 October 2025.

**Reading of 6 and 7 together.** The resolution change is dated as the declaration states, and
neither release announces a change to the order-book gate; document 5, issued after it, still
places the gate at 12:00 CET. The declaration's statement that 1 October 2025 does not create a
further closure regime is consistent with the retained text.

### 8. HEnEx — Decision 10, "Timeline Procedures for the Day-Ahead and Intra-Day Market", of 20 October 2020

| Field | Value |
| --- | --- |
| Supports | `config/decision_cutoff.json`: the closure in force at the 1 November 2020 launch and through the pre-coupling period to 15 December 2020 |
| URL | <https://www.enexgroup.gr/c/document_library/get_file?uuid=e6302200-e51e-5545-21da-4fe48fa1c5cd&groupId=20126> (HEnEx library entry "20201006 Decision 10 en") |
| Publisher, date | Hellenic Energy Exchange S.A., HEnEx ref. 2205/20.10.2020, unofficial English translation as of 20 October 2020; file created 22 October 2020; 14 pages |
| Asset | `www.enexgroup.gr__20201006_Decision_10_en.pdf` |
| Bytes, SHA-256 | 809,966; `ff6ce8415df22ef25b381cc1830419dea3b620eb97bf63efecddaa8348045c97` |

> 3. All times in Timeline procedures of this Decision, refer to Central European Time (CET) and
> Eastern European Time (EET).

> 6. HEnEx publishes, by 12:00 (EET), D-1, the Allocation Constraints.
>
> 12:00 (CET), D-1 · 13:00 (EET), D-1 — The Day-Ahead Market Gate Closure Time.
>
> from 12:00 (CET), D-1 until 12:05 (CET), D-1 — HEnEx anonymizes the Orders submitted to the
> Local Order Book and submit them to the MCO's Shared Order Book.

**Reading.** This is the only day-ahead timeline decision in the HEnEx library that predates the
16 December 2020 coupling; the next version is document 9. It places the gate at 12:00 CET,
13:00 Athens time, from the launch. **It contradicts the 3 September 2026 declaration, which
placed the closure before 2020-12-16 at 12:00 Europe/Athens, one hour earlier.** The declaration
was corrected on 10 September 2026, before any test run, as its own section 1 required
(`docs/fundamentals_declarations_2026-09-03.md`, amendment; `DECISIONS.md`). No admitted feature
exists before 2021-02-27, so no accepted observation is affected. Two things this text does not
settle are recorded rather than assumed: whether HEnEx applied every step of the coupled
procedure it describes during the six isolated weeks, and whether an unpublished intermediate
version existed between October 2020 and September 2021. The gate-closure line is the same in
every retained version, which is what the declaration rests on.

### 9. HEnEx — Decision 10, "Timeline Procedures for the Day-Ahead and Intra-Day Market", of 20 September 2021

| Field | Value |
| --- | --- |
| Supports | `config/decision_cutoff.json`: the closure through the coupled hourly period |
| URL | <https://www.enexgroup.gr/c/document_library/get_file?uuid=cdb8194c-3e2f-fdb0-0aec-bf9964d9bb5f&groupId=20126> (HEnEx library entry "20210920 Decision 10 en") |
| Publisher, date | Hellenic Energy Exchange S.A., HEnEx ref. 1371/20.09.2021, unofficial English translation as of 21 September 2021; 14 pages |
| Asset | `www.enexgroup.gr__20210920_Decision_10_en.pdf` |
| Bytes, SHA-256 | 284,827; `6e610d70c38394eae069cd929415cc15d73d8f4db970c0d9d59f2973245cbd27` |

> 12:00 (CET), D-1 · 13:00 (EET), D-1 — The Day-Ahead Market Gate Closure Time.

**Reading.** Unchanged gate between the 2020 and 2026 versions.

## What the retained text supports, in one table

| Declared element | Supported by | Verdict |
| --- | --- | --- |
| Geography: three regions, 2,293 / 639 / 534 MW at 31 December 2023, weights renormalised | Document 1 | Confirmed exactly |
| Closure 12:00 CET/CEST on D-1 from delivery day 2020-11-01 | Documents 8, 9, 5 | Confirmed; the superseded Athens-clock regime before 2020-12-16 was contradicted and corrected |
| Coupling from delivery day 2020-12-16 | Documents 2, 3 | Confirmed |
| 15-minute market time unit from delivery day 2025-10-01, gate unchanged | Documents 6, 7, 5 | Confirmed |
| Decision lead 0 minutes | none | An operator choice, not a published rule; nothing to retain |

