import os
import tkinter as tk

from zorven import desktop_app


def test_resolve_api_base_url_defaults_to_localhost():
    assert desktop_app.resolve_api_base_url("", []) == "http://127.0.0.1:8765"


def test_resolve_api_base_url_accepts_environment_override():
    original = os.environ.get("ZORVEN_API_URL")
    try:
        os.environ["ZORVEN_API_URL"] = "https://example.com:8443"
        assert desktop_app.resolve_api_base_url("", []) == "https://example.com:8443"
    finally:
        if original is None:
            os.environ.pop("ZORVEN_API_URL", None)
        else:
            os.environ["ZORVEN_API_URL"] = original


def test_resolve_api_base_url_accepts_cli_override():
    assert desktop_app.resolve_api_base_url("", ["--host", "https://cdn.example.com"]) == "https://cdn.example.com"


def test_main_falls_back_to_browser_for_headless_environment(monkeypatch, capsys):
    opened = []

    def raise_tcl_error():
        raise tk.TclError("no display name and no $DISPLAY environment variable")

    monkeypatch.setattr(desktop_app, "ZorvenChat", raise_tcl_error)
    monkeypatch.setattr(desktop_app.webbrowser, "open", lambda url: opened.append(url) or True)

    assert desktop_app.main() == 0
    assert opened == [f"{desktop_app.API}/login"]
    captured = capsys.readouterr()
    assert captured.err == ""


def test_resolve_web_route_handles_entry_points():
    assert desktop_app.resolve_api_base_url("", []) == "http://127.0.0.1:8765"
    from zorven.server import resolve_web_route

    assert resolve_web_route("/") == "login.html"
    assert resolve_web_route("/login") == "login.html"
    assert resolve_web_route("/server") == "index.html"
    assert resolve_web_route("/app") == "index.html"
    assert resolve_web_route("/admin") == "admin.html"
