from portfolio_app import snapshot


def _stub_snapshot_dependencies(monkeypatch):
    monkeypatch.setattr(
        snapshot,
        "load_holdings",
        lambda: [{"symbol": "AAPL", "shares": 2.0, "cost_basis": 100.0}],
    )
    monkeypatch.setattr(snapshot, "cached_close", lambda symbol: 125.0)
    monkeypatch.setattr(
        snapshot,
        "cached_stock_pe",
        lambda symbol: {"trailing_pe": 22.1, "forward_pe": 19.4},
    )
    monkeypatch.setattr(
        snapshot,
        "cached_stock_technicals",
        lambda symbol: {"drawdown": -12.5, "price": 125.0, "ma250": 110.0},
    )
    monkeypatch.setattr(
        snapshot,
        "cached_portfolio_metrics",
        lambda holdings: {
            "sharpe": 1.28,
            "beta": 0.86,
            "alpha": 0.0345,
            "portfolio_ytd_ret": 0.1625,
            "sp500_ytd_ret": 0.0975,
            "sharpe_str": "1.28",
            "beta_str": "0.86",
            "alpha_str": "0.0345",
            "alpha_pct_str": "+3.45%",
            "portfolio_ytd_ret_str": "+16.25%",
            "sp500_ytd_ret_str": "+9.75%",
        },
    )
    monkeypatch.setattr(
        snapshot,
        "cached_fear_greed",
        lambda: {
            "score": None,
            "score_str": "N/A",
            "rating": "N/A",
            "previous_close": None,
            "previous_close_str": "N/A",
            "previous_close_rating": "N/A",
            "week_ago": {"score_str": "N/A", "rating": "N/A"},
            "month_ago": {"score_str": "N/A", "rating": "N/A"},
            "year_ago": {"score_str": "N/A", "rating": "N/A"},
            "chart_labels": [],
            "chart_data": [],
            "vix_str": "N/A",
            "pcr_str": "N/A",
        },
    )
    monkeypatch.setattr(
        snapshot,
        "cached_sp500_trailing_pe",
        lambda: {
            "value_str": "N/A",
            "prev_value_str": "N/A",
            "delta_str": "N/A",
            "date": "N/A",
            "valuation": "N/A",
            "source_name": "N/A",
            "source_url": "https://example.com",
        },
    )
    monkeypatch.setattr(
        snapshot,
        "cached_shiller_pe",
        lambda: {"value_str": "N/A", "valuation": "N/A"},
    )
    monkeypatch.setattr(snapshot, "cached_finra_margin", lambda: {})
    monkeypatch.setattr(snapshot, "cached_sp500_historical", lambda: {})


def test_build_portfolio_snapshot_uses_generated_realized_metrics(tmp_path, monkeypatch):
    _stub_snapshot_dependencies(monkeypatch)
    metrics_path = tmp_path / "portfolio_metrics.json"
    metrics_path.write_text(
        '{"realized_pl": 12345.67, "realized_return_pct": 18.4}',
        encoding="utf-8",
    )
    monkeypatch.setattr(snapshot, "PORTFOLIO_METRICS_JSON_PATH", metrics_path)

    result = snapshot.build_portfolio_snapshot()

    assert [card["label_en"] for card in result["summary_primary_cards"]] == [
        "Total Value",
        "Total Cost",
        "Unrealized P&L",
        "Realized P&L",
    ]
    assert [card["label_en"] for card in result["summary_secondary_cards"]] == [
        "Portfolio YTD",
        "Sharpe Ratio",
        "Alpha",
        "Beta",
    ]
    assert result["summary_primary_cards"][2]["value"] == "+$50.00"
    assert result["summary_primary_cards"][2]["accent_value"] == "+25.00%"
    assert result["summary_primary_cards"][2]["accent_tone"] == "gain"
    assert result["summary_primary_cards"][3]["value"] == "+$12,345.67"
    assert result["summary_primary_cards"][3]["accent_value"] == "+18.40%"
    assert result["summary_primary_cards"][3]["accent_tone"] == "gain"
    assert result["summary_secondary_cards"][0]["value"] == "+16.25%"
    assert result["summary_secondary_cards"][0]["tooltip_zh"] == (
        "投資組合今年以來的報酬率，對照 S&P 500 為 +9.75%。"
    )
    assert result["summary_secondary_cards"][2]["value"] == "+3.45%"
    assert result["summary_secondary_cards"][2]["tone"] is None
    assert all("tooltip_zh" in card for card in result["summary_secondary_cards"])
    assert result["holdings_concentration_cards"] == [
        {"label": "Top 3", "value": "100.00%"},
        {"label": "Top 5", "value": "100.00%"},
        {"label": "Top 10", "value": "100.00%"},
    ]


def test_build_portfolio_snapshot_handles_missing_generated_realized_metrics(tmp_path, monkeypatch):
    _stub_snapshot_dependencies(monkeypatch)
    monkeypatch.setattr(snapshot, "PORTFOLIO_METRICS_JSON_PATH", tmp_path / "missing.json")

    result = snapshot.build_portfolio_snapshot()

    realized_card = result["summary_primary_cards"][3]

    assert realized_card["value"] == "N/A"
    assert realized_card["tone"] == "muted"
    assert realized_card["accent_value"] == "N/A"
