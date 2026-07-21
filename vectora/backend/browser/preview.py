"""Resolve a URL do dev server de preview ativo de um workspace.

Guardrail deliberado: as tools de browser automation só navegam pra dentro
de um preview que o PRÓPRIO workspace já subiu via `.vectora/launch.json`
(`preview_start`) — nunca uma URL arbitrária da internet.
"""

from __future__ import annotations


async def resolve_preview_url(workspace_id: str) -> str | None:
    """Retorna `http://localhost:{port}` do primeiro preview server rodando, ou None."""
    from backend.api.handlers.workspaces import (
        _is_port_open,
        _preview_key,
        _preview_procs,
        get_launch_json,
    )

    launch = await get_launch_json(workspace_id)
    for cfg in launch.configurations:
        proc = _preview_procs.get(_preview_key(workspace_id, cfg.name))
        if (
            proc is not None
            and proc.returncode is None
            and await _is_port_open("127.0.0.1", cfg.port)
        ):
            return f"http://localhost:{cfg.port}"
    return None
