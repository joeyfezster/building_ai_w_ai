# Project Conventions

## Decision Record Convention

Plan documents in `docs/` use YAML frontmatter to track lifecycle status. This enables automated tooling (e.g., `persist_decisions.py`) and provides consistent metadata across all plan docs.

### Frontmatter Schema

```yaml
---
type: plan                          # always "plan" for plan documents
status: implemented | wip | abandoned | deferred
pr: 26                              # PR number where this plan was executed (if applicable)
created: 2025-03-05                 # date the plan was created
updated: 2025-03-07                 # date of last status change
supersedes: plan_old_approach.md    # (optional) previous plan this replaces
---
```

### Status Definitions

| Status | Meaning | When to use |
|--------|---------|-------------|
| `implemented` | Plan executed and merged | After the PR implementing this plan is merged |
| `wip` | Work in progress | Plan is actively being executed |
| `abandoned` | Plan was rejected or superseded | When a different approach was chosen |
| `deferred` | Plan is valid but deprioritized | When the work is postponed to a future iteration |

### Rules

1. **Every plan document MUST have frontmatter.** No exceptions. If a plan doc exists without frontmatter, add it.
2. **Status updates happen in the frontmatter, not in the body.** Don't add "STATUS: DONE" text -- update the `status` field.
3. **The schema is static.** Do not add custom fields per plan. If a new field is needed, propose it here first.
4. **`updated` reflects the last status change**, not the last edit to the document body.

### Factory Decision Log Integration

The factory's decision persistence script (`packages/dark-factory/scripts/persist_decisions.py`) extracts decisions from PR review packs and appends them to `docs/decisions/decision_log.json`. This is a separate system from plan frontmatter:

- **Plan frontmatter** tracks the lifecycle of a plan document (the "what we decided to build").
- **Decision log** tracks individual decisions made during PR review (the "why we built it this way").

Both are useful. They don't replace each other. A single plan may produce multiple PRs, each with multiple decisions in the log.
