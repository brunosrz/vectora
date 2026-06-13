import { createFileRoute } from "@tanstack/react-router";

const BRAND = {
  bg: "#0a0e1a",
  border: "#1e3a5f",
  accent: "#3b82f6",
  text: "#f8fafc",
  muted: "#94a3b8",
};

async function buildOgSvg(title: string, desc: string): Promise<string> {
  // Imports dinâmicos: node:fs/node:path no top-level entram no bundle do
  // client via route tree e quebram a hidratação da página inteira.
  const [{ readFile }, { join }, { default: satori }] = await Promise.all([
    import("node:fs/promises"),
    import("node:path"),
    import("satori"),
  ]);

  const fontPath = join(process.cwd(), "public/fonts/aeonikmono-regular.otf");
  const buf = await readFile(fontPath);
  const fontData: ArrayBuffer = buf.buffer.slice(
    buf.byteOffset,
    buf.byteOffset + buf.byteLength,
  );

  return satori(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: BRAND.bg,
        padding: "60px 72px",
        fontFamily: "AeonikMono",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div
          style={{
            display: "flex",
            width: "40px",
            height: "40px",
            borderRadius: "10px",
            background: BRAND.accent,
            alignItems: "center",
            justifyContent: "center",
            fontSize: "22px",
            color: "#fff",
            fontWeight: 700,
          }}
        >
          V
        </div>
        <span style={{ color: BRAND.text, fontSize: "22px", fontWeight: 700 }}>
          Vectora
        </span>
        <div
          style={{
            marginLeft: "12px",
            background: `${BRAND.accent}20`,
            border: `1px solid ${BRAND.accent}40`,
            borderRadius: "999px",
            padding: "4px 16px",
            fontSize: "13px",
            color: BRAND.accent,
            display: "flex",
          }}
        >
          Self-hosted · Privacy-first
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        <div
          style={{
            fontSize: "58px",
            fontWeight: 700,
            color: BRAND.text,
            lineHeight: 1.1,
            letterSpacing: "-0.02em",
            maxWidth: "900px",
          }}
        >
          {title}
        </div>
        {desc && (
          <div
            style={{
              fontSize: "24px",
              color: BRAND.muted,
              lineHeight: 1.4,
              maxWidth: "780px",
            }}
          >
            {desc}
          </div>
        )}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ color: BRAND.muted, fontSize: "16px" }}>
          vectora.company
        </span>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "999px",
              background: "#4ade80",
              display: "flex",
            }}
          />
          <span style={{ color: BRAND.muted, fontSize: "14px" }}>
            30-day free trial
          </span>
        </div>
      </div>
    </div>,
    {
      width: 1200,
      height: 630,
      fonts: [
        {
          name: "AeonikMono",
          data: fontData,
          weight: 400,
          style: "normal",
        },
      ],
    },
  );
}

export const Route = createFileRoute("/api/og")({
  validateSearch: (search: Record<string, unknown>) => ({
    title: typeof search.title === "string" ? search.title : "Vectora",
    desc:
      typeof search.desc === "string"
        ? search.desc
        : "Your AI. Your Data. Your Server.",
  }),
  loaderDeps: ({ search: { title, desc } }) => ({ title, desc }),
  loader: async ({ deps }) => {
    const svg = await buildOgSvg(deps.title, deps.desc);
    return new Response(svg, {
      headers: {
        "Content-Type": "image/svg+xml",
        "Cache-Control": "public, max-age=86400, stale-while-revalidate=3600",
      },
    });
  },
  component: () => null,
});
