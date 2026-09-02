"""Deterministic rendering of verified run manifests into a self-contained report.

v0.8.0, the report rendering foundation. The design of record is `docs/v0.8_design.md`, and
one sentence governs every choice in this module:

    A report renders verified manifests, and only verified manifests.

`read_run_manifest` is the sole doorway, so every integrity property that doorway enforces —
the schema-version check, the closed kind registry, the basis cross-check, the standing-claim
cross-check and the scoped distributional-term refusal — is inherited here rather than restated,
which is what keeps this layer thin by construction instead of by discipline.

The one check the doorway deliberately does not apply is the guaranteed-key check, which the
contract runs when a manifest is built rather than when one is read so that a manifest recorded
before its kind guaranteed a key still verifies. This module therefore states such a key as not
recorded, exactly as it states any other value a manifest does not carry, rather than assuming
it is present or inventing one.

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

v0.8.1 adds composition across manifests, and composition is layout only. An index names
every manifest the report carries and where to find it, and deliberately carries no figure at
all: a table spanning two bases is exactly where a figure of one basis would end up beside — and
then inside — a figure of another. A scenario ensemble's per-path ranges, its per-scenario
provenance and the equivalent-basis evidence it recorded are laid out side by side, and every
cell of every one of those tables is still one recorded value of one manifest, walked back to
its exact place in that manifest's summary by ``RenderedFigure.summary_path``.

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
from decimal import Decimal, InvalidOperation
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

REPORT_RENDER_VERSION = 3

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

#: What the index across manifests is, stated in the index itself. The temptation a multi-manifest
#: report creates is a summary table spanning the whole report, and that table is where a figure
#: of one basis would first sit beside a figure of another and then be combined with it.
INDEX_RULE = (
    "This index is layout across manifests, not a result across them. It names what the report "
    "contains and where to find it, and it carries no figure at all. Every figure stays inside "
    "its own manifest's block below, beside the label that says what it is and what it is not."
)

#: The composition sections a result kind lays out itself, as (summary key, section name) pairs
#: in rendering order. A key listed here is rendered by its section and not also as a generic
#: headline or detail row, so one recorded value appears exactly once.
COMPOSITION_SECTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "scenario_ensemble_range": (
        ("scenarios", "scenarios_side_by_side"),
        ("equivalent_basis", "equivalent_basis"),
        ("path_ranges", "per_path_ranges"),
    ),
}

#: The per-scenario provenance rows of the side-by-side table, as (caption, path within the
#: scenario's recorded entry). The order is what a reader needs in order: which recorded run,
#: what judgment was applied to it, what availability was declared, and over how many paths.
SCENARIO_PROVENANCE_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Recorded run", ("input_run_id",)),
    ("Transformation", ("transformation", "method")),
    ("Transformation identifier", ("transformation", "transformation_id")),
    ("Transformation parameters", ("transformation", "parameters")),
    ("Declared availability", ("availability",)),
    ("Source era", ("source_era",)),
    ("Bootstrap configuration", ("bootstrap_configuration",)),
    ("Paths dispatched", ("path_count",)),
)

#: Heading and lead paragraph for each composition section. They are renderer vocabulary, so
#: they are checked against ``FORBIDDEN_REPORT_TERMS`` for a kind that declares it.
COMPOSITION_HEADINGS: dict[str, str] = {
    "scenarios_side_by_side": "Scenarios side by side",
    "equivalent_basis": "The basis every scenario shared",
    "per_path_ranges": "Range per bootstrap path",
}

COMPOSITION_LEADS: dict[str, str] = {
    "scenarios_side_by_side": (
        "One column per named scenario, in the order the scenarios were declared. There is no "
        "baseline column and no default scenario set: every scenario here was named by the "
        "caller, and an untransformed replay is one of the named scenarios rather than an "
        "implicit reference."
    ),
    "equivalent_basis": (
        "These are the properties every scenario was required to share before the ensemble "
        "would place them in one range at all. A difference in any of them is refused and "
        "named rather than reconciled, because comparing strategies only under equivalent "
        "physical and terminal-energy constraints is a standing project invariant."
    ),
    "per_path_ranges": (
        "One row per bootstrap path: the lowest and the highest margin any named scenario "
        "produced for that path, which scenario attained each end, and the spread between "
        "them. Nothing is totalled or combined across paths, and nothing here is ordered by "
        "anything but path identity. The scenario names join these rows to the provenance "
        "above, which is recorded once per scenario rather than repeated per path."
    ),
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
        input_name="Decision cutoff and decision lead",
        must_declare=(
            "the day-ahead closure schedule a point-in-time feature is judged against, with a "
            "rulebook citation and one dated regime per rule change, and the decision lead in "
            "minutes. Neither has a default; a publication at the cutoff is late"
        ),
        decision="Admit exogenous features only when provably available before a declared "
        "cutoff, with graded evidence",
        decided_on="2026-09-02",
        records_a_result_with=(
            "greek-bess audit-feature-availability --decision-cutoff <cutoff.json> "
            "--decision-lead-minutes <minutes>"
        ),
    ),
    DeclarationRequirement(
        input_name="Sampling geography of a gridded feature",
        must_declare=(
            "every point a gridded variable is sampled at, the weight each carries and what the "
            "choice represents. There is no default geography and no implicit centroid"
        ),
        decision="Sample gridded fundamentals at declared, weighted points with a stated basis",
        decided_on="2026-09-02",
        records_a_result_with="greek-bess fetch-fundamentals --geography <geography.json>",
    ),
    DeclarationRequirement(
        input_name="Price-regime bands of a forecast benchmark",
        must_declare=(
            "the ascending price levels the reported slices are cut at, in EUR/MWh. There is "
            "no default, because which regimes are worth separating is the judgment being made"
        ),
        decision="Slice benchmark accuracy at declared price regimes, never at inferred ones",
        decided_on="2026-09-02",
        records_a_result_with=(
            "greek-bess benchmark-fundamentals-forecast --price-regime-bands <edges>"
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

    ``summary_path`` is where that value sits inside the manifest's summary —
    ``("interval_count",)`` for a top-level figure, ``("path_ranges", 3, "spread_...")`` for one
    cell of a composition table. Composition lays recorded values out beside each other, so the
    check that nothing was computed has to reach into the layout rather than stop at the top
    level of the summary.
    """

    manifest_id: str
    result_kind: str
    basis: str
    key: str
    value_text: str
    is_headline: bool
    summary_path: tuple[str | int, ...]


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
        _render_index_section(sources, anchors),
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


