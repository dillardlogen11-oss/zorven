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
    assert 'id="directMessagesScreen"' in app_html
    assert 'id="directMessagesDialog"' not in app_html
    assert 'id="chatHeaderIcon" role="img" aria-label="Channel"' in app_html


def test_app_shell_default_banner_copy_matches_fluxer_shell_wording():
    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert "A Fluxer shell for messages, rooms, and lightweight voice spaces." in app_js


def test_direct_messages_open_in_shell_view_instead_of_modal():
    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'elements.directMessagesScreen.hidden = !showingDirectMessages;' in app_js
    assert 'elements.chatHeaderIcon.setAttribute("aria-label", showingDirectMessages ? "Direct messages" : "Channel");' in app_js
    assert '.direct-messages-screen {' in styles
    assert '.home-mark.active' in styles
