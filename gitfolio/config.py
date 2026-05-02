import yaml
import os
from datetime import datetime

CONFIG_PATH = os.path.expanduser("~/.gitfolio/config.yaml")
SYNC_PATH = os.path.expanduser("~/.gitfolio/last_sync.txt")


class Config:
    @staticmethod
    def save(config: dict):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        os.chmod(CONFIG_PATH, 0o600)

    @staticmethod
    def load() -> dict:
        if not os.path.exists(CONFIG_PATH):
            raise FileNotFoundError(
                "Config not found. Run `gitfolio init` first."
            )
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)

    @staticmethod
    def update_last_sync():
        os.makedirs(os.path.dirname(SYNC_PATH), exist_ok=True)
        with open(SYNC_PATH, "w") as f:
            f.write(datetime.utcnow().isoformat())

    @staticmethod
    def get_last_sync() -> str | None:
        if not os.path.exists(SYNC_PATH):
            return None
        with open(SYNC_PATH, "r") as f:
            return f.read().strip()