def _render_index_section(sources: Sequence[_Source], anchors: Mapping[str, str]) -> str:
    """The index across every manifest the report carries.

    It is grouped by basis, names each manifest by ID, kind, label, producing command, recorded
    time and digest, and links to the block that holds its figures. It carries no figure itself,
    deliberately: an index is the one table in a multi-manifest report that spans bases, and a
    number placed in it would be a number sitting outside the basis grouping that makes the rest
    of the document readable.
    """

    present = _bases_present(sources)
    absent = [basis for basis in RESULT_BASES if basis not in present]
    manifest_word = "manifest" if len(sources) == 1 else "manifests"
    group_word = "basis" if len(present) == 1 else "bases"
    parts: list[str] = [
        "<section class=\"report-index\">",
        "<h2>Index of rendered manifests</h2>",
        "<p class=\"index-composition\">"
        + html.escape(
            f"This report carries {len(sources)} run {manifest_word}, in "
            f"{len(present)} of the five recorded {group_word}."
        )
        + "</p>",
        "<p class=\"index-rule\">" + html.escape(INDEX_RULE) + "</p>",
    ]
    for basis in present:
        parts.append(f"<h3>{html.escape(BASIS_HEADING[basis])}</h3>")
        parts.append(
            "<p class=\"basis-wording\">Every figure in this group is "
            + html.escape(BASIS_WORDING[basis])
            + ".</p>"
        )
        rows = [
            "<tr><th scope=\"col\">Manifest</th><th scope=\"col\">Result kind</th>"
            "<th scope=\"col\">What it is</th><th scope=\"col\">Produced by</th>"
            "<th scope=\"col\">Recorded</th><th scope=\"col\">Manifest digest</th></tr>"
        ]
        for source in sources:
            manifest = source.manifest
            if manifest.basis != basis:
                continue
            rows.append(
                "<tr>"
                f"<td><a href=\"#{html.escape(anchors[manifest.manifest_id])}\">"
                f"{html.escape(manifest.manifest_id)}</a></td>"
                f"<td>{html.escape(manifest.result_kind)}</td>"
                f"<td class=\"index-label\">{html.escape(manifest.result_label)}</td>"
                f"<td>{html.escape(manifest.produced_by)}</td>"
                f"<td>{html.escape(manifest.created_at_utc)}</td>"
                f"<td class=\"digest\">{html.escape(source.digest)}</td>"
                "</tr>"
            )
        parts.append("<table class=\"index-table\">" + "".join(rows) + "</table>")
    parts.append(_render_bases_absent(absent))
    parts.append("</section>")
    return "".join(parts)


