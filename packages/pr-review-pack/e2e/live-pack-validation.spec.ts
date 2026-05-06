// live-pack-validation.spec.ts
// ===========================================================================
// LIVE PACK VALIDATION SUITE
//
// This spec validates a real, freshly-generated review pack HTML file passed
// via the PACK_PATH environment variable. It is selected by the `pr-review-pack`
// skill in Phase 4 Step 2 via `--project=live-pack-validation`.
//
//
// STRUCTURAL RULE (DO NOT VIOLATE)
// --------------------------------
// The banner-strip test is the TERMINAL test in this file. It must be the
// last test of the last describe in this file, and it must only fire when
// every preceding live-pack assertion has passed in the same Playwright run.
//
// Mechanism (the FIRST line is what the code enforces; the rest is convention
// that depends on serial mode):
//   1. `test.describe.configure({ mode: 'serial' })` — when a test fails,
//      Playwright skips every subsequent test in the describe. The terminal
//      banner-strip test is therefore unreachable after any prior failure.
//      This is the ONLY guarantee the code makes.
//   2. Module-level `liveValidationFailed` flag, set to `true` by an
//      `afterEach` hook on every non-`passed` status (failed, timedOut,
//      interrupted, AND skipped). With serial mode dropped, an upstream
//      failure leaves later siblings as `skipped` — observing that status
//      sets the flag, so the terminal test will still refuse to strip the
//      banner. Without this `skipped` capture, dropping serial mode would
//      silently break the causal chain.
//   3. `SERIAL_MODE_REQUIRED` sentinel: a TypeScript-level constant whose
//      sole purpose is to be visible at the same edit site as the
//      `test.describe.configure({ mode: 'serial' })` call, so that any
//      future refactor changing the mode is forced to also touch the
//      sentinel and read the comment block above it.
//
// Do not refactor the structure (split into multiple files, change to
// non-serial mode, remove the flag) without preserving the causal chain:
// banner removal MUST NOT happen if any prior live-pack assertion failed.
//
//
// DIAGNOSTIC FAILURE FORMAT
// -------------------------
// Every assertion failure throws a single-line, parseable diagnostic:
//
//   LIVE_PACK_FAIL {"code":"<code>","details":{...}}
//
// Codes are registered in `references/live-pack-failure-codes.md`. The
// orchestrator scrapes Playwright stderr for these lines, dispatches the
// matching reviewer/agent for correction, and re-runs validation.
//
// Add a code? Add a row to the failure-codes registry in the same commit.
// CI greps the spec for `LIVE_PACK_FAIL "..."` codes and rejects mismatches.
// ===========================================================================

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const LIVE_PACK_PATH = process.env.PACK_PATH;

