"""Policy gates for aged invoices, declines, client match, and ticket dedupe.

The gate helpers do not open sockets. process_customer calls the benji and halo
objects you pass in.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from decline_notify.config import DEFAULT_APP_URL
from decline_notify.halo_client import custom_field_value
from decline_notify.ticket import build_summary, build_ticket_details

DEFAULT_MATCH_FALLBACKS = ["BenjiCustomerId", "AccountingId", "accountsid"]


def parse_day(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def days_past_due(due: date | None, today: date) -> int | None:
    if due is None:
        return None
    return (today - due).days


def _balance(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def aged_open_invoices(
    invoices: list[dict[str, Any]],
    today: date,
    min_age_days: int,
) -> list[dict[str, Any]]:
    aged = []
    for inv in invoices:
        due = parse_day(inv.get("dueDate"))
        past_due = days_past_due(due, today)
        balance = _balance(inv.get("balance"))
        if past_due is not None and past_due >= min_age_days and balance > 0.00001:
            aged.append(
                {
                    "invoiceNumber": inv.get("invoiceNumber"),
                    "invoiceId": inv.get("id"),
                    "dueDate": inv.get("dueDate"),
                    "balance": inv.get("balance"),
                    "currency": inv.get("currency"),
                    "status": inv.get("status"),
                    "daysPastDue": past_due,
                }
            )
    return aged


def invoice_accounting_customer_id(inv: dict[str, Any]) -> str | None:
    """Accounting customer id from an invoice row.

    Benji Pays list payloads put that id on customer.id. The same value is
    the Halo accountsid and the customerId query on declined transactions.
    """
    customer = inv.get("customer") or {}
    if not isinstance(customer, dict):
        customer = {}
    acct = (
        customer.get("accountingCustomerId")
        or customer.get("accounting_customer_id")
        or inv.get("accountingCustomerId")
        or inv.get("accounting_customer_id")
        or customer.get("id")
    )
    if acct is None or acct == "":
        return None
    return str(acct).strip()


def invoice_customer_name(inv: dict[str, Any]) -> str | None:
    customer = inv.get("customer") or {}
    if isinstance(customer, dict) and customer.get("name"):
        return str(customer["name"])
    if inv.get("customerName"):
        return str(inv["customerName"])
    return None


def group_aged_customers(
    invoices: list[dict[str, Any]],
    today: date,
    min_age_days: int,
) -> dict[str, dict[str, Any]]:
    """Group open invoices by accounting customer id. Keep aged customers only."""
    by_acct: dict[str, dict[str, Any]] = {}
    for inv in invoices:
        acct = invoice_accounting_customer_id(inv)
        if not acct:
            continue
        if acct not in by_acct:
            by_acct[acct] = {
                "accountingCustomerId": acct,
                "customerName": invoice_customer_name(inv) or acct,
                "open_invoices": [],
                "aged_invoices": [],
            }
        entry = by_acct[acct]
        name = invoice_customer_name(inv)
        if name:
            entry["customerName"] = name
        entry["open_invoices"].append(inv)

    aged_only: dict[str, dict[str, Any]] = {}
    for acct, entry in by_acct.items():
        aged = aged_open_invoices(entry["open_invoices"], today, min_age_days)
        if not aged:
            continue
        entry["aged_invoices"] = aged
        aged_only[acct] = entry
    return aged_only


def summarize_declines(rows: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    out = []
    for txn in rows[:limit]:
        details = txn.get("details") if isinstance(txn.get("details"), dict) else {}
        message = details.get("message") if isinstance(details, dict) else None
        out.append(
            {
                "id": txn.get("id"),
                "transactionDate": txn.get("transactionDate"),
                "amount": txn.get("amount"),
                "currency": txn.get("currency"),
                "invoiceNumber": txn.get("invoiceNumber"),
                "invoiceId": txn.get("invoiceId"),
                "message": message,
                "result": txn.get("result"),
                "customerName": txn.get("customerName"),
            }
        )
    return out


def _norm_name(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def build_client_indexes(
    clients: list[dict[str, Any]],
    match_field: str = "accountsid",
    fallbacks: list[str] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return (by custom-field value, by normalized client name). First client wins."""
    by_id_field: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    fields: list[str] = []
    for field in [match_field, *(fallbacks if fallbacks is not None else DEFAULT_MATCH_FALLBACKS)]:
        field = (field or "").strip()
        if field and field.lower() not in {item.lower() for item in fields}:
            fields.append(field)

    for client in clients:
        name_key = _norm_name(client.get("name") or client.get("client_name"))
        if name_key and name_key not in by_name:
            by_name[name_key] = client
        for field in fields:
            val = custom_field_value(client, field)
            if val is None or val == "":
                continue
            key = str(val).strip()
            if key and key not in by_id_field:
                by_id_field[key] = client
    return by_id_field, by_name


