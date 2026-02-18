type PlannerTask = {
  step?: number;
  action?: string;
  status?: string;
};

type Props = {
  goal: string;
  reasoningSummary: string;
  nextAction: string;
  missingRequirements: string[];
  tasks: PlannerTask[];
};

function taskBadgeColor(status: string): string {
  if (status === "completed") return "bg-emerald-100 text-emerald-800";
  if (status === "in_progress") return "bg-amber-100 text-amber-800";
  if (status === "failed") return "bg-red-100 text-red-800";
  return "bg-slate-100 text-slate-700";
}

export default function AIThinkingPanel({ goal, reasoningSummary, nextAction, missingRequirements, tasks }: Props) {
  const completedTasks = tasks.filter((task) => task.status === "completed").length;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-bold text-slate-900">AI Thinking Panel</h2>
      <p className="mt-2 text-sm text-slate-700">
        <span className="font-semibold">Current goal:</span> {goal || "No goal yet"}
      </p>
      <p className="mt-1 text-sm text-slate-700">
        <span className="font-semibold">Reasoning summary:</span> {reasoningSummary || "Planner has not produced a summary yet."}
      </p>
      <p className="mt-1 text-sm text-slate-700">
        <span className="font-semibold">Next action:</span> {nextAction || "Waiting"}
      </p>

      <div className="mt-3 rounded border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
        <span className="font-semibold">Completed tasks:</span> {completedTasks}/{tasks.length || 0}
      </div>

      <div className="mt-3 rounded border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
        <span className="font-semibold">Missing requirements:</span>{" "}
        {missingRequirements.length > 0 ? missingRequirements.join(", ") : "none"}
      </div>

      <ul className="mt-4 space-y-2">
        {tasks.map((task, idx) => {
          const status = task.status || "pending";
          return (
            <li key={`${task.step}-${task.action}-${idx}`} className="flex items-center justify-between rounded border border-slate-200 p-2">
              <span className="text-sm text-slate-800">
                {(task.step ?? idx + 1).toString()}. {task.action || "task"}
              </span>
              <span className={`rounded px-2 py-1 text-xs font-semibold ${taskBadgeColor(status)}`}>{status}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
