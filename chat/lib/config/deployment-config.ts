/**
 * Vectora Chat — Model Configuration
 *
 * Modelos suportados pelo Vectora Agent:
 *   google-genai  → gemini-3.5-flash, gemini-3.1-pro-preview, gemini-3-flash-preview,
 *                   gemini-3.1-flash-lite, gemini-2.5-flash, gemini-2.5-pro
 *   openai        → gpt-5.5, gpt-5.5-pro, gpt-5.4, gpt-5.4-pro, gpt-5.4-mini,
 *                   gpt-5.4-nano, gpt-5, gpt-5-mini, gpt-5-nano, gpt-4.1, o3, o4-mini
 *   anthropic     → claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5
 *   cohere        → command-a-03-2025, command-r-plus-08-2024,
 *                   command-r-08-2024, command-r7b-12-2024
 *
 * O campo `id` é o valor enviado no campo `model` da ChatConfig para o backend.
 * O backend lê provider:model e inicializa o LLM correto via `load_llm()`.
 */

// =============================================================================
// Config Storage
// =============================================================================

/** Bump version to force reset of saved user configs */
export const CONFIG_STORAGE = {
  key: "agent-config",
  versionKey: "agent-config-version",
  version: "1.0",
} as const;

// =============================================================================
// Model Registry
// =============================================================================

interface ModelConfig {
  id: string;
  name: string;
  provider: "google-genai" | "openai" | "anthropic" | "cohere";
  description?: string;
}

/**
 * Todos os modelos disponíveis — fonte única da verdade.
 * Formato id: "<provider>:<model>" — espelhado pelo load_llm() do backend.
 */