def _render_bases_absent(absent: Sequence[str]) -> str:
    """Say which of the five bases this report does not cover.

    A reader cannot tell an absent basis from an absent question. Naming what is missing keeps a
    report from reading as the whole of what the project can record.
    """

    if not absent:
        return (
            "<p class=\"bases-absent\">All five recorded bases are represented in this "
            "report.</p>"
        )
    named = ", ".join(BASIS_HEADING[basis].lower() for basis in absent)
    return (
        "<p class=\"bases-absent\">Not represented in this report: "
        f"{html.escape(named)}. An absent basis is a question this report does not answer, not "
        "a question with no answer.</p>"
    )


def _bases_present(sources: Sequence[_Source]) -> list[str]:
    return [
        basis
        for basis in RESULT_BASES
        if any(source.manifest.basis == basis for source in sources)
    ]


def _render_manifest(
    source: _Source, anchors: Mapping[str, str], figures: list[RenderedFigure]
) -> str:
    manifest = source.manifest
    kind = RESULT_KINDS[manifest.result_kind]
    composition_keys = _composition_keys(manifest.result_kind)
    headline_keys = tuple(
        key
        for key in kind.required_summary_keys
        if key != "result_label" and key not in composition_keys
    )
    rendered_elsewhere = {*headline_keys, *composition_keys, "result_label"}
    detail_keys = tuple(key for key in manifest.summary if key not in rendered_elsewhere)

    if kind.forbids_distributional_terms:
        _refuse_distributional_vocabulary(
            manifest.result_kind,
            [
                kind.description,
                "What this figure is",
                "Recorded detail",
                "Declared inputs",
                "Provenance",
                *(_caption(key) for key in (*headline_keys, *detail_keys)),
                *_composition_chrome(source),
            ],
        )

    headline_rows = [
        _figure_row(source, key, is_headline=True, figures=figures) for key in headline_keys
    ]
    detail_rows = [
        _figure_row(source, key, is_headline=False, figures=figures) for key in detail_keys
    ]

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
        f"{_render_charts(source)}"
        f"{_render_composition(source, figures)}"
        f"{detail_block}"
        f"{_render_declared_inputs(manifest)}"
        f"{_render_provenance(source)}"
        "</article>"
    )


