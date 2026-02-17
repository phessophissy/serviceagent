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

export async function createApplication(prompt: string, applicationType: string) {
  return callApi<{ application_id: string; status: string; next_questions: string[] }>("/applications", {
    method: "POST",
    body: JSON.stringify({ prompt, application_type: applicationType }),
  });
}

export async function getApplication(applicationId: string) {
  return callApi(`/applications/${applicationId}`);
}

export async function getApplicationLogs(applicationId: string) {
  return callApi<{ logs: Array<Record<string, unknown>> }>(`/applications/${applicationId}/logs`);
}
