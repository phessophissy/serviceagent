"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import AgentActivityPanel from "@/components/AgentActivityPanel";
import AIThinkingPanel from "@/components/AIThinkingPanel";
import AutomationTimeline from "@/components/AutomationTimeline";
import ApplicationProgress from "@/components/ApplicationProgress";
import DocumentUploader from "@/components/DocumentUploader";
import StreamingVoicePanel from "@/components/StreamingVoicePanel";
import { getApplication, getApplicationTimeline, getPlannerState } from "@/lib/api";

export default function ApplicationDetailPage() {
  const params = useParams<{ applicationId: string }>();
  const applicationId = params.applicationId;

  const [application, setApplication] = useState<Record<string, unknown> | null>(null);
  const [timeline, setTimeline] = useState<Array<Record<string, unknown>>>([]);
  const [plannerState, setPlannerState] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const [app, timelinePayload, plannerPayload] = await Promise.all([
        getApplication(applicationId),
        getApplicationTimeline(applicationId),
        getPlannerState(applicationId),
      ]);
      setApplication(app as Record<string, unknown>);
      setTimeline(timelinePayload.timeline);
      setPlannerState(plannerPayload as Record<string, unknown>);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load application");
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applicationId]);

  if (error) {
    return <p className="text-red-600">{error}</p>;
  }

  const statusDetail: Record<string, string> = {
    collecting_information: "Collecting user information",
    processing_documents: "Processing documents",
    automating_submission: "Submitting application",
  };
  const statusText = statusDetail[String(application?.status || "")] || "Agents orchestrating workflow";

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h1 className="text-2xl font-bold text-slate-900">Application {applicationId}</h1>
          <div className="mb-4 mt-3 flex items-center gap-3 rounded-md bg-slate-900 px-4 py-2 text-white">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-green-500" />
            </span>
            <span className="font-medium">AI System Active</span>
            <span className="text-sm text-gray-300">{statusText}</span>
          </div>
          <p className="mt-2 text-sm text-slate-600">Status: {String(application?.status || "loading")}</p>
          {String(application?.status || "").toLowerCase() === "needs_user_confirmation" ? (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              The AI encountered a problem and needs your input before proceeding.
            </div>
          ) : null}
          <pre className="mt-3 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-200">
            {JSON.stringify(application, null, 2)}
          </pre>
        </section>

        <div className="space-y-6">
          <AIThinkingPanel
            goal={String(plannerState?.goal || "")}
            reasoningSummary={String(plannerState?.reasoning_summary || "")}
            currentStep={String(plannerState?.current_step || "")}
            nextAction={String(plannerState?.next_action || "")}
            missingRequirements={
              Array.isArray(plannerState?.missing_requirements) ? (plannerState?.missing_requirements as string[]) : []
            }
            tasks={Array.isArray(plannerState?.tasks) ? (plannerState?.tasks as Array<{ step?: number; action?: string; status?: string }>) : []}
          />
          <ApplicationProgress status={String(application?.status || "created")} />
        </div>
      </div>

      <AgentActivityPanel applicationId={applicationId} />
      <StreamingVoicePanel applicationId={applicationId} onVoiceUpdate={() => void refresh()} />
      <DocumentUploader
        applicationId={applicationId}
        missingRequirements={Array.isArray(plannerState?.missing_requirements) ? (plannerState?.missing_requirements as string[]) : []}
        onUploaded={refresh}
      />
      <AutomationTimeline
        timeline={
          timeline as Array<{
            step?: number;
            action?: string;
            status?: string;
            timestamp?: string;
            screenshot_url?: string;
            error?: string;
          }>
        }
      />
    </div>
  );
}
