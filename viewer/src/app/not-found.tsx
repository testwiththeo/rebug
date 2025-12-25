import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Session Not Found</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            This session doesn&apos;t exist or may have been deleted. Check the session ID and try again.
          </p>
          <Button asChild variant="outline">
            <Link href="/">Back to Sessions</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
