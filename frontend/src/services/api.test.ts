import { afterEach, describe, expect, it, vi } from 'vitest';
import { getHistory } from './api';

afterEach(() => vi.unstubAllGlobals());

describe('conversation history API', () => {
  it('treats the backend 404 for an empty session as an empty conversation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'session not found' }),
    }));

    await expect(getHistory('empty-session')).resolves.toEqual({ session_id: 'empty-session', messages: [] });
    expect(fetch).toHaveBeenCalledWith('/sessions/empty-session/messages', expect.any(Object));
  });

  it('preserves network and server failures for the UI to report', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network unavailable')));
    await expect(getHistory('session')).rejects.toThrow('Network unavailable');

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'service unavailable' }),
    }));
    await expect(getHistory('session')).rejects.toMatchObject({ status: 503 });
  });
});
