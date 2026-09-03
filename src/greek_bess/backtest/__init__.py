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
from .fundamentals_dispatch import (
    FUNDAMENTALS_DISPATCH_BENCHMARK_LABEL,
    FundamentalsDispatchBenchmarkResult,
    FundamentalsDispatchInputError,
    backtest_fundamentals_dispatch,
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
    "FUNDAMENTALS_DISPATCH_BENCHMARK_LABEL",
    "FundamentalsDispatchBenchmarkResult",
    "FundamentalsDispatchInputError",
    "backtest_fundamentals_dispatch",
    "ML_DISPATCH_BENCHMARK_LABEL",
    "MLDispatchBenchmarkResult",
    "backtest_ml_dispatch_benchmark",
]
