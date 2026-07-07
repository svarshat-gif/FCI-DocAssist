import type {
  ChatMessage,
  ChatResponse,
  Citation,
  Circular,
  Conversation,
  UploadSession,
  User,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type ApiOptions = RequestInit & {
  token?: string | null;
};

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed with ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (payload: { email: string; password: string; full_name?: string }) =>
    request<{ access_token: string; user: User }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  me: (token: string) => request<User>("/auth/me", { token }),
  chat: (
    payload: {
      message: string;
      conversation_id?: string;
      language: string;
      source_mode: "official" | "upload";
      upload_session_id?: string;
    },
    token?: string | null,
  ) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }),
  conversations: (token?: string | null) =>
    request<Conversation[]>("/chat/conversations", { token }),
  messages: (conversationId: string, token?: string | null) =>
    request<ChatMessage[]>(`/chat/conversations/${conversationId}/messages`, { token }),
  clearHistory: (token?: string | null) =>
    request<{ deleted: number }>("/chat/history", { method: "DELETE", token }),
  recentCirculars: () => request<Circular[]>("/circulars/recent"),
  searchCirculars: (params: URLSearchParams) =>
    request<{ items: Circular[]; total: number }>(`/circulars?${params.toString()}`),
  summarize: (
    payload: {
      circular_id?: string;
      circular_number?: string;
      style: "short" | "detailed" | "bullets";
      language: string;
    },
    token?: string | null,
  ) =>
    request<{ summary: string; citations: Citation[] }>(
      "/circulars/summarize",
      {
        method: "POST",
        token,
        body: JSON.stringify(payload),
      },
    ),
  uploadPdf: (file: File, token?: string | null) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<UploadSession>("/uploads/pdf", {
      method: "POST",
      token,
      body: formData,
    });
  },
  exportUrl: (conversationId: string, format: "pdf" | "txt") =>
    `${API_BASE}/chat/conversations/${conversationId}/export?format=${format}`,
  downloadExport: async (
    conversationId: string,
    format: "pdf" | "txt",
    token?: string | null,
  ) => {
    const headers = new Headers();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    const response = await fetch(api.exportUrl(conversationId, format), { headers });
    if (!response.ok) {
      throw new Error("Export failed");
    }
    return response.blob();
  },
};
