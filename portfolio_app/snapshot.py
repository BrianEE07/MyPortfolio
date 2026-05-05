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
    PORTFOLIO_SNAPSHOTS_JSON_PATH,
    PROJECT_ROADMAP_COMPLETED,
    PROJECT_ROADMAP_NEXT,
    SITE_TITLE,
    TIMEZONE_NAME,
    WEALTH_GOAL_USD,
)
from .holdings import load_holdings
from .market_data import (
    cached_close,
    cached_fear_greed,
    cached_finra_margin,
    cached_shiller_pe,
    cached_sp500_historical,
    cached_sp500_trailing_pe,
    cached_stock_pe,
    cached_stock_profile,
    cached_stock_technicals,
)
from .metrics import load_portfolio_metrics


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


def _fear_greed_display_integer(value):
    if value is None:
        return None
    return int(float(value))


def _fear_greed_display_delta(current_score, previous_score):
    if current_score is None or previous_score is None:
        return None
    return _fear_greed_display_integer(current_score) - _fear_greed_display_integer(previous_score)


def _valuation_delta_tone(delta_value):
    if delta_value is None:
        return "muted"
    if delta_value > 0:
        return "loss"
    if delta_value < 0:
        return "gain"
    return "muted"


def _split_fear_greed_rating(rating):
    if not rating or rating == "N/A":
        return {"rating_en": "N/A", "rating_zh": "N/A"}
    if " / " not in rating:
        return {"rating_en": rating, "rating_zh": rating}
    rating_en, rating_zh = rating.split(" / ", 1)
    return {"rating_en": rating_en, "rating_zh": rating_zh}


def _fear_greed_level(score):
    if score is None:
        return "neutral"
    score = float(score)
    if score <= 24:
        return "extreme-fear"
    if score <= 44:
        return "fear"
    if score <= 55:
        return "neutral"
    if score <= 75:
        return "greed"
    return "extreme-greed"


def _coerce_score(value):
    if value is None or value == "N/A":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _market_trend_status(sp500_historical):
    if sp500_historical.get("broken_250"):
        return {
            "label_zh": "風險轉弱",
            "label_en": "Risk-Off",
            "tone": "loss",
            "summary_zh": "S&P 500 已跌破年線，先觀察能否重新站回長期趨勢。",
            "summary_en": "S&P 500 is below its 250-day average; watch whether it can reclaim the long-term trend.",
        }
    if sp500_historical.get("broken_60"):
        return {
            "label_zh": "趨勢降溫",
            "label_en": "Cooling",
            "tone": "warning",
            "summary_zh": "中期均線失守，但長期趨勢仍未明顯轉弱。",
            "summary_en": "The medium-term average is under pressure, while the long-term trend has not fully broken.",
        }
    if sp500_historical.get("broken_20"):
        return {
            "label_zh": "短線整理",
            "label_en": "Pullback",
            "tone": "warning",
            "summary_zh": "短線跌破月線，偏向正常回檔或整理。",
            "summary_en": "Price is below the 20-day average, suggesting a near-term pullback or consolidation.",
        }
    return {
        "label_zh": "多頭延伸",
        "label_en": "Bullish",
        "tone": "gain",
        "summary_zh": "價格站上主要均線，趨勢仍偏強。",
        "summary_en": "Price is above the key moving averages, keeping the trend constructive.",
    }


def _format_distance_from_reference(value, reference):
    value = _coerce_number(value)
    reference = _coerce_number(reference)
    if value is None or reference in (None, 0):
        return "N/A"
    return _format_percent((value - reference) / reference * 100, signed=True)


def _vix_zone(value):
    value = _coerce_number(value)
    if value is None:
        return {"label": "資料不足", "tone": "muted"}
    if value < 15:
        return {"label": "平靜", "tone": "gain"}
    if value < 20:
        return {"label": "正常", "tone": "gain"}
    if value < 30:
        return {"label": "緊張", "tone": "warning"}
    return {"label": "恐慌", "tone": "loss"}


def _put_call_zone(value):
    value = _coerce_number(value)
    if value is None:
        return {"label": "資料不足", "tone": "muted"}
    if value < 0.75:
        return {"label": "偏貪婪", "tone": "gain"}
    if value < 1.0:
        return {"label": "中性", "tone": "gain"}
    if value < 1.2:
        return {"label": "避險升溫", "tone": "warning"}
    return {"label": "恐懼", "tone": "loss"}


def _margin_debt_zone(value):
    value = _coerce_number(value)
    if value is None:
        return {"label": "資料不足", "tone": "muted"}
    if value > 3:
        return {"label": "槓桿升溫", "tone": "warning"}
    if value < -3:
        return {"label": "去槓桿", "tone": "loss"}
    return {"label": "溫和", "tone": "gain"}


