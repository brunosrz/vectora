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

/**
 * Mesmo padrão, pra "criar novo workspace": setado ao sair de uma sessão
 * existente pro modal "Nova conversa" → "criar novo", antes de navegar pra
 * /session/new — nesse ponto o id da conversa nova ainda não existe (só é
 * gerado no destino), então não dá pra marcar `markCreateNewWorkspace(id)`
 * direto (ver workspace-choice-registry.ts). Consumido no mesmo lugar que
 * `consumeWorkspacePreChosen`, assim que o id novo é gerado.
 */
let createNewPreNavFlag = false;

export function signalCreateNewWorkspacePreNav(): void {
  createNewPreNavFlag = true;
}

export function consumeCreateNewWorkspacePreNav(): boolean {
  const val = createNewPreNavFlag;
  createNewPreNavFlag = false;
  return val;
}
