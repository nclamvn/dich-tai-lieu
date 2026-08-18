/**
 * Single source of truth for the backend base URL.
 *
 * Every module that talks to the backend must import API_BASE (and WS_URL for
 * websockets) from here. Previously the URL was duplicated across client.ts,
 * hooks.ts, the job detail page and the screenplay client — and two of those
 * defaulted to :3000 (the Next.js frontend port) instead of :8000, so PDF
 * preview and the screenplay API pointed at the wrong server in local dev.
 *
 * In production NEXT_PUBLIC_API_URL is always set; the localhost fallback is
 * dev-only.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Base websocket URL (…/ws is appended by callers as needed). */
export const WS_URL = API_BASE.replace(/^http/, "ws") + "/ws";
