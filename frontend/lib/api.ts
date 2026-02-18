const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function callApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
      "x-user-sub": "demo-user",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body}`);
  }

  return response.json() as Promise<T>;
}

export async function createApplication(
  prompt: string,
  applicationType: string,
  options?: { demoMode?: boolean; demoScenario?: string | null },
) {
  return callApi<{ application_id: string; status: string; next_questions: string[] }>("/applications", {
    method: "POST",
    body: JSON.stringify({
      prompt,
      application_type: applicationType,
      demo_mode: Boolean(options?.demoMode),
      demo_scenario: options?.demoScenario || null,
    }),
  });
}

export async function getApplication(applicationId: string) {
  return callApi(`/applications/${applicationId}`);
}

export async function getApplicationLogs(applicationId: string) {
  return callApi<{ logs: Array<Record<string, unknown>> }>(`/applications/${applicationId}/logs`);
}

export async function getApplicationTimeline(applicationId: string) {
  return callApi<{ application_id: string; timeline: Array<Record<string, unknown>> }>(
    `/applications/${applicationId}/timeline`,
  );
}

export async function getPlannerState(applicationId: string) {
  return callApi<{
    application_id: string;
    goal: string;
    reasoning_summary: string;
    next_action: string;
    tasks: Array<Record<string, unknown>>;
    missing_requirements: string[];
    status: string;
    updated_at: string;
  }>(`/planner/state/${applicationId}`);
}

export async function requestDocumentUploadUrl(applicationId: string, fileName: string, contentType: string) {
  return callApi<{ document_id: string; upload_url: string; s3_key: string }>(
    `/applications/${applicationId}/documents/upload-url`,
    {
      method: "POST",
      body: JSON.stringify({ file_name: fileName, content_type: contentType }),
    },
  );
}

export async function processDocumentUpload(applicationId: string, documentId: string, s3Key: string) {
  return callApi<{ extracted_fields: Record<string, unknown>; status: string }>(
    `/applications/${applicationId}/documents/process`,
    {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, s3_key: s3Key }),
    },
  );
}
