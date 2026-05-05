import json
import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Union

from .config import (
    HOLDINGS_JSON_PATH,
    LOCAL_MARKET_PRICES_DIR,
    LOCAL_TRANSACTIONS_JSON_PATH,
    PORTFOLIO_METRICS_JSON_PATH,
    PORTFOLIO_SNAPSHOTS_JSON_PATH,
)
from .holdings import write_holdings_data
from .metrics import write_portfolio_metrics

BASE_CURRENCY = "USD"
BUY = "BUY"
SELL = "SELL"
DEPOSIT = "DEPOSIT"
WITHDRAWAL = "WITHDRAWAL"
FEE = "FEE"
INTEREST = "INTEREST"
TRADE_TYPES = {BUY, SELL}
CASH_TYPES = {DEPOSIT, WITHDRAWAL, FEE, INTEREST}
SUPPORTED_TRANSACTION_TYPES = (BUY, SELL, DEPOSIT, WITHDRAWAL, FEE, INTEREST)
FIRSTRADE_CSV_HEADERS = (
    "Symbol",
    "Quantity",
    "Price",
    "Action",
    "Description",
    "TradeDate",
    "SettledDate",
    "Interest",
    "Amount",
    "Commission",
    "Fee",
    "CUSIP",
    "RecordType",
)
EPSILON = 1e-9


class TransactionValidationError(ValueError):
    """Raised when canonical transaction data cannot be processed safely."""


def _parse_iso_date(raw_value: object, field_name: str) -> date:
    value = str("" if raw_value is None else raw_value).strip()
    if not value:
        raise TransactionValidationError(f"'{field_name}' cannot be empty.")

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise TransactionValidationError(
            f"'{field_name}' must use YYYY-MM-DD format."
        ) from exc


def _parse_number(raw_value: object, field_name: str) -> float:
    value = (
        str("" if raw_value is None else raw_value)
        .strip()
        .replace(",", "")
        .replace("$", "")
    )
    if not value:
        raise TransactionValidationError(f"'{field_name}' cannot be empty.")

    try:
        return float(value)
    except ValueError as exc:
        raise TransactionValidationError(f"'{field_name}' must be numeric.") from exc


def _parse_positive_number(raw_value: object, field_name: str) -> float:
    value = _parse_number(raw_value, field_name)
    if value <= 0:
        raise TransactionValidationError(f"'{field_name}' must be greater than 0.")
    return value


def _parse_non_negative_number(raw_value: object, field_name: str) -> float:
    value = _parse_number(raw_value, field_name)
    if value < 0:
        raise TransactionValidationError(f"'{field_name}' cannot be negative.")
    return value


def _required_text(raw_transaction: dict, field_name: str, row_number: int) -> str:
    value = str(raw_transaction.get(field_name, "")).strip()
    if not value:
        raise TransactionValidationError(
            f"Transaction {row_number}: '{field_name}' cannot be empty."
        )
    return value


def normalize_transaction(raw_transaction: dict, row_number: int) -> dict:
    """Normalize one canonical transaction record."""
    if not isinstance(raw_transaction, dict):
        raise TransactionValidationError(
            f"Transaction {row_number}: each transaction must be an object."
        )

    transaction_type = _required_text(raw_transaction, "type", row_number).upper()
    if transaction_type not in SUPPORTED_TRANSACTION_TYPES:
        raise TransactionValidationError(
            "Transaction "
            f"{row_number}: unsupported transaction type '{transaction_type}'."
        )

    currency = _required_text(raw_transaction, "currency", row_number).upper()
    if currency != BASE_CURRENCY:
        raise TransactionValidationError(
            f"Transaction {row_number}: only {BASE_CURRENCY} transactions "
            "are supported."
        )

    transaction = {
        "id": _required_text(raw_transaction, "id", row_number),
        "date": _parse_iso_date(raw_transaction.get("date"), "date").isoformat(),
        "account": _required_text(raw_transaction, "account", row_number),
        "type": transaction_type,
        "currency": currency,
    }

    if transaction_type in TRADE_TYPES:
        symbol = _required_text(raw_transaction, "symbol", row_number).upper()
        transaction.update(
            {
                "symbol": symbol,
                "quantity": _parse_positive_number(
                    raw_transaction.get("quantity"), "quantity"
                ),
                "price": _parse_positive_number(raw_transaction.get("price"), "price"),
                "fee": _parse_non_negative_number(
                    raw_transaction.get("fee", 0), "fee"
                ),
            }
        )
        return transaction

    transaction["amount"] = _parse_positive_number(
        raw_transaction.get("amount"), "amount"
    )
    return transaction


