import { validate } from "uuid";
import { getApiKey } from "@/lib/api-key";
import { Thread } from "@langchain/langgraph-sdk";
import { useQueryState } from "nuqs";
import {
  createContext,
  useContext,
  ReactNode,
  useCallback,
  useState,
  Dispatch,
  SetStateAction,
} from "react";
import { createClient } from "./client";

// Default values for Vectora
const DEFAULT_API_URL = "http://localhost:2024";
const DEFAULT_ASSISTANT_ID = "vectora";

interface ThreadContextType {
  getThreads: () => Promise<Thread[]>;
  threads: Thread[];
  setThreads: Dispatch<SetStateAction<Thread[]>>;
  threadsLoading: boolean;
  setThreadsLoading: Dispatch<SetStateAction<boolean>>;
}

const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

function getThreadSearchMetadata(
  assistantId: string,
): { graph_id: string } | { assistant_id: string } {
  if (validate(assistantId)) {
    return { assistant_id: assistantId };
  } else {
    return { graph_id: assistantId };
  }
}

export function ThreadProvider({ children }: { children: ReactNode }) {
  // Use environment variables with hardcoded fallbacks
  const envApiUrl = process.env.NEXT_PUBLIC_API_URL;
  const envAssistantId = process.env.NEXT_PUBLIC_ASSISTANT_ID;

  const [apiUrl] = useQueryState("apiUrl", {
    defaultValue: envApiUrl || DEFAULT_API_URL,
  });
  const [assistantId] = useQueryState("assistantId", {
    defaultValue: envAssistantId || DEFAULT_ASSISTANT_ID,
  });
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);

  const getThreads = useCallback(async (): Promise<Thread[]> => {
    const finalApiUrl = apiUrl || envApiUrl || DEFAULT_API_URL;
    const finalAssistantId = assistantId || envAssistantId || DEFAULT_ASSISTANT_ID;
    
    if (!finalApiUrl || !finalAssistantId) return [];
    
    const client = createClient(finalApiUrl, getApiKey() ?? undefined);

    try {
      const threads = await client.threads.search({
        metadata: {
          ...getThreadSearchMetadata(finalAssistantId),
        },
        limit: 100,
      });

      return threads;
    } catch (error) {
      console.error("Failed to fetch threads:", error);
      return [];
    }
  }, [apiUrl, assistantId, envApiUrl, envAssistantId]);

  const value = {
    getThreads,
    threads,
    setThreads,
    threadsLoading,
    setThreadsLoading,
  };

  return (
    <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>
  );
}

export function useThreads() {
  const context = useContext(ThreadContext);
  if (context === undefined) {
    throw new Error("useThreads must be used within a ThreadProvider");
  }
  return context;
}
