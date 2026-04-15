import json

import pytest

from portfolio_app.holdings import HoldingsValidationError
from portfolio_app.holdings_import import import_holdings_source


def test_imports_canonical_csv_into_json(tmp_path):
    source_path = tmp_path / "holdings.csv"
    source_path.write_text(
        "symbol,shares,cost_basis\nmsft,1.5,$425.10\nnvda,2,120.00\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "holdings.json"

    holdings, resolved_source_type = import_holdings_source(
        source_path=source_path,
        json_path=output_path,
    )

    assert resolved_source_type == "canonical_csv"
    assert holdings == [
        {"symbol": "MSFT", "shares": 1.5, "cost_basis": 425.10},
        {"symbol": "NVDA", "shares": 2.0, "cost_basis": 120.00},
    ]
    assert json.loads(output_path.read_text(encoding="utf-8")) == holdings


def test_imports_canonical_json_into_json(tmp_path):
    source_path = tmp_path / "holdings.json"
    source_path.write_text(
        json.dumps(
            [
                {"symbol": " goog ", "shares": "0.5", "cost_basis": "$100.00"},
                {"symbol": "crm", "shares": 2, "cost_basis": 250.25},
            ]
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "canonical.json"

    holdings, resolved_source_type = import_holdings_source(
        source_path=source_path,
        source_type="canonical_json",
        json_path=output_path,
    )

    assert resolved_source_type == "canonical_json"
    assert holdings == [
        {"symbol": "GOOG", "shares": 0.5, "cost_basis": 100.0},
        {"symbol": "CRM", "shares": 2.0, "cost_basis": 250.25},
    ]
    assert json.loads(output_path.read_text(encoding="utf-8")) == holdings


def test_invalid_csv_does_not_overwrite_existing_json(tmp_path):
    source_path = tmp_path / "holdings.csv"
    source_path.write_text(
        "symbol,shares,cost_basis\nAAPL,1,\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "holdings.json"
    existing_payload = [{"symbol": "KEEP", "shares": 1.0, "cost_basis": 10.0}]
    output_path.write_text(json.dumps(existing_payload), encoding="utf-8")

    with pytest.raises(HoldingsValidationError):
        import_holdings_source(source_path=source_path, json_path=output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == existing_payload


def test_invalid_json_does_not_overwrite_existing_json(tmp_path):
    source_path = tmp_path / "holdings.json"
    source_path.write_text(
        json.dumps({"symbol": "TSLA", "shares": 1, "cost_basis": 100}),
        encoding="utf-8",
    )
    output_path = tmp_path / "canonical.json"
    existing_payload = [{"symbol": "KEEP", "shares": 1.0, "cost_basis": 10.0}]
    output_path.write_text(json.dumps(existing_payload), encoding="utf-8")

    with pytest.raises(HoldingsValidationError):
        import_holdings_source(
            source_path=source_path,
            source_type="canonical_json",
            json_path=output_path,
        )

    assert json.loads(output_path.read_text(encoding="utf-8")) == existing_payload


def test_imports_firstrade_csv_into_canonical_holdings(tmp_path):
    source_path = tmp_path / "firstrade.csv"
    source_path.write_text(
        (
            "Symbol,Quantity,Price,Action,Description,TradeDate,SettledDate,"
            "Interest,Amount,Commission,Fee,CUSIP,RecordType\n"
            ",0.00,,Other,Wire Funds Received,2026-04-01,2026-04-01,0.00,1500.00,0.00,0.00,,Financial\n"
            "AAPL,2,100,BUY,APPLE INC,2026-04-02,2026-04-06,0.00,-200.00,1.00,1.00,037833100,Trade\n"
            "AAPL,1,130,BUY,APPLE INC,2026-04-03,2026-04-07,0.00,-130.00,0.00,0.00,037833100,Trade\n"
            "AAPL,1,140,SELL,APPLE INC,2026-04-04,2026-04-08,0.00,140.00,0.00,0.00,037833100,Trade\n"
            "MSFT,3,50,BUY,MICROSOFT CORP,2026-04-05,2026-04-09,0.00,-150.00,0.00,0.00,594918104,Trade\n"
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "holdings.json"

    holdings, resolved_source_type = import_holdings_source(
        source_path=source_path,
        source_type="firstrade_csv",
        json_path=output_path,
    )

    assert resolved_source_type == "firstrade_csv"
    assert holdings[0]["symbol"] == "AAPL"
    assert holdings[0]["shares"] == 2.0
    assert holdings[0]["cost_basis"] == pytest.approx(110.66666666666666)
    assert holdings[1] == {"symbol": "MSFT", "shares": 3.0, "cost_basis": 50.0}
    assert json.loads(output_path.read_text(encoding="utf-8")) == holdings


def test_firstrade_import_fails_on_unsupported_trade_action(tmp_path):
    source_path = tmp_path / "firstrade.csv"
    source_path.write_text(
        (
            "Symbol,Quantity,Price,Action,Description,TradeDate,SettledDate,"
            "Interest,Amount,Commission,Fee,CUSIP,RecordType\n"
            "AAPL,1,100,DIV,APPLE INC,2026-04-02,2026-04-06,0.00,0.00,0.00,0.00,037833100,Trade\n"
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "holdings.json"
    existing_payload = [{"symbol": "KEEP", "shares": 1.0, "cost_basis": 10.0}]
    output_path.write_text(json.dumps(existing_payload), encoding="utf-8")

    with pytest.raises(HoldingsValidationError):
        import_holdings_source(
            source_path=source_path,
            source_type="firstrade_csv",
            json_path=output_path,
        )

    assert json.loads(output_path.read_text(encoding="utf-8")) == existing_payload


def test_imports_firstrade_csv_with_negative_sell_quantity(tmp_path):
    source_path = tmp_path / "firstrade.csv"
    source_path.write_text(
        (
            "Symbol,Quantity,Price,Action,Description,TradeDate,SettledDate,"
            "Interest,Amount,Commission,Fee,CUSIP,RecordType\n"
            "MU,0.21355,351.19,BUY,MICRON TECHNOLOGY INC,2026-04-02,2026-04-06,0.00,-75.00,0.00,0.00,595112103,Trade\n"
            "MU,-0.04577,436.90,SELL,MICRON TECHNOLOGY INC,2026-04-14,2026-04-15,0.00,19.99,0.00,0.01,595112103,Trade\n"
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "holdings.json"

    holdings, resolved_source_type = import_holdings_source(
        source_path=source_path,
        source_type="firstrade_csv",
        json_path=output_path,
    )

    assert resolved_source_type == "firstrade_csv"
    assert holdings == [
        {
            "symbol": "MU",
            "shares": pytest.approx(0.16778),
            "cost_basis": pytest.approx(351.19),
        }
    ]
