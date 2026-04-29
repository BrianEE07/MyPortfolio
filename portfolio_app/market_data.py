import json
import re
import threading
import time
import zipfile
from datetime import datetime, timedelta
from io import BytesIO
from xml.etree import ElementTree

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from pytz import timezone

from .config import TIMEZONE_NAME

_TTL_FAST = 60
_TTL_NORMAL = 300
_cache = {}
_cache_lock = threading.Lock()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

CNN_FNG_BASE_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
SP500_TRAILING_URL = "https://www.multpl.com/s-p-500-pe-ratio/table/by-month"
SP500_SHILLER_URL = "https://www.multpl.com/shiller-pe/table/by-month"
SP500_TRAILING_SOURCE_URL = "https://www.multpl.com/s-p-500-pe-ratio"
SP500_YAHOO_SOURCE_URL = "https://finance.yahoo.com/quote/%5EGSPC/"
FINRA_MARGIN_URL = "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"
FINRA_MARGIN_DOWNLOAD_URL = (
    "https://www.finra.org/sites/default/files/2022-05/debitbalances.xlsx"
)
FINRA_MARGIN_FALLBACK_ROWS = (
    ("Mar-26", 1220922),
    ("Feb-26", 1253192),
    ("Jan-26", 1279042),
    ("Dec-25", 1225597),
)


def _now() -> float:
    return time.time()


def _get_cache(key):
    with _cache_lock:
        return _cache.get(key)


def _set_cache(key, value):
    with _cache_lock:
        _cache[key] = value


def _timezone():
    return timezone(TIMEZONE_NAME)


def _format_fg_block(block):
    score = block.get("score")
    if score is None:
        return {"score": None, "score_str": "N/A", "rating": "N/A"}
    score = float(score)
    return {
        "score": score,
        "score_str": f"{score:.0f}",
        "rating": fear_greed_label(score),
    }


def _nearest_historical_value(chart_points, target_dt):
    if not chart_points:
        return None
    best = min(chart_points, key=lambda point: abs((point["dt"] - target_dt).total_seconds()))
    value = best.get("value")
    return float(value) if value is not None else None


def fear_greed_label(score):
    """Map CNN Fear & Greed scores to bilingual rating labels."""
    if score is None:
        return "N/A"
    score = float(score)
    if 0 <= score <= 24:
        return "Extreme Fear / 極度恐懼"
    if 25 <= score <= 44:
        return "Fear / 恐懼"
    if 45 <= score <= 55:
        return "Neutral / 中性"
    if 56 <= score <= 74:
        return "Greed / 貪婪"
    if 75 <= score <= 100:
        return "Extreme Greed / 極度貪婪"
    return "N/A"


def sp500_trailing_pe_valuation(value):
    if value is None:
        return "N/A"
    if value >= 28:
        return "Expensive / 偏貴"
    if value >= 22:
        return "Elevated / 中高"
    if value >= 18:
        return "Neutral / 中性"
    return "Relatively Cheap / 偏便宜"


def shiller_pe_valuation(value):
    if value is None:
        return "N/A"
    if value >= 30:
        return "Bubble Zone / 泡沫高估區"
    if value >= 25:
        return "Expensive / 偏貴"
    if value >= 20:
        return "Above Neutral / 中性偏高"
    if value >= 15:
        return "Reasonable / 合理偏便宜"
    return "Rarely Cheap / 十年一遇歷史大底"


def fetch_price_from_yahoo(symbol):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            result = data.get("chart", {}).get("result")
            if result:
                meta = result[0].get("meta", {})
                price = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
                return float(price) if price is not None else None
    except Exception as exc:
        print(f"Error fetching {symbol}: {exc}")
    return None


def cached_close(symbol, ttl=_TTL_FAST):
    key = ("price", symbol)
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl) and entry["price"] is not None:
        return entry["price"]
    price = fetch_price_from_yahoo(symbol)
    if price is not None:
        _set_cache(key, {"ts": now, "price": price})
        return price
    if entry and entry["price"] is not None:
        return entry["price"]
    return None


