"""Deterministic rendering of verified run manifests into a self-contained report.

v0.8.0, the report rendering foundation. The design of record is `docs/v0.8_design.md`, and
one sentence governs every choice in this module:

    A report renders verified manifests, and only verified manifests.

`read_run_manifest` is the sole doorway. Every integrity property the contract enforces — the
schema-version check, the closed kind registry, the basis cross-check, the guaranteed-key check
and the scoped distributional-term refusal — is therefore inherited here rather than restated,
which is what keeps this layer thin by construction instead of by discipline.

What this module deliberately cannot do:

- **Compute.** No dispatch, forecast, transformation, degradation or finance call is reachable
  from it. It formats recorded values; it never derives one. In particular no value is computed
  across manifests or across bases, because such a number's basis would be none of the five the
  contract defines.
- **Read anything but the manifests it is given.** Not the environment, not the network, not a
  path a manifest names in ``declared_inputs``. Official HEnEx and ENTSO-E interval series
  therefore cannot enter an export at all: a manifest carries the producing module's summary,
  and the summary is all the renderer ever sees.
- **Render an unlabeled figure.** The label block is built from the manifest, adjacent to the
  figure rather than in a global footer, and is not optional.

The distributional-term check applies to the renderer's **own** vocabulary — the headings and
key captions it emits for a block whose kind declares ``forbids_distributional_terms`` — and
not to text carried verbatim from the manifest. That scoping is load-bearing: the project's
standing exclusions say "not a probability-calibrated estimate" and "not expected or forecast
investment revenue", so a blanket scan would refuse the very disclaimer the design requires
every figure to carry. The contract has already cleared the manifest's own keys for that kind.
"""

from __future__ import annotations

import html
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import __version__
from ..data.provenance import atomic_write_bytes, sha256_bytes, utc_now_iso
from ..stress.ensemble import FORBIDDEN_REPORT_TERMS
from .contract import (
    REPORT_CONTRACT_VERSION,
    RESULT_BASES,
    RESULT_KINDS,
    STANDING_EXCLUSIONS,
    ReportContractError,
    RunManifest,
    read_run_manifest,
)

REPORT_RENDER_VERSION = 1

REPORT_TITLE = "Greek DAM battery stress tester — recorded run report"

#: The governing rule, stated in the report itself so a reader who meets the file without the
#: repository still meets the rule.
GOVERNING_RULE = (
    "This report renders verified run manifests, and only verified run manifests. Nothing here "
    "was computed while rendering, and no figure of one basis was combined with a figure of "
    "another."
)

#: Each basis in reader-facing words. The wording is what a reader needs before a euro figure
#: means anything; the machine-readable discriminator stays the manifest's own ``basis``.
BASIS_WORDING: dict[str, str] = {
    "historical_replay_upper_bound": (
        "a perfect-foresight ceiling over real history — the most the modelled battery could "
        "have earned knowing every price in advance, never revenue and never a forecast"
    ),
    "historical_forecast_backtest": (
        "a settled backtest — a strictly time-ordered forecast planned in advance and settled "
        "at the prices that actually occurred"
    ),
    "synthetic_scenario": (
        "a synthetic scenario — resampled or explicitly transformed prices, which are neither "
        "history nor a forecast and carry no probability"
    ),
    "screening_arithmetic": (
        "screening arithmetic — a transparent calculation over a supplied operating path and "
        "illustrative assumptions, not a project valuation"
    ),
    "data_acceptance_evidence": (
        "data-acceptance evidence — a statement about published data, not about investment "
        "outcomes"
    ),
}

#: Heading for each basis group. Grouping by basis makes the ceiling/backtest/scenario
#: distinction the structure of the document rather than a footnote.
BASIS_HEADING: dict[str, str] = {
    "historical_replay_upper_bound": "Historical replay upper bounds",
    "historical_forecast_backtest": "Historical forecast backtests",
    "synthetic_scenario": "Synthetic scenarios",
    "screening_arithmetic": "Screening arithmetic",
    "data_acceptance_evidence": "Data-acceptance evidence",
}