if (!LIVE_PACK_PATH) {
  test.describe('live-pack-validation', () => {
    test('PACK_PATH environment variable is required', () => {
      throw new Error(
        'PACK_PATH environment variable is required to run the ' +
          'live-pack-validation project. Set PACK_PATH to the absolute path ' +
          'of a rendered review pack HTML file.'
      );
    });
  });
} else {
  const PACK_ABS_PATH = path.resolve(LIVE_PACK_PATH);
  const PACK_URL = `file://${PACK_ABS_PATH}`;

  // -------------------------------------------------------------------------
  // Module-level state
  // -------------------------------------------------------------------------

  let liveValidationFailed = false;

  type DiagDetails = Record<string, unknown>;

  /** Build the structured failure line. */
  function diagnostic(code: string, details: DiagDetails): string {
    return `LIVE_PACK_FAIL ${JSON.stringify({ code, details })}`;
  }

  /** Throw a structured failure that the orchestrator can scrape. */
  function liveFail(code: string, details: DiagDetails): never {
    throw new Error(diagnostic(code, details));
  }

  // -------------------------------------------------------------------------
  // Source-of-truth helpers
  // -------------------------------------------------------------------------

  /**
   * Find the index AFTER the matching closing `}` for the `{` at start.
   * Tracks JS string literals so braces inside strings don't confuse the
   * counter.
   */
  function findObjectEnd(html: string, start: number): number {
    if (html[start] !== '{') {
      throw new Error(`expected '{' at index ${start}`);
    }
    let depth = 0;
    let i = start;
    let inStr: string | null = null;
    while (i < html.length) {
      const ch = html[i];
      if (inStr !== null) {
        if (ch === '\\') {
          i += 2;
          continue;
        }
        if (ch === inStr) inStr = null;
        i += 1;
        continue;
      }
      if (ch === '"' || ch === "'") {
        inStr = ch;
        i += 1;
        continue;
      }
      if (ch === '{') depth += 1;
      else if (ch === '}') {
        depth -= 1;
        if (depth === 0) return i + 1;
      }
      i += 1;
    }
    throw new Error('unbalanced braces');
  }

  /**
   * Extract the embedded `const DATA = {...};` JSON object from the on-disk
   * HTML file. We read the file directly rather than going through
   * `window.DATA` because `const` is script-scoped and never attached to
   * `window` — `page.evaluate(() => window.DATA)` always returns undefined.
   *
   * The renderer's `rfind` logic puts the data block at the LAST occurrence
   * of `const DATA = `, so we mirror that here.
   */
  function readPackData(): any {
    const html = fs.readFileSync(PACK_ABS_PATH, 'utf-8');
    const prefix = 'const DATA = ';
    const idx = html.lastIndexOf(prefix);
    if (idx < 0) {
      throw new Error(
        `could not find "${prefix}" in pack HTML at ${PACK_ABS_PATH}`
      );
    }
    const objStart = idx + prefix.length;
    if (html[objStart] !== '{') {
      throw new Error(`expected "{" after "${prefix}"`);
    }
    const objEnd = findObjectEnd(html, objStart);
    return JSON.parse(html.slice(objStart, objEnd));
  }

  /**
   * Extract DIFF_DATA_INLINE from the on-disk HTML file. The renderer
   * inserts this block BEFORE the main script (and BEFORE the rendered
   * source-code listings that contain the literal string), so we use
   * `indexOf` and skip occurrences that are not followed by `{`.
   *
   * Returns null if no parseable DIFF_DATA_INLINE block is found. Callers
   * are responsible for emitting the `diff-data-missing` diagnostic.
   */
  function readDiffData(): any | null {
    const html = fs.readFileSync(PACK_ABS_PATH, 'utf-8');
    const prefix = 'const DIFF_DATA_INLINE = ';
    let from = 0;
    while (true) {
      const idx = html.indexOf(prefix, from);
      if (idx < 0) return null;
      const objStart = idx + prefix.length;
      if (html[objStart] === '{') {
        try {
          const objEnd = findObjectEnd(html, objStart);
          return JSON.parse(html.slice(objStart, objEnd));
        } catch {
          // Brace parse failed — keep looking for the next occurrence.
          from = idx + prefix.length;
          continue;
        }
      }
      from = idx + prefix.length;
    }
  }

  /**
   * Normalize a finding-location path. Handles git compact rename notation
   * `dir/{old.py => new.py}` by resolving to the new (post-rename) path,
   * which is what diff_data.files keys look like.
   *
   * Also strips trailing whitespace and leading "./".
   */
  function normalizePath(p: string): string {
    if (!p) return p;
    let out = p.trim();
    if (out.startsWith('./')) out = out.slice(2);
    // git compact rename notation: "src/{old.py => new.py}" -> "src/new.py"
    const renameMatch = out.match(/^(.*)\{[^{}]*=>\s*([^{}]+)\}(.*)$/);
    if (renameMatch) {
      const prefix = renameMatch[1];
      const newName = renameMatch[2].trim();
      const suffix = renameMatch[3] ?? '';
      out = `${prefix}${newName}${suffix}`;
      out = out.replace(/\/\//g, '/');
    }
    return out;
  }

  /** Levenshtein distance — used to suggest closest-match diff file paths. */
  function levenshtein(a: string, b: string): number {
    if (a === b) return 0;
    if (a.length === 0) return b.length;
    if (b.length === 0) return a.length;
    const dp: number[][] = Array.from({ length: a.length + 1 }, () =>
      new Array(b.length + 1).fill(0)
    );
    for (let i = 0; i <= a.length; i++) dp[i][0] = i;
    for (let j = 0; j <= b.length; j++) dp[0][j] = j;
    for (let i = 1; i <= a.length; i++) {
      for (let j = 1; j <= b.length; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        dp[i][j] = Math.min(
          dp[i - 1][j] + 1,
          dp[i][j - 1] + 1,
          dp[i - 1][j - 1] + cost
        );
      }
    }
    return dp[a.length][b.length];
  }

  function closestPath(target: string, candidates: string[]): string | null {
    if (candidates.length === 0) return null;
    let best = candidates[0];
    let bestDist = levenshtein(target, best);
    for (const c of candidates) {
      const d = levenshtein(target, c);
      if (d < bestDist) {
        bestDist = d;
        best = c;
      }
    }
    return best;
  }

  /**
   * Locate the source .jsonl files for this pack. The pack lives at
   *   docs/pr{N}_review_pack_{...}.html
   * and the .jsonl reviews live at
   *   docs/reviews/pr{N}/pr{N}-{agent}-{...}.jsonl
   *
   * Returns parsed lines per agent. Synthesis and architecture-assessment
   * lines are exposed on the meta object.
   */
  function loadSourceJsonl(packPath: string): {
    pr: number | null;
    agentLines: Record<string, any[]>;
    architectureAssessmentLine: any | null;
    repoRoot: string | null;
  } {
    const filename = path.basename(packPath);
    const m = filename.match(/^pr(\d+)_review_pack_/);
    if (!m) {
      return {
        pr: null,
        agentLines: {},
        architectureAssessmentLine: null,
        repoRoot: null,
      };
    }
    const pr = parseInt(m[1], 10);

    // Walk up from the pack file looking for `docs/reviews/pr{N}/`.
    let dir: string | null = path.dirname(packPath);
    let reviewsDir: string | null = null;
    let repoRoot: string | null = null;
    while (dir && dir !== path.dirname(dir)) {
      const candidate = path.join(dir, 'docs', 'reviews', `pr${pr}`);
      if (fs.existsSync(candidate)) {
        reviewsDir = candidate;
        repoRoot = dir;
        break;
      }
      // Also try the same directory level (when packPath is already inside docs/)
      const sibling = path.join(dir, 'reviews', `pr${pr}`);
      if (fs.existsSync(sibling)) {
        reviewsDir = sibling;
        repoRoot = path.dirname(path.dirname(dir));
        break;
      }
      dir = path.dirname(dir);
    }

    const agentLines: Record<string, any[]> = {};
    let architectureAssessmentLine: any | null = null;

    if (!reviewsDir) {
      return { pr, agentLines, architectureAssessmentLine, repoRoot };
    }

    const entries = fs.readdirSync(reviewsDir);
    for (const entry of entries) {
      if (!entry.endsWith('.jsonl')) continue;
      const fullPath = path.join(reviewsDir, entry);
      const m2 = entry.match(/^pr\d+-([a-z-]+)-[0-9a-f]+-[0-9a-f]+\.jsonl$/);
      if (!m2) continue;
      const agent = m2[1];
      const lines: any[] = [];
      const text = fs.readFileSync(fullPath, 'utf-8');
      for (const raw of text.split('\n')) {
        const line = raw.trim();
        if (!line) continue;
        try {
          const parsed = JSON.parse(line);
          if (
            agent === 'architecture' &&
            parsed?._type === 'architecture_assessment'
          ) {
            architectureAssessmentLine = parsed;
          }
          lines.push(parsed);
        } catch {
          // Malformed JSON in source — flag as part of architecture-assessment-schema
          // or as an indirect signal via missing concept backings; skip here.
        }
      }
      agentLines[agent] = lines;
    }

    return { pr, agentLines, architectureAssessmentLine, repoRoot };
  }


  // -------------------------------------------------------------------------
  // Module-level data caches (lazily populated)
  // -------------------------------------------------------------------------

  let cachedPackData: any | null = null;
  let cachedDiffData: any | null = null;
  let cachedJsonl: ReturnType<typeof loadSourceJsonl> | null = null;

  function ensurePackData(): any {
    if (cachedPackData === null) {
      cachedPackData = readPackData();
    }
    return cachedPackData;
  }

  function ensureDiffData(): any {
    if (cachedDiffData === null) {
      const parsed = readDiffData();
      if (parsed === null) {
        liveFail('diff-data-missing', {
          packPath: PACK_ABS_PATH,
          reason:
            'no parseable `const DIFF_DATA_INLINE = {...};` block in pack HTML',
        });
      }
      cachedDiffData = parsed;
    }
    return cachedDiffData;
  }

  function ensureJsonl(): ReturnType<typeof loadSourceJsonl> {
    if (cachedJsonl === null) {
      cachedJsonl = loadSourceJsonl(PACK_ABS_PATH);
    }
    return cachedJsonl;
  }

  // -------------------------------------------------------------------------
  // Test suite — serial mode is non-negotiable (banner-strip is terminal).
  //
  // SERIAL_MODE_REQUIRED is a sentinel. It exists so that a contributor who
  // edits the configure() call below cannot avoid noticing it — the
  // adjacent comment block in the file header explains why dropping
  // serial mode breaks the banner-strip causal chain. If you change the
  // mode here, you must also re-read the file-header comment and update
  // the sentinel + flag accordingly. The constant is intentionally
  // unused at runtime; its only job is to be load-bearing prose pinned
  // to the same edit site.
  // -------------------------------------------------------------------------

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const SERIAL_MODE_REQUIRED = true;
  test.describe.configure({ mode: 'serial' });

  test.describe('Live Pack Validation', () => {
    // Capture every non-pass status (failed, timedOut, interrupted, skipped).
    // Capturing 'skipped' is what keeps the banner-strip safety net alive if
    // a future refactor drops serial mode: with serial dropped, prior
    // failures show up as `skipped` siblings here, the flag flips, and the
    // terminal test refuses. With serial in place (current behavior),
    // capturing 'skipped' is a no-op because the terminal test is itself
    // skipped before its afterEach can run.
    test.afterEach(({}, testInfo) => {
      if (testInfo.status !== 'passed') {
        liveValidationFailed = true;
      }
    });

    // ─── Content correctness ────────────────────────────────────────────

    test('every diff file has exactly one row in file-coverage', async ({
      page,
    }) => {
      await page.goto(PACK_URL);
      const data = ensurePackData();
      const diff = ensureDiffData();

      const diffFiles = new Set<string>(Object.keys(diff?.files ?? {}));

      const fileCoverage = data?.fileCoverage?.files ?? [];
      const coveredPaths = new Map<string, number>();
      for (const fc of fileCoverage) {
        const p = normalizePath(String(fc.file ?? ''));
        coveredPaths.set(p, (coveredPaths.get(p) ?? 0) + 1);
      }

      // Every diff file must be present.
      const missing: string[] = [];
      for (const f of diffFiles) {
        if (!coveredPaths.has(f)) missing.push(f);
      }

      // Every covered path must be present in the diff (no extras).
      const extras: string[] = [];
      for (const p of coveredPaths.keys()) {
        if (!diffFiles.has(p)) extras.push(p);
      }

      // No duplicate rows for the same file.
      const duplicates: string[] = [];
      for (const [p, n] of coveredPaths.entries()) {
        if (n > 1) duplicates.push(p);
      }

      if (missing.length > 0 || extras.length > 0 || duplicates.length > 0) {
        liveFail('file-coverage-gap', {
          missing,
          extras,
          duplicates,
          diffFileCount: diffFiles.size,
          coverageRowCount: fileCoverage.length,
        });
      }
    });

    test('every finding location resolves to a real diff file', async ({
      page,
    }) => {
      await page.goto(PACK_URL);
      const data = ensurePackData();
      const diff = ensureDiffData();

      const diffFiles = Object.keys(diff?.files ?? {}).map((p) =>
        normalizePath(p)
      );
      const diffFileSet = new Set(diffFiles);

      const findings = data?.agenticReview?.findings ?? [];
      const mismatches: Array<Record<string, unknown>> = [];

      for (const f of findings) {
        const locations = Array.isArray(f.locations) ? f.locations : [];
        // Backwards-compat: older packs may only have `file`.
        if (locations.length === 0 && f.file) {
          // Skip glob notation rows ("(N files)") — separate test catches them.
          if (/\(\d+ files?\)/.test(String(f.file))) continue;
          const norm = normalizePath(String(f.file));
          if (!diffFileSet.has(norm)) {
            mismatches.push({
              file: f.file,
              normalized: norm,
              agent: f.agent,
              suggestion: closestPath(norm, diffFiles),
            });
          }
          continue;
        }
        for (const loc of locations) {
          const orig = String(loc?.file ?? '');
          if (!orig) continue;
          const norm = normalizePath(orig);
          if (!diffFileSet.has(norm)) {
            mismatches.push({
              file: orig,
              normalized: norm,
              agent: f.agent,
              suggestion: closestPath(norm, diffFiles),
            });
          }
        }
      }

      if (mismatches.length > 0) {
        liveFail('finding-location-mismatch', {
          count: mismatches.length,
          examples: mismatches.slice(0, 10),
        });
      }
    });

    test('every finding zone resolves in the zone registry', async ({
      page,
    }) => {
      await page.goto(PACK_URL);
      const data = ensurePackData();

      const registryZones = new Set<string>(
        (data?.architecture?.zones ?? []).map((z: any) => String(z.id))
      );
      const findings = data?.agenticReview?.findings ?? [];

      const unresolved: Array<Record<string, unknown>> = [];
      for (const f of findings) {
        const zonesField = f.zones;
        const zoneList: string[] = Array.isArray(zonesField)
          ? zonesField.map(String)
          : String(zonesField ?? '')
              .split(/\s+/)
              .filter(Boolean);
        for (const z of zoneList) {
          if (!registryZones.has(z)) {
            unresolved.push({
              zone: z,
              agent: f.agent,
              file: f.file,
            });
          }
        }
      }

      if (unresolved.length > 0) {
        liveFail('finding-zone-unresolved', {
          count: unresolved.length,
          examples: unresolved.slice(0, 10),
          knownZones: Array.from(registryZones),
        });
      }
    });

    test('every file-coverage grade has a backing FileReviewOutcome', async ({
      page,
    }) => {
      await page.goto(PACK_URL);
      const data = ensurePackData();
      const { agentLines, pr } = ensureJsonl();

      if (Object.keys(agentLines).length === 0) {
        // No source .jsonl found — we can't validate. Surface this as a
        // file-coverage-gap with structured details rather than silently passing.
        liveFail('file-coverage-gap', {
          reason: 'source jsonl directory not found',
          pr,
          packPath: PACK_ABS_PATH,
        });
      }

      // Build {agent → set of files with FileReviewOutcome}
      const fileOutcomes: Record<string, Set<string>> = {};
      for (const [agent, lines] of Object.entries(agentLines)) {
        const set = new Set<string>();
        for (const line of lines) {
          if (line?._type === 'file_review' && line.file) {
            set.add(normalizePath(String(line.file)));
          }
        }
        fileOutcomes[agent] = set;
      }

      const fileCoverage = data?.fileCoverage?.files ?? [];
      const missing: Array<Record<string, unknown>> = [];
      for (const fc of fileCoverage) {
        const filePath = normalizePath(String(fc.file ?? ''));
        const grades: Record<string, string> = fc.grades ?? {};
        for (const [agent, _grade] of Object.entries(grades)) {
          const set = fileOutcomes[agent];
          if (!set) {
            missing.push({
              agent,
              file: filePath,
              reason: 'agent jsonl file not found',
            });
            continue;
          }
          if (!set.has(filePath)) {
            missing.push({ agent, file: filePath });
          }
        }
      }

      if (missing.length > 0) {
        liveFail('grade-without-outcome', {
          count: missing.length,
          examples: missing.slice(0, 10),
        });
      }
    });

    test('every rendered concept has a ReviewConcept in source jsonl', async ({
      page,
    }) => {
      await page.goto(PACK_URL);
      const data = ensurePackData();
      const { agentLines, pr } = ensureJsonl();

      if (Object.keys(agentLines).length === 0) {
        // Skip — file-coverage test above already raised file-coverage-gap.
        return;
      }

      // Build {agent → set of concept_ids}
      const conceptIds: Record<string, Set<string>> = {};
      for (const [agent, lines] of Object.entries(agentLines)) {
        const set = new Set<string>();
        for (const line of lines) {
          if (line?.concept_id) set.add(String(line.concept_id));
        }
        conceptIds[agent] = set;
      }

      // For each non-A finding, the assembler guarantees it came from a
      // ReviewConcept. We can't recover concept_id from rendered HTML alone,
      // but the assembler's invariant is: every finding's (title) and
      // (agent) must correspond to some ReviewConcept whose .title matches.
      const findings = data?.agenticReview?.findings ?? [];

      // Two sources of "title without backing concept_id":
      //   (a) source jsonl has a line with `title` but missing `concept_id`
      //       — this is a SOURCE schema defect, not a rendered-pack defect.
      //   (b) rendered finding's `notable` is not in any ReviewConcept.title
      //       in the source jsonl — this is the canonical concept-id-missing.
      // We separate (a) into its own diagnostic so the orchestrator can
      // dispatch the right correction (re-prompt the reviewer to emit
      // a proper concept_id) instead of misdirecting at the rendered pack.
      const titleByAgent: Record<string, Set<string>> = {};
      const malformedSourceLines: Array<Record<string, unknown>> = [];
      for (const [agent, lines] of Object.entries(agentLines)) {
        const set = new Set<string>();
        for (const line of lines) {
          const hasTitle = typeof line?.title === 'string' && line.title.length > 0;
          const hasConceptId =
            typeof line?.concept_id === 'string' && line.concept_id.length > 0;
          if (hasConceptId && hasTitle) {
            set.add(line.title);
          } else if (hasTitle && !hasConceptId) {
            malformedSourceLines.push({
              agent,
              title: String(line.title).slice(0, 120),
            });
          }
        }
        titleByAgent[agent] = set;
      }

      if (malformedSourceLines.length > 0) {
        liveFail('source-jsonl-missing-concept-id', {
          count: malformedSourceLines.length,
          examples: malformedSourceLines.slice(0, 10),
          pr,
        });
      }

      const orphaned: Array<Record<string, unknown>> = [];
      for (const f of findings) {
        if (!f?.agent) continue;
        const titles = titleByAgent[String(f.agent)] ?? new Set();
        const notable = String(f.notable ?? '');
        if (!notable) continue;
        if (!titles.has(notable)) {
          orphaned.push({
            agent: f.agent,
            notable,
            knownTitles: Array.from(titles).slice(0, 5),
          });
        }
      }

      if (orphaned.length > 0) {
        liveFail('concept-id-missing', {
          count: orphaned.length,
          examples: orphaned.slice(0, 10),
          pr,
        });
      }
    });

    test('architecture_assessment payload validates against schema', async ({
      page,
    }) => {
      await page.goto(PACK_URL);
      const data = ensurePackData();
      const { architectureAssessmentLine } = ensureJsonl();

      const aa = data?.architectureAssessment;
      if (!aa || aa === null) {
        // Renderer may render a "missing" placeholder; that's a different
        // signal handled by the status model, not a schema violation.
        return;
      }

      const requiredFields = [
        'overallHealth',
        'summary',
        'unzonedFiles',
        'registryWarnings',
        'decisionZoneVerification',
      ];
      const missing = requiredFields.filter(
        (k) => !(k in aa) || aa[k] === undefined
      );

      const validHealth = new Set([
        'healthy',
        'needs-attention',
        'action-required',
        'missing',
      ]);
      const healthBad =
        aa.overallHealth !== undefined && !validHealth.has(aa.overallHealth);

      // Cross-check against the source jsonl line if present.
      let sourceMismatch = false;
      const sourceMismatchDetails: Record<string, unknown> = {};
      if (architectureAssessmentLine) {
        // overallHealth must match between rendered DATA and source jsonl.
        if (
          architectureAssessmentLine.overallHealth !== undefined &&
          aa.overallHealth !== undefined &&
          architectureAssessmentLine.overallHealth !== aa.overallHealth
        ) {
          sourceMismatch = true;
          sourceMismatchDetails.overallHealth = {
            source: architectureAssessmentLine.overallHealth,
            rendered: aa.overallHealth,
          };
        }
      }

      if (missing.length > 0 || healthBad || sourceMismatch) {
        liveFail('architecture-assessment-schema', {
          missingFields: missing,
          invalidOverallHealth: healthBad ? aa.overallHealth : null,
          sourceMismatch: sourceMismatch ? sourceMismatchDetails : null,
        });
      }
    });

    // ─── Rendering invariants ───────────────────────────────────────────

    test('no literal "undefined" or "null" tokens in body text', async ({
      page,
    }) => {
      await page.goto(PACK_URL);
      // Walk the DOM, ignore <script>, <style>, and the file modal which
      // shows raw diff content (legitimately contains "/dev/null"). We're
      // looking for renderer leaks ("undefined" rendered into a label,
      // "null" rendered as a value), not legitimate text content.
      const visibleText = await page.evaluate(() => {
        const body = document.body;
        if (!body) return '';
        const skip = new Set([
          'SCRIPT',
          'STYLE',
          'NOSCRIPT',
          'TEMPLATE',
        ]);
        const skipIds = new Set(['file-modal-overlay']);
        const out: string[] = [];
        function walk(n: Node): void {
          if (n.nodeType === Node.ELEMENT_NODE) {
            const el = n as Element;
            if (skip.has(el.tagName)) return;
            if (skipIds.has(el.id)) return;
          }
          if (n.nodeType === Node.TEXT_NODE) {
            out.push(n.nodeValue ?? '');
            return;
          }
          n.childNodes.forEach(walk);
        }
        walk(body);
        return out.join('\n');
      });

      // Match standalone tokens, not substrings (nullable, isUndefinedFlag)
      // and not path components (/dev/null, /undefined).
      const undefRe = /(?<![A-Za-z_/.-])undefined(?![A-Za-z_/.-])/g;
      const nullRe = /(?<![A-Za-z_/.-])null(?![A-Za-z_/.-])/g;
      const undefHits = visibleText.match(undefRe) ?? [];
      const nullHits = visibleText.match(nullRe) ?? [];
      if (undefHits.length > 0 || nullHits.length > 0) {
        liveFail('rendered-undefined-or-null', {
          undefinedCount: undefHits.length,
          nullCount: nullHits.length,
          undefinedSamples: collectContexts(visibleText, undefRe, 3),
          nullSamples: collectContexts(visibleText, nullRe, 3),
        });
      }
    });

    test('no "(N files)" glob row leak in file coverage', async ({ page }) => {
      await page.goto(PACK_URL);
      // Only flag the assembler's glob notation — it always renders as
      // `path/* (N files)` (asterisk + space + parens). Free prose like
      // "...applies to (5 files)" inside a finding's detail HTML is not
      // a leak.
      const text = (await page.locator('body').textContent()) ?? '';
      const matches = text.match(/\*\s*\(\d+ files?\)/g) ?? [];
      if (matches.length > 0) {
        liveFail('glob-row-leak', {
          count: matches.length,
          examples: Array.from(new Set(matches)).slice(0, 5),
        });
      }
    });

    test('no unreplaced INJECT markers in HTML body', async ({ page }) => {
      await page.goto(PACK_URL);
      const bodyHtml = await page.locator('body').innerHTML();
      const outsideScripts = bodyHtml.replace(
        /<script\b[^>]*>[\s\S]*?<\/script>/gi,
        ''
      );
      const matches = outsideScripts.match(/<!-- INJECT:[^>]*-->/g) ?? [];
      if (matches.length > 0) {
        liveFail('inject-marker-leak', {
          count: matches.length,
          examples: matches.slice(0, 5),
        });
      }
    });

    test('every kf-detail-summary has non-empty content', async ({ page }) => {
      await page.goto(PACK_URL);
      // Iterate every detail-summary in the page; flag empties.
      const empties = await page.$$eval('.kf-detail-summary', (els) =>
        els
          .map((el, idx) => ({
            idx,
            text: (el.textContent ?? '').trim(),
            html: (el as HTMLElement).innerHTML.trim(),
          }))
          .filter((e) => e.text.length === 0 && e.html.length === 0)
      );
      if (empties.length > 0) {
        liveFail('empty-detail-summary', {
          count: empties.length,
          indices: empties.slice(0, 10).map((e) => e.idx),
        });
      }
    });

    // ─── Interactivity ──────────────────────────────────────────────────

    test('every kf-row click reveals non-empty detail', async ({ page }) => {
      await page.goto(PACK_URL);
      // Dismiss banner so it doesn't intercept clicks.
      await page.evaluate(() =>
        document.body.setAttribute('data-inspected', 'true')
      );

      const rowCount = await page.locator('.kf-row').count();
      if (rowCount === 0) {
        // Pack with zero findings is valid — nothing to check.
        return;
      }

      const broken: number[] = [];
      for (let i = 0; i < rowCount; i++) {
        const row = page.locator('.kf-row').nth(i);
        await row.click();
        // The detail row sits immediately after; query its summary.
        const detail = page
          .locator('.kf-detail-row')
          .nth(i)
          .locator('.kf-detail-summary');
        if ((await detail.count()) === 0) {
          broken.push(i);
          continue;
        }
        const text = (await detail.textContent()) ?? '';
        if (text.trim().length === 0) broken.push(i);
        // Re-click to collapse and avoid layout drift on the next iteration.
        await row.click();
      }

      if (broken.length > 0) {
        liveFail('interaction-no-detail', {
          count: broken.length,
          rowIndices: broken.slice(0, 10),
        });
      }
    });

    test('every agent filter pill click changes visible row count', async ({
      page,
    }) => {
      await page.goto(PACK_URL);
      await page.evaluate(() =>
        document.body.setAttribute('data-inspected', 'true')
      );

      const pillCount = await page.locator('.kf-agent-pill').count();
      if (pillCount === 0) {
        // Pack without per-agent pills is valid.
        return;
      }

      // Helper to count visible kf-rows.
      async function visibleKfRows(): Promise<number> {
        return page.$$eval('.kf-row', (rows) =>
          rows.filter(
            (r) =>
              (r as HTMLElement).offsetParent !== null &&
              (r as HTMLElement).style.display !== 'none'
          ).length
        );
      }

      const baseline = await visibleKfRows();
      const broken: Array<Record<string, unknown>> = [];

      // Build agent → expected-visible-count from data. A pill click should
      // hide every kf-row whose data-agents attribute does NOT include the
      // pill's agent. The expected count is a lower bound (rows that
      // legitimately match this pill).
      const agentRowCounts: Record<string, number> = await page.$$eval(
        '.kf-row',
        (rows) => {
          const counts: Record<string, number> = {};
          rows.forEach((row) => {
            const agents = (row.getAttribute('data-agents') ?? '')
              .split(/\s+/)
              .filter(Boolean);
            for (const a of agents) counts[a] = (counts[a] ?? 0) + 1;
          });
          return counts;
        }
      );

      for (let i = 0; i < pillCount; i++) {
        const pill = page.locator('.kf-agent-pill').nth(i);
        const agentName =
          (await pill.getAttribute('data-agent')) ?? `pill-${i}`;
        await pill.click();
        const filtered = await visibleKfRows();
        const totalRows = await page.locator('.kf-row').count();
        const expected = agentRowCounts[agentName] ?? 0;

        // The filtered count must equal the expected count of rows whose
        // data-agents includes this agent. If the filter is a no-op,
        // filtered == totalRows; if the filter is broken in another way,
        // filtered will not match expected.
        if (filtered !== expected) {
          // Don't flag the legitimate case where every kf-row already
          // belongs to this agent — that's filtered == totalRows == expected.
          broken.push({
            pill: agentName,
            visible: filtered,
            total: totalRows,
            expected,
            baseline,
          });
        }
        // Click again to deselect (toggle) before next iteration.
        await pill.click();
      }

      if (broken.length > 0) {
        liveFail('interaction-filter-broken', {
          count: broken.length,
          examples: broken.slice(0, 10),
        });
      }
    });

    test('every gate-review-card click reveals detail content', async ({
      page,
    }) => {
      await page.goto(PACK_URL);
      await page.evaluate(() =>
        document.body.setAttribute('data-inspected', 'true')
      );

      const data = ensurePackData();
      const cardCount = await page.locator('.gate-review-card').count();
      if (cardCount === 0) {
        return;
      }
      const gates = data?.convergence?.gates ?? [];

      const broken: Array<Record<string, unknown>> = [];
      for (let i = 0; i < cardCount; i++) {
        const card = page.locator('.gate-review-card').nth(i);
        await card.click();
        const detail = card.locator('.gate-detail');
        if ((await detail.count()) === 0) {
          broken.push({ index: i, reason: '.gate-detail not present' });
          continue;
        }
        const text = (await detail.textContent()) ?? '';
        // Only flag empty detail when the data says there should be detail.
        // Some gates legitimately have empty `detail` strings — that's a
        // signal-encoding choice, not a renderer bug. We trust the data.
        const sourceDetail = String(gates[i]?.detail ?? '').trim();
        if (sourceDetail.length > 0 && text.trim().length === 0) {
          broken.push({
            index: i,
            reason: 'data has detail but rendered detail is empty',
            sourceDetailLength: sourceDetail.length,
          });
        }
        await card.click();
      }

      if (broken.length > 0) {
        liveFail('interaction-gate-empty', {
          count: broken.length,
          examples: broken.slice(0, 10),
        });
      }
    });

    // ─── Terminal: banner strip ─────────────────────────────────────────
    //
    // This test MUST be the last test in this file. It writes to the HTML
    // file on disk only when every preceding test in this serial run has
    // passed.

    test('TERMINAL: strip self-review banner on full pass', async () => {
      // Defense-in-depth check. With serial mode in place this branch is
      // unreachable (Playwright already skipped us). If serial mode is
      // ever dropped, the afterEach hook above sets the flag from the
      // 'skipped' status of upstream failures' siblings, and we refuse
      // to strip the banner here.
      if (liveValidationFailed) {
        liveFail('renderer-template-gap', {
          reason: 'banner-strip refused — earlier live-pack assertion failed',
          rule: 'banner-strip is the terminal test; it only runs when every prior live-pack assertion passes',
        });
      }

      let html = fs.readFileSync(PACK_ABS_PATH, 'utf-8');

      // 1. Flip the data-inspected attribute on <body>.
      html = html.replace(/data-inspected="false"/, 'data-inspected="true"');

      // 2. Remove the banner div.
      html = html.replace(
        /<div id="visual-inspection-banner"[^>]*>[\s\S]*?<\/div>/,
        ''
      );

      // 3. Remove the spacer div.
      html = html.replace(
        /<div id="visual-inspection-spacer"[^>]*><\/div>/,
        ''
      );

      fs.writeFileSync(PACK_ABS_PATH, html, 'utf-8');

      const updated = fs.readFileSync(PACK_ABS_PATH, 'utf-8');
      expect(updated).toContain('data-inspected="true"');
      expect(updated).not.toMatch(/<div id="visual-inspection-banner"/);
    });
  });
}

// ---------------------------------------------------------------------------
// Helpers used outside the conditional branch
// ---------------------------------------------------------------------------

/**
 * Collect up to `max` short context windows for each match of `re` in `text`.
 * Used to build readable failure samples.
 */
function collectContexts(text: string, re: RegExp, max: number): string[] {
  const out: string[] = [];
  // Make sure regex is global.
  const flags = re.flags.includes('g') ? re.flags : re.flags + 'g';
  const r = new RegExp(re.source, flags);
  let m: RegExpExecArray | null;
  while ((m = r.exec(text)) !== null && out.length < max) {
    const start = Math.max(0, m.index - 30);
    const end = Math.min(text.length, m.index + m[0].length + 30);
    out.push(text.slice(start, end).replace(/\s+/g, ' '));
  }
  return out;
}
