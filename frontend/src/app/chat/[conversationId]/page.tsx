"use client";

/**
 * Chat Page
 * =========
 * The main chat interface for conversing with a YouTube video.
 *
 * Features:
 * - Message list with user/assistant bubbles
 * - Streaming response display
 * - Source references with clickable timestamp links
 * - Typing indicator during generation
 * - Auto-scroll to latest message
 */

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { conversationsApi, chatApi } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import {
  Youtube,
  Send,
  ArrowLeft,
  ExternalLink,
  Clock,
  Loader2,
  Bot,
  User,
} from "lucide-react";

interface SourceRef {
  text: string;
  video_id: string;
  start_time: number;
  end_time: number;
  timestamp_label: string;
  timestamp_link: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceRef[] | null;
  created_at: string;
}

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const conversationId = params.conversationId as string;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState("");
  const [streamSources, setStreamSources] = useState<SourceRef[]>([]);
  const [conversationTitle, setConversationTitle] = useState("");
  const [videoTitle, setVideoTitle] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/");
      return;
    }
    loadConversation();
  }, [conversationId, router]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamedText]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadConversation = async () => {
    try {
      const conv: any = await conversationsApi.get(conversationId);
      setMessages(conv.messages || []);
      setConversationTitle(conv.title);
      setVideoTitle(conv.video_title || "");
    } catch (err) {
      console.error("Failed to load conversation:", err);
      router.push("/dashboard");
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading || streaming) return;

    const userMessage = input.trim();
    setInput("");

    // Optimistically add the user message
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      sources: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    // Use streaming
    setStreaming(true);
    setStreamedText("");
    setStreamSources([]);

    try {
      let fullText = "";
      let sources: SourceRef[] = [];

      for await (const chunk of chatApi.stream(conversationId, userMessage)) {
        if (chunk.done) {
          sources = chunk.sources || [];
          setStreamSources(sources);
        } else if (chunk.token) {
          fullText += chunk.token;
          setStreamedText(fullText);
        }
      }

      // Add the completed assistant message
      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: fullText,
        sources: sources,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      // Fallback to non-streaming on error
      try {
        const res = await chatApi.send(conversationId, userMessage);
        const assistantMsg: ChatMessage = {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: res.answer,
          sources: res.sources,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (fallbackErr: any) {
        const errorMsg: ChatMessage = {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
          sources: null,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } finally {
      setStreaming(false);
      setStreamedText("");
      setStreamSources([]);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* ── Header ──────────────────────────────────────── */}
      <header className="glass shrink-0">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center gap-4">
          <button
            id="back-to-dashboard"
            onClick={() => router.push("/dashboard")}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 bg-gradient-to-br from-red-500 to-purple-500 rounded-lg flex items-center justify-center shrink-0">
              <Youtube className="w-4 h-4 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-semibold text-slate-200 truncate">
                {conversationTitle || "New Conversation"}
              </h1>
              {videoTitle && (
                <p className="text-xs text-slate-500 truncate">{videoTitle}</p>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* ── Messages ────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">
          {messages.length === 0 && !streaming && (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-red-500/20 to-purple-500/20 rounded-2xl flex items-center justify-center mb-6">
                <Bot className="w-8 h-8 text-purple-400" />
              </div>
              <h2 className="text-xl font-semibold text-slate-200 mb-2">
                Ready to chat
              </h2>
              <p className="text-slate-400 max-w-md">
                Ask any question about this video. I&apos;ll find the relevant parts
                of the transcript and give you an answer with timestamps.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 animate-fade-in ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-red-500/20 flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-purple-400" />
                </div>
              )}

              <div
                className={`max-w-[80%] ${
                  msg.role === "user"
                    ? "bg-gradient-to-r from-red-500/20 to-purple-500/20 border border-purple-500/20 rounded-2xl rounded-br-md px-5 py-3"
                    : "space-y-3"
                }`}
              >
                <div
                  className={`${
                    msg.role === "assistant"
                      ? "glass rounded-2xl rounded-bl-md px-5 py-4"
                      : ""
                  }`}
                >
                  <p className="text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </p>
                </div>

                {/* Source references */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {msg.sources.map((src, i) => (
                      <a
                        key={i}
                        href={src.timestamp_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 hover:text-purple-300 transition text-xs font-medium"
                      >
                        <Clock className="w-3 h-3" />
                        {src.timestamp_label}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    ))}
                  </div>
                )}
              </div>

              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500/20 to-red-500/10 flex items-center justify-center shrink-0 mt-1">
                  <User className="w-4 h-4 text-red-400" />
                </div>
              )}
            </div>
          ))}

          {/* Streaming response */}
          {streaming && streamedText && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-red-500/20 flex items-center justify-center shrink-0 mt-1">
                <Bot className="w-4 h-4 text-purple-400" />
              </div>
              <div className="glass rounded-2xl rounded-bl-md px-5 py-4 max-w-[80%]">
                <p className="text-slate-200 whitespace-pre-wrap leading-relaxed">
                  {streamedText}
                  <span className="inline-block w-2 h-5 bg-purple-400 animate-pulse ml-0.5 align-text-bottom" />
                </p>
              </div>
            </div>
          )}

          {/* Typing indicator */}
          {streaming && !streamedText && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-red-500/20 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-purple-400" />
              </div>
              <div className="glass rounded-2xl px-5 py-4">
                <div className="flex gap-1.5">
                  <div className="w-2 h-2 bg-purple-400 rounded-full typing-dot" />
                  <div className="w-2 h-2 bg-purple-400 rounded-full typing-dot" />
                  <div className="w-2 h-2 bg-purple-400 rounded-full typing-dot" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Input ───────────────────────────────────────── */}
      <div className="shrink-0 glass">
        <form
          onSubmit={handleSend}
          className="max-w-4xl mx-auto px-6 py-4 flex gap-3"
        >
          <input
            id="chat-input"
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this video..."
            disabled={streaming}
            className="flex-1 px-5 py-3 rounded-xl bg-[#0a0a0f] border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition disabled:opacity-50"
          />
          <button
            id="send-button"
            type="submit"
            disabled={!input.trim() || streaming}
            className="px-5 py-3 rounded-xl bg-gradient-to-r from-red-500 to-purple-500 text-white font-medium flex items-center gap-2 hover:from-red-600 hover:to-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {streaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
