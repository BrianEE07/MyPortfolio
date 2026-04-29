import json

from portfolio_app.holdings import load_holdings


def test_load_holdings_uses_env_override(monkeypatch, tmp_path):
    preview_path = tmp_path / "preview-holdings.json"
    preview_path.write_text(
        json.dumps(
            [
                {"symbol": "MSFT", "shares": 1.25, "cost_basis": 300.0},
                {"symbol": "NVDA", "shares": 0.5, "cost_basis": 120.0},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PORTFOLIO_HOLDINGS_PATH", str(preview_path))

    assert load_holdings() == [
        {"symbol": "MSFT", "shares": 1.25, "cost_basis": 300.0},
        {"symbol": "NVDA", "shares": 0.5, "cost_basis": 120.0},
    ]
