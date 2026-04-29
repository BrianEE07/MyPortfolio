DEFAULT_CATEGORY_ID = "other"

CATEGORY_DEFINITIONS = {
    "technology": {
        "id": "technology",
        "label_zh": "科技",
        "label_en": "Technology",
        "color": "#6e8fe8",
    },
    "communication-services": {
        "id": "communication-services",
        "label_zh": "通訊服務",
        "label_en": "Communication Services",
        "color": "#49b89a",
    },
    "consumer-cyclical": {
        "id": "consumer-cyclical",
        "label_zh": "非必需消費",
        "label_en": "Consumer Cyclical",
        "color": "#d8b45f",
    },
    "consumer-defensive": {
        "id": "consumer-defensive",
        "label_zh": "必需消費",
        "label_en": "Consumer Defensive",
        "color": "#7fb788",
    },
    "financial-services": {
        "id": "financial-services",
        "label_zh": "金融服務",
        "label_en": "Financial Services",
        "color": "#e08a63",
    },
    "healthcare": {
        "id": "healthcare",
        "label_zh": "醫療保健",
        "label_en": "Healthcare",
        "color": "#ad88da",
    },
    "industrials": {
        "id": "industrials",
        "label_zh": "工業",
        "label_en": "Industrials",
        "color": "#8b95a5",
    },
    "energy": {
        "id": "energy",
        "label_zh": "能源",
        "label_en": "Energy",
        "color": "#d7a15f",
    },
    "real-estate": {
        "id": "real-estate",
        "label_zh": "房地產",
        "label_en": "Real Estate",
        "color": "#da88a7",
    },
    "basic-materials": {
        "id": "basic-materials",
        "label_zh": "原物料",
        "label_en": "Basic Materials",
        "color": "#b79a6d",
    },
    "utilities": {
        "id": "utilities",
        "label_zh": "公用事業",
        "label_en": "Utilities",
        "color": "#6da2b8",
    },
    "other": {
        "id": "other",
        "label_zh": "其他",
        "label_en": "Other",
        "color": "#a2948a",
    },
}

SECTOR_CATEGORY_MAP = {
    "technology": "technology",
    "communication services": "communication-services",
    "consumer cyclical": "consumer-cyclical",
    "consumer defensive": "consumer-defensive",
    "financial services": "financial-services",
    "healthcare": "healthcare",
    "industrials": "industrials",
    "energy": "energy",
    "real estate": "real-estate",
    "basic materials": "basic-materials",
    "utilities": "utilities",
}

INDUSTRY_CATEGORY_KEYWORDS = (
    ("technology", ("semiconductor", "software", "information technology", "hardware", "ai")),
    (
        "communication-services",
        ("internet content", "internet content & information", "search", "social media", "interactive media"),
    ),
    ("consumer-cyclical", ("retail", "consumer electronics", "automotive", "travel", "restaurants")),
    ("financial-services", ("bank", "insurance", "asset management", "financial")),
    ("healthcare", ("biotech", "pharmaceutical", "medical", "healthcare")),
    ("energy", ("oil", "gas", "uranium", "energy")),
    ("industrials", ("industrial", "aerospace", "defense", "transportation")),
    ("real-estate", ("reit", "real estate")),
    ("consumer-defensive", ("beverages", "household", "consumer staples", "discount stores")),
    ("basic-materials", ("chemicals", "metals", "mining", "building materials")),
    ("utilities", ("regulated electric", "utilities", "independent power")),
)


def get_category_definition(category_id):
    return CATEGORY_DEFINITIONS.get(category_id, CATEGORY_DEFINITIONS[DEFAULT_CATEGORY_ID])


def _normalize_classification_value(value):
    return (value or "").strip().lower()


def resolve_holding_category(symbol, sector=None, industry=None):
    normalized_sector = _normalize_classification_value(sector)
    if normalized_sector in SECTOR_CATEGORY_MAP:
        return get_category_definition(SECTOR_CATEGORY_MAP[normalized_sector])

    normalized_industry = _normalize_classification_value(industry)
    combined_text = " ".join(part for part in (normalized_sector, normalized_industry) if part)
    for category_id, keywords in INDUSTRY_CATEGORY_KEYWORDS:
        if any(keyword in combined_text for keyword in keywords):
            return get_category_definition(category_id)

    # Keep a durable fallback so rows remain filterable even when upstream
    # quote metadata does not expose sector information.
    return get_category_definition(DEFAULT_CATEGORY_ID)
