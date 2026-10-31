# Demo: payment decline notify for Halo

This outline is for managed service provider (MSP) engineers and Halo admins.

Halo can see open receivables from accounting. Only Benji Pays sees that a payment was declined. Connect the two so support gets a Payment Decline ticket. Setting the Halo client field `CFCreditHold` is optional. You have three ways to do that. The policy is the same in each one.

Policy, in one line: an open Benji Pays invoice is at least 10 days past due, the balance is above 0, and Benji Pays has at least one declined payment for that customer. Then open one Halo Payment Decline ticket. If that client already has an open ticket of that type, skip. Set `CFCreditHold` only if you want the hold.

You do not build a runbook on stage. You can flash one that is already finished.

## 1. Grok Bot / agent (little or no code)

Use this when you want the policy run for you, without owning a script.

1. Connect Benji Pays and Halo to the bot. Keep the API key and the Halo client secret in the bot's secret store. Do not paste them into the chat.
2. Give the bot the policy above. Name the Halo ticket type Payment Decline. Say that `CFCreditHold` is opt-in.
3. Ask for a dry-run first. Read which customers it would ticket. Then tell it to apply.
4. If you want it every day, ask the bot to run on a schedule.

The point: this is the same policy as the sample in this repo. The bot runs it for you.

This is a setup sketch, not a Grok Bot install guide.

## 2. Cookbook script on a schedule

Use this when you want a command you can read, hand to an agent, or put on a clock.

1. Clone this repo.
2. Copy `.env.example` to `.env` and fill in your Benji Pays key and Halo application. Do not commit `.env`.
3. Dry-run: `python3 -m decline_notify --all`
4. When the dry-run looks right, run the same command with `--apply`. Add `--set-credit-hold` only if you want the hold.
5. Put that command on cron, Task Scheduler, or any other runner. See [docs/SCHEDULING.md](docs/SCHEDULING.md).

Flags, actions, and the `accountsid` join are in [README.md](README.md).

The point: give the script to an agent or a scheduler and run it regularly. This repo is the copy you can hand over.

## 3. Finished Halo Integration Runbook (show, do not build)

Use this when you want the lookup and the ticket create to live inside Halo.

A Halo Custom Integration holds the Benji Pays methods (open invoices, declined payments). A thin runbook creates the Payment Decline ticket and, if you ask, sets `CFCreditHold`.

Do not rely on a Halo flow chart Condition that gates on a mapped list count. That includes a decline count and an open ticket count. Those conditions were unreliable in testing. They can pass when the list is empty, or fail when it has rows. Do not use them as the gate that decides to open a ticket.

Method notes, and what a runbook is good for, are in [docs/halo-integration/](docs/halo-integration/README.md). They are optional. Halo import shapes differ by version. This repo does not claim a one-click import that works on every tenant. After any import, you still paste your own Benji Pays API key in the Halo UI.

Webinar tip: show a runbook you already finished, or a Payment Decline ticket that already exists. Do not build the runbook live.

## What to say on stage

- All three ways use one policy. Benji Pays supplies the decline. Halo supplies the ticket.
- Dry-run before anything creates tickets. A second run should skip a client that already has an open Payment Decline ticket.
- `CFCreditHold` is optional. None of these ways clear it for you when the customer pays. An agent does that.
- The script in this repo is the version you can read and schedule. The runbook is a finished picture of the same idea, not a list-count condition you should trust.
- The join is the Halo client field `accountsid`. It must be the Benji Pays accounting customer id. If it is empty, the customer does not match.
