"""Environment settings. Secrets stay in the environment or a local .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# Public API and app hosts. Override with BENJI_PAYS_API_URL / BENJI_PAYS_APP_URL.
DEFAULT_API_URL = "https://api.benjipays.com"  # pragma: allowlist secret
DEFAULT_APP_URL = "https://app.benjipays.com"  # pragma: allowlist secret

REQUIRED_SETTING_NAMES = (
    "BENJI_PAYS_API_KEY",
    "HALO_RESOURCE_URL",
    "HALO_AUTH_URL",
    "HALO_CLIENT_ID",
    "HALO_CLIENT_SECRET",
)

DEFAULT_MATCH_FALLBACKS = ("BenjiCustomerId", "AccountingId", "accountsid")


class SettingsError(Exception):
    """Raised when required settings are missing or malformed. Message has names only."""


@dataclass
class Settings:
    benji_pays_api_key: str
    benji_pays_api_url: str
    benji_pays_app_url: str
    halo_resource_url: str
    halo_auth_url: str
    halo_client_id: str
    halo_client_secret: str
    halo_tenant: str | None
    halo_scope: str
    ticket_type_name: str
    ticket_type_id: int | None
    credit_hold_field: str
    client_match_field: str
    client_match_fallbacks: list[str]
    timezone: str

    def __repr__(self) -> str:
        return "Settings(secrets redacted)"


def load_dotenv(path: Path, environ: dict) -> None:
    """Load KEY=value lines into environ. Existing keys are left unchanged."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if key and key not in environ:
            environ[key] = value


def _raw(environ: Mapping[str, str], name: str) -> str:
    return str(environ.get(name, "")).strip()


def missing_setting_names(environ: Mapping[str, str]) -> list[str]:
    missing = []
    for name in REQUIRED_SETTING_NAMES:
        if not _raw(environ, name):
            missing.append(name)
    return missing


def format_missing(names: list[str]) -> str:
    return "Missing required settings: " + ", ".join(names)


def _optional(environ: Mapping[str, str], name: str, default: str) -> str:
    value = _raw(environ, name)
    return value if value else default


def load_settings(
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> Settings:
    if environ is None:
        env: dict[str, str] = os.environ  # type: ignore[assignment]
    else:
        env = environ  # type: ignore[assignment]
    if dotenv_path is not None:
        load_dotenv(dotenv_path, env)  # type: ignore[arg-type]

    missing = missing_setting_names(env)
    if missing:
        raise SettingsError(format_missing(missing))

    ticket_type_raw = _raw(env, "HALO_PAYMENT_DECLINE_TICKET_TYPE_ID")
    ticket_type_id: int | None
    if ticket_type_raw:
        try:
            ticket_type_id = int(ticket_type_raw)
        except ValueError as exc:
            raise SettingsError(
                "HALO_PAYMENT_DECLINE_TICKET_TYPE_ID must be an integer."
            ) from exc
    else:
        ticket_type_id = None

    fallback_raw = _raw(env, "HALO_CLIENT_MATCH_FALLBACKS")
    if fallback_raw:
        fallbacks = [part.strip() for part in fallback_raw.split(",") if part.strip()]
    else:
        fallbacks = list(DEFAULT_MATCH_FALLBACKS)

    tenant = _raw(env, "HALO_TENANT")
    return Settings(
        benji_pays_api_key=_raw(env, "BENJI_PAYS_API_KEY"),
        benji_pays_api_url=_optional(env, "BENJI_PAYS_API_URL", DEFAULT_API_URL),
        benji_pays_app_url=_optional(env, "BENJI_PAYS_APP_URL", DEFAULT_APP_URL),
        halo_resource_url=_raw(env, "HALO_RESOURCE_URL"),
        halo_auth_url=_raw(env, "HALO_AUTH_URL"),
        halo_client_id=_raw(env, "HALO_CLIENT_ID"),
        halo_client_secret=_raw(env, "HALO_CLIENT_SECRET"),
        halo_tenant=tenant or None,
        halo_scope=_optional(env, "HALO_SCOPE", "all"),
        ticket_type_name=_optional(env, "HALO_PAYMENT_DECLINE_TICKET_TYPE", "Payment Decline"),
        ticket_type_id=ticket_type_id,
        credit_hold_field=_optional(env, "HALO_CREDIT_HOLD_FIELD", "CFCreditHold"),
        client_match_field=_optional(env, "HALO_CLIENT_MATCH_FIELD", "accountsid"),
        client_match_fallbacks=fallbacks,
        timezone=_optional(env, "TIMEZONE", "UTC"),
    )
