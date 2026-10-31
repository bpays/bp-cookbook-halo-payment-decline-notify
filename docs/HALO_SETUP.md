# Halo setup

Do this in the Halo tenant the sample will call.

## 1. Ticket type

Create a ticket type named `Payment Decline`. Agents should be able to see it. You do not need to show it on the end-user portal.

The sample looks up the id by that name (`HALO_PAYMENT_DECLINE_TICKET_TYPE`). If your type has a different name, set the env var to your name. If you already know the id for this tenant, set `HALO_PAYMENT_DECLINE_TICKET_TYPE_ID` instead. Ids are not the same from one Halo tenant to another. Do not reuse an id from a screenshot or from another MSP.

## 2. Credit hold field

Create a client custom field named `CFCreditHold`. Use a yes/no (checkbox) field. The sample writes `true` only when you pass `--set-credit-hold`.

If you already have a different field name, set `HALO_CREDIT_HOLD_FIELD` to that name.

This field does not block new tickets by itself. If you want Halo to stop new work while the flag is true, add that rule in Halo. This sample only sets the field.

## 3. accountsid

Create or reuse a client custom field named `accountsid`. Set it to the accounting customer id. That is the same value as `customer.id` on a Benji Pays invoice.

Customers with no `accountsid` show up as `UNMAPPED` in `--all`. The sample does not create a Halo client for them.

Optional fallback field names, if you already store the id under a different label: `BenjiCustomerId`, `AccountingId`. Change the list with `HALO_CLIENT_MATCH_FALLBACKS` (comma-separated).

## 4. API application

In Halo, create an API application that uses client credentials.

Copy these into `.env`:

| Variable | Where it comes from |
|----------|---------------------|
| `HALO_RESOURCE_URL` | API base URL, usually `https://YOUR_TENANT.halopsa.com/api` |
| `HALO_AUTH_URL` | Auth base URL, usually `https://YOUR_TENANT.halopsa.com/auth` |
| `HALO_CLIENT_ID` | Application client id |
| `HALO_CLIENT_SECRET` | Application secret |
| `HALO_TENANT` | Only if your Halo site requires a tenant query parameter |
| `HALO_SCOPE` | `all`, unless your application uses a narrower scope that still allows the calls below |

The application needs to:

- read clients, including custom fields
- read tickets
- create tickets
- update a client custom field (only if you use `--set-credit-hold`)

Halo permission labels vary by version. If a call returns 403, add the missing permission and request a new token. A 401 on the token URL means the client id, secret, or auth URL is wrong.

## 5. Smoke test

```bash
python3 -m decline_notify --customer YOUR_ACCOUNTING_ID --halo-client YOUR_HALO_CLIENT_ID
```

Expect `WOULD_CREATE`, `SKIP`, `NOOP_NO_DECLINES`, or `NOOP_NO_AGED_INVOICE`. Expect no new ticket until you add `--apply`.