def fetch_stock_pe(symbol):
    try:
        info = yf.Ticker(symbol).info
        return {
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
        }
    except Exception as exc:
        print(f"Error fetching PE for {symbol}: {exc}")
        return {"trailing_pe": None, "forward_pe": None}


def cached_stock_pe(symbol, ttl=3600):
    key = ("pe", symbol)
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl):
        return entry["data"]
    data = fetch_stock_pe(symbol)
    _set_cache(key, {"ts": now, "data": data})
    return data


def fetch_stock_technicals(symbol):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            result = data.get("chart", {}).get("result")
            if result:
                indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
                highs = indicators.get("high", [])
                closes = indicators.get("close", [])
                valid_highs = [value for value in highs if value is not None]
                valid_closes = [value for value in closes if value is not None]
                if not valid_highs or not valid_closes:
                    return None

                meta = result[0].get("meta", {})
                current_price = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
                max_high = max(valid_highs)
                drawdown = None
                if max_high and current_price:
                    drawdown = (current_price - max_high) / max_high * 100

                moving_average_60 = (
                    sum(valid_closes[-60:]) / 60 if len(valid_closes) >= 60 else None
                )
                moving_average_250 = (
                    sum(valid_closes[-250:]) / 250 if len(valid_closes) >= 250 else None
                )

                return {
                    "drawdown": drawdown,
                    "ma60": moving_average_60,
                    "ma250": moving_average_250,
                    "price": current_price,
                }
    except Exception as exc:
        print(f"Error fetching technicals for {symbol}: {exc}")
    return None


def cached_stock_technicals(symbol, ttl=_TTL_NORMAL):
    key = ("technicals", symbol)
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl) and entry["data"] is not None:
        return entry["data"]
    data = fetch_stock_technicals(symbol)
    if data is not None:
        _set_cache(key, {"ts": now, "data": data})
        return data
    if entry and entry["data"] is not None:
        return entry["data"]
    return None


def fetch_stock_profile(symbol):
    try:
        info = yf.Ticker(symbol).info
        return {
            "company_name": (
                info.get("longName")
                or info.get("shortName")
                or info.get("displayName")
                or symbol
            ),
            "sector": info.get("sectorDisp") or info.get("sector"),
            "industry": info.get("industryDisp") or info.get("industry"),
        }
    except Exception as exc:
        print(f"Error fetching profile for {symbol}: {exc}")
        return {"company_name": symbol, "sector": None, "industry": None}


def cached_stock_profile(symbol, ttl=3600):
    key = ("profile", symbol)
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl):
        return entry["data"]
    data = fetch_stock_profile(symbol)
    _set_cache(key, {"ts": now, "data": data})
    return data


def _portfolio_cache_key(holdings):
    return tuple(
        sorted(
            (
                holding["symbol"],
                round(float(holding["shares"]), 8),
                round(float(holding["cost_basis"]), 8),
            )
            for holding in holdings
        )
    )


