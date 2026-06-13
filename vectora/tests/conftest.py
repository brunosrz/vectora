"""Configuração compartilhada por toda a suíte Python (escopo ``tests/``).

⚠️ Rede de segurança contra travamento no shutdown — a CI não finalizava.

Sintoma: o pytest reportava o resultado final ("N passed") e gravava o
``coverage.xml`` normalmente, mas o **processo nunca saía**. O job da CI ficava
horas parado na tela de resultado até ser cancelado manualmente.

Causa: alguns recursos exercitados nos testes deixam **threads não-daemon**
vivas (ex.: o ``Observer`` do watchdog usado no SSE de eventos de workspace,
quando o stream de um teste não é drenado e o ``finally`` que faz
``observer.stop()`` nunca roda). Quando o pytest termina, o CPython chama
``threading._shutdown()``, que faz ``join`` em todas as threads não-daemon —
e fica bloqueado para sempre numa thread que nunca encerra. O resultado já foi
impresso; o interpretador apenas não consegue sair.

Correção: em ``pytest_unconfigure`` — que roda DEPOIS do summary e da gravação
do coverage — registramos (diagnóstico) as threads remanescentes e encerramos
o processo com ``os._exit(code)``, preemptando o ``join`` travado. O código de
saída é preservado, então a CI continua detectando falhas corretamente.

O ideal é também não vazar a thread (ver ``src/api/handlers/workspaces.py``,
onde o observer agora é ``daemon``), mas esta rede garante que NENHUM vazamento
futuro volte a travar o pipeline.
"""

from __future__ import annotations

import os
import sys
import threading
from typing import Any

# Capturado em pytest_sessionfinish e usado no pytest_unconfigure: o
# unconfigure não recebe o exitstatus, então guardamos aqui.
_exit_status: int = 0


def pytest_sessionfinish(exitstatus: int) -> None:
    """Memoriza o código de saída final para o pytest_unconfigure.

    O pytest injeta apenas os argumentos do hook que declaramos pelo nome —
    por isso pedimos só ``exitstatus`` (o ``session`` não é necessário aqui).
    """
    global _exit_status
    _exit_status = int(exitstatus)


def pytest_unconfigure(config: Any) -> None:
    """Força o término do processo após o pytest concluir todo o relatório.

    Roda no fim do ciclo do pytest, depois que o summary e o coverage já foram
    emitidos — antes do ``threading._shutdown()`` que travaria no join.
    """
    # Em workers do pytest-xdist NÃO forçamos o exit: quebraria o protocolo de
    # coleta de resultados do processo controlador. Só o principal encerra.
    if hasattr(config, "workerinput"):
        return

    main = threading.main_thread()
    alive = [
        t
        for t in threading.enumerate()
        if t is not main and not t.daemon and t.is_alive()
    ]
    if alive:
        names = ", ".join(sorted(t.name for t in alive))
        print(
            f"\n[conftest] {len(alive)} thread(s) não-daemon viva(s) no shutdown "
            f"(forçando os._exit para não travar a CI): {names}",
            file=sys.stderr,
        )

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_exit_status)
