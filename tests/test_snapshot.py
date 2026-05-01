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
        "cached_stock_profile",
        lambda symbol: {
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        },
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
            "score": 66.0,
            "score_str": "66",
            "rating": "Greed / 貪婪",
            "previous_close": 61.0,
            "previous_close_str": "61",
            "previous_close_rating": "Greed / 貪婪",
            "week_ago": {"score_str": "58", "rating": "Greed / 貪婪"},
            "month_ago": {"score_str": "44", "rating": "Fear / 恐懼"},
            "year_ago": {"score_str": "72", "rating": "Greed / 貪婪"},
            "chart_labels": ["04/01", "04/02"],
            "chart_data": [58.0, 66.0],
            "vix_str": "17.80",
            "pcr_str": "0.91",
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
        lambda: {"value_str": "31.40", "valuation": "Bubble Zone / 泡沫高估區"},
    )
    monkeypatch.setattr(
        snapshot,
        "cached_finra_margin",
        lambda: {"value_str": "1,225,597", "latest_month": "Dec-25", "mom_str": "+0.93%"},
    )
    monkeypatch.setattr(
        snapshot,
        "cached_sp500_historical",
        lambda: {
            "price_str": "7165.08",
            "ma20_str": "6834.03",
            "ma60_str": "6812.12",
            "ma250_str": "6551.31",
            "ma1250_str": "5044.10",
            "broken_20": False,
            "broken_60": False,
            "broken_250": False,
            "broken_1250": False,
            "chart_labels": ["25/04/28", "25/04/29"],
            "chart_points": [7010.12, 7165.08],
        },
    )


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
    assert result["holdings_category_segments"][0]["id"] == "technology"
    assert result["market_sentiment"]["score_str"] == "66"
    assert result["market_sentiment"]["delta_direction"] == "up"
    assert result["market_sentiment"]["gauge_level"] == "greed"
    assert result["market_sentiment"]["history_cards"][0]["label_zh"] == "前收盤"
    assert result["market_trend"]["price_str"] == "7165.08"
    assert result["dip_signals"][2]["value"] == "1,225,597"
    assert result["frontend_payload"]["sp500TrendChart"]["data"] == [7010.12, 7165.08]
    assert result["frontend_payload"]["holdingsChart"]["colors"] == ["#de8b5f"]


def test_build_portfolio_snapshot_treats_matching_truncated_fear_greed_score_as_flat(monkeypatch):
    _stub_snapshot_dependencies(monkeypatch)

    monkeypatch.setattr(
        snapshot,
        "cached_fear_greed",
        lambda: {
            "score": 66.2,
            "score_str": "66",
            "rating": "Greed / 貪婪",
            "previous_close": 66.9,
            "previous_close_str": "66",
            "previous_close_rating": "Greed / 貪婪",
            "week_ago": {"score_str": "58", "rating": "Greed / 貪婪"},
            "month_ago": {"score_str": "44", "rating": "Fear / 恐懼"},
            "year_ago": {"score_str": "72", "rating": "Greed / 貪婪"},
            "chart_labels": ["04/01", "04/02"],
            "chart_data": [58.0, 66.2],
            "vix_str": "17.80",
            "pcr_str": "0.91",
        },
    )

    result = snapshot.build_portfolio_snapshot()

    assert result["market_sentiment"]["delta_direction"] == "flat"
    assert result["market_sentiment"]["delta_tone"] == "flat"


def test_build_portfolio_snapshot_compares_truncated_fear_greed_scores(monkeypatch):
    _stub_snapshot_dependencies(monkeypatch)

    monkeypatch.setattr(
        snapshot,
        "cached_fear_greed",
        lambda: {
            "score": 66.2,
            "score_str": "66",
            "rating": "Greed / 貪婪",
            "previous_close": 67.1,
            "previous_close_str": "67",
            "previous_close_rating": "Greed / 貪婪",
            "week_ago": {"score_str": "58", "rating": "Greed / 貪婪"},
            "month_ago": {"score_str": "44", "rating": "Fear / 恐懼"},
            "year_ago": {"score_str": "72", "rating": "Greed / 貪婪"},
            "chart_labels": ["04/01", "04/02"],
            "chart_data": [58.0, 66.2],
            "vix_str": "17.80",
            "pcr_str": "0.91",
        },
    )

    result = snapshot.build_portfolio_snapshot()

    assert result["market_sentiment"]["delta_direction"] == "down"
    assert result["market_sentiment"]["delta_tone"] == "loss"