class ReportRenderError(ReportContractError):
    """Raised when a report cannot be rendered exactly as the manifests recorded it.

    It subclasses the contract's error deliberately: a rendering refusal and a contract refusal
    are the same kind of event to a caller, and neither produces a partial report.
    """


@dataclass(frozen=True)
class DeclarationRequirement:
    """One judgmental input this project refuses to default, and how to declare it."""

    input_name: str
    must_declare: str
    decision: str
    decided_on: str
    records_a_result_with: str


#: The landing state. Every judgmental input below has no default by recorded decision, so an
#: interface that rendered something before they are declared would make that something the de
#: facto default. The honest third option between a blank page and a demo with implied defaults
#: is a refusal with instructions, which is what this checklist is.
DECLARATION_CHECKLIST: tuple[DeclarationRequirement, ...] = (
    DeclarationRequirement(
        input_name="Bootstrap source era",
        must_declare=(
            "the first and last day of the historical era resampled, and its interval "
            "resolution. There is no default and no most-recent rule"
        ),
        decision="Require an explicit bootstrap source era, with no default",
        decided_on="2026-08-27",
        records_a_result_with="greek-bess generate-bootstrap-paths --config <bootstrap.json>",
    ),
    DeclarationRequirement(
        input_name="Spread-compression factor and reference basis",
        must_declare=(
            "the compression factor and the daily reference each interval is compressed "
            "toward. The reference basis has no default because the choice is the scenario"
        ),
        decision="Compress spread about a declared daily reference, with no default basis",
        decided_on="2026-08-28",
        records_a_result_with="greek-bess compress-spread --config <compression.json>",
    ),
    DeclarationRequirement(
        input_name="Availability baseline and outage windows",
        must_declare=(
            "the baseline available fraction, plus every outage window and its own available "
            "fraction. Outages are declared, never sampled, inferred or fitted"
        ),
        decision="Declare outages, never sample them",
        decided_on="2026-08-31",
        records_a_result_with=(
            "greek-bess dispatch-bootstrap-paths --availability-schedule <availability.json>"
        ),
    ),
    DeclarationRequirement(
        input_name="Negative-price event list",
        must_declare=(
            "every event window and its strictly negative replacement price. Timing and depth "
            "have no defaults; an empty list is the exact identity transformation"
        ),
        decision="Define negative-price events as declared interval replacements",
        decided_on="2026-08-31",
        records_a_result_with=(
            "greek-bess apply-negative-price-events --config <events.json>"
        ),
    ),
    DeclarationRequirement(
        input_name="Scenario set of an ensemble",
        must_declare=(
            "every scenario, by name, in a manifest. There is no default scenario set and no "
            "implicit baseline, so a range is a range across stated judgments"
        ),
        decision="Report scenario ranges as judgments, and refuse an unequal basis",
        decided_on="2026-08-31",
        records_a_result_with="greek-bess report-scenario-ensemble --manifest <scenarios.json>",
    ),
)


@dataclass(frozen=True)
class RenderedFigure:
    """One value as it appears in the report, and the manifest key it was read from.

    Every figure in a rendered report is one of these, so "no figure was computed while
    rendering" is checkable rather than asserted: each entry names the manifest and the summary
    key its text came from.
    """

    manifest_id: str
    result_kind: str
    basis: str
    key: str
    value_text: str
    is_headline: bool


@dataclass(frozen=True)
class RenderedReport:
    """A rendered report: the document, its audit index and every figure it contains."""

    html: str
    index: Mapping[str, Any]
    figures: tuple[RenderedFigure, ...]

    @property
    def is_landing_state(self) -> bool:
        return not self.figures and self.index["manifest_count"] == 0


@dataclass(frozen=True)
class _Source:
    manifest: RunManifest
    digest: str


def render_report(
    manifest_paths: Sequence[Path] | None = None,
    *,
    rendered_at_utc: str | None = None,
) -> RenderedReport:
    """Render verified manifests, or the declaration checklist when there are none.

    Every manifest is read through :func:`read_run_manifest`, so a manifest this build cannot
    honor refuses the whole report rather than being skipped: a report that silently omitted a
    failing manifest would present the remainder as the whole.
    """

    sources = _verified_sources(manifest_paths or ())
    figures: list[RenderedFigure] = []
    if sources:
        body = _render_manifest_body(sources, figures)
    else:
        body = _render_declaration_checklist()
    document = _document(body)
    index = _index(sources, tuple(figures), rendered_at_utc=rendered_at_utc)
    return RenderedReport(html=document, index=index, figures=tuple(figures))


