"""Shared fixtures for policy tests. No network."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 10, 31)
TICKET_TYPE_ID = 101
APP_URL = "https://app.example.test"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def today() -> date:
    return TODAY


@pytest.fixture
def open_invoices() -> list[dict]:
    return load_fixture("invoices_open.json")


@pytest.fixture
def declined_by_customer() -> dict:
    return load_fixture("transactions_declined.json")


@pytest.fixture
def halo_clients() -> list[dict]:
    return load_fixture("halo_clients.json")


@pytest.fixture
def halo_tickets() -> list[dict]:
    return load_fixture("halo_tickets_open.json")


class FakeBenji:
    def __init__(self, declines=None, invoices=None, boom_on=None):
        self.declines = declines or {}
        self.invoices = invoices or {}
        self.boom_on = boom_on
        self.decline_calls: list[str] = []

    def list_declines(self, accounting_customer_id: str) -> list[dict]:
        cid = str(accounting_customer_id)
        self.decline_calls.append(cid)
        if self.boom_on is not None and cid == self.boom_on:
            raise RuntimeError("boom")
        return list(self.declines.get(cid, []))

    def list_open_invoices(self, accounting_customer_id: str) -> list[dict]:
        return list(self.invoices.get(str(accounting_customer_id), []))


class FakeHalo:
    def __init__(self, client=None, tickets=None, create_result=None):
        self.client = client or {
            "id": 501,
            "name": "Acme Test Co",
            "customfields": [{"name": "CFCreditHold", "value": False}],
        }
        self.tickets = list(tickets or [])
        self.create_result = {"id": 4242} if create_result is None else create_result
        self.created: list[dict] = []
        self.updated: list[tuple] = []

    def get_client(self, client_id):
        return self.client

    def find_tickets_for_client(self, client_id, open_only=True):
        return list(self.tickets)

    def create_ticket(self, ticket):
        self.created.append(ticket)
        return self.create_result

    def update_client_custom_fields(self, client_id, fields):
        self.updated.append((client_id, dict(fields)))
        cfs = self.client.setdefault("customfields", [])
        for name, value in fields.items():
            for cf in cfs:
                if str(cf.get("name", "")).lower() == str(name).lower():
                    cf["value"] = value
                    break
            else:
                cfs.append({"name": name, "value": value})
        return {"id": client_id}
