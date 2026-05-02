import pytest
from gitfolio.scorer import Scorer


@pytest.fixture
def scorer():
    return Scorer()


def make_cluster(**kwargs):
    base = {
        "type": "pr",
        "repo": "org/repo",
        "pr_title": "feat: add authentication",
        "pr_body": "",
        "commits": [],
        "diff_sample": [],
        "files_changed": 0,
        "additions": 0,
        "deletions": 0,
        "reviews_given": 0,
    }
    base.update(kwargs)
    return base


def test_feature_pr_scores_high(scorer):
    cluster = make_cluster(
        pr_title="feat: add authentication",
        pr_body="Implements JWT authentication with refresh tokens to improve security",
        commits=[{"message": "feat: add JWT auth", "sha": "abc", "date": "2026-01-01"}],
        files_changed=5,
        additions=150,
    )
    score = scorer.score(cluster)
    assert score >= 15


def test_skip_keyword_penalizes(scorer):
    cluster = make_cluster(pr_title="fix typo in README")
    score = scorer.score(cluster)
    assert score < 5


def test_work_type_detected_as_feature(scorer):
    cluster = make_cluster(pr_title="feat: add new dashboard")
    scorer.score(cluster)
    assert cluster["work_type"] == "feature"


def test_work_type_detected_as_bugfix(scorer):
    cluster = make_cluster(pr_title="fix: resolve null pointer in auth")
    scorer.score(cluster)
    assert cluster["work_type"] == "bugfix"


def test_score_floor_is_zero(scorer):
    cluster = make_cluster(pr_title="wip: fixup lint whitespace bump version")
    score = scorer.score(cluster)
    assert score == 0
