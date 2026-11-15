# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""Read/update docs/data/manifest.json - the single file the web app reads."""
import json
from datetime import datetime, timezone

from . import config


def load():
    p = config.WEB_DATA_DIR / "manifest.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


def save(m):
    m.setdefault("project", "PunaPulse SAR")
    m["aoi"] = {"name": config.AOI_NAME, "bbox": list(config.AOI_BBOX)}
    m["generated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    config.WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (config.WEB_DATA_DIR / "manifest.json").write_text(json.dumps(m, indent=2))
