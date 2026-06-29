/**
 * Sinal one-shot: set antes de navegar para /session/new quando o workspace
 * já foi confirmado no diálogo, para que a rota destino não reabra o seletor.
 */
let preChosenFlag = false;

export function signalWorkspacePreChosen(): void {
  preChosenFlag = true;
}

export function consumeWorkspacePreChosen(): boolean {
  const val = preChosenFlag;
  preChosenFlag = false;
  return val;
}
