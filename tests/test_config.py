"""Settings loading. No network."""

from decline_notify.config import format_missing, load_dotenv, load_settings, missing_setting_names


REQUIRED_OK = {
    "BENJI_PAYS_API_KEY": "test-key",
    "HALO_RESOURCE_URL": "https://YOUR_TENANT.halopsa.com/api",
    "HALO_AUTH_URL": "https://YOUR_TENANT.halopsa.com/auth",
    "HALO_CLIENT_ID": "client-id",
    "HALO_CLIENT_SECRET": "client-secret",
}


def test_missing_settings_names_values_are_not_in_the_message():
    planted = "planted-value-should-not-leak"
    env = {"BENJI_PAYS_API_KEY": planted}
    missing = missing_setting_names(env)
    message = format_missing(missing)
    assert "HALO_CLIENT_SECRET" in missing
    assert "HALO_RESOURCE_URL" in missing
    assert "BENJI_PAYS_API_KEY" not in missing
    assert planted not in message
    assert "test-key" not in message


def test_dotenv_does_not_override_existing_env(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# comment",
                "export BENJI_PAYS_API_KEY=from-file",
                "HALO_TENANT=from-file",
                "",
            ]
        ),
        encoding="utf-8",
    )
    env = {"BENJI_PAYS_API_KEY": "from-env"}
    load_dotenv(env_file, env)
    assert env["BENJI_PAYS_API_KEY"] == "from-env"
    assert env["HALO_TENANT"] == "from-file"


def test_defaults_when_optional_settings_are_unset():
    settings = load_settings(dict(REQUIRED_OK), dotenv_path=None)
    assert settings.benji_pays_api_url == "https://api.benjipays.com"  # pragma: allowlist secret
    assert settings.benji_pays_app_url == "https://app.benjipays.com"  # pragma: allowlist secret
    assert settings.timezone == "UTC"
    assert settings.credit_hold_field == "CFCreditHold"
    assert settings.ticket_type_name == "Payment Decline"
    assert settings.ticket_type_id is None
    assert settings.client_match_field == "accountsid"
    assert settings.halo_scope == "all"
    assert "BenjiCustomerId" in settings.client_match_fallbacks


def test_blank_required_value_counts_as_missing():
    env = dict(REQUIRED_OK)
    env["HALO_CLIENT_SECRET"] = "   "
    assert "HALO_CLIENT_SECRET" in missing_setting_names(env)