def write_report(
    report: RenderedReport, output: Path, *, index_path: Path | None = None
) -> Path:
    """Write the report and its index, and return the index path actually written."""

    if output.suffix.lower() != ".html":
        raise ReportRenderError("A rendered report is written as a self-contained .html file")
    resolved_index = index_path or output.with_suffix(".index.json")
    atomic_write_bytes(output, report.html.encode("utf-8"))
    atomic_write_bytes(
        resolved_index,
        (json.dumps(dict(report.index), indent=2, default=str) + "\n").encode("utf-8"),
    )
    return resolved_index


def _verified_sources(manifest_paths: Sequence[Path]) -> tuple[_Source, ...]:
    sources: list[_Source] = []
    seen: set[str] = set()
    for path in manifest_paths:
        location = Path(path)
        digest = sha256_bytes(location.read_bytes())
        manifest = read_run_manifest(location)
        if manifest.manifest_id in seen:
            raise ReportRenderError(
                f"Two inputs declare manifest_id {manifest.manifest_id!r}. A manifest ID names "
                "one recorded run, and a report that listed it twice would present one run as "
                "two; give the runs distinct IDs or render them separately"
            )
        seen.add(manifest.manifest_id)
        sources.append(_Source(manifest=manifest, digest=digest))
    return tuple(sorted(sources, key=_sort_key))


def _sort_key(source: _Source) -> tuple[int, str, str]:
    """Declared ordering: basis, then kind, then manifest ID — never input order."""

    manifest = source.manifest
    return (RESULT_BASES.index(manifest.basis), manifest.result_kind, manifest.manifest_id)


def _render_manifest_body(sources: Sequence[_Source], figures: list[RenderedFigure]) -> str:
    anchors = _anchors(sources)
    parts: list[str] = [
        "<p class=\"governing-rule\">" + html.escape(GOVERNING_RULE) + "</p>",
        _render_contents(sources, anchors),
    ]
    for basis in RESULT_BASES:
        grouped = [source for source in sources if source.manifest.basis == basis]
        if not grouped:
            continue
        parts.append("<section class=\"basis-group\">")
        parts.append(f"<h2>{html.escape(BASIS_HEADING[basis])}</h2>")
        parts.append(
            "<p class=\"basis-wording\">Every figure below is "
            + html.escape(BASIS_WORDING[basis])
            + ".</p>"
        )
        for source in grouped:
            parts.append(_render_manifest(source, anchors, figures))
        parts.append("</section>")
    return "\n".join(parts)


def _render_contents(sources: Sequence[_Source], anchors: Mapping[str, str]) -> str:
    rows = [
        "<tr><th scope=\"col\">Manifest</th><th scope=\"col\">Result kind</th>"
        "<th scope=\"col\">Basis</th><th scope=\"col\">Recorded</th></tr>"
    ]
    for source in sources:
        manifest = source.manifest
        rows.append(
            "<tr>"
            f"<td><a href=\"#{html.escape(anchors[manifest.manifest_id])}\">"
            f"{html.escape(manifest.manifest_id)}</a></td>"
            f"<td>{html.escape(manifest.result_kind)}</td>"
            f"<td>{html.escape(manifest.basis)}</td>"
            f"<td>{html.escape(manifest.created_at_utc)}</td>"
            "</tr>"
        )
    return (
        "<section class=\"contents\"><h2>Manifests rendered</h2>"
        "<table>" + "".join(rows) + "</table></section>"
    )


