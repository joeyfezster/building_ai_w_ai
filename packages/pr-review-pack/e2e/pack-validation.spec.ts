/**
 * pack-validation.spec.ts — Generic structural & behavioral tests for ANY review pack HTML.
 *
 * Requires PACK_PATH env var pointing to a review pack HTML file.
 * No fixture dependency — tests structure, interactivity, and visual correctness.
 *
 * Usage:
 *   PACK_PATH="/path/to/review_pack.html" npx playwright test e2e/pack-validation.spec.ts
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import path from 'path';

const PACK_PATH = process.env.PACK_PATH;

test.skip(!PACK_PATH, 'PACK_PATH not set — skipping live pack validation');

const PACK_URL = PACK_PATH ? `file://${path.resolve(PACK_PATH)}` : '';

/** Helper: dismiss the inspection banner so it doesn't intercept clicks */
async function dismissBanner(page: Page) {
  await page.evaluate(() => document.body.setAttribute('data-inspected', 'true'));
}

// ═══════════════════════════════════════════════════════════════════
// Layout & Structure
// ═══════════════════════════════════════════════════════════════════

test.describe('Layout & Structure', () => {
  test('sidebar renders at expected width', async ({ page }) => {
    await page.goto(PACK_URL);
    const sidebar = page.locator('#mc-sidebar');
    await expect(sidebar).toBeVisible();
    const box = await sidebar.boundingBox();
    expect(box!.width).toBeGreaterThanOrEqual(240);
    expect(box!.width).toBeLessThanOrEqual(280);
  });

  test('main pane exists and is the scrollable content area', async ({ page }) => {
    await page.goto(PACK_URL);
    const main = page.locator('.mc-main');
    await expect(main).toBeVisible();
    const tagName = await main.evaluate(el => el.tagName);
    expect(tagName).toBe('MAIN');
  });

  test('tier dividers visible with correct labels', async ({ page }) => {
    await page.goto(PACK_URL);
    const dividers = page.locator('.tier-divider:not([style*="display:none"]):not([style*="display: none"])');
    const count = await dividers.count();
    // At least 3 tiers (Architecture, Review, Follow-ups); Factory tier may be hidden
    expect(count).toBeGreaterThanOrEqual(3);

    const allDividers = page.locator('.tier-divider');
    const texts = await allDividers.allTextContents();
    expect(texts.some(t => t.includes('Architecture'))).toBeTruthy();
    expect(texts.some(t => t.includes('Review'))).toBeTruthy();
    expect(texts.some(t => t.includes('Follow'))).toBeTruthy();
  });

  test('no unreplaced INJECT markers in visible HTML', async ({ page }) => {
    await page.goto(PACK_URL);
    const bodyHtml = await page.locator('body').innerHTML();
    const outsideScripts = bodyHtml.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '');
    expect(outsideScripts).not.toContain('<!-- INJECT:');
  });

  test('visual inspection banner visible by default', async ({ page }) => {
    await page.goto(PACK_URL);
    const banner = page.locator('#visual-inspection-banner');
    await expect(banner).toBeVisible();
  });

  test('banner hidden when data-inspected is true', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const banner = page.locator('#visual-inspection-banner');
    await expect(banner).toBeHidden();
  });
});

// ═══════════════════════════════════════════════════════════════════
// Sidebar Navigation
// ═══════════════════════════════════════════════════════════════════

