"""Versioned run manifest and report contract, and the renderer that reads it."""

from .contract import (
    REPORT_CONTRACT_VERSION,
    RESULT_BASES,
    RESULT_KINDS,
    STANDING_EXCLUSIONS,
    ReportContractError,
    ResultKind,
    RunManifest,
    build_run_manifest,
    read_run_manifest,
    write_run_manifest,
)
from .render import (
    BASIS_WORDING,
    DECLARATION_CHECKLIST,
    REPORT_RENDER_VERSION,
    DeclarationRequirement,
    RenderedFigure,
    RenderedReport,
    ReportRenderError,
    render_report,
    write_report,
)

__all__ = [
    "BASIS_WORDING",
    "DECLARATION_CHECKLIST",
    "REPORT_CONTRACT_VERSION",
    "REPORT_RENDER_VERSION",
    "RESULT_BASES",
    "RESULT_KINDS",
    "STANDING_EXCLUSIONS",
    "DeclarationRequirement",
    "RenderedFigure",
    "RenderedReport",
    "ReportContractError",
    "ReportRenderError",
    "ResultKind",
    "RunManifest",
    "build_run_manifest",
    "read_run_manifest",
    "render_report",
    "write_report",
    "write_run_manifest",
]
