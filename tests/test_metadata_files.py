from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_manifest_and_hacs_json_are_valid() -> None:
    manifest = json.loads((ROOT / "custom_components" / "catchsolar" / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())

    assert manifest["domain"] == "catchsolar"
    assert manifest["config_flow"] is True
    assert "version" in manifest
    assert "catchsolar" in hacs["domains"]
