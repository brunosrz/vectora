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


def test_secao_sandbox_vazia_como_dict_usa_defaults(tmp_path):
    # [sandbox] presente mas sem nenhuma chave — dict vazio, não None.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox]\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result != DISABLED_POLICY
    assert result.rw_paths == ()
    assert result.ro_paths == ()


def test_sandbox_como_lista_em_vez_de_tabela_falha_fechado(tmp_path):
    # Erro/borda: [[sandbox]] TOML array-of-tables vira lista, não dict —
    # isinstance(section, dict) deve rejeitar e não vira DISABLED silencioso.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[[sandbox]]\nenabled = true\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result == DISABLED_POLICY


def test_rw_paths_com_entradas_duplicadas_preserva_duplicatas(tmp_path):
    # Duplicado: parser não deduplica — é decisão do backend de execução,
    # não da camada de parsing (dedupe silencioso esconderia intenção).
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text(
        '[sandbox]\nrw_paths = ["/workspace", "/workspace"]\n', encoding="utf-8"
    )

    result = parse_policy(toml_path)

    assert result.rw_paths == ("/workspace", "/workspace")


def test_rw_e_ro_paths_vazios_explicitos_nao_quebram(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text(
        "[sandbox]\nrw_paths = []\nro_paths = []\nmask = []\n", encoding="utf-8"
    )

    result = parse_policy(toml_path)

    assert result.rw_paths == ()
    assert result.ro_paths == ()
    assert result.mask == ()


def test_mask_customizado_substitui_default_por_completo(tmp_path):
    # Borda: mask fornecido não faz merge com _DEFAULT_MASK, substitui.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text('[sandbox]\nmask = ["**/*.key"]\n', encoding="utf-8")

    result = parse_policy(toml_path)

    assert result.mask == ("**/*.key",)
    assert ".env" not in result.mask


def test_docker_image_ausente_fica_none(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text('[sandbox]\nbackend = "docker"\n', encoding="utf-8")

    result = parse_policy(toml_path)

    assert result.docker_image is None
    assert result.remote_host is None
    assert result.ssh_key_id is None


def test_docker_image_com_tipo_numerico_e_coagido_para_string(tmp_path):
    # docker_image = 123 não é erro de tipo fatal — str() converte.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox]\ndocker_image = 123\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result.docker_image == "123"


def test_backend_desconhecido_e_aceito_pelo_parser_mas_nao_pelo_dispatch(tmp_path):
    # O parser não valida o valor de backend (é o runner.py que faz dispatch
    # fail-closed) — só confirma que não quebra aqui, string livre é aceita.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text(
        '[sandbox]\nbackend = "backend-inexistente"\n', encoding="utf-8"
    )

    result = parse_policy(toml_path)

    assert result.backend == "backend-inexistente"


def test_arquivo_vazio_sem_nenhuma_secao_retorna_disabled(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result == DISABLED_POLICY


def test_encoding_invalido_falha_fechado(tmp_path):
    # Erro/borda: bytes que não decodificam como UTF-8 — read_text levanta
    # UnicodeDecodeError, capturado pelo except genérico do parse do TOML.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_bytes(b"[sandbox]\nbackend = \xff\xfe\n")

    result = parse_policy(toml_path)

    assert result == LOCKED_DOWN_POLICY


def test_enabled_com_string_truthy_e_coagido_para_bool(tmp_path):
    # enabled = "false" (string) via bool() vira True — comportamento do
    # bool() do Python é documentado aqui pra não surpreender no futuro.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text('[sandbox]\nenabled = "false"\n', encoding="utf-8")

    result = parse_policy(toml_path)

    assert result.enabled is True


def test_lockdown_true_com_backend_custom_preserva_backend(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text(
        '[sandbox]\nlockdown = true\nbackend = "docker"\n', encoding="utf-8"
    )

    result = parse_policy(toml_path)

    assert result.lockdown is True
    assert result.backend == "docker"


def test_empty_toml_file_returns_disabled_policy(tmp_path):
    # Erro/borda: arquivo vazio (sem nenhuma seção) não deve quebrar o parser.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result == DISABLED_POLICY


def test_sandbox_section_not_a_table_returns_disabled_policy(tmp_path):
    # `[sandbox]` precisa ser uma tabela — um escalar solto não é seção válida.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text('sandbox = "yes"\n', encoding="utf-8")

    result = parse_policy(toml_path)

    assert result == DISABLED_POLICY


def test_ro_paths_wrong_type_fails_closed(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox]\nro_paths = 7\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result == LOCKED_DOWN_POLICY


def test_mask_wrong_type_fails_closed(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox]\nmask = true\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result == LOCKED_DOWN_POLICY


def test_duplicate_keys_in_toml_fails_closed(tmp_path):
    # TOML não permite chave duplicada na mesma tabela — é erro de sintaxe.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text(
        "[sandbox]\nenabled = true\nenabled = false\n", encoding="utf-8"
    )

    result = parse_policy(toml_path)

    assert result == LOCKED_DOWN_POLICY


def test_optional_backend_fields_parsed_when_present(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text(
        """
[sandbox]
backend = "docker"
docker_image = "node:20-slim"
remote_host = "user@host"
ssh_key_id = "key-123"
""",
        encoding="utf-8",
    )

    result = parse_policy(toml_path)

    assert result.docker_image == "node:20-slim"
    assert result.remote_host == "user@host"
    assert result.ssh_key_id == "key-123"


def test_optional_backend_fields_default_to_none(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox]\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result.docker_image is None
    assert result.remote_host is None
    assert result.ssh_key_id is None


def test_enabled_explicitly_false_is_respected(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox]\nenabled = false\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result.enabled is False


def test_unknown_backend_name_is_preserved_not_normalized(tmp_path):
    # O parser não valida o valor de `backend` — quem falha fechado por
    # backend desconhecido é o dispatcher (runner.py), não o parser.
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text('[sandbox]\nbackend = "singularity"\n', encoding="utf-8")

    result = parse_policy(toml_path)

    assert result.backend == "singularity"
    assert result.enabled is True


def test_rw_and_ro_paths_with_unicode_and_spaces(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text(
        '[sandbox]\nrw_paths = ["/home/usuário/meu projeto"]\n',
        encoding="utf-8",
    )

    result = parse_policy(toml_path)

    assert result.rw_paths == ("/home/usuário/meu projeto",)


def test_empty_rw_and_ro_paths_lists_are_valid(tmp_path):
    toml_path = tmp_path / "vectora.toml"
    toml_path.write_text("[sandbox]\nrw_paths = []\nro_paths = []\n", encoding="utf-8")

    result = parse_policy(toml_path)

    assert result.rw_paths == ()
    assert result.ro_paths == ()
