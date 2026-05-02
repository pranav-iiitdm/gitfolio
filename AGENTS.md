# gitfolio — Agent Context

## What This Repo Is

`gitfolio` is a Python CLI tool that reads a developer's GitHub commits and PRs (including private repos), uses Claude AI to generate ATS-friendly XYZ-format resume bullets, injects them into a LaTeX `.tex` resume, and emails a weekly digest.

**PyPI package:** `gitfolio`  
**Entry point:** `gitfolio.cli:main` (Click CLI)  
**Author:** Pranav Parimi  
**Version:** 0.1.0

## Context Read Order

1. This file (`AGENTS.md`) — architecture and rules
2. `KNOWLEDGE.md` — domain model, workflows, invariants
3. Module source files for implementation details

## Commands

```bash
# Install
pip install -e .

# Run CLI
gitfolio init               # Interactive setup → ~/.gitfolio/config.yaml
gitfolio sync               # Weekly sync (since last sync, or last 7 days)
gitfolio sync --backfill    # Scan last 12 months
gitfolio sync --dry-run     # Preview bullets, no file/email changes
gitfolio doctor             # Validate config, GitHub, Anthropic, resume path

# Build for PyPI
pip install build twine
python -m build
twine upload dist/*

# No test suite exists yet
```

## Module Map

| File | Responsibility |
|------|---------------|
| `gitfolio/cli.py` | Click CLI commands: `init`, `sync`, `doctor` |
| `gitfolio/config.py` | Load/save config from `~/.gitfolio/config.yaml`, track last sync |
| `gitfolio/github_analyzer.py` | Fetch merged PRs and standalone commits via PyGithub; produce "clusters" |
| `gitfolio/scorer.py` | Score clusters by work type, scope, PR quality, skip signals |
| `gitfolio/bullet_generator.py` | Call Claude API to convert clusters → JSON resume bullets |
| `gitfolio/resume_updater.py` | Inject bullets into LaTeX `.tex` using `% gitfolio:start/end` markers |
| `gitfolio/emailer.py` | Send digest email with attached `.tex` via Gmail SMTP SSL |
| `setup.py` | Package metadata and dependencies |
| `config.yaml.example` | User-facing config template |

## Runtime Config

- Config file: `~/.gitfolio/config.yaml`
- Last sync timestamp: `~/.gitfolio/last_sync.txt`
- Required env var: `ANTHROPIC_API_KEY`

## Non-Negotiable Rules

1. **Never commit `.env`** — it contains a live Anthropic API key. Add to `.gitignore` immediately.
2. **Never modify `.tex` outside the `% gitfolio:start` / `% gitfolio:end` marker block** — users edit the rest manually.
3. **Never invent resume metrics** — if no metric is inferable, emit `[METRIC: add impact here]` placeholder and set `tier: 2`.
4. **Config at `~/.gitfolio/`** — never store config inside the repo directory.
5. **Diff access is optional** — `diff_access: false` in config must skip diff fetching and generation entirely.

## Durable Architectural Decisions

- **Cluster model**: a "cluster" is either a merged PR (with its commits) or a standalone commit not attached to any PR. All downstream processing operates on clusters, not raw commits.
- **Tier system**: Tier 1 = ready bullet, Tier 2 = needs user metric, Tier 3 = skipped (score < 3 or generation failed). Tier 3 bullets are never injected into the resume.
- **LaTeX injection**: bullets inject into the first `\resumeSubHeadingListStart` after `\section{\textbf{Experience}}`, or before `\end{document}` as fallback. Idempotent via marker replacement.
- **PR cap**: standalone commits capped at 30 per repo to keep sync fast. PR diffs capped at 3 files × 3000 chars each.
- **Score threshold**: clusters scoring < 3 bypass Claude entirely (Tier 3 directly).

## Current Tech Debt / Known Issues

- `bullet_generator.py` uses `claude-3-haiku-20240307` — outdated, should upgrade to `claude-haiku-4-5-20251001`.
- No prompt caching on Claude calls — wasteful for the system prompt (repeated every call).
- No tests exist.
- `.env` file committed with live API key (security issue).
- `resume_updater.py` hardcodes `EXPERIENCE_SECTION_PATTERN` for one specific LaTeX template format.
