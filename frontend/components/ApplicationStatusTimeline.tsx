type LogRecord = {
  created_at?: string;
  agent_name?: string;
  message?: string;
};

type Props = {
  logs: LogRecord[];
};

export default function ApplicationStatusTimeline({ logs }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">Agent Activity</div>
      <ul className="space-y-3">
        {logs.map((log, idx) => (
          <li key={`${log.created_at}-${idx}`} className="border-l-2 border-signal pl-3">
            <div className="text-xs text-slate-500">{log.created_at || "unknown time"}</div>
            <div className="text-sm font-medium text-slate-900">{log.agent_name || "agent"}</div>
            <div className="text-sm text-slate-700">{log.message || "event"}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
