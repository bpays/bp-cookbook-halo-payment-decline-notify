# Troubleshooting

## `Missing required settings`

The message lists variable names only. Copy `.env.example` to `.env`, fill in the blanks, and run the command from that directory. A variable that is already exported, even as an empty string, is not replaced by `.env`.

## `UNMAPPED`

`--all` found an aged open invoice and no Halo client with that id in `accountsid` (or the fallback fields). Put the accounting customer id on the Halo client. Do not turn on `--allow-name-match` to hide this until you have checked that the names are unique.

## `NOOP_NO_DECLINES`

The invoice is old enough and the balance is above 0, and Benji Pays returned no `status=declined` transactions for that customer id. Confirm the id you stored in `accountsid` is `customer.id` from the invoice, not an internal database id from another system.

## `NOOP_NO_AGED_INVOICE`

No open invoice has a due date at least N days ago with a balance above 0. Check `TIMEZONE` and `--invoice-age-days`. Age uses `dueDate`, not `invoiceDate`.

## `SKIP` on the first run

An open Payment Decline ticket already exists for that client. Close it in Halo if you need a new one, then run again. This sample does not close tickets.

## Halo 401

The token request failed, or Halo rejected the bearer token. Check `HALO_AUTH_URL`, `HALO_CLIENT_ID`, `HALO_CLIENT_SECRET`, and `HALO_SCOPE`. The auth URL should be the Halo auth host. The sample appends `/token` if the URL does not already end in `token`.

## Halo 403

The application authenticated and is not allowed to make that call. Add the missing client, ticket, or custom-field permission, then try again.

## Benji Pays 401 or 403

401: `BENJI_PAYS_API_KEY` is missing or not valid.

403: the key is missing `organizations:invoices:read` or `organizations:transactions:read`, or the key owner cannot read that data. The response `detail` says which case it is. Do not paste that response into a public issue if it contains customer data. The `detail` line for a missing scope does not contain the key.

## Ticket type was not found

Halo has no ticket type with the configured name. Create `Payment Decline`, or set `HALO_PAYMENT_DECLINE_TICKET_TYPE` to the name you use. Alternatively set `HALO_PAYMENT_DECLINE_TICKET_TYPE_ID` to the id from this tenant only.

## `ERROR` for one customer during `--all`

The scan keeps going. The summary count `errors` is the number of customers that failed. The row's `skipped_reason` is the message. A Benji Pays or Halo error for one customer does not roll back tickets already created earlier in that run.

## Pagination stopped

A safety stop means the API kept returning full pages past the limit (100 pages for Benji Pays, 200 pages of tickets, 500 pages of clients). Treat that as a fault, not as a complete scan.
