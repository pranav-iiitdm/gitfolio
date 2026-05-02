import os
import stat
import tempfile
import pytest
from unittest.mock import patch
from gitfolio.config import Config


def test_config_save_sets_0600_permissions(tmp_path):
    config_path = str(tmp_path / "config.yaml")
    sync_path = str(tmp_path / "last_sync.txt")

    with patch("gitfolio.config.CONFIG_PATH", config_path), \
         patch("gitfolio.config.SYNC_PATH", sync_path):
        Config.save({"github_token": "test", "repos": []})

    mode = oct(stat.S_IMODE(os.stat(config_path).st_mode))
    assert mode == oct(0o600)
