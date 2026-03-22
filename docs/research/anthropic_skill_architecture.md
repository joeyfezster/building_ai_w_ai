# How Anthropic Builds Skills: Architecture Patterns from 12+ Official Skills

**Date:** 2026-03-14
**Method:** Deep source code analysis of every Anthropic-published skill and plugin across 4 GitHub repositories
**Author:** Joey Baruch (research assisted by Claude)

---

## Repositories Analyzed

| Repository | Contents | Count |
|-----------|----------|-------|
| `anthropics/claude-code/plugins/` | Bundled plugins shipping with Claude Code | 13 plugins |
| `anthropics/claude-plugins-official/plugins/` | Official marketplace plugins | 30+ plugins |
| `anthropics/skills/skills/` | Standalone SKILL.md instruction sets | 17 skills |
| `anthropics/knowledge-work-plugins/` | Cowork-oriented connector plugins | 11 plugins |

## Skills Deep-Read (Full Source)

| Skill | Complexity | Agents | Scripts | Key Pattern |
|-------|-----------|--------|---------|-------------|
| **plugin-dev** | Highest | 3 + 7 sub-skills | Validation scripts | Phase-gated skill loading |
| **skill-creator** | Very High | 3 | 9 Python scripts | Eval infrastructure + description optimization |
| **feature-dev** | High | 3 | None | Human gates + confidence scoring |
| **code-review** | High | 8+ inline | None | Model tiering (haiku/sonnet/opus) + two-pass validation |
| **pr-review-toolkit** | High | 6 | None | Description-as-router + Task tool dispatch |
| **hookify** | High | 1 + rule engine | 4 Python hooks | Lifecycle hooks + YAML config |
| **ralph-wiggum** | Medium | None | Shell scripts | Stop hook interception loop |
| **agent-sdk-dev** | Medium | 2 verifiers | None | Post-creation verification agents |
| **mcp-builder** | Medium | None | Eval harness | Reference-heavy progressive disclosure |
| **security-guidance** | Low | None | 1 Python hook | PreToolUse pattern detection |
| **webapp-testing** | Low | None | 1 Python script | "Scripts as black boxes" pattern |
| **playground** | Medium | None | None | Template selection via sub-skills |

---

## Pattern 1: Progressive Contexting — The 3-Tier Architecture

Every complex Anthropic skill follows the same context management strategy. This is the single most important pattern.

### The Three Tiers

