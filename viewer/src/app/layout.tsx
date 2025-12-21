import type { Metadata } from 'next';
import 'rrweb-player/dist/style.css';
import './globals.css';

export const metadata: Metadata = {
  title: 'Rebug Viewer',
  description: 'Replay recorded Rebug sessions',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