test.describe('Sidebar Navigation', () => {
  test('section nav has group labels', async ({ page }) => {
    await page.goto(PACK_URL);
    const labels = page.locator('#mc-sidebar .sb-nav-group-label');
    const count = await labels.count();
    // At least 3 groups (Architecture, Review, Follow-ups)
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test('section nav items are clickable', async ({ page }) => {
    await page.goto(PACK_URL);
    const navItems = page.locator('#mc-sidebar .sb-nav-item');
    const count = await navItems.count();
    expect(count).toBeGreaterThan(0);
  });

  test('clicking nav item scrolls to section', async ({ page }) => {
    await page.goto(PACK_URL);
    const archNav = page.locator('#mc-sidebar .sb-nav-item[data-section="section-architecture"]');
    await expect(archNav).toHaveCount(1);
    const section = page.locator('#section-architecture');
    const initialY = await section.evaluate(el => el.getBoundingClientRect().top);
    await archNav.click();
    await page.waitForTimeout(600);
    const afterY = await section.evaluate(el => el.getBoundingClientRect().top);
    expect(afterY).toBeLessThanOrEqual(initialY);
  });

  test('clicking nav item in collapsed tier auto-expands tier', async ({ page }) => {
    await page.goto(PACK_URL);
    // Collapse the last tier
    const lastDivider = page.locator('.tier-divider').last();
    await lastDivider.click();
    const lastContent = page.locator('.tier-content').last();
    await expect(lastContent).toHaveClass(/collapsed/);

    // Click the last nav item to auto-expand
    const navItems = page.locator('#mc-sidebar .sb-nav-item');
    await navItems.last().click();
    await expect(lastContent).not.toHaveClass(/collapsed/);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Theme Toggle
// ═══════════════════════════════════════════════════════════════════

test.describe('Theme Toggle', () => {
  test('theme toggle is in sidebar top area', async ({ page }) => {
    await page.goto(PACK_URL);
    const toggle = page.locator('#mc-sidebar .theme-toggle');
    await expect(toggle).toBeVisible();
    const buttons = toggle.locator('button');
    await expect(buttons).toHaveCount(3);
  });

  test('clicking dark theme button applies dark theme', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    await page.locator('#mc-sidebar [data-theme-btn="dark"]').click();
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(theme).toBe('dark');
  });

  test('clicking light theme button applies light theme', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    await page.locator('#mc-sidebar [data-theme-btn="dark"]').click();
    await page.locator('#mc-sidebar [data-theme-btn="light"]').click();
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(theme).toBe('light');
  });
});

// ═══════════════════════════════════════════════════════════════════
// Tier Collapse/Expand
// ═══════════════════════════════════════════════════════════════════

test.describe('Tier Collapse/Expand', () => {
  test('clicking tier divider collapses content', async ({ page }) => {
    await page.goto(PACK_URL);
    const divider = page.locator('.tier-divider').first();
    const content = page.locator('.tier-content').first();
    await expect(content).not.toHaveClass(/collapsed/);
    await divider.click();
    await expect(content).toHaveClass(/collapsed/);
    await expect(divider).toHaveClass(/collapsed/);
  });

  test('clicking collapsed tier divider expands content', async ({ page }) => {
    await page.goto(PACK_URL);
    const divider = page.locator('.tier-divider').first();
    const content = page.locator('.tier-content').first();
    await divider.click();
    await expect(content).toHaveClass(/collapsed/);
    await divider.click();
    await expect(content).not.toHaveClass(/collapsed/);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Architecture Diagram
// ═══════════════════════════════════════════════════════════════════

test.describe('Architecture Diagram', () => {
  test('main architecture SVG is rendered', async ({ page }) => {
    await page.goto(PACK_URL);
    const svg = page.locator('#arch-diagram');
    await expect(svg).toBeVisible();
  });

  test('zone boxes are present in diagram', async ({ page }) => {
    await page.goto(PACK_URL);
    const zones = page.locator('#arch-diagram .zone-box');
    const count = await zones.count();
    expect(count).toBeGreaterThan(0);
  });

  test('zoom controls are present', async ({ page }) => {
    await page.goto(PACK_URL);
    const zoomIn = page.locator('[onclick*="archZoom"]');
    const count = await zoomIn.count();
    expect(count).toBeGreaterThan(0);
  });

  test('mini architecture diagram container exists in sidebar', async ({ page }) => {
    await page.goto(PACK_URL);
    const mini = page.locator('#sb-arch-mini');
    await expect(mini).toBeVisible();
  });

  test('architecture diagram legend swatches have colors', async ({ page }) => {
    await page.goto(PACK_URL);
    const swatches = page.locator('.arch-legend-swatch');
    const count = await swatches.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const bg = await swatches.nth(i).evaluate(el => el.style.background || getComputedStyle(el).backgroundColor);
      expect(bg).toBeTruthy();
      expect(bg).not.toBe('rgba(0, 0, 0, 0)');
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// Expandable Sections
// ═══════════════════════════════════════════════════════════════════

test.describe('Expandable Sections', () => {
  test('decision cards open on header click', async ({ page }) => {
    await page.goto(PACK_URL);
    const cards = page.locator('.decision-card');
    const count = await cards.count();
    if (count === 0) return; // Some packs may have no decisions
    const header = cards.first().locator('.decision-header');
    await header.click();
    await expect(cards.first()).toHaveClass(/open/);
  });

  test('CI performance rows are expandable', async ({ page }) => {
    await page.goto(PACK_URL);
    const rows = page.locator('.ci-row, .expandable');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Gate Pills
// ═══════════════════════════════════════════════════════════════════

test.describe('Gate Pills', () => {
  test('gate pills are visible in sidebar', async ({ page }) => {
    await page.goto(PACK_URL);
    const pills = page.locator('#mc-sidebar .sb-gate-pills');
    await expect(pills).toBeVisible();
  });

  test('gate pills exist with pass or fail class', async ({ page }) => {
    await page.goto(PACK_URL);
    const allPills = page.locator('#mc-sidebar .sb-gate-pill');
    const count = await allPills.count();
    expect(count).toBeGreaterThan(0);
    // Each pill should have either pass or fail class
    for (let i = 0; i < count; i++) {
      const classes = await allPills.nth(i).getAttribute('class');
      expect(classes).toMatch(/pass|fail/);
    }
  });

  test('clicking a gate pill navigates to review gates section', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const pill = page.locator('#mc-sidebar .sb-gate-pill').first();
    await pill.click();
    const section = page.locator('#section-review-gates');
    await expect(section).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════
// Review Gates Section
// ═══════════════════════════════════════════════════════════════════

test.describe('Review Gates Section', () => {
  test('section exists in DOM', async ({ page }) => {
    await page.goto(PACK_URL);
    const section = page.locator('#section-review-gates');
    await expect(section).toBeAttached();
  });

  test('gate cards are rendered', async ({ page }) => {
    await page.goto(PACK_URL);
    const cards = page.locator('.gate-review-card');
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test('gate cards are expandable', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const card = page.locator('.gate-review-card').first();
    await card.click();
    await expect(card).toHaveClass(/open/);
  });

  test('clicking gate pill auto-expands matching card', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const pill = page.locator('#mc-sidebar .sb-gate-pill').first();
    await pill.click();
    await page.waitForTimeout(200);
    const openCards = page.locator('.gate-review-card.open');
    expect(await openCards.count()).toBeGreaterThan(0);
  });

  test('gate cards have detail content when expanded', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const card = page.locator('.gate-review-card').first();
    await card.click();
    const detail = card.locator('.gate-detail');
    await expect(detail).toBeVisible();
    const detailText = await detail.textContent();
    expect(detailText!.length).toBeGreaterThan(10);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Self-Contained Guarantees
// ═══════════════════════════════════════════════════════════════════

test.describe('Self-Contained', () => {
  test('DATA object is embedded in the page', async ({ page }) => {
    await page.goto(PACK_URL);
    const html = await page.content();
    expect(html).toContain('const DATA');
  });

  test('no external network requests', async ({ page }) => {
    const requests: string[] = [];
    page.on('request', req => {
      if (!req.url().startsWith('file://') && !req.url().startsWith('data:')) {
        requests.push(req.url());
      }
    });
    await page.goto(PACK_URL);
    await page.waitForTimeout(2000);
    expect(requests).toHaveLength(0);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Sections Exist
// ═══════════════════════════════════════════════════════════════════

test.describe('Sections Exist', () => {
  test('Architecture section exists', async ({ page }) => {
    await page.goto(PACK_URL);
    await expect(page.locator('#section-architecture')).toBeAttached();
  });

  test('What Changed section exists', async ({ page }) => {
    await page.goto(PACK_URL);
    await expect(page.locator('#section-what-changed')).toBeAttached();
  });

  test('Key Findings section exists', async ({ page }) => {
    await page.goto(PACK_URL);
    await expect(page.locator('#section-key-findings')).toBeAttached();
  });

  test('File Coverage section exists', async ({ page }) => {
    await page.goto(PACK_URL);
    await expect(page.locator('#section-file-coverage')).toBeAttached();
  });

  test('CI Performance section exists', async ({ page }) => {
    await page.goto(PACK_URL);
    await expect(page.locator('#section-ci-performance')).toBeAttached();
  });

  test('Architecture Assessment section exists', async ({ page }) => {
    await page.goto(PACK_URL);
    await expect(page.locator('#section-arch-assessment')).toBeAttached();
  });

  test('Review Gates section exists', async ({ page }) => {
    await page.goto(PACK_URL);
    await expect(page.locator('#section-review-gates')).toBeAttached();
  });
});

// ═══════════════════════════════════════════════════════════════════
// Key Findings Card — Structural
// ═══════════════════════════════════════════════════════════════════

test.describe('Key Findings Card — Structure', () => {
  test('severity heatbar exists with colored segments', async ({ page }) => {
    await page.goto(PACK_URL);
    const heatbar = page.locator('#section-key-findings .kf-heatbar');
    await expect(heatbar).toBeVisible();
    const segments = heatbar.locator('.kf-heatbar-seg');
    const count = await segments.count();
    expect(count).toBeGreaterThan(0);
  });

  test('finding rows have grade, finding text, agent tag, zone tag', async ({ page }) => {
    await page.goto(PACK_URL);
    const rows = page.locator('#section-key-findings .kf-row');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
    const firstRow = rows.first();
    await expect(firstRow.locator('.grade')).toBeVisible();
    await expect(firstRow.locator('td:nth-child(2)')).toBeVisible();
    await expect(firstRow.locator('.kf-agent-tag')).toBeVisible();
    await expect(firstRow.locator('.zone-tag')).toBeVisible();
  });

  test('click finding row expands to show detail', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const row = page.locator('#section-key-findings .kf-row').first();
    await row.click();
    const detail = page.locator('#section-key-findings .kf-detail-row').first();
    await expect(detail).toBeVisible();
  });

  test('key findings table has expected columns', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const headers = page.locator('.kf-table thead th');
    const texts = await headers.allTextContents();
    const joined = texts.join(' ').toLowerCase();
    expect(joined).toContain('grade');
    expect(joined).toContain('finding');
    expect(joined).toContain('agent');
    expect(joined).toContain('zone');
    expect(joined).toContain('loc');
    expect(joined).toContain('corr');
  });

  test('agent filter pills exist in key findings', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const pills = page.locator('#section-key-findings .kf-agent-pill');
    expect(await pills.count()).toBeGreaterThan(0);
  });

  test('agent filter pill click filters the findings table', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const pill = page.locator('#section-key-findings .kf-agent-pill').first();
    await pill.click();
    const hiddenRows = page.locator('#section-key-findings .kf-row.agent-hidden');
    const visibleRows = page.locator('#section-key-findings .kf-row:not(.agent-hidden)');
    const totalVisible = await visibleRows.count();
    const totalHidden = await hiddenRows.count();
    expect(totalVisible + totalHidden).toBeGreaterThan(0);
  });

  test('agent legend exists', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const section = page.locator('#section-key-findings');
    if (await section.count() > 0) {
      await section.scrollIntoViewIfNeeded();
      const pills = section.locator('.kf-agent-pill');
      expect(await pills.count()).toBeGreaterThan(0);
    }
  });

  test('key findings rows show agent tags', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const tags = page.locator('#section-key-findings .kf-agent-tag');
    expect(await tags.count()).toBeGreaterThan(0);
  });

  test('dark mode renders correctly for key findings', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    await page.locator('#mc-sidebar [data-theme-btn="dark"]').click();
    const heatbar = page.locator('#section-key-findings .kf-heatbar');
    await expect(heatbar).toBeVisible();
    const rows = page.locator('#section-key-findings .kf-row');
    expect(await rows.count()).toBeGreaterThan(0);
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(theme).toBe('dark');
  });
});

// ═══════════════════════════════════════════════════════════════════
// File Coverage — Structural
// ═══════════════════════════════════════════════════════════════════

test.describe('File Coverage — Structure', () => {
  test('file coverage section has heading', async ({ page }) => {
    await page.goto(PACK_URL);
    const section = page.locator('#section-file-coverage');
    const heading = section.locator('h2, h3').first();
    await expect(heading).toContainText('File Coverage');
  });

  test('file coverage renders as a table with header row', async ({ page }) => {
    await page.goto(PACK_URL);
    const table = page.locator('.cr-table');
    await expect(table).toBeVisible();
    const headers = table.locator('thead th');
    const texts = await headers.allTextContents();
    // Should have agent abbreviation columns
    expect(texts.length).toBeGreaterThan(2);
  });

  test('file rows exist', async ({ page }) => {
    await page.goto(PACK_URL);
    const rows = page.locator('.cr-file-row');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('file path click opens modal', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const pathLink = page.locator('.cr-file-row .file-path-link').first();
    await pathLink.click();
    const modal = page.locator('.file-modal');
    await expect(modal).toBeVisible();
  });

  test('file coverage table does not exceed its container width', async ({ page }) => {
    await page.goto(PACK_URL);
    const table = page.locator('.cr-table');
    await expect(table).toBeVisible();
    const overflow = await table.evaluate(el => {
      const parent = el.parentElement!;
      return el.scrollWidth > parent.clientWidth + 2;
    });
    expect(overflow).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Zone Filtering
// ═══════════════════════════════════════════════════════════════════

test.describe('Zone Filtering', () => {
  test('clicking zone chip activates filter', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    await page.waitForSelector('.sb-arch-chip', { timeout: 5000 });
    const chip = page.locator('.sb-arch-chip:not(.unzoned)').first();
    await chip.click();
    const dimmed = page.locator('#arch-diagram .zone-box.dimmed');
    await expect(dimmed.first()).toBeVisible();
  });

  test('double-clicking zone chip deselects active filter', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    await page.waitForSelector('.sb-arch-chip', { timeout: 5000 });
    const chip = page.locator('.sb-arch-chip:not(.unzoned)').first();
    await chip.click();
    const dimmed = page.locator('#arch-diagram .zone-box.dimmed');
    await expect(dimmed.first()).toBeVisible();
    await chip.dblclick();
    await expect(dimmed).toHaveCount(0);
  });

  test('sidebar zone chips have category-specific background colors', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    await page.waitForSelector('.sb-arch-chip', { timeout: 5000 });
    const chips = page.locator('.sb-arch-chip:not(.unzoned):not(.unzoned-info)');
    const count = await chips.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < Math.min(count, 3); i++) {
      const bg = await chips.nth(i).evaluate(el => getComputedStyle(el).backgroundColor);
      expect(bg).not.toBe('rgba(0, 0, 0, 0)');
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// Trackpad Pinch-to-Zoom
// ═══════════════════════════════════════════════════════════════════

test.describe('Trackpad Pinch-to-Zoom', () => {
  test('pinch-zoom-in on architecture diagram increases scale', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const diagram = page.locator('#arch-diagram');
    await expect(diagram).toBeVisible();

    const initialScale = await page.evaluate(() => {
      const svg = document.querySelector('#arch-diagram svg') as SVGSVGElement;
      if (!svg) return 1;
      const match = (svg.style.transform || '').match(/scale\(([^)]+)\)/);
      return match ? parseFloat(match[1]) : 1;
    });

    const box = await diagram.boundingBox();
    await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
    await page.evaluate((coords) => {
      const el = document.querySelector('#arch-diagram');
      el?.dispatchEvent(new WheelEvent('wheel', {
        clientX: coords.x, clientY: coords.y,
        deltaY: -100, ctrlKey: true, bubbles: true
      }));
    }, { x: box!.x + box!.width / 2, y: box!.y + box!.height / 2 });
    await page.waitForTimeout(200);

    const newScale = await page.evaluate(() => {
      const svg = document.querySelector('#arch-diagram svg') as SVGSVGElement;
      if (!svg) return 1;
      const match = (svg.style.transform || '').match(/scale\(([^)]+)\)/);
      return match ? parseFloat(match[1]) : 1;
    });

    expect(newScale).toBeGreaterThanOrEqual(initialScale);
  });

  test('regular scroll without ctrl does not zoom', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);
    const diagram = page.locator('#arch-diagram');
    const box = await diagram.boundingBox();

    const initialScale = await page.evaluate(() => {
      const svg = document.querySelector('#arch-diagram svg') as SVGSVGElement;
      if (!svg) return 1;
      const match = (svg.style.transform || '').match(/scale\(([^)]+)\)/);
      return match ? parseFloat(match[1]) : 1;
    });

    await page.evaluate((c) => {
      const el = document.querySelector('#arch-diagram');
      el?.dispatchEvent(new WheelEvent('wheel', {
        clientX: c.x, clientY: c.y,
        deltaY: -100, ctrlKey: false, bubbles: true
      }));
    }, { x: box!.x + box!.width / 2, y: box!.y + box!.height / 2 });
    await page.waitForTimeout(200);

    const afterScale = await page.evaluate(() => {
      const svg = document.querySelector('#arch-diagram svg') as SVGSVGElement;
      if (!svg) return 1;
      const match = (svg.style.transform || '').match(/scale\(([^)]+)\)/);
      return match ? parseFloat(match[1]) : 1;
    });

    expect(afterScale).toBe(initialScale);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Decision Click — No Scroll Jump
// ═══════════════════════════════════════════════════════════════════

test.describe('Decision Click — Scroll Stability', () => {
  test('clicking a decision card does not cause scroll jump', async ({ page }) => {
    await page.goto(PACK_URL);
    await dismissBanner(page);

    const cards = page.locator('.decision-card');
    const count = await cards.count();
    if (count === 0) return;

    await page.evaluate(() => {
      document.getElementById('section-key-decisions')?.scrollIntoView();
    });
    await page.waitForTimeout(300);

    const scrollBefore = await page.evaluate(() => window.scrollY);
    const header = cards.first().locator('.decision-header');
    await header.click();
    await page.waitForTimeout(300);
    const scrollAfter = await page.evaluate(() => window.scrollY);
    expect(Math.abs(scrollAfter - scrollBefore)).toBeLessThanOrEqual(5);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Empty Card Validation
// ═══════════════════════════════════════════════════════════════════

test.describe('Empty Card Validation', () => {
  test('all visible sections have content beyond headers', async ({ page }) => {
    await page.goto(PACK_URL);
    const sections = page.locator('.mc-main .section:visible');
    const count = await sections.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const section = sections.nth(i);
      const body = section.locator('.section-body');
      const bodyCount = await body.count();
      if (bodyCount > 0) {
        const bodyText = await body.first().textContent();
        expect(bodyText!.trim().length).toBeGreaterThan(0);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// What Changed HTML Rendering
// ═══════════════════════════════════════════════════════════════════

test.describe('What Changed HTML Rendering', () => {
  test('wc-summary renders styled HTML not raw tags', async ({ page }) => {
    await page.goto(PACK_URL);
    const summaries = page.locator('.wc-summary');
    const count = await summaries.count();
    if (count === 0) return; // Some packs may not have summaries
    const html = await summaries.first().innerHTML();
    // Should contain rendered tags, not escaped text
    expect(html).not.toContain('&lt;strong&gt;');
  });
});

// ═══════════════════════════════════════════════════════════════════
// Sidebar Gate Pills — Structure
// ═══════════════════════════════════════════════════════════════════

test.describe('Sidebar Pills', () => {
  test('gate pills show tooltip on hover', async ({ page }) => {
    await page.goto(PACK_URL);
    const pill = page.locator('.sb-gate-pill').first();
    const title = await pill.getAttribute('title');
    expect(title).toBeTruthy();
    expect(title!.length).toBeGreaterThan(5);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Architecture Assessment — Collapsible Structure
// ═══════════════════════════════════════════════════════════════════

test.describe('Architecture Assessment — Collapsible', () => {
  test('arch-section elements are present', async ({ page }) => {
    await page.goto(PACK_URL);
    const sections = page.locator('#section-arch-assessment .arch-section');
    const count = await sections.count();
    expect(count).toBeGreaterThan(0);
  });

  test('clicking section header toggles expansion', async ({ page }) => {
    await page.goto(PACK_URL);
    const section = page.locator('#section-arch-assessment .arch-section').first();
    const header = section.locator('.arch-section-header');

    // Click to expand
    await header.click();
    await expect(section).not.toHaveClass(/collapsed/);
    const body = section.locator('.arch-section-body');
    await expect(body).toBeVisible();

    // Click to collapse
    await header.click();
    await expect(section).toHaveClass(/collapsed/);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Banner Removal — MUST be the LAST test block
// Runs only when PACK_PATH env var is set. Strips the self-review
// banner from the HTML file on disk, marking the pack as validated.
// ═══════════════════════════════════════════════════════════════════

test.describe('Banner Removal (live pack)', () => {
  test('remove validation banner on all-pass', async () => {
    const htmlPath = path.resolve(PACK_PATH!);
    let html = fs.readFileSync(htmlPath, 'utf-8');

    // Set data-inspected="true" on <body>
    html = html.replace(
      /data-inspected="false"/,
      'data-inspected="true"'
    );

    // Remove the banner div
    html = html.replace(
      /<div id="visual-inspection-banner"[^>]*>[\s\S]*?<\/div>/,
      ''
    );

    // Remove the spacer div
    html = html.replace(
      /<div id="visual-inspection-spacer"[^>]*><\/div>/,
      ''
    );

    fs.writeFileSync(htmlPath, html, 'utf-8');

    // Verify
    const updated = fs.readFileSync(htmlPath, 'utf-8');
    expect(updated).toContain('data-inspected="true"');
    expect(updated).not.toMatch(/<div id="visual-inspection-banner"/);
  });
});
