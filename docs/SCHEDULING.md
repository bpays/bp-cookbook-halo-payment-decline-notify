# Scheduling

Run a dry-run in a terminal before you put `--apply` on a schedule. Read `WOULD_CREATE` and `UNMAPPED`. Fix `accountsid` on the Halo clients you care about. Then turn on apply.

The process working directory must be the folder that contains `.env`, because the sample loads `.env` from the current directory. File mode `600` on `.env` keeps the keys readable only by that user.

Do not put the API key in the cron command. Leave it in `.env`.

Stdout includes customer names and invoice numbers. Send cron mail only to people who should see that list.

## cron

Daily at 07:00, server local time. Credit hold stays off:

```bash
0 7 * * * cd /opt/bp-decline-notify && python3 -m decline_notify --all --apply
```

Same schedule, and set `CFCreditHold` when a ticket is created:

```bash
0 7 * * * cd /opt/bp-decline-notify && python3 -m decline_notify --all --apply --set-credit-hold
```

A daily dry-run, if you want a person to apply by hand:

```bash
0 7 * * * cd /opt/bp-decline-notify && python3 -m decline_notify --all
```

## Windows Task Scheduler

Create a daily task that starts in the folder with `.env`:

```text
Program: py
Arguments: -m decline_notify --all --apply
Start in: C:\bp-decline-notify
```

`py -m` uses the Python launcher. If `py` is not on the task's PATH, use the full path to `python.exe`.

## Time zone

`--invoice-age-days` uses `TIMEZONE` in `.env`. UTC is the default. Set an IANA name such as `America/Chicago` if you want the day boundary to follow that region. The due date is a calendar date. The sample does not convert it to a timestamp.
