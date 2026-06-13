/**
 * Slash commands (Bloco H) — registry e parser.
 *
 * Apenas comandos cuja ação já existe no Vectora hoje. O dispatch real vive no
 * chat-interface; aqui ficam o registro (para o autocomplete) e helpers puros
 * de parsing, testáveis isoladamente.
 */

export interface SlashCommand {
  /** Nome sem a barra, ex: "model". */
  name: string;
  /** Chave i18n da descrição curta. */
  descKey: string;
  /** Uso exibido no autocomplete, ex: "/model <nome>". */
  usage: string;
  /** true quando o comando recebe argumento livre. */
  takesArg?: boolean;
}

export const SLASH_COMMANDS: SlashCommand[] = [
  { name: "help", descKey: "slash.help", usage: "/help" },
  { name: "clear", descKey: "slash.clear", usage: "/clear" },
  {
    name: "model",
    descKey: "slash.model",
    usage: "/model <nome>",
    takesArg: true,
  },
];

export interface ParsedSlash {
  name: string;
  arg: string;
}

/**
 * true quando o texto é uma "consulta de comando" — começa com "/" e ainda não
 * passou do nome do comando (sem espaço). Usado para abrir o autocomplete.
 */
export function isSlashQuery(input: string): boolean {
  return /^\/[a-z]*$/i.test(input);
}

/** Extrai {name, arg} de um input "/comando args". Retorna null se não for comando. */
export function parseSlashCommand(input: string): ParsedSlash | null {
  const trimmed = input.trim();
  if (!trimmed.startsWith("/")) return null;
  const match = trimmed.match(/^\/([a-z]+)(?:\s+([\s\S]*))?$/i);
  if (!match) return null;
  return { name: match[1].toLowerCase(), arg: (match[2] ?? "").trim() };
}

/** Filtra os comandos cujo nome começa com o termo digitado após a "/". */
export function filterCommands(input: string): SlashCommand[] {
  if (!input.startsWith("/")) return [];
  const term = input.slice(1).toLowerCase();
  return SLASH_COMMANDS.filter((c) => c.name.startsWith(term));
}

/** true quando o nome corresponde a um comando registrado. */
export function isKnownCommand(name: string): boolean {
  return SLASH_COMMANDS.some((c) => c.name === name);
}