def match_halo_client(
    accounting_customer_id: str,
    customer_name: str | None,
    by_id_field: dict[str, dict[str, Any]],
    by_name: dict[str, dict[str, Any]],
    allow_name_match: bool = False,
) -> tuple[dict[str, Any] | None, str]:
    sid = str(accounting_customer_id).strip()
    if sid in by_id_field:
        return by_id_field[sid], "custom_field"
    if allow_name_match:
        name_key = _norm_name(customer_name)
        if name_key and name_key in by_name:
            return by_name[name_key], "name"
    return None, "unmatched"


def open_payment_decline_ids(tickets: list[dict[str, Any]], ticket_type_id: int) -> list[int]:
    found: list[int] = []
    for ticket in tickets:
        raw = ticket.get("tickettype_id")
        if raw is None:
            raw = ticket.get("tickettype")
        try:
            type_id = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            type_id = None
        if type_id != int(ticket_type_id):
            continue
        if ticket.get("id") is None:
            continue
        try:
            found.append(int(ticket["id"]))
        except (TypeError, ValueError):
            continue
    return found


def decide_action(
    *,
    aged: list[Any],
    declines_found: bool,
    open_pd_ticket_ids: list[int],
    dry_run: bool,
    set_credit_hold: bool,
    invoice_age_days: int,
) -> dict[str, Any]:
    """Choose the action. Does not call Halo."""
    if not aged:
        return {
            "action": "NOOP_NO_AGED_INVOICE",
            "skipped_reason": (
                f"No open invoices aged >= {invoice_age_days} days with balance > 0"
            ),
            "should_create": False,
            "should_set_hold": False,
        }
    if not declines_found:
        return {
            "action": "NOOP_NO_DECLINES",
            "skipped_reason": "No declined Benji Pays transactions for this customer",
            "should_create": False,
            "should_set_hold": False,
        }
    if open_pd_ticket_ids:
        return {
            "action": "SKIP",
            "skipped_reason": (
                f"Open Payment Decline ticket already exists: {open_pd_ticket_ids}"
            ),
            "should_create": False,
            "should_set_hold": False,
        }
    return {
        "action": "WOULD_CREATE" if dry_run else "CREATE",
        "skipped_reason": None,
        "should_create": not dry_run,
        "should_set_hold": (not dry_run) and set_credit_hold,
    }


def now_label(timezone_name: str) -> str:
    tz = ZoneInfo(timezone_name)
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")


def today_in(timezone_name: str) -> date:
    return datetime.now(ZoneInfo(timezone_name)).date()


