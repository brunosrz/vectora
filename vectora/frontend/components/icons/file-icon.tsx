/**
 * FileIcon — ícones de arquivo coloridos por extensão, inspirados no tema
 * "Symbols" (miguelsolorio.symbols): cada família de linguagem/arquivo tem
 * uma cor reconhecível, em vez do ícone genérico cinza único.
 *
 * Implementado com `lucide-react` (já é dependência do projeto) — sem
 * depender de pacotes de ícones externos não publicados/instaláveis.
 */
import {
  File,
  FileCode2,
  FileJson,
  FileText,
  FileType2,
  Image as ImageIcon,
  Settings2,
  Terminal,
  type LucideIcon,
} from "lucide-react";

interface IconSpec {
  icon: LucideIcon;
  className: string;
}

/** Mapa extensão → { ícone, cor }. Cores seguem a paleta do tema Symbols. */
const EXT_MAP: Record<string, IconSpec> = {
  // JavaScript / TypeScript
  js: { icon: FileCode2, className: "text-yellow-400" },
  jsx: { icon: FileCode2, className: "text-cyan-400" },
  ts: { icon: FileCode2, className: "text-blue-400" },
  tsx: { icon: FileCode2, className: "text-cyan-400" },
  mjs: { icon: FileCode2, className: "text-yellow-400" },
  cjs: { icon: FileCode2, className: "text-yellow-400" },

  // Web
  html: { icon: FileCode2, className: "text-orange-400" },
  css: { icon: FileCode2, className: "text-blue-400" },
  scss: { icon: FileCode2, className: "text-pink-400" },
  less: { icon: FileCode2, className: "text-indigo-400" },

  // Data / config
  json: { icon: FileJson, className: "text-yellow-500" },
  yaml: { icon: Settings2, className: "text-purple-400" },
  yml: { icon: Settings2, className: "text-purple-400" },
  toml: { icon: Settings2, className: "text-purple-400" },
  env: { icon: Settings2, className: "text-emerald-400" },

  // Docs
  md: { icon: FileText, className: "text-sky-400" },
  mdx: { icon: FileText, className: "text-sky-400" },
  txt: { icon: FileText, className: "text-muted-foreground" },

  // Backend langs
  py: { icon: FileCode2, className: "text-blue-300" },
  go: { icon: FileCode2, className: "text-cyan-300" },
  rs: { icon: FileCode2, className: "text-orange-500" },
  java: { icon: FileCode2, className: "text-red-400" },
  rb: { icon: FileCode2, className: "text-red-500" },
  php: { icon: FileCode2, className: "text-indigo-300" },

  // Shell
  sh: { icon: Terminal, className: "text-green-400" },
  bash: { icon: Terminal, className: "text-green-400" },
  zsh: { icon: Terminal, className: "text-green-400" },

  // Images
  png: { icon: ImageIcon, className: "text-purple-400" },
  jpg: { icon: ImageIcon, className: "text-purple-400" },
  jpeg: { icon: ImageIcon, className: "text-purple-400" },
  gif: { icon: ImageIcon, className: "text-purple-400" },
  svg: { icon: ImageIcon, className: "text-purple-400" },
  webp: { icon: ImageIcon, className: "text-purple-400" },
  ico: { icon: ImageIcon, className: "text-purple-400" },

  // Fonts
  ttf: { icon: FileType2, className: "text-pink-300" },
  otf: { icon: FileType2, className: "text-pink-300" },
  woff: { icon: FileType2, className: "text-pink-300" },
  woff2: { icon: FileType2, className: "text-pink-300" },
};

/** Resolve ícone + cor a partir do nome do arquivo (extensão). */
export function FileIcon({
  name,
  className = "w-3.5 h-3.5 shrink-0",
}: {
  name: string;
  className?: string;
}) {
  const ext = name.includes(".")
    ? (name.split(".").pop()?.toLowerCase() ?? "")
    : "";
  const spec = EXT_MAP[ext];
  const Icon = spec?.icon ?? File;
  const colorClass = spec?.className ?? "text-muted-foreground";
  return <Icon className={`${className} ${colorClass}`} />;
}
