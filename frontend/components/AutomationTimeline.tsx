type TimelineRecord = {
  step?: number;
  action?: string;
  status?: string;
  timestamp?: string;
  screenshot_url?: string;
  error?: string;
};

type Props = {
  timeline: TimelineRecord[];
};

export default function AutomationTimeline({ timeline }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">Automation Timeline</div>
      {timeline.length === 0 ? <p className="text-sm text-slate-500">No automation steps yet.</p> : null}
      <div className="space-y-4">
        {timeline.map((item, index) => (
          <article key={`${item.timestamp}-${index}`} className="rounded-lg border border-slate-200 p-3">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span>Step {item.step ?? index + 1}</span>
              <span className="rounded bg-slate-100 px-2 py-0.5">{item.status || "unknown"}</span>
              <span>{item.timestamp || "unknown time"}</span>
            </div>
            <div className="mt-1 text-sm font-medium text-slate-900">{item.action || "action"}</div>
            {item.error ? <p className="mt-1 text-sm text-red-600">{item.error}</p> : null}
            {item.screenshot_url ? (
              <a href={item.screenshot_url} target="_blank" rel="noreferrer" className="mt-2 block">
                <img
                  src={item.screenshot_url}
                  alt={`Automation step ${item.step || index + 1}`}
                  className="max-h-64 w-full rounded border border-slate-200 object-cover"
                />
              </a>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}
