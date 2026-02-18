"use client";

import { useCallback, useMemo, useRef, useState } from "react";

type VoiceUpdate = {
  user_transcript?: string;
  assistant_text?: string;
  status?: string;
  next_questions?: string[];
  missing_requirements?: string[];
  goal?: string;
  next_action?: string;
  reasoning_summary?: string;
};

type Props = {
  applicationId: string;
  onVoiceUpdate?: (payload: VoiceUpdate) => void;
};

function toWebSocketBase(httpBase: string): string {
  if (httpBase.startsWith("https://")) return httpBase.replace("https://", "wss://");
  if (httpBase.startsWith("http://")) return httpBase.replace("http://", "ws://");
  return httpBase;
}

async function blobToBase64(blob: Blob): Promise<string> {
  const arrayBuffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function playAssistantAudio(audioB64: string, mimeType: string, fallbackText: string): void {
  if (audioB64) {
    const binaryString = atob(audioB64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i += 1) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: mimeType || "audio/wav" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    void audio.play().finally(() => URL.revokeObjectURL(url));
    return;
  }

  if (fallbackText && "speechSynthesis" in window) {
    const utterance = new SpeechSynthesisUtterance(fallbackText);
    window.speechSynthesis.speak(utterance);
  }
}

export default function StreamingVoicePanel({ applicationId, onVoiceUpdate }: Props) {
  const [connected, setConnected] = useState(false);
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState("Voice session idle");
  const [messages, setMessages] = useState<string[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const wsUrl = useMemo(() => {
    const base = toWebSocketBase(process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000");
    return `${base}/ws/interview/${applicationId}?x_user_sub=demo-user`;
  }, [applicationId]);

  const closeSession = useCallback(() => {
    if (mediaRef.current && mediaRef.current.state !== "inactive") {
      mediaRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "stop" }));
      wsRef.current.close();
    }
    wsRef.current = null;
    mediaRef.current = null;
    setRecording(false);
    setConnected(false);
    setStatus("Voice session stopped");
  }, []);

  const startSession = useCallback(async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = mediaStream;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setStatus("Connected. Streaming voice...");
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data));
          if (payload.type === "assistant_response") {
            const userText = payload.user_transcript ? `You: ${payload.user_transcript}` : "";
            const assistantText = payload.assistant_text ? `SA: ${payload.assistant_text}` : "";
            setMessages((prev) => [...prev, userText, assistantText].filter(Boolean));

            playAssistantAudio(
              String(payload.assistant_audio_b64 || ""),
              String(payload.assistant_audio_mime_type || "audio/wav"),
              String(payload.assistant_text || ""),
            );

            if (onVoiceUpdate) {
              onVoiceUpdate(payload as VoiceUpdate);
            }
          }

          if (payload.type === "error") {
            setStatus(`Error: ${payload.message || "Unknown websocket error"}`);
          }
        } catch {
          setStatus("Received non-JSON websocket message");
        }
      };

      ws.onerror = () => {
        setStatus("WebSocket connection error");
      };

      ws.onclose = () => {
        setConnected(false);
      };

      const recorder = new MediaRecorder(mediaStream);
      mediaRef.current = recorder;

      recorder.ondataavailable = async (evt) => {
        if (!evt.data || evt.data.size === 0) {
          return;
        }
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          return;
        }

        const audioB64 = await blobToBase64(evt.data);
        wsRef.current.send(
          JSON.stringify({
            type: "audio_chunk",
            audio_b64: audioB64,
            mime_type: recorder.mimeType || "audio/webm",
          }),
        );
      };

      recorder.start(1200);
      ws.addEventListener("open", () => {
        ws.send(JSON.stringify({ type: "start", mime_type: recorder.mimeType || "audio/webm" }));
      });

      setRecording(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to start voice streaming";
      setStatus(`Error: ${message}`);
      closeSession();
    }
  }, [closeSession, onVoiceUpdate, wsUrl]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Live Voice Interview</div>
      <div className="mb-3 flex gap-2">
        <button
          onClick={() => void startSession()}
          disabled={recording}
          className="rounded-lg bg-signal px-4 py-2 text-sm font-semibold text-white hover:bg-sky-600 disabled:opacity-60"
        >
          Start Live Voice
        </button>
        <button
          onClick={closeSession}
          disabled={!recording && !connected}
          className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
        >
          Stop
        </button>
      </div>
      <p className="text-sm text-slate-600">{status}</p>
      <div className="mt-3 max-h-48 space-y-1 overflow-auto rounded border border-slate-200 p-2 text-sm text-slate-700">
        {messages.length === 0 ? <p>No voice exchanges yet.</p> : null}
        {messages.map((line, index) => (
          <p key={`${line}-${index}`}>{line}</p>
        ))}
      </div>
    </div>
  );
}
