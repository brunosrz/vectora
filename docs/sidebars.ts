import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: "doc",
      id: "intro",
      label: "Introduction",
    },
    {
      type: "category",
      label: "Getting Started",
      collapsed: false,
      items: [
        "getting-started/introduction",
        "getting-started/installation",
        "getting-started/quick-start",
        "getting-started/vectora-token",
        "getting-started/first-workspace",
        "getting-started/upgrade-from-cli",
      ],
    },
    {
      type: "category",
      label: "REST API Reference",
      collapsed: false,
      items: [
        "api-reference/overview",
        "api-reference/authentication",
        "api-reference/chat",
        "api-reference/documents",
        "api-reference/projects",
        "api-reference/webhooks",
      ],
    },
    {
      type: "category",
      label: "Guides",
      items: [
        "guides/vps-deploy",
        "guides/api-integration",
        "guides/team-setup",
        "guides/rag-guide",
        "guides/mcp-integration",
        "guides/api-keys",
        "guides/webhooks",
        "guides/git-workflows",
        "guides/sdk-python",
        "guides/sdk-typescript",
        "guides/ide-integration",
        "guides/github-actions",
        "guides/n8n-workflows",
        "guides/data-migration",
      ],
    },
    {
      type: "category",
      label: "Reference",
      items: [
        "reference/cli",
        "reference/config",
        "reference/tools",
        "reference/agents",
        "reference/mcp-server",
        "reference/acp-server",
        "reference/storage-backends",
      ],
    },
    {
      type: "category",
      label: "Self-Hosting",
      items: [
        "self-hosting/requirements",
        "self-hosting/docker",
        "self-hosting/kubernetes",
        "self-hosting/nginx-traefik",
        "self-hosting/storage-backends",
        "self-hosting/monitoring",
        "self-hosting/backup-restore",
        "self-hosting/updates",
      ],
    },
    {
      type: "doc",
      id: "changelog",
      label: "Changelog",
    },
  ],
};

export default sidebars;
