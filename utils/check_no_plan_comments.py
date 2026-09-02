#!/usr/bin/env python3
"""Rejeita comentários/strings de código-fonte com proveniência de processo:
referência de planejamento (Sprint/Bloco/Fase) ou menção a ferramenta/revisor
de IA (CodeRabbit, Claude, Copilot, ChatGPT, etc). Comentários descrevem o
que o código faz agora, não como ou por quem ele chegou nesse estado —
histórico de planejamento/revisão mora em markdown ou na mensagem do commit,
nunca em `.py`/`.ts`/`.tsx`/`.js`/`.jsx`. Roda como hook local de pre-commit,
recebendo os arquivos staged como argv.
"""

import re
import sys

reconfigure = getattr(sys.stdout, "reconfigure", None)
if reconfigure is not None and sys.stdout.encoding.lower() != "utf-8":
    reconfigure(encoding="utf-8")

# Três formas usadas neste repo pra numerar etapas de plano: a primeira
# palavra de release ("SPRINT" em qualquer capitalização) seguida de um
# número; a palavra de subdivisão de release ("PHASE", em português)
# seguida de um número (com sufixo de letra ou hífen opcional); e a
# palavra de bloco de trabalho ("BLOCK", em português) com "B" maiúsculo
# literal seguida de um identificador iniciado por maiúscula/dígito — sem
# essa última exigência, o regex bateria em qualquer uso comum do
# substantivo equivalente em português (como em "bloco de código"), que
# não tem nada a ver com plano. As duas primeiras casam sem distinguir
# maiúscula (`(?i:...)` escopado só a elas).
_PLAN_PATTERN = re.compile(
    r"(?i:\bsprint\s+\d+\b)|\bBloco\s+[A-Z][\w.]*\b|(?i:\bfase[\s-]+\d+[a-z]?\b)"
)

# Nome de ferramenta/revisor de IA — mesmo princípio do padrão de plano
# acima: comentário não é diário de quem/o-que produziu o código. Cada
# nome usa fronteira de palavra (\b) pra não colidir com substantivo comum
# (ex.: "copilot" sozinho já é o produto, sem risco de falso positivo real
# neste repo; "codex" também é específico o bastante). Case-insensitive —
# "CodeRabbit", "coderabbit", "CODERABBIT" são o mesmo problema.
_AI_TOOL_PATTERN = re.compile(
    r"(?i:\b(?:coderabbit(?:ai)?|claude(?:\s*code)?|chatgpt|copilot|codex)\b)"
)

_PATTERN = re.compile(f"{_PLAN_PATTERN.pattern}|{_AI_TOOL_PATTERN.pattern}")


def _find_violations(path: str) -> list[tuple[int, str]]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return []
    return [
        (i, line.rstrip("\n"))
        for i, line in enumerate(lines, start=1)
        if _PATTERN.search(line)
    ]


def main(argv: list[str]) -> int:
    had_violation = False
    for path in argv:
        for lineno, line in _find_violations(path):
            had_violation = True
            print(
                f"{path}:{lineno}: proveniência de processo em código-fonte: {line.strip()}"
            )
    if had_violation:
        print(
            "\nComentários/strings de código não referenciam Sprint/Bloco/Fase "
            "nem ferramenta/revisor de IA (CodeRabbit, Claude, Copilot, etc). "
            "Reescreva descrevendo só o estado atual do código — histórico de "
            "planejamento/revisão vai em docs/, .claude/plans/ ou na mensagem "
            "do commit."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
