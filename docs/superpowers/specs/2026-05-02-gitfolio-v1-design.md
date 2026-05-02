# gitfolio v1.0 — Design Spec

**Date:** 2026-05-02  
**Language:** Python (Go rewrite deferred to v2.0)  
**Goal:** Polish, complete review flow, and ship via own Homebrew tap + PyPI

---

## 1. Architecture

### Pending Bullets Store

Introduce `~/.gitfolio/pending.json` as a queue between generation and injection. This decouples `sync` from `inject`, enabling the review flow.

```
fetch → score → generate → pending.json → review (CLI or web) → inject → email
```

**New commands:**

| Command | Behavior |
|---------|----------|
| `gitfolio sync` | fetch + generate + save to `pending.json` (no inject) |
| `gitfolio sync --auto` | old behavior — generate + inject + email in one shot (use in cron) |
| `gitfolio review` | CLI review: approve/edit/skip/delete bullets |
| `gitfolio serve` | local web UI for same review flow |
| `gitfolio push` | inject approved bullets from pending + send email |

**New module:** `gitfolio/pending_store.py` — read/write/clear `pending.json`.

Bullet state in `pending.json`: `pending | approved | skipped | deleted`.

All existing modules (`github_analyzer`, `scorer`, `bullet_generator`, `resume_updater`, `emailer`, `config`) keep their current interfaces unchanged.

---

## 2. Security

### `.gitignore`
Add to repo root:
```
.env
venv/
__pycache__/
*.egg-info/
dist/
build/
.DS_Store
*.pyc
```

### Secrets handling
- `ANTHROPIC_API_KEY` — env var only, never in `config.yaml`. `doctor` warns if key found in config file.
- `Config.save()` sets file mode `0o600` on write.
- `gitfolio init` prints one-time warning about protecting `config.yaml` (contains GitHub token).

### Diff privacy mode
`diff_access: false` in config → skip `pr.get_files()` and `commit.files` entirely. Use PR title + commit messages only for bullet generation. Add `diff_access` prompt to `gitfolio init`.

---

## 3. Model Upgrade + Prompt Caching

**Model:** `claude-3-haiku-20240307` → `claude-haiku-4-5-20251001`

**Prompt caching** in `bullet_generator.py`:
```python
message = self.client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1000,
    system=[{
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"}
    }],
    messages=[{"role": "user", "content": prompt}],
)
```

Cache TTL is 5 minutes — all clusters in a single sync share the cache hit. Estimated savings: ~85% on system prompt tokens per sync.

**Model config override** in `config.yaml`:
```yaml
model: "claude-haiku-4-5-20251001"   # optional, this is the default
```

---

## 4. CLI Review (`gitfolio review`)

Reads bullets from `~/.gitfolio/pending.json`. Interactive terminal flow:

```
─────────────────────────────────────────
[1/5] org/repo · feature · score 18
PR: Implement JWT authentication with refresh token flow

  Engineered JWT-based authentication system with refresh token
  rotation and middleware, reducing session-related support
  tickets across the platform

  Keywords: JWT, authentication, middleware, Python
  ⚠️  Tier 2 — missing metric: what was the ticket reduction %?

[a]pprove  [e]dit  [s]kip  [d]elete  [q]uit
─────────────────────────────────────────
```

**Actions:**

| Key | Behavior |
|-----|----------|
| `a` | Mark approved, next bullet |
| `e` | Open bullet text in `$EDITOR` or inline prompt |
| `s` | Skip — keep in pending for later |
| `d` | Delete — remove permanently |
| `q` | Quit — save progress, resume later |

**Flags:**
- `gitfolio review --push` — inject + send email immediately after review session ends

---

## 5. Web UI (`gitfolio serve`)

Local Flask server. Opens browser automatically on `localhost:7842`.

**Stack:** Flask + single `index.html` with vanilla JS (no build step — critical for Homebrew compatibility).

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  gitfolio                        [Push to resume →]  │
├──────────┬──────────────────────────┬───────────────┤
│ PENDING  │                          │  APPROVED     │
│ ──────── │   <bullet detail +       │  ──────────── │
│ • JWT    │    edit panel>           │  • GraphQL    │
│ • Perf   │                          │  • DB optim   │
│ • Feed   │   [Edit]  [Approve ✓]    │               │
│          │   [Skip]  [Delete]       │  SKIPPED      │
│          │                          │  ──────────── │
└──────────┴──────────────────────────┴───────────────┘
```

**New module:** `gitfolio/server.py` — Flask app.

**Bullet ID:** SHA256 of `repo + pr_title + merged_at` — stable across reloads, stored in `pending.json`.

**Routes:**
| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Serve `index.html` |
| `/api/bullets` | GET | Return all bullets from `pending.json` |
| `/api/bullets/<id>` | PATCH | Update bullet `status` and/or `bullet` text |
| `/api/push` | POST | Trigger inject + email (no-op if 0 approved bullets) |

**Flags:**
- `gitfolio serve --port 8080` — override default port
- No auth — binds to `127.0.0.1` only, never `0.0.0.0`

**New dependency:** `flask>=3.0` added to `install_requires` in `setup.py`.

---

## 6. Distribution

### GitHub Repo
- Add `.gitignore`, confirm `LICENSE` (MIT), add `CONTRIBUTING.md`
- Tagged releases trigger `release.yml` → PyPI publish (already working)

### Homebrew Own Tap
New repo: `github.com/venkatasai/homebrew-tap`

Formula uses `Language::Python::Virtualenv`:
```ruby
class Gitfolio < Formula
  include Language::Python::Virtualenv
  desc "Auto-generate ATS-friendly resume bullets from GitHub commits"
  homepage "https://github.com/venkatasai/gitfolio"
  url "https://files.pythonhosted.org/packages/.../gitfolio-1.0.0.tar.gz"
  sha256 "..."
  license "MIT"
  depends_on "python@3.11"
  # resource blocks for each dependency
  def install
    virtualenv_install_with_resources
  end
end
```

Install: `brew tap venkatasai/tap && brew install gitfolio`

### Auto-update tap on release
`release.yml` additions:
- After PyPI publish: update SHA256 + URL in `homebrew-tap` repo via `gh` API
- Keeps formula in sync on every tagged release automatically

### README badges
```
brew install · PyPI · Python 3.11+ · MIT
```

---

## 7. Error Handling Improvements

- Wrap all GitHub API calls with specific error messages (rate limit, auth failure, repo not found)
- Wrap Claude API calls: surface quota errors, invalid key, model not available
- `gitfolio doctor` additions: check `pending.json` state, warn if bullets stuck in pending > 7 days
- Retry logic: 3 attempts with exponential backoff on GitHub API rate limit (429)

---

## Out of Scope (v1.0)

- Go rewrite (deferred to v2.0)
- `homebrew-core` submission (requires 30+ stars, post-launch)
- Multiple email providers beyond Gmail
- Web UI auth
- Metrics tracking / analytics
