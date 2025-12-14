import { defineConfig } from 'wxt';

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    name: 'Rebug',
    description: 'Record browser bug sessions and package them for AI analysis.',
    permissions: ['storage', 'tabs', 'scripting'],
    host_permissions: ['<all_urls>'],
    action: {
      default_title: 'Rebug',
    },
    web_accessible_resources: [
      {
        resources: ['page-hooks.js'],
        matches: ['<all_urls>'],
      },
    ],
  },
});
