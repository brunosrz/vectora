/**
 * Registro de threads "novas" — persiste entre navegações SPA sem reload.
 *
 * Quando page.tsx cria um UUID e redireciona para /session/<uuid>,
 * este módulo lembra que esse thread ainda não existe no backend
 * (ChatInterface usa isso para pular o fetch de histórico).
 */

const _newThreads = new Set<string>();

/** Marca um thread como recém-criado (não existe no backend ainda). */
export function markAsNew(threadId: string): void {
  _newThreads.add(threadId);
}

/** Retorna true se o thread foi criado localmente e ainda não persistido. */
export function isNew(threadId: string): boolean {
  return _newThreads.has(threadId);
}

/** Remove a marcação (chamado quando o thread é persistido no backend). */
export function clearNew(threadId: string): void {
  _newThreads.delete(threadId);
}
