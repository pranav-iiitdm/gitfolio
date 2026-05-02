import datetime
import pytest
from unittest.mock import MagicMock, patch
from gitfolio.github_analyzer import GitHubAnalyzer, _with_retry


def make_config(diff_access=True):
    return {
        "github_token": "fake",
        "author_email": "dev@example.com",
        "repos": ["org/repo"],
        "diff_access": diff_access,
    }


def test_diff_access_false_skips_file_fetch():
    config = make_config(diff_access=False)
    with patch("gitfolio.github_analyzer.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.full_name = "org/repo"
        mock_repo.default_branch = "main"
        mock_pr = MagicMock()
        mock_pr.merged_at = datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc)
        mock_pr.user.login = "testuser"
        mock_pr.title = "feat: add feature"
        mock_pr.body = "description"
        mock_pr.number = 1
        mock_pr.get_commits.return_value = []
        mock_repo.get_pulls.return_value = [mock_pr]
        MockGithub.return_value.get_repo.return_value = mock_repo
        MockGithub.return_value.get_user.return_value.login = "testuser"

        analyzer = GitHubAnalyzer(config)
        clusters = analyzer._fetch_pr_clusters(
            mock_repo,
            datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        )

        mock_pr.get_files.assert_not_called()
        assert clusters[0]["diff_sample"] == []


def test_retry_succeeds_after_rate_limit():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise Exception("rate limit exceeded")
        return "success"

    with patch("gitfolio.github_analyzer.time.sleep"):
        result = _with_retry(flaky, retries=3, backoff=1)

    assert result == "success"
    assert len(attempts) == 3


def test_retry_reraises_non_rate_limit():
    def always_fails():
        raise ValueError("not a rate limit error")

    with pytest.raises(ValueError):
        _with_retry(always_fails, retries=3, backoff=1)


def test_retry_reraises_after_max_attempts():
    calls = []

    def always_rate_limited():
        calls.append(1)
        raise Exception("rate limit exceeded")

    with patch("gitfolio.github_analyzer.time.sleep"):
        with pytest.raises(Exception, match="rate limit exceeded"):
            _with_retry(always_rate_limited, retries=3, backoff=1)

    assert len(calls) == 3