def _render_manifest(
    source: _Source, anchors: Mapping[str, str], figures: list[RenderedFigure]
) -> str:
    manifest = source.manifest
    kind = RESULT_KINDS[manifest.result_kind]
    headline_keys = tuple(
        key for key in kind.required_summary_keys if key != "result_label"
    )
    rendered_elsewhere = {*headline_keys, "result_label"}
    detail_keys = tuple(key for key in manifest.summary if key not in rendered_elsewhere)

    headline_rows = [
        _figure_row(source, key, is_headline=True, figures=figures) for key in headline_keys
    ]
    detail_rows = [
        _figure_row(source, key, is_headline=False, figures=figures) for key in detail_keys
    ]

    chrome = [
        kind.description,
        "What this figure is",
        "Recorded detail",
        "Declared inputs",
        "Provenance",
        *(_caption(key) for key in (*headline_keys, *detail_keys)),
    ]
    if kind.forbids_distributional_terms:
        _refuse_distributional_vocabulary(manifest.result_kind, chrome)

    headline_block = (
        "<table class=\"headline\">" + "".join(headline_rows) + "</table>"
        if headline_rows
        else ""
    )
    detail_block = (
        "<h4>Recorded detail</h4><table class=\"detail\">" + "".join(detail_rows) + "</table>"
        if detail_rows
        else ""
    )
    return (
        "<article class=\"figure-block\" "
        f"id=\"{html.escape(anchors[manifest.manifest_id])}\">"
        f"<h3>{html.escape(manifest.manifest_id)}</h3>"
        f"<p class=\"kind-description\">{html.escape(kind.description)}</p>"
        f"{headline_block}"
        f"{_render_label_block(source)}"
        f"{detail_block}"
        f"{_render_declared_inputs(manifest)}"
        f"{_render_provenance(source)}"
        "</article>"
    )


def _render_label_block(source: _Source) -> str:
    """The label, the basis in words and the standing exclusions, adjacent to the figure.

    Every element here is read from the manifest. The renderer never re-declares a label, so it
    cannot drift from the sentence the producing module wrote.
    """

    manifest = source.manifest
    exclusions = "".join(
        f"<li>{html.escape(exclusion)}</li>" for exclusion in STANDING_EXCLUSIONS
    )
    return (
        "<aside class=\"label-block\">"
        "<h4>What this figure is</h4>"
        f"<p class=\"result-label\">{html.escape(manifest.result_label)}</p>"
        f"<p class=\"basis\">This is {html.escape(BASIS_WORDING[manifest.basis])}.</p>"
        f"<ul class=\"standing-exclusions\">{exclusions}</ul>"
        "</aside>"
    )


def _render_declared_inputs(manifest: RunManifest) -> str:
    if not manifest.declared_inputs:
        return ""
    rows = "".join(
        f"<tr><th scope=\"row\">{html.escape(_caption(str(key)))}</th>"
        f"<td>{html.escape(_format_value(value))}</td></tr>"
        for key, value in manifest.declared_inputs.items()
    )
    return f"<h4>Declared inputs</h4><table class=\"declared-inputs\">{rows}</table>"


def _render_provenance(source: _Source) -> str:
    manifest = source.manifest
    rows = (
        ("Produced by", manifest.produced_by),
        ("Recorded at", manifest.created_at_utc),
        ("Project version", manifest.project_version),
        ("Manifest digest", source.digest),
    )
    body = "".join(
        f"<tr><th scope=\"row\">{html.escape(caption)}</th><td>{html.escape(value)}</td></tr>"
        for caption, value in rows
    )
    return f"<h4>Provenance</h4><table class=\"provenance\">{body}</table>"


def _figure_row(
    source: _Source, key: str, *, is_headline: bool, figures: list[RenderedFigure]
) -> str:
    manifest = source.manifest
    value_text = _format_value(manifest.summary[key])
    figures.append(
        RenderedFigure(
            manifest_id=manifest.manifest_id,
            result_kind=manifest.result_kind,
            basis=manifest.basis,
            key=key,
            value_text=value_text,
            is_headline=is_headline,
        )
    )
    return (
        f"<tr><th scope=\"row\">{html.escape(_caption(key))}</th>"
        f"<td><span class=\"figure-value\">{html.escape(value_text)}</span></td></tr>"
    )


def _caption(key: str) -> str:
    return key.replace("_", " ")


