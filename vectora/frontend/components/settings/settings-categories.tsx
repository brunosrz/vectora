"use client";

/**
 * Registro das categorias do `SettingsOverlay` — remapeamento 1:1 das
 * ~12 abas que hoje vivem espalhadas em 3 diálogos Radix independentes,
 * mais Plugins/Skills/Tool Policy (componentes prontos, mas nunca
 * renderizados por nenhum dos 3 diálogos até agora) e Billing/About
 * (conteúdo real relocado, não placeholder — CLAUDE.md §9).
 *
 * Cada categoria aponta pro MESMO componente de conteúdo que já existia
 * — o remapeamento troca só a casca (onde a categoria aparece e como se
 * navega até ela), nunca reescreve a lógica de negócio de dentro.
 */

import type { ComponentType } from "react";

import { lazyWithRetry } from "@/lib/lazy-with-retry";
import { m } from "@/lib/paraglide/messages";
import type { SettingsCategoryId } from "@/lib/stores/settings-overlay-store";

const GeralTab = lazyWithRetry(
  () =>
    import("./preferencias/tabs/preferencias-tab").then((mod) => ({
      default: mod.PreferenciasTab,
    })),
  "settings-geral-tab",
);
const FallbacksTab = lazyWithRetry(
  () =>
    import("./preferencias/tabs/fallbacks-tab").then((mod) => ({
      default: mod.FallbacksTab,
    })),
  "settings-fallbacks-tab",
);
const MemoriaTab = lazyWithRetry(
  () =>
    import("./preferencias/tabs/memoria-tab").then((mod) => ({
      default: mod.MemoriaTab,
    })),
  "settings-memoria-tab",
);
const ContaTab = lazyWithRetry(
  () =>
    import("./preferencias/tabs/conta-tab").then((mod) => ({
      default: mod.ContaTab,
    })),
  "settings-conta-tab",
);
const IntegracoesTab = lazyWithRetry(
  () =>
    import("./environment/tabs/integracoes-tab").then((mod) => ({
      default: mod.IntegracoesTab,
    })),
  "settings-integracoes-tab",
);
const ProviderRoutingTab = lazyWithRetry(
  () =>
    import("./environment/tabs/provider-routing-tab").then((mod) => ({
      default: mod.ProviderRoutingTab,
    })),
  "settings-provider-routing-tab",
);
const ConnectTab = lazyWithRetry(
  () =>
    import("./environment/tabs/connect-tab").then((mod) => ({
      default: mod.ConnectTab,
    })),
  "settings-connect-tab",
);
const PluginsTab = lazyWithRetry(
  () =>
    import("./environment/tabs/plugins-tab").then((mod) => ({
      default: mod.PluginsTab,
    })),
  "settings-plugins-tab",
);
const SkillsTab = lazyWithRetry(
  () =>
    import("./environment/tabs/skills-tab").then((mod) => {
      // `SkillsTab` só aceita `onSkillsChange` opcional, mas TS não permite
      // atribuir a `ComponentType<unknown>` (contravariância estrita) — o
      // wrapper só existe pra satisfazer o tipo, roda uma vez por load.
      // oxlint-disable-next-line unicorn/consistent-function-scoping
      const Wrapped = () => <mod.SkillsTab />;
      return { default: Wrapped };
    }),
  "settings-skills-tab",
);
const ToolPolicyPanel = lazyWithRetry(
  () =>
    import("./environment/tabs/tool-policy-panel").then((mod) => ({
      default: mod.ToolPolicyPanel,
    })),
  "settings-tool-policy-tab",
);
const AdminTab = lazyWithRetry(
  () =>
    import("./administracao/admin-tab").then((mod) => ({
      default: mod.AdminTab,
    })),
  "settings-admin-tab",
);
const BillingPanelLazy = lazyWithRetry(
  () =>
    import("./billing-panel").then((mod) => ({ default: mod.BillingPanel })),
  "settings-billing-tab",
);
const AboutPanelLazy = lazyWithRetry(
  () => import("./about-panel").then((mod) => ({ default: mod.AboutPanel })),
  "settings-about-tab",
);

export type SettingsGroupId =
  "preferencias" | "ambiente" | "administracao" | "geral_grupo";

