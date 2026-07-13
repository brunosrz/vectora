// @vitest-environment jsdom
/**
 * useVoiceInput: no browser usa Web Speech API; no desktop (window.vectora
 * presente) usa MediaRecorder + transcrição via backend, porque a Web Speech
 * API sempre falha com erro de rede no Electron/Chromium.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { transcribeAudio } from "@/lib/api/vectora-client";
import { useVoiceInput } from "../use-voice-input";

vi.mock("@/lib/api/vectora-client", () => ({
  transcribeAudio: vi.fn(),
}));

const mockedTranscribeAudio = vi.mocked(transcribeAudio);

class FakeMediaRecorder {
  static isTypeSupported = vi.fn(() => true);
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  mimeType = "audio/webm";
  start = vi.fn();
  stop = vi.fn(() => {
    this.ondataavailable?.({
      data: new Blob(["chunk"], { type: "audio/webm" }),
    });
    this.onstop?.();
  });
  constructor(public stream: MediaStream) {}
}

class FakeSpeechRecognition extends EventTarget {
  continuous = false;
  interimResults = false;
  lang = "en-US";
  onresult: ((event: unknown) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;
  onend: (() => void) | null = null;
  onstart: (() => void) | null = null;
  start = vi.fn(() => this.onstart?.());
  stop = vi.fn(() => this.onend?.());
  abort = vi.fn();
}

function fakeStream(): MediaStream {
  const stop = vi.fn();
  return { getTracks: () => [{ stop }] } as unknown as MediaStream;
}

function setMediaDevices(value: unknown) {
  Object.defineProperty(navigator, "mediaDevices", {
    value,
    configurable: true,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  setMediaDevices(undefined);
  delete (window as { vectora?: unknown }).vectora;
  delete (window as { webkitSpeechRecognition?: unknown })
    .webkitSpeechRecognition;
});

describe("useVoiceInput — desktop (MediaRecorder + backend)", () => {
  beforeEach(() => {
    (window as { vectora?: unknown }).vectora = {};
    vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
    setMediaDevices({ getUserMedia: vi.fn().mockResolvedValue(fakeStream()) });
    mockedTranscribeAudio.mockReset();
  });

  it("isSupported é true quando getUserMedia + MediaRecorder existem", () => {
    const { result } = renderHook(() =>
      useVoiceInput({ onTranscript: vi.fn() }),
    );
    expect(result.current.isSupported).toBe(true);
  });

  it("startListening grava e stopListening transcreve via backend", async () => {
    mockedTranscribeAudio.mockResolvedValue({ text: "olá mundo" });
    const onTranscript = vi.fn();
    const { result } = renderHook(() => useVoiceInput({ onTranscript }));

    await act(async () => {
      result.current.startListening();
      await Promise.resolve();
    });
    expect(result.current.isListening).toBe(true);

    await act(async () => {
      result.current.stopListening();
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(onTranscript).toHaveBeenCalledWith("olá mundo");
    });
    expect(result.current.isListening).toBe(false);
  });

  it("erro do backend na transcrição vira mensagem de erro, sem chamar onTranscript", async () => {
    mockedTranscribeAudio.mockRejectedValue(new Error("502"));
    const onTranscript = vi.fn();
    const { result } = renderHook(() => useVoiceInput({ onTranscript }));

    await act(async () => {
      result.current.startListening();
      await Promise.resolve();
    });
    await act(async () => {
      result.current.stopListening();
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current.error).not.toBeNull();
    });
    expect(onTranscript).not.toHaveBeenCalled();
  });

  it("negar acesso ao microfone seta erro e não entra em isListening", async () => {
    setMediaDevices({
      getUserMedia: vi.fn().mockRejectedValue(new Error("denied")),
    });
    const { result } = renderHook(() =>
      useVoiceInput({ onTranscript: vi.fn() }),
    );

    await act(async () => {
      result.current.startListening();
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current.error).not.toBeNull();
    });
    expect(result.current.isListening).toBe(false);
  });
});

describe("useVoiceInput — browser (Web Speech API)", () => {
  let recognitionInstance: FakeSpeechRecognition;

  beforeEach(() => {
    recognitionInstance = new FakeSpeechRecognition();
    vi.stubGlobal(
      "webkitSpeechRecognition",
      vi.fn(() => recognitionInstance),
    );
  });

  it("isSupported é true quando webkitSpeechRecognition existe", () => {
    const { result } = renderHook(() =>
      useVoiceInput({ onTranscript: vi.fn() }),
    );
    expect(result.current.isSupported).toBe(true);
  });

  it("startListening chama recognition.start()", () => {
    const { result } = renderHook(() =>
      useVoiceInput({ onTranscript: vi.fn() }),
    );
    act(() => {
      result.current.startListening();
    });
    expect(recognitionInstance.start).toHaveBeenCalledTimes(1);
    expect(result.current.isListening).toBe(true);
  });

  it("resultado final chama onTranscript com o texto transcrito", () => {
    const onTranscript = vi.fn();
    renderHook(() => useVoiceInput({ onTranscript }));

    act(() => {
      recognitionInstance.onresult?.({
        resultIndex: 0,
        results: [Object.assign([{ transcript: "oi" }], { isFinal: true })],
      });
    });

    expect(onTranscript).toHaveBeenCalledWith("oi");
  });
});
