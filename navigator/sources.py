from pathlib import Path

import yaml

SOURCES_FILE = Path(__file__).parent.parent / "data" / "sources.yaml"


def load_programs() -> dict[str, dict]:
    return {p["id"]: p for p in yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))}