export const MODELS = {
  // ── Google Gemini 3.x ─────────────────────────────────────────────────────
  "gemini-3.5-flash": {
    id: "google-genai:gemini-3.5-flash",
    name: "Gemini 3.5 Flash",
    provider: "google-genai",
    description: "Geração atual — rápido e capaz (Google)",
  },
  "gemini-3.1-pro-preview": {
    id: "google-genai:gemini-3.1-pro-preview",
    name: "Gemini 3.1 Pro Preview",
    provider: "google-genai",
    description: "Preview avançado (Google)",
  },
  "gemini-3-flash-preview": {
    id: "google-genai:gemini-3-flash-preview",
    name: "Gemini 3 Flash Preview",
    provider: "google-genai",
    description: "Preview rápido (Google)",
  },
  "gemini-3.1-flash-lite": {
    id: "google-genai:gemini-3.1-flash-lite",
    name: "Gemini 3.1 Flash Lite",
    provider: "google-genai",
    description: "Ultra-leve e econômico (Google)",
  },
  // ── Google Gemini 2.5 ─────────────────────────────────────────────────────
  "gemini-2.5-flash": {
    id: "google-genai:gemini-2.5-flash",
    name: "Gemini 2.5 Flash",
    provider: "google-genai",
    description: "Modelo padrão — rápido e capaz (Google)",
  },
  "gemini-2.5-pro": {
    id: "google-genai:gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    provider: "google-genai",
    description: "Alta capacidade (Google)",
  },
  // ── OpenAI GPT-5.5 ────────────────────────────────────────────────────────
  "gpt-5.5": {
    id: "openai:gpt-5.5",
    name: "GPT-5.5",
    provider: "openai",
    description: "Frontier — geração atual (OpenAI)",
  },
  "gpt-5.5-pro": {
    id: "openai:gpt-5.5-pro",
    name: "GPT-5.5 Pro",
    provider: "openai",
    description: "Frontier Pro (OpenAI)",
  },
  // ── OpenAI GPT-5.4 ────────────────────────────────────────────────────────
  "gpt-5.4": {
    id: "openai:gpt-5.4",
    name: "GPT-5.4",
    provider: "openai",
    description: "Alto desempenho (OpenAI)",
  },
  "gpt-5.4-pro": {
    id: "openai:gpt-5.4-pro",
    name: "GPT-5.4 Pro",
    provider: "openai",
    description: "Alto desempenho Pro (OpenAI)",
  },
  "gpt-5.4-mini": {
    id: "openai:gpt-5.4-mini",
    name: "GPT-5.4 Mini",
    provider: "openai",
    description: "Equilibrado e eficiente (OpenAI)",
  },
  "gpt-5.4-nano": {
    id: "openai:gpt-5.4-nano",
    name: "GPT-5.4 Nano",
    provider: "openai",
    description: "Ultra-leve (OpenAI)",
  },
  // ── OpenAI GPT-5 ──────────────────────────────────────────────────────────
  "gpt-5": {
    id: "openai:gpt-5",
    name: "GPT-5",
    provider: "openai",
    description: "Geração anterior — estável (OpenAI)",
  },
  "gpt-5-mini": {
    id: "openai:gpt-5-mini",
    name: "GPT-5 Mini",
    provider: "openai",
    description: "Eficiente (OpenAI)",
  },
  "gpt-5-nano": {
    id: "openai:gpt-5-nano",
    name: "GPT-5 Nano",
    provider: "openai",
    description: "Ultra-leve (OpenAI)",
  },
  // ── OpenAI GPT-4.1 + raciocínio ───────────────────────────────────────────
  "gpt-4.1": {
    id: "openai:gpt-4.1",
    name: "GPT-4.1",
    provider: "openai",
    description: "Instrução e código (OpenAI)",
  },
  o3: {
    id: "openai:o3",
    name: "o3",
    provider: "openai",
    description: "Raciocínio avançado (OpenAI)",
  },
  "o4-mini": {
    id: "openai:o4-mini",
    name: "o4-mini",
    provider: "openai",
    description: "Raciocínio eficiente (OpenAI)",
  },
  // ── Anthropic Claude 4 ────────────────────────────────────────────────────
  "claude-opus-4-7": {
    id: "anthropic:claude-opus-4-7",
    name: "Claude Opus 4.7",
    provider: "anthropic",
    description: "Máxima capacidade (Anthropic)",
  },
  "claude-sonnet-4-6": {
    id: "anthropic:claude-sonnet-4-6",
    name: "Claude Sonnet 4.6",
    provider: "anthropic",
    description: "Equilíbrio velocidade/qualidade (Anthropic)",
  },
  "claude-haiku-4-5": {
    id: "anthropic:claude-haiku-4-5",
    name: "Claude Haiku 4.5",
    provider: "anthropic",
    description: "Ultra-rápido e econômico (Anthropic)",
  },
  // ── Cohere ────────────────────────────────────────────────────────────────
  "command-a-03-2025": {
    id: "cohere:command-a-03-2025",
    name: "Command A (Mar 2025)",
    provider: "cohere",
    description: "Geração atual (Cohere)",
  },
  "command-r-plus-08-2024": {
    id: "cohere:command-r-plus-08-2024",
    name: "Command R+ (Aug 2024)",
    provider: "cohere",
    description: "Alto desempenho RAG (Cohere)",
  },
  "command-r-08-2024": {
    id: "cohere:command-r-08-2024",
    name: "Command R (Aug 2024)",
    provider: "cohere",
    description: "RAG eficiente (Cohere)",
  },
  "command-r7b-12-2024": {
    id: "cohere:command-r7b-12-2024",
    name: "Command R7B (Dec 2024)",
    provider: "cohere",
    description: "Modelo compacto (Cohere)",
  },
} as const satisfies Record<string, ModelConfig>;

export type ModelKey = keyof typeof MODELS;
export type ModelOption = (typeof MODELS)[ModelKey]["id"];

// =============================================================================
// Agent Registry  (Vectora tem um único agente — o orchestrator)
// =============================================================================

interface AgentConfig {
  id: string;
  name: string;
  shortName: string;
  description?: string;
}

