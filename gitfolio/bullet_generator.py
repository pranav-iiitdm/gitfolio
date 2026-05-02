import os
import json
import anthropic

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are an expert resume writer specializing in ATS-optimized software engineering resumes.

Your job is to convert raw GitHub commit/PR data into concise, impactful resume bullet points.

Rules:
- Use the XYZ format: "Accomplished X by doing Y, resulting in Z"
- Start with a strong action verb (Implemented, Designed, Engineered, Optimized, Developed, Architected, Refactored, Integrated, Migrated, Built)
- Include tech stack keywords naturally (important for ATS)
- Be specific about what was built — name the system, service, or feature
- If you can infer a metric from the diff (e.g., reduced DB calls, added caching), include it
- If no metric can be inferred, leave a placeholder: [METRIC: add impact here]
- Keep bullets to 1-2 lines max
- Do NOT invent details not present in the data
- Respond ONLY with a valid JSON object, no preamble, no markdown fences

Response format:
{
  "bullet": "The resume bullet text",
  "tier": 1 or 2,
  "flag_reason": "null or a question for the user about missing metrics",
  "keywords": ["list", "of", "ATS", "keywords", "used"]
}

Tier 1 = strong bullet, ready to include
Tier 2 = good bullet but missing a metric or context — flag it
"""


class BulletGenerator:
    def __init__(self, config: dict):
        self.config = config
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self.target_role = config.get("target_role", "SDE")
        self.model = config.get("model", DEFAULT_MODEL)

    def generate(self, clusters: list[dict]) -> list[dict]:
        results = []

        for cluster in clusters:
            score = cluster.get("score", 0)

            if score < 3:
                results.append({
                    "tier": 3,
                    "bullet": None,
                    "flag_reason": None,
                    "keywords": [],
                    "cluster": cluster,
                    "score": score,
                })
                continue

            try:
                result = self._generate_bullet(cluster)
                result["cluster"] = cluster
                result["score"] = score
                results.append(result)
            except Exception as e:
                print(f"   Warning: Failed to generate bullet for '{cluster.get('pr_title')}': {e}")
                results.append({
                    "tier": 3,
                    "bullet": None,
                    "flag_reason": f"Generation failed: {e}",
                    "keywords": [],
                    "cluster": cluster,
                    "score": score,
                })

        return results

    def _generate_bullet(self, cluster: dict) -> dict:
        prompt = self._build_prompt(cluster)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    def _build_prompt(self, cluster: dict) -> str:
        diff_text = ""
        for f in cluster.get("diff_sample", [])[:3]:
            diff_text += f"\nFile: {f['filename']} (+{f['additions']} -{f['deletions']})\n"
            diff_text += f.get("patch", "")[:1500] + "\n"

        commit_messages = "\n".join(
            f"- {c['message'].split(chr(10))[0]}"
            for c in cluster.get("commits", [])[:10]
        )

        return f"""Target role: {self.target_role}
Repo: {cluster.get('repo')}
Work type: {cluster.get('work_type', 'unknown')}

PR/Commit title: {cluster.get('pr_title')}
PR description: {cluster.get('pr_body', 'N/A')}

Commit messages:
{commit_messages}

Files changed: {cluster.get('files_changed', 0)} files, +{cluster.get('additions', 0)} -{cluster.get('deletions', 0)} lines

Diff sample:
{diff_text if diff_text else 'Not available'}

Generate a single resume bullet for this work."""