def fetch_portfolio_metrics(holdings):
    try:
        symbols = [holding["symbol"] for holding in holdings]
        if not symbols:
            return None

        tickers = symbols + ["^GSPC"]
        downloaded = yf.download(
            tickers=tickers,
            period="ytd",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
        if downloaded.empty:
            return None

        if isinstance(downloaded.columns, pd.MultiIndex):
            if "Close" in downloaded.columns.get_level_values(0):
                close_data = downloaded["Close"]
            elif "Adj Close" in downloaded.columns.get_level_values(0):
                close_data = downloaded["Adj Close"]
            else:
                return None
        else:
            column_name = None
            if "Close" in downloaded.columns:
                column_name = "Close"
            elif "Adj Close" in downloaded.columns:
                column_name = "Adj Close"
            if column_name is None:
                return None
            close_data = downloaded[[column_name]]

        close_data = close_data.ffill().bfill()
        if "^GSPC" not in close_data.columns:
            return None

        sp500_returns = close_data["^GSPC"].pct_change().dropna()
        if sp500_returns.empty:
            return None

        portfolio_value = pd.Series(0.0, index=close_data.index)
        for holding in holdings:
            symbol = holding["symbol"]
            if symbol in close_data.columns:
                portfolio_value += close_data[symbol] * holding["shares"]

        portfolio_returns = portfolio_value.pct_change().dropna()
        aligned = pd.concat([portfolio_returns, sp500_returns], axis=1).dropna()
        if aligned.empty:
            return None

        portfolio_series = aligned.iloc[:, 0]
        benchmark_series = aligned.iloc[:, 1]

        risk_free_rate = 0.04 / 252
        excess_returns = portfolio_series - risk_free_rate
        standard_deviation = excess_returns.std()
        sharpe_ratio = (
            0
            if standard_deviation == 0
            else np.sqrt(252) * excess_returns.mean() / standard_deviation
        )

        covariance_matrix = np.cov(portfolio_series, benchmark_series)
        benchmark_variance = covariance_matrix[1, 1]
        beta = covariance_matrix[0, 1] / benchmark_variance if benchmark_variance != 0 else 1

        annual_portfolio_return = (portfolio_series + 1).prod() - 1
        annual_sp500_return = (benchmark_series + 1).prod() - 1
        ytd_risk_free = risk_free_rate * len(portfolio_series)
        alpha = annual_portfolio_return - (
            ytd_risk_free + beta * (annual_sp500_return - ytd_risk_free)
        )

        return {
            "sharpe": float(sharpe_ratio),
            "beta": float(beta),
            "alpha": float(alpha),
            "portfolio_ytd_ret": float(annual_portfolio_return),
            "sp500_ytd_ret": float(annual_sp500_return),
            "sharpe_str": f"{sharpe_ratio:.2f}",
            "beta_str": f"{beta:.2f}",
            "alpha_str": f"{alpha:.4f}",
            "alpha_pct_str": f"{alpha * 100:+.2f}%",
            "sp500_ytd_ret_str": f"{annual_sp500_return * 100:+.2f}%",
            "portfolio_ytd_ret_str": f"{annual_portfolio_return * 100:+.2f}%",
        }
    except Exception as exc:
        print(f"Error calculating portfolio metrics: {exc}")
        return None


def cached_portfolio_metrics(holdings, ttl=3600):
    key = ("portfolio_metrics", _portfolio_cache_key(holdings))
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl) and entry["data"] is not None:
        return entry["data"]
    data = fetch_portfolio_metrics(holdings)
    if data is not None:
        _set_cache(key, {"ts": now, "data": data})
        return data
    if entry and entry["data"] is not None:
        return entry["data"]
    return {
        "sharpe": None,
        "beta": None,
        "alpha": None,
        "portfolio_ytd_ret": None,
        "sp500_ytd_ret": None,
        "sharpe_str": "N/A",
        "beta_str": "N/A",
        "alpha_str": "N/A",
        "alpha_pct_str": "N/A",
        "sp500_ytd_ret_str": "N/A",
        "portfolio_ytd_ret_str": "N/A",
    }


