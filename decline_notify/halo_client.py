"""Thin Halo PSA REST client. OAuth2 client credentials. Credentials come from the environment."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


REQUIRED_ENV = (
    "HALO_RESOURCE_URL",
    "HALO_AUTH_URL",
    "HALO_CLIENT_ID",
    "HALO_CLIENT_SECRET",
)


def missing_halo_env() -> list[str]:
    missing = []
    for name in REQUIRED_ENV:
        if not os.environ.get(name, "").strip():
            missing.append(name)
    return missing


def custom_field_value(client: dict[str, Any], field_name: str) -> Any:
    """Read a custom field by name (case-insensitive) from a Halo client dict."""
    target = (field_name or "").strip().lower()
    if not target:
        return None
    fields = client.get("customfields") or client.get("custom_fields") or []
    if isinstance(fields, list):
        for field in fields:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name") or field.get("label") or "").strip().lower()
            if name == target:
                return field.get("value")
    for key, val in client.items():
        if str(key).lower() == target:
            return val
    return None


class HaloClient:
    """Minimal Halo API wrapper. Tokens stay in memory for this process."""

    def __init__(self) -> None:
        missing = missing_halo_env()
        if missing:
            raise RuntimeError(
                "Halo API is not configured. Set these environment variables: "
                + ", ".join(missing)
            )
        self.resource_url = os.environ["HALO_RESOURCE_URL"].rstrip("/")
        self.auth_url = os.environ["HALO_AUTH_URL"].rstrip("/")
        self.client_id = os.environ["HALO_CLIENT_ID"].strip()
        self.client_secret = os.environ["HALO_CLIENT_SECRET"].strip()
        self.tenant = os.environ.get("HALO_TENANT", "").strip() or None
        self.scope = os.environ.get("HALO_SCOPE", "all").strip() or "all"
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def get_token(self, *, force: bool = False) -> str:
        now = time.time()
        if not force and self._token and now < (self._token_expires_at - 60):
            return self._token

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }
        body = urllib.parse.urlencode(data).encode("utf-8")
        url = self.auth_url
        if not url.rstrip("/").endswith("token"):
            url = url.rstrip("/") + "/token"

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Halo auth HTTP {exc.code}: {err}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Halo auth network failure: {exc}") from exc

        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Halo auth response missing access_token.")
        expires_in = int(payload.get("expires_in") or 3600)
        self._token = str(token)
        self._token_expires_at = now + expires_in
        return self._token

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
        path = path if path.startswith("/") else f"/{path}"
        query: dict[str, Any] = {}
        if self.tenant:
            query["tenant"] = self.tenant
        if params:
            for key, value in params.items():
                if value is not None:
                    query[key] = value
        qs = ("?" + urllib.parse.urlencode({k: str(v) for k, v in query.items()})) if query else ""
        return f"{self.resource_url}{path}{qs}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any = None,
        timeout: int = 120,
    ) -> Any:
        token = self.get_token()
        data = None
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        url = self._url(path, params)
        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                if not raw.strip():
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                token = self.get_token(force=True)
                headers["Authorization"] = f"Bearer {token}"
                req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        raw = resp.read().decode("utf-8")
                        if not raw.strip():
                            return None
                        return json.loads(raw)
                except urllib.error.HTTPError as exc2:
                    err = exc2.read().decode("utf-8", errors="replace")[:500]
                    raise RuntimeError(f"Halo HTTP {exc2.code} {method} {path}: {err}") from exc2
            err = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Halo HTTP {exc.code} {method} {path}: {err}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Halo network failure {method} {path}: {exc}") from exc

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: Any, params: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, params=params, body=body)

    def list_clients(self, *, page_size: int = 100) -> list[dict[str, Any]]:
        clients: list[dict[str, Any]] = []
        page_no = 1
        while True:
            params = {
                "pageinate": "true",
                "page_size": page_size,
                "page_no": page_no,
                "includeinactive": "false",
                "include_custom_fields": True,
            }
            rows = _extract_rows(self.get("/Client", params=params))
            clients.extend(rows)
            if not rows or len(rows) < page_size:
                break
            page_no += 1
            if page_no > 500:
                print("WARNING: Halo client pagination safety stop", file=sys.stderr)
                break
        return clients

    def get_client(self, client_id: int | str) -> dict[str, Any] | None:
        body = self.get(f"/Client/{client_id}", params={"include_custom_fields": True})
        if isinstance(body, list) and body:
            return body[0] if isinstance(body[0], dict) else None
        if isinstance(body, dict):
            return body
        return None

    def update_client_custom_fields(self, client_id: int, fields: dict[str, Any]) -> Any:
        customfields = [{"name": name, "value": value} for name, value in fields.items()]
        payload = [{"id": int(client_id), "customfields": customfields}]
        return self.post("/Client", payload)

    def list_ticket_types(self) -> list[dict[str, Any]]:
        return _extract_rows(self.get("/TicketType"))

    def resolve_ticket_type_id(self, name: str) -> int | None:
        target = (name or "").strip().lower()
        if not target:
            return None
        for ticket_type in self.list_ticket_types():
            type_name = str(
                ticket_type.get("name") or ticket_type.get("tickettype_name") or ""
            ).strip().lower()
            if type_name == target:
                tid = ticket_type.get("id") or ticket_type.get("tickettype_id")
                if tid is not None:
                    return int(tid)
        return None

    def create_ticket(self, ticket: dict[str, Any]) -> dict[str, Any]:
        body = self.post("/Tickets", [ticket])
        if isinstance(body, list) and body:
            return body[0] if isinstance(body[0], dict) else {"raw": body[0]}
        if isinstance(body, dict):
            if "id" in body:
                return body
            tickets = body.get("tickets") or body.get("data")
            if isinstance(tickets, list) and tickets:
                return tickets[0]
            return body
        raise RuntimeError("Unexpected Halo create_ticket response.")

    def find_tickets_for_client(
        self,
        client_id: int,
        *,
        open_only: bool = True,
        search: str | None = None,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        tickets: list[dict[str, Any]] = []
        page_no = 1
        while True:
            params: dict[str, Any] = {
                "client_id": int(client_id),
                "pageinate": "true",
                "page_size": page_size,
                "page_no": page_no,
            }
            if open_only:
                params["open_only"] = "true"
            if search:
                params["search"] = search
            rows = _extract_rows(self.get("/Tickets", params=params))
            tickets.extend(rows)
            if len(rows) < page_size:
                break
            page_no += 1
            if page_no > 200:
                print("WARNING: Halo ticket pagination safety stop", file=sys.stderr)
                break
        return tickets


def _extract_rows(body: Any) -> list[dict[str, Any]]:
    if body is None:
        return []
    if isinstance(body, list):
        return [row for row in body if isinstance(row, dict)]
    if isinstance(body, dict):
        for key in ("clients", "tickets", "tickettypes", "actions", "data", "record"):
            rows = body.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        if "id" in body:
            return [body]
    return []
