"""Grouping open invoices and Halo client matching. No network."""

from decline_notify.halo_client import custom_field_value
from decline_notify.policy import (
    build_client_indexes,
    group_aged_customers,
    invoice_accounting_customer_id,
    match_halo_client,
)

from tests.conftest import TODAY


def test_group_keeps_customers_with_an_aged_invoice_only(open_invoices):
    grouped = group_aged_customers(open_invoices, TODAY, 10)
    assert set(grouped) == {"1001"}
    assert grouped["1001"]["customerName"] == "Acme Test Co"
    numbers = {row["invoiceNumber"] for row in grouped["1001"]["aged_invoices"]}
    assert numbers == {"INV-1001", "INV-1000"}


def test_invoice_without_customer_id_is_skipped():
    inv = {
        "id": "x",
        "invoiceNumber": "INV-X",
        "dueDate": "2026-01-01",
        "balance": 10,
        "customer": {},
    }
    assert invoice_accounting_customer_id(inv) is None
    assert group_aged_customers([inv], TODAY, 10) == {}


def test_accountsid_match_wins_and_fallback_field_matches(halo_clients):
    by_id, by_name = build_client_indexes(halo_clients)
    client, how = match_halo_client("1001", "Someone Else", by_id, by_name)
    assert how == "custom_field"
    assert client["id"] == 501
    fallback, how_fb = match_halo_client("2002", "Nope", by_id, by_name)
    assert how_fb == "custom_field"
    assert fallback["id"] == 502


def test_name_match_requires_allow_name_match(halo_clients):
    by_id, by_name = build_client_indexes(halo_clients)
    missed, how = match_halo_client("9999", "Name Only Co", by_id, by_name)
    assert missed is None
    assert how == "unmatched"
    found, how_name = match_halo_client(
        "9999",
        "  name   only co ",
        by_id,
        by_name,
        allow_name_match=True,
    )
    assert how_name == "name"
    assert found["id"] == 503


def test_custom_field_lookup_is_case_insensitive(halo_clients):
    case_client = next(c for c in halo_clients if c["id"] == 504)
    assert custom_field_value(case_client, "accountsid") == "3003"
    assert custom_field_value(case_client, "ACCOUNTSID") == "3003"
    top = next(c for c in halo_clients if c["id"] == 505)
    assert custom_field_value(top, "accountsid") == "4004"
    by_id, _by_name = build_client_indexes(halo_clients)
    assert by_id["3003"]["id"] == 504
    assert by_id["4004"]["id"] == 505