def fetch_sp500_historical():
    url = "https://query2.finance.yahoo.com/v8/finance/chart/^GSPC?range=5y&interval=1d"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            data = response.json()
            result = data.get("chart", {}).get("result", [])
            if result:
                timestamps = result[0].get("timestamp", [])
                indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
                closes = indicators.get("close", [])
                valid = [(ts, close) for ts, close in zip(timestamps, closes) if close is not None]
                if not valid:
                    return None

                close_values = [value for _, value in valid]
                current_price = close_values[-1]
                ma20 = sum(close_values[-20:]) / 20 if len(close_values) >= 20 else None
                ma60 = sum(close_values[-60:]) / 60 if len(close_values) >= 60 else None
                ma250 = sum(close_values[-250:]) / 250 if len(close_values) >= 250 else None
                ma1250 = sum(close_values[-1250:]) / 1250 if len(close_values) >= 1250 else None

                chart_data = valid[-250:]
                labels = [
                    datetime.fromtimestamp(ts, tz=_timezone()).strftime("%y/%m/%d")
                    for ts, _ in chart_data
                ]
                points = [round(value, 2) for _, value in chart_data]

                return {
                    "price_str": f"{current_price:.2f}",
                    "ma20_str": f"{ma20:.2f}" if ma20 else "N/A",
                    "ma60_str": f"{ma60:.2f}" if ma60 else "N/A",
                    "ma250_str": f"{ma250:.2f}" if ma250 else "N/A",
                    "ma1250_str": f"{ma1250:.2f}" if ma1250 else "N/A",
                    "broken_20": current_price < ma20 if ma20 else False,
                    "broken_60": current_price < ma60 if ma60 else False,
                    "broken_250": current_price < ma250 if ma250 else False,
                    "broken_1250": current_price < ma1250 if ma1250 else False,
                    "chart_labels": labels,
                    "chart_points": points,
                }
    except Exception as exc:
        print(f"Error fetching S&P 500 historical data: {exc}")
    return None


def cached_sp500_historical(ttl=_TTL_NORMAL):
    key = ("sp500_historical",)
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl) and entry["data"] is not None:
        return entry["data"]
    data = fetch_sp500_historical()
    if data is not None:
        _set_cache(key, {"ts": now, "data": data})
        return data
    if entry and entry["data"] is not None:
        return entry["data"]
    return None


def _parse_multpl_pe(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        rows = re.findall(
            r"<tr[^>]*>\s*<td[^>]*>([^<]+)</td>\s*<td[^>]*>([^<]+)</td>\s*</tr>",
            response.text,
        )
        results = []
        for date_text, value_text in rows:
            normalized_value = value_text.strip().replace(",", "")
            normalized_value = re.sub(r"&#[^;]+;", "", normalized_value)
            number_match = re.search(r"(-?\d+(?:\.\d+)?)", normalized_value)
            if not number_match:
                continue
            try:
                results.append((date_text.strip(), float(number_match.group(1))))
            except ValueError:
                continue
        return results
    except Exception as exc:
        print(f"Error parsing multpl data: {exc}")
        return []


def fetch_sp500_trailing_pe():
    default_payload = {
        "value": None,
        "value_str": "N/A",
        "prev_value": None,
        "prev_value_str": "N/A",
        "delta": None,
        "delta_str": "N/A",
        "date": "N/A",
        "valuation": "N/A",
        "source_name": "Multpl.com / S&P 500 Trailing P/E",
        "source_url": SP500_TRAILING_SOURCE_URL,
    }
    try:
        rows = _parse_multpl_pe(SP500_TRAILING_URL)
        if len(rows) < 2:
            return default_payload

        date_text, latest_value = rows[0]
        _, previous_value = rows[1]
        delta_value = latest_value - previous_value
        return {
            "value": latest_value,
            "value_str": f"{latest_value:.2f}",
            "prev_value": previous_value,
            "prev_value_str": f"{previous_value:.2f}",
            "delta": delta_value,
            "delta_str": f"{delta_value:+.2f}",
            "date": date_text,
            "valuation": sp500_trailing_pe_valuation(latest_value),
            "source_name": "Multpl.com / S&P 500 Trailing P/E",
            "source_url": SP500_TRAILING_SOURCE_URL,
        }
    except Exception as exc:
        print(f"Error fetching S&P 500 trailing PE: {exc}")
        return default_payload


def cached_sp500_trailing_pe(ttl=_TTL_NORMAL):
    key = ("sp500_trailing_pe",)
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl):
        return entry["data"]
    data = fetch_sp500_trailing_pe()
    _set_cache(key, {"ts": now, "data": data})
    return data


