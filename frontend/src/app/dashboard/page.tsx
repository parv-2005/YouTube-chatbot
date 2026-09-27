"use client";

/**
 * Dashboard Page
 * ==============
 * Main dashboard after login. Shows:
 * - Video ingestion form (paste a YouTube URL)
 * - List of previously ingested videos
 * - Navigate to chat for any ready video
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { videosApi, conversationsApi, authApi } from "@/lib/api";
import { isAuthenticated, removeToken } from "@/lib/auth";
import {
  Youtube,
  Plus,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  MessageSquarePlus,
  LogOut,
  Sparkles,
} from "lucide-react";

interface Video {
  id: string;
  youtube_video_id: string;
  url: string;
  title: string | null;
  transcript_source: string;
  chunk_count: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [videos, setVideos] = useState<Video[]>([]);
  const [url, setUrl] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState("");
  const [userName, setUserName] = useState("");

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/");
      return;
    }
    loadVideos();
    loadUser();
  }, [router]);

  const loadUser = async () => {
    try {
      const user = await authApi.me();
      setUserName(user.full_name || user.email);
    } catch {
      // Token might be expired
      removeToken();
      router.push("/");
    }
  };

  const loadVideos = async () => {
    try {
      const data = await videosApi.list();
      setVideos(data.videos);
    } catch (err: any) {
      console.error("Failed to load videos:", err);
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIngesting(true);

    try {
      await videosApi.ingest(url);
      setUrl("");
      await loadVideos();
    } catch (err: any) {
      setError(err.message || "Failed to ingest video");
    } finally {
      setIngesting(false);
    }
  };

  const handleStartChat = async (video: Video) => {
    try {
      const conv: any = await conversationsApi.create(video.id);
      router.push(`/chat/${conv.id}`);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleLogout = () => {
    removeToken();
    router.push("/");
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "ready":
        return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      case "processing":
        return <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />;
      case "failed":
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-slate-400" />;
    }
  };

  return (
    <div className="min-h-screen">
      {/* ── Header ──────────────────────────────────────── */}
      <header className="glass sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-red-500 to-purple-500 rounded-lg flex items-center justify-center">
              <Youtube className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-semibold gradient-text">
              YouTube Intelligence
            </span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-400">
              Hello, {userName}
            </span>
            <button
              id="logout-button"
              onClick={handleLogout}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        {/* ── Ingest Form ─────────────────────────────────── */}
        <div className="glass rounded-2xl p-8 mb-10">
          <div className="flex items-center gap-3 mb-4">
            <Sparkles className="w-6 h-6 text-purple-400" />
            <h2 className="text-xl font-semibold">Ingest a YouTube Video</h2>
          </div>
          <p className="text-slate-400 mb-6">
            Paste a YouTube URL below. The system will extract the transcript
            (with Whisper fallback), chunk it, embed it, and make it searchable.
          </p>

          <form onSubmit={handleIngest} className="flex gap-3">
            <input
              id="video-url-input"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              required
              className="flex-1 px-4 py-3 rounded-xl bg-[#0a0a0f] border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition"
            />
            <button
              id="ingest-button"
              type="submit"
              disabled={ingesting}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-red-500 to-purple-500 text-white font-medium flex items-center gap-2 hover:from-red-600 hover:to-purple-600 transition-all disabled:opacity-50"
            >
              {ingesting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Ingest
                </>
              )}
            </button>
          </form>

          {error && (
            <p className="mt-4 text-red-400 text-sm bg-red-500/10 p-3 rounded-lg">
              {error}
            </p>
          )}
        </div>

        {/* ── Videos List ─────────────────────────────────── */}
        <h2 className="text-xl font-semibold mb-6">Your Videos</h2>

        {videos.length === 0 ? (
          <div className="glass rounded-2xl p-12 text-center">
            <Youtube className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">
              No videos yet. Paste a YouTube URL above to get started.
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {videos.map((video) => (
              <div
                key={video.id}
                className="glass rounded-xl p-5 flex items-center justify-between hover:bg-[#1c1c2e] transition group"
              >
                <div className="flex items-center gap-4 min-w-0">
                  {statusIcon(video.status)}
                  <div className="min-w-0">
                    <h3 className="font-medium text-slate-200 truncate">
                      {video.title || video.youtube_video_id}
                    </h3>
                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                      <span className="capitalize">
                        Transcript: {video.transcript_source || "pending"}
                      </span>
                      <span>•</span>
                      <span>{video.chunk_count} chunks</span>
                      <span>•</span>
                      <span className="capitalize">{video.status}</span>
                    </div>
                    {video.error_message && (
                      <p className="text-xs text-red-400 mt-1">
                        {video.error_message}
                      </p>
                    )}
                  </div>
                </div>

                {video.status === "ready" && (
                  <button
                    onClick={() => handleStartChat(video)}
                    className="shrink-0 ml-4 px-4 py-2 rounded-lg bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 hover:text-purple-300 transition flex items-center gap-2 text-sm font-medium"
                  >
                    <MessageSquarePlus className="w-4 h-4" />
                    Chat
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
