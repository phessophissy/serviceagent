"use client";

import { type ChangeEvent, useState } from "react";

type Props = {
  applicationId: string;
};

export default function DocumentUploader({ applicationId }: Props) {
  const [status, setStatus] = useState("No file uploaded");

  const onUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setStatus(`Queued: ${file.name} for ${applicationId}`);
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Documents</div>
      <input type="file" onChange={onUpload} className="block w-full text-sm text-slate-700" />
      <p className="mt-3 text-sm text-slate-600">{status}</p>
    </div>
  );
}
