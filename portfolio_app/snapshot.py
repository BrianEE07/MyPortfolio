import json
from datetime import datetime

from pytz import timezone

from .config import (
    DEFAULT_TABS,
    FIRST_US_STOCK_PURCHASE_DATE,
    PORTFOLIO_METRICS_JSON_PATH,
    SITE_TITLE,
    TIMEZONE_NAME,
    WEALTH_GOAL_USD,
)
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


def _format_whole_currency(value):
    if value is None:
        return "N/A"
    return f"${value:,.0f}"


def _format_detail_currency(value, decimals_small=2, decimals_medium=1):
    if value is None:
        return "N/A"
    absolute_value = abs(value)
    if absolute_value >= 100000:
        return f"${value:,.0f}"
    if absolute_value >= 10000:
        return f"${value:,.1f}"
    return f"${value:,.{decimals_small}f}" if absolute_value < 1000 else f"${value:,.{decimals_medium}f}"


def _format_percent(value, signed=False):
    if value is None:
        return "N/A"
    return f"{value:+.2f}%" if signed else f"{value:.2f}%"


def _format_percent_from_ratio(value, signed=False):
    if value is None:
        return "N/A"
    return _format_percent(value * 100, signed=signed)


def _format_detail_percent(value):
    if value is None:
        return "N/A"
    if value == 0:
        return "0.00%"
    if abs(value) >= 100:
        return f"{value:+.1f}%"
    return f"{value:+.2f}%"


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


def _format_detail_shares(value):
    if value is None:
        return "N/A"

    absolute_value = abs(value)
    if absolute_value >= 1000:
        formatted = f"{value:,.1f}"
    elif absolute_value >= 100:
        formatted = f"{value:,.2f}"
    elif absolute_value >= 1:
        formatted = f"{value:,.4f}"
    else:
        formatted = f"{value:,.5f}"

    return formatted.rstrip("0").rstrip(".")


def _format_detail_signed_currency(value):
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else "-" if value < 0 else ""
    return sign + _format_detail_currency(abs(value))


def _trend_label(is_below_ma250):
    if is_below_ma250:
        return "Below 250D"
    return "Above 250D"


def _coerce_number(value):
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


def _load_portfolio_metrics(metrics_path=None):
    metrics_path = metrics_path or PORTFOLIO_METRICS_JSON_PATH
    empty_metrics = {"realized_pl": None, "realized_return_pct": None}

    try:
        if not metrics_path.exists():
            return empty_metrics
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return empty_metrics

    if not isinstance(payload, dict):
        return empty_metrics

    return {
        "realized_pl": _coerce_number(payload.get("realized_pl")),
        "realized_return_pct": _coerce_number(payload.get("realized_return_pct")),
    }


def _build_summary_primary_card(
    label_zh,
    label_en,
    value,
    tone=None,
    accent_value=None,
    accent_tone=None,
    label_en_compact=None,
):
    return {
        "label_zh": label_zh,
        "label_en": label_en,
        "label_en_compact": label_en_compact or label_en,
        "label_text": f"{label_zh} / {label_en}",
        "label_text_compact": f"{label_zh} / {label_en_compact or label_en}",
        "value": value,
        "tone": tone,
        "accent_value": accent_value,
        "accent_tone": accent_tone,
    }


def _build_summary_secondary_card(
    label_zh,
    label_en,
    value,
    tone=None,
    tooltip_zh="",
    tooltip_en="",
    label_en_compact=None,
):
    return {
        "label_zh": label_zh,
        "label_en": label_en,
        "label_en_compact": label_en_compact or label_en,
        "label_text": f"{label_zh} / {label_en}",
        "label_text_compact": f"{label_zh} / {label_en_compact or label_en}",
        "value": value,
        "tone": tone,
        "tooltip_zh": tooltip_zh,
        "tooltip_en": tooltip_en,
    }


