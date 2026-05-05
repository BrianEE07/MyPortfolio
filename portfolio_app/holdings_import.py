import json
import csv
from pathlib import Path

from .config import (
    HOLDINGS_JSON_PATH,
    LOCAL_CANONICAL_HOLDINGS_CSV_PATH,
    PORTFOLIO_METRICS_JSON_PATH,
)
from .holdings import (
    HoldingsValidationError,
    convert_holdings_csv_to_data,
    validate_holdings_data,
    write_holdings_data,
)
from .metrics import default_portfolio_metrics, write_portfolio_metrics
from .transactions import (
    TransactionValidationError,
    build_portfolio_history,
    convert_firstrade_csv_to_transactions,
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
) -> tuple[list[dict], str, dict]:
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
        return holdings, resolved_source_type, default_portfolio_metrics()

    if resolved_source_type == CANONICAL_JSON_SOURCE:
        try:
            data = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HoldingsValidationError(
                f"Invalid JSON in source file '{source_path}'."
            ) from exc
        holdings = validate_holdings_data(data)
        return holdings, resolved_source_type, default_portfolio_metrics()

    if resolved_source_type == FIRSTRADE_CSV_SOURCE:
        try:
            transactions = convert_firstrade_csv_to_transactions(source_path)
        except TransactionValidationError as exc:
            raise HoldingsValidationError(str(exc)) from exc
        output = build_portfolio_history(transactions=transactions)
        return output["holdings"], resolved_source_type, output["metrics"]

    raise HoldingsImportError(
        f"Source type '{resolved_source_type}' is not implemented yet."
    )


def import_holdings_source(
    source_path: Path = LOCAL_CANONICAL_HOLDINGS_CSV_PATH,
    source_type: str = AUTO_SOURCE_TYPE,
    json_path: Path = HOLDINGS_JSON_PATH,
    metrics_path: Path = PORTFOLIO_METRICS_JSON_PATH,
) -> tuple[list[dict], str]:
    """Import a local source file into the canonical holdings JSON file."""
    holdings, resolved_source_type, metrics = normalize_holdings_source(
        source_path=source_path,
        source_type=source_type,
    )
    normalized_holdings = write_holdings_data(holdings, json_path=json_path)
    write_portfolio_metrics(metrics, metrics_path=metrics_path)
    return normalized_holdings, resolved_source_type
