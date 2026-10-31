"""Ticket summary and details. No network."""

from decline_notify.ticket import build_summary, build_ticket_details, customer_url


def test_customer_name_and_gateway_message_are_escaped():
    details = build_ticket_details(
        customer_name='Acme <script>alert("x")</script>',
        accounting_customer_id="1001",
        halo_client_id=501,
        declines=[
            {
                "transactionDate": "2026-10-20",
                "invoiceNumber": "INV-1",
                "currency": "USD",
                "amount": 10,
                "message": 'failed & "no"',
                "result": "DECLINED",
            }
        ],
        aged_invoices=[
            {
                "invoiceNumber": "INV-1",
                "dueDate": "2026-10-01",
                "currency": "USD",
                "balance": 10,
                "daysPastDue": 30,
            }
        ],
        invoice_age_days=10,
        app_url="https://app.example.test",
    )
    assert "<script>" not in details
    assert "&lt;script&gt;" in details
    assert "failed &amp;" in details
    assert "&quot;no&quot;" in details
    assert 'rel="noopener"' in details


def test_deep_link_uses_app_url_and_encodes_id():
    url = customer_url("https://app.example.test/", "10/01")
    assert url == "https://app.example.test/app/customers/s/10%2F01"
    details = build_ticket_details(
        customer_name="Acme Test Co",
        accounting_customer_id="10/01",
        halo_client_id=7,
        declines=[],
        aged_invoices=[],
        invoice_age_days=10,
        app_url="https://app.example.test",
    )
    assert "https://app.example.test/app/customers/s/10%2F01" in details


def test_summary_has_no_em_dash():
    summary = build_summary("Acme Test Co", 2)
    assert summary == "Payment Decline: Acme Test Co (2 declines)"
    assert "\u2014" not in summary
    assert "\u2013" not in summary