export interface SettingsCategory {
  id: SettingsCategoryId;
  group: SettingsGroupId;
  label: string;
  Component: ComponentType<Record<string, never>>;
}

export interface SettingsCategoryGroup {
  id: SettingsGroupId;
  label: string;
  categories: SettingsCategory[];
}

interface BuildCategoriesArgs {
  connectEnabled: boolean;
  isAdmin: boolean;
}

/** Monta a lista de grupos/categorias visíveis pro usuário atual — gating
 * de feature flag (Connect) e role (Administração) decidido aqui, num só
 * lugar, em vez de espalhado pelos componentes individuais. */
export function buildSettingsCategoryGroups({
  connectEnabled,
  isAdmin,
}: BuildCategoriesArgs): SettingsCategoryGroup[] {
  const preferencias: SettingsCategory[] = [
    {
      id: "geral",
      group: "preferencias",
      label: m.settings_category_geral(),
      Component: GeralTab,
    },
    {
      id: "fallbacks",
      group: "preferencias",
      label: m.settings_category_fallbacks(),
      Component: FallbacksTab,
    },
    {
      id: "memoria",
      group: "preferencias",
      label: m.settings_category_memoria(),
      Component: MemoriaTab,
    },
    {
      id: "conta",
      group: "preferencias",
      label: m.settings_category_conta(),
      Component: ContaTab,
    },
  ];

  const ambiente: SettingsCategory[] = [
    {
      id: "integracoes",
      group: "ambiente",
      label: m.settings_category_integracoes(),
      Component: IntegracoesTab,
    },
    {
      id: "provider_routing",
      group: "ambiente",
      label: m.settings_category_provider_routing(),
      Component: ProviderRoutingTab,
    },
    ...(connectEnabled
      ? ([
          {
            id: "connect",
            group: "ambiente",
            label: m.settings_category_connect(),
            Component: ConnectTab,
          },
        ] as SettingsCategory[])
      : []),
    {
      id: "plugins",
      group: "ambiente",
      label: m.settings_category_plugins(),
      Component: PluginsTab,
    },
    {
      id: "skills",
      group: "ambiente",
      label: m.settings_category_skills(),
      Component: SkillsTab,
    },
    {
      id: "tool_policy",
      group: "ambiente",
      label: m.settings_category_tool_policy(),
      Component: ToolPolicyPanel,
    },
  ];

  const administracao: SettingsCategory[] = isAdmin
    ? [
        {
          id: "administracao",
          group: "administracao",
          label: m.settings_category_administracao(),
          Component: AdminTab,
        },
      ]
    : [];

  const geralGrupo: SettingsCategory[] = [
    {
      id: "billing",
      group: "geral_grupo",
      label: m.settings_category_billing(),
      Component: BillingPanelLazy,
    },
    {
      id: "about",
      group: "geral_grupo",
      label: m.settings_category_about(),
      Component: AboutPanelLazy,
    },
  ];

  const groups: SettingsCategoryGroup[] = [
    {
      id: "preferencias",
      label: m.settings_group_preferencias(),
      categories: preferencias,
    },
    {
      id: "ambiente",
      label: m.settings_group_environment(),
      categories: ambiente,
    },
  ];
  if (administracao.length > 0) {
    groups.push({
      id: "administracao",
      label: m.settings_group_admin(),
      categories: administracao,
    });
  }
  groups.push({ id: "geral_grupo", label: "", categories: geralGrupo });

  return groups;
}

export function findCategory(
  groups: SettingsCategoryGroup[],
  id: SettingsCategoryId,
): SettingsCategory | undefined {
  for (const group of groups) {
    const found = group.categories.find((c) => c.id === id);
    if (found) return found;
  }
  return undefined;
}

/** Fallback pra quando `activeCategory` persistido/pedido não existe mais
 * na lista visível (ex.: usuário perdeu role admin) — nunca renderiza tela
 * em branco. */
export function firstAvailableCategory(
  groups: SettingsCategoryGroup[],
): SettingsCategoryId {
  for (const group of groups) {
    if (group.categories[0]) return group.categories[0].id;
  }
  return "geral";
}