def _render_charts(source: _Source) -> str:
    """Render deterministic views of values already recorded by one manifest.

    Chart coordinates are presentation geometry, not reported quantities: every visible value
    is the manifest's exact text, and the SVG neither adds a statistic nor combines manifests.
    The closed dispatch below also prevents a manifest from selecting a file or another data
    source merely by naming it.
    """

    if source.manifest.result_kind != "scenario_ensemble_range":
        return ""
    key = "path_ranges"
    if key not in source.manifest.summary:
        return _chart_absent(key)
    recorded = source.manifest.summary[key]
    if not isinstance(recorded, Sequence) or isinstance(recorded, (str, bytes)):
        return _chart_absent(key)
    if not recorded:
        return _chart_absent(key, empty=True)
    if any(not isinstance(row, Mapping) for row in recorded):
        return _chart_absent(key)

    metrics = (
        ("minimum_net_market_margin_eur", "Minimum", "minimum"),
        ("maximum_net_market_margin_eur", "Maximum", "maximum"),
        ("spread_net_market_margin_eur", "Spread", "spread"),
    )
    values: list[Decimal] = []
    for row in recorded:
        for key_name, _, _ in metrics:
            if key_name not in row:
                continue
            numeric = _chart_number(row[key_name])
            if numeric is not None:
                values.append(numeric)
    if not values:
        return _chart_absent(key)

    width = Decimal(720)
    left = Decimal(150)
    plot_width = Decimal(540)
    row_height = Decimal(82)
    top = Decimal(40)
    height = top + row_height * len(recorded) + Decimal(36)
    low = min(Decimal(0), *values)
    high = max(Decimal(0), *values)
    span = high - low
    if span == 0:
        span = Decimal(1)

    def x(value: Decimal) -> Decimal:
        return left + (value - low) * plot_width / span

    zero_x = x(Decimal(0))
    identifier = source.digest[:12]
    title_id = f"path-range-chart-title-{identifier}"
    description_id = f"path-range-chart-description-{identifier}"
    elements = [
        '<svg class="manifest-chart" role="img" '
        f'aria-labelledby="{title_id} {description_id}" '
        f'viewBox="0 0 {_svg_number(width)} {_svg_number(height)}">',
        f'<title id="{title_id}">Recorded range values by bootstrap path</title>',
        f'<desc id="{description_id}">Minimum, maximum and spread values exactly '
        'as recorded in this manifest. Text, opacity, outline, dash and shape distinguish '
        'the series.</desc>',
        f'<line class="chart-zero" x1="{_svg_number(zero_x)}" y1="24" '
        f'x2="{_svg_number(zero_x)}" y2="{_svg_number(height - 24)}"/>',
    ]
    for position, row in enumerate(recorded):
        path_text = _format_value(row.get("path_id")) if "path_id" in row else "not recorded"
        base_y = top + row_height * position
        elements.append(
            f'<text class="chart-path" x="8" y="{_svg_number(base_y + 18)}">'
            f'Path {html.escape(path_text)}</text>'
        )
        for metric_position, (key_name, caption, css_class) in enumerate(metrics):
            if key_name not in row:
                continue
            numeric = _chart_number(row[key_name])
            if numeric is None:
                continue
            value_x = x(numeric)
            bar_x = min(zero_x, value_x)
            bar_width = abs(value_x - zero_x)
            y = base_y + Decimal(4 + metric_position * 22)
            value_text = _format_value(row[key_name])
            shape = ' rx="7"' if css_class == "maximum" else ""
            elements.extend(
                (
                    f'<rect class="chart-bar chart-{css_class}"{shape} '
                    f'x="{_svg_number(bar_x)}" '
                    f'y="{_svg_number(y)}" width="{_svg_number(bar_width)}" height="14"/>',
                    f'<text class="chart-value" x="{_svg_number(left)}" '
                    f'y="{_svg_number(y + 12)}">{html.escape(caption)}: '
                    f'{html.escape(value_text)}</text>',
                )
            )
    elements.append("</svg>")
    return (
        '<section class="chart-section"><h4>Recorded path ranges — chart</h4>'
        '<p class="chart-note">This chart plots only values recorded in this manifest; '
        'position and bar length are rendering geometry, not newly reported quantities.</p>'
        + "".join(elements)
        + "</section>"
    )


