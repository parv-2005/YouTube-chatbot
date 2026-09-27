/**
 * TypeScript Type Definitions
 * ===========================
 * Shared types used across the frontend application.
 * These mirror the backend Pydantic schemas to ensure type safety.
 */

// ── Auth Types ─────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ── Video Types ────────────────────────────────────────────

export interface Video {
  id: string;
  youtube_video_id: string;
  url: string;
  title: string | null;
  channel_name: string | null;
  duration_seconds: number | null;
  transcript_source: "youtube" | "whisper";
  chunk_count: number;
  status: "pending" | "processing" | "ready" | "failed";
  error_message: string | null;
  created_at: string;
  processed_at: string | null;
}

// ── Chat Types ─────────────────────────────────────────────

export interface SourceReference {
  text: string;
  video_id: string;
  start_time: number;
  end_time: number;
  timestamp_label: string;
  timestamp_link: string;
}

export interface ChatRequest {
  conversation_id: string;
  message: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceReference[];
}

// ── Conversation Types ─────────────────────────────────────

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceReference[] | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  video_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  video_title: string | null;
  messages: Message[];
}

export interface ConversationListItem {
  id: string;
  video_id: string;
  title: string;
  video_title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

// ── API Error ──────────────────────────────────────────────

export interface ApiError {
  detail: string;
}
