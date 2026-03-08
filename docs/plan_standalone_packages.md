---
type: plan
status: wip
pr: 26
created: 2025-03-05
updated: 2025-03-07
---

# Plan: Make Standalone Packages Work as Advertised

## Context

PR #15 restructured the dark factory and PR review pack into extractable packages under `packages/`. The `publish-subtrees.yml` workflow splits and pushes them to standalone repos (`joeyfezster/dark-factory`, `joeyfezster/pr-review-pack`). The repos exist and have code, but:

1. **Docs and scripts contain monorepo-relative paths** that don't work standalone
2. **Two scripts hardcode `joeyfezster/building_ai_w_ai`** instead of auto-detecting the repo
3. **Dependencies are undocumented** — no requirements.txt, no complete prerequisite lists in READMEs
4. **The publish workflow doesn't rewrite paths** — it only resolves the review-prompts symlink

## Completed (prior to this plan)

- [x] Branch protections set on both downstream repos (PRs required, 1 approval, enforce for admins)
- [x] GitHub issues created: #19-#25
- [x] Smoke test completed — structure is sound, path references are the problem

## Dependency Audit

### dark-factory

| Type | Dependency | Required by | Status in README |
|------|-----------|-------------|-----------------|
| Python | stdlib only | all scripts | N/A |
| CLI | `git` | strip/restore holdout, persist_decisions | listed |
| CLI | `gh` (authenticated) | persist_decisions.py (GitHub API) | **missing** |
| CLI | `ruff` | run_gate0.py, nfr_checks.py | not listed (optional, scripts handle gracefully) |
| CLI | `radon` | run_gate0.py, nfr_checks.py | not listed (optional) |
| CLI | `vulture` | run_gate0.py, nfr_checks.py | not listed (optional) |
| CLI | `bandit` | run_gate0.py, nfr_checks.py | not listed (optional) |
| Tool | Claude Code + Agent Teams | orchestration | listed |
| Tool | OpenAI Codex | attractor | listed |

### pr-review-pack

| Type | Dependency | Required by | Status in README |
|------|-----------|-------------|-----------------|
| Python | `pyyaml` (`import yaml`) | scaffold_review_pack_data.py | **missing** |
| CLI | `git` | generate_diff_data.py | listed implicitly |
| CLI | `gh` (authenticated) | scaffold_review_pack_data.py, generate_diff_data.py | **missing** |
| Tool | Claude Code + Agent Teams | Pass 2 semantic analysis | listed |

**Neither package has a `requirements.txt`.** pr-review-pack needs one (for pyyaml). dark-factory doesn't need one (stdlib only) but should note optional CLI tools.

## Work Streams

### Stream 1: Auto-detect repo slug (eliminate hardcoded values)

**Why:** Joey's buddies will use these packages in their own repos. Hardcoded `joeyfezster/building_ai_w_ai` breaks that.

**Files to change (in monorepo, source of truth):**

#### 1a. `packages/dark-factory/scripts/persist_decisions.py`
- Line 34: `REPO_SLUG = "joeyfezster/building_ai_w_ai"` — replace with auto-detect
- Line 126: `f"https://github.com/{REPO_SLUG}/pull/{pr_number}"` — will work automatically once REPO_SLUG is dynamic
- Add `--repo owner/repo` CLI arg as optional override
- Auto-detect implementation:
  ```python
  def _get_repo_slug(override: str | None = None) -> str:
      """Return owner/repo from CLI flag or git remote origin."""
      if override:
          return override
      url = subprocess.check_output(
          ["git", "remote", "get-url", "origin"], text=True
      ).strip()
      # git@github.com:owner/repo.git  OR  https://github.com/owner/repo.git
      if ":" in url and "@" in url:
          slug = url.split(":")[-1]
      else:
          slug = "/".join(url.split("/")[-2:])
      return slug.removesuffix(".git")
  ```
- Remove the module-level `REPO_SLUG = ...` constant; call `_get_repo_slug()` where needed
- Update docstring usage examples to remove hardcoded repo

