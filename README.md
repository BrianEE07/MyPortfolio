# Wei's Portfolio

[**Portfolio Link**](https://portfolio.weiweifan.com)

Credit to: https://github.com/huangchink/portfolio

## Local Commands

```bash
python3 portfolio.py --serve
PORT=5002 python3 portfolio.py --serve
python3 portfolio.py --output docs/index.html
python3 scripts/build_portfolio_data.py --firstrade-csv imports/firstrade/FT_CSV_91323853.csv --refresh-prices --build-output docs/index.html
python3 scripts/build_portfolio_data.py
python3 scripts/import_holdings.py imports/holdings.csv
PYTHONPATH=. .venv/bin/pytest
```

For local holdings update details, see [docs/holdings-import.md](docs/holdings-import.md).
For the private transaction pipeline, see [docs/data-foundation.md](docs/data-foundation.md).
