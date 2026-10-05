const DEFAULT_REDIRECT = "/dashboard";

/**
 * Returns a safe in-app path from a user-supplied `next` value.
 * Only same-origin absolute paths ("/foo") are accepted; anything that could
 * navigate off-site ("//evil.com", "https://...", "/\evil") falls back to the dashboard.
 */
export function safeNextPath(next: string | null | undefined): string {
  if (!next) return DEFAULT_REDIRECT;
  if (!next.startsWith("/")) return DEFAULT_REDIRECT;
  if (next.startsWith("//") || next.includes("\\")) return DEFAULT_REDIRECT;
  return next;
}

/** Reads the `next` query parameter from the current browser location (client-side only). */
export function getNextFromLocation(): string {
  if (typeof window === "undefined") return DEFAULT_REDIRECT;
  return safeNextPath(new URLSearchParams(window.location.search).get("next"));
}
