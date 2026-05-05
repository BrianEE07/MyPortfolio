from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
IMPORTS_DIR = BASE_DIR / "imports"
PRIVATE_DIR = BASE_DIR / "private"
LOCAL_CANONICAL_HOLDINGS_CSV_PATH = IMPORTS_DIR / "holdings.csv"
LOCAL_TRANSACTIONS_JSON_PATH = PRIVATE_DIR / "transactions.json"
LOCAL_MARKET_PRICES_DIR = PRIVATE_DIR / "market_prices"
HOLDINGS_JSON_PATH = DATA_DIR / "holdings.json"
PORTFOLIO_METRICS_JSON_PATH = DATA_DIR / "portfolio_metrics.json"
PORTFOLIO_SNAPSHOTS_JSON_PATH = DATA_DIR / "portfolio_snapshots.json"

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

PROJECT_ROADMAP_COMPLETED = (
    {
        "version": "v1.0.1",
        "title_zh": "模組化整理與分頁骨架",
        "title_en": "Modular cleanup and tab foundation",
        "detail_zh": "把原本單檔原型拆進 portfolio_app，建立持倉總覽、個股明細和市場觀察三個主分頁。",
    },
    {
        "version": "v1.1.0",
        "title_zh": "持倉匯入與 canonical schema",
        "title_en": "Canonical holdings import flow",
        "detail_zh": "建立 holdings.json 為單一持倉來源，接上本地匯入流程與基本驗證。",
    },
    {
        "version": "v1.2.0",
        "title_zh": "持倉總覽第一輪重整",
        "title_en": "Holdings Overview refresh",
        "detail_zh": "把總覽頁整理成較清楚的 hero cards、核心績效數字與前十大持股視覺化。",
    },
    {
        "version": "v1.3.4",
        "title_zh": "市場觀察第一輪完成",
        "title_en": "First Market Pulse pass",
        "detail_zh": "完成市場情緒、大盤趨勢與抄底訊號三塊內容，並補上多輪互動與版面微調。",
    },
    {
        "version": "v1.4.0",
        "title_zh": "資料地基與投組指標",
        "title_en": "Data foundation and portfolio metrics",
        "detail_zh": "建立本機交易到公開持倉、績效與每日快照的資料管線，並讓總覽顯示現金、總市值、IRR、CAGR 與回檔。",
    },
)

PROJECT_ROADMAP_NEXT = (
    {
        "order": 1,
        "title_zh": "投資總覽 2.0",
        "title_en": "Investment Overview 2.0",
        "detail_zh": "把現在的持倉總覽升級成真正的投組總覽頁，加入投組價值走勢、配置、風險狀態與更完整的資產類別。",
    },
    {
        "order": 2,
        "title_zh": "配置目標與再平衡",
        "title_en": "Allocation & Rebalancing",
        "detail_zh": "加入目標配置、drift、rebalance status 和下一步該補哪類資產的提示。",
    },
    {
        "order": 3,
        "title_zh": "持倉明細 2.0",
        "title_en": "Positions 2.0",
        "detail_zh": "把個股明細擴展成支援 ETF、台股、美股和 Crypto 的多資產持倉頁。",
    },
    {
        "order": 4,
        "title_zh": "設定面板與動態視圖",
        "title_en": "Settings & Dynamic View",
        "detail_zh": "把主題切換升級成完整 settings，讓資產類別 filter 可以影響全站數值與圖表。",
    },
    {
        "order": 5,
        "title_zh": "市場觀察 2.0",
        "title_en": "Market Pulse 2.0",
        "detail_zh": "往估值、總經、利率、美元、新聞摘要和外部內容延伸，讓市場觀察更完整。",
    },
    {
        "order": 6,
        "title_zh": "介面打磨與專案文件",
        "title_en": "UI Polish & Documentation",
        "detail_zh": "最後再收整視覺、fake data 情境、README、版本紀錄與整體說明文件。",
    },
)