export const AGENTS = {
  vectora: {
    id: "vectora",
    name: "Vectora",
    shortName: "Vectora",
    description: "Agente de propósito geral com RAG nativo",
  },
} as const satisfies Record<string, AgentConfig>;

export type AgentKey = keyof typeof AGENTS;
export type AgentType = (typeof AGENTS)[AgentKey]["id"];

// =============================================================================
// Deployment
// =============================================================================

interface DeploymentConfig {
  models: ModelKey[];
  agents: AgentKey[];
  defaultModel: ModelKey;
  defaultAgent: AgentKey;
  requiresAuth: boolean;
}

const DEPLOYMENT: DeploymentConfig = {
  models: [
    // Google Gemini 3.x
    "gemini-3.5-flash",
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    // Google Gemini 2.5
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    // OpenAI GPT-5.5
    "gpt-5.5",
    "gpt-5.5-pro",
    // OpenAI GPT-5.4
    "gpt-5.4",
    "gpt-5.4-pro",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    // OpenAI GPT-5
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    // OpenAI outros
    "gpt-4.1",
    "o3",
    "o4-mini",
    // Anthropic Claude 4
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    // Cohere
    "command-a-03-2025",
    "command-r-plus-08-2024",
    "command-r-08-2024",
    "command-r7b-12-2024",
  ],
  agents: ["vectora"],
  defaultModel: "gemini-2.5-flash",
  defaultAgent: "vectora",
  requiresAuth: false,
};

// =============================================================================
// Core Functions
// =============================================================================

export function getDeploymentConfig(): DeploymentConfig {
  return DEPLOYMENT;
}

// =============================================================================
// Model Functions
// =============================================================================

export function getAllowedModels(): ModelOption[] {
  return getDeploymentConfig().models.map((key) => MODELS[key].id);
}

export function getDefaultModel(): ModelOption {
  return MODELS[getDeploymentConfig().defaultModel].id;
}

export function isModelAllowed(modelId: ModelOption): boolean {
  return getAllowedModels().includes(modelId);
}

export function getModelDisplayName(modelId: ModelOption): string {
  const model = Object.values(MODELS).find((m) => m.id === modelId);
  return model?.name ?? modelId;
}

export function getModelDescription(modelId: ModelOption): string {
  const model = Object.values(MODELS).find((m) => m.id === modelId);
  return model?.description ?? "";
}

export function getModelProvider(
  modelId: ModelOption,
): ModelConfig["provider"] {
  const model = Object.values(MODELS).find((m) => m.id === modelId);
  return model?.provider ?? "google-genai";
}

/**
 * Tamanho da janela de contexto (em tokens) do modelo, para o medidor de
 * contexto (R5). Derivado por família quando não há valor explícito: Gemini
 * trabalha em escala de milhão; os demais frontier models giram em torno de 200k.
 */
export function getContextWindow(modelId: ModelOption): number {
  if (modelId.startsWith("google-genai:")) return 1_000_000;
  if (modelId.startsWith("cohere:")) return 128_000;
  return 200_000;
}

// =============================================================================
// Agent Functions
// =============================================================================

export function getAllowedAgents(): AgentType[] {
  return getDeploymentConfig().agents.map((key) => AGENTS[key].id);
}

export function getDefaultAgent(): AgentType {
  return AGENTS[getDeploymentConfig().defaultAgent].id;
}

export function isAgentAllowed(agentId: AgentType): boolean {
  return getAllowedAgents().includes(agentId);
}

export function getAgentDisplayName(agentId: AgentType): string {
  const agent = Object.values(AGENTS).find((a) => a.id === agentId);
  return agent?.name ?? agentId;
}

export function getAgentShortDisplayName(agentId: AgentType): string {
  const agent = Object.values(AGENTS).find((a) => a.id === agentId);
  return agent?.shortName ?? agentId;
}

// =============================================================================
// Auth Functions
// =============================================================================

export function isAuthRequired(): boolean {
  return getDeploymentConfig().requiresAuth;
}
