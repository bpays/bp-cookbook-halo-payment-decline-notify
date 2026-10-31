# Live demo (about 8 minutes)

Use a Halo tenant you are allowed to change, and a Benji Pays organization you are allowed to read. Use one test customer. Do not demo against a customer you would not show on a webinar slide.

## Before you start

- `.env` is loaded and is not on screen. Close any editor tab that has the key in it.
- The test Halo client has `accountsid` set to the Benji Pays accounting customer id.
- Ticket type Payment Decline exists. `CFCreditHold` exists if you will show the hold.
- You have run `--all` once already so you know whether the test customer is `WOULD_CREATE` or `SKIP`.
- If the test customer is already `SKIP`, close that Payment Decline ticket in Halo before the demo if you want to show a create. Closing the ticket is a manual step. This sample does not close it.
- Terminal font is large. `data/` may contain customer names. Do not scroll a full JSON dump on the projector if the dry-run includes real customers. Prefer a single test tenant.

## Script

### 0:00 What Halo cannot see

Show a declined payment in Benji Pays. Say that Halo can see an open balance from accounting, and that the decline itself is only in Benji Pays. This sample opens a Halo ticket when both are true: an invoice is at least 10 days past due, and Benji Pays has a declined payment.

### 1:00 Halo setup

Open the test client. Show `accountsid`. Open the ticket type Payment Decline. If you will set the hold, show `CFCreditHold` still false.

### 2:00 Dry-run

```bash
python3 -m decline_notify --all
```

Read the summary counts out loud: open invoices fetched, customers aged, would_create, skip, unmapped. Point at one `WOULD_CREATE` line. Say what `UNMAPPED` means: the accounting id is not on a Halo client yet.

### 4:30 One customer on purpose

If you do not want the org-wide list on screen, run the test customer only:

```bash
python3 -m decline_notify --customer YOUR_ACCOUNTING_ID --halo-client YOUR_HALO_CLIENT_ID
```

The action should be `WOULD_CREATE`. Mention the ticket summary shape: `Payment Decline: {name} ({n} declines)`.

### 5:30 Apply for that one customer

```bash
python3 -m decline_notify --customer YOUR_ACCOUNTING_ID --halo-client YOUR_HALO_CLIENT_ID --apply
```

Open the new ticket in Halo. Show the decline lines and the Benji Pays link. Skip this step if you are not willing to leave a ticket behind. Dry-run alone is a complete demo.

Optional, only if `CFCreditHold` exists and you want to show it:

```bash
python3 -m decline_notify --customer YOUR_ACCOUNTING_ID --halo-client YOUR_HALO_CLIENT_ID --apply --set-credit-hold
```

Use that form on the first apply, not after a ticket already exists. A second apply will `SKIP` and will not set the field.

### 7:00 Dedupe

Run the apply command again. The action is `SKIP`, and the ticket id is the one you just opened.

### 8:00 How an MSP runs it

Show [docs/SCHEDULING.md](docs/SCHEDULING.md): a daily dry-run or `--apply` from cron, with `.env` kept out of git. Point at the fork and pull request path in [CONTRIBUTING.md](CONTRIBUTING.md). If someone asks about building this only inside Halo, say the script is the reliable gate, and open [docs/halo-integration/README.md](docs/halo-integration/README.md).

## After the demo

Close the demo ticket if you do not want it left open. Clear `CFCreditHold` on the test client if you set it. Delete `data/*.json` if it contains customers you do not want on that machine.