#### 1b. `packages/pr-review-pack/scripts/scaffold_review_pack_data.py`
- Line 152: hardcoded fallback URL `https://github.com/joeyfezster/building_ai_w_ai/pull/...` — use auto-detected slug
- Line 425: GraphQL query `repository(owner: "joeyfezster", name: "building_ai_w_ai")` — split auto-detected slug into owner/name
- Add `--repo owner/repo` CLI arg as optional override (or detect from existing `--pr` + `gh` context)
- Same `_get_repo_slug()` pattern as 1a (can be copy-pasted; shared module is a separate issue #23)

#### 1c. Verify no other hardcoded repo references in scripts
- `create_postmerge_issues.py` (root `scripts/`, not in a package) — check if it also hardcodes the slug
- Any other script that calls `gh api` or constructs GitHub URLs

### Stream 2: Publish workflow path rewriting (open/closed design)

**Why:** The monorepo uses `packages/dark-factory/scripts/...` paths everywhere. These are correct in-context but wrong in the standalone repos where `scripts/` is at the root.

**File to change:** `.github/workflows/publish-subtrees.yml`

#### Design principle: open/closed via convention, verified by gate

Instead of maintaining a brittle list of sed patterns that must be updated every time a file or path is added, the rewriting uses **two generic rules** plus a **verification gate** that catches anything the rules miss.

#### The two generic rules

**Rule 1 — Self-references:** Strip the package's own monorepo prefix. This is a single sed pattern per package that handles ALL current and future self-referencing paths:

```bash
# dark-factory: strip "packages/dark-factory/" → ""
sed -i "s|packages/dark-factory/||g" "$file"

# pr-review-pack: strip "packages/pr-review-pack/" → ""
sed -i "s|packages/pr-review-pack/||g" "$file"
```

This automatically handles `packages/dark-factory/scripts/`, `packages/dark-factory/docs/`, `packages/dark-factory/SKILL.md`, and any future subdirectory — no maintenance needed when adding new files.

**Rule 2 — Cross-references:** Replace references to sibling packages and monorepo skill paths with their standalone repo URLs. These are a small, stable set:

```bash
# In dark-factory context:
sed -i "s|packages/pr-review-pack/|https://github.com/joeyfezster/pr-review-pack/tree/main/|g" "$file"
sed -i "s|packages/review-prompts/|review-prompts/|g" "$file"

# In pr-review-pack context:
sed -i "s|packages/dark-factory/|https://github.com/joeyfezster/dark-factory/tree/main/|g" "$file"
sed -i "s|packages/review-prompts/|review-prompts/|g" "$file"
```

**Rule 2b — Skill install paths:** The SKILL.md and other docs reference `.claude/skills/{name}/...` paths. These are the paths as seen from the *consuming repo's root* after installation. In the standalone repo they should reference the local root:

```bash
# In dark-factory context:
sed -i "s|\.claude/skills/factory-orchestrate/||g" "$file"

# In pr-review-pack context:
sed -i "s|\.claude/skills/pr-review-pack/||g" "$file"
```

**Order:** Rule 1 (self-references) runs first. Then Rule 2 (cross-references). Then Rule 2b (skill paths). Longest patterns naturally match first within each sed call (sed is greedy).

#### Special case handling (via sed, not manual)

Lines like `From the monorepo root, these resolve to packages/dark-factory/scripts/.` become `From the monorepo root, these resolve to scripts/.` after Rule 1 — which is awkward but not broken. If we want cleaner results for known special-case lines:

```bash
# Remove the "From the monorepo root" explanatory line (only relevant in monorepo)
sed -i '/From the monorepo root, these resolve to/d' "$file"

# Replace hardcoded repo references with generic instruction
sed -i 's|Repository: `joeyfezster/building_ai_w_ai`|Repository: your project repository|g' "$file"
```

These are **content-aware deletions** — a small set of lines that only make sense in monorepo context. They are stable (the lines don't change frequently) and safe (deleting a line that doesn't match is a no-op).

#### The verification gate (this is the key)

After all rewrites, before committing, run a verification step that **fails the publish job** if stale monorepo paths remain:

```yaml
- name: Verify no stale monorepo paths
  run: |
    cd packages/${{ matrix.package }}
    STALE=$(grep -rn \
      "packages/dark-factory\|packages/pr-review-pack\|packages/review-prompts\|\.claude/skills/" \
      --include="*.md" --include="*.py" --include="*.yaml" --include="*.yml" \
      . 2>/dev/null | grep -v "CONTRIBUTING.md" | grep -v "^Binary" || true)
    if [ -n "$STALE" ]; then
      echo "ERROR: Stale monorepo paths found after rewrite:"
      echo "$STALE"
      echo ""
      echo "Fix: add a rewrite rule in publish-subtrees.yml or update the source file."
      exit 1
    fi
    echo "OK: no stale monorepo paths found."
```

**This is the open/closed compliance mechanism:**
- **Open:** Add new scripts, docs, or paths freely. Rule 1 (prefix stripping) handles them automatically.
- **Closed:** If someone adds a *new cross-reference pattern* that Rule 2 doesn't cover, the gate catches it and the publish fails with a clear error message telling you exactly which file and line needs attention.
- **No silent breakage:** Stale paths can't reach the downstream repos.

#### Full publish job structure (per package)

```yaml
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 0

  - name: Resolve review-prompts symlink
    run: |
      # (existing step — unchanged)

  - name: Rewrite paths for standalone context
    run: |
      cd packages/{package-name}

      # Rule 1: Strip self-referencing monorepo prefix
      find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.yaml" -o -name "*.yml" \) \
        -not -path './.git/*' -exec \
        sed -i "s|packages/{package-name}/||g" {} +

      # Rule 2: Cross-references to sibling packages → standalone repo URLs
      find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.yaml" -o -name "*.yml" \) \
        -not -path './.git/*' -exec \
        sed -i \
          -e "s|packages/{sibling}/|https://github.com/joeyfezster/{sibling}/tree/main/|g" \
          -e "s|packages/review-prompts/|review-prompts/|g" {} +

      # Rule 2b: Skill install paths → local root
      find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.yaml" -o -name "*.yml" \) \
        -not -path './.git/*' -exec \
        sed -i "s|\.claude/skills/{skill-name}/||g" {} +

      # Special cases: remove monorepo-only context lines
      sed -i '/From the monorepo root, these resolve to/d' SKILL.md
      sed -i 's|Repository: `joeyfezster/building_ai_w_ai`|Repository: your project repository|g' SKILL.md

      cd ../..

  - name: Verify no stale monorepo paths
    run: |
      cd packages/{package-name}
      STALE=$(grep -rn \
        "packages/dark-factory\|packages/pr-review-pack\|packages/review-prompts\|\.claude/skills/" \
        --include="*.md" --include="*.py" --include="*.yaml" --include="*.yml" \
        . 2>/dev/null | grep -v "CONTRIBUTING.md" | grep -v "^Binary" || true)
      if [ -n "$STALE" ]; then
        echo "ERROR: Stale monorepo paths found after rewrite:"
        echo "$STALE"
        echo ""
        echo "Fix: add a rewrite rule in publish-subtrees.yml or update the source file."
        exit 1
      fi
      echo "OK: no stale monorepo paths found."

  - name: Commit all publish transforms
    run: |
      cd packages/{package-name}
      git add -A
      git diff --staged --quiet || git commit --amend --no-edit
      cd ../..

  - name: Split subtree
    run: git subtree split --prefix packages/{package-name} -b subtree-{package-name}

  # (SSH + push steps unchanged)
```

### Stream 3: Dependency documentation + README improvements

**Files to change:**
- `packages/dark-factory/README.md`
- `packages/pr-review-pack/README.md`
- NEW: `packages/pr-review-pack/requirements.txt`

#### 3a. pr-review-pack: add requirements.txt

```
pyyaml>=6.0
```

This is the only third-party Python dependency across both packages. dark-factory is stdlib-only and doesn't need one.

#### 3b. dark-factory README.md

**Prerequisites section — rewrite to be complete:**

```markdown
## Prerequisites

**Required:**
- **Python 3.12+**
- **git**
- **gh CLI** (authenticated — `gh auth login`) — used by `persist_decisions.py` for GitHub API calls
- **Claude Code** with Agent Teams enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)
- **OpenAI Codex** or any non-interactive coding agent

**Optional (for Gate 0 Tier 1 and Gate 2 NFR checks):**
- `ruff` — code quality (`pip install ruff`)
- `radon` — cyclomatic complexity (`pip install radon`)
- `vulture` — dead code detection (`pip install vulture`)
- `bandit` — security scanning (`pip install bandit`)

Scripts handle missing optional tools gracefully — checks are skipped with a warning, not a crash.
```

**Add Installation section:**

```markdown
## Installation

Clone into your repo's Claude Code skills directory:
\```bash
git clone https://github.com/joeyfezster/dark-factory.git .claude/skills/factory-orchestrate
\```

The factory also uses the [PR Review Pack](https://github.com/joeyfezster/pr-review-pack) for generating merge-gate reports:
\```bash
git clone https://github.com/joeyfezster/pr-review-pack.git .claude/skills/pr-review-pack
\```
```

**Fix broken cross-reference:** `../pr-review-pack/` → `https://github.com/joeyfezster/pr-review-pack`

#### 3c. pr-review-pack README.md

**Prerequisites section — rewrite:**

```markdown
## Prerequisites

- **Python 3.12+** with `pyyaml` installed (`pip install -r requirements.txt`)
- **git**
- **gh CLI** (authenticated — `gh auth login`) — used for PR metadata, CI checks, and comment resolution
- **Claude Code** with Agent Teams enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)
```

**Quick Start section — rewrite line 15-23:**

```markdown
## Quick Start

1. Clone into your repo's Claude Code skills directory:
   \```bash
   git clone https://github.com/joeyfezster/pr-review-pack.git .claude/skills/pr-review-pack
   pip install -r .claude/skills/pr-review-pack/requirements.txt
   \```
2. Create a zone registry from the example:
   \```bash
   cp .claude/skills/pr-review-pack/examples/zone-registry.example.yaml .claude/zone-registry.yaml
   # Edit zone-registry.yaml to map your repo's files to architectural zones
   \```
3. Run the skill:
   \```
   /pr-review-pack <PR#>
   \```
```

### Stream 4: Verify end-to-end

After streams 1-3, push to main (triggers publish-subtrees), then:

1. **Delete and re-clone** both standalone repos to `/tmp/package-smoke-test/`
2. **Verify the publish gate passed** — check the Actions run for "Verify no stale monorepo paths" step
3. **Check zero hardcoded repo slugs** — `grep -r "joeyfezster/building_ai_w_ai" .` should return nothing in scripts (CONTRIBUTING.md reference is OK)
4. **Verify script --help** works for all scripts in both packages
5. **Verify `pip install -r requirements.txt`** works for pr-review-pack
6. **Verify README instructions** — follow the Quick Start steps: clone into a test repo's `.claude/skills/`, check that documented paths match actual file locations
7. **Visual review** of both READMEs for clarity, completeness, and accuracy

## Execution Order

1. **Stream 1** (repo slug auto-detect) — code change in monorepo scripts
2. **Stream 3** (dependency docs + README) — can run in parallel with Stream 1 (different files)
3. **Stream 2** (publish workflow + verification gate) — depends on knowing the final file state from Streams 1 and 3
4. **Stream 4** (verify) — requires all changes merged and publish workflow to have run

All changes are made in the monorepo (`building_ai_w_ai`). The downstream repos update automatically via `publish-subtrees.yml`.

## Out of Scope

- Extracting `_get_repo_root()` into shared module (tracked in issue #23)
- Installing gate 2 tools (tracked in issue #20)
- Zone registry updates (tracked in issue #21)
- factory.yaml CI readiness (tracked in issue #19)
