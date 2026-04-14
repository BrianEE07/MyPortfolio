#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio_app.holdings_import import SUPPORTED_SOURCE_TYPES, import_holdings_source


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
    args = parser.parse_args()

    kwargs = {
        "source_path": Path(args.source),
        "source_type": args.source_type,
    }
    if args.json_path:
        kwargs["json_path"] = Path(args.json_path)

    holdings, resolved_source_type = import_holdings_source(**kwargs)
    print(
        f"Imported {len(holdings)} holdings from {resolved_source_type} "
        f"into canonical JSON."
    )

    if args.build_output:
        from portfolio_app.web import write_static_output

        write_static_output(Path(args.build_output))
        print(f"Rebuilt static HTML at {args.build_output}.")


if __name__ == "__main__":
    main()
