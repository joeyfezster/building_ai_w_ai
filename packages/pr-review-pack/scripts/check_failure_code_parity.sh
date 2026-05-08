#!/usr/bin/env bash
# Failure-code registry parity check.
#
# Every code referenced by liveFail(...) in the live-pack-validation spec
# must be documented in the failure-codes registry, and vice versa. The
# grep matches single-quoted, double-quoted, and backtick-quoted code
# literals so a future contributor cannot bypass parity by switching
# quote style. Empty extractions fail loud: a silently-passing parity
# check is worse than no check at all.
#
# Usage: bash scripts/check_failure_code_parity.sh
# Resolves paths relative to the skill root (parent of this script's dir).

set -euo pipefail

SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SPEC="$SKILL_ROOT/e2e/live-pack-validation.spec.ts"
REG="$SKILL_ROOT/references/live-pack-failure-codes.md"

if [ ! -f "$SPEC" ]; then
  echo "ERROR: spec file not found at $SPEC"
  exit 1
fi
if [ ! -f "$REG" ]; then
  echo "ERROR: registry file not found at $REG"
  exit 1
fi

spec_codes=$(grep -oE "liveFail\(\s*['\"\`][a-z][a-z0-9-]*['\"\`]" "$SPEC" \
  | sed -E "s/.*['\"\`]([a-z0-9-]+)['\"\`].*/\1/" | sort -u)
reg_codes=$(grep -E "^\| \`[a-z][a-z0-9-]*\` \|" "$REG" \
  | sed -E 's/^\| `([a-z0-9-]+)`.*/\1/' | sort -u)

# Sanity guard: empty extraction means the regex broke and the
# parity check would silently pass. Fail loudly instead.
if [ -z "$spec_codes" ]; then
  echo "ERROR: spec_codes extraction was empty — parity check broken."
  echo "Inspect the regex against $SPEC."
  exit 1
fi
if [ -z "$reg_codes" ]; then
  echo "ERROR: reg_codes extraction was empty — parity check broken."
  echo "Inspect the regex against $REG."
  exit 1
fi

if [ "$spec_codes" != "$reg_codes" ]; then
  echo "Failure-code registry mismatch."
  echo ""
  echo "Spec codes:"
  echo "$spec_codes"
  echo ""
  echo "Registry codes:"
  echo "$reg_codes"
  echo ""
  echo "Diff (spec vs registry):"
  diff <(echo "$spec_codes") <(echo "$reg_codes") || true
  exit 1
fi

code_count=$(echo "$spec_codes" | wc -l | tr -d ' ')
echo "Failure-code registry parity OK ($code_count codes match between spec and registry)."
