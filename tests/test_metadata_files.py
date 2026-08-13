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
    assert "python-socketio>=5.0,<6.0" in manifest["requirements"]
    assert "catchsolar" in hacs["domains"]


def test_branding_assets_are_present_and_valid_svg() -> None:
    component_dir = ROOT / "custom_components" / "catchsolar"
    for asset_name in ("icon.svg", "logo.svg"):
        asset_path = component_dir / asset_name
        assert asset_path.exists()
        root = ET.fromstring(asset_path.read_text())
        assert root.tag.endswith("svg")


def test_smatch_solar_mit_notice_is_retained() -> None:
    notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()

    assert "simonsays11/ha-smatch-solar" in notice
    assert "Copyright (c) 2026 simonsays11" in notice
    assert "MIT License" in notice


def test_experimental_feature_register_documents_rollback_boundary() -> None:
    register = (ROOT / "EXPERIMENTAL_FEATURES.md").read_text()

    assert "live_socketio_telemetry" in register
    assert "daily_energy_meters" in register
    assert "enable_live_data" in register
    assert "enable_daily_energy" in register
    assert "supplemental_sensor.py" in register
    assert "Immediate rollback" in register
