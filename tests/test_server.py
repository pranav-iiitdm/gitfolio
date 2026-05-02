import json
import pytest
from unittest.mock import patch


def make_bullet(bullet_id="abc123", status="pending", tier=1):
    return {
        "id": bullet_id,
        "bullet": "Engineered auth system",
        "tier": tier,
        "flag_reason": None,
        "keywords": ["Python"],
        "score": 16,
        "status": status,
        "cluster": {"repo": "org/repo", "pr_title": "feat", "work_type": "feature", "merged_at": "2026-01-01"},
        "created_at": "2026-01-01",
    }


@pytest.fixture
def client(tmp_path):
    pending_path = str(tmp_path / "pending.json")
    with patch("gitfolio.pending_store.PENDING_PATH", pending_path):
        from gitfolio.server import create_app
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c, pending_path


def test_get_bullets_empty(client):
    c, _ = client
    res = c.get("/api/bullets")
    assert res.status_code == 200
    assert json.loads(res.data) == []


def test_get_bullets_returns_all(client):
    c, pending_path = client
    with open(pending_path, "w") as f:
        json.dump([make_bullet()], f)
    res = c.get("/api/bullets")
    data = json.loads(res.data)
    assert len(data) == 1
    assert data[0]["id"] == "abc123"


def test_patch_bullet_status(client):
    c, pending_path = client
    with open(pending_path, "w") as f:
        json.dump([make_bullet()], f)
    res = c.patch(
        "/api/bullets/abc123",
        data=json.dumps({"status": "approved"}),
        content_type="application/json",
    )
    assert res.status_code == 200
    assert json.loads(res.data)["ok"] is True


def test_patch_bullet_not_found(client):
    c, _ = client
    res = c.patch(
        "/api/bullets/nonexistent",
        data=json.dumps({"status": "approved"}),
        content_type="application/json",
    )
    assert res.status_code == 404


def test_push_with_no_approved_returns_400(client):
    c, _ = client
    res = c.post("/api/push")
    assert res.status_code == 400
