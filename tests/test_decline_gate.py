"""Decline gate combined with the aged-invoice gate. No network."""

from decline_notify.policy import process_customer, summarize_declines

from tests.conftest import APP_URL, TODAY, TICKET_TYPE_ID, FakeBenji, FakeHalo


def _aged_invoice():
    return {
        "id": "inv-acme-aged",
        "invoiceNumber": "INV-1001",
        "dueDate": "2026-10-21",
        "balance": 100.0,
        "currency": "USD",
        "status": "overdue",
        "customer": {"id": "1001", "name": "Acme Test Co", "active": True},
    }


def _run(declines, invoices, tickets=None):
    benji = FakeBenji(declines=declines, invoices={"1001": invoices})
    halo = FakeHalo(tickets=tickets or [])
    result = process_customer(
        benji=benji,
        halo=halo,
        accounting_id="1001",
        halo_client_id=501,
        customer_name="Acme Test Co",
        invoice_age_days=10,
        dry_run=True,
        today=TODAY,
        set_credit_hold=False,
        ticket_type_id=TICKET_TYPE_ID,
        app_url=APP_URL,
    )
    return result, halo


def test_zero_declines_with_aged_invoice_is_noop(declined_by_customer):
    result, halo = _run(declines={"1001": []}, invoices=[_aged_invoice()])
    assert result["action_taken"] == "NOOP_NO_DECLINES"
    assert result["decline_count"] == 0
    assert halo.created == []
    assert "1001" in declined_by_customer


def test_one_decline_passes_the_gate(declined_by_customer):
    one = declined_by_customer["1001"][:1]
    result, _halo = _run(declines={"1001": one}, invoices=[_aged_invoice()])
    assert result["declines_found"] is True
    assert result["decline_count"] == 1
    assert result["action_taken"] == "WOULD_CREATE"


def test_summary_caps_at_ten_and_count_is_full():
    rows = []
    for i in range(12):
        rows.append(
            {
                "id": f"txn-{i}",
                "transactionDate": "2026-10-01",
                "amount": i + 1,
                "currency": "USD",
                "invoiceNumber": "INV-1001",
                "invoiceId": "inv-acme-aged",
                "result": "DECLINED",
                "customerName": "Acme Test Co",
                "details": {"message": f"reason {i}"},
            }
        )
    sample = summarize_declines(rows, limit=10)
    assert len(sample) == 10
    assert sample[0]["message"] == "reason 0"
    result, _halo = _run(declines={"1001": rows}, invoices=[_aged_invoice()])
    assert result["decline_count"] == 12
    assert len(result["declines_sample"]) == 10


def test_missing_message_falls_back_to_result(declined_by_customer):
    row = declined_by_customer["1001"][1]
    sample = summarize_declines([row])
    assert sample[0]["message"] is None or sample[0]["message"] == ""
    assert sample[0]["result"] == "DECLINED"
    result, _halo = _run(declines={"1001": [row]}, invoices=[_aged_invoice()])
    assert result["action_taken"] == "WOULD_CREATE"


def test_declines_without_aged_invoice_noop_aged_first(declined_by_customer, open_invoices):
    young = next(i for i in open_invoices if i["id"] == "inv-nine-days")
    young = dict(young)
    young["customer"] = {"id": "1001", "name": "Acme Test Co", "active": True}
    result, halo = _run(
        declines={"1001": declined_by_customer["1001"]},
        invoices=[young],
    )
    assert result["action_taken"] == "NOOP_NO_AGED_INVOICE"
    assert result["decline_count"] == 2
    assert halo.created == []
