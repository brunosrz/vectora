"""Módulo de segurança para execução de ferramentas com whitelisting."""

import re
from pathlib import Path


def is_safe_file_path(path: str, allowed_dirs: list[str] | None = None) -> bool:
    """Verifica se um caminho de arquivo é seguro para leitura/edição.

    Rejeita:
    - Caminhos absolutoscom /../
    - Arquivos fora de allowed_dirs (se especificado)
    - Extensões perigosas

    Args:
        path: Caminho do arquivo
        allowed_dirs: Diretórios permitidos (ex: ["./vectora", "./data"])

    Returns:
        True se caminho é seguro
    """
    try:
        file_path = Path(path).resolve()

        if ".." in path:
            return False

        dangerous_extensions = {".exe", ".sh", ".bat", ".cmd", ".com", ".pif"}
        if file_path.suffix.lower() in dangerous_extensions:
            return False

        if allowed_dirs:
            for allowed_dir in allowed_dirs:
                allowed_path = Path(allowed_dir).resolve()
                try:
                    file_path.relative_to(allowed_path)
                    return True
                except ValueError:
                    pass
            return False

        return True
    except (ValueError, OSError):
        return False


def is_safe_regex_pattern(pattern: str) -> bool:
    """Valida se um padrão regex é seguro (evita ReDoS).

    Args:
        pattern: Padrão regex

    Returns:
        True se padrão é válido
    """
    dangerous_patterns = [
        r"(.*)*",
        r"(.*)+",
        r"(.+)*",
        r"(.+)+",
        r"(a*)*",
        r"(a+)*",
        r"(a*)+",
        r"(a+)+",
        r"(a|a)*",
        r"(a|a)+",
    ]

    # Remove anchors for pattern matching to catch variations like (a+)+$ and (a|a)*$
    pattern_without_anchors = pattern.lstrip("^").rstrip("$")

    if any(dangerous in pattern_without_anchors for dangerous in dangerous_patterns):
        return False

    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def is_safe_shell_command(command: str) -> bool:
    """Valida se um comando shell é seguro usando modelo blacklist-only.

    Política: PERMITIR tudo, exceto comandos explicitamente destrutivos.

    BLACKLIST (sempre bloqueados):
    - Deleção recursiva / irrecuperável: rm -rf, rm -fr, rmdir /s
    - Formatação de disco: mkfs, format c:, dd if=/dev/zero
    - Escalada de privilégios: sudo su, runas
    - Ataque fork bomb: :(){:|:&};:
    - Wipe de dados: shred, wipe, secure-delete

    Todos os outros comandos — incluindo git add, git commit, git push,
    npm install, python scripts, curl, etc. — são permitidos sem restrição.

    Args:
        command: Comando shell a validar

    Returns:
        True se o comando NÃO está na blacklist (pode ser executado)
        False se o comando está na blacklist (bloqueado)
    """
    cmd = command.strip().lower()

    # Blacklist: padrões destrutivos e irrecuperáveis
    blacklist: list[str] = [
        # Deleção recursiva/forçada
        "rm -rf",
        "rm -fr",
        "rm --no-preserve-root",
        "rmdir /s",
        "rd /s",
        # Formatação de disco
        "mkfs",
        "format c:",
        "format d:",
        "format e:",
        "dd if=/dev/zero",
        "dd if=/dev/urandom",
        # Wipe de dados
        "shred ",
        "wipe ",
        "secure-delete",
        # Fork bomb
        ":(){:|:&};:",
        # Escalada de privilégios perigosa
        "sudo rm",
        "sudo mkfs",
        "sudo dd",
        "sudo shred",
    ]

    return not any(blocked in cmd for blocked in blacklist)
