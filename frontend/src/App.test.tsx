import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import type { ChatResponse, Message } from './types/chat';

const api = vi.hoisted(() => ({ getHistory: vi.fn(), sendMessage: vi.fn() }));
vi.mock('./services/api', () => api);

const metadata = {
  resolution_source: 'LIVE_INFERENCE' as const,
  model: 'gemini/gemini-3.1-flash-lite',
  latency_ms: 100,
  input_tokens: 4,
  output_tokens: 3,
  key_id: 'key_1',
  fallback_attempts: 0,
};
const generatedSessionId = '123e4567-e89b-12d3-a456-426614174000';

function send(text: string) {
  fireEvent.change(screen.getByTestId('chat-input'), { target: { value: text } });
  fireEvent.click(screen.getByTestId('send-button'));
}

function visibleMessages(): string[] {
  return Array.from(document.querySelectorAll('.message .message-content'), (element) => element.textContent ?? '');
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => {
  window.localStorage.clear();
  api.getHistory.mockReset();
  api.sendMessage.mockReset();
  vi.spyOn(globalThis.crypto, 'randomUUID').mockReturnValue(generatedSessionId);
});

describe('conversation session restoration', () => {
  it('reuses the saved session, sends multiple turns, and restores the chronological history after remount', async () => {
    const sessionId = 'existing-session-123';
    const stored: Message[] = [
      { role: 'user', content: 'Earlier question' },
      { role: 'assistant', content: 'Earlier answer', metadata },
    ];
    window.localStorage.setItem('resilient-ai-chat.active-session-id', sessionId);
    api.getHistory.mockImplementation(async (requestedSession: string) => ({ session_id: requestedSession, messages: [...stored] }));
    api.sendMessage.mockImplementation(async (requestedSession: string, message: string): Promise<ChatResponse> => {
      const reply = `Answer to ${message}`;
      stored.push({ role: 'user', content: message }, { role: 'assistant', content: reply, metadata });
      return { session_id: requestedSession, reply, metadata };
    });

    const firstMount = render(<App />);
    await screen.findByText('Earlier answer');
    expect(api.getHistory).toHaveBeenCalledWith(sessionId);
    expect(globalThis.crypto.randomUUID).not.toHaveBeenCalled();

    send('Follow-up one');
    await screen.findByText('Answer to Follow-up one');
    send('Follow-up two');
    await screen.findByText('Answer to Follow-up two');
    expect(api.sendMessage).toHaveBeenNthCalledWith(1, sessionId, 'Follow-up one');
    expect(api.sendMessage).toHaveBeenNthCalledWith(2, sessionId, 'Follow-up two');
    expect(window.localStorage.length).toBe(1);
    expect(window.localStorage.getItem('resilient-ai-chat.active-session-id')).toBe(sessionId);

    firstMount.unmount();
    render(<App />);
    await screen.findByText('Answer to Follow-up two');
    expect(api.getHistory).toHaveBeenLastCalledWith(sessionId);
    expect(visibleMessages()).toEqual([
      'Earlier question', 'Earlier answer',
      'Follow-up one', 'Answer to Follow-up one',
      'Follow-up two', 'Answer to Follow-up two',
    ]);
  });

  it('starts an isolated session only on New Chat and leaves the previous session history available', async () => {
    const previousSession = 'previous-session-123';
    const previousMessages: Message[] = [
      { role: 'user', content: 'Keep this history' },
      { role: 'assistant', content: 'Previous answer', metadata },
    ];
    const histories = new Map([[previousSession, previousMessages]]);
    window.localStorage.setItem('resilient-ai-chat.active-session-id', previousSession);
    api.getHistory.mockImplementation(async (requestedSession: string) => ({ session_id: requestedSession, messages: histories.get(requestedSession) ?? [] }));
    api.sendMessage.mockImplementation(async (requestedSession: string, message: string): Promise<ChatResponse> => {
      const reply = `Answer to ${message}`;
      histories.set(requestedSession, [...(histories.get(requestedSession) ?? []), { role: 'user', content: message }, { role: 'assistant', content: reply, metadata }]);
      return { session_id: requestedSession, reply, metadata };
    });
    render(<App />);
    await screen.findByText('Previous answer');

    fireEvent.click(screen.getByTestId('new-chat-button'));

    await waitFor(() => expect(window.localStorage.getItem('resilient-ai-chat.active-session-id')).toBe(generatedSessionId));
    await screen.findByText('What can I help you solve?');
    expect(api.getHistory).toHaveBeenLastCalledWith(generatedSessionId);
    expect(visibleMessages()).toEqual([]);
    expect(api.getHistory).toHaveBeenCalledWith(previousSession);
    send('A separate conversation');
    await screen.findByText('Answer to A separate conversation');
    expect(api.sendMessage).toHaveBeenCalledWith(generatedSessionId, 'A separate conversation');
    await expect(api.getHistory(previousSession)).resolves.toEqual({ session_id: previousSession, messages: previousMessages });
    expect(histories.get(generatedSessionId)?.map((message) => message.content)).toEqual(['A separate conversation', 'Answer to A separate conversation']);
    expect(globalThis.crypto.randomUUID).toHaveBeenCalledTimes(1);
  });

  it('shows an empty chat for an empty history and remains usable when history loading fails', async () => {
    api.getHistory.mockResolvedValueOnce({ session_id: generatedSessionId, messages: [] })
      .mockRejectedValueOnce(new Error('Network unavailable'));
    const firstMount = render(<App />);
    await screen.findByText('What can I help you solve?');
    firstMount.unmount();

    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to restore this conversation. Network unavailable');
    expect(screen.getByTestId('chat-input')).not.toBeDisabled();
    api.sendMessage.mockResolvedValue({ session_id: generatedSessionId, reply: 'Chat still works', metadata });
    send('Can I still chat?');
    await screen.findByText('Chat still works');
    expect(globalThis.crypto.randomUUID).toHaveBeenCalledTimes(1);
  });
});
