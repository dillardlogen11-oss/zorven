import os

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
