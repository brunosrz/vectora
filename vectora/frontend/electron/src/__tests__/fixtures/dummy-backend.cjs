/**
 * Backend dummy pros testes reais de backend-lifecycle.ts — processo Node
 * puro (sem TS, sem depender de build), imita o essencial do binário real:
 * imprime VECTORA_IPC_PIPE=<algo> no stdout e sobe um HTTP server que
 * responde /health.
 *
 * Configurável via env vars (cada teste escolhe o comportamento):
 *   TEST_HEALTH_PORT     — porta onde o /health escuta (obrigatória)
 *   CRASH_IMMEDIATELY=1  — sai com código 1 antes de fazer qualquer coisa
 *   NEVER_HEALTHY=1      — nunca abre o servidor de /health (fica vivo)
 *   DELAY_HEALTH_MS=N    — espera N ms antes de abrir o /health
 *   SPLIT_PIPE_WRITE=1   — escreve "VECTORA_IPC_PIPE=...” fatiado em dois
 *                          process.stdout.write() com um tick entre eles
 */
const http = require("http");

if (process.env.CRASH_IMMEDIATELY === "1") {
  process.exit(1);
}

const pipeValue = "\\\\.\\pipe\\test-dummy-backend";

if (process.env.SPLIT_PIPE_WRITE === "1") {
  process.stdout.write(`VECTORA_IPC_PIPE=\\\\.\\pipe\\test-du`);
  setTimeout(() => {
    process.stdout.write(`mmy-backend\n`);
  }, 20);
} else {
  process.stdout.write(`VECTORA_IPC_PIPE=${pipeValue}\n`);
}

if (process.env.NEVER_HEALTHY === "1") {
  // Fica vivo sem nunca responder /health — usado pro teste de timeout.
} else {
  const startHealthServer = () => {
    const port = Number(process.env.TEST_HEALTH_PORT);
    const server = http.createServer((req, res) => {
      if (req.url === "/health") {
        res.writeHead(200);
        res.end("ok");
      } else {
        res.writeHead(404);
        res.end();
      }
    });
    server.listen(port, "127.0.0.1");
  };

  const delay = Number(process.env.DELAY_HEALTH_MS || "0");
  if (delay > 0) {
    setTimeout(startHealthServer, delay);
  } else {
    startHealthServer();
  }
}

process.on("SIGTERM", () => process.exit(0));
