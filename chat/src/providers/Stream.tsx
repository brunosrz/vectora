import React, {
  createContext,
  useContext,
  ReactNode,
  useState,
  useEffect,
} from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import { uiMessageReducer } from "@langchain/langgraph-sdk/react-ui";
import { useQueryState, parseAsBoolean } from "nuqs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { LangGraphLogoSVG } from "@/components/icons/langgraph";
import { Label } from "@/components/ui/label";
import { ArrowRight, Settings2 } from "lucide-react";
import { PasswordInput } from "@/components/ui/password-input";
import { getApiKey } from "@/lib/api-key";
import { useThreads } from "./Thread";
import { toast } from "sonner";
import { StateType, StreamUpdateType, CustomEventType } from "@/types/agent";

export type { UIMetrics, StateType } from "@/types/agent";

const useTypedStream = useStream<
  StateType,
  {
    UpdateType: StreamUpdateType;
    CustomEventType: CustomEventType;
  }
>;

type StreamContextType = ReturnType<typeof useTypedStream> & {
  apiUrl: string;
  assistantId: string;
};
const StreamContext = createContext<StreamContextType | undefined>(undefined);

async function sleep(ms = 4000) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function checkGraphStatus(
  apiUrl: string,
  apiKey: string | null,
): Promise<boolean> {
  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), 5000);

    const res = await fetch(`${apiUrl}/info`, {
      signal: controller.signal,
      ...(apiKey && {
        headers: {
          "X-Api-Key": apiKey,
        },
      }),
    });
    clearTimeout(id);
    return res.ok;
  } catch (e) {
    console.debug("Graph status check failed:", e);
    return false;
  }
}

const StreamSession = ({
  children,
  apiKey,
  apiUrl,
  assistantId,
}: {
  children: ReactNode;
  apiKey: string | null;
  apiUrl: string;
  assistantId: string;
}) => {
  const [threadId, setThreadId] = useQueryState("threadId");
  const { getThreads, setThreads } = useThreads();
  const streamValue = useTypedStream({
    apiUrl,
    apiKey: apiKey ?? undefined,
    assistantId,
    threadId: threadId ?? null,
    onCustomEvent: (event, options) => {
      options.mutate((prev) => {
        const ui = uiMessageReducer(prev.ui ?? [], event);
        return { ...prev, ui };
      });
    },
    onThreadId: (id) => {
      setThreadId(id);
      // Refetch threads list when thread ID changes.
      // Wait for some seconds before fetching so we're able to get the new thread that was created.
      sleep().then(() => getThreads().then(setThreads).catch(console.error));
    },
  });

  useEffect(() => {
    checkGraphStatus(apiUrl, apiKey).then((ok) => {
      if (!ok) {
        toast.error("Erro de conexão", {
          description: () => (
            <p>
              Não foi possível conectar ao servidor Vectora em{" "}
              <code>{apiUrl}</code>. Certifique-se de que o agent está rodando (
              <code>uv run vectora</code>).
            </p>
          ),
          duration: 15000,
          richColors: true,
          closeButton: true,
        });
      }
    });
  }, [apiKey, apiUrl]);

  return (
    <StreamContext.Provider
      value={{
        ...streamValue,
        apiUrl,
        assistantId,
      }}
    >
      {children}
    </StreamContext.Provider>
  );
};

// Default values for Vectora
const DEFAULT_API_URL = "http://localhost:2024";
const DEFAULT_ASSISTANT_ID = "vectora";

