import type {
  ChatMessage,
  ChatResponse,
  Citation,
  Circular,
  Conversation,
  UploadSession,
  User,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1";

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
    const message = typeof detail?.detail === "string" ? detail.detail :
      Array.isArray(detail?.detail) ? detail.detail.map((item: { msg: string }) => item.msg).join("; ") :
      `Request failed with ${response.status}`;
    throw new Error(message);
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
  chatStream: async (
    payload: { message: string; conversation_id?: string; language: string; source_mode: "official" | "upload"; upload_session_id?: string },
    onUpdate: (text: string, citations: Citation[]) => void,
    token?: string | null,
  ): Promise<ChatResponse> => {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new Error(typeof error?.detail === "string" ? error.detail : "Unable to answer right now.");
    }
    if (!response.body) throw new Error("The response stream is unavailable.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    let text = "";
    let citations: Citation[] = [];
    let result: ChatResponse | undefined;
    try {
      while (true) {
        const { value, done } = await reader.read();
        pending += decoder.decode(value, { stream: !done });
        const lines = pending.split("\n");
        pending = lines.pop() || "";
        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          if (event.type === "sources") citations = event.citations;
          if (event.type === "delta") { text += event.text; onUpdate(text, citations); }
          if (event.type === "done") result = event.response;
        }
        if (done) break;
      }
    } finally { reader.releaseLock(); }
    if (!result) throw new Error("The answer was interrupted. Please reload the conversation.");
    return result;
  },
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
  conversations: (token?: string | null, query = "", offset = 0) =>
    request<Conversation[]>(`/chat/conversations?${new URLSearchParams({ query, offset: String(offset), limit: "50" })}`, { token }),
  conversation: (id: string, token?: string | null) =>
    request<Conversation>(`/chat/conversations/${encodeURIComponent(id)}`, { token }),
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
    request<{ conversation_id: string; summary: string; citations: Citation[] }>(
      "/circulars/summarize",
      {
        method: "POST",
        token,
        body: JSON.stringify(payload),
      },
    ),
  uploadPolicy: () => request<{ google_processing: boolean; max_upload_mb: number; expires_minutes: number }>("/health/upload-policy"),
  uploadPdf: (file: File, token?: string | null, allowGoogleProcessing = false) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("allow_google_processing", String(allowGoogleProcessing));
    return request<UploadSession>("/uploads/pdf", {
      method: "POST",
      token,
      body: formData,
    });
  },
  uploadSession: (id: string, token?: string | null) => request<UploadSession>(`/uploads/${id}`, { token }),
  deleteUpload: (id: string, token?: string | null) => request<void>(`/uploads/${id}`, { method: "DELETE", token }),
  bookmarks: (token?: string | null) => request<Circular[]>("/circulars/bookmarks", { token }),
  bookmark: (id: string, saved: boolean, token?: string | null) => request<void>(`/circulars/${id}/bookmark`, { method: saved ? "POST" : "DELETE", token }),
  crawl: (token?: string | null) => request<{ discovered: number; indexed: number; skipped: number; errors: string[] }>("/circulars/crawl", { method: "POST", token }),
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
