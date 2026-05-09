import json

from portfolio_app.watchlist import load_watchlist


def test_load_watchlist_returns_empty_when_missing(tmp_path):
    assert load_watchlist(tmp_path / "missing.json") == []


def test_load_watchlist_normalizes_public_items(tmp_path):
    watchlist_path = tmp_path / "watchlist.json"
    watchlist_path.write_text(
        json.dumps(
            [
                {"symbol": " msft "},
                {"symbol": ""},
                {"symbol": "amd"},
                {"symbol": "MSFT"},
                {"symbol": "MSFT"},
            ]
        ),
        encoding="utf-8",
    )

    items = load_watchlist(watchlist_path)

    assert items == [
        {"symbol": "MSFT", "order": 0},
        {"symbol": "AMD", "order": 2},
    ]
