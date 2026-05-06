import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    {
      // Renderer regression suite. Runs against pre-built fixture HTML at
      // /tmp/pr26_review_pack_v2_<variant>.html for variants ready/gap/
      // blocked/nofactory. The path contract is owned by
      // scripts/dev/generate_fixtures.py; the spec hard-codes the same
      // paths via READY_PACK / GAP_PACK / BLOCKED_PACK / NOFACTORY_PACK.
      // Used by skill-internal CI; never selected by `/pr-review-pack`.
      name: 'renderer-fixtures',
      testMatch: /e2e\/renderer-fixtures\.spec\.ts/,
      use: { browserName: 'chromium' },
    },
    {
      // Live-pack validation suite. Runs against a real review-pack HTML
      // file passed via PACK_PATH env var. Selected by `/pr-review-pack`
      // Phase 4 Step 2.
      name: 'live-pack-validation',
      testMatch: /e2e\/live-pack-validation\.spec\.ts/,
      use: { browserName: 'chromium' },
    },
  ],
});
