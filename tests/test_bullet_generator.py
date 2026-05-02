import pytest
from unittest.mock import MagicMock, patch
from gitfolio.bullet_generator import BulletGenerator


def make_config(model=None):
    cfg = {"target_role": "SDE"}
    if model:
        cfg["model"] = model
    return cfg


def make_cluster():
    return {
        "repo": "org/repo",
        "work_type": "feature",
        "pr_title": "feat: add auth",
        "pr_body": "Adds JWT authentication",
        "commits": [{"message": "feat: add JWT"}],
        "diff_sample": [],
        "files_changed": 3,
        "additions": 120,
        "deletions": 10,
        "score": 16,
    }


def test_uses_configured_model():
    with patch("gitfolio.bullet_generator.anthropic.Anthropic") as MockClient:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"bullet":"Built X","tier":1,"flag_reason":null,"keywords":[]}')]
        MockClient.return_value.messages.create.return_value = mock_msg

        gen = BulletGenerator(make_config(model="claude-opus-4-7"))
        gen._generate_bullet(make_cluster())

        call_kwargs = MockClient.return_value.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-7"


def test_default_model_is_haiku():
    with patch("gitfolio.bullet_generator.anthropic.Anthropic") as MockClient:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"bullet":"Built X","tier":1,"flag_reason":null,"keywords":[]}')]
        MockClient.return_value.messages.create.return_value = mock_msg

        gen = BulletGenerator(make_config())
        gen._generate_bullet(make_cluster())

        call_kwargs = MockClient.return_value.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


def test_system_prompt_has_cache_control():
    with patch("gitfolio.bullet_generator.anthropic.Anthropic") as MockClient:
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"bullet":"Built X","tier":1,"flag_reason":null,"keywords":[]}')]
        MockClient.return_value.messages.create.return_value = mock_msg

        gen = BulletGenerator(make_config())
        gen._generate_bullet(make_cluster())

        call_kwargs = MockClient.return_value.messages.create.call_args[1]
        system = call_kwargs["system"]
        assert isinstance(system, list)
        assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_tier3_clusters_skipped():
    with patch("gitfolio.bullet_generator.anthropic.Anthropic"):
        gen = BulletGenerator(make_config())
        cluster = make_cluster()
        cluster["score"] = 2
        results = gen.generate([cluster])
        assert results[0]["tier"] == 3
        assert results[0]["bullet"] is None
