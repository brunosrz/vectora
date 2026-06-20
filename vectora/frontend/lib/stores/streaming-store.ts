import { create } from "zustand";

interface StreamingStore {
  streamingThreadId: string | null;
  setStreaming: (id: string | null) => void;
}

export const useStreamingStore = create<StreamingStore>((set) => ({
  streamingThreadId: null,
  setStreaming: (id) => set({ streamingThreadId: id }),
}));