def _valuation_tone(valuation):
    if not valuation or valuation == "N/A":
        return "muted"
    if any(keyword in valuation for keyword in ("Cheap", "便宜", "大底")):
        return "gain"
    if any(keyword in valuation for keyword in ("Bubble", "Expensive", "貴", "泡沫")):
        return "loss"
    return "warning"


def _zh_from_bilingual(value):
    if not value or value == "N/A":
        return "N/A"
    text = str(value)
    if " / " in text:
        return text.split(" / ", 1)[1]
    return text


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
    return load_portfolio_metrics(metrics_path)


def _resolve_portfolio_metrics_path(metrics_path=None):
    if metrics_path is not None:
        return metrics_path

    override_path = os.environ.get("PORTFOLIO_METRICS_PATH")
    if not override_path:
        return PORTFOLIO_METRICS_JSON_PATH

    return Path(override_path).expanduser()


def _load_latest_portfolio_snapshot(snapshots_path=None):
    snapshots_path = _resolve_portfolio_snapshots_path(snapshots_path)
    try:
        snapshots = json.loads(snapshots_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(snapshots, list) or not snapshots:
        return {}

    latest_snapshot = snapshots[-1]
    return latest_snapshot if isinstance(latest_snapshot, dict) else {}


def _resolve_portfolio_snapshots_path(snapshots_path=None):
    if snapshots_path is not None:
        return snapshots_path

    override_path = os.environ.get("PORTFOLIO_SNAPSHOTS_PATH")
    if not override_path:
        return PORTFOLIO_SNAPSHOTS_JSON_PATH

    return Path(override_path).expanduser()


def _coerce_optional_number(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    def build_card(label_zh, score, score_str, rating):
        rating_parts = _split_fear_greed_rating(rating)
        score_value = _coerce_score(score)
        if score_value is None:
            score_value = _coerce_score(score_str)
        return {
            "label_zh": label_zh,
            "score_str": score_str,
            "rating": rating,
            "rating_zh": rating_parts["rating_zh"],
            "level": _fear_greed_level(score_value),
        }

    return [
        build_card(
            "前收盤",
            fear_greed.get("previous_close"),
            fear_greed.get("previous_close_str", "N/A"),
            fear_greed.get("previous_close_rating", "N/A"),
        ),
        build_card(
            "一週前",
            fear_greed.get("week_ago", {}).get("score"),
            fear_greed.get("week_ago", {}).get("score_str", "N/A"),
            fear_greed.get("week_ago", {}).get("rating", "N/A"),
        ),
        build_card(
            "一月前",
            fear_greed.get("month_ago", {}).get("score"),
            fear_greed.get("month_ago", {}).get("score_str", "N/A"),
            fear_greed.get("month_ago", {}).get("rating", "N/A"),
        ),
        build_card(
            "一年前",
            fear_greed.get("year_ago", {}).get("score"),
            fear_greed.get("year_ago", {}).get("score_str", "N/A"),
            fear_greed.get("year_ago", {}).get("rating", "N/A"),
        ),
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


def _build_generated_portfolio_metric_display(metrics):
    return {
        "sharpe": metrics["sharpe"],
        "beta": metrics["beta"],
        "alpha": metrics["alpha"],
        "twr": metrics["twr"],
        "irr": metrics["irr"],
        "cagr": metrics["cagr"],
        "current_drawdown": metrics["current_drawdown"],
        "max_drawdown": metrics["max_drawdown"],
        "sp500_ytd_ret": metrics["sp500_ytd_ret"],
        "sharpe_str": (
            f"{metrics['sharpe']:.2f}"
            if metrics["sharpe"] is not None
            else "N/A"
        ),
        "beta_str": (
            f"{metrics['beta']:.2f}"
            if metrics["beta"] is not None
            else "N/A"
        ),
        "alpha_str": (
            f"{metrics['alpha']:.4f}"
            if metrics["alpha"] is not None
            else "N/A"
        ),
        "alpha_pct_str": _format_percent(metrics["alpha"], signed=True),
        "twr_str": _format_percent(metrics["twr"], signed=True),
        "irr_str": _format_percent(metrics["irr"], signed=True),
        "cagr_str": _format_percent(metrics["cagr"], signed=True),
        "current_drawdown_str": _format_percent(metrics["current_drawdown"]),
        "max_drawdown_str": _format_percent(metrics["max_drawdown"]),
        "sp500_ytd_ret_str": _format_percent(
            metrics["sp500_ytd_ret"],
            signed=True,
        ),
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
    latest_portfolio_snapshot = _load_latest_portfolio_snapshot()
    portfolio_cash_value = _coerce_optional_number(
        latest_portfolio_snapshot.get("portfolio_cash")
    )
    total_portfolio_value = (
        total_market_value_value + portfolio_cash_value
        if total_market_value_value is not None and portfolio_cash_value is not None
        else _coerce_optional_number(latest_portfolio_snapshot.get("total_portfolio_value"))
    )
    site_subtitle = _build_site_subtitle(total_portfolio_value, current_datetime)

    stored_portfolio_metrics = _load_portfolio_metrics()
    portfolio_metrics = _build_generated_portfolio_metric_display(
        stored_portfolio_metrics
    )
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
    fear_greed_display_delta = _fear_greed_display_delta(fear_greed_score, fear_greed_previous)

    sp500_trailing_pe = cached_sp500_trailing_pe()
    shiller_pe = cached_shiller_pe()
    finra_margin = cached_finra_margin() or {}
    sp500_historical = cached_sp500_historical() or {}

    fear_greed_history_cards = _build_fear_greed_history_cards(fear_greed)
    fear_greed_rating_parts = _split_fear_greed_rating(fear_greed.get("rating", "N/A"))

    market_sentiment = {
        "score": fear_greed_score,
        "score_str": fear_greed.get("score_str", "N/A"),
        "rating": fear_greed.get("rating", "N/A"),
        "rating_en": fear_greed_rating_parts["rating_en"],
        "rating_zh": fear_greed_rating_parts["rating_zh"],
        "delta_tone": "flat" if fear_greed_display_delta == 0 else _tone_for_number(fear_greed_display_delta),
        "delta_direction": _direction_for_number(fear_greed_display_delta),
        "gauge_rotation_deg": (
            round((fear_greed_score * 1.8) - 90, 2)
            if fear_greed_score is not None
            else -90
        ),
        "gauge_level": _fear_greed_level(fear_greed_score),
        "history_cards": fear_greed_history_cards,
        "source_url": "https://edition.cnn.com/markets/fear-and-greed",
        "source_tooltip_zh": "Open CNN Fear & Greed Index",
        "source_tooltip_en": "",
    }

    market_trend_signals = [
        {
            "label_zh": "月線",
            "label_en": "20MA",
            "value": sp500_historical.get("ma20_str", "N/A"),
            "distance": _format_distance_from_reference(
                sp500_historical.get("price"),
                sp500_historical.get("ma20"),
            ),
            "status": "跌破" if sp500_historical.get("broken_20") else "有守",
            "tone": "loss" if sp500_historical.get("broken_20") else "gain",
        },
        {
            "label_zh": "季線",
            "label_en": "60MA",
            "value": sp500_historical.get("ma60_str", "N/A"),
            "distance": _format_distance_from_reference(
                sp500_historical.get("price"),
                sp500_historical.get("ma60"),
            ),
            "status": "跌破" if sp500_historical.get("broken_60") else "有守",
            "tone": "loss" if sp500_historical.get("broken_60") else "gain",
        },
        {
            "label_zh": "年線",
            "label_en": "250MA",
            "value": sp500_historical.get("ma250_str", "N/A"),
            "distance": _format_distance_from_reference(
                sp500_historical.get("price"),
                sp500_historical.get("ma250"),
            ),
            "status": "跌破" if sp500_historical.get("broken_250") else "有守",
            "tone": "loss" if sp500_historical.get("broken_250") else "gain",
        },
        {
            "label_zh": "五年線",
            "label_en": "1250MA",
            "value": sp500_historical.get("ma1250_str", "N/A"),
            "distance": _format_distance_from_reference(
                sp500_historical.get("price"),
                sp500_historical.get("ma1250"),
            ),
            "status": "跌破" if sp500_historical.get("broken_1250") else "有守",
            "tone": "loss" if sp500_historical.get("broken_1250") else "gain",
        },
    ]
    market_trend_status = _market_trend_status(sp500_historical)

    market_trend = {
        "price_str": sp500_historical.get("price_str", "N/A"),
        "status": market_trend_status,
        "signals": market_trend_signals,
        "trailing_pe": {
            "value_str": sp500_trailing_pe.get("value_str", "N/A"),
            "prev_value_str": sp500_trailing_pe.get("prev_value_str", "N/A"),
            "delta_str": sp500_trailing_pe.get("delta_str", "N/A"),
            "delta_tone": _valuation_delta_tone(sp500_trailing_pe.get("delta")),
            "date": sp500_trailing_pe.get("date", "N/A"),
            "valuation_zh": _zh_from_bilingual(sp500_trailing_pe.get("valuation", "N/A")),
            "valuation_tone": _valuation_tone(sp500_trailing_pe.get("valuation", "N/A")),
        },
        "source_url": "https://finance.yahoo.com/quote/%5EGSPC/",
        "source_tooltip_zh": "Open Yahoo Finance S&P 500 Quote",
        "source_tooltip_en": "",
    }

    vix_zone = _vix_zone(fear_greed.get("vix") if fear_greed.get("vix") is not None else fear_greed.get("vix_str"))
    put_call_zone = _put_call_zone(
        fear_greed.get("pcr") if fear_greed.get("pcr") is not None else fear_greed.get("pcr_str")
    )
    margin_debt_zone = _margin_debt_zone(finra_margin.get("mom_str"))
    shiller_zone_label = _zh_from_bilingual(shiller_pe.get("valuation", "N/A"))
    shiller_tone = _valuation_tone(shiller_pe.get("valuation", "N/A"))
    vix_zone_tooltip = "• 低於 15：平靜\n• 15-20：正常\n• 20-30：緊張\n• 30 以上：恐慌"
    put_call_zone_tooltip = "• 低於 0.75：偏貪婪\n• 0.75-1.0：中性\n• 1.0-1.2：避險升溫\n• 1.2 以上：恐懼"
    margin_debt_zone_tooltip = "• 高於 +3%：槓桿升溫\n• -3% 到 +3%：溫和\n• 低於 -3%：去槓桿"
    shiller_zone_tooltip = "• 30 以上：泡沫高估區\n• 25-30：偏貴\n• 20-25：中性偏高\n• 15-20：合理偏便宜\n• 15 以下：十年一遇歷史大底"

    dip_signals = [
        {
            "title_zh": "波動率指數",
            "title_en": "VIX",
            "value": fear_greed.get("vix_str", "N/A"),
            "status_label": vix_zone["label"],
            "status_tone": vix_zone["tone"],
            "definition_zh": "衡量市場對未來波動的定價；越高代表避險和恐慌需求越強。",
            "side_stats": [],
            "meta": [
                {
                    "label": "目前區域",
                    "value": vix_zone["label"],
                    "tone": vix_zone["tone"],
                    "tooltip_zh": vix_zone_tooltip,
                },
                {"label": "抄底意義", "value": "高波動才有恐慌折價", "tone": "muted"},
            ],
            "tooltip_zh": "衡量市場對未來波動的定價；越高代表避險和恐慌需求越強。",
            "tooltip_en": "",
        },
        {
            "title_zh": "賣權買權比",
            "title_en": "Put / Call",
            "value": fear_greed.get("pcr_str", "N/A"),
            "status_label": put_call_zone["label"],
            "status_tone": put_call_zone["tone"],
            "definition_zh": "觀察選擇權市場避險需求；數字升高通常代表投資人更想買保護。",
            "side_stats": [],
            "meta": [
                {
                    "label": "目前區域",
                    "value": put_call_zone["label"],
                    "tone": put_call_zone["tone"],
                    "tooltip_zh": put_call_zone_tooltip,
                },
                {"label": "抄底意義", "value": "避險升溫時較有反向訊號", "tone": "muted"},
            ],
            "tooltip_zh": "觀察選擇權市場避險需求；數字升高通常代表投資人更想買保護。",
            "tooltip_en": "",
        },
        {
            "title_zh": "融資餘額",
            "title_en": "Margin Debt",
            "value": finra_margin.get("value_str", "N/A"),
            "status_label": margin_debt_zone["label"],
            "status_tone": margin_debt_zone["tone"],
            "definition_zh": "追蹤市場槓桿資金規模；快速增加偏熱，急速下降常見於去槓桿壓力。",
            "side_stats": [
                {"label": "最新月份", "value": finra_margin.get("latest_month", "N/A"), "tone": "muted"},
                {"label": "月變動", "value": finra_margin.get("mom_str", "N/A"), "tone": margin_debt_zone["tone"]},
            ],
            "meta": [
                {
                    "label": "目前區域",
                    "value": margin_debt_zone["label"],
                    "tone": margin_debt_zone["tone"],
                    "tooltip_zh": margin_debt_zone_tooltip,
                },
                {"label": "抄底意義", "value": "去槓桿後更接近清洗", "tone": "muted"},
            ],
            "tooltip_zh": "追蹤市場槓桿資金規模；快速增加偏熱，急速下降常見於去槓桿壓力。",
            "tooltip_en": "",
        },
        {
            "title_zh": "席勒本益比",
            "title_en": "Shiller P/E",
            "value": shiller_pe.get("value_str", "N/A"),
            "status_label": shiller_zone_label,
            "status_tone": shiller_tone,
            "definition_zh": "用十年平均盈餘平滑景氣循環，判斷大盤長期估值是否昂貴。",
            "side_stats": [],
            "meta": [
                {
                    "label": "目前區域",
                    "value": shiller_zone_label,
                    "tone": shiller_tone,
                    "tooltip_zh": shiller_zone_tooltip,
                },
                {"label": "抄底意義", "value": "估值越低，長期安全邊際越高", "tone": "muted"},
            ],
            "tooltip_zh": "用十年平均盈餘平滑景氣循環，判斷大盤長期估值是否昂貴。",
            "tooltip_en": "",
        },
    ]

    summary_primary_cards = [
        _build_summary_primary_card(
            "總市值",
            "Total Value",
            _format_currency(total_portfolio_value),
        ),
        _build_summary_primary_card(
            "現金餘額",
            "Cash Balance",
            _format_currency(portfolio_cash_value),
            label_en_compact="Cash",
        ),
        _build_summary_primary_card(
            "持倉市值",
            "Holdings Value",
            _format_currency(total_market_value_value),
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
            "持倉成本",
            "Holdings Cost",
            _format_currency(total_cost),
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
            portfolio_metrics["twr_str"],
            tooltip_zh=f"投資組合今年以來的報酬率，對照 S&P 500 為 {portfolio_metrics['sp500_ytd_ret_str']}。",
            tooltip_en="",
            label_en_compact="Port. YTD",
        ),
        _build_summary_secondary_card(
            "內部報酬",
            "IRR",
            portfolio_metrics["irr_str"],
            tooltip_zh="把每次入金、出金的時間也算進去後，投資組合的年化報酬率。越高代表資金投入的時間效率越好。",
            tooltip_en="",
        ),
        _build_summary_secondary_card(
            "年化成長",
            "CAGR",
            portfolio_metrics["cagr_str"],
            tooltip_zh="把第一天到今天的總報酬平均攤成年報酬率，像是在問每年平均長大多少。",
            tooltip_en="",
        ),
        _build_summary_secondary_card(
            "阿爾法值",
            "Alpha",
            portfolio_metrics["alpha_pct_str"],
            tooltip_zh="扣除市場波動影響後，相對 S&P 500 的超額報酬。正值通常代表跑贏基準。",
            tooltip_en="",
        ),
        _build_summary_secondary_card(
            "貝塔值",
            "Beta",
            portfolio_metrics["beta_str"],
            tooltip_zh="衡量投資組合相對 S&P 500 的波動敏感度。1.0 約等於跟大盤同步。",
            tooltip_en="",
        ),
        _build_summary_secondary_card(
            "夏普值",
            "Sharpe Ratio",
            portfolio_metrics["sharpe_str"],
            tooltip_zh="每承擔一單位波動風險，投資組合換回多少超額報酬。通常越高越好。",
            tooltip_en="",
            label_en_compact="Sharpe",
        ),
        _build_summary_secondary_card(
            "目前回檔",
            "Current Drawdown",
            portfolio_metrics["current_drawdown_str"],
            tone=_tone_for_number(portfolio_metrics["current_drawdown"]),
            tooltip_zh="目前總市值離歷史最高點跌了多少。0% 代表現在就在新高附近，負值越大代表離高點越遠。",
            tooltip_en="",
            label_en_compact="Curr. DD",
        ),
        _build_summary_secondary_card(
            "最大回檔",
            "Max Drawdown",
            portfolio_metrics["max_drawdown_str"],
            tone=_tone_for_number(portfolio_metrics["max_drawdown"]),
            tooltip_zh="這段紀錄裡，投資組合從高點跌到低點的最大跌幅。用來看最痛的下跌曾經有多深。",
            tooltip_en="",
            label_en_compact="Max DD",
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
            "ma20": sp500_historical.get("chart_ma20_points", []),
            "ma60": sp500_historical.get("chart_ma60_points", []),
            "ma250": sp500_historical.get("chart_ma250_points", []),
            "tone": market_trend_status["tone"],
        },
        "tabs": [tab["id"] for tab in DEFAULT_TABS],
    }

    return {
        "site_title": SITE_TITLE,
        "site_subtitle": site_subtitle["full_text"],
        "site_subtitle_parts": site_subtitle,
        "updated_at": updated_at,
        "project_roadmap_completed": PROJECT_ROADMAP_COMPLETED,
        "project_roadmap_next": PROJECT_ROADMAP_NEXT,
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
