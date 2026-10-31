"""Halo ticket summary and HTML details. Dynamic text is escaped."""

from __future__ import annotations

from html import escape
from urllib.parse import quote
from typing import Any


def customer_url(app_url: str, accounting_customer_id: str) -> str:
    base = app_url.rstrip("/")
    acct = quote(str(accounting_customer_id), safe="")
    return f"{base}/app/customers/s/{acct}"


def build_summary(customer_name: str, decline_count: int) -> str:
    return f"Payment Decline: {customer_name} ({decline_count} declines)"


def build_ticket_details(
    *,
    customer_name: str,
    accounting_customer_id: str,
    halo_client_id: int,
    declines: list[dict[str, Any]],
    aged_invoices: list[dict[str, Any]],
    invoice_age_days: int,
    app_url: str,
) -> str:
    lines = [
        f"Payment decline detected for {escape(customer_name)}.",
        "",
        (
            "Source: Benji Pays "
            f"(accountingCustomerId={escape(str(accounting_customer_id))} "
            f"/ Halo client {halo_client_id})."
        ),
        f"Declined transactions found: {len(declines)}.",
    ]
    for row in declines[:5]:
        msg = row.get("message") or row.get("result") or ""
        lines.append(
            "- "
            + escape(str(row.get("transactionDate") or ""))
            + " INV "
            + escape(str(row.get("invoiceNumber") or ""))
            + " "
            + escape(str(row.get("currency") or ""))
            + " "
            + escape(str(row.get("amount") or ""))
            + " "
            + escape(str(msg))
        )
    if aged_invoices:
        lines.append("")
        lines.append(f"Open invoices aged >= {invoice_age_days} days: {len(aged_invoices)}")
        for inv in aged_invoices[:10]:
            lines.append(
                "- #"
                + escape(str(inv.get("invoiceNumber") or ""))
                + " due "
                + escape(str(inv.get("dueDate") or ""))
                + " "
                + escape(str(inv.get("currency") or ""))
                + " "
                + escape(str(inv.get("balance") or ""))
                + f" ({inv.get('daysPastDue')}d)"
            )
    url = customer_url(app_url, accounting_customer_id)
    lines.append("")
    lines.append(
        f'<p><a href="{escape(url, quote=True)}" target="_blank" rel="noopener">'
        "Open customer in Benji Pays</a></p>"
    )
    return "\n".join(lines)
