# Policy

This is the policy the script implements.

## Trigger

All of these must be true:

1. The invoice is in the Benji Pays open list (`GET /v2/invoices?status=open`). That list includes unpaid invoices that are past due. A row whose own `status` is `overdue` still counts.
2. Age is days past `dueDate`, not days since `invoiceDate`. `days past due = today - dueDate`, using `TIMEZONE` (default UTC). The default minimum is 10. The due date itself is included when you set `--invoice-age-days 0`.
3. `balance` is greater than 0. A missing balance counts as 0 and does not qualify. A missing or unreadable due date does not qualify.
4. `GET /v2/transactions?status=declined&customerId={accountingCustomerId}` returns at least one row.

The accounting customer id comes from `customer.id` on the invoice. That is the same id you store in Halo `accountsid`.

Declines are counted for the customer, including declines that are not on the aged invoice. There is no date window. If you need "declines in the last 90 days", that is a change to the sample, not current behavior.

## Actions

| Action | Default | What the script does |
|--------|---------|----------------------|
| Open a Payment Decline ticket | On, when you pass `--apply` | Creates one ticket. Dry-run prints `WOULD_CREATE` and writes nothing. |
| Skip when a ticket is already open | Always | Any open ticket of the Payment Decline type for that client blocks a new one. |
| Set `CFCreditHold` | Off | Pass `--set-credit-hold` with `--apply`. The field is set to true after the ticket is created. |

The script does not resolve the ticket when the balance is paid. It does not set `CFCreditHold` back to false. Run it again after you close the ticket if you want a new one.

## Join

Default match field: `accountsid`.

Also tried, in order, if you leave the defaults: `BenjiCustomerId`, `AccountingId`, then `accountsid` again. The first Halo client with that value wins.

Client name is not used unless you pass `--allow-name-match`. Two customers can share a similar name. Leave name matching off unless you have checked the hits.

## Not this sample

- A balance rule with no decline check. Halo can do that from accounting data alone.
- Creating invoices in Benji Pays. Benji Pays does not create the accounting invoice.
- Slack notifications.
- A Halo runbook condition as the only gate. See [halo-integration/README.md](halo-integration/README.md).
