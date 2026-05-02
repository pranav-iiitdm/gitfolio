import re
import os
from datetime import datetime


# Marker comments injected into the .tex file to track gitfolio bullets
GITFOLIO_START = "% gitfolio:start"
GITFOLIO_END = "% gitfolio:end"

# The section in your resume where work experience bullets go
EXPERIENCE_SECTION_PATTERN = r"\\section\{\\textbf\{Experience\}\}"


class ResumeUpdater:
    def __init__(self, config: dict):
        self.resume_path = config["resume_path"]

    def inject(self, results: list[dict]) -> tuple[str, str]:
        """
        Inject new bullets into the LaTeX resume.
        Returns (updated_tex_content, diff_summary).
        """
        with open(self.resume_path, "r") as f:
            tex = f.read()

        new_bullets = [
            r for r in results
            if r.get("bullet") and r.get("tier") in [1, 2]
        ]

        if not new_bullets:
            return tex, "No new bullets to add this week."

        # Build the new bullet block
        bullet_block = self._build_bullet_block(new_bullets)

        # Check if gitfolio section already exists
        if GITFOLIO_START in tex:
            # Replace existing gitfolio block
            pattern = re.compile(
                rf"{re.escape(GITFOLIO_START)}.*?{re.escape(GITFOLIO_END)}",
                re.DOTALL
            )
            existing = pattern.search(tex)
            existing_bullets = existing.group(0) if existing else ""
            updated_tex = pattern.sub(bullet_block, tex)
        else:
            # First time — inject after \section{Experience} heading
            inject_point = self._find_inject_point(tex)
            if inject_point == -1:
                # Fallback: inject before \end{document}
                inject_point = tex.rfind(r"\end{document}")

            updated_tex = tex[:inject_point] + "\n" + bullet_block + "\n" + tex[inject_point:]

        diff_summary = self._build_diff_summary(new_bullets)
        return updated_tex, diff_summary

    def _find_inject_point(self, tex: str) -> int:
        """Find position right after the Experience section heading."""
        match = re.search(EXPERIENCE_SECTION_PATTERN, tex)
        if match:
            # Find the \resumeSubHeadingListStart after it
            after = tex[match.end():]
            sub = after.find(r"\resumeSubHeadingListStart")
            if sub != -1:
                return match.end() + sub + len(r"\resumeSubHeadingListStart")
        return -1

    def _build_bullet_block(self, results: list[dict]) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        lines = [f"{GITFOLIO_START} — last updated {date_str}"]
        lines.append("")
        lines.append(r"    % ── gitfolio auto-generated bullets ──")

        # Group by repo
        by_repo = {}
        for r in results:
            repo = r.get("cluster", {}).get("repo", "Unknown")
            by_repo.setdefault(repo, []).append(r)

        for repo, repo_results in by_repo.items():
            lines.append(f"    % Repo: {repo}")
            for r in repo_results:
                bullet = r["bullet"]
                tier = r["tier"]
                flag = ""
                if tier == 2 and r.get("flag_reason"):
                    flag = f"  % ⚠️ {r['flag_reason']}"
                lines.append(f"        \\item {{{bullet}}}{flag}")

        lines.append("")
        lines.append(GITFOLIO_END)
        return "\n".join(lines)

    def _build_diff_summary(self, results: list[dict]) -> str:
        tier1 = [r for r in results if r["tier"] == 1]
        tier2 = [r for r in results if r["tier"] == 2]

        lines = [
            f"Added {len(tier1)} bullet(s) ready to use.",
            f"Flagged {len(tier2)} bullet(s) needing your input.",
            "",
        ]

        if tier1:
            lines.append("✅ Ready bullets:")
            for r in tier1:
                lines.append(f"  • {r['bullet']}")
            lines.append("")

        if tier2:
            lines.append("⚠️  Needs your input:")
            for r in tier2:
                lines.append(f"  • {r['bullet']}")
                if r.get("flag_reason"):
                    lines.append(f"    → {r['flag_reason']}")
            lines.append("")

        return "\n".join(lines)
