import { installRecorderMessageHandler } from '@/src/content/recorder';

export default defineContentScript({
  matches: ['<all_urls>'],
  runAt: 'document_start',
  main() {
    installRecorderMessageHandler();
  },
});
