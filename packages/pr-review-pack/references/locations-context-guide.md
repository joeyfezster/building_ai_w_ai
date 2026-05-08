# `ConceptLocation.context` — anchors vs cross-references

Every `locations[*]` entry in a `ReviewConcept` (or `ConceptUpdate`) carries one of two distinct intents, distinguished by the boolean `context` flag:

| Field | Intent | File-in-diff requirement |
|---|---|---|
| `context: false` (default) | **Anchor** — this code is what the finding is ABOUT | **Required** — file MUST be in the PR diff |
| `context: true` | **Cross-reference** — where the fix goes / analogous pattern / related test / contract spec / docs | **None** — file does NOT need to be in the diff |

Live-pack validation enforces:
- Every finding must have **at least one anchor** location whose file resolves to a path in `diff_data.files` (anchor = in-diff anchor).
- Out-of-diff anchors trigger `finding-location-mismatch`.
- A finding with anchors but **zero in-diff anchors** triggers the sharper `finding-without-anchor`.
- `context: true` locations are **never** validated against the diff — they pass freely.

## When to set `context: true`

Set `context: true` whenever the file you are pointing at is **not the subject of the finding**, but is referenced for one of these reasons:

1. **Where the fix should go.** The change you recommend lives in this file, but this PR does not touch it.
   ```json
   {
     "file": ".claude/zone-registry.yaml",
     "lines": "68-73",
     "comment": "Add live-pack-failure-codes.md to the review-pack zone's specs list",
     "context": true
   }
   ```

2. **An analogous pattern.** "This finding is consistent with how we did X over there."
   ```json
   {
     "file": "src/auth/legacy_handler.py",
     "comment": "Same retry shape as here — see the existing implementation for reference",
     "context": true
   }
   ```

3. **A related test.** "Coverage exists for the in-diff change at this test location, even though that file is not modified in this PR."
   ```json
   {
     "file": "tests/test_url_routing.py",
     "comment": "Existing coverage of the function being refactored; verify no regressions",
     "context": true
   }
   ```

4. **A contract spec or documentation file.** "This change should be reflected in the spec/CHANGELOG."
   ```json
   {
     "file": "CHANGELOG.md",
     "comment": "Add an entry under the Unreleased section",
     "context": true
   }
   ```

## When NOT to set `context: true`

Do NOT use `context: true` to silence the validation when the location is genuinely the subject of your finding. If you find yourself flagging code in a file that's not in the diff, your finding is probably about something not in the PR — that's a hallucination or a misplaced finding, not a cross-reference.

Specifically:
- ❌ "This file is broken" with `context: true` → the file IS the subject, mark `context: false` and confirm the file is in the diff.
- ❌ "This code does X" with `context: true` → IS the subject.
- ✅ "The fix for the in-diff code lives in this other file" with `context: true` → cross-reference.

## Required pattern

A finding can have:
- 1+ anchor locations (`context: false`, in-diff) — REQUIRED
- 0+ context locations (`context: true`, anywhere) — OPTIONAL

The first location does NOT have to be the anchor; ordering is convention-only. What matters is that at least one location has `context: false` AND is in the diff.

## Backwards compatibility

Existing reviewer outputs that omit the `context` field default to `context: false`. This is correct for findings whose locations are all in-diff anchors. It misclassifies pre-existing cross-references as anchors, which would now fail validation. If you encounter this in a `ConceptUpdate` correction loop, the right fix is to re-emit the location with `context: true` rather than to delete it.
