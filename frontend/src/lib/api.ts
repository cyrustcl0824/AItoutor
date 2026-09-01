export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "include",
    headers: { ...(init.body ? { "Content-Type": "application/json" } : {}), ...init.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new ApiError(response.status, payload.message || payload.detail || "请求失败");
  }
  return response.json();
}

export type Student = { id: string; display_name: string; grade: number };
export type Course = { id: string; name: string; grade: number; semester: string };
export type Unit = { id: string; title: string; position: number };
export type Lesson = { id: string; title: string; position: number; progress?: {stars: number; best_accuracy: number} };