def _chart_number(value: Any) -> Decimal | None:
    """Return a finite recorded JSON number for SVG placement, excluding booleans."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        numeric = Decimal(str(value))
    except InvalidOperation:
        return None
    return numeric if numeric.is_finite() else None


def _svg_number(value: Decimal) -> str:
    """Canonical fixed-point SVG number formatting for byte determinism."""

    return format(value.quantize(Decimal("0.001")), "f").rstrip("0").rstrip(".") or "0"


def _chart_absent(key: str, *, empty: bool = False) -> str:
    state = "an empty" if empty else "no usable"
    return (
        '<section class="chart-section"><h4>Recorded path ranges — chart</h4>'
        f'<p class="chart-unavailable">This manifest records {state} '
        f'<code>{html.escape(key)}</code> value, so no chart is shown.</p></section>'
    )


def _composition_keys(result_kind: str) -> tuple[str, ...]:
    return tuple(key for key, _ in COMPOSITION_SECTIONS.get(result_kind, ()))


def _composition_chrome(source: _Source) -> list[str]:
    """Every phrase a composition section would emit in its own voice.

    That includes the nested key names it turns into column headings and row captions. The
    contract clears those names when the manifest is built; checking them again here is what
    keeps the rule "the renderer checks what the renderer says" true now that the renderer says
    nested key names out loud.
    """

    phrases: list[str] = []
    summary = source.manifest.summary
    for key, section in COMPOSITION_SECTIONS.get(source.manifest.result_kind, ()):
        phrases.append(COMPOSITION_HEADINGS[section])
        phrases.append(COMPOSITION_LEADS[section])
        if key not in summary:
            continue
        if section == "scenarios_side_by_side":
            phrases.extend(caption for caption, _ in SCENARIO_PROVENANCE_ROWS)
            phrases.append("Scenario")
        elif section == "equivalent_basis":
            phrases.extend(_caption(name) for name in _equivalent_basis_captions(summary[key]))
        elif section == "per_path_ranges":
            phrases.extend(_caption(name) for name in _path_range_columns(summary[key]))
    return phrases


def _equivalent_basis_captions(recorded: Any) -> list[str]:
    names: list[str] = []
    if isinstance(recorded, Mapping):
        for group, value in recorded.items():
            names.append(str(group))
            if isinstance(value, Mapping):
                names.extend(str(name) for name in value)
    return names


def _render_composition(source: _Source, figures: list[RenderedFigure]) -> str:
    """Lay a kind's recorded composition out, section by section, in declared order."""

    summary = source.manifest.summary
    parts: list[str] = []
    for key, section in COMPOSITION_SECTIONS.get(source.manifest.result_kind, ()):
        heading = f"<h4>{html.escape(COMPOSITION_HEADINGS[section])}</h4>"
        if key not in summary:
            parts.append(heading + _not_recorded(key))
            continue
        parts.append(
            heading
            + "<p class=\"composition-lead\">"
            + html.escape(COMPOSITION_LEADS[section])
            + "</p>"
            + _COMPOSITION_RENDERERS[section](source, key, figures)
        )
    return "".join(parts)


def _not_recorded(key: str, *, empty: bool = False) -> str:
    """State plainly what a manifest records here, rather than filling it in.

    A manifest recorded before its producing module carried this key is still a verified
    manifest, and the report says what it records. The alternative — opening the CSV the run
    wrote beside it — would put a figure in a report that never passed through the manifest,
    which is the one thing this layer must not do.

    An empty recording and an absent one are stated differently. They are different facts about
    the run, and a report that reported one as the other would be wrong about its own evidence.
    """

    if empty:
        return (
            "<p class=\"not-recorded\">This manifest records an empty "
            f"<code>{html.escape(key)}</code>, so there is nothing to lay out.</p>"
        )
    return (
        "<p class=\"not-recorded\">This manifest records no "
        f"<code>{html.escape(key)}</code>, so the report shows none. A report reads the "
        "manifest and nothing else; it does not open the files a run wrote beside it.</p>"
    )


