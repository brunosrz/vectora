#!/usr/bin/env node
/**
 * lint-i18n — auditoria de cobertura de traduções.
 *
 * Extrai chaves do CSV de strings e varre todo o código-fonte em busca de
 * chamadas `t("key")` / `t('key')`. Reporta:
 *   • chaves usadas no código mas ausentes no CSV  (MISSING)
 *   • chaves no CSV mas não usadas no código       (UNUSED)
 *
 * Saída: tabela no stdout. Código de saída 1 se houver MISSING keys.
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { join, extname } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __dir = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dir, "..");

// ---------------------------------------------------------------------------
// 1. Ler CSV de strings e extrair chaves definidas
// ---------------------------------------------------------------------------

const csvPath = join(ROOT, "lib", "i18n", "strings.csv.ts");
const csvContent = readFileSync(csvPath, "utf8");

// Extrai a string CSV do template literal (de `\`` até o próximo `\``)
const csvMatch = csvContent.match(/const CSV = `\\?\n?([\s\S]+?)`\s*;/);
if (!csvMatch) {
  console.error("ERRO: Não foi possível extrair o CSV de strings.csv.ts");
  process.exit(2);
}

const csvLines = csvMatch[1]
  .split("\n")
  .map((l) => l.trimEnd())
  .filter((l) => l.length > 0 && !l.startsWith("#"));

const definedKeys = new Set();
// Pula cabeçalho (key,en,es,pt)
for (const line of csvLines.slice(1)) {
  let key = line.split(",")[0]?.trim() ?? "";
  // Desquota campos entre aspas duplas (RFC 4180).
  if (key.startsWith('"') && key.endsWith('"')) key = key.slice(1, -1);
  if (key) definedKeys.add(key);
}

// ---------------------------------------------------------------------------
// 2. Varrer código-fonte e extrair chaves usadas
// ---------------------------------------------------------------------------

const SRC_DIRS = ["src", "components", "lib", "hooks"];
const EXTENSIONS = new Set([".ts", ".tsx"]);

/** Recursivamente lista arquivos. */
function walk(dir) {
  const entries = readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (entry.name === "node_modules" || entry.name === ".next") continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(full));
    } else if (EXTENSIONS.has(extname(entry.name))) {
      files.push(full);
    }
  }
  return files;
}

const sourceFiles = SRC_DIRS.flatMap((d) => {
  const full = join(ROOT, d);
  try {
    statSync(full);
    return walk(full);
  } catch {
    return [];
  }
});

// Regex para t("key") e t('key') — também captura chaves com ponto e hífen.
// Chaves válidas sempre contêm pelo menos um ponto (ex: "chat.rewind").
const KEY_RE = /\bt\(\s*["']([a-zA-Z0-9_.:-]+)["']/g;

const usedKeys = new Set();
const usedInFiles = new Map(); // key → arquivo (para debug)

for (const file of sourceFiles) {
  const content = readFileSync(file, "utf8");
  let m;
  KEY_RE.lastIndex = 0;
  while ((m = KEY_RE.exec(content)) !== null) {
    const key = m[1];
    // Ignora falsos positivos: chaves i18n reais sempre contêm um ponto.
    if (!key.includes(".")) continue;
    usedKeys.add(key);
    if (!usedInFiles.has(key)) {
      usedInFiles.set(key, file.replace(ROOT, "").replace(/\\/g, "/"));
    }
  }
}

// ---------------------------------------------------------------------------
// 3. Calcular diff
// ---------------------------------------------------------------------------

const missing = [...usedKeys].filter((k) => !definedKeys.has(k));
const unused = [...definedKeys].filter((k) => !usedKeys.has(k));

// ---------------------------------------------------------------------------
// 4. Relatório
// ---------------------------------------------------------------------------

const W = process.stdout.columns || 100;
const hr = "─".repeat(Math.min(W, 80));

console.log(`\n${hr}`);
console.log(`  Vectora i18n audit`);
console.log(`  Chaves definidas : ${definedKeys.size}`);
console.log(`  Chaves usadas    : ${usedKeys.size}`);
console.log(`  Arquivos varridos: ${sourceFiles.length}`);
console.log(hr);

if (missing.length > 0) {
  console.log(
    `\n🔴  MISSING (${missing.length}) — usadas no código mas ausentes no CSV:\n`,
  );
  for (const key of missing.sort()) {
    const file = usedInFiles.get(key) ?? "?";
    console.log(`   ✗  ${key.padEnd(50)}  ${file}`);
  }
}

if (unused.length > 0) {
  console.log(
    `\n🟡  UNUSED (${unused.length}) — no CSV mas não usadas no código:\n`,
  );
  for (const key of unused.sort()) {
    console.log(`   ~  ${key}`);
  }
}

if (missing.length === 0 && unused.length === 0) {
  console.log("\n✅  Todas as chaves estão cobertas.");
}

console.log(`\n${hr}\n`);

// Sai com código 1 se há chaves faltando (bloqueia CI).
if (missing.length > 0) {
  process.exit(1);
}
