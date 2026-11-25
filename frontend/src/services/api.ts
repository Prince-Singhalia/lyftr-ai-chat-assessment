import type { ChatResponse, Message } from '../types/chat';
const API_BASE = (import.meta.env.VITE_API_BASE_URL || window.__APP_CONFIG__?.API_BASE_URL || '').replace(/\/$/, '');
async function request<T>(path: string, options?: RequestInit): Promise<T> { const response = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) }, ...options }); if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || `Request failed (${response.status})`); } return response.json(); }
export const sendMessage = (sessionId: string, message: string, systemPrompt?: string) => request<ChatResponse>('/chat', { method: 'POST', body: JSON.stringify({ session_id: sessionId, message, ...(systemPrompt ? { system_prompt: systemPrompt } : {}) }) });
export const getHistory = (sessionId: string) => request<{ session_id: string; messages: Message[] }>(`/sessions/${encodeURIComponent(sessionId)}/messages`);
declare global { interface Window { __APP_CONFIG__?: { API_BASE_URL?: string } } }
