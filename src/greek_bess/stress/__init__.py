"""Reproducible research stress-path generators."""

from .bootstrap import (
    SOURCE_ERA_POLICY,
    BootstrapConfig,
    BootstrapInputError,
    BootstrapResult,
    SourceEra,
    detect_source_eras,
    generate_seasonal_bootstrap_paths,
    select_source_era,
)
from .bootstrap_dispatch import (
    BootstrapDispatchInputError,
    BootstrapDispatchResult,
    dispatch_bootstrap_paths,
)
from .price_level import (
    PriceLevelShockConfig,
    PriceLevelShockInputError,
    PriceLevelShockResult,
    apply_price_level_shock,
)
from .spread import (
    REFERENCE_BASES,
    SPREAD_COMPRESSION_POLICY,
    SpreadCompressionConfig,
    SpreadCompressionInputError,
    SpreadCompressionResult,
    apply_spread_compression,
)

__all__ = [
    "BootstrapConfig",
    "BootstrapInputError",
    "BootstrapResult",
    "SOURCE_ERA_POLICY",
    "SourceEra",
    "detect_source_eras",
    "select_source_era",
    "generate_seasonal_bootstrap_paths",
    "BootstrapDispatchInputError",
    "BootstrapDispatchResult",
    "dispatch_bootstrap_paths",
    "PriceLevelShockConfig",
    "PriceLevelShockInputError",
    "PriceLevelShockResult",
    "apply_price_level_shock",
    "REFERENCE_BASES",
    "SPREAD_COMPRESSION_POLICY",
    "SpreadCompressionConfig",
    "SpreadCompressionInputError",
    "SpreadCompressionResult",
    "apply_spread_compression",
]
