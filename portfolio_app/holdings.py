import csv
import json
import os
from pathlib import Path
from typing import Optional

from .config import HOLDINGS_JSON_PATH, LOCAL_CANONICAL_HOLDINGS_CSV_PATH

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


def validate_holdings_data(raw_holdings: object) -> list[dict]:
    """Validate and normalize a list of holdings records."""
    if not isinstance(raw_holdings, list):
        raise HoldingsValidationError("Holdings data must contain a list.")

    holdings = []
    for index, entry in enumerate(raw_holdings, start=1):
        if not isinstance(entry, dict):
            raise HoldingsValidationError(
                f"Entry {index}: each holding must be an object."
            )
        holdings.append(normalize_holding(entry, index))
    return holdings


def _validate_fields(fieldnames: Optional[list[str]]) -> None:
    if not fieldnames:
        raise HoldingsValidationError("The CSV file is missing a header row.")

    normalized_headers = [header.strip() for header in fieldnames]
    if tuple(normalized_headers) != CANONICAL_FIELDS:
        raise HoldingsValidationError(
            "CSV headers must be exactly: symbol,shares,cost_basis"
        )


def convert_holdings_csv_to_data(
    csv_path: Path = LOCAL_CANONICAL_HOLDINGS_CSV_PATH,
) -> list[dict]:
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
    csv_path: Path = LOCAL_CANONICAL_HOLDINGS_CSV_PATH,
    json_path: Path = HOLDINGS_JSON_PATH,
) -> list[dict]:
    """Convert holdings CSV into canonical JSON and write it to disk."""
    holdings = convert_holdings_csv_to_data(csv_path)
    return write_holdings_data(holdings, json_path)


def write_holdings_data(
    holdings: object, json_path: Path = HOLDINGS_JSON_PATH
) -> list[dict]:
    """Validate holdings and atomically persist canonical JSON to disk."""
    normalized_holdings = validate_holdings_data(holdings)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = json_path.with_name(f"{json_path.name}.tmp")
    temp_path.write_text(
        json.dumps(normalized_holdings, indent=2), encoding="utf-8"
    )
    temp_path.replace(json_path)
    return normalized_holdings


def _resolve_holdings_json_path(json_path: Optional[Path]) -> Path:
    if json_path is not None:
        return json_path

    override_path = os.environ.get("PORTFOLIO_HOLDINGS_PATH")
    if not override_path:
        return HOLDINGS_JSON_PATH

    return Path(override_path).expanduser()


def load_holdings(json_path: Optional[Path] = None) -> list[dict]:
    """Load holdings from canonical JSON and validate the stored schema."""
    json_path = _resolve_holdings_json_path(json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return validate_holdings_data(data)