def _build_concentration_cards(rows):
    concentration_rows = (
        ("Top 3", 3),
        ("Top 5", 5),
        ("Top 10", 10),
    )
    total_sort_value = sum(row["sort_value"] for row in rows)
    cards = []

    for label, limit in concentration_rows:
        share_ratio = (
            sum(row["sort_value"] for row in rows[:limit]) / total_sort_value
            if total_sort_value
            else None
        )
        cards.append(
            {
                "label": label,
                "value": _format_percent_from_ratio(share_ratio),
            }
        )

    return cards


def _build_site_subtitle(current_market_value, current_datetime):
    start_date = datetime.strptime(FIRST_US_STOCK_PURCHASE_DATE, "%Y-%m-%d").date()
    current_date = current_datetime.date()
    journey_day = max((current_date - start_date).days + 1, 1)

    prefix = f"邁向財富自由之路的第 {journey_day} 天"
    if current_market_value is None:
        return {
            "full_text": f"{prefix}｜進度暫不可用",
            "lead_text": prefix,
            "progress_text": "進度暫不可用",
        }

    progress_pct = (current_market_value / WEALTH_GOAL_USD) * 100
    progress_text = (
        f"{_format_percent(progress_pct)}"
        f" · {_format_currency(current_market_value)} / {_format_whole_currency(WEALTH_GOAL_USD)}"
    )
    return {
        "full_text": f"{prefix}｜{progress_text}",
        "lead_text": prefix,
        "progress_text": progress_text,
    }


