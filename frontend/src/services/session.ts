export const ACTIVE_SESSION_STORAGE_KEY = 'resilient-ai-chat.active-session-id';

export function createSessionId(): string {
  return crypto.randomUUID();
}

export function setActiveSessionId(sessionId: string): void {
  try {
    window.localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, sessionId);
  } catch {
    // Keep the current conversation usable when browser storage is unavailable.
  }
}

export function getOrCreateActiveSessionId(): string {
  try {
    const saved = window.localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY);
    if (saved && saved.trim() && saved.length <= 128) return saved;
  } catch {
    // Storage can be blocked by browser privacy settings.
  }

  const sessionId = createSessionId();
  setActiveSessionId(sessionId);
  return sessionId;
}
