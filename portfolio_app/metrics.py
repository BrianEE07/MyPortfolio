import json
from pathlib import Path

from .config import PORTFOLIO_METRICS_JSON_PATH


def default_portfolio_metrics() -> dict:
    """Return the canonical generated portfolio metrics payload."""
    return {
        "realized_pl": None,
        "realized_return_pct": None,
        "twr": None,
        "irr": None,
        "cagr": None,
        "current_drawdown": None,
        "max_drawdown": None,
        "sharpe": None,
        "beta": None,
        "alpha": None,
        "sp500_ytd_ret": None,
    }


def write_portfolio_metrics(
    metrics: dict,
    metrics_path: Path = PORTFOLIO_METRICS_JSON_PATH,
) -> dict:
    """Write generated portfolio metrics JSON to disk."""
    payload = default_portfolio_metrics()
    for field_name in payload:
        payload[field_name] = metrics.get(field_name)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def coerce_number(value):
    """Coerce stored metric values into floats while preserving missing values."""
    if value in (None, "", "N/A"):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    normalized = str(value).strip().replace(",", "").replace("%", "")
    if not normalized:
        return None

    try:
        return float(normalized)
    except ValueError:
        return None


def load_portfolio_metrics(metrics_path: Path = PORTFOLIO_METRICS_JSON_PATH) -> dict:
    """Load generated portfolio metrics with stable default fields."""
    try:
        if not metrics_path.exists():
            return default_portfolio_metrics()
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default_portfolio_metrics()

    if not isinstance(payload, dict):
        return default_portfolio_metrics()

    metrics = default_portfolio_metrics()
    for field_name in metrics:
        metrics[field_name] = coerce_number(payload.get(field_name))
    return metrics
