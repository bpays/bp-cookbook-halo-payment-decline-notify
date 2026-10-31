"""Benji Pays list client for open invoices and declined transactions.

Auth is the x-api-key header. The key is never included in error text.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ApiError(RuntimeError):
    """Benji Pays API call failed. The message does not include the API key."""


class Client:
    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = ""
        if params:
            clean = {key: value for key, value in params.items() if value is not None}
            query = "?" + urllib.parse.urlencode({key: str(value) for key, value in clean.items()})
        url = f"{self.base_url}{path}{query}"
        req = urllib.request.Request(
            url,
            headers={"x-api-key": self._api_key, "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")[:500]
            raise ApiError(f"Benji Pays HTTP {exc.code} {path}: {err}") from exc
        except urllib.error.URLError as exc:
            raise ApiError(f"Benji Pays network failure {path}: {exc}") from exc

    def paginate(self, path: str, params: dict[str, Any] | None = None, *, limit: int = 1000) -> list[dict[str, Any]]:
        params = dict(params or {})
        params["limit"] = limit
        rows: list[dict[str, Any]] = []
        offset = 0
        pages = 0
        while True:
            params["offset"] = offset
            body = self._get(path, params)
            chunk = body.get("data") or []
            if not isinstance(chunk, list):
                raise ApiError(f"Unexpected Benji Pays response shape for {path}")
            rows.extend(row for row in chunk if isinstance(row, dict))
            pages += 1
            pagination = body.get("pagination") or {}
            if not pagination.get("hasMore") or not chunk:
                break
            next_offset = pagination.get("nextOffset")
            offset = int(next_offset) if next_offset is not None else offset + limit
            if pages > 100:
                raise ApiError(f"Benji Pays pagination safety stop on {path}")
        return rows

    def list_declines(self, accounting_customer_id: str) -> list[dict[str, Any]]:
        return self.paginate(
            "/v2/transactions",
            {
                "status": "declined",
                "customerId": str(accounting_customer_id),
                "sort": "transactionDate",
                "order": "desc",
            },
        )

    def list_open_invoices(self, accounting_customer_id: str) -> list[dict[str, Any]]:
        return self.paginate(
            "/v2/invoices",
            {
                "status": "open",
                "customerId": str(accounting_customer_id),
                "sort": "dueDate",
                "order": "asc",
            },
        )

    def list_all_open_invoices(self) -> list[dict[str, Any]]:
        return self.paginate(
            "/v2/invoices",
            {
                "status": "open",
                "sort": "dueDate",
                "order": "asc",
            },
        )
