"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import VoiceInterviewPanel from "@/components/VoiceInterviewPanel";
import { createApplication } from "@/lib/api";

const APPLICATION_TYPES = [
  { value: "scholarship_application", label: "Scholarship" },
  { value: "business_registration", label: "Business Registration" },
  { value: "visa_application", label: "Visa" },
  { value: "job_application", label: "Job" },
];

export default function HomePage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("I want to apply for a scholarship.");
  const [applicationType, setApplicationType] = useState("scholarship_application");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const onCreate = async () => {
    setBusy(true);
    setError("");
    try {
      const created = await createApplication(prompt, applicationType);
      router.push(`/applications/${created.application_id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create application";
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-gradient-to-r from-slateInk to-slate-700 p-8 text-white">
        <h1 className="text-3xl font-bold">Service Agent (SA)</h1>
        <p className="mt-2 max-w-2xl text-slate-200">
          Multi-agent administrative worker for business registration, scholarship intake, visa forms, and other real-world processes.
        </p>
      </section>

      <section className="grid gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:grid-cols-2">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-slate-700">Application Type</span>
          <select
            value={applicationType}
            onChange={(e) => setApplicationType(e.target.value)}
            className="w-full rounded-lg border border-slate-300 p-2"
          >
            {APPLICATION_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2">
          <span className="text-sm font-semibold text-slate-700">Initial Request</span>
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full rounded-lg border border-slate-300 p-2"
          />
        </label>

        <div className="md:col-span-2">
          <button
            onClick={onCreate}
            disabled={busy}
            className="rounded-lg bg-ember px-4 py-2 text-white hover:bg-orange-600 disabled:opacity-60"
          >
            {busy ? "Creating..." : "Start Application"}
          </button>
          {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
        </div>
      </section>

      <VoiceInterviewPanel onTranscript={setPrompt} />
    </div>
  );
}
