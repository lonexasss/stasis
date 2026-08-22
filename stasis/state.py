"""shared state between invocations: what did stasis freeze/change."""

import json
import os
import tempfile
from pathlib import Path


def state_dir() -> Path:
    d = Path(tempfile.gettempdir()) / f"stasis-{os.getuid()}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def state_path() -> Path:
    return state_dir() / "state.json"


def load_state() -> dict:
    try:
        with open(state_path()) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    tmp = state_path().with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f)
    tmp.replace(state_path())


def clear_state() -> None:
    state_path().unlink(missing_ok=True)