def build_portfolio_snapshot():
    """Build the server-side snapshot used by Flask rendering and static export."""
    holdings = load_holdings()
    current_timezone = timezone(TIMEZONE_NAME)
    current_datetime = datetime.now(current_timezone)
    updated_at = current_datetime.strftime("%Y-%m-%d %H:%M")

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
                "shares_str": _format_detail_shares(shares),
                "cost_basis": cost_basis,
                "cost_basis_str": f"{cost_basis:.2f}",
                "cost_basis_detail_str": _format_detail_currency(cost_basis).replace("$", ""),
                "cost_total": cost_total,
                "cost_total_str": _format_currency(cost_total),
                "price": live_price,
                "price_str": f"{live_price:.2f}" if live_price is not None else "N/A",
                "price_detail_str": _format_detail_currency(live_price),
                "price_tone": (
                    _tone_for_number(live_price - cost_basis)
                    if live_price is not None
                    else "muted"
                ),
                "market_value": market_value,
                "market_value_str": _format_currency(market_value),
                "market_value_detail_str": _format_detail_currency(market_value),
                "profit": profit,
                "profit_str": _format_currency(profit),
                "profit_detail_str": _format_detail_signed_currency(profit),
                "profit_pct": profit_pct,
                "profit_pct_str": _format_percent(profit_pct, signed=True),
                "profit_pct_detail_str": _format_detail_percent(profit_pct),
                "profit_tone": _tone_for_number(profit),
                "drawdown": technicals.get("drawdown"),
                "drawdown_str": _format_percent(technicals.get("drawdown"), signed=True),
                "drawdown_detail_str": _format_detail_percent(technicals.get("drawdown")),
                "drawdown_tone": _tone_for_number(technicals.get("drawdown")),
                "trailing_pe": (
                    pe_data.get("trailing_pe")
                    if pe_data and pe_data.get("trailing_pe") is not None
                    else None
                ),
                "trailing_pe_str": (
                    f"{pe_data['trailing_pe']:.1f}"
                    if pe_data and pe_data.get("trailing_pe") is not None
                    else "N/A"
                ),
                "forward_pe": (
                    pe_data.get("forward_pe")
                    if pe_data and pe_data.get("forward_pe") is not None
                    else None
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
    site_subtitle = _build_site_subtitle(total_market_value_value, current_datetime)

    portfolio_metrics = cached_portfolio_metrics(holdings)
    stored_portfolio_metrics = _load_portfolio_metrics()
    top_holdings = rows[:10]
    chart_labels = [row["symbol"] for row in top_holdings]
    chart_data = [round(row["sort_value"], 2) for row in top_holdings]
    holdings_concentration_cards = _build_concentration_cards(rows)

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

    summary_primary_cards = [
        _build_summary_primary_card(
            "總市值",
            "Total Value",
            _format_currency(total_market_value_value),
        ),
        _build_summary_primary_card(
            "總成本",
            "Total Cost",
            _format_currency(total_cost),
        ),
        _build_summary_primary_card(
            "未實現損益",
            "Unrealized P/L",
            _format_currency(total_profit_value),
            tone=_tone_for_number(total_profit_value),
            accent_value=_format_percent(total_profit_pct_value, signed=True),
            accent_tone=_tone_for_number(total_profit_pct_value),
            label_en_compact="Unreal. P/L",
        ),
        _build_summary_primary_card(
            "已實現損益",
            "Realized P/L",
            _format_currency(stored_portfolio_metrics["realized_pl"]),
            tone=_tone_for_number(stored_portfolio_metrics["realized_pl"]),
            accent_value=_format_percent(
                stored_portfolio_metrics["realized_return_pct"],
                signed=True,
            ),
            accent_tone=_tone_for_number(stored_portfolio_metrics["realized_return_pct"]),
            label_en_compact="Real. P/L",
        ),
    ]

    summary_secondary_cards = [
        _build_summary_secondary_card(
            "持倉 YTD",
            "Portfolio YTD",
            portfolio_metrics["portfolio_ytd_ret_str"],
            tooltip_zh=f"投資組合今年以來的報酬率，對照 S&P 500 為 {portfolio_metrics['sp500_ytd_ret_str']}。",
            tooltip_en=f"Portfolio return year to date. S&P 500 YTD is {portfolio_metrics['sp500_ytd_ret_str']}.",
            label_en_compact="Port. YTD",
        ),
        _build_summary_secondary_card(
            "夏普值",
            "Sharpe Ratio",
            portfolio_metrics["sharpe_str"],
            tooltip_zh="每承擔一單位波動風險，投資組合換回多少超額報酬。通常越高越好。",
            tooltip_en="Shows how much excess return the portfolio earns per unit of volatility. Higher is generally better.",
            label_en_compact="Sharpe",
        ),
        _build_summary_secondary_card(
            "貝塔值",
            "Beta",
            portfolio_metrics["beta_str"],
            tooltip_zh="衡量投資組合相對 S&P 500 的波動敏感度。1.0 約等於跟大盤同步。",
            tooltip_en="Measures how sensitive the portfolio is to S&P 500 moves. Around 1.0 means market-like swings.",
        ),
        _build_summary_secondary_card(
            "阿爾法值",
            "Alpha",
            portfolio_metrics["alpha_pct_str"],
            tooltip_zh="扣除市場波動影響後，相對 S&P 500 的超額報酬。正值通常代表跑贏基準。",
            tooltip_en="Measures excess return beyond what market exposure would imply versus the S&P 500. Positive values generally indicate outperformance.",
        ),
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
        },
        "fearGreedChart": {
            "labels": fear_greed.get("chart_labels", []),
            "data": fear_greed.get("chart_data", []),
        },
        "tabs": [tab["id"] for tab in DEFAULT_TABS],
    }

    return {
        "site_title": SITE_TITLE,
        "site_subtitle": site_subtitle["full_text"],
        "site_subtitle_parts": site_subtitle,
        "updated_at": updated_at,
        "tabs": DEFAULT_TABS,
        "summary_primary_cards": summary_primary_cards,
        "summary_secondary_cards": summary_secondary_cards,
        "holdings_rows": rows,
        "has_holdings": bool(rows),
        "holdings_concentration_cards": holdings_concentration_cards,
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
