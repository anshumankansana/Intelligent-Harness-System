import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Production API (Render) — used when Vercel env vars are not set. */
export const PRODUCTION_API_URL = "https://intelligent-harness-system.onrender.com";
export const PRODUCTION_WS_URL = "wss://intelligent-harness-system.onrender.com";

/** Avoid `https://host//api/...` when env URL has a trailing slash. */
function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

function resolveApiUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) return normalizeBaseUrl(fromEnv);
  if (process.env.NODE_ENV === "production") {
    return PRODUCTION_API_URL;
  }
  return "http://localhost:8000";
}

function resolveWsUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (fromEnv) return normalizeBaseUrl(fromEnv);
  if (process.env.NODE_ENV === "production") {
    return PRODUCTION_WS_URL;
  }
  return "ws://localhost:8000";
}

export const API_URL = resolveApiUrl();
export const WS_URL = resolveWsUrl();
