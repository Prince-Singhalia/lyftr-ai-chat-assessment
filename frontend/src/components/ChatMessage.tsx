import type { Message } from '../types/chat';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function ChatMessage({ message }: { message: Message }) {
  const assistant = message.role === 'assistant';

  return (
    <article
      className={`message ${assistant ? 'assistant' : 'user'}`}
      data-testid={assistant ? 'assistant-message' : undefined}
    >
      <div className="message-role">{assistant ? 'Resilient AI' : 'You'}</div>
      <div className="message-content">
        {assistant ? (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              pre: ({ children, ...props }) => <pre className="markdown-code" {...props}>{children}</pre>,
              a: ({ children, ...props }) => <a {...props} target="_blank" rel="noreferrer">{children}</a>,
            }}
          >
            {message.content}
          </ReactMarkdown>
        ) : message.content}
      </div>
      {assistant && message.metadata && (
        <div className="metadata">
          <span data-testid="meta-source">{message.metadata.resolution_source}</span>
          <span data-testid="meta-model">{message.metadata.model}</span>
          <span data-testid="meta-latency">{message.metadata.latency_ms} ms</span>
          <span data-testid="meta-input-tokens">In {message.metadata.input_tokens}</span>
          <span data-testid="meta-output-tokens">Out {message.metadata.output_tokens}</span>
        </div>
      )}
    </article>
  );
}
