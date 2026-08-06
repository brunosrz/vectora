"use client";

import { useState } from "react";
import {
  Plug,
  Save,
  KeyRound,
  Loader2,
  Mail,
  MessageCircle,
  Webhook,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ProBadge } from "@/components/ui/pro-badge";
import { m } from "@/lib/paraglide/messages";
import { useToastStore } from "@/lib/stores/toast-store";

interface ConnectConfig {
  TELEGRAM_BOT_TOKEN: string;
  DISCORD_BOT_TOKEN: string;
  DISCORD_APPLICATION_ID: string;
  EMAIL_SMTP_HOST: string;
  EMAIL_IMAP_HOST: string;
}

export function ConnectTab() {
  const [loading, setLoading] = useState(false);
  const [configs, setConfigs] = useState<ConnectConfig>({
    TELEGRAM_BOT_TOKEN: "",
    DISCORD_BOT_TOKEN: "",
    DISCORD_APPLICATION_ID: "",
    EMAIL_SMTP_HOST: "",
    EMAIL_IMAP_HOST: "",
  });

  const handleSave = async () => {
    setLoading(true);
    try {
      const payload = Object.entries(configs)
        .filter(([_, v]) => v.trim() !== "")
        .map(([k, v]) => ({ key: k, value: v }));

      if (payload.length === 0) {
        useToastStore.getState().warning("Nenhuma configuração para salvar.");
        return;
      }

      const res = await fetch("/auth/envs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Falha ao salvar configurações.");

      useToastStore
        .getState()
        .success("Configurações do Connect salvas com sucesso.");
    } catch (error) {
      useToastStore
        .getState()
        .error("Erro ao salvar configurações", { description: String(error) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 pb-6">
      <div className="space-y-1">
        <h3 className="text-lg font-medium flex items-center gap-2">
          <Plug className="w-5 h-5 text-muted-foreground" />
          Vectora Connect
        </h3>
        <p className="text-sm text-muted-foreground">
          Conecte o Vectora a plataformas externas para receber e responder
          mensagens através de mensageiros e e-mail.
        </p>
      </div>

      <div className="space-y-4">
        {/* Telegram */}
        <div className="rounded-lg border bg-card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <MessageCircle className="w-5 h-5 text-blue-500" />
              <div>
                <h4 className="text-sm font-semibold flex items-center gap-1.5">
                  Telegram
                  <ProBadge />
                </h4>
                <p className="text-xs text-muted-foreground">
                  Integração via webhook oficial do Telegram Bot API
                </p>
              </div>
            </div>
            <Badge
              variant={configs.TELEGRAM_BOT_TOKEN ? "default" : "secondary"}
            >
              {configs.TELEGRAM_BOT_TOKEN ? "Configurado" : "Pendente"}
            </Badge>
          </div>
          <div className="space-y-2">
            <Label className="text-xs">Bot Token</Label>
            <Input
              type="password"
              placeholder="Ex: 123456789:ABCdefGHIjklMNO..."
              value={configs.TELEGRAM_BOT_TOKEN}
              onChange={(e) =>
                setConfigs({ ...configs, TELEGRAM_BOT_TOKEN: e.target.value })
              }
            />
          </div>
        </div>

        {/* Discord */}
        <div className="rounded-lg border bg-card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <MessageCircle className="w-5 h-5 text-indigo-500" />
              <div>
                <h4 className="text-sm font-semibold flex items-center gap-1.5">
                  Discord
                  <ProBadge />
                </h4>
                <p className="text-xs text-muted-foreground">
                  Responda mensagens em servidores do Discord
                </p>
              </div>
            </div>
            <Badge
              variant={configs.DISCORD_BOT_TOKEN ? "default" : "secondary"}
            >
              {configs.DISCORD_BOT_TOKEN ? "Configurado" : "Pendente"}
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-xs">Application ID</Label>
              <Input
                placeholder="Ex: 123456789012345678"
                value={configs.DISCORD_APPLICATION_ID}
                onChange={(e) =>
                  setConfigs({
                    ...configs,
                    DISCORD_APPLICATION_ID: e.target.value,
                  })
                }
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Bot Token</Label>
              <Input
                type="password"
                placeholder="Ex: MTA..."
                value={configs.DISCORD_BOT_TOKEN}
                onChange={(e) =>
                  setConfigs({ ...configs, DISCORD_BOT_TOKEN: e.target.value })
                }
              />
            </div>
          </div>
        </div>

        {/* Email */}
        <div className="rounded-lg border bg-card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-red-500" />
              <div>
                <h4 className="text-sm font-semibold flex items-center gap-1.5">
                  Email (IMAP/SMTP)
                  <ProBadge />
                </h4>
                <p className="text-xs text-muted-foreground">
                  Delegue ao assistente a leitura e resposta de e-mails
                </p>
              </div>
            </div>
            <Badge variant={configs.EMAIL_IMAP_HOST ? "default" : "secondary"}>
              {configs.EMAIL_IMAP_HOST ? "Configurado" : "Pendente"}
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-xs">IMAP Host (Leitura)</Label>
              <Input
                placeholder="Ex: imap.gmail.com"
                value={configs.EMAIL_IMAP_HOST}
                onChange={(e) =>
                  setConfigs({ ...configs, EMAIL_IMAP_HOST: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">SMTP Host (Envio)</Label>
              <Input
                placeholder="Ex: smtp.gmail.com"
                value={configs.EMAIL_SMTP_HOST}
                onChange={(e) =>
                  setConfigs({ ...configs, EMAIL_SMTP_HOST: e.target.value })
                }
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end mt-4">
        <Button onClick={handleSave} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Salvar Configurações
        </Button>
      </div>
    </div>
  );
}
