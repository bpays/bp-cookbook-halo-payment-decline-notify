# Contributing

Issues and pull requests are welcome.

## Access

This repository is public. You can open issues, fork it, and send pull requests.

Do not push to `main`. Benji Pays org admins review pull requests and merge to `main`. Branch protection on `main` (require a pull request, require the `tests` check, no direct pushes) is an admin setting in GitHub. It is not something this sample turns on by itself.

## How to send a change

1. Fork the repository.
2. Create a branch from `main`.
3. Make the change.
4. Run `pytest -q` and `python scripts/public_scan.py`.
5. Open a pull request against `main`.

If you are a Benji Pays admin, use a branch and a pull request as well. Merge in GitHub after the tests pass.

## What not to include

- API keys, OAuth client secrets, `.env` files, or Halo tokens.
- Customer names, invoice exports, ticket ids from a live tenant, or run JSON from `data/`.
- A hard-coded Halo ticket type id. Tenants do not share ids.

Fixtures in `tests/fixtures/` use made-up companies. Keep them that way.

## Writing

Write "Benji Pays" in prose. Do not shorten the product name.

Use short sentences and the second person in docs. Do not use em dashes. Do not invent prices or metrics.

## Tests

Add or update a fixture test when you change a gate: aged invoice, decline, client match, or the create/skip decision. Tests must not call the live APIs.
