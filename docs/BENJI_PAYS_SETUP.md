# Benji Pays setup

## API key

Create an organization API key in Benji Pays. The sample sends it as the `x-api-key` header. Put it in `BENJI_PAYS_API_KEY`. Do not commit it.

The key needs these scopes:

- `organizations:invoices:read`
- `organizations:transactions:read`

A 403 body that says a scope is missing means the key cannot read that resource. A 401 means the key is missing or not valid.

## Calls this sample makes

| Call | Why |
|------|-----|
| `GET /v2/invoices?status=open` | Find unpaid invoices, including ones that are past due. |
| `GET /v2/transactions?status=declined&customerId=` | Count declined payments for one accounting customer id. |

Both calls are paginated. The sample asks for `limit=1000` (the API maximum) and follows `pagination.nextOffset` while `hasMore` is true.

`customerId` and invoice `customer.id` are the accounting system customer id (QuickBooks, Xero, Business Central, or QuickBooks Desktop). Store that value in Halo `accountsid`.

The default API host is `https://api.benjipays.com`. <!-- // pragma: allowlist secret -->
Override it with `BENJI_PAYS_API_URL` only if Benji Pays gives you a different host.

## Customer link

Ticket details include an HTML link:

`{BENJI_PAYS_APP_URL}/app/customers/s/{accountingCustomerId}`

The default app host is `https://app.benjipays.com`. <!-- // pragma: allowlist secret -->
Open one link after a dry-run preview (the URL is in the ticket body the script would send). If it 404s, set `BENJI_PAYS_APP_URL` to the host you actually use. The path stays `/app/customers/s/{id}`.

## What Benji Pays does not do here

Benji Pays does not create the Halo ticket. Benji Pays does not create the accounting invoice. The invoice already exists in the accounting system. Benji Pays is where the declined payment shows up.
