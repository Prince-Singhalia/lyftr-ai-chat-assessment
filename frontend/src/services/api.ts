import type { ChatResponse, Message } from '../types/chat';
const API_BASE = (import.meta.env.VITE_API_BASE_URL || window.__APP_CONFIG__?.API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail || `Request failed (${response.status})`, response.status);
  }
  return response.json();
}

export const sendMessage = (sessionId: string, message: string, systemPrompt?: string) => request<ChatResponse>('/chat', { method: 'POST', body: JSON.stringify({ session_id: sessionId, message, ...(systemPrompt ? { system_prompt: systemPrompt } : {}) }) });

export async function getHistory(sessionId: string): Promise<{ session_id: string; messages: Message[] }> {
  try {
    return await request<{ session_id: string; messages: Message[] }>(`/sessions/${encodeURIComponent(sessionId)}/messages`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return { session_id: sessionId, messages: [] };
    throw error;
  }
}

declare global { interface Window { __APP_CONFIG__?: { API_BASE_URL?: string } } }
