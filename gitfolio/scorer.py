import re


WORK_TYPE_SCORES = {
    "feature": 10,
    "performance": 9,
    "refactor": 7,
    "migration": 8,
    "integration": 8,
    "bugfix": 5,
    "testing": 4,
    "infra": 4,
    "config": 2,
    "chore": 1,
    "docs": 1,
}

IMPACT_KEYWORDS = [
    "improve", "reduce", "optimize", "increase", "decrease",
    "implement", "design", "architect", "integrate", "migrate",
    "launch", "ship", "deploy", "scale", "refactor", "build",
    "create", "develop", "introduce", "add", "enhance",
]

SKIP_KEYWORDS = [
    "wip", "fixup", "typo", "merge branch", "bump version",
    "update dependency", "update deps", "update packages",
    "lint", "format", "whitespace", ".gitignore",
]


class Scorer:
    def score(self, cluster: dict) -> float:
        score = 0.0

        # 1. Work type signal
        work_type = self._detect_work_type(cluster)
        cluster["work_type"] = work_type
        score += WORK_TYPE_SCORES.get(work_type, 3)

        # 2. Scope of change
        files = cluster.get("files_changed", 0)
        additions = cluster.get("additions", 0)
        if files >= 10:
            score += 5
        elif files >= 5:
            score += 3
        elif files >= 2:
            score += 1

        if additions >= 300:
            score += 3
        elif additions >= 100:
            score += 2
        elif additions >= 30:
            score += 1

        # 3. PR description quality (has business context)
        pr_body = cluster.get("pr_body", "")
        if len(pr_body) > 100:
            score += 2
        if any(kw in pr_body.lower() for kw in IMPACT_KEYWORDS):
            score += 2

        # 4. Authored vs reviewed
        if cluster.get("type") == "pr":
            score += 3
        if cluster.get("reviews_given", 0) > 0:
            score += 1

        # 5. Skip signal penalty
        title = cluster.get("pr_title", "").lower()
        if any(kw in title for kw in SKIP_KEYWORDS):
            score -= 8

        return max(score, 0)

    def _detect_work_type(self, cluster: dict) -> str:
        text = (
            cluster.get("pr_title", "") + " " +
            cluster.get("pr_body", "") + " " +
            " ".join(c.get("message", "") for c in cluster.get("commits", []))
        ).lower()

        filenames = " ".join(
            f.get("filename", "") for f in cluster.get("diff_sample", [])
        ).lower()

        if any(w in text for w in ["feat", "feature", "add", "implement", "introduce", "new"]):
            return "feature"
        if any(w in text for w in ["perf", "performance", "optim", "speed", "latency", "cache"]):
            return "performance"
        if any(w in text for w in ["migrat", "upgrade", "move from", "replace"]):
            return "migration"
        if any(w in text for w in ["integrat", "connect", "api", "webhook", "third-party"]):
            return "integration"
        if any(w in text for w in ["refactor", "restructure", "clean", "reorganize"]):
            return "refactor"
        if any(w in text for w in ["fix", "bug", "patch", "resolve", "hotfix"]):
            return "bugfix"
        if any(w in text for w in ["test", "spec", "coverage", "unit", "integration test"]):
            return "testing"
        if any(w in filenames for w in [".yaml", ".yml", "dockerfile", "terraform", "ci", ".sh"]):
            return "infra"
        if any(w in text for w in ["config", "env", "setting", "setup"]):
            return "config"
        if any(w in text for w in ["doc", "readme", "comment", "changelog"]):
            return "docs"
        return "chore"
