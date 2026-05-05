#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio_app.config import (
    HOLDINGS_JSON_PATH,
    LOCAL_MARKET_PRICES_DIR,
    LOCAL_TRANSACTIONS_JSON_PATH,
    PORTFOLIO_METRICS_JSON_PATH,
    PORTFOLIO_SNAPSHOTS_JSON_PATH,
)
from portfolio_app.market_data import (
    fetch_latest_prices_from_yahoo,
    fetch_price_history_from_yahoo,
)
from portfolio_app.transactions import (
    TransactionValidationError,
    convert_firstrade_csv_to_transactions,
    generate_public_portfolio_data,
    generate_public_portfolio_data_from_firstrade_csv,
    load_price_history,
    merge_price_histories,
    validate_transactions_data,
    write_price_history,
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate public portfolio data from private canonical transactions."
    )
    parser.add_argument(
        "--transactions",
        default=str(LOCAL_TRANSACTIONS_JSON_PATH),
        help="Path to private canonical transactions JSON.",
    )
    parser.add_argument(
        "--firstrade-csv",
        help="Optional Firstrade Account History CSV source.",
    )
    parser.add_argument(
        "--price-history-dir",
        default=str(LOCAL_MARKET_PRICES_DIR),
        help="Path to private market price cache directory.",
    )
    parser.add_argument(
        "--holdings-output",
        default=str(HOLDINGS_JSON_PATH),
        help="Path to generated public holdings JSON.",
    )
    parser.add_argument(
        "--metrics-output",
        default=str(PORTFOLIO_METRICS_JSON_PATH),
        help="Path to generated public portfolio metrics JSON.",
    )
    parser.add_argument(
        "--snapshots-output",
        default=str(PORTFOLIO_SNAPSHOTS_JSON_PATH),
        help="Path to generated public portfolio snapshots JSON.",
    )
    parser.add_argument(
        "--end-date",
        help="Optional snapshot end date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--refresh-prices",
        action="store_true",
        help="Fetch Yahoo daily closes into private market price history before generation.",
    )
    parser.add_argument(
        "--build-output",
        help="Optional path for rebuilding the static HTML output after data generation.",
    )
    args = parser.parse_args()

    try:
        resolved_end_date = args.end_date
        price_history_dir = Path(args.price_history_dir)
        if args.refresh_prices:
            if args.firstrade_csv:
                transactions = convert_firstrade_csv_to_transactions(
                    Path(args.firstrade_csv)
                )
            else:
                transactions = validate_transactions_data(
                    json.loads(Path(args.transactions).read_text(encoding="utf-8"))
                )
            symbols = {
                transaction["symbol"]
                for transaction in transactions
                if "symbol" in transaction
            }
            symbols.add("^GSPC")
            start_date = transactions[0]["date"]
            end_date = args.end_date or date.today().isoformat()
            resolved_end_date = end_date
            fetched_history = fetch_price_history_from_yahoo(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
            )
            if end_date == date.today().isoformat():
                latest_prices = fetch_latest_prices_from_yahoo(symbols)
                if latest_prices:
                    latest_history = {
                        symbol: {end_date: price}
                        for symbol, price in latest_prices.items()
                    }
                    fetched_history = merge_price_histories(
                        fetched_history,
                        latest_history,
                    )
            merged_history = merge_price_histories(
                load_price_history(price_history_dir),
                fetched_history,
            )
            write_price_history(merged_history, price_history_dir)
            print(
                f"Refreshed price history for {len(fetched_history)} symbols "
                f"into {price_history_dir / 'prices.json'}."
            )

        if args.firstrade_csv:
            output = generate_public_portfolio_data_from_firstrade_csv(
                source_path=Path(args.firstrade_csv),
                price_history_dir=price_history_dir,
                holdings_path=Path(args.holdings_output),
                metrics_path=Path(args.metrics_output),
                snapshots_path=Path(args.snapshots_output),
                end_date=resolved_end_date,
            )
        else:
            output = generate_public_portfolio_data(
                transactions_path=Path(args.transactions),
                price_history_dir=price_history_dir,
                holdings_path=Path(args.holdings_output),
                metrics_path=Path(args.metrics_output),
                snapshots_path=Path(args.snapshots_output),
                end_date=resolved_end_date,
            )
    except TransactionValidationError as exc:
        print(f"Portfolio data generation failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Generated {len(output['holdings'])} holdings and "
        f"{len(output['snapshots'])} daily portfolio snapshots."
    )
    print(f"Updated public holdings at {args.holdings_output}.")
    print(f"Updated public metrics at {args.metrics_output}.")
    print(f"Updated public snapshots at {args.snapshots_output}.")

    if args.build_output:
        from portfolio_app.web import write_static_output

        write_static_output(Path(args.build_output))
        print(f"Rebuilt static HTML at {args.build_output}.")


if __name__ == "__main__":
    raise SystemExit(main())
