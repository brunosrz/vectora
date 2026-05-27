/**
 * Markdown Envelope Stripping
 *
 * O orchestrator do Vectora envelopa toda resposta markdown em um bloco com
 * exatamente seis crases e o identificador `markdown`:
 *
 *     ``````markdown
 *     # Título
 *     ```python
 *     print("blocos triplos internos funcionam")
 *     ```
 *     ``````
 *
 * Razão: blocos de código ``` ``` ``` internos não quebram a hierarquia de
 * parsing, porque o envelope externo usa 6 crases (qualquer fence interno
 * com ≤5 crases é tratado como conteúdo).
 *
 * Este módulo desempacota o envelope antes da renderização. Streaming-safe:
 * remove o abre/fecha mesmo quando ainda parciais durante a chegada dos tokens.
 */

// Captura ``````markdown\n...\n`````` (com fechamento, tolerante a CRLF/trailing space).
// Lazy quantifier no corpo + final opcional para suportar streaming parcial.
const FULL_ENVELOPE_RE = /^[\t ]*``````\s*markdown[\t ]*\r?\n([\s\S]*?)\r?\n[\t ]*``````[\t ]*\s*$/

// Apenas a abertura — usado quando o stream ainda está chegando.
const OPEN_ENVELOPE_RE = /^[\t ]*``````\s*markdown[\t ]*\r?\n/

/**
 * Remove o envelope ``````markdown ... `````` se presente.
 *
 * - Fechado completo → retorna o conteúdo interno
 * - Apenas aberto (streaming em andamento) → remove só o abre
 * - Sem envelope (resposta plain) → retorna como está
 * - Conteúdo vazio ou não-string → retorna inalterado
 */
export function stripMarkdownEnvelope(content: string): string {
  if (!content) return content

  const trimmed = content.trimStart()

  // Caso 1: envelope completo (abre + corpo + fecha)
  const full = trimmed.match(FULL_ENVELOPE_RE)
  if (full) return full[1] ?? ""

  // Caso 2: apenas a abertura chegou (token streaming parcial)
  if (OPEN_ENVELOPE_RE.test(trimmed)) {
    let body = trimmed.replace(OPEN_ENVELOPE_RE, "")
    // Se o fecho ainda não chegou mas o stream terminou com `````` no final,
    // remove o fechamento parcial também.
    body = body.replace(/\r?\n[\t ]*``````[\t ]*\s*$/, "")
    return body
  }

  // Caso 3: sem envelope — retorna como veio
  return content
}
