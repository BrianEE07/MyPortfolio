import json
from datetime import datetime

from pytz import timezone

from .config import DEFAULT_TABS, SITE_SUBTITLE, SITE_TITLE, TIMEZONE_NAME
from .holdings import load_holdings
from .market_data import (
    cached_close,
    cached_fear_greed,
    cached_finra_margin,
    cached_portfolio_metrics,
    cached_shiller_pe,
    cached_sp500_historical,
    cached_sp500_trailing_pe,
    cached_stock_pe,
    cached_stock_technicals,
)


def _format_currency(value):
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def _format_percent(value, signed=False):
    if value is None:
        return "N/A"
    return f"{value:+.2f}%" if signed else f"{value:.2f}%"


def _format_signed_currency(value):
    if value is None:
        return "N/A"
    return f"{value:+,.2f}"


def _tone_for_number(value):
    if value is None:
        return "muted"
    if value > 0:
        return "gain"
    if value < 0:
        return "loss"
    return "muted"


def _trend_label(is_below_ma250):
    if is_below_ma250:
        return "Below 250D / 跌破年線"
    return "Above 250D / 站上年線"


def build_portfolio_snapshot():
    """Build the server-side snapshot used by Flask rendering and static export."""
    holdings = load_holdings()
    current_timezone = timezone(TIMEZONE_NAME)
    updated_at = datetime.now(current_timezone).strftime("%Y-%m-%d %H:%M")

    rows = []
    total_cost = 0.0
    total_market_value = 0.0
    all_prices_available = True

    for holding in holdings:
        symbol = holding["symbol"]
        shares = holding["shares"]
        cost_basis = holding["cost_basis"]
        cost_total = shares * cost_basis
        total_cost += cost_total

        live_price = cached_close(symbol)
        pe_data = cached_stock_pe(symbol)
        technicals = cached_stock_technicals(symbol) or {}
        market_value = live_price * shares if live_price is not None else None
        profit = market_value - cost_total if market_value is not None else None
        profit_pct = ((profit / cost_total) * 100) if (profit is not None and cost_total) else None

        if market_value is None:
            all_prices_available = False
        else:
            total_market_value += market_value

        fallback_sort_value = market_value if market_value is not None else cost_total
        broken_250 = bool(
            technicals.get("price") is not None
            and technicals.get("ma250") is not None
            and technicals["price"] < technicals["ma250"]
        )

        rows.append(
            {
                "symbol": symbol,
                "shares": shares,
                "shares_str": f"{shares:.5f}",
                "cost_basis": cost_basis,
                "cost_basis_str": f"{cost_basis:.2f}",
                "cost_total": cost_total,
                "cost_total_str": _format_currency(cost_total),
                "price": live_price,
                "price_str": f"{live_price:.2f}" if live_price is not None else "N/A",
                "market_value": market_value,
                "market_value_str": _format_currency(market_value),
                "profit": profit,
                "profit_str": _format_currency(profit),
                "profit_pct": profit_pct,
                "profit_pct_str": _format_percent(profit_pct, signed=True),
                "profit_tone": _tone_for_number(profit),
                "drawdown": technicals.get("drawdown"),
                "drawdown_str": _format_percent(technicals.get("drawdown"), signed=True),
                "trailing_pe_str": (
                    f"{pe_data['trailing_pe']:.1f}"
                    if pe_data and pe_data.get("trailing_pe") is not None
                    else "N/A"
                ),
                "forward_pe_str": (
                    f"{pe_data['forward_pe']:.1f}"
                    if pe_data and pe_data.get("forward_pe") is not None
                    else "N/A"
                ),
                "trend_label": _trend_label(broken_250),
                "trend_tone": "loss" if broken_250 else "gain",
                "sort_value": fallback_sort_value,
            }
        )

    rows.sort(key=lambda row: row["sort_value"], reverse=True)

    total_market_value_value = total_market_value if all_prices_available else None
    total_profit_value = (
        total_market_value_value - total_cost
        if total_market_value_value is not None
        else None
    )
    total_profit_pct_value = (
        (total_profit_value / total_cost) * 100
        if total_profit_value is not None and total_cost
        else None
    )

    portfolio_metrics = cached_portfolio_metrics(holdings)
    top_holdings = rows[:10]
    chart_labels = [row["symbol"] for row in top_holdings]
    chart_data = [round(row["sort_value"], 2) for row in top_holdings]

    fear_greed = cached_fear_greed()
    fear_greed_score = fear_greed.get("score")
    fear_greed_previous = fear_greed.get("previous_close")
    fear_greed_delta = (
        fear_greed_score - fear_greed_previous
        if fear_greed_score is not None and fear_greed_previous is not None
        else None
    )

    sp500_trailing_pe = cached_sp500_trailing_pe()
    shiller_pe = cached_shiller_pe()
    finra_margin = cached_finra_margin() or {}
    sp500_historical = cached_sp500_historical() or {}

    summary_cards = [
        {
            "label_zh": "持股總市值",
            "label_en": "Market Value",
            "value": _format_currency(total_market_value_value),
            "tone": _tone_for_number(total_profit_value),
            "meta": "Live pricing / 即時報價" if total_market_value_value is not None else "Unavailable / 暫不可用",
        },
        {
            "label_zh": "持股總成本",
            "label_en": "Total Cost",
            "value": _format_currency(total_cost),
            "tone": "muted",
            "meta": "Average cost basis / 平均成本",
        },
        {
            "label_zh": "總報酬金額",
            "label_en": "Unrealized P/L",
            "value": _format_currency(total_profit_value),
            "tone": _tone_for_number(total_profit_value),
            "meta": "Open positions / 未實現損益",
        },
        {
            "label_zh": "總報酬率",
            "label_en": "Unrealized Return",
            "value": _format_percent(total_profit_pct_value, signed=True),
            "tone": _tone_for_number(total_profit_pct_value),
            "meta": "vs total cost / 相對總成本",
        },
        {
            "label_zh": "持倉 YTD 報酬",
            "label_en": "Portfolio YTD",
            "value": portfolio_metrics["portfolio_ytd_ret_str"],
            "tone": "muted" if portfolio_metrics["portfolio_ytd_ret_str"] == "N/A" else None,
            "meta": "YTD return / 年初至今",
        },
        {
            "label_zh": "大盤 YTD 報酬",
            "label_en": "S&P 500 YTD",
            "value": portfolio_metrics["sp500_ytd_ret_str"],
            "tone": "muted" if portfolio_metrics["sp500_ytd_ret_str"] == "N/A" else None,
            "meta": "Benchmark / 基準報酬",
        },
        {
            "label_zh": "夏普值",
            "label_en": "Sharpe Ratio",
            "value": portfolio_metrics["sharpe_str"],
            "tone": "muted",
            "meta": "Risk adjusted / 風險調整",
        },
        {
            "label_zh": "貝塔值",
            "label_en": "Beta",
            "value": portfolio_metrics["beta_str"],
            "tone": "muted",
            "meta": "vs S&P 500 / 相對大盤",
        },
    ]

    macro_cards = [
        {
            "title_zh": "波動率指數",
            "title_en": "VIX",
            "value": fear_greed.get("vix_str", "N/A"),
            "description": "Volatility gauge / 市場波動觀察",
        },
        {
            "title_zh": "賣權買權比",
            "title_en": "Put / Call Ratio",
            "value": fear_greed.get("pcr_str", "N/A"),
            "description": "Options positioning / 期權情緒",
        },
        {
            "title_zh": "融資餘額",
            "title_en": "FINRA Margin Debt",
            "value": finra_margin.get("value_str", "N/A"),
            "description": (
                f"MoM {finra_margin.get('mom_str', 'N/A')} / 資料月份 {finra_margin.get('latest_month', 'N/A')}"
            ),
        },
        {
            "title_zh": "席勒本益比",
            "title_en": "Shiller P/E",
            "value": shiller_pe.get("value_str", "N/A"),
            "description": shiller_pe.get("valuation", "N/A"),
        },
    ]

    sp500_snapshot_cards = [
        {"label_zh": "現價", "label_en": "Price", "value": sp500_historical.get("price_str", "N/A")},
        {"label_zh": "20 日均線", "label_en": "MA20", "value": sp500_historical.get("ma20_str", "N/A")},
        {"label_zh": "60 日均線", "label_en": "MA60", "value": sp500_historical.get("ma60_str", "N/A")},
        {"label_zh": "250 日均線", "label_en": "MA250", "value": sp500_historical.get("ma250_str", "N/A")},
    ]

    frontend_payload = {
        "holdingsChart": {
            "labels": chart_labels,
            "data": chart_data,
            "usesCostFallback": not all_prices_available,
        },
        "fearGreedChart": {
            "labels": fear_greed.get("chart_labels", []),
            "data": fear_greed.get("chart_data", []),
        },
        "tabs": [tab["id"] for tab in DEFAULT_TABS],
    }

    return {
        "site_title": SITE_TITLE,
        "site_subtitle": SITE_SUBTITLE,
        "updated_at": updated_at,
        "tabs": DEFAULT_TABS,
        "summary_cards": summary_cards,
        "holdings_rows": rows,
        "has_holdings": bool(rows),
        "holdings_chart_note": (
            "Using cost basis where live prices are unavailable / 若即時報價不可用，圖表暫以成本估算"
            if not all_prices_available
            else ""
        ),
        "fear_greed": {
            "score_str": fear_greed.get("score_str", "N/A"),
            "rating": fear_greed.get("rating", "N/A"),
            "previous_close_str": fear_greed.get("previous_close_str", "N/A"),
            "previous_close_rating": fear_greed.get("previous_close_rating", "N/A"),
            "delta_str": _format_percent(fear_greed_delta, signed=True),
            "delta_tone": _tone_for_number(fear_greed_delta),
            "week_ago": fear_greed.get("week_ago", {"score_str": "N/A", "rating": "N/A"}),
            "month_ago": fear_greed.get("month_ago", {"score_str": "N/A", "rating": "N/A"}),
            "year_ago": fear_greed.get("year_ago", {"score_str": "N/A", "rating": "N/A"}),
        },
        "sp500_trailing_pe": sp500_trailing_pe,
        "macro_cards": macro_cards,
        "sp500_snapshot_cards": sp500_snapshot_cards,
        "frontend_payload": frontend_payload,
    }