| Tier | What Gets Loaded | When | Context Cost | Example |
|------|-----------------|------|-------------|---------|
| **1** | Frontmatter: `name` + `description` | Always (every conversation) | ~100 words | `"Create new skills, modify and improve existing skills..."` |
| **2** | SKILL.md body | On skill invocation | **< 500 lines** (skill-creator's own recommendation) | Workflow phases, agent table, key instructions |
| **3** | `references/`, `agents/`, `scripts/`, `examples/` | On-demand, per phase | Unlimited | Schema docs, paradigm prompts, validation scripts |

### How It Works in Practice

**skill-creator** is the canonical example. Its SKILL.md is ~500 lines and explicitly states: "Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next."

**plugin-dev** is the most sophisticated implementation. Its command file assigns specific skills to specific phases:
- Phase 2: "Load the `plugin-structure` skill first"
- Phase 5: Load the relevant skill per component type (agent-development, command-development, hook-development, etc.)
- Phase 6: Run `plugin-validator` and `skill-reviewer` agents

The command file is a **conductor** — it tells Claude what to load and when, not what's in those files.

**mcp-builder** tells Claude to fetch reference docs from URLs: "Read the appropriate SDK reference based on the user's language choice." The SKILL.md itself never includes those docs — it just points to them.

**webapp-testing** goes further: "Treat bundled scripts as black boxes — invoke with `--help`, don't read source." The scripts execute without ever entering Claude's context window.

### The Key Insight

Context is a finite, precious resource. Every line in SKILL.md is loaded on every invocation regardless of which phase the skill is in. Anthropic treats SKILL.md like a conductor's score — it tells you the structure and when to bring in each section of the orchestra. The actual music lives in the parts (reference files, agent definitions, scripts).

### What This Means for Skill Builders

```
skill-name/
├── SKILL.md                    ← Tier 2: conductor (~500 lines max)
│   ├── YAML frontmatter        ← Tier 1: always loaded (~100 words)
│   └── Workflow + phase gates
├── agents/                     ← Tier 3: loaded per agent spawn
├── references/                 ← Tier 3: loaded on demand
├── scripts/                    ← Tier 3: executed, never read
├── examples/                   ← Tier 3: loaded on demand
└── assets/                     ← Tier 3: used in output, never loaded
```

---

## Pattern 2: Agent Definition Files Are First-Class Citizens

All complex Anthropic plugins define agents in separate `.md` files under `agents/`, never inline in the command file.

### Agent Frontmatter Schema

```yaml
---
name: plugin-validator              # kebab-case, 2-4 words
description: "Use this agent when..." # Includes <example> blocks for triggering
model: inherit                       # inherit | sonnet | opus | haiku
color: yellow                        # blue | cyan | green | yellow | magenta | red
tools: ["Read", "Grep", "Glob", "Bash"]  # Explicit tool whitelist
---
```

### Real Examples Across Skills

| Plugin | Agent | Model | Tools | Purpose |
|--------|-------|-------|-------|---------|
| plugin-dev | agent-creator | sonnet | Write, Read | Creates agent files |
| plugin-dev | plugin-validator | inherit | Read, Grep, Glob, Bash | Structural validation |
| plugin-dev | skill-reviewer | inherit | Read, Grep, Glob | Quality review (no writes!) |
| feature-dev | code-explorer | sonnet | Glob, Grep, LS, Read, ... | Codebase analysis |
| feature-dev | code-architect | sonnet | Glob, Grep, LS, Read, ... | Architecture design |
| feature-dev | code-reviewer | sonnet | Glob, Grep, LS, Read, ... | Code review |
| pr-review-toolkit | code-reviewer | **opus** | (inherited) | General code quality |
| pr-review-toolkit | code-simplifier | **opus** | (inherited) | Post-review polish |
| pr-review-toolkit | pr-test-analyzer | inherit | (inherited) | Test coverage analysis |

### The `tools` Field Is the Permission Mechanism

This is critical: the `tools` array in agent frontmatter is how Anthropic grants subagent permissions. It's not `mode: "acceptEdits"` on the spawn call — it's a declarative field on the agent definition itself.

- **plugin-dev's skill-reviewer** gets `["Read", "Grep", "Glob"]` — no Write, no Bash. It can analyze but never modify.
- **plugin-dev's agent-creator** gets `["Write", "Read"]` — it needs to create files.
- **plugin-dev's plugin-validator** gets `["Read", "Grep", "Glob", "Bash"]` — it needs Bash to run validation scripts.

This is **least privilege by design**.

### Description-as-Router

Several agents (especially in pr-review-toolkit) use the `description` field not just for documentation but as the primary routing mechanism. The comment-analyzer agent has **no body prompt at all** — its entire definition is in the description field with `<example>` blocks:

```yaml
description: Use this agent when you need to analyze code comments for accuracy...

<example>
Context: The user is working on a pull request that adds documentation comments.
user: "I've added documentation to these functions. Can you check if the comments are accurate?"
assistant: "I'll use the comment-analyzer agent to review all comments..."
<commentary>
Since the user has added documentation comments, use the comment-analyzer agent.
</commentary>
</example>
```

The examples teach Claude when to invoke the agent. The commentary explains the reasoning. This is how triggering is tuned without keyword matching.

---

## Pattern 3: Model Tiering — Cost Optimization by Routing

Anthropic doesn't use opus for everything. They route tasks to the cheapest model that can handle them.

### code-review's Three-Tier Pipeline

| Task | Model | Why |
|------|-------|-----|
| Is the PR closed/draft/already reviewed? | **Haiku** | Binary check, cheapest possible |
| Summarize changes | **Sonnet** | Needs comprehension, not deep reasoning |
| CLAUDE.md compliance audit (2 agents) | **Sonnet** | Pattern matching against rules |
| Bug detection (2 agents) | **Opus** | Requires deep logical reasoning |
| Bug validation (per finding) | **Opus** | Confirms/rejects first-pass findings |

This pipeline processes the same PR at three cost levels. The cheapest model does the cheapest work.

### feature-dev's Uniform Approach

All three agents (explorer, architect, reviewer) use **sonnet**. The orchestrating command runs at whatever model the user chose. This makes sense — the agents are doing analysis and design, not the hardest reasoning tasks.

### pr-review-toolkit's Selective Upgrade

Only `code-reviewer` and `code-simplifier` use **opus**. The other 4 agents (comment-analyzer, pr-test-analyzer, silent-failure-hunter, type-design-analyzer) use **inherit** — they get whatever model the user is running.

### The Principle

Use the cheapest model that produces acceptable quality for each specific subtask. Haiku for triage, sonnet for analysis, opus for adversarial reasoning. Don't pay opus prices for a "is this PR closed?" check.

---

## Pattern 4: The Orchestrator Is a Conductor, Not a Textbook

### What Orchestrating Commands Do

Every complex Anthropic skill has a command file that follows the same pattern:

1. **Phase list** — numbered phases with clear gates
2. **What to load** — which skill/agent/reference to read for each phase
3. **When to stop** — human confirmation checkpoints
4. **What to track** — TodoWrite progress markers

### What Orchestrating Commands Do NOT Do

- They do not contain the full system prompts for agents (those live in `agents/*.md`)
- They do not contain schema definitions (those live in `references/`)
- They do not contain implementation logic (that lives in `scripts/`)
- They do not contain examples (those live in `examples/`)

### plugin-dev's Command: The Gold Standard

plugin-dev's `create-plugin.md` is ~200 lines. It orchestrates:
- 3 agents (agent-creator, plugin-validator, skill-reviewer)
- 7 sub-skills (agent-development, command-development, hook-development, mcp-integration, plugin-settings, plugin-structure, skill-development)
- Each sub-skill has its own SKILL.md + references/ + examples/ + scripts/

The command file never duplicates what's in those sub-skills. It says things like:
- "Load the `plugin-structure` skill first"
- "Load relevant skill per component type before creating"
- "Run `plugin-validator` agent"

If the command file tried to contain everything those 7 skills and 3 agents contain, it would be thousands of lines — all loaded into Tier 2 context on every invocation.

### feature-dev's Command: Human Gates

feature-dev's command file is ~150 lines with 7 phases. Five of those phases end with explicit human gates:
- Phase 3: "**CRITICAL**: This is one of the most important phases. DO NOT SKIP."
- Phase 5: "**DO NOT START WITHOUT USER APPROVAL**"
- Phase 6: "**Present findings to user and ask what they want to do**"

The gates are the primary enforcement mechanism for phase transitions.

---

## Pattern 5: Validation Architecture

Anthropic uses three distinct validation patterns, often in combination.

### Pattern A: Agent-as-Validator (code-review)

For each bug finding, spawn a **separate validation subagent** whose only job is to confirm or reject it:

```
Step 4: 4 agents find issues independently
Step 5: For each issue from agents 3+4, launch a validation subagent
Step 6: Filter out issues that weren't validated
```

This is explicit false-positive defense. The system distrusts its own first-pass findings.

### Pattern B: Confidence Scoring (feature-dev, pr-review-toolkit)

feature-dev's code-reviewer uses a 0-100 confidence scale with a hard cutoff:
- "**Only report issues with confidence >= 80.** Focus on issues that truly matter — quality over quantity."

Different agents use different scales:
- code-reviewer: 0-100 numeric
- pr-test-analyzer: 1-10 criticality
- silent-failure-hunter: CRITICAL / HIGH / MEDIUM categories
- type-design-analyzer: four separate 1-10 dimensions

### Pattern C: Structural Validation (plugin-dev)

plugin-dev's `plugin-validator` agent runs validation scripts:
- `validate-agent.sh`
- `validate-hook-schema.sh`
- `test-hook.sh`
- `hook-linter.sh`

These are deterministic checks, not LLM judgment.

### Pattern D: Self-Review Gate (code-review)

Before posting comments, the orchestrator writes out all planned comments internally: "Create a list of all comments that you plan on leaving. This is only for you... Do not post this list anywhere."

This chain-of-thought checkpoint forces the agent to review its own actions before executing them.

### What None of Them Do

**None of the 12+ skills enforce structured JSON schemas between agents and orchestrator.** All agent communication is natural language. skill-creator's graders write `grading.json` to disk, but the orchestrator reads the file — it doesn't parse agent return values as structured data.

---

## Pattern 6: Scripts Execute Without Context Cost

This is a simple but powerful pattern used by every skill with complex logic.

### skill-creator: 9 Python Scripts

```bash
python -m scripts.aggregate_benchmark workspace/iteration-N --skill-name my-skill
python -m scripts.run_loop --eval-set eval.json --skill-path skill/ --max-iterations 5
python -m scripts.run_eval --eval-set eval.json --skill-path skill/
python -m scripts.improve_description ...
python -m scripts.package_skill path/to/skill
python -m scripts.quick_validate path/to/skill
```

The orchestrator never reads the script source — it just calls it. The scripts' logic (stratified train/test splits, trigger detection via stream events, benchmark aggregation with mean/stddev) never enters the context window.

### mcp-builder: Eval Harness

```bash
python scripts/evaluation.py -t stdio -c python -a server.py evaluation.xml
```

The evaluation harness (XML parsing, agent loop, accuracy reporting) runs as a black box.

### webapp-testing: Explicit Instruction

> "Treat bundled scripts as black boxes — invoke with `--help`, don't read source."

This is the clearest statement of the principle: scripts are tools, not context.

---

## Pattern 7: TodoWrite for Progress Tracking

plugin-dev mandates TodoWrite at every phase: "Use TodoWrite to track progress at every phase."

skill-creator: "Please add steps to your TodoList, if you have such a thing, to make sure you don't forget."

feature-dev Phase 1: "Create todo list with all phases."

This creates:
1. **Visible progress tracking** — the user can see what phase the agent is in
2. **Recovery state** — if the session interrupts, the todo list shows where to resume
3. **Accountability** — the agent can't silently skip phases if they're tracked

---

## Pattern 8: `allowed-tools` — Broad Categories, Not Granular

### The Spectrum

| Skill | allowed-tools | Strategy |
|-------|--------------|----------|
| code-review | `Bash(gh issue view:*)`, `Bash(gh pr comment:*)`, ... | Granular: only specific gh subcommands |
| plugin-dev | `Read, Write, Grep, Glob, Bash, TodoWrite, AskUserQuestion, Skill, Task` | Maximal: everything needed |
| feature-dev | *(none specified)* | Inherit everything from session |
| skill-creator | *(none specified)* | Inherit everything from session |

### The Pattern

Most complex skills either:
1. **List nothing** — inherit everything from the session (feature-dev, skill-creator)
2. **List broad categories** — `Bash`, `Read`, `Write`, not `Bash(git diff:*)` (plugin-dev)

Only code-review uses granular `Bash(subcommand:*)` syntax — and it's a pure GitHub operation where tight scoping makes sense.

### Key Tools to Include

plugin-dev's `allowed-tools` is the most instructive because it explicitly includes tools that enable orchestration:
- **`Skill`** — to load sub-skills per phase
- **`Task`** — to spawn agents
- **`TodoWrite`** — for progress tracking
- **`AskUserQuestion`** — for human gates

---

## Pattern 9: Hook Architecture

Two plugins (hookify, security-guidance) and ralph-wiggum use hooks — shell/Python scripts that fire on Claude Code lifecycle events.

### Available Hook Events

| Event | When It Fires | Use Case |
|-------|--------------|----------|
| PreToolUse | Before any tool call | Security checks, permission gates |
| PostToolUse | After any tool call | Logging, validation |
| UserPromptSubmit | When user sends a message | Context injection |
| Stop | When Claude tries to exit | Ralph loop continuation |
| SessionStart | Session begins | Context loading |
| SessionEnd | Session ends | Cleanup |
| SubagentStop | Subagent completes | Coordination |
| PreCompact | Before context compaction | State preservation |
| Notification | On notification | Alert handling |

### Hook Protocol

- Exit code 0 = allow
- Exit code 2 = block (PreToolUse only)
- JSON output: `{"decision": "block", "reason": "..."}` (Stop), `{"permissionDecision": "allow/deny"}` (PreToolUse)
- All hooks have 10-second timeout
- Hooks read JSON from stdin (tool call details, transcript path, etc.)

### security-guidance: Stateful Pattern Detection

Maintains session state files to avoid repeating warnings. A specific security rule for a given file triggers only once per session. Auto-cleans state files older than 30 days.

### ralph-wiggum: Stop Hook Interception

The Stop hook reads the transcript JSONL, extracts the last assistant message, checks for a `<promise>` tag, and if not found, feeds the same prompt back by returning `{"decision": "block", "reason": "<original prompt>"}`.

---

## Pattern 10: Eval Infrastructure (skill-creator)

skill-creator has the most sophisticated quality assurance system of any Anthropic skill.

### The Eval Loop

1. **Write test prompts** — 2-3 realistic user messages
2. **Spawn parallel subagents** — with-skill AND baseline runs simultaneously
3. **While running, draft assertions** — quantitative checks for each test case
4. **Grade** — subagent reads `agents/grader.md`, evaluates assertions, writes `grading.json`
5. **Aggregate** — `aggregate_benchmark.py` produces stats with mean/stddev
6. **Analyze** — surface patterns stats would hide (non-discriminating assertions, flaky evals)
7. **Launch viewer** — `generate_review.py` serves HTML for human review
8. **Collect feedback** — user reviews in browser, feedback auto-saves to `feedback.json`
9. **Improve and repeat**

### Description Optimization (Separate Loop)

1. Generate 20 trigger/no-trigger eval queries (10 should-trigger, 10 should-not)
2. 60/40 train/test stratified split
3. Evaluate current description (3 runs per query for reliability)
4. Improve via Claude (sees train scores only — test scores stripped to prevent overfitting)
5. Re-evaluate on both train and test
6. Select best by test score
7. Max 5 iterations

This is ML-style hyperparameter optimization applied to natural language descriptions.

### The Writing Philosophy

skill-creator's SKILL.md contains the most explicit writing guidance of any Anthropic skill:

> "Try hard to explain the **why** behind everything you're asking the model to do. Today's LLMs are *smart*. If you find yourself writing ALWAYS or NEVER in all caps, or using super rigid structures, that's a yellow flag — reframe and explain the reasoning so that the model understands why the thing you're asking for is important."

> "Rather than put in fiddly overfitty changes, or oppressively constrictive MUSTs, if there's some stubborn issue, you might try branching out and using different metaphors."

This is the anti-pattern to what we've been doing with our HARD GATE / CRITICAL / DO NOT SKIP language.

---

## Pattern 11: Skill vs Plugin — Two Primitives

| | Skill | Plugin |
|--|-------|--------|
| **Entry point** | `SKILL.md` | `.claude-plugin/plugin.json` |
| **Structure** | SKILL.md + optional dirs | Manifest + commands/ + agents/ + hooks/ + skills/ |
| **Capabilities** | Instructions only | Instructions + lifecycle hooks + MCP servers |
| **Lifecycle hooks** | No | Yes (PreToolUse, PostToolUse, Stop, etc.) |
| **Multiple commands** | No (single entry point) | Yes (commands/ directory) |
| **Agent definitions** | Inline or none | Separate files in agents/ |
| **Installation** | Copy to `~/.claude/skills/` | Copy to `~/.claude/plugins/` |

A skill is a set of instructions. A plugin is a skill plus live code execution.

---

## Pattern 12: `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}`

Every Anthropic plugin uses `${CLAUDE_PLUGIN_ROOT}` for internal path references. Every standalone skill uses paths relative to the skill directory. These built-in variables ensure portability — the skill works regardless of where it's installed.

**Never hardcode paths.** This is enforced across all 12+ skills.

---

## Appendix: Complexity Spectrum

Skills exist on a spectrum from simple instruction sets to full orchestration platforms:

```
Simple ←————————————————————————————————→ Complex

security-guidance    mcp-builder    feature-dev    plugin-dev
(1 hook script)      (SKILL.md +    (1 command +   (1 command +
                      references/)   3 agents)      3 agents +
                                                    7 sub-skills +
                                                    validation scripts)
```

The right complexity level depends on the task. Not every skill needs agents, scripts, or sub-skills. But every skill benefits from progressive contexting.
