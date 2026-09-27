/**
 * Auth Utilities
 * ==============
 * Token storage and authentication helpers.
 * Uses localStorage to persist the JWT token across page reloads.
 */

const TOKEN_KEY = "youtube_chatbot_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
