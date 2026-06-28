/**
 * Registro de threads cujo workspace já foi escolhido nesta navegação SPA.
 *
 * Uma sessão nova em modo Code precisa que o usuário escolha um workspace antes
 * de começar (em vez de herdar silenciosamente o workspace global persistido).
 * Quando o usuário confirma a escolha no modal de "Nova conversa", marcamos o id
 * aqui — assim a rota de sessão sabe que NÃO deve reabrir o seletor para esse id
 * (evita um loop, já que confirmar gera um id novo e marcado).
 *
 * TTL: entradas expiram após 5 minutos, espelhando o new-thread-registry, para
 * que um reload tardio não deixe a marcação presa para sempre.
 */

const TTL_MS = 5 * 60 * 1000;

const chosen = new Map<string, number>();

/** Marca que o workspace desta thread já foi escolhido pelo usuário. */
export function markWorkspaceChosen(threadId: string): void {
  chosen.set(threadId, Date.now());
}

/** Retorna true se o usuário já escolheu o workspace desta thread. */
export function isWorkspaceChosen(threadId: string): boolean {
  const at = chosen.get(threadId);
  if (at === undefined) return false;
  if (Date.now() - at > TTL_MS) {
    chosen.delete(threadId);
    return false;
  }
  return true;
}
