"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import ApplicationStatusTimeline from "@/components/ApplicationStatusTimeline";
import DocumentUploader from "@/components/DocumentUploader";
import { getApplication, getApplicationLogs } from "@/lib/api";

export default function ApplicationDetailPage() {
  const params = useParams<{ applicationId: string }>();
  const applicationId = params.applicationId;

  const [application, setApplication] = useState<Record<string, unknown> | null>(null);
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const [app, logPayload] = await Promise.all([
          getApplication(applicationId),
          getApplicationLogs(applicationId),
        ]);
        setApplication(app as Record<string, unknown>);
        setLogs(logPayload.logs);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load application");
      }
    };

    void load();
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

      <DocumentUploader applicationId={applicationId} />
      <ApplicationStatusTimeline logs={logs as Array<{ created_at?: string; agent_name?: string; message?: string }>} />
    </div>
  );
}
