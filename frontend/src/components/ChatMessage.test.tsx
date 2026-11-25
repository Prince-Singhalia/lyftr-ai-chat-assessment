import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ChatMessage } from './ChatMessage';
import { MessageInput } from './MessageInput';
import type { Message } from '../types/chat';

afterEach(cleanup);

const metadata = {
  resolution_source: 'LIVE_INFERENCE' as const,
  model: 'gemini/gemini-3.8-flash',
  latency_ms: 812,
  input_tokens: 20,
  output_tokens: 10,
  key_id: 'key_1',
  fallback_attempts: 0,
};

describe('assistant Markdown rendering', () => {
  it('renders headings, emphasis, lists, code, links, quotes, separators, and GFM tables', () => {
    const message: Message = {
      role: 'assistant',
      content: '# Heading\n\n**Bold** and `inline()`\n\n- one\n- two\n\n```ts\nconst answer = 42;\n```\n\n> A quote\n\n---\n\n[Docs](https://example.com)\n\n| A | B |\n| - | - |\n| 1 | 2 |',
      metadata,
    };
    const { container } = render(<ChatMessage message={message} />);
    expect(screen.getByRole('heading', { name: 'Heading', level: 1 })).toBeInTheDocument();
    expect(screen.getByText('Bold').tagName).toBe('STRONG');
    expect(screen.getByText('one')).toBeInTheDocument();
    expect(container.querySelector('pre code')).toHaveTextContent('const answer = 42;');
    expect(container.querySelector('blockquote')).toHaveTextContent('A quote');
    expect(container.querySelector('hr')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Docs' })).toHaveAttribute('rel', 'noreferrer');
    expect(container.querySelector('table')).toBeInTheDocument();
  });

  it('keeps long responses readable and shows all required assistant metadata ids', () => {
    const longText = Array.from({ length: 240 }, (_, index) => `Paragraph ${index + 1}: ${'Readable response text. '.repeat(5)}`).join('\n\n');
    const { container } = render(<ChatMessage message={{ role: 'assistant', content: longText, metadata }} />);
    expect(container.querySelectorAll('.message-content p')).toHaveLength(240);
    for (const id of ['assistant-message', 'meta-source', 'meta-model', 'meta-latency', 'meta-input-tokens', 'meta-output-tokens']) {
      expect(screen.getByTestId(id)).toBeInTheDocument();
    }
  });

  it('does not interpret embedded HTML as markup', () => {
    const { container } = render(<ChatMessage message={{ role: 'assistant', content: '<img src=x onerror=alert(1)>', metadata }} />);
    expect(container.querySelector('img')).toBeNull();
    expect(screen.getByTestId('assistant-message')).toHaveTextContent('<img src=x onerror=alert(1)>');
  });

  it('preserves the input and send button test ids', () => {
    const onSend = vi.fn();
    render(<MessageInput disabled={false} onSend={onSend} />);
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
    expect(screen.getByTestId('send-button')).toBeInTheDocument();
    const input = screen.getByTestId('chat-input');
    fireEvent.change(input, { target: { value: 'Question' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    expect(onSend).toHaveBeenCalledWith('Question');
    expect(input).toHaveValue('');
  });
});
