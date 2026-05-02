import json
import os
import pytest
from unittest.mock import patch
from gitfolio.pending_store import PendingStore


def make_result(pr_title="feat: add auth", repo="org/repo", tier=1, score=16):
    return {
        "tier": tier,
        "bullet": "Engineered JWT authentication system",
        "flag_reason": None,
        "keywords": ["JWT", "Python"],
        "score": score,
        "cluster": {
            "repo": repo,
            "pr_title": pr_title,
            "merged_at": "2026-01-15T10:00:00",
            "work_type": "feature",
            "type": "pr",
        },
    }


@pytest.fixture
def store(tmp_path):
    pending_path = str(tmp_path / "pending.json")
    with patch("gitfolio.pending_store.PENDING_PATH", pending_path):
        yield PendingStore()


def test_save_and_load(store):
    results = [make_result()]
    store.save(results)
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0]["bullet"] == "Engineered JWT authentication system"
    assert loaded[0]["status"] == "pending"
    assert loaded[0]["tier"] == 1


def test_save_assigns_id(store):
    results = [make_result()]
    store.save(results)
    loaded = store.load()
    assert "id" in loaded[0]
    assert len(loaded[0]["id"]) == 12


def test_id_is_stable(store):
    r = make_result()
    store.save([r])
    id1 = store.load()[0]["id"]
    store.save([r])
    id2 = store.load()[0]["id"]
    assert id1 == id2


def test_update_status(store):
    store.save([make_result()])
    bullet_id = store.load()[0]["id"]
    result = store.update(bullet_id, status="approved")
    assert result is True
    assert store.load()[0]["status"] == "approved"


def test_update_bullet_text(store):
    store.save([make_result()])
    bullet_id = store.load()[0]["id"]
    store.update(bullet_id, bullet_text="Updated bullet text")
    assert store.load()[0]["bullet"] == "Updated bullet text"


def test_update_nonexistent_returns_false(store):
    store.save([make_result()])
    assert store.update("nonexistent_id", status="approved") is False


def test_get_approved(store):
    store.save([make_result(tier=1), make_result(pr_title="fix: bug", tier=2)])
    bullets = store.load()
    store.update(bullets[0]["id"], status="approved")
    approved = store.get_approved()
    assert len(approved) == 1


def test_load_returns_empty_when_no_file(store):
    result = store.load()
    assert result == []


def test_clear_removes_file(store, tmp_path):
    pending_path = str(tmp_path / "pending.json")
    with patch("gitfolio.pending_store.PENDING_PATH", pending_path):
        s = PendingStore()
        s.save([make_result()])
        assert os.path.exists(pending_path)
        s.clear()
        assert not os.path.exists(pending_path)
