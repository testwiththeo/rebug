import { installBackgroundHandlers } from '@/src/background/service-worker';

export default defineBackground(() => {
  installBackgroundHandlers();
});
