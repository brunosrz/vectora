import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { m } from "#/paraglide/messages";
import Container from "#/components/shared/Container";
import PageHeader from "#/components/shared/PageHeader";

// Base das releases. Ajuste os nomes dos assets conforme o que o build do
// Electron publica (electron-builder). Mantido num único ponto para edição.
const RELEASE_BASE =
  "https://github.com/vectora-company/vectora/releases/latest/download";

type OS = "windows" | "macos" | "linux";

interface Platform {
  os: OS;
  label: string;
  emoji: string;
  sub: string;
  href: string;
}

const PLATFORMS: Platform[] = [
  {
    os: "windows",
    label: "Windows",
    emoji: "🪟",
    sub: ".exe · Windows 10/11 (x64)",
    href: `${RELEASE_BASE}/Vectora-Setup.exe`,
  },
  {
    os: "macos",
    label: "macOS",
    emoji: "🍎",
    sub: ".dmg · Apple Silicon & Intel",
    href: `${RELEASE_BASE}/Vectora.dmg`,
  },
  {
    os: "linux",
    label: "Linux",
    emoji: "🐧",
    sub: ".AppImage · x86_64",
    href: `${RELEASE_BASE}/Vectora.AppImage`,
  },
];

/** Detecta o SO pelo userAgent (client-only — SSR retorna null). */
function detectOS(): OS | null {
  if (typeof navigator === "undefined") return null;
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("win")) return "windows";
  if (ua.includes("mac")) return "macos";
  if (ua.includes("linux") || ua.includes("x11")) return "linux";
  return null;
}

export const Route = createFileRoute("/downloads")({
  head: () => ({
    meta: [
      { title: m.page_downloads_title() },
      { name: "description", content: m.page_downloads_desc() },
    ],
  }),
  component: DownloadsPage,
});

function DownloadsPage() {
  const [userOS, setUserOS] = useState<OS | null>(null);
  useEffect(() => setUserOS(detectOS()), []);

  // O SO detectado vem primeiro (destacado como recomendado).
  const ordered = [...PLATFORMS].sort((a, b) =>
    a.os === userOS ? -1 : b.os === userOS ? 1 : 0,
  );

  return (
    <Container size="default" className="py-16">
      <PageHeader title={m.page_downloads_title()}>
        <p className="mt-2 text-muted-foreground">{m.page_downloads_desc()}</p>
      </PageHeader>

      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {ordered.map((p) => {
          const recommended = p.os === userOS;
          return (
            <a
              key={p.os}
              href={p.href}
              className={`flex flex-col items-center gap-3 rounded-2xl border p-6 text-center transition-all ${
                recommended
                  ? "border-primary bg-primary/5"
                  : "border-border bg-card/30 hover:border-primary/50"
              }`}
            >
              <span className="h-5 text-[11px] font-semibold uppercase tracking-wide text-primary">
                {recommended ? m.downloads_recommended() : ""}
              </span>
              <span className="text-4xl leading-none" aria-hidden>
                {p.emoji}
              </span>
              <div>
                <p className="font-semibold text-foreground">{p.label}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{p.sub}</p>
              </div>
              <span className="mt-2 inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground">
                <Download className="h-4 w-4" />
                {m.downloads_cta()}
              </span>
            </a>
          );
        })}
      </div>

      <p className="mt-8 text-center text-xs text-muted-foreground">
        {m.downloads_footer()}
      </p>
    </Container>
  );
}
