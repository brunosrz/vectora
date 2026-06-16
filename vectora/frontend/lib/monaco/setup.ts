/**
 * Configuração local do Monaco — sem CDN.
 *
 * O `@monaco-editor/react`, por padrão, baixa o Monaco de um CDN em runtime.
 * Isso quebra no Electron e em ambientes offline (a proposta self-hosted do
 * Vectora). Aqui apontamos o loader para o pacote `monaco-editor` empacotado
 * pelo Vite e registramos os web workers via imports `?worker`.
 *
 * Importar este módulo (efeito colateral) antes de montar qualquer `<Editor>`.
 */

// Os imports `?worker` são módulos virtuais do Vite (cada um exporta um
// construtor Worker como default); o resolver do oxlint não os entende.
/* oxlint-disable import/default */
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import jsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker";
import cssWorker from "monaco-editor/esm/vs/language/css/css.worker?worker";
import htmlWorker from "monaco-editor/esm/vs/language/html/html.worker?worker";
import tsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker?worker";
import { loader } from "@monaco-editor/react";

declare global {
  interface Window {
    MonacoEnvironment?: monaco.Environment;
  }
}

self.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    if (label === "json") return new jsonWorker();
    if (label === "css" || label === "scss" || label === "less") {
      return new cssWorker();
    }
    if (label === "html" || label === "handlebars" || label === "razor") {
      return new htmlWorker();
    }
    if (label === "typescript" || label === "javascript") {
      return new tsWorker();
    }
    return new editorWorker();
  },
};

loader.config({ monaco });

/** Linguagem do Monaco a partir da extensão do arquivo. */
export function languageFromPath(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    mjs: "javascript",
    cjs: "javascript",
    json: "json",
    css: "css",
    scss: "scss",
    less: "less",
    html: "html",
    htm: "html",
    xml: "xml",
    md: "markdown",
    markdown: "markdown",
    py: "python",
    rs: "rust",
    go: "go",
    java: "java",
    c: "c",
    h: "c",
    cpp: "cpp",
    hpp: "cpp",
    cs: "csharp",
    rb: "ruby",
    php: "php",
    sh: "shell",
    bash: "shell",
    yaml: "yaml",
    yml: "yaml",
    toml: "ini",
    ini: "ini",
    sql: "sql",
    graphql: "graphql",
    swift: "swift",
    kt: "kotlin",
    scala: "scala",
    r: "r",
  };
  return map[ext] ?? "plaintext";
}