export const StreamProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  // Get environment variables
  const envApiUrl: string | undefined = process.env.NEXT_PUBLIC_API_URL;
  const envAssistantId: string | undefined =
    process.env.NEXT_PUBLIC_ASSISTANT_ID;
  const envApiKey: string | undefined =
    process.env.NEXT_PUBLIC_LANGSMITH_API_KEY;

  // Use URL params with env var fallbacks and finally hardcoded defaults
  const [apiUrl, setApiUrl] = useQueryState("apiUrl", {
    defaultValue: envApiUrl || DEFAULT_API_URL,
  });
  const [assistantId, setAssistantId] = useQueryState("assistantId", {
    defaultValue: envAssistantId || DEFAULT_ASSISTANT_ID,
  });
  const [showConfig, setShowConfig] = useQueryState(
    "setup",
    parseAsBoolean.withDefault(false),
  );

  // For API key, use localStorage with env var fallback
  const [apiKey, _setApiKey] = useState(() => {
    const storedKey = getApiKey();
    return storedKey || envApiKey || "";
  });

  const setApiKey = (key: string) => {
    window.localStorage.setItem("lg:chat:apiKey", key);
    _setApiKey(key);
  };

  // Determine final values to use
  const finalApiUrl = apiUrl || envApiUrl || DEFAULT_API_URL;
  const finalAssistantId =
    assistantId || envAssistantId || DEFAULT_ASSISTANT_ID;

  if (showConfig || !finalApiUrl || !finalAssistantId) {
    return (
      <div className="flex items-center justify-center min-h-screen w-full p-4 bg-gray-50/50 dark:bg-gray-950">
        <div className="animate-in fade-in-0 zoom-in-95 flex flex-col border dark:border-gray-800 bg-background shadow-xl rounded-xl max-w-xl w-full overflow-hidden">
          <div className="flex flex-col gap-2 p-8 border-b dark:border-gray-800 bg-white dark:bg-gray-900">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="bg-indigo-600 p-2 rounded-lg">
                  <Settings2 className="size-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
                    Configuração do Agent
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    Ajuste a conexão com o Vectora Agent.
                  </p>
                </div>
              </div>
            </div>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();

              const form = e.target as HTMLFormElement;
              const formData = new FormData(form);
              const newApiUrl = formData.get("apiUrl") as string;
              const newAssistantId = formData.get("assistantId") as string;
              const newApiKey = formData.get("apiKey") as string;

              setApiUrl(newApiUrl);
              setApiKey(newApiKey);
              setAssistantId(newAssistantId);
              setShowConfig(null); // Hide setup after submit

              form.reset();
            }}
            className="flex flex-col gap-6 p-8 bg-white dark:bg-gray-900"
          >
            <div className="flex flex-col gap-2">
              <Label
                htmlFor="apiUrl"
                className="text-sm font-semibold text-gray-900 dark:text-gray-100"
              >
                URL de Deployment<span className="text-rose-500">*</span>
              </Label>
              <Input
                id="apiUrl"
                name="apiUrl"
                className="bg-background border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100"
                defaultValue={apiUrl || DEFAULT_API_URL}
                placeholder="http://localhost:2024"
                required
              />
              <p className="text-xs text-muted-foreground">
                Porta padrão do Vectora Agent: 2024.
              </p>
            </div>

            <div className="flex flex-col gap-2">
              <Label
                htmlFor="assistantId"
                className="text-sm font-semibold text-gray-900 dark:text-gray-100"
              >
                Graph ID / Assistant ID<span className="text-rose-500">*</span>
              </Label>
              <Input
                id="assistantId"
                name="assistantId"
                className="bg-background border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100"
                defaultValue={assistantId || DEFAULT_ASSISTANT_ID}
                placeholder="vectora"
                required
              />
              <p className="text-xs text-muted-foreground">
                Graph ID padrão: "vectora".
              </p>
            </div>

            <div className="flex flex-col gap-2">
              <Label
                htmlFor="apiKey"
                className="text-sm font-semibold text-gray-400"
              >
                LangSmith API Key (opcional)
              </Label>
              <PasswordInput
                id="apiKey"
                name="apiKey"
                defaultValue={apiKey ?? ""}
                className="bg-background border-dashed border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100"
                placeholder="lsv2_pt_..."
              />
            </div>

            <div className="flex justify-between items-center mt-4">
              <button
                type="button"
                onClick={() => setShowConfig(null)}
                className="text-sm text-muted-foreground hover:text-indigo-600 transition-colors"
              >
                Pular
              </button>
              <Button
                type="submit"
                size="lg"
                className="px-8 bg-indigo-600 hover:bg-indigo-700 text-white shadow-md"
              >
                Conectar
                <ArrowRight className="size-4 ml-2" />
              </Button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <StreamSession
      apiKey={apiKey}
      apiUrl={finalApiUrl}
      assistantId={finalAssistantId}
    >
      {children}
    </StreamSession>
  );
};

// Create a custom hook to use the context
export const useStreamContext = (): StreamContextType => {
  const context = useContext(StreamContext);
  if (context === undefined) {
    throw new Error("useStreamContext must be used within a StreamProvider");
  }
  return context;
};

export default StreamContext;
