"""Aged-open-invoice gate. Fixed today: 2026-10-31. No network."""

from datetime import date

from decline_notify.policy import aged_open_invoices, days_past_due, parse_day

from tests.conftest import TODAY


def _invoice(due, balance, number="INV-1"):
    return {
        "id": number,
        "invoiceNumber": number,
        "dueDate": due,
        "balance": balance,
        "currency": "USD",
        "status": "open",
    }


def test_exactly_ten_days_past_due_with_balance_is_aged(open_invoices):
    row = next(i for i in open_invoices if i["id"] == "inv-acme-aged")
    aged = aged_open_invoices([row], TODAY, 10)
    assert len(aged) == 1
    assert aged[0]["daysPastDue"] == 10
    assert aged[0]["invoiceNumber"] == "INV-1001"
    assert aged[0]["balance"] == 100.0


def test_nine_days_past_due_is_not_aged(open_invoices):
    row = next(i for i in open_invoices if i["id"] == "inv-nine-days")
    assert aged_open_invoices([row], TODAY, 10) == []


def test_zero_and_null_balance_are_excluded_even_when_old(open_invoices):
    rows = [i for i in open_invoices if i["id"] in ("inv-zero-balance", "inv-null-balance")]
    assert aged_open_invoices(rows, TODAY, 10) == []


def test_missing_or_malformed_due_date_is_excluded(open_invoices):
    rows = [i for i in open_invoices if i["id"] in ("inv-missing-due", "inv-bad-due")]
    assert aged_open_invoices(rows, TODAY, 10) == []
    assert parse_day(None) is None
    assert parse_day("not-a-date") is None
    assert parse_day(20261021) is None


def test_future_due_date_is_excluded(open_invoices):
    row = next(i for i in open_invoices if i["id"] == "inv-future")
    assert days_past_due(parse_day(row["dueDate"]), TODAY) < 0
    assert aged_open_invoices([row], TODAY, 10) == []


def test_threshold_zero_includes_due_today_and_custom_threshold():
    due_today = _invoice("2026-10-31", 5, "INV-TODAY")
    ten_days = _invoice("2026-10-21", 5, "INV-10")
    forty_days = _invoice("2026-09-21", 5, "INV-40")
    assert len(aged_open_invoices([due_today], TODAY, 0)) == 1
    assert aged_open_invoices([ten_days], TODAY, 30) == []
    assert aged_open_invoices([forty_days], TODAY, 30)[0]["daysPastDue"] == (TODAY - date(2026, 9, 21)).days


def test_aged_rows_include_invoice_fields(open_invoices):
    aged = aged_open_invoices(open_invoices, TODAY, 10)
    assert aged
    for row in aged:
        assert "invoiceNumber" in row
        assert "balance" in row
        assert "daysPastDue" in row
        assert row["daysPastDue"] >= 10
