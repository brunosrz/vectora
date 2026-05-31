/**
 * chat-input-store — Bloco T (T10.4)
 *
 * Permite que outras áreas da UI (ex.: empty state do PlanTab) pré-populem
 * o input do chat sem acoplamento direto. Padrão simples: quem quer
 * "injetar" um rascunho chama `pushDraft("texto")`. O ChatInput observa o
 * campo `draft` num useEffect e, ao receber valor não-nulo, seta o
 * próprio state e limpa o store via `consumeDraft()`. Sem persistência.
 */

import { create } from "zustand";

interface ChatInputState {
  draft: string | null;
  pushDraft: (text: string) => void;
  consumeDraft: () => void;
}

export const useChatInputStore = create<ChatInputState>((set) => ({
  draft: null,
  pushDraft: (text) => set({ draft: text }),
  consumeDraft: () => set({ draft: null }),
}));
