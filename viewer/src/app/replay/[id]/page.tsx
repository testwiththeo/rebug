import { notFound } from 'next/navigation';

import { SessionReplay } from '@/components/SessionReplay';
import { getReplayPayload } from '@/lib/api';

interface ReplayPageProps {
  params: {
    id: string;
  };
}

export default async function ReplayPage({ params }: ReplayPageProps) {
  try {
    const payload = await getReplayPayload(params.id);
    return <SessionReplay payload={payload} />;
  } catch (error) {
    if (error instanceof Error && error.message.startsWith('404')) {
      notFound();
    }
    throw error;
  }
}
