import json
import os
import hashlib
from datetime import datetime

PENDING_PATH = os.path.expanduser("~/.gitfolio/pending.json")


class PendingStore:
    def save(self, results: list[dict]) -> None:
        bullets = []
        for r in results:
            cluster = r.get("cluster", {})
            bullets.append({
                "id": self._make_id(cluster),
                "bullet": r.get("bullet"),
                "tier": r.get("tier"),
                "flag_reason": r.get("flag_reason"),
                "keywords": r.get("keywords", []),
                "score": r.get("score", 0),
                "status": "pending",
                "cluster": cluster,
                "created_at": datetime.utcnow().isoformat(),
            })
        os.makedirs(os.path.dirname(PENDING_PATH), exist_ok=True)
        self._write(bullets)

    def load(self) -> list[dict]:
        if not os.path.exists(PENDING_PATH):
            return []
        with open(PENDING_PATH, "r") as f:
            return json.load(f)

    def update(self, bullet_id: str, status: str = None, bullet_text: str = None) -> bool:
        bullets = self.load()
        for b in bullets:
            if b["id"] == bullet_id:
                if status is not None:
                    b["status"] = status
                if bullet_text is not None:
                    b["bullet"] = bullet_text
                self._write(bullets)
                return True
        return False

    def get_approved(self) -> list[dict]:
        return [b for b in self.load() if b["status"] == "approved"]

    def clear(self) -> None:
        if os.path.exists(PENDING_PATH):
            os.remove(PENDING_PATH)

    def _make_id(self, cluster: dict) -> str:
        key = f"{cluster.get('repo','')}{cluster.get('pr_title','')}{cluster.get('merged_at','')}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def _write(self, bullets: list[dict]) -> None:
        with open(PENDING_PATH, "w") as f:
            json.dump(bullets, f, indent=2)
