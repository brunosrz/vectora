/**
 * Voice Input Hook
 *
 * Ditado de voz pro composer. No browser puro usa a Web Speech API
 * (client-side, sem chamada ao backend). No desktop (Electron/Chromium)
 * a Web Speech API sempre falha com erro de rede — o Chromium vendored
 * não embarca a chave de voz proprietária do Google que o Chrome tem —
 * então usa MediaRecorder + transcrição via backend (Whisper) como fallback.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { transcribeAudio } from "@/lib/api/vectora-client";

// ============================================================================
// Types
// ============================================================================

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message?: string;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

export interface UseVoiceInputReturn {
  isListening: boolean;
  isSupported: boolean;
  error: string | null;
  interimTranscript: string;
  startListening: () => void;
  stopListening: () => void;
  toggleListening: () => void;
}

function isDesktopEnvironment(): boolean {
  return typeof window !== "undefined" && Boolean(window.vectora);
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const result = reader.result as string;
      resolve(result.split(",")[1] ?? "");
    });
    reader.addEventListener("error", () => reject(reader.error));
    reader.readAsDataURL(blob);
  });
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook de ditado de voz. Mesma interface (`UseVoiceInputReturn`) independente
 * do backend usado — quem consome (`VoiceInputButton`, `chat-interface.tsx`)
 * não precisa saber se é Web Speech API ou gravação + transcrição via backend.
 *
 * @param onTranscript - Called with finalized transcript text
 * @returns Voice input state and controls
 */
export function useVoiceInput({
  onTranscript,
  lang = "en-US",
}: {
  onTranscript: (text: string) => void;
  /** Idioma do reconhecimento em BCP-47 (ex: "pt-BR"). */
  lang?: string;
}): UseVoiceInputReturn {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");

  const isDesktop = isDesktopEnvironment();

  const onTranscriptRef = useRef(onTranscript);
  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  const langRef = useRef(lang);
  useEffect(() => {
    langRef.current = lang;
  }, [lang]);

  // ── Backend (MediaRecorder + Whisper) — desktop ──────────────────────────
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startDesktopRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      mediaStreamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "";
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e: BlobEvent) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
        setIsListening(false);

        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        chunksRef.current = [];
        if (blob.size === 0) return;

        void (async () => {
          try {
            const base64 = await blobToBase64(blob);
            const { text } = await transcribeAudio(
              base64,
              blob.type || "audio/webm",
            );
            if (text) onTranscriptRef.current(text);
          } catch {
            setError(
              "Falha ao transcrever o áudio. Verifique sua conexão e tente novamente.",
            );
            setTimeout(() => setError(null), 5000);
          }
        })();
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setError(null);
      setIsListening(true);
    } catch {
      setError(
        "Acesso ao microfone negado. Permita o acesso ao microfone nas configurações do sistema.",
      );
      setTimeout(() => setError(null), 5000);
    }
  }, []);

  const stopDesktopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
  }, []);

  useEffect(() => {
    if (!isDesktop) return;
    setIsSupported(
      typeof navigator !== "undefined" &&
        Boolean(navigator.mediaDevices?.getUserMedia) &&
        typeof MediaRecorder !== "undefined",
    );
    return () => {
      mediaRecorderRef.current?.stop();
      mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Web Speech API — browser ─────────────────────────────────────────────
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const isStartingRef = useRef(false);

  useEffect(() => {
    if (isDesktop) return;

    const SpeechRecognitionAPI =
      typeof window !== "undefined"
        ? window.SpeechRecognition || window.webkitSpeechRecognition
        : null;

    setIsSupported(!!SpeechRecognitionAPI);

    if (SpeechRecognitionAPI && !recognitionRef.current) {
      const recognition = new SpeechRecognitionAPI();
      // Use non-continuous mode for better compatibility
      // User can click again to continue recording
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = langRef.current;
      // @ts-expect-error - maxAlternatives exists but not in types
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        isStartingRef.current = false;
        setIsListening(true);
        setError(null);
        setInterimTranscript("");
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let interim = "";
        let final = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const transcript = result[0].transcript;

          if (result.isFinal) {
            final += transcript;
          } else {
            interim += transcript;
          }
        }

        setInterimTranscript(interim);

        if (final) {
          onTranscriptRef.current(final);
          setInterimTranscript("");
        }
      };

      recognition.addEventListener("error", (event: Event) => {
        const errEvent = event as SpeechRecognitionErrorEvent;
        isStartingRef.current = false;

        // "aborted" is expected when user stops listening or component unmounts
        if (errEvent.error === "aborted") {
          setIsListening(false);
          return;
        }

        console.error("Speech recognition error:", errEvent.error);

        let errorMessage: string;
        switch (errEvent.error) {
          case "no-speech":
            errorMessage = "No speech detected. Please try again.";
            break;
          case "audio-capture":
            errorMessage = "No microphone found. Please check your microphone.";
            break;
          case "not-allowed":
            errorMessage =
              "Microphone access denied. Please allow microphone access.";
            break;
          case "network":
            errorMessage =
              "Speech recognition unavailable. Try Chrome or Edge, or check browser privacy settings.";
            break;
          default:
            errorMessage = `Error: ${errEvent.error}`;
        }

        setError(errorMessage);
        setIsListening(false);

        // Auto-dismiss error after 5 seconds
        setTimeout(() => setError(null), 5000);
      });

      recognition.onend = () => {
        isStartingRef.current = false;
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    // Cleanup on unmount
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount - callbacks are handled via refs

  // ── API pública — despacha pro backend certo ─────────────────────────────

  const startListening = useCallback(() => {
    if (isDesktop) {
      if (!isListening && !isStartingRef.current) {
        isStartingRef.current = true;
        void startDesktopRecording().finally(() => {
          isStartingRef.current = false;
        });
      }
      return;
    }

    // Prevent double-start with ref (more reliable than state for rapid clicks)
    if (recognitionRef.current && !isListening && !isStartingRef.current) {
      isStartingRef.current = true;
      setError(null);
      // Reaplica o idioma atual — o usuário pode tê-lo trocado desde o mount.
      recognitionRef.current.lang = langRef.current;
      try {
        recognitionRef.current.start();
      } catch {
        // Recognition might already be running - silently ignore
        isStartingRef.current = false;
      }
    }
  }, [isDesktop, isListening, startDesktopRecording]);

  const stopListening = useCallback(() => {
    if (isDesktop) {
      stopDesktopRecording();
      return;
    }

    if (recognitionRef.current) {
      isStartingRef.current = false;
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore errors when stopping
      }
    }
  }, [isDesktop, stopDesktopRecording]);

  const toggleListening = useCallback(() => {
    if (isListening || isStartingRef.current) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  return {
    isListening,
    isSupported,
    error,
    interimTranscript,
    startListening,
    stopListening,
    toggleListening,
  };
}