def fetch_shiller_pe():
    default_payload = {
        "value": None,
        "value_str": "N/A",
        "prev_value": None,
        "prev_value_str": "N/A",
        "delta": None,
        "delta_str": "N/A",
        "date": "N/A",
        "valuation": "N/A",
        "source_name": "Multpl.com / Shiller P/E",
        "source_url": SP500_SHILLER_URL,
    }
    try:
        rows = _parse_multpl_pe(SP500_SHILLER_URL)
        if len(rows) < 2:
            return default_payload

        date_text, latest_value = rows[0]
        _, previous_value = rows[1]
        delta_value = latest_value - previous_value
        return {
            "value": latest_value,
            "value_str": f"{latest_value:.2f}",
            "prev_value": previous_value,
            "prev_value_str": f"{previous_value:.2f}",
            "delta": delta_value,
            "delta_str": f"{delta_value:+.2f}",
            "date": date_text,
            "valuation": shiller_pe_valuation(latest_value),
            "source_name": "Multpl.com / Shiller P/E",
            "source_url": SP500_SHILLER_URL,
        }
    except Exception as exc:
        print(f"Error fetching Shiller PE: {exc}")
        return default_payload


def cached_shiller_pe(ttl=_TTL_NORMAL):
    key = ("shiller_pe",)
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl):
        return entry["data"]
    data = fetch_shiller_pe()
    _set_cache(key, {"ts": now, "data": data})
    return data


def _parse_finra_margin_rows(response_text):
    rows = re.findall(
        r"([A-Z][a-z]{2}-\d{2})\s+([\d,]+)\s+[\d,]+\s+[\d,]+",
        response_text,
    )
    parsed_rows = []
    seen_months = set()
    for month, value_text in rows:
        if month in seen_months:
            continue
        try:
            parsed_rows.append((month, int(value_text.replace(",", ""))))
            seen_months.add(month)
        except ValueError:
            continue
    return sorted(
        parsed_rows,
        key=lambda item: datetime.strptime(item[0], "%b-%y"),
        reverse=True,
    )


def _extract_finra_download_url(response_text):
    match = re.search(r'href="([^"]+debitbalances\.xlsx[^"]*)"', response_text, flags=re.IGNORECASE)
    if not match:
        return FINRA_MARGIN_DOWNLOAD_URL

    download_url = match.group(1)
    if download_url.startswith("http://") or download_url.startswith("https://"):
        return download_url
    return f"https://www.finra.org{download_url}"


def _read_xlsx_shared_strings(workbook_archive):
    try:
        shared_strings_xml = workbook_archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ElementTree.fromstring(shared_strings_xml)
    values = []
    for string_item in root.findall("main:si", namespace):
        text_fragments = [
            text_node.text or ""
            for text_node in string_item.findall(".//main:t", namespace)
        ]
        values.append("".join(text_fragments))
    return values


def _parse_xlsx_cell_value(cell, shared_strings, namespace):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(
            text_node.text or ""
            for text_node in cell.findall(".//main:t", namespace)
        )

    value_node = cell.find("main:v", namespace)
    if value_node is None or value_node.text is None:
        return ""

    raw_value = value_node.text.strip()
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (IndexError, ValueError):
            return ""
    return raw_value


def _iter_xlsx_row_values(workbook_bytes):
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(BytesIO(workbook_bytes)) as workbook_archive:
        shared_strings = _read_xlsx_shared_strings(workbook_archive)
        worksheet_paths = sorted(
            path_name
            for path_name in workbook_archive.namelist()
            if path_name.startswith("xl/worksheets/") and path_name.endswith(".xml")
        )
        for worksheet_path in worksheet_paths:
            worksheet_root = ElementTree.fromstring(workbook_archive.read(worksheet_path))
            for row in worksheet_root.findall(".//main:sheetData/main:row", namespace):
                yield [
                    _parse_xlsx_cell_value(cell, shared_strings, namespace)
                    for cell in row.findall("main:c", namespace)
                ]


