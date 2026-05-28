"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { markAsNew } from "@/lib/stores/new-thread-registry";

/**
 * Página raiz — cria um novo thread e redireciona para /session/<uuid>.
 * Preserva ?q=<prompt> se presente na URL.
 */
export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    const newThreadId = crypto.randomUUID();
    markAsNew(newThreadId);
    const target = q ? `/session/${newThreadId}?q=${encodeURIComponent(q)}` : `/session/${newThreadId}`;
    router.replace(target);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}
