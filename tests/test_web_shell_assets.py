import json
from html.parser import HTMLParser
from pathlib import Path

from zorven.server import ROOT, resolve_web_route


WEB_ROOT = Path(ROOT) / "web"


class ElementIdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.elements[element_id] = {"tag": tag, "attrs": attributes}


def test_resolve_web_route_supports_manifest():
    assert resolve_web_route("/manifest.json") == "manifest.json"


def test_manifest_uses_fluxer_style_brand_asset():
    manifest = json.loads((WEB_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["theme_color"] == "#5865f2"
    assert manifest["icons"][0]["src"] == "/fluxer-symbol.svg"


def test_login_and_app_shell_expose_fluxer_style_controls():
    login_html = (WEB_ROOT / "login.html").read_text(encoding="utf-8")
    app_html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    parser = ElementIdParser()
    parser.feed(app_html)

    assert "Fluxer community shell" in login_html
    assert 'id="themeToggleButton"' in login_html
    assert 'href="/download/zorven-client"' in login_html
    assert "FLUXER SHELL" in app_html
    assert 'id="serverBannerStats"' in app_html
    assert "directMessagesDialog" not in parser.elements
    assert parser.elements["directMessagesScreen"]["tag"] == "section"
    assert "hidden" in parser.elements["directMessagesScreen"]["attrs"]
    assert parser.elements["chatHeaderIcon"]["tag"] == "span"
    assert parser.elements["chatHeaderIcon"]["attrs"]["role"] == "img"
    assert parser.elements["chatHeaderIcon"]["attrs"]["aria-label"] == "Channel"


def test_app_shell_default_banner_copy_matches_fluxer_shell_wording():
    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert "A Fluxer shell for messages, rooms, and lightweight voice spaces." in app_js


def test_direct_messages_open_in_shell_view_instead_of_modal():
    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    app_html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'id="directMessageRecipientInput"' in app_html
    assert 'class="composer-dm-target-label">Recipient</span>' in app_html
    assert "Public member-to-member conversations open here in the main shell instead of a popup." in app_html
    assert 'elements.directMessagesScreen.hidden = !showingDirectMessages;' in app_js
    assert 'elements.chatHeaderIcon.setAttribute("aria-label", showingDirectMessages ? "Direct messages" : "Channel");' in app_js
    assert "async function loadChannelMessages()" in app_js
    assert "async function refreshCurrentView()" in app_js
    assert '.direct-messages-screen {' in styles
    assert '.composer-dm-target-wrap {' in styles
    assert '.direct-message-status {' in styles
    assert '.home-mark.active' in styles
