from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_manifest_and_hacs_json_are_valid() -> None:
    manifest = json.loads((ROOT / "custom_components" / "catchsolar" / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())

    assert manifest["domain"] == "catchsolar"
    assert manifest["config_flow"] is True
    assert "version" in manifest
    assert "catchsolar" in hacs["domains"]


def test_branding_assets_are_present_and_valid_svg() -> None:
    component_dir = ROOT / "custom_components" / "catchsolar"
    for asset_name in ("icon.svg", "logo.svg"):
        asset_path = component_dir / asset_name
        assert asset_path.exists()
        root = ET.fromstring(asset_path.read_text())
        assert root.tag.endswith("svg")
