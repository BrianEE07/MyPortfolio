from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
IMPORTS_DIR = BASE_DIR / "imports"
LOCAL_CANONICAL_HOLDINGS_CSV_PATH = IMPORTS_DIR / "holdings.csv"
HOLDINGS_JSON_PATH = DATA_DIR / "holdings.json"

SITE_TITLE = "Wei's Portfolio"
TIMEZONE_NAME = "Asia/Taipei"
CHART_JS_URL = "https://cdn.jsdelivr.net/npm/chart.js"
WEALTH_GOAL_USD = 1_000_000
FIRST_US_STOCK_PURCHASE_DATE = "2026-04-02"

DEFAULT_TABS = (
    {"id": "overview", "label_zh": "持倉總覽", "label_en": "Holdings Overview"},
    {"id": "details", "label_zh": "個股明細", "label_en": "Stock Details"},
    {"id": "pulse", "label_zh": "市場觀察", "label_en": "Market Pulse"},
)
