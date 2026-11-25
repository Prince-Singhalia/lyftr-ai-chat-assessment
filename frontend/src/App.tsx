import { useEffect, useRef, useState } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { ErrorMessage } from './components/ErrorMessage';
import { MessageInput } from './components/MessageInput';
import { MetadataPanel } from './components/MetadataPanel';
import { getHistory, sendMessage } from './services/api';
import { createSessionId, getOrCreateActiveSessionId, setActiveSessionId } from './services/session';
import type { Message } from './types/chat';
import './styles/global.css';
import './styles/chat.css';

export default function App() {
  const [sessionId, setSessionId] = useState(getOrCreateActiveSessionId);
  const sessionIdRef = useRef(sessionId);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    setMessages([]);
    setError('');

    getHistory(sessionId)
      .then((history) => {
        if (cancelled) return;
        if (history.session_id !== sessionId || !Array.isArray(history.messages)) {
          throw new Error('The server returned invalid conversation history.');
        }
        setMessages(history.messages);
      })
      .catch((restoreError: unknown) => {
        if (cancelled) return;
        setMessages([]);
        setError(`Unable to restore this conversation. ${restoreError instanceof Error ? restoreError.message : 'Please try again.'}`);
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const submit = async (value: string) => {
    const requestSessionId = sessionIdRef.current;
    setError('');
    setMessages((current) => [...current, { role: 'user', content: value }]);
    setLoading(true);
    try {
      const result = await sendMessage(requestSessionId, value);
      if (sessionIdRef.current === requestSessionId) {
        setMessages((current) => [...current, { role: 'assistant', content: result.reply, metadata: result.metadata }]);
      }
    } catch (submitError) {
      if (sessionIdRef.current === requestSessionId) {
        setError(submitError instanceof Error ? submitError.message : 'Unable to reach the assistant.');
      }
    } finally {
      if (sessionIdRef.current === requestSessionId) setLoading(false);
    }
  };

  const startNewChat = () => {
    const nextSessionId = createSessionId();
    sessionIdRef.current = nextSessionId;
    setActiveSessionId(nextSessionId);
    setSessionId(nextSessionId);
    setMessages([]);
    setLoading(false);
    setHistoryLoading(true);
    setError('');
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-icon">✦</span><span>resilient<span className="brand-muted">.ai</span></span></div>
        <div className="topbar-actions">
          <div className="session">SESSION <code>{sessionId.slice(0, 8)}</code></div>
          <button className="new-chat-button" data-testid="new-chat-button" onClick={startNewChat}>New chat</button>
        </div>
      </header>
      <div className="layout">
        <MetadataPanel />
        <section className="conversation">
          <ChatWindow messages={messages} loading={loading} historyLoading={historyLoading} />
          {error && <ErrorMessage message={error} />}
          <MessageInput disabled={loading || historyLoading} onSend={submit} />
          <div className="disclaimer">Powered by a resilient multi-provider gateway · Enter to send, Shift + Enter for a new line</div>
        </section>
      </div>
    </div>
  );
}
