"use client";

/**
 * Landing Page
 * ============
 * The entry point of the application.
 * Shows a login/register form, or redirects to dashboard if authenticated.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { setToken, isAuthenticated } from "@/lib/auth";
import { Youtube, Sparkles, Brain, Clock } from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) {
      router.push("/dashboard");
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "register") {
        await authApi.register({ email, password, full_name: fullName });
        // After registration, login automatically
      }

      const res = await authApi.login({ email, password });
      setToken(res.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* ── Left Panel: Hero ──────────────────────────────── */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-center p-16 relative overflow-hidden">
        {/* Background gradient blobs */}
        <div className="absolute top-1/4 -left-20 w-72 h-72 bg-red-500/20 rounded-full blur-[100px]" />
        <div className="absolute bottom-1/4 right-10 w-64 h-64 bg-purple-500/20 rounded-full blur-[100px]" />

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-purple-500 rounded-xl flex items-center justify-center">
              <Youtube className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-3xl font-bold gradient-text">
              YouTube Intelligence
            </h1>
          </div>

          <p className="text-xl text-slate-300 mb-12 leading-relaxed max-w-lg">
            Chat with any YouTube video using AI. Ask questions, get timestamped
            answers, and explore video content like never before.
          </p>

          {/* Feature cards */}
          <div className="space-y-4">
            {[
              {
                icon: Brain,
                title: "Agentic RAG Pipeline",
                desc: "Hybrid search + cross-encoder reranking for precise answers",
              },
              {
                icon: Sparkles,
                title: "Powered by Gemini",
                desc: "Google's latest AI generates contextual, grounded responses",
              },
              {
                icon: Clock,
                title: "Timestamped Sources",
                desc: "Every answer links back to the exact moment in the video",
              },
            ].map((feature, i) => (
              <div
                key={i}
                className="glass rounded-xl p-4 flex items-start gap-4 transition-transform hover:scale-[1.02]"
              >
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500/20 to-purple-500/20 flex items-center justify-center shrink-0">
                  <feature.icon className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-200">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-slate-400">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Right Panel: Auth Form ────────────────────────── */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-purple-500 rounded-xl flex items-center justify-center">
              <Youtube className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold gradient-text">
              YouTube Intelligence
            </h1>
          </div>

          <div className="glass rounded-2xl p-8">
            <h2 className="text-2xl font-bold mb-2">
              {mode === "login" ? "Welcome back" : "Create account"}
            </h2>
            <p className="text-slate-400 mb-8">
              {mode === "login"
                ? "Sign in to continue to your dashboard"
                : "Start chatting with YouTube videos"}
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {mode === "register" && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Full Name
                  </label>
                  <input
                    id="full-name-input"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Your name"
                    required
                    className="w-full px-4 py-3 rounded-xl bg-[#0a0a0f] border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  Email
                </label>
                <input
                  id="email-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full px-4 py-3 rounded-xl bg-[#0a0a0f] border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  Password
                </label>
                <input
                  id="password-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={8}
                  className="w-full px-4 py-3 rounded-xl bg-[#0a0a0f] border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition"
                />
              </div>

              {error && (
                <p className="text-red-400 text-sm bg-red-500/10 p-3 rounded-lg">
                  {error}
                </p>
              )}

              <button
                id="submit-button"
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-red-500 to-purple-500 text-white font-semibold hover:from-red-600 hover:to-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading
                  ? "Please wait..."
                  : mode === "login"
                  ? "Sign In"
                  : "Create Account"}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-slate-400">
              {mode === "login" ? (
                <>
                  Don&apos;t have an account?{" "}
                  <button
                    id="toggle-auth-mode"
                    onClick={() => {
                      setMode("register");
                      setError("");
                    }}
                    className="text-purple-400 hover:text-purple-300 font-medium"
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button
                    id="toggle-auth-mode"
                    onClick={() => {
                      setMode("login");
                      setError("");
                    }}
                    className="text-purple-400 hover:text-purple-300 font-medium"
                  >
                    Sign in
                  </button>
                </>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