def _render_scenarios_side_by_side(
    source: _Source, key: str, figures: list[RenderedFigure]
) -> str:
    """One column per named scenario, with the provenance each figure has to carry."""

    scenarios = _recorded_sequence(source, key)
    if not scenarios:
        return _not_recorded(key, empty=scenarios is not None)

    header = ["<tr><th scope=\"col\">Scenario</th>"]
    for position, scenario in enumerate(scenarios):
        header.append(
            "<th scope=\"col\">"
            + _figure_cell(
                source,
                key="scenario_name",
                summary_path=(key, position, "scenario_name"),
                recorded=_lookup(scenario, ("scenario_name",)),
                figures=figures,
            )
            + "</th>"
        )
    header.append("</tr>")

    rows: list[str] = ["".join(header)]
    for caption, path in SCENARIO_PROVENANCE_ROWS:
        cells = [f"<tr><th scope=\"row\">{html.escape(caption)}</th>"]
        for position, scenario in enumerate(scenarios):
            cells.append(
                "<td>"
                + _figure_cell(
                    source,
                    key=path[-1],
                    summary_path=(key, position, *path),
                    recorded=_lookup(scenario, path),
                    figures=figures,
                )
                + "</td>"
            )
        cells.append("</tr>")
        rows.append("".join(cells))
    return (
        "<div class=\"side-by-side\"><table class=\"scenarios\">"
        + "".join(rows)
        + "</table></div>"
    )


def _render_equivalent_basis(
    source: _Source, key: str, figures: list[RenderedFigure]
) -> str:
    """Render the equivalence the ensemble checked, group by group, as it recorded it."""

    recorded = source.manifest.summary.get(key)
    if not isinstance(recorded, Mapping):
        return _not_recorded(key)
    if not recorded:
        return _not_recorded(key, empty=True)

    parts: list[str] = []
    for group, value in recorded.items():
        parts.append(
            f"<p class=\"basis-group-name\">{html.escape(_caption(str(group)))}</p>"
        )
        entries: list[tuple[str, tuple[str, ...]]]
        if isinstance(value, Mapping):
            entries = [(str(name), (key, str(group), str(name))) for name in value]
        else:
            entries = [(str(group), (key, str(group)))]
        rows = "".join(
            "<tr>"
            f"<th scope=\"row\">{html.escape(_caption(name))}</th>"
            "<td>"
            + _figure_cell(
                source,
                key=path[-1],
                summary_path=path,
                recorded=_lookup(recorded, path[1:]),
                figures=figures,
            )
            + "</td></tr>"
            for name, path in entries
        )
        parts.append(f"<table class=\"equivalent-basis\">{rows}</table>")
    return "".join(parts)


def _render_path_ranges(source: _Source, key: str, figures: list[RenderedFigure]) -> str:
    """One row per bootstrap path, in the columns and the order the manifest recorded."""

    records = _recorded_sequence(source, key)
    if not records:
        return _not_recorded(key, empty=records is not None)
    columns = _path_range_columns(records)
    if not columns:
        return _not_recorded(key, empty=True)

    header = "<tr>" + "".join(
        f"<th scope=\"col\">{html.escape(_caption(column))}</th>" for column in columns
    ) + "</tr>"
    rows = [header]
    for position, record in enumerate(records):
        cells = "".join(
            "<td>"
            + _figure_cell(
                source,
                key=column,
                summary_path=(key, position, column),
                recorded=_lookup(record, (column,)),
                figures=figures,
            )
            + "</td>"
            for column in columns
        )
        rows.append(f"<tr>{cells}</tr>")
    return (
        "<div class=\"side-by-side\"><table class=\"path-ranges\">"
        + "".join(rows)
        + "</table></div>"
    )


