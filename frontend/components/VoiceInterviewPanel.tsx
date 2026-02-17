"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  onTranscript: (text: string) => void;
};

export default function VoiceInterviewPanel({ onTranscript }: Props) {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    const SpeechRecognitionClass =
      (window as unknown as { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition;

    if (!SpeechRecognitionClass) return;

    const recognition = new SpeechRecognitionClass();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const spoken = event.results[0][0].transcript;
      setTranscript(spoken);
      onTranscript(spoken);
    };

    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
  }, [onTranscript]);

  const toggleVoice = () => {
    const recognition = recognitionRef.current;
    if (!recognition) return;

    if (listening) {
      recognition.stop();
      return;
    }

    setListening(true);
    recognition.start();
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Voice Intake</div>
      <button
        onClick={toggleVoice}
        className="rounded-lg bg-signal px-4 py-2 text-sm font-semibold text-white hover:bg-sky-600"
      >
        {listening ? "Stop Listening" : "Start Voice Interview"}
      </button>
      <p className="mt-3 text-sm text-slate-600">{transcript || "No transcript yet."}</p>
    </div>
  );
}
