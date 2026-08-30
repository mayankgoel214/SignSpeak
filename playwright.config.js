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
    baseURL: process.env.BASE_URL || "http://127.0.0.1:8099",
  },
  // The page is plain modules, plain CSS and a WebAssembly hand tracker, none of
  // which is Chromium-specific -- so it is worth proving rather than assuming.
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        permissions: ["camera"],
        launchOptions: {
          // HOST_RESOLVER lets the suite run against the deployed site from a
          // network whose DNS blocks *.vercel.app, without touching /etc/hosts.
          args: [
            "--use-fake-ui-for-media-stream",
            ...(process.env.HOST_RESOLVER ? [`--host-resolver-rules=${process.env.HOST_RESOLVER}`] : []),
          ],
        },
      },
    },
    {
      // Firefox has no "camera" permission in Playwright, so it is granted by a
      // preference instead. The camera itself is stubbed inside the page in any
      // case; what matters here is that the modules, the CSS and the WebAssembly
      // tracker work outside Chromium.
      name: "firefox",
      use: {
        ...devices["Desktop Firefox"],
        launchOptions: {
          firefoxUserPrefs: {
            "media.navigator.streams.fake": true,
            "media.navigator.permission.disabled": true,
          },
        },
      },
    },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
  // No local server needed when the suite is pointed at a deployment.
  webServer: process.env.BASE_URL
    ? undefined
    : {
        // Not a plain static server: this one sends the production security
        // headers, so the content security policy is enforced in every local and
        // CI run instead of only on the deployed site.
        command: "node scripts/serve.mjs 8099",
        url: "http://127.0.0.1:8099/index.html",
        reuseExistingServer: !process.env.CI,
        timeout: 30_000,
      },
});