def _format_value(value: Any) -> str:
    """Format a recorded value without changing it.

    Strings pass through; everything else is rendered as the JSON it was recorded as, so no
    rounding, unit conversion or other quiet transformation can happen between the manifest and
    the page.
    """

    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _refuse_distributional_vocabulary(kind_id: str, phrases: Iterable[str]) -> None:
    """Refuse renderer vocabulary that would read as a claim about a distribution.

    Scoped to the renderer's own headings and captions for kinds that declare it. Text carried
    verbatim from the manifest is exempt: the contract has already cleared that kind's summary
    keys, and the standing exclusions this design requires beside every figure themselves say
    "not a probability-calibrated estimate" — scanning them would refuse the disclaimer.
    """

    for phrase in phrases:
        lowered = phrase.lower()
        for term in FORBIDDEN_REPORT_TERMS:
            if term in lowered:
                raise ReportRenderError(
                    f"Refusing to render {kind_id} with the caption {phrase!r}: it reads as "
                    f"{term!r}, and this result kind reports a range across named judgments "
                    "rather than a distribution over outcomes"
                )


def _anchors(sources: Sequence[_Source]) -> dict[str, str]:
    """Assign one readable, unique in-document anchor per manifest.

    Manifest IDs are refused when they repeat, but two distinct IDs can still reduce to the same
    readable anchor, which would put two elements behind one fragment identifier. Sources are
    already in the report's declared order, so a positional suffix disambiguates without making
    the anchor depend on input order.
    """

    anchors: dict[str, str] = {}
    taken: set[str] = set()
    for position, source in enumerate(sources):
        manifest_id = source.manifest.manifest_id
        safe = "".join(
            character if character.isalnum() else "-" for character in manifest_id.lower()
        )
        anchor = f"manifest-{safe}"
        if anchor in taken:
            anchor = f"{anchor}-{position}"
        taken.add(anchor)
        anchors[manifest_id] = anchor
    return anchors


def _render_declaration_checklist() -> str:
    items: list[str] = []
    for requirement in DECLARATION_CHECKLIST:
        items.append(
            "<article class=\"declaration\">"
            f"<h3>{html.escape(requirement.input_name)}</h3>"
            f"<p class=\"must-declare\">You must declare {html.escape(requirement.must_declare)}."
            "</p>"
            "<p class=\"decision\">Recorded decision, "
            f"{html.escape(requirement.decided_on)}: "
            f"<em>{html.escape(requirement.decision)}</em>.</p>"
            "<p class=\"records-with\">Records a result with "
            f"<code>{html.escape(requirement.records_a_result_with)}</code></p>"
            "</article>"
        )
    return (
        "<p class=\"governing-rule\">" + html.escape(GOVERNING_RULE) + "</p>"
        "<section class=\"landing-state\">"
        "<h2>Nothing has been declared yet, so there is nothing to report</h2>"
        "<p>This report was rendered with no run manifests. It shows no figures on purpose. "
        "Every judgmental input below has no default by recorded decision, and a page that "
        "showed an example result before they were declared would quietly settle each of the "
        "trade-offs the decision log deliberately refused to settle. What follows is the "
        "declaration checklist instead: what to declare, the decision that made it "
        "default-free, and the command that records a result once you have declared it.</p>"
        + "".join(items)
        + "<section class=\"how-to\">"
        "<h3>Then record the result and render it</h3>"
        "<p>Each command above writes a summary. Record that summary under the run-manifest "
        "contract, then render the manifest — a report reads verified manifests and nothing "
        "else:</p>"
        "<pre><code>greek-bess record-run-manifest &lt;result.summary.json&gt; \\\n"
        "  --result-kind &lt;kind&gt; --manifest-id &lt;id&gt; --produced-by &lt;command&gt; \\\n"
        "  --output &lt;result.manifest.json&gt;\n\n"
        "greek-bess render-report &lt;result.manifest.json&gt; --output &lt;report.html&gt;"
        "</code></pre>"
        "</section>"
        "</section>"
    )


