"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import { sendMagicLink } from "#/server/fns/auth";
import { exportData, requestAccountDeletion } from "#/server/fns/gdpr";
import { updateProfile } from "#/server/fns/profile";
import { useAuthStore } from "#/store/auth";
import { toast } from "sonner";
import { Download, Trash2, Save } from "lucide-react";

const LANGUAGES = [
  { value: "pt", label: "Português" },
  { value: "en", label: "English" },
  { value: "es", label: "Español" },
  { value: "fr", label: "Français" },
  { value: "de", label: "Deutsch" },
  { value: "it", label: "Italiano" },
  { value: "ru", label: "Русский" },
];

export default function AccountSection() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.session);

  const [name, setName] = useState(user?.user_metadata.full_name ?? "");
  const [country, setCountry] = useState<"BR" | "INTL">(
    (user?.user_metadata.country as "BR" | "INTL" | undefined) ?? "INTL",
  );
  const [language, setLanguage] = useState<string>(
    (user?.user_metadata.language as string | undefined) ?? "pt",
  );

  const [confirmEmail, setConfirmEmail] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const profileMutation = useMutation({
    mutationFn: () =>
      updateProfile({ data: { full_name: name, country, language } }),
    onSuccess: () => toast.success(m.account_profile_saved()),
    onError: () => toast.error(m.error_generic()),
  });

  const magicLinkMutation = useMutation({
    mutationFn: () => sendMagicLink({ data: { email: user?.email ?? "" } }),
    onSuccess: () => toast.success(m.login_magic_sent()),
    onError: () => toast.error(m.error_generic()),
  });

  const exportMutation = useMutation({
    mutationFn: () => exportData(),
    onSuccess: (res) => {
      const a = document.createElement("a");
      a.href = res.url;
      a.download = "vectora-export.json";
      a.click();
    },
    onError: () => toast.error(m.error_generic()),
  });

  const deleteMutation = useMutation({
    mutationFn: () => requestAccountDeletion(),
    onSuccess: () => navigate({ to: "/" }),
    onError: () => toast.error(m.error_generic()),
  });

  const canDelete = confirmEmail === user?.email && !deleteMutation.isPending;
  const canSave = name.length >= 2 && !profileMutation.isPending;

  return (
    <div className="max-w-xl space-y-8">
      {/* Profile */}
      <div className="rounded-xl border border-brand-700 bg-brand-800/30 p-6">
        <h2 className="mb-4 text-base font-semibold text-white">
          {m.account_profile_heading()}
        </h2>
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              {m.form_name()}
            </label>
            <input
              type="text"
              value={name}
              minLength={2}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-brand-700 bg-brand-800/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              {m.form_email()}
            </label>
            <p className="rounded-xl border border-brand-700 bg-brand-800/20 px-4 py-2.5 text-sm text-slate-400">
              {user?.email}
            </p>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              {m.form_country()}
            </label>
            <div className="flex gap-2">
              {(["BR", "INTL"] as const).map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setCountry(c)}
                  className={`flex-1 rounded-xl border py-2.5 text-sm font-medium transition-all ${
                    country === c
                      ? "border-brand-500 bg-brand-500/10 text-brand-300"
                      : "border-brand-700 text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {c === "BR" ? "🇧🇷 Brasil" : "🌍 Internacional"}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              {m.account_language()}
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full rounded-xl border border-brand-700 bg-brand-800/60 px-4 py-2.5 text-sm text-white outline-none focus:border-brand-500 transition-colors"
            >
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => profileMutation.mutate()}
            disabled={!canSave}
            className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white shadow shadow-brand-500/25 transition-all hover:bg-brand-400 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Save className="h-4 w-4" />
            {profileMutation.isPending ? m.form_submitting() : m.form_save()}
          </button>
        </div>
      </div>

      {/* Security */}
      <div className="rounded-xl border border-brand-700 bg-brand-800/30 p-6">
        <h2 className="mb-4 text-base font-semibold text-white">
          {m.account_security_heading()}
        </h2>
        <p className="mb-4 text-sm text-slate-400">
          {m.account_password_desc()}
        </p>
        <button
          onClick={() => magicLinkMutation.mutate()}
          disabled={magicLinkMutation.isPending || !user?.email}
          className="rounded-xl border border-brand-700 px-4 py-2 text-sm font-medium text-slate-300 hover:border-brand-500 hover:text-white disabled:opacity-50 transition-all"
        >
          {magicLinkMutation.isPending
            ? m.form_submitting()
            : m.account_change_password()}
        </button>
      </div>

      {/* GDPR */}
      <div className="rounded-xl border border-brand-700 bg-brand-800/30 p-6">
        <h2 className="mb-4 text-base font-semibold text-white">
          {m.account_gdpr_heading()}
        </h2>

        <div className="mb-5">
          <p className="mb-3 text-sm text-slate-400">
            {m.account_export_desc()}
          </p>
          <button
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending}
            className="flex items-center gap-2 rounded-xl border border-brand-700 px-4 py-2 text-sm font-medium text-slate-300 hover:border-brand-500 hover:text-white disabled:opacity-50 transition-all"
          >
            <Download className="h-4 w-4" />
            {exportMutation.isPending
              ? m.form_submitting()
              : m.account_export_cta()}
          </button>
        </div>

        <hr className="border-brand-800 my-5" />

        <div>
          <p className="mb-3 text-sm text-slate-400">
            {m.account_delete_desc()}
          </p>
          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-2 rounded-xl border border-red-500/30 px-4 py-2 text-sm font-medium text-red-400 hover:border-red-500 hover:bg-red-500/5 transition-all"
            >
              <Trash2 className="h-4 w-4" />
              {m.account_delete_cta()}
            </button>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-red-400">
                {m.account_delete_confirm_desc()}
              </p>
              <input
                type="email"
                value={confirmEmail}
                onChange={(e) => setConfirmEmail(e.target.value)}
                placeholder={user?.email}
                className="w-full rounded-xl border border-red-500/30 bg-brand-800/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-600 outline-none focus:border-red-500 transition-colors"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setConfirmEmail("");
                  }}
                  className="rounded-xl border border-brand-700 px-4 py-2 text-sm text-slate-400 hover:text-white transition-all"
                >
                  {m.form_cancel()}
                </button>
                <button
                  onClick={() => deleteMutation.mutate()}
                  disabled={!canDelete}
                  className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-40 transition-all"
                >
                  {deleteMutation.isPending
                    ? m.form_submitting()
                    : m.account_delete_confirm_cta()}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
