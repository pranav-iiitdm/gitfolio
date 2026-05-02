# gitfolio — Domain Knowledge

## What This Service Owns

- Fetching the authenticated user's GitHub activity (PRs + commits) across configured repos
- Scoring and prioritizing that activity by resume impact
- Generating ATS-optimized resume bullets via Claude AI
- Injecting bullets into a LaTeX resume file idempotently
- Sending a weekly digest email with the updated `.tex` attachment

## What It Does Not Own

- The LaTeX resume template (user-managed, typically on Overleaf)
- GitHub data beyond what the token can access
- Email infrastructure (delegates to Gmail SMTP via user-provided App Password)
- Storage of any data beyond `~/.gitfolio/` on the user's local machine

## Glossary

| Term | Meaning |
|------|---------|
| **Cluster** | Unit of work: either a merged PR (+ its commits) or a standalone commit not in any PR |
| **Score** | Float assigned to each cluster; drives tier assignment and sort order |
| **Tier 1** | High-confidence bullet, auto-included in resume |
| **Tier 2** | Good bullet missing a metric; flagged in email for user to fill in |
| **Tier 3** | Skipped; too low signal (score < 3) or generation failed |
| **XYZ format** | Resume bullet format: "Accomplished X by doing Y, resulting in Z" |
| **Backfill** | Sync mode covering last 12 months instead of since last sync |
| **Dry run** | Preview mode: generate bullets but write nothing to disk and send no email |
| **Markers** | `% gitfolio:start` / `% gitfolio:end` comments in `.tex` that bound the injected block |

## Core Pipeline

```
GitHub API
  → GitHubAnalyzer.fetch()
    → _fetch_pr_clusters()       # merged PRs authored by user
    → _fetch_standalone_commits()# commits not in any PR, cap 30
  → Scorer.score() per cluster
  → sort by score descending

BulletGenerator.generate()
  → skip tier 3 (score < 3)
  → Claude API (claude-3-haiku) per cluster
  → returns {bullet, tier, flag_reason, keywords}

ResumeUpdater.inject()
  → read .tex file
  → replace or insert gitfolio marker block
  → return (updated_tex, diff_summary)

Emailer.send()
  → Gmail SMTP SSL port 465
  → attach updated .tex as resume_updated_YYYYMMDD.tex
```

## Scoring Model (scorer.py)

| Dimension | Points |
|-----------|--------|
| Work type (feature=10, migration=8, integration=8, performance=9, refactor=7, bugfix=5, testing=4, infra=4, config=2, chore=1) | 1–10 |
| Files changed (≥10→5, ≥5→3, ≥2→1) | 0–5 |
| Lines added (≥300→3, ≥100→2, ≥30→1) | 0–3 |
| PR body length > 100 chars | +2 |
| PR body contains impact keywords | +2 |
| Cluster type == "pr" | +3 |
| Reviews given > 0 | +1 |
| Skip keyword in title (wip, typo, bump, etc.) | −8 |

Score floor = 0. Tier 3 if score < 3.

## Claude Integration (bullet_generator.py)

- Model: `claude-3-haiku-20240307` (**outdated** — upgrade to `claude-haiku-4-5-20251001`)
- System prompt: instructs XYZ format, JSON-only response, no invented details
- Response schema: `{bullet: str, tier: 1|2, flag_reason: str|null, keywords: [str]}`
- Input: target role, repo name, work type, PR title/body, commit messages, diff sample (3 files × 1500 chars)
- No prompt caching — system prompt sent every call (optimization opportunity)

## LaTeX Resume Injection (resume_updater.py)

Injection is idempotent:
- If markers exist → replace the block between them
- If no markers → find `\section{\textbf{Experience}}` then `\resumeSubHeadingListStart`, inject after it
- Fallback: inject before `\end{document}`

Hardcoded pattern assumes Overleaf `\textbf{Experience}` section name. Different templates will need `EXPERIENCE_SECTION_PATTERN` updated.

## Email Format (emailer.py)

- Subject: `gitfolio weekly digest — {Month DD, YYYY}`
- Body: plain text with SUMMARY / ACTION NEEDED / SKIPPED sections
- Attachment: `resume_updated_YYYYMMDD.tex` (base64 encoded)
- Transport: Gmail SMTP SSL on port 465

## External Dependencies

| Dep | Purpose |
|-----|---------|
| `click>=8.1.0` | CLI framework |
| `PyGithub>=2.1.0` | GitHub REST API client |
| `anthropic>=0.25.0` | Claude API client |
| `PyYAML>=6.0` | Config file parsing |

## GitHub API Access Pattern

- Auth: `Auth.Token` (PAT with `repo` scope)
- PR fetch: `get_pulls(state="closed", sort="updated", direction="desc")` — breaks early once past time window
- Each matched PR: 1 call for commits + 1 call for files (intentional, acceptable N+1)
- Standalone commits: `get_commits(since=..., author=email)` — cap 30, triggers lazy file/stats fetch per commit
- User login cached after first fetch to avoid repeated `/user` calls

## Operational Constraints

- Requires `ANTHROPIC_API_KEY` env var at runtime
- Config stored locally at `~/.gitfolio/` — never inside repo
- `.env` in repo root **must not be committed** (contains live key)
- Weekly cron recommended: `0 9 * * 0 ANTHROPIC_API_KEY=... gitfolio sync`
- Python 3.11+ required