def test_build_portfolio_snapshot_includes_holdings_chart_company_names(monkeypatch):
    _stub_snapshot_dependencies(monkeypatch)

    result = snapshot.build_portfolio_snapshot()

    assert result["holdings_rows"][0]["company_name"] == "Apple Inc."
    assert result["frontend_payload"]["holdingsChart"]["labels"] == ["AAPL"]
    assert result["frontend_payload"]["holdingsChart"]["companyNames"] == ["Apple Inc."]


def test_build_portfolio_snapshot_prefers_yahoo_sector_and_industry_for_categories(monkeypatch, tmp_path):
    holdings = [
        {"symbol": "GOOG", "shares": 1.0, "cost_basis": 150.0},
        {"symbol": "NVDA", "shares": 1.0, "cost_basis": 100.0},
    ]
    close_map = {"GOOG": 180.0, "NVDA": 220.0}
    profile_map = {
        "GOOG": {
            "company_name": "Alphabet Inc.",
            "sector": "Communication Services",
            "industry": "Internet Content & Information",
        },
        "NVDA": {
            "company_name": "NVIDIA Corporation",
            "sector": "Technology",
            "industry": "Semiconductors",
        },
    }

    _stub_snapshot_dependencies(monkeypatch)
    monkeypatch.setattr(snapshot, "load_holdings", lambda: holdings)
    monkeypatch.setattr(snapshot, "cached_close", lambda symbol: close_map[symbol])
    monkeypatch.setattr(snapshot, "cached_stock_profile", lambda symbol: profile_map[symbol])
    monkeypatch.setattr(snapshot, "PORTFOLIO_METRICS_JSON_PATH", tmp_path / "missing.json")

    result = snapshot.build_portfolio_snapshot()

    rows_by_symbol = {row["symbol"]: row for row in result["holdings_rows"]}

    assert rows_by_symbol["GOOG"]["category_id"] == "communication-services"
    assert rows_by_symbol["GOOG"]["category_label_en"] == "Communication Services"
    assert rows_by_symbol["NVDA"]["category_id"] == "technology"


def test_build_portfolio_snapshot_handles_missing_generated_realized_metrics(tmp_path, monkeypatch):
    _stub_snapshot_dependencies(monkeypatch)
    monkeypatch.setattr(snapshot, "PORTFOLIO_METRICS_JSON_PATH", tmp_path / "missing.json")

    result = snapshot.build_portfolio_snapshot()

    realized_card = result["summary_primary_cards"][3]

    assert realized_card["value"] == "N/A"
    assert realized_card["tone"] == "muted"
    assert realized_card["accent_value"] == "N/A"


def test_build_portfolio_snapshot_uses_metrics_env_override(tmp_path, monkeypatch):
    _stub_snapshot_dependencies(monkeypatch)
    metrics_path = tmp_path / "preview-portfolio-metrics.json"
    metrics_path.write_text(
        '{"realized_pl": 4321.0, "realized_return_pct": 11.2}',
        encoding="utf-8",
    )
    monkeypatch.setattr(snapshot, "PORTFOLIO_METRICS_JSON_PATH", tmp_path / "missing.json")
    monkeypatch.setenv("PORTFOLIO_METRICS_PATH", str(metrics_path))

    result = snapshot.build_portfolio_snapshot()

    realized_card = result["summary_primary_cards"][3]

    assert realized_card["value"] == "+$4,321.00"
    assert realized_card["accent_value"] == "+11.20%"


