#!/usr/bin/env node

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, "..", ".."); // Ajustado para a raiz do monorepo/projeto

console.log("🚀 Iniciando Vectora Agent (LangGraph)...");

// Inicia o servidor LangGraph em background
const agentProcess = spawn("langgraph", ["dev"], {
  cwd: projectRoot,
  stdio: "ignore", // Oculta logs do servidor para não poluir o terminal
  shell: true,
});

// Aguarda 3 segundos para garantir que o servidor suba
setTimeout(() => {
  console.log("🚀 Iniciando Vectora Chat...");
  
  // Inicia o Next.js
  const chatProcess = spawn("npm", ["start"], {
    cwd: join(__dirname, ".."),
    stdio: "inherit",
    shell: true,
  });

  chatProcess.on("exit", (code) => {
    agentProcess.kill(); // Mata o agente ao fechar o chat
    process.exit(code || 0);
  });
}, 3000);

agentProcess.on("error", (err) => {
  console.error("❌ Falha ao iniciar o agente:", err);
  process.exit(1);
});
