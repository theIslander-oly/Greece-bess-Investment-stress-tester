"""Historical backtesting interfaces."""

from .degradation_dispatch import (
    DEGRADED_DISPATCH_LABEL,
    DegradationDispatchInputError,
    DegradationDispatchResult,
    simulate_degradation_dispatch,
)
from .forecast_dispatch import (
    FORECAST_BACKTEST_LABEL,
    ForecastDispatchBacktestResult,
    ForecastDispatchInputError,
    backtest_forecast_dispatch,
)
from .ml_dispatch import (
    ML_DISPATCH_BENCHMARK_LABEL,
    MLDispatchBenchmarkResult,
    backtest_ml_dispatch_benchmark,
)

__all__ = [
    "DEGRADED_DISPATCH_LABEL",
    "DegradationDispatchInputError",
    "DegradationDispatchResult",
    "simulate_degradation_dispatch",
    "FORECAST_BACKTEST_LABEL",
    "ForecastDispatchBacktestResult",
    "ForecastDispatchInputError",
    "backtest_forecast_dispatch",
    "ML_DISPATCH_BENCHMARK_LABEL",
    "MLDispatchBenchmarkResult",
    "backtest_ml_dispatch_benchmark",
]
