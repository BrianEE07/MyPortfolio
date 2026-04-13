import csv
import json
from pathlib import Path
from typing import Optional

from .config import HOLDINGS_CSV_PATH, HOLDINGS_JSON_PATH

CANONICAL_FIELDS = ("symbol", "shares", "cost_basis")


class HoldingsValidationError(ValueError):
    """Raised when holdings data does not match the canonical schema."""


def _parse_float(raw_value: str, field_name: str, row_number: int) -> float:
    value = raw_value.strip().replace(",", "")
    if field_name == "cost_basis":
        value = value.replace("$", "")

    if not value:
        raise HoldingsValidationError(
            f"Row {row_number}: '{field_name}' cannot be empty."
        )

    try:
        return float(value)
    except ValueError as exc:
        raise HoldingsValidationError(
            f"Row {row_number}: '{field_name}' must be a number."
        ) from exc


def normalize_holding(raw_holding: dict, row_number: int) -> dict:
    """Normalize a raw holding into the canonical holdings schema."""
    symbol = str(raw_holding.get("symbol", "")).strip().upper()
    if not symbol:
        raise HoldingsValidationError(f"Row {row_number}: 'symbol' cannot be empty.")

    shares_raw = str(raw_holding.get("shares", "")).strip()
    cost_basis_raw = str(raw_holding.get("cost_basis", "")).strip()

    holding = {
        "symbol": symbol,
        "shares": _parse_float(shares_raw, "shares", row_number),
        "cost_basis": _parse_float(cost_basis_raw, "cost_basis", row_number),
    }
    return holding


def _validate_fields(fieldnames: Optional[list[str]]) -> None:
    if not fieldnames:
        raise HoldingsValidationError("The CSV file is missing a header row.")

    normalized_headers = [header.strip() for header in fieldnames]
    if tuple(normalized_headers) != CANONICAL_FIELDS:
        raise HoldingsValidationError(
            "CSV headers must be exactly: symbol,shares,cost_basis"
        )


def convert_holdings_csv_to_data(csv_path: Path = HOLDINGS_CSV_PATH) -> list[dict]:
    """Convert canonical CSV holdings input into validated holdings records."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        _validate_fields(reader.fieldnames)
        rows = list(reader)

    holdings = []
    for index, row in enumerate(rows, start=2):
        holdings.append(normalize_holding(row, index))

    return holdings


def write_holdings_json(
    csv_path: Path = HOLDINGS_CSV_PATH, json_path: Path = HOLDINGS_JSON_PATH
) -> list[dict]:
    """Convert holdings CSV into canonical JSON and write it to disk."""
    holdings = convert_holdings_csv_to_data(csv_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(holdings, indent=2), encoding="utf-8")
    return holdings


def load_holdings(json_path: Path = HOLDINGS_JSON_PATH) -> list[dict]:
    """Load holdings from canonical JSON and validate the stored schema."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise HoldingsValidationError("Holdings JSON must contain a list.")

    holdings = []
    for index, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            raise HoldingsValidationError(
                f"Entry {index}: each holding must be an object."
            )
        holdings.append(normalize_holding(entry, index))
    return holdings
