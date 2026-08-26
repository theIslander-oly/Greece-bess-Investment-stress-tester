# Release notes — v0.6.3

Version 0.6.3 fixes incremental HEnEx daily discovery after the first complete 2026 workflow
attempt exposed a difference between the synthetic catalogue fixture and the live website.

The live HEnEx asset publisher displays labels such as
`20260825_EL-DAM_Results_EN_v01` without the `.xlsx` suffix. Discovery now recognizes that label,
restores the canonical workbook filename, follows the live `/web/guest/` Liferay pagination route
and continues past pages that are newer than the requested range.

The client also rejects repeated catalogue pages and requires every requested delivery day. It
will not silently accept a partial date range. Downloaded files still pass through the existing
HTTPS allowlist, XLSX-container check, revision selection, parser and quality gates.

No official workbook or normalized market dataset is committed.
