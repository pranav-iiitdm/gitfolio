# gitfolio

> Turn your GitHub commits into ATS-friendly resume bullets. Automatically. Every week.

---

## The Problem

You ship features every day. You close PRs, review code, fix bugs, build systems. None of it shows up on your resume because it's all in private repos and you're too busy shipping to write about it.

**gitfolio fixes that.**

It reads your commits and PRs (including private repos), uses Claude AI to analyze the actual diffs, and generates polished XYZ-format resume bullets. Every week it emails you the updated `.tex` file — you review, upload to Overleaf, done.

---

## How It Works

```
GitHub (private + public repos)
        ↓
Fetch commits + diffs + PRs
        ↓
Score & prioritize by impact
        ↓
Claude AI → XYZ format resume bullets
        ↓
Inject into your LaTeX resume
        ↓
Email digest + updated .tex file → you review → upload to Overleaf
```

---

## Install

```bash
pip install gitfolio
```

Or via Homebrew tap (coming soon):
```bash
brew install pranav-iiitdm/tap/gitfolio
```

---

## Setup

### 1. Get a GitHub token
Go to [github.com/settings/tokens](https://github.com/settings/tokens) → New token → select `repo` scope.

### 2. Get an Anthropic API key
Sign up at [console.anthropic.com](https://console.anthropic.com) and create an API key.

### 3. Set your API key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 4. Run setup
```bash
gitfolio init
```

This walks you through setting up your GitHub token, repos, email, and resume path.

---

## Usage

### First run (backfill last 12 months)
```bash
gitfolio sync --backfill
```

### Preview without sending email
```bash
gitfolio sync --dry-run
```

### Weekly sync
```bash
gitfolio sync
```

### Check everything is working
```bash
gitfolio doctor
```

---

## Set Up Weekly Cron

```bash
# Open crontab
crontab -e

# Add this line — runs every Sunday at 9am
0 9 * * 0 ANTHROPIC_API_KEY=sk-ant-... gitfolio sync
```

---

## What You Get in Your Weekly Email

```
gitfolio weekly digest — March 08, 2026
==================================================

SUMMARY
-------
Added 3 bullet(s) ready to use.
Flagged 1 bullet(s) needing your input.

✅ Ready bullets:
  • Implemented JWT-based authentication system with refresh token
    flow and middleware, reducing session-related support tickets
    across the platform
  • Migrated legacy REST endpoints to GraphQL, improving API
    response consistency for mobile clients

⚠️  Needs your input:
  • Optimized database query layer for user feed service,
    reducing load time by [METRIC: add latency improvement here]
  → Do you know the before/after query time for this change?

SKIPPED (14 items)
-------
These were too small to include:
  • fix typo in README
  • bump lodash version
  ...

==================================================
The updated resume .tex file is attached.
Review it, upload to Overleaf, and you're done.
```

---

## How Bullets Are Prioritized

Every commit/PR cluster is scored across 5 dimensions:

| Signal | What it looks at |
|--------|-----------------|
| Work type | Feature > Perf > Migration > Refactor > Bugfix > Chore |
| Scope | Files changed, lines added |
| Business context | PR description quality, impact keywords |
| Your involvement | Author vs reviewer |
| Skip signals | WIP, typo, dependency bump, etc. |

**Tier 1** — strong signal, written directly into resume  
**Tier 2** — good work but needs a metric from you (flagged in email)  
**Tier 3** — skipped (mentioned in summary only)

---

## Privacy

- Your code diffs are sent to the Anthropic API for analysis
- No data is stored anywhere outside your machine and Anthropic's API
- Only your own commits (filtered by your git email) are analyzed
- You can use `PR titles + commit messages only` mode if you prefer (set `diff_access: false` in config)

---

## Requirements

- Python 3.11+
- GitHub Personal Access Token (`repo` scope)
- Anthropic API key
- Gmail account with App Password (for sending digest)
- A `.tex` resume (Overleaf format works perfectly)

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT
