# Halo Custom Integration (optional)

Use the Python sample in this repo as the path that applies the policy. The notes here are optional packaging if you want a Benji Pays method inside Halo for a manual lookup.

## Known limit

In testing, a Halo Integration Runbook **Condition** on a variable mapped from a list count did not evaluate reliably. A condition such as "decline count >= 1", where the count is mapped from the list response, can pass when the list is empty or fail when the list has rows.

Do not use that condition as the gate that decides whether to open a Payment Decline ticket. Do not claim that a runbook condition on a mapped count implements this policy.

The agent-side script is the reliable path. It counts aged invoices and declined transactions in Python, then creates the Halo ticket itself.

## What a Custom Integration is good for

- A manual "list open invoices" or "list declines" call from inside Halo, so an agent can look.
- Storing the Benji Pays API key in the Halo integration credential, encrypted, instead of in a ticket.

It is not a substitute for the age gate, the decline gate, or open-ticket dedupe. If you import methods, re-enter the API key in the Halo UI. Do not put the key in the JSON file.

## If you still build a runbook

Keep it as a thin caller, or do not build it. A runbook that only lists declines and stops is safe, because it does not decide. A runbook that creates tickets based on a mapped count is not safe.

Flow you can copy into a design doc, with the decision still made by the script:

1. Run `python -m decline_notify --all` on a schedule.
2. Let the script create the ticket and, if you asked, set `CFCreditHold`.

There is no importable runbook in this repo. Tenant-specific runbook ids and method ids from one Halo site do not belong in a public sample. Rebuild methods from [methods.md](methods.md) and [benji-pays-methods.example.json](benji-pays-methods.example.json). After import, bind them to your integration and paste your own API key.

## Slack

This sample does not post to Slack. Add that in your own process if you need it. Do not commit a webhook URL.
