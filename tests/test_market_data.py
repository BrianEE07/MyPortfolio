from io import BytesIO
from zipfile import ZipFile

from portfolio_app import market_data


def _build_finra_xlsx_bytes(rows):
    shared_strings = "".join(
        f"<si><t>{month}</t></si>"
        for month, _ in rows
    )
    worksheet_rows = "".join(
        (
            f'<row r="{index}">'
            f'<c r="A{index}" t="s"><v>{index - 1}</v></c>'
            f'<c r="B{index}"><v>{value}</v></c>'
            "</row>"
        )
        for index, (_, value) in enumerate(rows, start=1)
    )
    workbook_buffer = BytesIO()
    with ZipFile(workbook_buffer, "w") as workbook_archive:
        workbook_archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                '<Override PartName="/xl/sharedStrings.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
                "</Types>"
            ),
        )
        workbook_archive.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="xl/workbook.xml"/>'
                "</Relationships>"
            ),
        )
        workbook_archive.writestr(
            "xl/workbook.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
                "</workbook>"
            ),
        )
        workbook_archive.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                'Target="worksheets/sheet1.xml"/>'
                "</Relationships>"
            ),
        )
        workbook_archive.writestr(
            "xl/sharedStrings.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                f'count="{len(rows)}" uniqueCount="{len(rows)}">{shared_strings}</sst>'
            ),
        )
        workbook_archive.writestr(
            "xl/worksheets/sheet1.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f"<sheetData>{worksheet_rows}</sheetData>"
                "</worksheet>"
            ),
        )
    return workbook_buffer.getvalue()


def test_parse_finra_margin_rows_extracts_latest_values():
    sample_response = """
    <h3>FINRA Statistics</h3>
    Month/Year Debit Balances in Customers' Securities Margin Accounts
    Dec-25 1,225,597 211,720 199,762
    Nov-25 1,214,321 202,131 194,418
    Oct-25 1,183,654 197,923 195,376
    """

    rows = market_data._parse_finra_margin_rows(sample_response)

    assert rows == [
        ("Dec-25", 1225597),
        ("Nov-25", 1214321),
        ("Oct-25", 1183654),
    ]


def test_build_finra_margin_payload_formats_month_over_month():
    payload = market_data._build_finra_margin_payload(
        [
            ("Mar-26", 1220922),
            ("Feb-26", 1253192),
        ]
    )

    assert payload["latest_month"] == "Mar-26"
    assert payload["value_str"] == "1,220,922"
    assert payload["previous_month"] == "Feb-26"
    assert payload["mom_str"] == "-2.58%"
    assert payload["source_status"] == "live"


def test_parse_finra_margin_rows_from_xlsx_bytes_extracts_latest_values():
    workbook_bytes = _build_finra_xlsx_bytes(
        [
            ("Mar-26", 1220922),
            ("Feb-26", 1253192),
            ("Jan-26", 1279042),
        ]
    )

    rows = market_data._parse_finra_margin_rows_from_xlsx_bytes(workbook_bytes)

    assert rows == [
        ("Mar-26", 1220922),
        ("Feb-26", 1253192),
        ("Jan-26", 1279042),
    ]


def test_fetch_finra_margin_uses_parsed_html(monkeypatch):
    class StubResponse:
        text = """
        Month/Year Debit Balances in Customers' Securities Margin Accounts
        Mar-26 1,220,922 221,860 205,600
        Feb-26 1,253,192 205,060 200,047
        """

        def raise_for_status(self):
            return None

    monkeypatch.setattr(market_data.requests, "get", lambda *args, **kwargs: StubResponse())

    payload = market_data.fetch_finra_margin()

    assert payload["latest_month"] == "Mar-26"
    assert payload["value_str"] == "1,220,922"
    assert payload["source_status"] == "live"


def test_fetch_finra_margin_uses_download_when_finra_blocks_html_request(monkeypatch):
    workbook_bytes = _build_finra_xlsx_bytes(
        [
            ("Mar-26", 1220922),
            ("Feb-26", 1253192),
        ]
    )

    class Html403Response:
        text = "Forbidden"
        content = b""

        def raise_for_status(self):
            raise market_data.requests.HTTPError("403 Client Error")

    class DownloadResponse:
        text = ""
        content = workbook_bytes

        def raise_for_status(self):
            return None

    def stub_get(url, *args, **kwargs):
        if url == market_data.FINRA_MARGIN_URL:
            return Html403Response()
        if url == market_data.FINRA_MARGIN_DOWNLOAD_URL:
            return DownloadResponse()
        raise AssertionError(f"Unexpected URL requested: {url}")

    monkeypatch.setattr(market_data.requests, "get", stub_get)

    payload = market_data.fetch_finra_margin()

    assert payload["latest_month"] == "Mar-26"
    assert payload["value_str"] == "1,220,922"
    assert payload["source_status"] == "download"


def test_fetch_finra_margin_falls_back_when_html_and_download_fail(monkeypatch):
    class ErrorResponse:
        text = "Forbidden"
        content = b""

        def raise_for_status(self):
            raise market_data.requests.HTTPError("403 Client Error")

    monkeypatch.setattr(market_data.requests, "get", lambda *args, **kwargs: ErrorResponse())

    payload = market_data.fetch_finra_margin()

    assert payload["latest_month"] == "Mar-26"
    assert payload["value_str"] == "1,220,922"
    assert payload["source_status"] == "fallback"
