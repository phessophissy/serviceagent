"use client";

import { type ChangeEvent, useState } from "react";

import { processDocumentUpload, requestDocumentUploadUrl } from "@/lib/api";

type Props = {
  applicationId: string;
  missingRequirements: string[];
  onUploaded?: () => Promise<void> | void;
};

export default function DocumentUploader({ applicationId, missingRequirements, onUploaded }: Props) {
  const [status, setStatus] = useState("No file uploaded");
  const [busy, setBusy] = useState(false);

  const onUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setBusy(true);
    setStatus(`Uploading ${file.name}...`);
    try {
      const uploadTarget = await requestDocumentUploadUrl(applicationId, file.name, file.type || "application/octet-stream");
      const putResponse = await fetch(uploadTarget.upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });
      if (!putResponse.ok) {
        throw new Error(`Upload failed (${putResponse.status})`);
      }

      await processDocumentUpload(applicationId, uploadTarget.document_id, uploadTarget.s3_key);
      setStatus(`Uploaded and processed: ${file.name}`);
      if (onUploaded) {
        await onUploaded();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed";
      setStatus(`Error: ${message}`);
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Documents</div>
      <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
        {missingRequirements.length > 0 ? (
          missingRequirements.map((item) => <li key={item}>Required: {item.replaceAll("_", " ")}</li>)
        ) : (
          <li>No missing requirements currently detected.</li>
        )}
      </ul>
      <input type="file" onChange={onUpload} disabled={busy} className="block w-full text-sm text-slate-700" />
      <p className="mt-3 text-sm text-slate-600">{status}</p>
    </div>
  );
}
