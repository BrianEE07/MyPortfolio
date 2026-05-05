import json

import pytest

from portfolio_app.transactions import (
    TransactionValidationError,
    build_portfolio_history,
    convert_firstrade_csv_to_transactions,
    generate_public_portfolio_data,
    generate_public_portfolio_data_from_firstrade_csv,
    validate_transactions_data,
)


def _sample_transactions():
    return [
        {
            "id": "deposit-1",
            "date": "2026-04-01",
            "account": "firstrade",
            "type": "DEPOSIT",
            "currency": "USD",
            "amount": 1000,
        },
        {
            "id": "buy-1",
            "date": "2026-04-01",
            "account": "firstrade",
            "type": "BUY",
            "currency": "USD",
            "symbol": "aapl",
            "quantity": 2,
            "price": 100,
            "fee": 1,
        },
        {
            "id": "buy-2",
            "date": "2026-04-02",
            "account": "firstrade",
            "type": "BUY",
            "currency": "USD",
            "symbol": "AAPL",
            "quantity": 1,
            "price": 120,
            "fee": 0,
        },
        {
            "id": "sell-1",
            "date": "2026-04-03",
            "account": "firstrade",
            "type": "SELL",
            "currency": "USD",
            "symbol": "AAPL",
            "quantity": 1,
            "price": 150,
            "fee": 2,
        },
        {
            "id": "platform-fee",
            "date": "2026-04-05",
            "account": "firstrade",
            "type": "FEE",
            "currency": "USD",
            "amount": 5,
        },
        {
            "id": "withdrawal-1",
            "date": "2026-04-06",
            "account": "firstrade",
            "type": "WITHDRAWAL",
            "currency": "USD",
            "amount": 100,
        },
    ]


def test_validates_transaction_schema_and_normalizes_values():
    transactions = validate_transactions_data(
        [
            {
                "id": "buy-lowercase",
                "date": "2026-04-02",
                "account": "firstrade",
                "type": "buy",
                "currency": "usd",
                "symbol": " nvda ",
                "quantity": "0.5",
                "price": "$100.25",
                "fee": "0",
            }
        ]
    )

    assert transactions == [
        {
            "id": "buy-lowercase",
            "date": "2026-04-02",
            "account": "firstrade",
            "type": "BUY",
            "currency": "USD",
            "symbol": "NVDA",
            "quantity": 0.5,
            "price": 100.25,
            "fee": 0.0,
        }
    ]


def test_rejects_invalid_transaction_schema():
    with pytest.raises(TransactionValidationError, match="unsupported transaction type"):
        validate_transactions_data(
            [
                {
                    "id": "dividend-1",
                    "date": "2026-04-02",
                    "account": "firstrade",
                    "type": "DIVIDEND",
                    "currency": "USD",
                    "amount": 2,
                }
            ]
        )

    with pytest.raises(TransactionValidationError, match="only USD"):
        validate_transactions_data(
            [
                {
                    "id": "deposit-twd",
                    "date": "2026-04-02",
                    "account": "tw-broker",
                    "type": "DEPOSIT",
                    "currency": "TWD",
                    "amount": 1000,
                }
            ]
        )


def test_reconstructs_holdings_cash_metrics_and_daily_snapshots():
    output = build_portfolio_history(
        transactions=_sample_transactions(),
        price_history={
            "AAPL": {
                "2026-04-01": 100,
                "2026-04-02": 125,
                "2026-04-03": 140,
                "2026-04-04": 130,
                "2026-04-06": 160,
            }
        },
    )

    assert output["holdings"] == [
        {
            "symbol": "AAPL",
            "shares": pytest.approx(2.0),
            "cost_basis": pytest.approx(107.0),
        }
    ]
    assert output["metrics"]["realized_pl"] == pytest.approx(41.0)
    assert output["metrics"]["realized_return_pct"] == pytest.approx(38.317757)
    assert output["metrics"]["twr"] == pytest.approx(14.314314)
    assert output["metrics"]["cagr"] is not None
    assert output["metrics"]["current_drawdown"] == pytest.approx(-5.871725)
    assert output["metrics"]["max_drawdown"] == pytest.approx(-5.871725)
    assert output["metrics"]["sharpe"] is not None
    assert output["metrics"]["beta"] is None
    assert output["metrics"]["alpha"] is None

    snapshots = output["snapshots"]
    assert [snapshot["date"] for snapshot in snapshots] == [
        "2026-04-01",
        "2026-04-02",
        "2026-04-03",
        "2026-04-04",
        "2026-04-05",
        "2026-04-06",
    ]
    assert snapshots[0]["portfolio_cash"] == pytest.approx(799.0)
    assert snapshots[0]["net_external_cash_flow"] == pytest.approx(1000.0)
    assert snapshots[4]["holdings_market_value"] == pytest.approx(260.0)
    assert snapshots[4]["total_portfolio_value"] == pytest.approx(1082.0)
    assert snapshots[-1] == {
        "date": "2026-04-06",
        "holdings_market_value": pytest.approx(320.0),
        "portfolio_cash": pytest.approx(722.0),
        "total_portfolio_value": pytest.approx(1042.0),
        "invested_cost_basis": pytest.approx(214.0),
        "unrealized_pl": pytest.approx(106.0),
        "realized_pl": pytest.approx(41.0),
        "net_external_cash_flow": pytest.approx(-100.0),
    }


