import { defineConfig, devices } from "@playwright/test";

// The demo is a static page, so the test server is a static server. The camera
// is stubbed inside the page rather than through Chromium's fake-device flags,
// because the useful test is "this exact dataset image produces this letter",
// and that needs a real image on the wire, not a test pattern.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:8099",
    ...devices["Desktop Chrome"],
    permissions: ["camera"],
    launchOptions: { args: ["--use-fake-ui-for-media-stream"] },
  },
  webServer: {
    command: "python3 -m http.server 8099 --directory web",
    url: "http://127.0.0.1:8099/index.html",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
