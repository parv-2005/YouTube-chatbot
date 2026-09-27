/**
 * API Client
 * ==========
 * Centralized API client for all backend communication.
 * Handles authentication headers, error parsing, and base URL configuration.
 */

import { getToken } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/**
 * Make an authenticated API request.
 * Automatically includes the JWT token if available.
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: "An unknown error occurred",
    }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

// ── Auth API ──────────────────────────────────────────────

export const authApi = {
  register: (data: { email: string; password: string; full_name: string }) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(data) }),

  login: (data: { email: string; password: string }) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  me: () => request<{ id: string; email: string; full_name: string | null }>("/auth/me"),
};

// ── Videos API ────────────────────────────────────────────

export const videosApi = {
  ingest: (url: string) =>
    request("/videos/ingest", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  list: () =>
    request<{ videos: any[]; total: number }>("/videos"),

  get: (id: string) => request(`/videos/${id}`),
};

// ── Conversations API ─────────────────────────────────────

export const conversationsApi = {
  create: (videoId: string, title?: string) =>
    request("/conversations", {
      method: "POST",
      body: JSON.stringify({ video_id: videoId, title }),
    }),

  list: () =>
    request<{ conversations: any[]; total: number }>("/conversations"),

  get: (id: string) => request(`/conversations/${id}`),

  delete: (id: string) =>
    request(`/conversations/${id}`, { method: "DELETE" }),
};

// ── Chat API ──────────────────────────────────────────────

export const chatApi = {
  send: (conversationId: string, message: string) =>
    request<{ answer: string; sources: any[] }>("/chat", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId, message }),
    }),

  /**
   * Send a message and receive a streaming response via SSE.
   * Returns a ReadableStream of tokens.
   */
  stream: async function* (conversationId: string, message: string) {
    const token = getToken();

    const response = await fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ conversation_id: conversationId, message }),
    });

    if (!response.ok) {
      throw new Error("Streaming request failed");
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) throw new Error("No response body");

    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = JSON.parse(line.slice(6));
          yield data;
        }
      }
    }
  },
};
