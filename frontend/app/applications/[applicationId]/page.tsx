"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import AIThinkingPanel from "@/components/AIThinkingPanel";
import AutomationTimeline from "@/components/AutomationTimeline";
import ApplicationStatusTimeline from "@/components/ApplicationStatusTimeline";
import DocumentUploader from "@/components/DocumentUploader";
import StreamingVoicePanel from "@/components/StreamingVoicePanel";
import { getApplication, getApplicationLogs, getApplicationTimeline, getPlannerState } from "@/lib/api";

export default function ApplicationDetailPage() {
  const params = useParams<{ applicationId: string }>();
  const applicationId = params.applicationId;

  const [application, setApplication] = useState<Record<string, unknown> | null>(null);
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([]);
  const [timeline, setTimeline] = useState<Array<Record<string, unknown>>>([]);
  const [plannerState, setPlannerState] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const [app, logPayload, timelinePayload, plannerPayload] = await Promise.all([
        getApplication(applicationId),
        getApplicationLogs(applicationId),
        getApplicationTimeline(applicationId),
        getPlannerState(applicationId),
      ]);
      setApplication(app as Record<string, unknown>);
      setLogs(logPayload.logs);
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

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Application {applicationId}</h1>
        <p className="mt-2 text-sm text-slate-600">Status: {String(application?.status || "loading")}</p>
        <pre className="mt-3 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-200">
          {JSON.stringify(application, null, 2)}
        </pre>
      </section>

      <AIThinkingPanel
        goal={String(plannerState?.goal || "")}
        reasoningSummary={String(plannerState?.reasoning_summary || "")}
        nextAction={String(plannerState?.next_action || "")}
        missingRequirements={Array.isArray(plannerState?.missing_requirements) ? (plannerState?.missing_requirements as string[]) : []}
        tasks={Array.isArray(plannerState?.tasks) ? (plannerState?.tasks as Array<{ step?: number; action?: string; status?: string }>) : []}
      />

      <StreamingVoicePanel applicationId={applicationId} onVoiceUpdate={() => void refresh()} />
      <DocumentUploader
        applicationId={applicationId}
        missingRequirements={Array.isArray(plannerState?.missing_requirements) ? (plannerState?.missing_requirements as string[]) : []}
        onUploaded={refresh}
      />
      <ApplicationStatusTimeline logs={logs as Array<{ created_at?: string; agent_name?: string; message?: string }>} />
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
