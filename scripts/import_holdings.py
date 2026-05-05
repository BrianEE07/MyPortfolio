#!/usr/bin/env python3

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio_app.config import (
    HOLDINGS_JSON_PATH,
    LOCAL_MARKET_PRICES_DIR,
    PORTFOLIO_METRICS_JSON_PATH,
    PORTFOLIO_SNAPSHOTS_JSON_PATH,
)
from portfolio_app.holdings_import import (
    AUTO_SOURCE_TYPE,
    FIRSTRADE_CSV_SOURCE,
    SUPPORTED_SOURCE_TYPES,
    detect_holdings_source_type,
    import_holdings_source,
)
from portfolio_app.market_data import (
    fetch_latest_prices_from_yahoo,
    fetch_price_history_from_yahoo,
)
from portfolio_app.transactions import (
    convert_firstrade_csv_to_transactions,
    generate_public_portfolio_data_from_firstrade_csv,
    load_price_history,
    merge_price_histories,
    write_price_history,
)


def main():
    parser = argparse.ArgumentParser(
        description="Import a local holdings source into canonical JSON."
    )
    parser.add_argument(
        "source",
        nargs="?",
        default="imports/holdings.csv",
        help="Path to the local source file. Defaults to imports/holdings.csv.",
    )
    parser.add_argument(
        "--source-type",
        choices=SUPPORTED_SOURCE_TYPES,
        default="auto",
        help="Supported local source type. Defaults to auto detection by file extension.",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        help="Path to the output canonical JSON file.",
    )
    parser.add_argument(
        "--build-output",
        dest="build_output",
        help="Optional path for rebuilding the static HTML output after import.",
    )
    parser.add_argument(
        "--end-date",
        help="Optional snapshot end date in YYYY-MM-DD format for Firstrade imports.",
    )
    parser.add_argument(
        "--refresh-prices",
        action="store_true",
        help="Fetch Yahoo daily closes before Firstrade transaction generation.",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    resolved_source_type = (
        detect_holdings_source_type(source_path)
        if args.source_type == AUTO_SOURCE_TYPE
        else args.source_type
    )
    if resolved_source_type == FIRSTRADE_CSV_SOURCE:
        resolved_end_date = args.end_date
        if args.refresh_prices:
            transactions = convert_firstrade_csv_to_transactions(source_path)
            symbols = {
                transaction["symbol"]
                for transaction in transactions
                if "symbol" in transaction
            }
            symbols.add("^GSPC")
            end_date = args.end_date or date.today().isoformat()
            resolved_end_date = end_date
            fetched_history = fetch_price_history_from_yahoo(
                symbols=symbols,
                start_date=transactions[0]["date"],
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
                load_price_history(LOCAL_MARKET_PRICES_DIR),
                fetched_history,
            )
            write_price_history(merged_history, LOCAL_MARKET_PRICES_DIR)
            print(
                f"Refreshed price history for {len(fetched_history)} symbols "
                f"into {LOCAL_MARKET_PRICES_DIR / 'prices.json'}."
            )

        holdings_path = Path(args.json_path) if args.json_path else HOLDINGS_JSON_PATH
        output = generate_public_portfolio_data_from_firstrade_csv(
            source_path=source_path,
            holdings_path=holdings_path,
            metrics_path=PORTFOLIO_METRICS_JSON_PATH,
            snapshots_path=PORTFOLIO_SNAPSHOTS_JSON_PATH,
            price_history_dir=LOCAL_MARKET_PRICES_DIR,
            end_date=resolved_end_date,
        )
        print(
            f"Imported {len(output['holdings'])} holdings from firstrade_csv "
            "through canonical transactions."
        )
        print("Updated generated portfolio metrics at data/portfolio_metrics.json.")
        print("Updated generated portfolio snapshots at data/portfolio_snapshots.json.")
        if args.build_output:
            from portfolio_app.web import write_static_output

            write_static_output(Path(args.build_output))
            print(f"Rebuilt static HTML at {args.build_output}.")
        return

    kwargs = {
        "source_path": source_path,
        "source_type": resolved_source_type,
    }
    if args.json_path:
        kwargs["json_path"] = Path(args.json_path)

    holdings, resolved_source_type = import_holdings_source(**kwargs)
    print(
        f"Imported {len(holdings)} holdings from {resolved_source_type} "
        f"into canonical JSON."
    )
    print("Updated generated portfolio metrics at data/portfolio_metrics.json.")

    if args.build_output:
        from portfolio_app.web import write_static_output

        write_static_output(Path(args.build_output))
        print(f"Rebuilt static HTML at {args.build_output}.")


if __name__ == "__main__":
    main()
