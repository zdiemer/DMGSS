const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests', timeout: 30000, workers: 1,
  use: { baseURL: 'http://127.0.0.1:8080', javaScriptEnabled: false, screenshot: 'only-on-failure' },
  webServer: { command: 'python3 tools/build.py --fixtures && python3 -m http.server 8080 --directory dist', url: 'http://127.0.0.1:8080', reuseExistingServer: false },
  projects: [
    { name: 'desktop', use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { browserName: 'chromium', viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
});
