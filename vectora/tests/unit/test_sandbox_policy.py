"""AI Jail — parser de `vectora.toml` [sandbox]. Fail-closed sempre que o
arquivo existe mas está malformado ou tem campo de tipo errado."""

from __future__ import annotations

from backend.sandbox.policy import DISABLED_POLICY, LOCKED_DOWN_POLICY, parse_policy


def test_missing_file_returns_disabled_policy(tmp_path):
    result = parse_policy(tmp_path / "vectora.toml")

    assert result == DISABLED_POLICY
    assert result.enabled is False


def test_file_without_sandbox_section_returns_disabled_policy(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text('[other]\nkey = "value"\n', encoding="utf-8")

    result = parse_policy(toml_path)

    assert result == DISABLED_POLICY


def test_valid_sandbox_section_parses_all_fields(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text(
        """
[sandbox]
enabled = true
backend = "local"
rw_paths = ["/workspace"]
ro_paths = ["/opt/tools"]
mask = [".env"]
no_gpu = false
lockdown = true
""",
        encoding="utf-8",
    )

    result = parse_policy(toml_path)

    assert result.enabled is True
    assert result.backend == "local"
    assert result.rw_paths == ("/workspace",)
    assert result.ro_paths == ("/opt/tools",)
    assert result.mask == (".env",)
    assert result.no_gpu is False
    assert result.lockdown is True


def test_malformed_toml_fails_closed(tmp_path):
    # Erro/borda: TOML quebrado nunca deve desabilitar a proteção
    # silenciosamente — a política mais restritiva é o resultado seguro.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox\nenabled = true", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result == LOCKED_DOWN_POLICY
    assert result.enabled is True
    assert result.lockdown is True


def test_wrong_field_type_fails_closed(tmp_path):
    # rw_paths deveria ser array de strings — aqui é um int solto.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox]\nrw_paths = 42\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result == LOCKED_DOWN_POLICY


def test_defaults_applied_when_fields_omitted(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox]\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result.enabled is True
    assert result.backend == "local"
    assert result.no_gpu is True
    assert result.lockdown is False
    assert ".env" in result.mask
