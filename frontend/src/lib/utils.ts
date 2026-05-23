import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Avoid `https://host//api/...` when env URL has a trailing slash. */
function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

export const API_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
);
export const WS_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"
);
