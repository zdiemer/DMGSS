const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  // Full-RAM documents need parsing/reload headroom; specs bound CPU progress separately.
  testDir: './tests', timeout: 120000, workers: 1,
  // Distribute independent tests across CI shards, still one browser per runner.
  fullyParallel: true,
  // Full-map style evaluation can itself exceed five seconds on shared runners.
  expect: {timeout:30000},
  use: { baseURL: 'http://127.0.0.1:8080', javaScriptEnabled: false, screenshot: 'only-on-failure' },
  // Full-map fixture generation exceeded five minutes on shared CI runners.
  webServer: { timeout:600000, command: 'python3 tools/build.py --fixtures && python3 -m gunicorn --chdir tools --bind 127.0.0.1:8080 --workers 2 --no-control-socket --access-logfile - server:application', url: 'http://127.0.0.1:8080', reuseExistingServer: false },
  projects: [
    { name: 'desktop', use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } } },
    { name: 'chromium-mobile', use: { browserName: 'chromium', viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
    { name: 'webkit-mobile', testMatch: /(compatibility|portable|checkpoint|automatic|converter|conformance|alu|bits|high|interrupts|timing|timer|serial|rom|memory|mbc1|lcd|palette|vram)\.spec\.js/, use: { browserName: 'webkit', viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
});