def _index(
    sources: Sequence[_Source],
    figures: Sequence[RenderedFigure],
    *,
    rendered_at_utc: str | None,
) -> dict[str, Any]:
    """The machine-readable audit index.

    A manifest is identified by its ID and the digest of the exact bytes rendered, never by its
    path on the machine that rendered it: an export travels, and the operator's directory layout
    is not part of the evidence.
    """

    return {
        "report_render_version": REPORT_RENDER_VERSION,
        "report_contract_version": REPORT_CONTRACT_VERSION,
        "project_version": __version__,
        "rendered_at_utc": rendered_at_utc or utc_now_iso(),
        "state": "rendered_manifests" if sources else "declaration_checklist",
        "manifest_count": len(sources),
        "figure_count": len(figures),
        "bases_rendered": [
            basis
            for basis in RESULT_BASES
            if any(source.manifest.basis == basis for source in sources)
        ],
        "standing_exclusions": list(STANDING_EXCLUSIONS),
        "manifests": [
            {
                "manifest_id": source.manifest.manifest_id,
                "result_kind": source.manifest.result_kind,
                "basis": source.manifest.basis,
                "result_label": source.manifest.result_label,
                "produced_by": source.manifest.produced_by,
                "project_version": source.manifest.project_version,
                "created_at_utc": source.manifest.created_at_utc,
                "manifest_sha256": source.digest,
                "rendered_figure_keys": [
                    figure.key
                    for figure in figures
                    if figure.manifest_id == source.manifest.manifest_id
                ],
            }
            for source in sources
        ],
    }


def _document(body: str) -> str:
    """Wrap a body in a self-contained document: no scripts, no external assets, no fetches."""

    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html.escape(REPORT_TITLE)}</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n"
        "<body>\n"
        f"<header><h1>{html.escape(REPORT_TITLE)}</h1></header>\n"
        f"<main>\n{body}\n</main>\n"
        f"<footer>{_FOOTER}</footer>\n"
        "</body>\n"
        "</html>\n"
    )


_FOOTER = (
    "Rendered by the Greek DAM battery stress tester from run manifests under report contract "
    f"version {REPORT_CONTRACT_VERSION}, renderer version {REPORT_RENDER_VERSION}, project "
    f"version {html.escape(__version__)}. This is research tooling: it is not financial advice, "
    "an investment-grade forecast or a bankable study."
)

_STYLE = """
:root { color-scheme: light dark; }
body { font-family: system-ui, sans-serif; line-height: 1.5; margin: 0 auto; max-width: 52rem;
  padding: 1.5rem; }
header h1 { font-size: 1.4rem; }
h2 { border-bottom: 1px solid currentColor; font-size: 1.15rem; margin-top: 2.5rem;
  padding-bottom: 0.25rem; }
h3 { font-size: 1.05rem; margin-bottom: 0.25rem; }
h4 { font-size: 0.9rem; letter-spacing: 0.04em; margin-bottom: 0.25rem;
  text-transform: uppercase; }
p { margin: 0.5rem 0; }
table { border-collapse: collapse; margin: 0.5rem 0; width: 100%; }
th, td { border-bottom: 1px solid rgba(127, 127, 127, 0.35); padding: 0.35rem 0.5rem;
  text-align: left; vertical-align: top; }
th[scope="row"] { font-weight: 600; width: 40%; }
td { overflow-wrap: anywhere; }
pre { overflow-x: auto; padding: 0.5rem; }
code, pre, .figure-value { font-family: ui-monospace, monospace; }
.governing-rule { font-weight: 600; }
.figure-block, .declaration { border: 1px solid rgba(127, 127, 127, 0.45); border-radius: 4px;
  margin: 1.25rem 0; padding: 0.75rem 1rem; }
.headline .figure-value { font-size: 1.1rem; }
.label-block { border-left: 4px solid currentColor; margin: 0.75rem 0; padding: 0.25rem 0.9rem; }
.result-label { font-style: italic; }
.standing-exclusions { margin: 0.25rem 0 0.25rem 1rem; padding: 0; }
.kind-description, .basis-wording { opacity: 0.85; }
footer { border-top: 1px solid currentColor; font-size: 0.85rem; margin-top: 3rem;
  padding-top: 0.75rem; }
"""
