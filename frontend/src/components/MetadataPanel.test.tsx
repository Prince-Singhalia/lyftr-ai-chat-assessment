import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { MetadataPanel } from './MetadataPanel';

afterEach(cleanup);

describe('metadata panel', () => {
  it('describes persistent conversation history without assuming the local database provider', () => {
    render(<MetadataPanel />);
    expect(screen.getByText('Persistent conversation history enabled')).toBeInTheDocument();
    expect(screen.queryByText(/SQLite history enabled/i)).not.toBeInTheDocument();
  });
});
