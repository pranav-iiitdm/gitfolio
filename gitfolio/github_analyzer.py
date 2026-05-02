import time
from github import Github, Auth
from datetime import datetime, timedelta, timezone
from gitfolio.config import Config
from gitfolio.scorer import Scorer


def _with_retry(fn, retries: int = 3, backoff: int = 2):
    last_exc = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if "rate limit" in str(e).lower() or "429" in str(e):
                if attempt < retries - 1:
                    sleep_time = backoff ** attempt
                    print(f"   Rate limited. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
            raise
    raise last_exc


class GitHubAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.g = Github(auth=Auth.Token(config["github_token"]))
        self.author_email = config["author_email"]
        self.repos = config["repos"]
        self.diff_access = config.get("diff_access", True)
        self.scorer = Scorer()
        self._user_login = None  # Cached login
        self._default_branches: dict[str, str] = {}  # Cached default branch per repo

    def _get_user_login(self) -> str:
        """Fetch and cache the authenticated user's GitHub login."""
        if self._user_login is None:
            try:
                self._user_login = self.g.get_user().login
            except Exception:
                self._user_login = ""
        return self._user_login

    def _get_default_branch(self, repo) -> str:
        """Return the repo's default branch (main/master), cached per repo."""
        if repo.full_name not in self._default_branches:
            self._default_branches[repo.full_name] = repo.default_branch or "main"
        return self._default_branches[repo.full_name]

    def fetch(self, backfill: bool = False) -> list[dict]:
        """
        Fetch and cluster commits/PRs from configured repos.
        backfill=True → last 12 months
        backfill=False → since last sync (or last 7 days)
        """
        if backfill:
            since = datetime.now(timezone.utc) - timedelta(days=365)
        else:
            last_sync = Config.get_last_sync()
            if last_sync:
                since = datetime.fromisoformat(last_sync).replace(tzinfo=timezone.utc)
            else:
                since = datetime.now(timezone.utc) - timedelta(days=7)

        clusters = []

        for repo_name in self.repos:
            repo = self.g.get_repo(repo_name)
            print(f"   Scanning {repo_name}...")

            pr_clusters = self._fetch_pr_clusters(repo, since)
            clusters.extend(pr_clusters)
            print(f"   Found {len(pr_clusters)} matching PR(s).")

            pr_commit_shas = {
                commit["sha"]
                for c in pr_clusters
                for commit in c.get("commits", [])
            }

            standalone = self._fetch_standalone_commits(repo, since, pr_commit_shas)
            clusters.extend(standalone)
            print(f"   Found {len(standalone)} standalone commit(s).")

        # Score and sort
        for cluster in clusters:
            cluster["score"] = self.scorer.score(cluster)

        clusters.sort(key=lambda x: x["score"], reverse=True)
        return clusters

    def _fetch_pr_clusters(self, repo, since: datetime) -> list[dict]:
        """
        Fetch merged PRs authored by the user in the given time window.
        Uses only attributes present in the list payload to avoid N+1 API calls.
        """
        clusters = []
        user_login = self._get_user_login()
        default_branch = self._get_default_branch(repo)
        print(f"   Default branch: {default_branch}")

        try:
            pulls = _with_retry(lambda: repo.get_pulls(state="closed", sort="updated", direction="desc", base=default_branch))
            matched = 0
            for i, pr in enumerate(pulls):
                if i % 100 == 0 and i > 0:
                    print(f"   ... scanned {i} PRs, found {matched} matches so far.")

                # All fields below are in the list response payload — no extra API call
                if not pr.merged_at:
                    continue
                if pr.merged_at.replace(tzinfo=timezone.utc) < since:
                    break  # PRs are sorted by updated desc, once past window we can stop

                if pr.user.login != user_login:
                    continue

                matched += 1

                # Fetch commits (1 API call per matched PR — acceptable)
                commits_data = []
                try:
                    for commit in pr.get_commits():
                        commits_data.append({
                            "sha": commit.sha,
                            "message": commit.commit.message,
                            "date": commit.commit.author.date.isoformat(),
                        })
                except Exception:
                    pass

                # Fetch PR-level file diffs (skipped if diff_access is False)
                diff_sample = []
                if self.diff_access:
                    try:
                        for f in pr.get_files():
                            if f.patch and len(diff_sample) < 3:
                                diff_sample.append({
                                    "filename": f.filename,
                                    "patch": f.patch[:3000],
                                    "additions": f.additions,
                                    "deletions": f.deletions,
                                })
                            if len(diff_sample) >= 3:
                                break
                    except Exception:
                        pass

                clusters.append({
                    "type": "pr",
                    "repo": repo.full_name,
                    "pr_title": pr.title,
                    "pr_body": (pr.body or "")[:1000],
                    "pr_number": pr.number,
                    "merged_at": pr.merged_at.isoformat(),
                    "commits": commits_data,
                    "diff_sample": diff_sample,
                    "files_changed": len(diff_sample),
                    "additions": sum(f.get("additions", 0) for f in diff_sample),
                    "deletions": sum(f.get("deletions", 0) for f in diff_sample),
                    "reviews_given": 0,
                })

        except Exception as e:
            print(f"   Warning: Could not fetch PRs for {repo.full_name}: {e}")

        return clusters

    def _fetch_standalone_commits(self, repo, since: datetime, exclude_shas: set) -> list[dict]:
        """
        Fetch direct commits not tied to any PR.
        Limits to 30 commits max to keep sync fast.
        """
        clusters = []
        try:
            default_branch = self._get_default_branch(repo)
            commits = repo.get_commits(since=since, author=self.author_email, sha=default_branch)
            count = 0
            for commit in commits:
                if count >= 30:
                    break
                if commit.sha in exclude_shas:
                    continue
                count += 1

                diff_sample = []
                additions, deletions = 0, 0
                if self.diff_access:
                    try:
                        for f in commit.files:
                            if f.patch and len(diff_sample) < 3:
                                diff_sample.append({
                                    "filename": f.filename,
                                    "patch": f.patch[:3000],
                                    "additions": f.additions,
                                    "deletions": f.deletions,
                                })
                            if len(diff_sample) >= 3:
                                break
                        additions = commit.stats.additions
                        deletions = commit.stats.deletions
                    except Exception:
                        pass

                clusters.append({
                    "type": "commit",
                    "repo": repo.full_name,
                    "pr_title": commit.commit.message.split("\n")[0],
                    "pr_body": "",
                    "merged_at": commit.commit.author.date.isoformat(),
                    "commits": [{
                        "sha": commit.sha,
                        "message": commit.commit.message,
                        "date": commit.commit.author.date.isoformat(),
                    }],
                    "diff_sample": diff_sample,
                    "files_changed": len(diff_sample),
                    "additions": additions,
                    "deletions": deletions,
                    "reviews_given": 0,
                })
        except Exception as e:
            print(f"   Warning: Could not fetch commits for {repo.full_name}: {e}")

        return clusters
