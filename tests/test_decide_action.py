"""Action decision and Halo writes. Fakes only. No network."""

from decline_notify.policy import decide_action, process_customer, process_customers

from tests.conftest import APP_URL, TODAY, TICKET_TYPE_ID, FakeBenji, FakeHalo


def _invoice():
    return {
        "id": "inv-1",
        "invoiceNumber": "INV-1001",
        "dueDate": "2026-10-01",
        "balance": 25.0,
        "currency": "USD",
        "status": "overdue",
        "customer": {"id": "1001", "name": "Acme Test Co", "active": True},
    }


def _decline():
    return {
        "id": "txn-1",
        "transactionDate": "2026-10-20",
        "amount": 25.0,
        "currency": "USD",
        "invoiceNumber": "INV-1001",
        "invoiceId": "inv-1",
        "result": "DECLINED",
        "customerName": "Acme Test Co",
        "details": {"message": "Card declined"},
    }


def _process(halo, *, dry_run=True, set_credit_hold=False, declines=None, invoices=None):
    benji = FakeBenji(
        declines={"1001": [_decline()] if declines is None else declines},
        invoices={"1001": [_invoice()] if invoices is None else invoices},
    )
    return process_customer(
        benji=benji,
        halo=halo,
        accounting_id="1001",
        halo_client_id=501,
        customer_name="Acme Test Co",
        invoice_age_days=10,
        dry_run=dry_run,
        today=TODAY,
        set_credit_hold=set_credit_hold,
        ticket_type_id=TICKET_TYPE_ID,
        credit_hold_field="CFCreditHold",
        app_url=APP_URL,
    )


def test_open_payment_decline_ticket_skips(halo_tickets):
    decision = decide_action(
        aged=[{"invoiceNumber": "INV-1001"}],
        declines_found=True,
        open_pd_ticket_ids=[9001],
        dry_run=True,
        set_credit_hold=True,
        invoice_age_days=10,
    )
    assert decision["action"] == "SKIP"
    halo = FakeHalo(tickets=halo_tickets)
    result = _process(halo)
    assert result["action_taken"] == "SKIP"
    assert result["ticket_id"] == 9001
    assert halo.created == []
    assert halo.updated == []


def test_other_open_ticket_type_does_not_skip(halo_tickets):
    other = [t for t in halo_tickets if t["tickettype_id"] != TICKET_TYPE_ID]
    halo = FakeHalo(tickets=other)
    result = _process(halo, dry_run=True)
    assert result["action_taken"] == "WOULD_CREATE"
    assert halo.created == []


def test_dry_run_would_create_writes_nothing():
    halo = FakeHalo(tickets=[])
    result = _process(halo, dry_run=True, set_credit_hold=True)
    assert result["action_taken"] == "WOULD_CREATE"
    assert result["ticket_id"] is None
    assert halo.created == []
    assert halo.updated == []
    assert "would set" in str(result["CFCreditHold_after"]).lower()


def test_apply_sets_hold_only_when_requested():
    halo_hold = FakeHalo(tickets=[])
    created = _process(halo_hold, dry_run=False, set_credit_hold=True)
    assert created["action_taken"] == "CREATE"
    assert created["ticket_id"] == 4242
    assert len(halo_hold.created) == 1
    assert halo_hold.created[0]["tickettype_id"] == TICKET_TYPE_ID
    assert halo_hold.created[0]["client_id"] == 501
    assert halo_hold.updated == [(501, {"CFCreditHold": True})]
    assert created["CFCreditHold_after"] is True

    halo_plain = FakeHalo(tickets=[])
    plain = _process(halo_plain, dry_run=False, set_credit_hold=False)
    assert plain["action_taken"] == "CREATE"
    assert halo_plain.created
    assert halo_plain.updated == []
    assert plain["CFCreditHold_after"] is False


def test_create_without_id_is_error_and_does_not_set_hold():
    halo = FakeHalo(tickets=[], create_result={"ok": True})
    result = _process(halo, dry_run=False, set_credit_hold=True)
    assert result["action_taken"] == "ERROR"
    assert result["ticket_id"] is None
    assert halo.updated == []


def test_batch_continues_after_one_customer_error():
    class BoomBenji(FakeBenji):
        def list_declines(self, accounting_customer_id: str):
            if str(accounting_customer_id) == "bad":
                raise RuntimeError("boom")
            return super().list_declines(accounting_customer_id)

    benji = BoomBenji(
        declines={"1001": [_decline()]},
        invoices={"1001": [_invoice()], "bad": [_invoice()]},
    )
    halo = FakeHalo(tickets=[])
    results = process_customers(
        [
            {
                "accounting_id": "bad",
                "halo_client_id": 1,
                "customer_name": "Bad Co",
            },
            {
                "accounting_id": "1001",
                "halo_client_id": 501,
                "customer_name": "Acme Test Co",
            },
        ],
        benji=benji,
        halo=halo,
        invoice_age_days=10,
        dry_run=True,
        today=TODAY,
        set_credit_hold=False,
        ticket_type_id=TICKET_TYPE_ID,
        app_url=APP_URL,
    )
    assert [r["action_taken"] for r in results] == ["ERROR", "WOULD_CREATE"]
    assert "boom" in results[0]["skipped_reason"]
