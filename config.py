"""Load config.yaml (and optional config.local.yaml override) for this tool."""
from pathlib import Path
from types import SimpleNamespace

import yaml

_HERE = Path(__file__).parent


def _to_namespace(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_to_namespace(v) for v in value]
    return value


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load() -> SimpleNamespace:
    cfg_path = _HERE / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    local_path = _HERE / "config.local.yaml"
    if local_path.exists():
        with open(local_path, "r", encoding="utf-8") as f:
            cfg = _deep_merge(cfg, yaml.safe_load(f) or {})

    return _to_namespace(cfg)


settings = _load()
