"""Command line for the Benji Pays payment-decline notify sample."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfoNotFoundError

from decline_notify.benji_pays_client import ApiError, Client
from decline_notify.config import Settings, SettingsError, load_dotenv, load_settings
from decline_notify.halo_client import HaloClient
from decline_notify.policy import (
    build_client_indexes,
    group_aged_customers,
    match_halo_client,
    now_label,
    process_customer,
    today_in,
)

DATA_DIR = Path("data")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Open a Halo Payment Decline ticket when a Benji Pays customer has "
            "an open invoice aged at least N days and at least one declined payment. "
            "Dry-run unless you pass --apply."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--all",
        action="store_true",
        help="Scan every open Benji Pays invoice and apply the policy per customer.",
    )
    mode.add_argument(
        "--customer",
        metavar="ACCT_ID",
        help="Benji Pays accounting customer id. Requires --halo-client.",
    )
    parser.add_argument(
        "--halo-client",
        type=int,
        metavar="ID",
        help="Halo client id. Required with --customer.",
    )
    parser.add_argument(
        "--customer-name",
        default="",
        help="Name to print on the ticket. Default: Benji Pays or Halo client name.",
    )
    parser.add_argument(
        "--invoice-age-days",
        type=int,
        default=10,
        help="Minimum days past the invoice due date. Default: 10.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create tickets in Halo. Without this flag the run only reports.",
    )
    parser.add_argument(
        "--set-credit-hold",
        action="store_true",
        help="Also set the Halo credit-hold field when a ticket is created.",
    )
    parser.add_argument(
        "--allow-name-match",
        action="store_true",
        help="With --all, match a Halo client by name if accountsid is missing. Off by default.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Also write the result JSON to this path.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write the default data/*.json file. --json-out still writes.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.customer is not None and args.halo_client is None:
        parser.error("--customer requires --halo-client")
    if args.all and args.halo_client is not None:
        parser.error("--halo-client cannot be used with --all")
    if args.invoice_age_days < 0:
        parser.error("--invoice-age-days must be >= 0")
    return args


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote: {path}")


def _ticket_type_id(halo: HaloClient, settings: Settings) -> int | None:
    if settings.ticket_type_id is not None:
        return settings.ticket_type_id
    found = halo.resolve_ticket_type_id(settings.ticket_type_name)
    if found is None:
        print(
            f"ERROR: Halo ticket type {settings.ticket_type_name!r} was not found. "
            "Create it, or set HALO_PAYMENT_DECLINE_TICKET_TYPE_ID.",
            file=sys.stderr,
        )
        return None
    return found


def _count_action(counts: dict[str, int], result: dict[str, Any]) -> None:
    action = result.get("action_taken") or "UNKNOWN"
    if result.get("declines_found"):
        counts["with_declines"] += 1
    if action == "WOULD_CREATE":
        counts["would_create"] += 1
    elif action == "CREATE":
        counts["create"] += 1
    elif action == "SKIP":
        counts["skip"] += 1
    elif action in ("NOOP_NO_DECLINES", "NOOP_NO_AGED_INVOICE"):
        counts["noop"] += 1
    elif action == "UNMAPPED":
        counts["unmapped"] += 1
    elif action == "ERROR":
        counts["errors"] += 1
    else:
        counts["other"] += 1


def _print_summary(counts: dict[str, int]) -> None:
    print("=== batch summary ===")
    for key in (
        "open_invoices_fetched",
        "candidates_aged",
        "with_declines",
        "would_create",
        "create",
        "skip",
        "noop",
        "unmapped",
        "errors",
        "other",
    ):
        print(f"  {key}: {counts.get(key, 0)}")


def run_all(
    *,
    args: argparse.Namespace,
    settings: Settings,
    benji: Client,
    halo: HaloClient,
    ticket_type_id: int,
    today,
) -> int:
    dry_run = not args.apply
    print(f"=== decline notify --all ({'dry-run' if dry_run else 'apply'}) ===")
    print(f"tested_at: {now_label(settings.timezone)}")
    print(f"invoice_age_days: {args.invoice_age_days}")
    print(f"set_credit_hold: {args.set_credit_hold}")

    print("Fetching open Benji Pays invoices...")
    open_invoices = benji.list_all_open_invoices()
    print(f"open_invoices_fetched: {len(open_invoices)}")

    aged_customers = group_aged_customers(open_invoices, today, args.invoice_age_days)
    print(f"customers_aged_ge_{args.invoice_age_days}d: {len(aged_customers)}")

    print("Loading Halo clients for accountsid match...")
    clients = halo.list_clients()
    by_id, by_name = build_client_indexes(
        clients,
        settings.client_match_field,
        settings.client_match_fallbacks,
    )
    print(f"halo_clients_indexed: {len(clients)} (match keys={len(by_id)})")

    counts: dict[str, int] = defaultdict(int)
    counts["open_invoices_fetched"] = len(open_invoices)
    counts["candidates_aged"] = len(aged_customers)
    results: list[dict[str, Any]] = []

    for acct_id, entry in sorted(aged_customers.items(), key=lambda item: item[0]):
        name = entry.get("customerName") or acct_id
        matched, match_how = match_halo_client(
            acct_id,
            name,
            by_id,
            by_name,
            allow_name_match=args.allow_name_match,
        )
        if matched is None:
            row = {
                "accountingCustomerId": acct_id,
                "customerName": name,
                "aged_open_invoice_count": len(entry["aged_invoices"]),
                "action_taken": "UNMAPPED",
                "skipped_reason": "No Halo client matched the accounting customer id.",
                "match_how": match_how,
            }
            results.append(row)
            _count_action(counts, row)
            print(f"  UNMAPPED acct={acct_id} name={name!r} aged={len(entry['aged_invoices'])}")
            continue

        halo_client_id = int(matched["id"])
        try:
            result = process_customer(
                benji=benji,
                halo=halo,
                accounting_id=acct_id,
                halo_client_id=halo_client_id,
                customer_name=name,
                invoice_age_days=args.invoice_age_days,
                dry_run=dry_run,
                today=today,
                set_credit_hold=args.set_credit_hold,
                ticket_type_id=ticket_type_id,
                credit_hold_field=settings.credit_hold_field,
                app_url=settings.benji_pays_app_url,
                open_invoices=entry["open_invoices"],
                aged_invoices=entry["aged_invoices"],
                client=matched,
            )
            result["match_how"] = match_how
        except Exception as exc:  # noqa: BLE001 - one customer must not stop the scan
            result = {
                "accountingCustomerId": acct_id,
                "customerName": name,
                "haloClientId": halo_client_id,
                "aged_open_invoice_count": len(entry["aged_invoices"]),
                "action_taken": "ERROR",
                "skipped_reason": str(exc)[:500],
                "match_how": match_how,
            }
        results.append(result)
        _count_action(counts, result)
        print(
            f"  {result.get('action_taken')} acct={acct_id} halo={halo_client_id} "
            f"name={name!r} declines={result.get('decline_count')} "
            f"aged={result.get('aged_open_invoice_count')}"
        )

    batch = {
        "tested_at": now_label(settings.timezone),
        "mode": "dry-run" if dry_run else "apply",
        "scope": "all",
        "invoice_age_days": args.invoice_age_days,
        "set_credit_hold": args.set_credit_hold,
        "allow_name_match": args.allow_name_match,
        "counts": dict(counts),
        "results": results,
    }
    _print_summary(counts)
    if not args.no_write:
        _dump(DATA_DIR / "decline-notify-all-latest.json", batch)
    if args.json_out is not None:
        _dump(args.json_out, batch)
    return 1 if counts.get("errors") else 0


def run_one(
    *,
    args: argparse.Namespace,
    settings: Settings,
    benji: Client,
    halo: HaloClient,
    ticket_type_id: int,
    today,
) -> int:
    dry_run = not args.apply
    try:
        result = process_customer(
            benji=benji,
            halo=halo,
            accounting_id=str(args.customer).strip(),
            halo_client_id=int(args.halo_client),
            customer_name=(args.customer_name or "").strip(),
            invoice_age_days=args.invoice_age_days,
            dry_run=dry_run,
            today=today,
            set_credit_hold=args.set_credit_hold,
            ticket_type_id=ticket_type_id,
            credit_hold_field=settings.credit_hold_field,
            app_url=settings.benji_pays_app_url,
        )
    except ApiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - report and stop this one customer
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    result["tested_at"] = now_label(settings.timezone)
    result["mode"] = "dry-run" if dry_run else "apply"
    print("=== decline notify result ===")
    print(f"tested_at:           {result.get('tested_at')}")
    print(f"mode:                {result.get('mode')}")
    print(f"customer:            {result.get('customer')}")
    print(f"declines_found:      {result.get('declines_found')} (count={result.get('decline_count')})")
    print(
        f"aged_open_invoices:  {result.get('aged_open_invoice_count')} "
        f"(>= {result.get('aged_open_invoices_ge_days')}d)"
    )
    print(f"open_pd_before:      {result.get('open_pd_tickets_before')}")
    print(f"action_taken:        {result.get('action_taken')}")
    print(f"ticket_id:           {result.get('ticket_id')}")
    print(f"CFCreditHold_before: {result.get('CFCreditHold_before')}")
    print(f"CFCreditHold_after:  {result.get('CFCreditHold_after')}")
    if result.get("skipped_reason"):
        print(f"skipped_reason:      {result.get('skipped_reason')}")
    if not args.no_write:
        _dump(DATA_DIR / "decline-notify-latest.json", result)
    if args.json_out is not None:
        _dump(args.json_out, result)
    if result.get("action_taken") == "ERROR":
        print(f"ERROR: {result.get('skipped_reason')}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_dotenv(Path.cwd() / ".env", os.environ)
    try:
        settings = load_settings(os.environ)
    except SettingsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    try:
        today = today_in(settings.timezone)
        now_label(settings.timezone)
    except ZoneInfoNotFoundError:
        print("ERROR: TIMEZONE is not a valid IANA timezone name.", file=sys.stderr)
        return 2

    benji = Client(settings.benji_pays_api_key, settings.benji_pays_api_url)
    try:
        halo = HaloClient()
        ticket_type_id = _ticket_type_id(halo, settings)
        if ticket_type_id is None:
            return 2
        if args.all:
            return run_all(
                args=args,
                settings=settings,
                benji=benji,
                halo=halo,
                ticket_type_id=ticket_type_id,
                today=today,
            )
        return run_one(
            args=args,
            settings=settings,
            benji=benji,
            halo=halo,
            ticket_type_id=ticket_type_id,
            today=today,
        )
    except ApiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
