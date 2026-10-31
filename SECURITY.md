# Security

## Reporting a vulnerability

Report privately. Use GitHub private vulnerability reporting on this repository (Security, then Report a vulnerability). A Benji Pays admin has to enable private vulnerability reporting in the repository settings. Do not open a public GitHub issue for a security report.

If private reporting is not available yet, contact a Benji Pays org admin directly. Do not send the report to a public channel.

## Keys and secrets

Never paste a Benji Pays API key, a Halo client secret, or an access token into an issue, a pull request, a log, or a chat.

If you already exposed a key:

1. Revoke or rotate it in Benji Pays or Halo.
2. Then send the private report. The report can name the file and the commit. It does not need the key itself.

The sample reads secrets from the environment or from a local `.env` file. `.env` is gitignored. `.env.example` has empty secret fields on purpose.

Do not add a second secret store, a personal path, or a committed credential file.

## What the sample can change

With `--apply`, the sample creates Halo tickets. With `--apply --set-credit-hold`, it also sets a client custom field. Run a dry-run first. Use a Halo application and a Benji Pays key that belong to the tenant you mean to change.
