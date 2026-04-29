import json
import os
from datetime import datetime
from pathlib import Path

from pytz import timezone

from .categories import resolve_holding_category
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
    cached_stock_profile,
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
    sign = "+" if value > 0 else "-" if value < 0 else ""
    return sign + _format_currency(abs(value))


def _tone_for_number(value):
    if value is None:
        return "muted"
    if value > 0:
        return "gain"
    if value < 0:
        return "loss"
    return "muted"


def _direction_for_number(value):
    if value is None:
        return "flat"
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


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
    metrics_path = _resolve_portfolio_metrics_path(metrics_path)
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


def _resolve_portfolio_metrics_path(metrics_path=None):
    if metrics_path is not None:
        return metrics_path

    override_path = os.environ.get("PORTFOLIO_METRICS_PATH")
    if not override_path:
        return PORTFOLIO_METRICS_JSON_PATH

    return Path(override_path).expanduser()


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


def _build_top_holdings_chart(rows):
    top_holdings = rows[:10]
    chart_rows = list(top_holdings)
    other_count = max(len(rows) - 10, 0)

    if other_count:
        other_value = sum(row["sort_value"] for row in rows[10:])
        chart_rows.append(
            {
                "symbol": "Others",
                "chart_label": "Others",
                "company_name": "Others",
                "sort_value": other_value,
                "is_other_bucket": True,
            }
        )

    chart_labels = [row.get("chart_label", row["symbol"]) for row in chart_rows]
    chart_company_names = [row.get("company_name") or row["symbol"] for row in chart_rows]
    chart_data = [round(row["sort_value"], 2) for row in chart_rows]
    chart_colors = [
        "#de8b5f",
        "#97b79d",
        "#81a3ca",
        "#dfbe76",
        "#ad98c8",
        "#8abac1",
        "#d79ca1",
        "#d9aa7d",
        "#9bb1df",
        "#9fc3a6",
        "#b2a8a0",
    ][: len(chart_rows)]

    return {
        "labels": chart_labels,
        "company_names": chart_company_names,
        "data": chart_data,
        "colors": chart_colors,
        "has_other_bucket": bool(other_count),
        "other_count": other_count,
    }


def _build_holdings_category_breakdown(rows):
    total_value = sum(row["sort_value"] for row in rows)
    grouped = {}

    for row in rows:
        category_id = row["category"]["id"]
        bucket = grouped.setdefault(
            category_id,
            {
                "category": row["category"],
                "market_value": 0.0,
                "count": 0,
            },
        )
        bucket["market_value"] += row["sort_value"]
        bucket["count"] += 1

    segments = []
    for category_id, bucket in grouped.items():
        share_ratio = (bucket["market_value"] / total_value) if total_value else None
        category = bucket["category"]
        segments.append(
            {
                "id": category_id,
                "label_zh": category["label_zh"],
                "label_en": category["label_en"],
                "label": f"{category['label_zh']} {_format_percent_from_ratio(share_ratio)}",
                "color": category["color"],
                "market_value": bucket["market_value"],
                "market_value_str": _format_currency(bucket["market_value"]),
                "share_ratio": share_ratio,
                "share_ratio_str": _format_percent_from_ratio(share_ratio),
                "count": bucket["count"],
            }
        )

    segments.sort(key=lambda item: item["market_value"], reverse=True)
    return segments


