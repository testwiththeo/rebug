import type { Metadata } from 'next';
import 'rrweb-player/dist/style.css';
import './globals.css';

export const metadata: Metadata = {
  title: 'Rebug — Session Replay Viewer',
  description: 'Replay recorded Rebug sessions, inspect console and network events, and file bug reports.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
