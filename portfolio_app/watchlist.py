import json
import os
from pathlib import Path

from .config import WATCHLIST_JSON_PATH


def normalize_watchlist_item(raw_item, order):
    """Normalize one public watchlist item."""
    if not isinstance(raw_item, dict):
        return None

    symbol = str(raw_item.get("symbol", "")).strip().upper()
    if not symbol:
        return None

    return {
        "symbol": symbol,
        "order": order,
    }


def _resolve_watchlist_path(json_path=None):
    if json_path is not None:
        return Path(json_path)

    override_path = os.environ.get("PORTFOLIO_WATCHLIST_PATH")
    if override_path:
        return Path(override_path).expanduser()

    return WATCHLIST_JSON_PATH


def load_watchlist(json_path=None):
    """Load the public lightweight watchlist."""
    watchlist_path = _resolve_watchlist_path(json_path)
    try:
        payload = json.loads(watchlist_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []

    if not isinstance(payload, list):
        return []

    items = []
    seen_symbols = set()
    for index, raw_item in enumerate(payload):
        item = normalize_watchlist_item(raw_item, index)
        if item is None or item["symbol"] in seen_symbols:
            continue
        seen_symbols.add(item["symbol"])
        items.append(item)

    return items
