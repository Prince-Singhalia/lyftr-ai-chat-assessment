import { useMemo, useState } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { ErrorMessage } from './components/ErrorMessage';
import { MessageInput } from './components/MessageInput';
import { MetadataPanel } from './components/MetadataPanel';
import { sendMessage } from './services/api';
import type { Message } from './types/chat';
import './styles/global.css';
import './styles/chat.css';

export default function App() { const sessionId = useMemo(() => crypto.randomUUID(), []); const [messages, setMessages] = useState<Message[]>([]); const [loading, setLoading] = useState(false); const [error, setError] = useState(''); const submit = async (value: string) => { setError(''); setMessages(current => [...current, { role: 'user', content: value }]); setLoading(true); try { const result = await sendMessage(sessionId, value); setMessages(current => [...current, { role: 'assistant', content: result.reply, metadata: result.metadata }]); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to reach the assistant.'); } finally { setLoading(false); } }; return <div className="app-shell"><header className="topbar"><div className="brand"><span className="brand-icon">✦</span><span>resilient<span className="brand-muted">.ai</span></span></div><div className="session">SESSION <code>{sessionId.slice(0, 8)}</code></div></header><div className="layout"><MetadataPanel /><section className="conversation"><ChatWindow messages={messages} loading={loading} />{error && <ErrorMessage message={error} />}<MessageInput disabled={loading} onSend={submit} /><div className="disclaimer">Powered by a resilient multi-provider gateway · Enter to send, Shift + Enter for a new line</div></section></div></div> }