def test_build_portfolio_snapshot_groups_other_holdings_and_breaks_down_categories(monkeypatch, tmp_path):
    holdings = [
        {"symbol": f"SYM{i:02d}", "shares": 1.0, "cost_basis": 50.0}
        for i in range(1, 12)
    ]
    close_map = {holding["symbol"]: 120.0 - index * 5 for index, holding in enumerate(holdings)}
    profile_map = {
        "SYM01": {"sector": "Technology", "industry": "Semiconductors"},
        "SYM02": {"sector": "Technology", "industry": "Software"},
        "SYM03": {"sector": "Healthcare", "industry": "Biotechnology"},
        "SYM04": {"sector": "Healthcare", "industry": "Biotechnology"},
        "SYM05": {"sector": "Financial Services", "industry": "Asset Management"},
        "SYM06": {"sector": "Technology", "industry": "Hardware"},
        "SYM07": {"sector": "Communication Services", "industry": "Internet Content"},
        "SYM08": {"sector": "Technology", "industry": "Semiconductors"},
        "SYM09": {"sector": "Consumer Defensive", "industry": "Beverages"},
        "SYM10": {"sector": "Technology", "industry": "Semiconductors"},
        "SYM11": {"sector": "Energy", "industry": "Oil & Gas"},
    }

    _stub_snapshot_dependencies(monkeypatch)
    monkeypatch.setattr(snapshot, "load_holdings", lambda: holdings)
    monkeypatch.setattr(snapshot, "cached_close", lambda symbol: close_map[symbol])
    monkeypatch.setattr(snapshot, "cached_stock_profile", lambda symbol: profile_map[symbol])
    monkeypatch.setattr(snapshot, "PORTFOLIO_METRICS_JSON_PATH", tmp_path / "missing.json")

    result = snapshot.build_portfolio_snapshot()

    assert result["top_holdings_chart"]["has_other_bucket"] is True
    assert result["top_holdings_chart"]["other_count"] == 1
    assert result["frontend_payload"]["holdingsChart"]["labels"][-1] == "Others"
    assert result["frontend_payload"]["holdingsChart"]["data"][-1] == 70.0

    category_ids = [segment["id"] for segment in result["holdings_category_segments"]]
    assert category_ids[:3] == ["technology", "healthcare", "financial-services"]
    assert result["holdings_category_segments"][0]["share_ratio_str"] == "46.89%"
    assert result["holdings_rows"][0]["category_id"] == "technology"
    assert {row["category_id"] for row in result["holdings_rows"]} >= {
        "technology",
        "healthcare",
        "financial-services",
        "communication-services",
        "consumer-defensive",
        "energy",
    }


def test_build_portfolio_snapshot_groups_all_holdings_after_top_ten(monkeypatch, tmp_path):
    holdings = [
        {"symbol": f"SYM{i:02d}", "shares": 1.0, "cost_basis": 40.0}
        for i in range(1, 14)
    ]
    close_map = {holding["symbol"]: 130.0 - index * 5 for index, holding in enumerate(holdings)}

    _stub_snapshot_dependencies(monkeypatch)
    monkeypatch.setattr(snapshot, "load_holdings", lambda: holdings)
    monkeypatch.setattr(snapshot, "cached_close", lambda symbol: close_map[symbol])
    monkeypatch.setattr(
        snapshot,
        "cached_stock_profile",
        lambda symbol: {"sector": "Technology", "industry": "Semiconductors"},
    )
    monkeypatch.setattr(snapshot, "PORTFOLIO_METRICS_JSON_PATH", tmp_path / "missing.json")

    result = snapshot.build_portfolio_snapshot()

    assert result["top_holdings_chart"]["has_other_bucket"] is True
    assert result["top_holdings_chart"]["other_count"] == 3
    assert result["frontend_payload"]["holdingsChart"]["labels"][-1] == "Others"
    assert result["frontend_payload"]["holdingsChart"]["data"][-1] == 225.0
    assert result["frontend_payload"]["holdingsChart"]["colors"][-1] == "#b2a8a0"
    assert len(result["frontend_payload"]["holdingsChart"]["labels"]) == 11
