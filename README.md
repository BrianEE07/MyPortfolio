# Wei's Portfolio

[**Portfolio Link**](https://portfolio.weiweifan.com)

Credit to: https://github.com/huangchink/portfolio

## Local Commands

```bash
python3 portfolio.py --serve
PORT=5002 python3 portfolio.py --serve
python3 portfolio.py --output docs/index.html
python3 scripts/import_holdings.py imports/holdings.csv
python3 scripts/import_holdings.py imports/firstrade/FT_CSV_91323853.csv --source-type firstrade_csv
PYTHONPATH=. .venv/bin/pytest
```

For local holdings update details, see [docs/holdings-import.md](docs/holdings-import.md).
