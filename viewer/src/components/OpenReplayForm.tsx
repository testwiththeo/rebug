'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search } from 'lucide-react';

import { Button } from '@/components/ui/button';

export function OpenReplayForm() {
  const [sessionId, setSessionId] = useState('');
  const router = useRouter();

  return (
    <form
      className="flex gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        const trimmed = sessionId.trim();
        if (trimmed) {
          router.push(`/replay/${trimmed}`);
        }
      }}
    >
      <input
        className="h-10 min-w-0 flex-1 rounded-md border bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        onChange={(event) => setSessionId(event.target.value)}
        placeholder="Session UUID"
        value={sessionId}
      />
      <Button type="submit">
        <Search className="mr-2 h-4 w-4" />
        Open
      </Button>
    </form>
  );
}
