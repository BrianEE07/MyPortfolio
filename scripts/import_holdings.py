#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio_app.holdings import write_holdings_json


def main():
    parser = argparse.ArgumentParser(description="Convert holdings CSV to canonical JSON.")
    parser.add_argument("--csv", dest="csv_path", help="Path to the canonical holdings CSV file.")
    parser.add_argument("--json", dest="json_path", help="Path to the output canonical JSON file.")
    args = parser.parse_args()

    kwargs = {}
    if args.csv_path:
        kwargs["csv_path"] = Path(args.csv_path)
    if args.json_path:
        kwargs["json_path"] = Path(args.json_path)

    holdings = write_holdings_json(**kwargs)
    print(f"Imported {len(holdings)} holdings into canonical JSON.")


if __name__ == "__main__":
    main()