def _parse_finra_margin_rows_from_xlsx_bytes(workbook_bytes):
    parsed_rows = []
    seen_months = set()

    try:
        row_values_iter = _iter_xlsx_row_values(workbook_bytes)
    except (ElementTree.ParseError, KeyError, zipfile.BadZipFile):
        return []

    for row_values in row_values_iter:
        normalized_values = [str(value).strip() for value in row_values if str(value).strip()]
        month = next(
            (
                value
                for value in normalized_values
                if re.fullmatch(r"[A-Z][a-z]{2}-\d{2}", value)
            ),
            None,
        )
        if not month or month in seen_months:
            continue

        numeric_values = []
        for value in normalized_values:
            cleaned_value = value.replace(",", "")
            if re.fullmatch(r"\d+(?:\.\d+)?", cleaned_value):
                numeric_values.append(cleaned_value)

        if not numeric_values:
            continue

        try:
            parsed_rows.append((month, int(float(numeric_values[0]))))
            seen_months.add(month)
        except ValueError:
            continue

    return sorted(
        parsed_rows,
        key=lambda item: datetime.strptime(item[0], "%b-%y"),
        reverse=True,
    )


def _build_finra_margin_payload(rows, source_status="live"):
    if len(rows) < 2:
        return None

    latest_month, latest_value = rows[0]
    previous_month, previous_value = rows[1]
    month_over_month = (
        ((latest_value - previous_value) / previous_value * 100)
        if previous_value
        else None
    )
    return {
        "latest_month": latest_month,
        "latest_value": latest_value,
        "value_str": f"{latest_value:,}",
        "previous_month": previous_month,
        "previous_value": previous_value,
        "mom_pct": month_over_month,
        "mom_str": f"{month_over_month:+.2f}%" if month_over_month is not None else "N/A",
        "source_status": source_status,
    }