def validate_transactions_data(raw_transactions: object) -> list[dict]:
    """Validate and normalize a list of canonical transaction records."""
    if not isinstance(raw_transactions, list):
        raise TransactionValidationError("Transactions data must contain a list.")

    transactions = []
    seen_ids = set()
    for index, entry in enumerate(raw_transactions, start=1):
        transaction = normalize_transaction(entry, index)
        if transaction["id"] in seen_ids:
            raise TransactionValidationError(
                f"Transaction {index}: duplicate transaction id '{transaction['id']}'."
            )
        seen_ids.add(transaction["id"])
        transactions.append((index, transaction))

    transactions.sort(key=lambda item: (item[1]["date"], item[0]))
    return [transaction for _, transaction in transactions]


def load_transactions(json_path: Path = LOCAL_TRANSACTIONS_JSON_PATH) -> list[dict]:
    """Load local canonical transactions from JSON."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TransactionValidationError(
            f"Transaction file '{json_path}' cannot be read."
        ) from exc
    except json.JSONDecodeError as exc:
        raise TransactionValidationError(
            f"Invalid JSON in transaction file '{json_path}'."
        ) from exc
    return validate_transactions_data(data)


def load_price_history(price_history_dir: Path = LOCAL_MARKET_PRICES_DIR) -> dict:
    """Load optional local market price cache files from private storage."""
    if not price_history_dir.exists():
        return {}

    combined_path = price_history_dir / "prices.json"
    if combined_path.exists():
        try:
            payload = json.loads(combined_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TransactionValidationError(
                f"Invalid JSON in price history file '{combined_path}'."
            ) from exc
        return normalize_price_history(payload)

    payload = {}
    for price_path in sorted(price_history_dir.glob("*.json")):
        symbol = price_path.stem.upper()
        try:
            payload[symbol] = json.loads(price_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TransactionValidationError(
                f"Invalid JSON in price history file '{price_path}'."
            ) from exc
    return normalize_price_history(payload)


def write_price_history(
    price_history: object,
    price_history_dir: Path = LOCAL_MARKET_PRICES_DIR,
) -> dict:
    """Persist private market price history used by snapshot generation."""
    normalized = normalize_price_history(price_history)
    serializable = {
        symbol: {price_date.isoformat(): price for price_date, price in prices.items()}
        for symbol, prices in normalized.items()
    }
    price_history_dir.mkdir(parents=True, exist_ok=True)
    price_history_path = price_history_dir / "prices.json"
    price_history_path.write_text(
        json.dumps(serializable, indent=2) + "\n",
        encoding="utf-8",
    )
    return normalized


def merge_price_histories(*price_histories: object) -> dict:
    """Merge price histories, with later histories replacing duplicate dates."""
    merged = {}
    for price_history in price_histories:
        normalized = normalize_price_history(price_history or {})
        for symbol, prices in normalized.items():
            merged.setdefault(symbol, {}).update(prices)
    return {
        symbol: dict(sorted(prices.items()))
        for symbol, prices in sorted(merged.items())
    }


def normalize_price_history(raw_price_history: object) -> dict:
    """Normalize a symbol keyed date-to-price mapping."""
    if raw_price_history is None:
        return {}
    if not isinstance(raw_price_history, dict):
        raise TransactionValidationError("Price history must be an object.")

    normalized = {}
    for raw_symbol, raw_prices in raw_price_history.items():
        symbol = str(raw_symbol).strip().upper()
        if not symbol:
            raise TransactionValidationError("Price history symbol cannot be empty.")
        if not isinstance(raw_prices, dict):
            raise TransactionValidationError(
                f"Price history for {symbol} must be a date-to-price object."
            )

        prices = {}
        for raw_date, raw_price in raw_prices.items():
            price_date = _parse_iso_date(raw_date, f"{symbol} price date")
            prices[price_date] = _parse_positive_number(
                raw_price, f"{symbol} price"
            )
        normalized[symbol] = dict(sorted(prices.items()))
    return normalized


def _empty_position() -> dict:
    return {"shares": 0.0, "total_cost": 0.0, "last_price": None}


def _apply_transaction(transaction: dict, state: dict) -> None:
    transaction_type = transaction["type"]
    transaction_date = _parse_iso_date(transaction["date"], "date")

    if transaction_type == DEPOSIT:
        state["cash"] += transaction["amount"]
        state["external_flows"][transaction_date] = (
            state["external_flows"].get(transaction_date, 0.0) + transaction["amount"]
        )
        return

    if transaction_type == WITHDRAWAL:
        state["cash"] -= transaction["amount"]
        state["external_flows"][transaction_date] = (
            state["external_flows"].get(transaction_date, 0.0) - transaction["amount"]
        )
        return

    if transaction_type == FEE:
        state["cash"] -= transaction["amount"]
        return

    if transaction_type == INTEREST:
        state["cash"] += transaction["amount"]
        return

    symbol = transaction["symbol"]
    quantity = transaction["quantity"]
    price = transaction["price"]
    fee = transaction["fee"]
    position = state["positions"].setdefault(symbol, _empty_position())
    position["last_price"] = price

    if transaction_type == BUY:
        state["cash"] -= (quantity * price) + fee
        position["shares"] += quantity
        position["total_cost"] += (quantity * price) + fee
        return

    if position["shares"] + EPSILON < quantity:
        raise TransactionValidationError(
            f"Transaction '{transaction['id']}': sell quantity exceeds current "
            f"shares for {symbol}."
        )

    average_cost = (
        position["total_cost"] / position["shares"]
        if position["shares"]
        else 0.0
    )
    realized_cost_basis = average_cost * quantity
    net_proceeds = (quantity * price) - fee
    state["cash"] += net_proceeds
    state["realized_pl"] += net_proceeds - realized_cost_basis
    state["realized_cost_basis"] += realized_cost_basis
    position["shares"] -= quantity
    position["total_cost"] -= realized_cost_basis

    if abs(position["shares"]) < EPSILON:
        position["shares"] = 0.0
        position["total_cost"] = 0.0


def _price_for_date(
    symbol: str,
    snapshot_date: date,
    price_history: dict,
    position: dict,
) -> Optional[float]:
    prices = price_history.get(symbol, {})
    if prices:
        available_dates = [
            price_date for price_date in prices if price_date <= snapshot_date
        ]
        if available_dates:
            return prices[max(available_dates)]
    return position.get("last_price")


def _holdings_from_positions(positions: dict) -> list[dict]:
    holdings = []
    for symbol, position in sorted(positions.items()):
        shares = position["shares"]
        if shares <= EPSILON:
            continue
        holdings.append(
            {
                "symbol": symbol,
                "shares": shares,
                "cost_basis": position["total_cost"] / shares,
            }
        )
    return holdings


def _snapshot_from_state(
    snapshot_date: date,
    state: dict,
    price_history: dict,
) -> dict:
    holdings_market_value = 0.0
    invested_cost_basis = 0.0

    for symbol, position in state["positions"].items():
        shares = position["shares"]
        if shares <= EPSILON:
            continue
        price = _price_for_date(symbol, snapshot_date, price_history, position)
        if price is not None:
            holdings_market_value += shares * price
        invested_cost_basis += position["total_cost"]

    total_portfolio_value = holdings_market_value + state["cash"]
    unrealized_pl = holdings_market_value - invested_cost_basis
    return {
        "date": snapshot_date.isoformat(),
        "holdings_market_value": holdings_market_value,
        "portfolio_cash": state["cash"],
        "total_portfolio_value": total_portfolio_value,
        "invested_cost_basis": invested_cost_basis,
        "unrealized_pl": unrealized_pl,
        "realized_pl": state["realized_pl"],
        "net_external_cash_flow": state["external_flows"].get(snapshot_date, 0.0),
    }


def _date_range(start_date: date, end_date: date):
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def build_portfolio_history(
    transactions: list[dict],
    price_history: Optional[dict] = None,
    end_date: Optional[Union[str, date]] = None,
) -> dict:
    """Build public holdings, metrics, and daily snapshots from transactions."""
    normalized_transactions = validate_transactions_data(transactions)
    normalized_price_history = normalize_price_history(price_history or {})

    if not normalized_transactions:
        return {
            "holdings": [],
            "metrics": _build_metrics([], 0.0, 0.0),
            "snapshots": [],
        }

    start_date = _parse_iso_date(normalized_transactions[0]["date"], "date")
    resolved_end_date = (
        _parse_iso_date(end_date, "end_date")
        if end_date is not None and not isinstance(end_date, date)
        else end_date
    )
    if resolved_end_date is None:
        resolved_end_date = _parse_iso_date(
            normalized_transactions[-1]["date"], "date"
        )
    if resolved_end_date < start_date:
        raise TransactionValidationError(
            "'end_date' cannot be before the first transaction date."
        )

    transactions_by_date = {}
    for transaction in normalized_transactions:
        transaction_date = _parse_iso_date(transaction["date"], "date")
        transactions_by_date.setdefault(transaction_date, []).append(transaction)

    state = {
        "cash": 0.0,
        "positions": {},
        "realized_pl": 0.0,
        "realized_cost_basis": 0.0,
        "external_flows": {},
    }
    snapshots = []

    for snapshot_date in _date_range(start_date, resolved_end_date):
        for transaction in transactions_by_date.get(snapshot_date, []):
            _apply_transaction(transaction, state)
        snapshots.append(
            _snapshot_from_state(snapshot_date, state, normalized_price_history)
        )

    holdings = _holdings_from_positions(state["positions"])
    metrics = _build_metrics(
        snapshots,
        state["realized_pl"],
        state["realized_cost_basis"],
        normalized_price_history,
    )
    return {
        "holdings": holdings,
        "metrics": metrics,
        "snapshots": snapshots,
    }


def _parse_firstrade_amount(raw_value: object, field_name: str) -> float:
    return _parse_number(raw_value, field_name)


def convert_firstrade_csv_to_transactions(source_path: Path) -> list[dict]:
    """Convert a Firstrade account history CSV into canonical transactions."""
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise TransactionValidationError("Firstrade CSV is missing a header row.")

        normalized_headers = tuple(header.strip() for header in reader.fieldnames)
        if normalized_headers != FIRSTRADE_CSV_HEADERS:
            raise TransactionValidationError(
                "Firstrade CSV headers do not match the supported export format."
            )

        transactions = []
        for row_number, row in enumerate(reader, start=2):
            record_type = str(row.get("RecordType", "")).strip()
            action = str(row.get("Action", "")).strip().upper()
            trade_date = _parse_iso_date(row.get("TradeDate"), "TradeDate").isoformat()

            if record_type == "Financial":
                amount = _parse_firstrade_amount(
                    row.get("Amount"), f"Row {row_number} amount"
                )
                if action == "OTHER" and amount:
                    transactions.append(
                        {
                            "id": f"firstrade-{trade_date}-{row_number}-deposit",
                            "date": trade_date,
                            "account": "firstrade",
                            "type": DEPOSIT if amount > 0 else WITHDRAWAL,
                            "currency": BASE_CURRENCY,
                            "amount": abs(amount),
                        }
                    )
                    continue
                if action == "INTEREST" and amount:
                    transactions.append(
                        {
                            "id": f"firstrade-{trade_date}-{row_number}-interest",
                            "date": trade_date,
                            "account": "firstrade",
                            "type": INTEREST,
                            "currency": BASE_CURRENCY,
                            "amount": abs(amount),
                        }
                    )
                    continue
                continue

            if record_type != "Trade":
                continue

            if action not in {BUY, SELL}:
                raise TransactionValidationError(
                    f"Row {row_number}: unsupported Firstrade trade action '{action}'."
                )

            symbol = str(row.get("Symbol", "")).strip().upper()
            if not symbol:
                raise TransactionValidationError(
                    f"Row {row_number}: Firstrade trade row is missing a symbol."
                )

            raw_quantity = _parse_number(
                row.get("Quantity"), f"Row {row_number} quantity"
            )
            quantity = abs(raw_quantity)
            if quantity <= 0:
                raise TransactionValidationError(
                    f"Row {row_number}: trade quantity must be positive."
                )

            price = _parse_positive_number(row.get("Price"), f"Row {row_number} price")
            commission = _parse_non_negative_number(
                row.get("Commission", 0) or 0, f"Row {row_number} commission"
            )
            fee = _parse_non_negative_number(
                row.get("Fee", 0) or 0, f"Row {row_number} fee"
            )

            transactions.append(
                {
                    "id": (
                        f"firstrade-{trade_date}-{row_number}-"
                        f"{symbol.lower()}-{action.lower()}"
                    ),
                    "date": trade_date,
                    "account": "firstrade",
                    "type": action,
                    "currency": BASE_CURRENCY,
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": price,
                    "fee": commission + fee,
                }
            )

    return validate_transactions_data(transactions)


def _build_metrics(
    snapshots: list[dict],
    realized_pl: float,
    realized_cost_basis: float,
    price_history: Optional[dict] = None,
) -> dict:
    realized_return_pct = (
        (realized_pl / realized_cost_basis) * 100
        if realized_cost_basis
        else None
    )
    twr = _calculate_twr(snapshots)
    irr = _calculate_irr(snapshots)
    daily_returns = _portfolio_daily_returns(snapshots)
    has_external_price_history = _has_external_price_history(price_history or {})
    benchmark_returns = _benchmark_daily_returns(snapshots, price_history or {})
    sharpe = _calculate_sharpe(daily_returns) if has_external_price_history else None
    beta = _calculate_beta(daily_returns, benchmark_returns)
    sp500_ytd_ret = _compound_returns(benchmark_returns)
    alpha = _calculate_alpha(
        twr=twr if has_external_price_history else None,
        benchmark_return=sp500_ytd_ret,
        beta=beta,
        periods=len(daily_returns),
    )

    return {
        "realized_pl": realized_pl,
        "realized_return_pct": realized_return_pct,
        "twr": twr,
        "irr": irr,
        "cagr": _annualize_return(twr, snapshots),
        "current_drawdown": _calculate_current_drawdown(snapshots),
        "max_drawdown": _calculate_max_drawdown(snapshots),
        "sharpe": sharpe,
        "beta": beta,
        "alpha": alpha,
        "sp500_ytd_ret": sp500_ytd_ret,
    }


def _calculate_twr(snapshots: list[dict]) -> Optional[float]:
    if len(snapshots) < 2:
        return None

    cumulative_return = 1.0
    previous_value = snapshots[0]["total_portfolio_value"]
    has_return = False
    for snapshot in snapshots[1:]:
        if previous_value:
            period_return = (
                snapshot["total_portfolio_value"]
                - snapshot["net_external_cash_flow"]
                - previous_value
            ) / previous_value
            cumulative_return *= 1 + period_return
            has_return = True
        previous_value = snapshot["total_portfolio_value"]

    if not has_return:
        return None
    return (cumulative_return - 1) * 100


def _portfolio_daily_returns(snapshots: list[dict]) -> list[float]:
    returns = []
    if len(snapshots) < 2:
        return returns

    previous_value = snapshots[0]["total_portfolio_value"]
    for snapshot in snapshots[1:]:
        if previous_value:
            period_return = (
                snapshot["total_portfolio_value"]
                - snapshot["net_external_cash_flow"]
                - previous_value
            ) / previous_value
            returns.append(period_return)
        previous_value = snapshot["total_portfolio_value"]
    return returns


def _has_external_price_history(price_history: dict) -> bool:
    return any(symbol != "^GSPC" and bool(prices) for symbol, prices in price_history.items())


def _benchmark_daily_returns(snapshots: list[dict], price_history: dict) -> list[float]:
    benchmark_prices = price_history.get("^GSPC") or price_history.get("SPY") or {}
    if len(snapshots) < 2 or not benchmark_prices:
        return []

    returns = []
    previous_price = None
    for snapshot in snapshots:
        snapshot_date = _parse_iso_date(snapshot["date"], "snapshot date")
        available_dates = [
            price_date for price_date in benchmark_prices if price_date <= snapshot_date
        ]
        if not available_dates:
            continue
        price = benchmark_prices[max(available_dates)]
        if previous_price:
            returns.append((price - previous_price) / previous_price)
        previous_price = price
    return returns


def _compound_returns(returns: list[float]) -> Optional[float]:
    if not returns:
        return None
    cumulative_return = 1.0
    for value in returns:
        cumulative_return *= 1 + value
    return (cumulative_return - 1) * 100


def _calculate_sharpe(returns: list[float]) -> Optional[float]:
    if len(returns) < 2:
        return None
    average_return = sum(returns) / len(returns)
    variance = sum((value - average_return) ** 2 for value in returns) / (len(returns) - 1)
    standard_deviation = variance ** 0.5
    if not standard_deviation:
        return None
    daily_risk_free = 0.04 / 252
    excess_average_return = average_return - daily_risk_free
    return (252 ** 0.5) * excess_average_return / standard_deviation


def _calculate_beta(
    portfolio_returns: list[float], benchmark_returns: list[float]
) -> Optional[float]:
    aligned_length = min(len(portfolio_returns), len(benchmark_returns))
    if aligned_length < 2:
        return None

    portfolio_values = portfolio_returns[-aligned_length:]
    benchmark_values = benchmark_returns[-aligned_length:]
    benchmark_average = sum(benchmark_values) / aligned_length
    portfolio_average = sum(portfolio_values) / aligned_length
    benchmark_variance = sum(
        (value - benchmark_average) ** 2 for value in benchmark_values
    ) / (aligned_length - 1)
    if not benchmark_variance:
        return None
    covariance = sum(
        (portfolio_values[index] - portfolio_average)
        * (benchmark_values[index] - benchmark_average)
        for index in range(aligned_length)
    ) / (aligned_length - 1)
    return covariance / benchmark_variance


def _calculate_alpha(
    twr: Optional[float],
    benchmark_return: Optional[float],
    beta: Optional[float],
    periods: int,
) -> Optional[float]:
    if twr is None or benchmark_return is None or beta is None:
        return None
    risk_free_return = (0.04 / 252) * periods * 100
    return twr - (
        risk_free_return + beta * (benchmark_return - risk_free_return)
    )


def _calculate_irr(snapshots: list[dict]) -> Optional[float]:
    if not snapshots:
        return None

    cash_flows = []
    for snapshot in snapshots:
        flow = snapshot["net_external_cash_flow"]
        if flow:
            cash_flows.append((snapshot["date"], -flow))

    ending_value = snapshots[-1]["total_portfolio_value"]
    if ending_value:
        cash_flows.append((snapshots[-1]["date"], ending_value))

    has_positive_flow = any(amount > 0 for _, amount in cash_flows)
    has_negative_flow = any(amount < 0 for _, amount in cash_flows)
    if not cash_flows or not has_positive_flow or not has_negative_flow:
        return None

    start_date = _parse_iso_date(cash_flows[0][0], "cash flow date")

    def net_present_value(rate):
        total = 0.0
        for flow_date, amount in cash_flows:
            days = (_parse_iso_date(flow_date, "cash flow date") - start_date).days
            total += amount / ((1 + rate) ** (days / 365))
        return total

    low = -0.9999
    high = 10.0
    low_value = net_present_value(low)
    high_value = net_present_value(high)
    while low_value * high_value > 0 and high < 1_000_000:
        high *= 10
        high_value = net_present_value(high)

    if low_value * high_value > 0:
        return None

    for _ in range(100):
        midpoint = (low + high) / 2
        midpoint_value = net_present_value(midpoint)
        if abs(midpoint_value) < 1e-7:
            return midpoint * 100
        if low_value * midpoint_value <= 0:
            high = midpoint
            high_value = midpoint_value
        else:
            low = midpoint
            low_value = midpoint_value

    return ((low + high) / 2) * 100


def _annualize_return(
    total_return_pct: Optional[float], snapshots: list[dict]
) -> Optional[float]:
    if total_return_pct is None or len(snapshots) < 2:
        return None

    start_date = _parse_iso_date(snapshots[0]["date"], "snapshot date")
    end_date = _parse_iso_date(snapshots[-1]["date"], "snapshot date")
    days = (end_date - start_date).days
    if days <= 0:
        return None

    total_return_ratio = 1 + (total_return_pct / 100)
    if total_return_ratio <= 0:
        return None
    return ((total_return_ratio ** (365 / days)) - 1) * 100


def _drawdown_values(snapshots: list[dict]) -> list[float]:
    values = []
    high_watermark = None
    for snapshot in snapshots:
        total_value = snapshot["total_portfolio_value"]
        if high_watermark is None or total_value > high_watermark:
            high_watermark = total_value
        if high_watermark:
            values.append(((total_value - high_watermark) / high_watermark) * 100)
    return values


def _calculate_current_drawdown(snapshots: list[dict]) -> Optional[float]:
    values = _drawdown_values(snapshots)
    return values[-1] if values else None


def _calculate_max_drawdown(snapshots: list[dict]) -> Optional[float]:
    values = _drawdown_values(snapshots)
    return min(values) if values else None


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def generate_public_portfolio_data(
    transactions_path: Path = LOCAL_TRANSACTIONS_JSON_PATH,
    price_history_dir: Path = LOCAL_MARKET_PRICES_DIR,
    holdings_path: Path = HOLDINGS_JSON_PATH,
    metrics_path: Path = PORTFOLIO_METRICS_JSON_PATH,
    snapshots_path: Path = PORTFOLIO_SNAPSHOTS_JSON_PATH,
    end_date: Optional[Union[str, date]] = None,
) -> dict:
    """Generate public portfolio runtime files from private local inputs."""
    transactions = load_transactions(transactions_path)
    price_history = load_price_history(price_history_dir)
    output = build_portfolio_history(
        transactions=transactions,
        price_history=price_history,
        end_date=end_date,
    )
    write_holdings_data(output["holdings"], json_path=holdings_path)
    write_portfolio_metrics(output["metrics"], metrics_path=metrics_path)
    _write_json(snapshots_path, output["snapshots"])
    return output


def generate_public_portfolio_data_from_firstrade_csv(
    source_path: Path,
    holdings_path: Path = HOLDINGS_JSON_PATH,
    metrics_path: Path = PORTFOLIO_METRICS_JSON_PATH,
    snapshots_path: Path = PORTFOLIO_SNAPSHOTS_JSON_PATH,
    price_history_dir: Path = LOCAL_MARKET_PRICES_DIR,
    end_date: Optional[Union[str, date]] = None,
) -> dict:
    """Generate public portfolio runtime files directly from a Firstrade CSV."""
    transactions = convert_firstrade_csv_to_transactions(source_path)
    price_history = load_price_history(price_history_dir)
    output = build_portfolio_history(
        transactions=transactions,
        price_history=price_history,
        end_date=end_date,
    )
    write_holdings_data(output["holdings"], json_path=holdings_path)
    write_portfolio_metrics(output["metrics"], metrics_path=metrics_path)
    _write_json(snapshots_path, output["snapshots"])
    return output
