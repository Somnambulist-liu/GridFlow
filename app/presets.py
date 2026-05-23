"""Preset save/load via JSON files."""
import json
import os
from pathlib import Path

PRESETS_DIR = Path.home() / ".gridflow" / "presets"


def _ensure_dir():
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def save_preset(feature_id: str, preset_name: str, config: dict):
    _ensure_dir()
    feature_dir = PRESETS_DIR / feature_id
    feature_dir.mkdir(exist_ok=True)
    filepath = feature_dir / f"{preset_name}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_preset(feature_id: str, preset_name: str) -> dict | None:
    filepath = PRESETS_DIR / feature_id / f"{preset_name}.json"
    if not filepath.exists():
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_presets(feature_id: str) -> list[str]:
    feature_dir = PRESETS_DIR / feature_id
    if not feature_dir.exists():
        return []
    return sorted([p.stem for p in feature_dir.glob("*.json")])


def delete_preset(feature_id: str, preset_name: str):
    filepath = PRESETS_DIR / feature_id / f"{preset_name}.json"
    if filepath.exists():
        filepath.unlink()
