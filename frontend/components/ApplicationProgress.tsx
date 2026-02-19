type Props = {
  status: string;
};

const STEPS = [
  "created",
  "collecting_information",
  "waiting_documents",
  "processing_documents",
  "automating_submission",
  "submitted",
  "completed",
];

function labelFor(step: string): string {
  return step.replaceAll("_", " ");
}

export default function ApplicationProgress({ status }: Props) {
  const normalizedStatus = status === "needs_user_confirmation" ? "collecting_information" : status;
  const currentIndex = Math.max(0, STEPS.indexOf(normalizedStatus));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Application Progress</div>
      <div className="mb-4 h-2 w-full rounded-full bg-slate-200">
        <div
          className="h-2 rounded-full bg-emerald-500 transition-all"
          style={{ width: `${((currentIndex + 1) / STEPS.length) * 100}%` }}
        />
      </div>
      <ol className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        {STEPS.map((step, index) => (
          <li key={step} className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                index <= currentIndex ? "bg-emerald-500" : "bg-slate-300"
              }`}
            />
            <span className={index <= currentIndex ? "text-slate-900" : "text-slate-500"}>{labelFor(step)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
