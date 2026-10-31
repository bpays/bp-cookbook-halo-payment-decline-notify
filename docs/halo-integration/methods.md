# Method notes

Base URL for every Benji Pays method: the `BENJI_PAYS_API_URL` value in `.env.example` (the public Benji Pays API host).

Auth on the integration: API key header `x-api-key`. Paste the key in the Halo UI after you create the integration. The example JSON does not contain a key.

Halo's `limit` on these calls should be `1000` or less. `1000` is the API maximum. If `pagination.hasMore` is true, call again with `offset` set to `pagination.nextOffset`.

## List open invoices for one customer

- Method: `GET /v2/invoices`
- Query: `status=open`, `customerId={{accountingCustomerId}}`, `limit=1000`, `sort=dueDate`, `order=asc`
- Header: `Accept: application/json`

Use `customer.id` from each row as the accounting customer id. Use `dueDate`, `balance`, `invoiceNumber`, and `currency` in the ticket body. Compute days past due in the script, not in a runbook condition.

`status=open` returns every unpaid invoice. A row can still show `status: overdue`.

## List open invoices for the whole organization

Same path and headers, without `customerId`. This is what `--all` does. Group rows by `customer.id` in the script.

## List declined transactions for one customer

- Method: `GET /v2/transactions`
- Query: `status=declined`, `customerId={{accountingCustomerId}}`, `limit=1000`, `sort=transactionDate`, `order=desc`

`customerId` is the accounting customer id, the same value as Halo `accountsid`. At least one row means the decline gate passes. The script does not filter these rows by date.

Gateway text is `details.message`. If that is empty, the script prints `result` on the ticket.

## Find the Halo client

Prefer a Halo client search on custom field `accountsid` = the accounting customer id.

Outputs you need: client `id`, client `name`, current `CFCreditHold`.

If nothing matches, stop. Do not create a ticket with no client. The script records `UNMAPPED` and continues.

## Create the Payment Decline ticket

Only when the script's policy says create, and no open Payment Decline ticket exists for that client.

| Field | Value |
|-------|-------|
| Ticket type | Payment Decline (your tenant's id) |
| Client | Halo client id |
| Summary | `Payment Decline: {name} ({n} declines)` |
| Details | Decline lines, aged invoice lines, and the Benji Pays customer link |
| Status | The type's default new status |

The script escapes customer names, invoice numbers, and gateway messages before it puts them in the HTML body.

## Set CFCreditHold

Only when `--set-credit-hold` is on and a ticket was created.

Update the client. Set custom field `CFCreditHold` to `true`. Do not send the rest of the client payload if Halo would overwrite other fields. The sample posts `id` plus the `customfields` array only.

The sample never sets the field back to false.