def _path_range_columns(records: Any) -> tuple[str, ...]:
    """The recorded columns, taken from the recorded rows rather than restated here.

    Every row must declare the same columns. A ragged table is refused instead of rendered with
    blanks, because a blank cell in a range table reads as a value rather than as an absence.
    """

    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or not records:
        return ()
    rows = [record for record in records if isinstance(record, Mapping)]
    if len(rows) != len(records):
        raise ReportRenderError(
            "A recorded per-path range row is not an object; the report renders the table a "
            "manifest recorded, and cannot render a row it cannot read"
        )
    columns = tuple(str(name) for name in rows[0])
    for row in rows[1:]:
        if tuple(str(name) for name in row) != columns:
            raise ReportRenderError(
                "Recorded per-path range rows declare different columns. A ragged table would "
                "be rendered with blank cells, and a blank cell in a range table reads as a "
                "value rather than as an absence"
            )
    return columns


def _recorded_sequence(source: _Source, key: str) -> tuple[Mapping[str, Any], ...] | None:
    """The recorded rows of a composition table, or ``None`` when the key is not a list of rows.

    An empty tuple and ``None`` are different answers: the first says the manifest records an
    empty table, the second that it records no such table at all.
    """

    if key not in source.manifest.summary:
        return None
    recorded = source.manifest.summary[key]
    if not isinstance(recorded, Sequence) or isinstance(recorded, (str, bytes)):
        return None
    entries = tuple(item for item in recorded if isinstance(item, Mapping))
    if len(entries) != len(recorded):
        raise ReportRenderError(
            f"Recorded {key} contains an entry that is not an object; the report renders what "
            "a manifest recorded and cannot render an entry it cannot read"
        )
    return entries


def _lookup(recorded: Any, path: Sequence[str]) -> tuple[bool, Any]:
    """Resolve a recorded value by path, distinguishing a recorded null from an absent key."""

    current: Any = recorded
    for name in path:
        if not isinstance(current, Mapping) or name not in current:
            return (False, None)
        current = current[name]
    return (True, current)


_COMPOSITION_RENDERERS: dict[str, Any] = {
    "scenarios_side_by_side": _render_scenarios_side_by_side,
    "equivalent_basis": _render_equivalent_basis,
    "per_path_ranges": _render_path_ranges,
}


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
    """One recorded value as a labelled row, including a guaranteed key that is absent.

    A kind's guaranteed keys are checked when a manifest is built, not when one is read, so a
    verified manifest can still reach the renderer without one — a manifest recorded before its
    kind guaranteed that key, or recorded by another build. Such a key is stated as not recorded
    by the same route every other absent value takes. Reading it out of the summary directly
    would raise ``KeyError`` instead, turning a manifest this report can describe honestly into
    an unhandled crash.
    """

    cell = _figure_cell(
        source,
        key=key,
        summary_path=(key,),
        recorded=_lookup(source.manifest.summary, (key,)),
        figures=figures,
        is_headline=is_headline,
    )
    return (
        f"<tr><th scope=\"row\">{html.escape(_caption(key))}</th>"
        f"<td>{cell}</td></tr>"
    )


