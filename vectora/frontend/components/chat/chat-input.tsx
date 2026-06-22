/**
 * Chat Input Component
 *
 * Fixed input area at the bottom of the chat interface.
 * Includes file upload, drag & drop, and paste support.
 */

import { useCallback, useEffect, useState } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { FilePreviewGrid } from "./features/file-preview-grid";
import { VoiceInputButton } from "./features/voice-input-button";
import { PermissionModeMenu } from "./features/permission-mode-menu";
import { ChatParamsMenu } from "./features/chat-params-menu";
import { PlusMenu } from "./features/plus-menu";
import { UsagePopover } from "./features/usage-popover";
import { SlashCommandMenu } from "./features/slash-command-menu";
import { AtMentionMenu } from "./features/at-mention-menu";
import { WorkspaceSelector } from "@/components/sidebar/workspace-selector";
import { ModelSelector } from "./model-selector";
import { VscodeIcon } from "@/components/icons/vscode-icon";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { LayoutDashboard, MessageSquare } from "lucide-react";
import type { SlashCommand } from "@/lib/constants/slash-commands";
import type { AgentConfig } from "@/components/layout/agent-settings";
import type { ImageAttachment } from "@/lib/types";
import { useNetworkStatus } from "@/lib/hooks/use-network-status";
import { useToastStore } from "@/lib/stores/toast-store";
import { m } from "@/lib/paraglide/messages";

interface VscodeOption {
  strategy: string;
  label: string;
  url: string;
}

/**
 * Botão "Abrir no VS Code" — lança o VS Code direto, sem popup intermediário.
 * Prefere a estratégia "local" (vscode://file/...) e cai para a primeira
 * opção disponível (ssh/devcontainer) quando o workspace não é local.
 */
function VscodeMenu({ workspaceId }: { workspaceId: string }) {
  const handleLaunch = useCallback(async () => {
    if (!workspaceId) return;
    const res = await fetch(
      `/workspaces/${encodeURIComponent(workspaceId)}/vscode-options`,
    );
    const options: VscodeOption[] = res.ok
      ? ((await res.json()).options ?? [])
      : [];
    const opt =
      options.find((o) => o.strategy === "local") ?? options[0] ?? null;
    if (!opt) {
      useToastStore.getState().error(m.workbench_open_vscode_unavailable());
      return;
    }
    window.location.href = opt.url;
  }, [workspaceId]);

  return (
    <button
      onClick={handleLaunch}
      className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 shrink-0"
      title={m.workbench_open_vscode()}
      aria-label={m.workbench_open_vscode()}
    >
      <VscodeIcon className="w-4 h-4" />
    </button>
  );
}

interface ChatInputProps {
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  isLoading: boolean;
  isStopping: boolean;
  onStop: () => void;
  userId?: string | null;

  // File upload
  attachedFiles: ImageAttachment[];
  uploadError: string | null;
  inputError: string | null;
  isDragging: boolean;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onPaste: (e: React.ClipboardEvent<HTMLTextAreaElement>) => void;
  onRemoveFile: (fileId: string) => void;
  onFileButtonClick: (e: React.MouseEvent) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  textareaRef?: React.RefObject<HTMLTextAreaElement | null>;

  // Voice input
  isVoiceListening?: boolean;
  isVoiceSupported?: boolean;
  onVoiceToggle?: () => void;
  voiceError?: string | null;

  // Queued messages
  queuedMessages?: { content: string; id: string }[];

  // Context meter (R5)
  tokensUsed?: number;
  modelId?: string;

  // Modelo (seletor permanente no rodapé) — F.2.2/F.2.3
  agentConfig?: AgentConfig;
  onAgentConfigChange?: (config: AgentConfig) => void;

  // F.2.3 — overlay de drop zone mais explícito no estado vazio
  dropHintExpanded?: boolean;
  /** Callback de seleção de arquivo via @mention. */
  onAtMentionSelect?: (path: string, startIdx: number, endIdx: number) => void;
}

const EMPTY_QUEUED_MESSAGES: NonNullable<ChatInputProps["queuedMessages"]> = [];

/**
 * Chat input area with file upload support.
 * Displays at the bottom of the chat interface when there are existing messages.
 */
