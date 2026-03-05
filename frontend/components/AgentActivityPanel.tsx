"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { getApplicationLogs } from "@/lib/api";

type AgentLog = {
  created_at?: string;
  agent_name?: string;
  message?: string;
  action?: string;
  result?: string;
};

type Props = {
  applicationId: string;
};

function normalizeAgentName(agentName: string): string {
  return agentName.trim().toLowerCase().replaceAll("-", "_");
}

function displayAgentName(agentName: string): string {
  const normalized = normalizeAgentName(agentName);
  const knownNames: Record<string, string> = {
    planner_agent: "PlannerAgent",
    interview_agent: "InterviewAgent",
    document_agent: "DocumentAgent",
    automation_agent: "AutomationAgent",
    validation_agent: "ValidationAgent",
    notification_agent: "NotificationAgent",
  };
  if (knownNames[normalized]) {
    return knownNames[normalized];
  }

  return agentName
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function badgeClass(agentName: string): string {
  const normalized = normalizeAgentName(agentName);
  if (normalized === "planner_agent") return "bg-violet-100 text-violet-800 border-violet-200";
  if (normalized === "interview_agent") return "bg-sky-100 text-sky-800 border-sky-200";
  if (normalized === "document_agent") return "bg-emerald-100 text-emerald-800 border-emerald-200";
  if (normalized === "automation_agent") return "bg-orange-100 text-orange-800 border-orange-200";
  if (normalized === "validation_agent") return "bg-red-100 text-red-800 border-red-200";
  if (normalized === "notification_agent") return "bg-slate-200 text-slate-800 border-slate-300";
  return "bg-slate-100 text-slate-700 border-slate-200";
}

function byNewest(a: AgentLog, b: AgentLog): number {
  const left = a.created_at ? Date.parse(a.created_at) : 0;
  const right = b.created_at ? Date.parse(b.created_at) : 0;
  return right - left;
}

export default function AgentActivityPanel({ applicationId }: Props) {
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [error, setError] = useState("");
  const [hasFreshUpdate, setHasFreshUpdate] = useState(false);
  const latestSeenRef = useRef("");

  useEffect(() => {
    let active = true;
    let pulseTimer: ReturnType<typeof setTimeout> | null = null;

    const fetchLogs = async () => {
      try {
        const payload = await getApplicationLogs(applicationId);
        if (!active) return;

        const sorted = [...payload.logs].sort(byNewest) as AgentLog[];
        setLogs(sorted);
        setError("");

        const newestMarker = `${sorted[0]?.created_at || ""}:${sorted[0]?.message || ""}:${sorted.length}`;
        if (newestMarker && newestMarker !== latestSeenRef.current) {
          latestSeenRef.current = newestMarker;
          setHasFreshUpdate(true);
          if (pulseTimer) clearTimeout(pulseTimer);
          pulseTimer = setTimeout(() => setHasFreshUpdate(false), 1100);
        }
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load agent activity");
      }
    };

    void fetchLogs();
    const intervalId = setInterval(() => {
      void fetchLogs();
    }, 3000);

    return () => {
      active = false;
      clearInterval(intervalId);
      if (pulseTimer) clearTimeout(pulseTimer);
    };
  }, [applicationId]);

  const headerIndicatorClass = useMemo(() => {
    if (hasFreshUpdate) return "bg-emerald-500 animate-pulse";
    return "bg-slate-400";
  }, [hasFreshUpdate]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <span className={`h-2.5 w-2.5 rounded-full ${headerIndicatorClass}`} />
        <h2 className="text-base font-bold text-slate-900">AI Agents Working</h2>
      </div>

      {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
      {logs.length === 0 ? <p className="text-sm text-slate-500">No agent activity yet.</p> : null}

      <div className="space-y-3">
        {logs.map((log, index) => {
          const agentName = String(log.agent_name || "agent");
          return (
            <article key={`${log.created_at}-${log.agent_name}-${index}`} className="rounded-lg border border-slate-200 p-3">
              <div className="mb-1 flex items-center gap-2">
                <span className={`rounded border px-2 py-0.5 text-xs font-semibold ${badgeClass(agentName)}`}>
                  {displayAgentName(agentName)}
                </span>
              </div>
              <p className="text-sm text-slate-900">{String(log.message || "Agent activity recorded")}</p>
              {log.action ? (
                <p className="mt-1 text-xs text-slate-600">
                  Action: <span className="font-medium">{String(log.action)}</span>
                  {log.result ? <> • Result: <span className="font-medium">{String(log.result)}</span></> : null}
                </p>
              ) : null}
              <p className="mt-2 text-xs text-slate-500">{String(log.created_at || "unknown time")}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
