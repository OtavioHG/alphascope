const API_BASE_URL = process.env.NEXT_PUBLIC_ALPHASCOPE_API_BASE_URL ?? "http://127.0.0.1:8010";

export type ApiHealthPayload = {
  status?: string;
  healthy?: boolean;
  service?: string;
  health?: {
    status?: string;
    healthy?: boolean;
  };
};

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function fetchPlatformHealth(): Promise<ApiHealthPayload | null> {
  return fetchJson<ApiHealthPayload>("/healthz");
}

export async function fetchDashboardPayload(): Promise<Record<string, unknown> | null> {
  return fetchJson<Record<string, unknown>>("/dashboard");
}

export async function fetchRankingPayload(): Promise<Record<string, unknown> | null> {
  return fetchJson<Record<string, unknown>>("/ranking");
}

export async function fetchRiskPayload(): Promise<Record<string, unknown> | null> {
  return fetchJson<Record<string, unknown>>("/risk");
}

export async function fetchAuditPayload(): Promise<Record<string, unknown> | null> {
  return fetchJson<Record<string, unknown>>("/audit");
}

export { API_BASE_URL };