export function ChatInput({
  input,
  onInputChange,
  onSend,
  onKeyDown,
  isLoading,
  isStopping,
  onStop,
  userId,
  attachedFiles,
  uploadError,
  inputError,
  isDragging,
  onDragOver,
  onDragLeave,
  onDrop,
  onPaste,
  onRemoveFile,
  onFileButtonClick,
  fileInputRef,
  onFileSelect,
  textareaRef,
  isVoiceListening,
  isVoiceSupported,
  onVoiceToggle,
  voiceError,
  queuedMessages = EMPTY_QUEUED_MESSAGES,
  tokensUsed,
  modelId,
  agentConfig,
  onAgentConfigChange,
  dropHintExpanded = false,
  onAtMentionSelect,
}: ChatInputProps) {
  const wsId = useWorkspacesStore((s) => s.getActive())?.id ?? "";
  const chatMode = useSettingsStore((s) => s.chatMode);
  const setChatMode = useSettingsStore((s) => s.setChatMode);
  // UX-16 — sem rede não há para onde enviar; desabilita entrada e ações
  // que dependem do backend (anexos, voz) em vez de deixar o usuário digitar
  // para uma falha certa.
  const { offline } = useNetworkStatus();
  const handleModelChange = (model: string) => {
    if (agentConfig && onAgentConfigChange) {
      onAgentConfigChange({ ...agentConfig, model });
    }
  };

  // Auto-grow do textarea: ajusta a altura ao conteúdo até o teto de 240px;
  // depois disso o próprio textarea passa a scrollar internamente. Resolve
  // a queixa "ele não expande pra cima e com scroll visível".
  useEffect(() => {
    const el = textareaRef?.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(240, el.scrollHeight);
    el.style.height = `${next}px`;
  }, [input, textareaRef]);
  return (
    <div className="relative">
      {/* Enhanced visibility layer */}
      <div className="absolute inset-0 pointer-events-none" />

      <div className="relative z-[50] border-t border-border/60 bg-background backdrop-blur-sm">
        <div className="w-full max-w-4xl mx-auto px-3 sm:px-4 py-1.5">
          {/* File Previews */}
          <FilePreviewGrid files={attachedFiles} onRemove={onRemoveFile} />

          {/* Upload Error */}
          {uploadError && (
            <div className="mb-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">
              {uploadError}
            </div>
          )}

          {/* Voice Error */}
          {voiceError && (
            <div className="mb-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">
              {voiceError}
            </div>
          )}

          {/* Queued Messages */}
          {queuedMessages.length > 0 && (
            <div className="mb-2 space-y-1.5">
              {queuedMessages.map((msg) => (
                <div
                  key={msg.id}
                  className="flex items-center gap-2 px-3 py-2 bg-muted/50 border border-border/50 rounded-lg text-sm"
                >
                  <div className="flex items-center gap-1.5 text-muted-foreground flex-shrink-0">
                    <svg
                      className="w-3 h-3 animate-pulse"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <circle cx="12" cy="12" r="10" />
                    </svg>
                    <span className="text-xs font-medium">
                      {m.input_queued()}
                    </span>
                  </div>
                  <span className="text-foreground/80 truncate">
                    {msg.content}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="relative group">
            {/* Autocomplete de @arquivo — aparece antes do slash para não conflitar */}
            {onAtMentionSelect && (
              <AtMentionMenu input={input} onSelect={onAtMentionSelect} />
            )}

            {/* Autocomplete de slash commands (Bloco H) */}
            <SlashCommandMenu
              input={input}
              onSelect={(cmd: SlashCommand) => {
                onInputChange(cmd.takesArg ? `/${cmd.name} ` : `/${cmd.name}`);
                textareaRef?.current?.focus();
              }}
            />

            {/* Input container — borda única, sem glow nem ring duplicado. */}
            <div className="relative">
              <div
                className={`relative rounded-xl border bg-background transition-colors duration-200 ${isDragging ? "border-primary bg-primary/5" : "border-border/60 group-focus-within:border-primary/70"}`}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
              >
                {isDragging && (
                  <div
                    className={
                      dropHintExpanded
                        ? "absolute inset-0 bg-primary/15 rounded-xl flex items-center justify-center z-20 pointer-events-none border-2 border-dashed border-primary"
                        : "absolute inset-0 bg-primary/10 rounded-xl flex items-center justify-center z-20 pointer-events-none"
                    }
                  >
                    <div className="text-primary font-medium">
                      {m.welcome_drop_files()}
                    </div>
                  </div>
                )}
                <div className="flex items-end gap-2 px-3 py-1.5">
                  {/* Hidden File Input */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.py,.js,.ts,.tsx,.jsx,.java,.cpp,.c,.h,.cs,.go,.rs,.rb,.php,.sh,.bash,.yaml,.yml,.json,.xml,.html,.css,.md,.txt,.log,.sql,.graphql,.r,.swift,.kt,.scala,.har"
                    multiple
                    onChange={onFileSelect}
                    className="hidden"
                  />

                  <Textarea
                    ref={textareaRef}
                    data-testid="chat-input"
                    value={input}
                    onChange={(e) => onInputChange(e.target.value)}
                    onKeyDown={onKeyDown}
                    onPaste={onPaste}
                    placeholder={
                      !userId
                        ? m.input_initializing()
                        : offline
                          ? m.network_disabled_offline()
                          : isLoading
                            ? m.input_loading_placeholder()
                            : m.input_placeholder()
                    }
                    title={offline ? m.network_disabled_offline() : undefined}
                    className="relative z-10 min-h-[36px] max-h-[240px] resize-none overflow-y-auto bg-transparent border-0 w-full px-3 py-2 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 transition-[height] duration-150 break-words custom-scrollbar"
                    disabled={!userId || offline}
                    rows={1}
                  />

                  {!isLoading && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          onClick={onSend}
                          data-testid="chat-send"
                          variant="ghost"
                          size="sm"
                          disabled={!input.trim() || !userId || offline}
                          className="h-8 w-8 p-0 mb-0.5 shrink-0 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 disabled:bg-muted disabled:text-muted-foreground"
                          type="button"
                          aria-label={m.tooltip_chat_send()}
                        >
                          <Send className="w-3.5 h-3.5" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="top">
                        {m.tooltip_chat_send()}
                      </TooltipContent>
                    </Tooltip>
                  )}

                  {isLoading && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          onClick={onStop}
                          variant="ghost"
                          size="sm"
                          disabled={isStopping}
                          className={`
                            h-9 px-4 mb-0.5 rounded-full flex-shrink-0
                            transition-all duration-200 hover:scale-105 active:scale-95
                            bg-muted text-primary hover:text-primary hover:bg-muted/80 border-2 border-primary
                            ${isStopping ? "opacity-60 cursor-not-allowed" : ""}
                          `}
                          type="button"
                          aria-label={
                            isStopping
                              ? m.input_stopping()
                              : m.tooltip_chat_stop()
                          }
                        >
                          <span className="text-xs font-medium">
                            {isStopping ? m.input_stopping() : m.input_stop()}
                          </span>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="top">
                        {isStopping
                          ? m.input_stopping()
                          : m.tooltip_chat_stop()}
                      </TooltipContent>
                    </Tooltip>
                  )}
                </div>
              </div>
            </div>
          </div>

          {inputError && (
            <div className="mt-1 px-2 text-xs text-destructive">
              {inputError}
            </div>
          )}

          {/* Rodapé do input — "meio-termo" entre o estilo Claude Code
              (dois grupos minimalistas) e a chip row do Codex (contexto →
              configuração). Grupo esquerdo: workspace (onde) → modo de
              permissão; direita: modelo e medidor de uso. Sem barra de
              contexto acima do input (poluição visual desnecessária). */}
          <div className="flex items-center justify-between gap-2 mt-1 px-1 flex-nowrap">
            <div className="flex items-center gap-1 min-w-0">
              <PlusMenu
                disabled={!userId || offline}
                onAddFiles={onFileButtonClick}
              />
              <div className="hidden sm:block h-4 w-px bg-border/60 mx-0.5" />
              {!chatMode && (
                <>
                  <WorkspaceSelector compact />
                  {wsId && <VscodeMenu workspaceId={wsId} />}
                  <div className="hidden sm:block h-4 w-px bg-border/60 mx-0.5" />
                </>
              )}
              <PermissionModeMenu />
              <div className="hidden sm:block h-4 w-px bg-border/60 mx-0.5" />
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => setChatMode(!chatMode)}
                    data-chatmode={chatMode ? "on" : "off"}
                    aria-label={
                      chatMode ? m.chat_mode_disable() : m.chat_mode_enable()
                    }
                    className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 shrink-0 transition-colors"
                  >
                    {chatMode ? (
                      <MessageSquare className="w-4 h-4" />
                    ) : (
                      <LayoutDashboard className="w-4 h-4" />
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top">
                  {chatMode ? m.chat_mode_disable() : m.chat_mode_enable()}
                </TooltipContent>
              </Tooltip>
            </div>

            <div className="flex items-center gap-1 min-w-0 justify-end">
              <ChatParamsMenu />
              {agentConfig && onAgentConfigChange && (
                <ModelSelector
                  value={agentConfig.model}
                  onChange={handleModelChange}
                  compact
                />
              )}
              {modelId && (
                <UsagePopover tokensUsed={tokensUsed ?? 0} modelId={modelId} />
              )}
              {isVoiceSupported && onVoiceToggle && (
                <VoiceInputButton
                  isListening={isVoiceListening ?? false}
                  disabled={!userId || offline}
                  onClick={onVoiceToggle}
                  size="sm"
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
