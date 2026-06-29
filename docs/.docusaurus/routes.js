import React from "react";
import ComponentCreator from "@docusaurus/ComponentCreator";

export default [
  {
    path: "/pt/search",
    component: ComponentCreator("/pt/search", "24b"),
    exact: true,
  },
  {
    path: "/pt/",
    component: ComponentCreator("/pt/", "cb1"),
    exact: true,
  },
  {
    path: "/pt/",
    component: ComponentCreator("/pt/", "e93"),
    routes: [
      {
        path: "/pt/",
        component: ComponentCreator("/pt/", "8ee"),
        routes: [
          {
            path: "/pt/",
            component: ComponentCreator("/pt/", "e09"),
            routes: [
              {
                path: "/pt/api-reference/authentication",
                component: ComponentCreator(
                  "/pt/api-reference/authentication",
                  "de0",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/api-reference/chat",
                component: ComponentCreator("/pt/api-reference/chat", "568"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/api-reference/documents",
                component: ComponentCreator(
                  "/pt/api-reference/documents",
                  "b7f",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/api-reference/overview",
                component: ComponentCreator(
                  "/pt/api-reference/overview",
                  "e9c",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/api-reference/projects",
                component: ComponentCreator(
                  "/pt/api-reference/projects",
                  "470",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/api-reference/webhooks",
                component: ComponentCreator(
                  "/pt/api-reference/webhooks",
                  "5b4",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/changelog",
                component: ComponentCreator("/pt/changelog", "036"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/getting-started/first-workspace",
                component: ComponentCreator(
                  "/pt/getting-started/first-workspace",
                  "d27",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/getting-started/installation",
                component: ComponentCreator(
                  "/pt/getting-started/installation",
                  "9e8",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/getting-started/introduction",
                component: ComponentCreator(
                  "/pt/getting-started/introduction",
                  "211",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/getting-started/quick-start",
                component: ComponentCreator(
                  "/pt/getting-started/quick-start",
                  "557",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/getting-started/upgrade-from-cli",
                component: ComponentCreator(
                  "/pt/getting-started/upgrade-from-cli",
                  "472",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/getting-started/vectora-token",
                component: ComponentCreator(
                  "/pt/getting-started/vectora-token",
                  "7a2",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/api-keys",
                component: ComponentCreator("/pt/guides/api-keys", "ad4"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/data-migration",
                component: ComponentCreator("/pt/guides/data-migration", "cc2"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/git-workflows",
                component: ComponentCreator("/pt/guides/git-workflows", "56f"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/github-actions",
                component: ComponentCreator("/pt/guides/github-actions", "596"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/ide-integration",
                component: ComponentCreator(
                  "/pt/guides/ide-integration",
                  "9f0",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/mcp-integration",
                component: ComponentCreator(
                  "/pt/guides/mcp-integration",
                  "8c4",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/n8n-workflows",
                component: ComponentCreator("/pt/guides/n8n-workflows", "382"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/rag-guide",
                component: ComponentCreator("/pt/guides/rag-guide", "392"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/sdk-python",
                component: ComponentCreator("/pt/guides/sdk-python", "535"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/sdk-typescript",
                component: ComponentCreator("/pt/guides/sdk-typescript", "59c"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/team-setup",
                component: ComponentCreator("/pt/guides/team-setup", "225"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/vps-deploy",
                component: ComponentCreator("/pt/guides/vps-deploy", "487"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/guides/webhooks",
                component: ComponentCreator("/pt/guides/webhooks", "c1d"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/intro",
                component: ComponentCreator("/pt/intro", "324"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/reference/acp-server",
                component: ComponentCreator("/pt/reference/acp-server", "6b9"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/reference/agents",
                component: ComponentCreator("/pt/reference/agents", "217"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/reference/cli",
                component: ComponentCreator("/pt/reference/cli", "5e0"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/reference/config",
                component: ComponentCreator("/pt/reference/config", "889"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/reference/mcp-server",
                component: ComponentCreator("/pt/reference/mcp-server", "7f2"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/reference/storage-backends",
                component: ComponentCreator(
                  "/pt/reference/storage-backends",
                  "e57",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/reference/tools",
                component: ComponentCreator("/pt/reference/tools", "dd9"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/self-hosting/backup-restore",
                component: ComponentCreator(
                  "/pt/self-hosting/backup-restore",
                  "c22",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/self-hosting/docker",
                component: ComponentCreator("/pt/self-hosting/docker", "407"),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/self-hosting/kubernetes",
                component: ComponentCreator(
                  "/pt/self-hosting/kubernetes",
                  "165",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/self-hosting/monitoring",
                component: ComponentCreator(
                  "/pt/self-hosting/monitoring",
                  "0c9",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/self-hosting/nginx-traefik",
                component: ComponentCreator(
                  "/pt/self-hosting/nginx-traefik",
                  "200",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/self-hosting/requirements",
                component: ComponentCreator(
                  "/pt/self-hosting/requirements",
                  "832",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/self-hosting/storage-backends",
                component: ComponentCreator(
                  "/pt/self-hosting/storage-backends",
                  "ec0",
                ),
                exact: true,
                sidebar: "docsSidebar",
              },
              {
                path: "/pt/self-hosting/updates",
                component: ComponentCreator("/pt/self-hosting/updates", "ebf"),
                exact: true,
                sidebar: "docsSidebar",
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: "*",
    component: ComponentCreator("*"),
  },
];
