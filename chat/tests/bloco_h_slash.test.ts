/**
 * TDD — Bloco H: parser de slash commands (lib/constants/slash-commands.ts)
 */

import { describe, it, expect } from "vitest";
import {
  isSlashQuery,
  parseSlashCommand,
  filterCommands,
  isKnownCommand,
} from "../lib/constants/slash-commands";

describe("isSlashQuery", () => {
  it("true para '/' e '/mod' (ainda escolhendo comando)", () => {
    expect(isSlashQuery("/")).toBe(true);
    expect(isSlashQuery("/mod")).toBe(true);
  });

  it("false quando já há espaço (comando + arg)", () => {
    expect(isSlashQuery("/model gpt")).toBe(false);
  });

  it("false para texto normal", () => {
    expect(isSlashQuery("ola")).toBe(false);
    expect(isSlashQuery("")).toBe(false);
  });
});

describe("parseSlashCommand", () => {
  it("retorna null para texto sem barra", () => {
    expect(parseSlashCommand("ola mundo")).toBeNull();
  });

  it("extrai nome sem argumento", () => {
    expect(parseSlashCommand("/help")).toEqual({ name: "help", arg: "" });
  });

  it("extrai nome e argumento", () => {
    expect(parseSlashCommand("/model gemini-2.5-flash")).toEqual({
      name: "model",
      arg: "gemini-2.5-flash",
    });
  });

  it("normaliza o nome para minúsculas e apara espaços", () => {
    expect(parseSlashCommand("  /HELP  ")).toEqual({ name: "help", arg: "" });
  });
});

describe("filterCommands", () => {
  it("lista todos quando só há a barra", () => {
    expect(filterCommands("/").length).toBeGreaterThanOrEqual(3);
  });

  it("filtra por prefixo", () => {
    const r = filterCommands("/mo");
    expect(r).toHaveLength(1);
    expect(r[0].name).toBe("model");
  });

  it("vazio quando não começa com barra", () => {
    expect(filterCommands("mo")).toEqual([]);
  });
});

describe("isKnownCommand", () => {
  it("reconhece comandos registrados", () => {
    expect(isKnownCommand("help")).toBe(true);
    expect(isKnownCommand("model")).toBe(true);
  });
  it("rejeita desconhecidos", () => {
    expect(isKnownCommand("deploy")).toBe(false);
  });
});
