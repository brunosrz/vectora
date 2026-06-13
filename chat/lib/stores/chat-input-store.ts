/**
 * chat-input-store — Bloco T (T10.4)
 *
 * Permite que outras áreas da UI (ex.: empty state do PlanTab, painel de
 * arquivos) pré-populem o input do chat sem acoplamento direto.
 *
 * Padrões:
 *  - `pushDraft(texto)` → substitui o input inteiro (ex.: templates do PlanTab)
 *  - `pushMention(path)` → adiciona `@path` ao final do input atual
 *
 * O ChatInterface observa os campos num useEffect e consome (limpa) após aplicar.
 * Sem persistência — volatile por design.
 */

import { create } from "zustand";

interface ChatInputState {
  draft: string | null;
  /** Path adicionado via painel de arquivos → inserido como @path no input. */
  mention: string | null;
  pushDraft: (text: string) => void;
  consumeDraft: () => void;
  pushMention: (path: string) => void;
  consumeMention: () => void;
}

export const useChatInputStore = create<ChatInputState>((set) => ({
  draft: null,
  mention: null,
  pushDraft: (text) => set({ draft: text }),
  consumeDraft: () => set({ draft: null }),
  pushMention: (path) => set({ mention: path }),
  consumeMention: () => set({ mention: null }),
}));
