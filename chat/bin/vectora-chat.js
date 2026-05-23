#!/usr/bin/env node

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

// O type module exige essa gambiarra para ter o __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// O app reside na raiz do pacote instalado (um nível acima do bin)
const appDir = join(__dirname, "..");

console.log("🚀 Iniciando Vectora Chat...");

// Inicia o processo Next.js em modo de producao usando o npm local
const child = spawn("npm", ["start"], {
  cwd: appDir,
  stdio: "inherit",
  shell: true,
});

child.on("error", (err) => {
  console.error("❌ Falha ao iniciar o chat:", err);
  process.exit(1);
});

child.on("exit", (code) => {
  if (code !== 0) {
    console.error(`❌ O processo encerrou com código ${code}`);
  }
  process.exit(code || 0);
});
