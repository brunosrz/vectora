"use client";

/**
 * MonacoReadOnly — editor Monaco read-only, carregado sob demanda.
 *
 * Isolado em um módulo próprio para ser importado via `React.lazy` pelo
 * FileViewer: o `monaco-editor` depende de `window` e quebra em ambientes
 * sem DOM (testes/SSR). Mantê-lo fora do grafo de import estático do viewer
 * evita esse acoplamento — só carrega no cliente quando há texto a exibir.
 */

import MonacoEditor from "@monaco-editor/react";
import { Loader2 } from "lucide-react";

import { languageFromPath } from "@/lib/monaco/setup";
import { useSettingsStore } from "@/lib/stores/settings-store";

export default function MonacoReadOnly({
  value,
  path,
  isDark,
}: {
  value: string;
  path: string;
  isDark: boolean;
}) {
  const monacoFontSize = useSettingsStore((s) => s.monacoFontSize);
  return (
    <MonacoEditor
      value={value}
      language={languageFromPath(path)}
      theme={isDark ? "vs-dark" : "vs"}
      options={{
        readOnly: true,
        domReadOnly: true,
        fontSize: monacoFontSize,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 2,
        wordWrap: "on",
      }}
      loading={
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      }
    />
  );
}
