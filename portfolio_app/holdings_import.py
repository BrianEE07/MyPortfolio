import json
import csv
from pathlib import Path

from .config import HOLDINGS_JSON_PATH, LOCAL_CANONICAL_HOLDINGS_CSV_PATH
from .holdings import (
    HoldingsValidationError,
    convert_holdings_csv_to_data,
    validate_holdings_data,
    write_holdings_data,
)

AUTO_SOURCE_TYPE = "auto"
CANONICAL_CSV_SOURCE = "canonical_csv"
CANONICAL_JSON_SOURCE = "canonical_json"
FIRSTRADE_CSV_SOURCE = "firstrade_csv"
SUPPORTED_SOURCE_TYPES = (
    AUTO_SOURCE_TYPE,
    CANONICAL_CSV_SOURCE,
    CANONICAL_JSON_SOURCE,
    FIRSTRADE_CSV_SOURCE,
)

CANONICAL_CSV_HEADERS = ("symbol", "shares", "cost_basis")
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


class HoldingsImportError(ValueError):
    """Raised when a local holdings source cannot be imported."""


def _parse_number(raw_value: object, field_name: str) -> float:
    value = str("" if raw_value is None else raw_value).strip().replace(",", "").replace("$", "")
    if not value:
        raise HoldingsValidationError(f"'{field_name}' cannot be empty.")
    try:
        return float(value)
    except ValueError as exc:
        raise HoldingsValidationError(f"'{field_name}' must be numeric.") from exc


def _detect_csv_source_type(source_path: Path) -> str:
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            headers = next(reader)
        except StopIteration as exc:
            raise HoldingsValidationError(
                f"CSV source file '{source_path}' is empty."
            ) from exc

    normalized_headers = tuple(header.strip() for header in headers)
    if normalized_headers == CANONICAL_CSV_HEADERS:
        return CANONICAL_CSV_SOURCE
    if normalized_headers == FIRSTRADE_CSV_HEADERS:
        return FIRSTRADE_CSV_SOURCE

    raise HoldingsImportError(
        "Unsupported CSV headers. Use canonical holdings CSV headers or a "
        "supported broker export format."
    )


def _normalize_firstrade_holdings(source_path: Path) -> list[dict]:
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise HoldingsValidationError("Firstrade CSV is missing a header row.")

        normalized_headers = tuple(header.strip() for header in reader.fieldnames)
        if normalized_headers != FIRSTRADE_CSV_HEADERS:
            raise HoldingsValidationError(
                "Firstrade CSV headers do not match the supported export format."
            )

        positions = {}
        for row_number, row in enumerate(reader, start=2):
            record_type = str(row.get("RecordType", "")).strip()
            if record_type != "Trade":
                continue

            action = str(row.get("Action", "")).strip().upper()
            if action not in {"BUY", "SELL"}:
                raise HoldingsValidationError(
                    f"Row {row_number}: unsupported Firstrade trade action '{action}'."
                )

            symbol = str(row.get("Symbol", "")).strip().upper()
            if not symbol:
                raise HoldingsValidationError(
                    f"Row {row_number}: Firstrade trade row is missing a symbol."
                )

            raw_quantity = _parse_number(
                row.get("Quantity"), f"Row {row_number} quantity"
            )
            price = _parse_number(row.get("Price"), f"Row {row_number} price")
            commission = _parse_number(
                row.get("Commission", 0) or 0, f"Row {row_number} commission"
            )
            fee = _parse_number(row.get("Fee", 0) or 0, f"Row {row_number} fee")

            quantity = abs(raw_quantity)
            if quantity <= 0:
                raise HoldingsValidationError(
                    f"Row {row_number}: trade quantity must be positive."
                )

            position = positions.setdefault(
                symbol,
                {"shares": 0.0, "total_cost": 0.0},
            )

            if action == "BUY":
                position["shares"] += quantity
                position["total_cost"] += (quantity * price) + commission + fee
                continue

            if position["shares"] + 1e-9 < quantity:
                raise HoldingsValidationError(
                    f"Row {row_number}: sell quantity exceeds current shares for {symbol}."
                )

            average_cost = (
                position["total_cost"] / position["shares"]
                if position["shares"]
                else 0.0
            )
            position["shares"] -= quantity
            position["total_cost"] -= average_cost * quantity

            if abs(position["shares"]) < 1e-9:
                position["shares"] = 0.0
                position["total_cost"] = 0.0

    holdings = []
    for symbol, position in sorted(positions.items()):
        shares = position["shares"]
        if shares <= 0:
            continue
        cost_basis = position["total_cost"] / shares
        holdings.append(
            {
                "symbol": symbol,
                "shares": shares,
                "cost_basis": cost_basis,
            }
        )

    return validate_holdings_data(holdings)


def detect_holdings_source_type(source_path: Path) -> str:
    """Infer the supported source type from the local file extension."""
    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        return _detect_csv_source_type(source_path)
    if suffix == ".json":
        return CANONICAL_JSON_SOURCE
    raise HoldingsImportError(
        "Unsupported source file extension. Use a .csv or .json file, "
        "or pass an explicit supported --source-type."
    )


def normalize_holdings_source(
    source_path: Path, source_type: str = AUTO_SOURCE_TYPE
) -> tuple[list[dict], str]:
    """Load a supported local source file and normalize it to canonical holdings."""
    resolved_source_type = (
        detect_holdings_source_type(source_path)
        if source_type == AUTO_SOURCE_TYPE
        else source_type
    )

    if resolved_source_type not in SUPPORTED_SOURCE_TYPES:
        raise HoldingsImportError(
            "Unsupported source type. Supported values are: "
            f"{', '.join(SUPPORTED_SOURCE_TYPES)}"
        )

    if resolved_source_type == CANONICAL_CSV_SOURCE:
        holdings = convert_holdings_csv_to_data(source_path)
        return holdings, resolved_source_type

    if resolved_source_type == CANONICAL_JSON_SOURCE:
        try:
            data = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HoldingsValidationError(
                f"Invalid JSON in source file '{source_path}'."
            ) from exc
        holdings = validate_holdings_data(data)
        return holdings, resolved_source_type

    if resolved_source_type == FIRSTRADE_CSV_SOURCE:
        holdings = _normalize_firstrade_holdings(source_path)
        return holdings, resolved_source_type

    raise HoldingsImportError(
        f"Source type '{resolved_source_type}' is not implemented yet."
    )


def import_holdings_source(
    source_path: Path = LOCAL_CANONICAL_HOLDINGS_CSV_PATH,
    source_type: str = AUTO_SOURCE_TYPE,
    json_path: Path = HOLDINGS_JSON_PATH,
) -> tuple[list[dict], str]:
    """Import a local source file into the canonical holdings JSON file."""
    holdings, resolved_source_type = normalize_holdings_source(
        source_path=source_path,
        source_type=source_type,
    )
    normalized_holdings = write_holdings_data(holdings, json_path=json_path)
    return normalized_holdings, resolved_source_type