def process_customer(
    *,
    benji,
    halo,
    accounting_id: str,
    halo_client_id: int,
    customer_name: str,
    invoice_age_days: int,
    dry_run: bool,
    today: date,
    set_credit_hold: bool = False,
    ticket_type_id: int,
    credit_hold_field: str = "CFCreditHold",
    app_url: str = DEFAULT_APP_URL,
    open_invoices: list[dict[str, Any]] | None = None,
    aged_invoices: list[dict[str, Any]] | None = None,
    client: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply the policy for one customer. benji and halo are small client objects."""
    declines_raw = benji.list_declines(str(accounting_id))
    declines = summarize_declines(declines_raw)
    declines_found = len(declines_raw) >= 1

    if open_invoices is None:
        open_invoices = benji.list_open_invoices(str(accounting_id))
    if aged_invoices is None:
        aged_invoices = aged_open_invoices(open_invoices, today, invoice_age_days)

    if client is None:
        client = halo.get_client(halo_client_id) or {}
    if not customer_name:
        customer_name = (
            (declines[0].get("customerName") if declines else None)
            or client.get("name")
            or f"customer {accounting_id}"
        )
    hold_before = custom_field_value(client, credit_hold_field)
    open_ids = open_payment_decline_ids(
        halo.find_tickets_for_client(halo_client_id, open_only=True),
        ticket_type_id,
    )
    decision = decide_action(
        aged=aged_invoices,
        declines_found=declines_found,
        open_pd_ticket_ids=open_ids,
        dry_run=dry_run,
        set_credit_hold=set_credit_hold,
        invoice_age_days=invoice_age_days,
    )

    result: dict[str, Any] = {
        "accountingCustomerId": str(accounting_id),
        "customer": {
            "accountingCustomerId": str(accounting_id),
            "haloClientId": halo_client_id,
            "name": customer_name,
        },
        "declines_found": declines_found,
        "decline_count": len(declines_raw),
        "declines_sample": declines,
        "open_invoices_total": len(open_invoices),
        "aged_open_invoices_ge_days": invoice_age_days,
        "aged_open_invoice_count": len(aged_invoices),
        "aged_open_invoices": aged_invoices,
        "open_pd_tickets_before": open_ids,
        "open_pd_count_before": len(open_ids),
        "credit_hold_field": credit_hold_field,
        "CFCreditHold_before": hold_before,
        "action_taken": decision["action"],
        "ticket_id": open_ids[0] if open_ids and decision["action"] == "SKIP" else None,
        "CFCreditHold_after": hold_before,
        "skipped_reason": decision["skipped_reason"],
        "set_credit_hold": set_credit_hold,
    }

    if decision["action"] != "WOULD_CREATE" and decision["action"] != "CREATE":
        return result

    details = build_ticket_details(
        customer_name=customer_name,
        accounting_customer_id=str(accounting_id),
        halo_client_id=halo_client_id,
        declines=declines,
        aged_invoices=aged_invoices,
        invoice_age_days=invoice_age_days,
        app_url=app_url,
    )
    summary = build_summary(customer_name, len(declines_raw))
    ticket_payload = {
        "tickettype_id": int(ticket_type_id),
        "client_id": int(halo_client_id),
        "summary": summary,
        "details": details,
    }

    if decision["action"] == "WOULD_CREATE":
        result["ticket_payload_preview"] = {
            "tickettype_id": ticket_payload["tickettype_id"],
            "client_id": ticket_payload["client_id"],
            "summary": summary,
            "details_len": len(details),
        }
        if set_credit_hold:
            result["CFCreditHold_after"] = "True (would set)"
        return result

    created = halo.create_ticket(ticket_payload)
    created_id = created.get("id") if isinstance(created, dict) else None
    if created_id is None:
        result["action_taken"] = "ERROR"
        result["ticket_id"] = None
        result["skipped_reason"] = "Halo create_ticket returned no id."
        result["CFCreditHold_after"] = hold_before
        return result

    created_id = int(created_id)
    result["ticket_id"] = created_id
    result["created_ticket"] = {"id": created_id, "summary": summary}

    if set_credit_hold:
        halo.update_client_custom_fields(halo_client_id, {credit_hold_field: True})
        client_after = halo.get_client(halo_client_id) or {}
        result["CFCreditHold_after"] = custom_field_value(client_after, credit_hold_field)
    else:
        result["CFCreditHold_after"] = hold_before

    result["action_taken"] = "CREATE"
    open_after = open_payment_decline_ids(
        halo.find_tickets_for_client(halo_client_id, open_only=True),
        ticket_type_id,
    )
    result["open_pd_tickets_after"] = open_after
    result["open_pd_count_after"] = len(open_after)
    return result


def process_customers(entries: list[dict[str, Any]], **shared: Any) -> list[dict[str, Any]]:
    """Run process_customer for each entry. One failure does not stop the rest."""
    results: list[dict[str, Any]] = []
    for entry in entries:
        try:
            results.append(process_customer(**shared, **entry))
        except Exception as exc:  # noqa: BLE001 - batch must continue
            results.append(
                {
                    "accountingCustomerId": entry.get("accounting_id"),
                    "action_taken": "ERROR",
                    "skipped_reason": str(exc)[:500],
                }
            )
    return results
