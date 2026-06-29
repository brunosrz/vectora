import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";
import { themes as prismThemes } from "prism-react-renderer";

const DOCS_URL = process.env.DOCS_URL ?? "https://docs.vectora.company";
const APP_URL = process.env.APP_URL ?? "https://vectora.company";
const DISCORD_URL = process.env.DISCORD_URL ?? "https://discord.gg/vectora";
const GITHUB_URL =
  process.env.GITHUB_URL ?? "https://github.com/vectora-company/vectora";
const WHATSAPP_URL = process.env.WHATSAPP_URL ?? "https://wa.me/5535910179164";

const config: Config = {
  title: "Vectora Docs",
  tagline: "Self-hosted AI agent — documentation",
  favicon: "/img/favicon.ico",

  url: DOCS_URL,
  baseUrl: "/",

  organizationName: "vectora-company",
  projectName: "vectora",

  onBrokenLinks: "warn",
  onBrokenMarkdownLinks: "warn",

  i18n: {
    defaultLocale: "en",
    locales: ["en", "pt"],
    localeConfigs: {
      en: { label: "English", htmlLang: "en" },
      pt: { label: "Português", htmlLang: "pt-BR" },
    },
  },

  plugins: [
    [
      "@easyops-cn/docusaurus-search-local",
      {
        hashed: true,
        language: ["en", "pt"],
        indexBlog: false,
        docsRouteBasePath: "/",
        searchBarShortcutHint: false,
      },
    ],
  ],

  presets: [
    [
      "classic",
      {
        docs: {
          sidebarPath: "./sidebars.ts",
          routeBasePath: "/",
          editUrl: undefined,
          showLastUpdateTime: false,
          breadcrumbs: true,
        },
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
        sitemap: {
          changefreq: "weekly",
          priority: 0.8,
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      defaultMode: "dark",
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },

    image: "/img/vectora-og.png",

    navbar: {
      title: "Vectora",
      logo: {
        alt: "Vectora",
        src: "/img/vectora-logo.svg",
        href: "/",
      },
      items: [
        {
          type: "docSidebar",
          sidebarId: "docsSidebar",
          position: "left",
          label: "Docs",
        },
        {
          to: "/api-reference/overview",
          position: "left",
          label: "API",
        },
        {
          href: APP_URL,
          label: "vectora.company",
          position: "right",
        },
        {
          href: `${APP_URL}/signup`,
          label: "Start free trial →",
          position: "right",
          className: "navbar-cta",
        },
      ],
    },

    footer: {
      style: "dark",
      links: [
        {
          title: "Documentation",
          items: [
            { label: "Installation", to: "/getting-started/installation" },
            { label: "Quick start", to: "/getting-started/quick-start" },
            { label: "REST API", to: "/api-reference/overview" },
            { label: "Self-hosting", to: "/self-hosting/requirements" },
          ],
        },
        {
          title: "Guides",
          items: [
            { label: "VPS deployment", to: "/guides/vps-deploy" },
            { label: "API integration", to: "/guides/api-integration" },
            { label: "RAG pipeline", to: "/guides/rag-guide" },
            { label: "MCP integration", to: "/guides/mcp-integration" },
          ],
        },
        {
          title: "Product",
          items: [
            { label: "Pricing", href: `${APP_URL}/#pricing` },
            { label: "Roadmap", href: `${APP_URL}/roadmap` },
            { label: "Changelog", to: "/changelog" },
            { label: "Issues", href: `${APP_URL}/issues` },
          ],
        },
        {
          title: "Community",
          items: [
            { label: "Discord", href: DISCORD_URL },
            { label: "GitHub", href: GITHUB_URL },
            { label: "WhatsApp", href: WHATSAPP_URL },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Vectora. All rights reserved.`,
    },

    prism: {
      theme: prismThemes.vsDark,
      darkTheme: prismThemes.vsDark,
      additionalLanguages: [
        "bash",
        "python",
        "typescript",
        "json",
        "yaml",
        "docker",
        "toml",
      ],
    },

    docs: {
      sidebar: {
        hideable: true,
        autoCollapseCategories: true,
      },
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
