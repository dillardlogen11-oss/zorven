import json
from pathlib import Path

from zorven.server import ROOT, resolve_web_route


WEB_ROOT = Path(ROOT) / "web"


def test_resolve_web_route_supports_manifest():
    assert resolve_web_route("/manifest.json") == "manifest.json"


def test_manifest_uses_fluxer_style_brand_asset():
    manifest = json.loads((WEB_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["theme_color"] == "#5865f2"
    assert manifest["icons"][0]["src"] == "/fluxer-symbol.svg"


def test_login_and_app_shell_expose_fluxer_style_controls():
    login_html = (WEB_ROOT / "login.html").read_text(encoding="utf-8")
    app_html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

    assert "Fluxer community shell" in login_html
    assert 'id="themeToggleButton"' in login_html
    assert 'href="/download/zorven-client"' in login_html
    assert "FLUXER SHELL" in app_html
    assert 'id="serverBannerStats"' in app_html