def fetch_finra_margin():
    download_url = FINRA_MARGIN_DOWNLOAD_URL

    try:
        response = requests.get(
            FINRA_MARGIN_URL,
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        download_url = _extract_finra_download_url(response.text)
        data = _parse_finra_margin_rows(response.text)
        payload = _build_finra_margin_payload(data)
        if payload:
            return payload
    except Exception as exc:
        print(f"Error fetching FINRA margin HTML: {exc}")

    try:
        response = requests.get(
            download_url,
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        data = _parse_finra_margin_rows_from_xlsx_bytes(response.content)
        payload = _build_finra_margin_payload(data, source_status="download")
        if payload:
            return payload
    except Exception as exc:
        print(f"Error fetching FINRA margin download, using fallback: {exc}")

    return _build_finra_margin_payload(FINRA_MARGIN_FALLBACK_ROWS, source_status="fallback")


def cached_finra_margin(ttl=_TTL_NORMAL):
    key = ("finra_margin",)
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl):
        return entry["data"]
    data = fetch_finra_margin()
    _set_cache(key, {"ts": now, "data": data})
    return data


def fetch_cnn_fear_greed(days=370):
    now_local = datetime.now(_timezone())
    start_date = (now_local - timedelta(days=days)).strftime("%Y-%m-%d")
    url = f"{CNN_FNG_BASE_URL}{start_date}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        current_block = data.get("fear_and_greed", {})
        historical = data.get("fear_and_greed_historical", {}).get("data", [])

        chart_points = []
        for point in historical:
            timestamp = point.get("x")
            value = point.get("y")
            if timestamp is None or value is None:
                continue
            dt = datetime.fromtimestamp(int(timestamp) / 1000, tz=_timezone())
            chart_points.append({"dt": dt, "date": dt.strftime("%m/%d"), "value": float(value)})

        current_value = current_block.get("score")
        if current_value is None and chart_points:
            current_value = chart_points[-1]["value"]

        previous_close = current_block.get("previous_close")
        if previous_close is None and len(chart_points) >= 2:
            previous_close = chart_points[-2]["value"]

        week_block = _format_fg_block(data.get("fear_and_greed_week_ago", {}))
        month_block = _format_fg_block(data.get("fear_and_greed_month_ago", {}))
        year_block = _format_fg_block(data.get("fear_and_greed_year_ago", {}))

        if week_block["score"] is None:
            week_score = _nearest_historical_value(chart_points, now_local - timedelta(days=7))
            week_block = {
                "score": week_score,
                "score_str": f"{week_score:.0f}" if week_score is not None else "N/A",
                "rating": fear_greed_label(week_score) if week_score is not None else "N/A",
            }
        if month_block["score"] is None:
            month_score = _nearest_historical_value(chart_points, now_local - timedelta(days=30))
            month_block = {
                "score": month_score,
                "score_str": f"{month_score:.0f}" if month_score is not None else "N/A",
                "rating": fear_greed_label(month_score) if month_score is not None else "N/A",
            }
        if year_block["score"] is None:
            year_score = _nearest_historical_value(chart_points, now_local - timedelta(days=365))
            year_block = {
                "score": year_score,
                "score_str": f"{year_score:.0f}" if year_score is not None else "N/A",
                "rating": fear_greed_label(year_score) if year_score is not None else "N/A",
            }

        recent_chart_points = chart_points[-90:]
        vix_data = data.get("market_volatility_vix", {}).get("data", [])
        latest_vix = vix_data[-1].get("y") if vix_data else None
        put_call_data = data.get("put_call_options", {}).get("data", [])
        latest_pcr = put_call_data[-1].get("y") if put_call_data else None

        return {
            "score": float(current_value) if current_value is not None else None,
            "score_str": f"{float(current_value):.0f}" if current_value is not None else "N/A",
            "rating": fear_greed_label(float(current_value)) if current_value is not None else "N/A",
            "previous_close": float(previous_close) if previous_close is not None else None,
            "previous_close_str": f"{float(previous_close):.0f}" if previous_close is not None else "N/A",
            "previous_close_rating": fear_greed_label(previous_close) if previous_close is not None else "N/A",
            "week_ago": week_block,
            "month_ago": month_block,
            "year_ago": year_block,
            "chart_labels": [point["date"] for point in recent_chart_points],
            "chart_data": [point["value"] for point in recent_chart_points],
            "vix": latest_vix,
            "vix_str": f"{latest_vix:.2f}" if latest_vix is not None else "N/A",
            "pcr": latest_pcr,
            "pcr_str": f"{latest_pcr:.2f}" if latest_pcr is not None else "N/A",
        }
    except Exception as exc:
        print(f"Error fetching CNN Fear & Greed Index: {exc}")
        return {
            "score": None,
            "score_str": "N/A",
            "rating": "N/A",
            "previous_close": None,
            "previous_close_str": "N/A",
            "previous_close_rating": "N/A",
            "week_ago": {"score": None, "score_str": "N/A", "rating": "N/A"},
            "month_ago": {"score": None, "score_str": "N/A", "rating": "N/A"},
            "year_ago": {"score": None, "score_str": "N/A", "rating": "N/A"},
            "chart_labels": [],
            "chart_data": [],
            "vix": None,
            "vix_str": "N/A",
            "pcr": None,
            "pcr_str": "N/A",
        }


def cached_fear_greed(ttl=_TTL_NORMAL):
    key = ("cnn_fear_greed",)
    entry = _get_cache(key)
    now = _now()
    if entry and (now - entry["ts"] < ttl):
        return entry["data"]
    data = fetch_cnn_fear_greed(days=90)
    _set_cache(key, {"ts": now, "data": data})
    return data