def test_uses_trade_price_when_market_price_is_missing_on_buy_date():
    output = build_portfolio_history(
        transactions=[
            {
                "id": "deposit-1",
                "date": "2026-04-01",
                "account": "firstrade",
                "type": "DEPOSIT",
                "currency": "USD",
                "amount": 1000,
            },
            {
                "id": "buy-1",
                "date": "2026-04-01",
                "account": "firstrade",
                "type": "BUY",
                "currency": "USD",
                "symbol": "NVDA",
                "quantity": 1,
                "price": 120,
                "fee": 0,
            },
        ],
        price_history={},
    )

    assert output["snapshots"][0]["holdings_market_value"] == pytest.approx(120.0)


def test_fails_when_sell_exceeds_current_shares():
    with pytest.raises(TransactionValidationError, match="sell quantity exceeds"):
        build_portfolio_history(
            transactions=[
                {
                    "id": "deposit-1",
                    "date": "2026-04-01",
                    "account": "firstrade",
                    "type": "DEPOSIT",
                    "currency": "USD",
                    "amount": 1000,
                },
                {
                    "id": "sell-1",
                    "date": "2026-04-02",
                    "account": "firstrade",
                    "type": "SELL",
                    "currency": "USD",
                    "symbol": "AAPL",
                    "quantity": 1,
                    "price": 100,
                    "fee": 0,
                },
            ]
        )


def test_generates_public_files_from_private_inputs(tmp_path):
    transactions_path = tmp_path / "private" / "transactions.json"
    transactions_path.parent.mkdir()
    transactions_path.write_text(json.dumps(_sample_transactions()), encoding="utf-8")
    price_history_dir = tmp_path / "private" / "market_prices"
    price_history_dir.mkdir()
    (price_history_dir / "prices.json").write_text(
        json.dumps({"AAPL": {"2026-04-01": 100, "2026-04-06": 160}}),
        encoding="utf-8",
    )
    holdings_path = tmp_path / "data" / "holdings.json"
    metrics_path = tmp_path / "data" / "portfolio_metrics.json"
    snapshots_path = tmp_path / "data" / "portfolio_snapshots.json"

    generate_public_portfolio_data(
        transactions_path=transactions_path,
        price_history_dir=price_history_dir,
        holdings_path=holdings_path,
        metrics_path=metrics_path,
        snapshots_path=snapshots_path,
    )

    assert json.loads(holdings_path.read_text(encoding="utf-8")) == [
        {"symbol": "AAPL", "shares": 2.0, "cost_basis": 107.0}
    ]
    assert json.loads(metrics_path.read_text(encoding="utf-8"))["realized_pl"] == 41.0
    assert len(json.loads(snapshots_path.read_text(encoding="utf-8"))) == 6


def test_converts_firstrade_csv_to_transactions_with_interest(tmp_path):
    source_path = tmp_path / "firstrade.csv"
    source_path.write_text(
        (
            "Symbol,Quantity,Price,Action,Description,TradeDate,SettledDate,"
            "Interest,Amount,Commission,Fee,CUSIP,RecordType\n"
            ",0.00,,Other,Wire Funds Received,2026-04-01,2026-04-01,0.00,1500.00,0.00,0.00,,Financial\n"
            "AAPL,1,100,BUY,APPLE INC,2026-04-02,2026-04-06,0.00,-100.00,0.00,0.00,037833100,Trade\n"
            ",0.00,,Interest,INTEREST,2026-04-03,2026-04-03,0.08,0.08,0.00,0.00,,Financial\n"
            "AAPL,-0.5,120,SELL,APPLE INC,2026-04-04,2026-04-07,0.00,60.00,0.00,0.01,037833100,Trade\n"
        ),
        encoding="utf-8",
    )

    transactions = convert_firstrade_csv_to_transactions(source_path)

    assert [transaction["type"] for transaction in transactions] == [
        "DEPOSIT",
        "BUY",
        "INTEREST",
        "SELL",
    ]
    assert transactions[2]["amount"] == pytest.approx(0.08)
    assert transactions[3]["fee"] == pytest.approx(0.01)


def test_generates_public_files_from_firstrade_csv(tmp_path):
    source_path = tmp_path / "firstrade.csv"
    source_path.write_text(
        (
            "Symbol,Quantity,Price,Action,Description,TradeDate,SettledDate,"
            "Interest,Amount,Commission,Fee,CUSIP,RecordType\n"
            ",0.00,,Other,Wire Funds Received,2026-04-01,2026-04-01,0.00,1500.00,0.00,0.00,,Financial\n"
            "AAPL,1,100,BUY,APPLE INC,2026-04-02,2026-04-06,0.00,-100.00,0.00,0.00,037833100,Trade\n"
            "AAPL,-0.5,120,SELL,APPLE INC,2026-04-04,2026-04-07,0.00,60.00,0.00,0.01,037833100,Trade\n"
        ),
        encoding="utf-8",
    )
    holdings_path = tmp_path / "data" / "holdings.json"
    metrics_path = tmp_path / "data" / "portfolio_metrics.json"
    snapshots_path = tmp_path / "data" / "portfolio_snapshots.json"

    output = generate_public_portfolio_data_from_firstrade_csv(
        source_path=source_path,
        holdings_path=holdings_path,
        metrics_path=metrics_path,
        snapshots_path=snapshots_path,
        end_date="2026-04-05",
    )

    assert output["holdings"] == [
        {"symbol": "AAPL", "shares": pytest.approx(0.5), "cost_basis": pytest.approx(100.0)}
    ]
    assert json.loads(metrics_path.read_text(encoding="utf-8"))["realized_pl"] == pytest.approx(9.99)
    assert [snapshot["date"] for snapshot in output["snapshots"]] == [
        "2026-04-01",
        "2026-04-02",
        "2026-04-03",
        "2026-04-04",
        "2026-04-05",
    ]