def _build_fear_greed_history_cards(fear_greed):
    return [
        {
            "label_en": "Previous close",
            "label_zh": "前一日",
            "score_str": fear_greed.get("previous_close_str", "N/A"),
            "rating": fear_greed.get("previous_close_rating", "N/A"),
        },
        {
            "label_en": "1 week ago",
            "label_zh": "一週前",
            "score_str": fear_greed.get("week_ago", {}).get("score_str", "N/A"),
            "rating": fear_greed.get("week_ago", {}).get("rating", "N/A"),
        },
        {
            "label_en": "1 month ago",
            "label_zh": "一月前",
            "score_str": fear_greed.get("month_ago", {}).get("score_str", "N/A"),
            "rating": fear_greed.get("month_ago", {}).get("rating", "N/A"),
        },
        {
            "label_en": "1 year ago",
            "label_zh": "一年前",
            "score_str": fear_greed.get("year_ago", {}).get("score_str", "N/A"),
            "rating": fear_greed.get("year_ago", {}).get("rating", "N/A"),
        },
    ]


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
        profile_data = cached_stock_profile(symbol) or {}
        technicals = cached_stock_technicals(symbol) or {}
        category = resolve_holding_category(
            symbol,
            sector=profile_data.get("sector"),
            industry=profile_data.get("industry"),
        )
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
                "company_name": profile_data.get("company_name") or symbol,
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
                "category": category,
                "category_id": category["id"],
                "category_label_zh": category["label_zh"],
                "category_label_en": category["label_en"],
                "category_color": category["color"],
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
    top_holdings_chart = _build_top_holdings_chart(rows)
    holdings_concentration_cards = _build_concentration_cards(rows)
    holdings_category_segments = _build_holdings_category_breakdown(rows)

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

    fear_greed_history_cards = _build_fear_greed_history_cards(fear_greed)

    market_sentiment = {
        "score": fear_greed_score,
        "score_str": fear_greed.get("score_str", "N/A"),
        "rating": fear_greed.get("rating", "N/A"),
        "delta_tone": _tone_for_number(fear_greed_delta),
        "delta_direction": _direction_for_number(fear_greed_delta),
        "gauge_rotation_deg": (
            round((fear_greed_score * 1.8) - 90, 2)
            if fear_greed_score is not None
            else -90
        ),
        "history_cards": fear_greed_history_cards,
        "source_url": "https://edition.cnn.com/markets/fear-and-greed",
        "source_tooltip_zh": "CNN Fear & Greed Index",
        "source_tooltip_en": "Open CNN Fear & Greed Index",
    }

    market_trend_signals = [
        {
            "label_zh": "月線",
            "label_en": "20MA",
            "value": sp500_historical.get("ma20_str", "N/A"),
            "status": "跌破" if sp500_historical.get("broken_20") else "有守",
            "tone": "loss" if sp500_historical.get("broken_20") else "gain",
        },
        {
            "label_zh": "季線",
            "label_en": "60MA",
            "value": sp500_historical.get("ma60_str", "N/A"),
            "status": "跌破" if sp500_historical.get("broken_60") else "有守",
            "tone": "loss" if sp500_historical.get("broken_60") else "gain",
        },
        {
            "label_zh": "年線",
            "label_en": "250MA",
            "value": sp500_historical.get("ma250_str", "N/A"),
            "status": "跌破" if sp500_historical.get("broken_250") else "有守",
            "tone": "loss" if sp500_historical.get("broken_250") else "gain",
        },
        {
            "label_zh": "五年線",
            "label_en": "1250MA",
            "value": sp500_historical.get("ma1250_str", "N/A"),
            "status": "跌破" if sp500_historical.get("broken_1250") else "有守",
            "tone": "loss" if sp500_historical.get("broken_1250") else "gain",
        },
    ]

    market_trend = {
        "price_str": sp500_historical.get("price_str", "N/A"),
        "signals": market_trend_signals,
        "trailing_pe": {
            "value_str": sp500_trailing_pe.get("value_str", "N/A"),
            "prev_value_str": sp500_trailing_pe.get("prev_value_str", "N/A"),
            "delta_str": sp500_trailing_pe.get("delta_str", "N/A"),
            "date": sp500_trailing_pe.get("date", "N/A"),
            "valuation": sp500_trailing_pe.get("valuation", "N/A"),
        },
        "source_url": "https://finance.yahoo.com/quote/%5EGSPC/",
        "source_tooltip_zh": "Yahoo Finance S&P 500 + Multpl Trailing P/E",
        "source_tooltip_en": "Open Yahoo Finance S&P 500 quote",
    }

    dip_signals = [
        {
            "title_zh": "波動率指數",
            "title_en": "VIX",
            "value": fear_greed.get("vix_str", "N/A"),
            "tooltip_zh": "CNN Fear & Greed 的市場波動子指標。數字越高，市場越偏向避險。",
            "tooltip_en": "CNN volatility component. Higher readings usually mean risk-off sentiment.",
        },
        {
            "title_zh": "賣權買權比",
            "title_en": "Put / Call",
            "value": fear_greed.get("pcr_str", "N/A"),
            "tooltip_zh": "CNN Fear & Greed 的選擇權情緒子指標。數字偏高通常代表避險需求上升。",
            "tooltip_en": "CNN options positioning component. Higher readings often imply more hedging demand.",
        },
        {
            "title_zh": "融資餘額",
            "title_en": "Margin Debt",
            "value": finra_margin.get("value_str", "N/A"),
            "tooltip_zh": (
                f"FINRA 最新月份 {finra_margin.get('latest_month', 'N/A')}，"
                f"月變動 {finra_margin.get('mom_str', 'N/A')}。"
            ),
            "tooltip_en": (
                f"FINRA latest month {finra_margin.get('latest_month', 'N/A')}, "
                f"month-over-month {finra_margin.get('mom_str', 'N/A')}."
            ),
        },
        {
            "title_zh": "席勒本益比",
            "title_en": "Shiller P/E",
            "value": shiller_pe.get("value_str", "N/A"),
            "tooltip_zh": f"Multpl 十年平滑本益比，目前估值區間為 {shiller_pe.get('valuation', 'N/A')}。",
            "tooltip_en": f"Multpl cyclically adjusted valuation. Current zone: {shiller_pe.get('valuation', 'N/A')}.",
        },
    ]

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
            "Unrealized P&L",
            _format_signed_currency(total_profit_value),
            tone=_tone_for_number(total_profit_value),
            accent_value=_format_percent(total_profit_pct_value, signed=True),
            accent_tone=_tone_for_number(total_profit_pct_value),
            label_en_compact="Unreal. P&L",
        ),
        _build_summary_primary_card(
            "已實現損益",
            "Realized P&L",
            _format_signed_currency(stored_portfolio_metrics["realized_pl"]),
            tone=_tone_for_number(stored_portfolio_metrics["realized_pl"]),
            accent_value=_format_percent(
                stored_portfolio_metrics["realized_return_pct"],
                signed=True,
            ),
            accent_tone=_tone_for_number(stored_portfolio_metrics["realized_return_pct"]),
            label_en_compact="Real. P&L",
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
            "阿爾法值",
            "Alpha",
            portfolio_metrics["alpha_pct_str"],
            tooltip_zh="扣除市場波動影響後，相對 S&P 500 的超額報酬。正值通常代表跑贏基準。",
            tooltip_en="Measures excess return beyond what market exposure would imply versus the S&P 500. Positive values generally indicate outperformance.",
        ),
        _build_summary_secondary_card(
            "貝塔值",
            "Beta",
            portfolio_metrics["beta_str"],
            tooltip_zh="衡量投資組合相對 S&P 500 的波動敏感度。1.0 約等於跟大盤同步。",
            tooltip_en="Measures how sensitive the portfolio is to S&P 500 moves. Around 1.0 means market-like swings.",
        ),
    ]

    frontend_payload = {
        "holdingsChart": {
            "labels": top_holdings_chart["labels"],
            "companyNames": top_holdings_chart["company_names"],
            "data": top_holdings_chart["data"],
            "colors": top_holdings_chart["colors"],
        },
        "fearGreedChart": {
            "labels": fear_greed.get("chart_labels", []),
            "data": fear_greed.get("chart_data", []),
        },
        "sp500TrendChart": {
            "labels": sp500_historical.get("chart_labels", []),
            "data": sp500_historical.get("chart_points", []),
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
        "holdings_category_segments": holdings_category_segments,
        "top_holdings_chart": top_holdings_chart,
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
        "market_sentiment": market_sentiment,
        "market_trend": market_trend,
        "dip_signals": dip_signals,
        "sp500_trailing_pe": sp500_trailing_pe,
        "frontend_payload": frontend_payload,
    }