def _figure_cell(
    source: _Source,
    *,
    key: str,
    summary_path: tuple[str | int, ...],
    recorded: tuple[bool, Any],
    figures: list[RenderedFigure],
    is_headline: bool = False,
) -> str:
    """Render one recorded value, and record where in the manifest it came from.

    An absent key is stated as absent rather than shown as a blank or a zero, and no figure is
    recorded for it: there is no value to attribute. A recorded ``null`` is a value, and renders
    as the JSON null it was recorded as.
    """

    present, value = recorded
    if not present:
        return "<span class=\"absent-value\">not recorded</span>"
    manifest = source.manifest
    value_text = _format_value(value)
    figures.append(
        RenderedFigure(
            manifest_id=manifest.manifest_id,
            result_kind=manifest.result_kind,
            basis=manifest.basis,
            key=key,
            value_text=value_text,
            is_headline=is_headline,
            summary_path=summary_path,
        )
    )
    return f"<span class=\"figure-value\">{html.escape(value_text)}</span>"


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

    The suffixed anchor is itself checked and advanced until it is unused. A single unchecked
    suffix is not enough: IDs ``A``, ``A-2`` and ``a`` are three distinct manifests whose second
    and third anchors both reduce to ``manifest-a-2``, and the index link for one would then
    jump to the other's block.
    """

    anchors: dict[str, str] = {}
    taken: set[str] = set()
    for position, source in enumerate(sources):
        manifest_id = source.manifest.manifest_id
        safe = "".join(
            character if character.isalnum() else "-" for character in manifest_id.lower()
        )
        base = f"manifest-{safe}"
        anchor = base
        suffix = position
        while anchor in taken:
            anchor = f"{base}-{suffix}"
            suffix += 1
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
        "bases_rendered": _bases_present(sources),
        "bases_absent": [
            basis for basis in RESULT_BASES if basis not in _bases_present(sources)
        ],
        "manifests_by_basis": {
            basis: [
                source.manifest.manifest_id
                for source in sources
                if source.manifest.basis == basis
            ]
            for basis in _bases_present(sources)
        },
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
                "rendered_summary_keys": _rendered_summary_keys(source, figures),
                "composition_sections": [
                    section
                    for key, section in COMPOSITION_SECTIONS.get(
                        source.manifest.result_kind, ()
                    )
                    if key in source.manifest.summary
                ],
            }
            for source in sources
        ],
    }


def _rendered_summary_keys(
    source: _Source, figures: Sequence[RenderedFigure]
) -> list[str]:
    """The summary keys a manifest contributed, in rendering order and without repetition.

    A composition table renders many cells out of one summary key, so the audit index names the
    key once. What each individual cell was read from is carried by the figure itself.
    """

    keys: list[str] = []
    for figure in figures:
        if figure.manifest_id != source.manifest.manifest_id:
            continue
        name = str(figure.summary_path[0])
        if name not in keys:
            keys.append(name)
    return keys


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
.kind-description, .basis-wording, .composition-lead, .index-rule { opacity: 0.85; }
.side-by-side { overflow-x: auto; }
.side-by-side table { min-width: 100%; width: auto; }
.side-by-side th[scope="row"] { white-space: nowrap; width: auto; }
.basis-group-name { font-weight: 600; margin-bottom: 0; }
.absent-value, .not-recorded { font-style: italic; opacity: 0.8; }
.index-table td.digest { font-size: 0.75rem; }
.index-table td.index-label { font-style: italic; }
.bases-absent { font-size: 0.9rem; opacity: 0.85; }
.manifest-chart { border: 1px solid currentColor; display: block; height: auto; margin: 0.5rem 0;
  max-width: 100%; width: 100%; }
.chart-zero { stroke: currentColor; stroke-width: 1; }
.chart-bar { fill: currentColor; stroke: currentColor; stroke-width: 1; }
.chart-minimum { fill-opacity: 0.3; }
.chart-spread { fill: none; stroke-dasharray: 4 2; stroke-width: 2; }
.chart-path, .chart-value { fill: currentColor; font-family: ui-monospace, monospace;
  font-size: 11px; }
.chart-value { paint-order: stroke; stroke: Canvas; stroke-width: 3px; }
.chart-note, .chart-unavailable { font-size: 0.9rem; opacity: 0.85; }
footer { border-top: 1px solid currentColor; font-size: 0.85rem; margin-top: 3rem;
  padding-top: 0.75rem; }
"""
