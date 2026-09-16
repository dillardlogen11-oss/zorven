import json
import threading
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from zorven import server


class NoRedirectHandler(HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


def test_admin_shell_exposes_clear_sessions_control():
    admin_html = open("/home/runner/work/zorven/zorven/zorven/web/admin.html", encoding="utf-8").read()
    admin_js = open("/home/runner/work/zorven/zorven/zorven/web/admin.js", encoding="utf-8").read()

    assert 'id="clearSessionsButton"' in admin_html
    assert 'command("clear_sessions")' in admin_js


def test_admin_command_can_clear_all_sessions(monkeypatch):
    original_data = server.DATA
    test_data = {
        "users": {"admin": {"username": "admin", "password": "unused", "role": "admin"}},
        "sessions": {"admin-token": "admin", "member-token": "admin"},
        "queue": [],
        "orders": [],
        "messages": [],
        "voice": {},
        "servers": {"zorven": {"id": "zorven", "name": "Zorven Community", "description": "The official Zorven community.", "owner": "system", "status": "active"}},
        "maintenanceMode": False,
        "directMessages": [],
        "serverReviews": [],
    }
    monkeypatch.setattr(server, "DATA", test_data)
    monkeypatch.setattr(server, "save_data", lambda: None)

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.ZorvenHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(
            f"http://127.0.0.1:{httpd.server_port}/api/admin/command",
            data=json.dumps({"command": "clear_sessions"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + "admin-token"},
            method="POST",
        )
        with urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload == {"cleared": True, "removed": 2}
        assert server.DATA["sessions"] == {}
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        monkeypatch.setattr(server, "DATA", original_data)


def test_public_status_route_redirects_to_admin_site(monkeypatch):
    original_data = server.DATA
    test_data = {
        "users": {},
        "sessions": {},
        "queue": [],
        "orders": [],
        "messages": [],
        "voice": {},
        "servers": {"zorven": {"id": "zorven", "name": "Zorven Community", "description": "The official Zorven community.", "owner": "system", "status": "active"}},
        "maintenanceMode": False,
        "directMessages": [],
        "serverReviews": [],
    }
    monkeypatch.setattr(server, "DATA", test_data)

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.ZorvenHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        opener = build_opener(NoRedirectHandler)
        for path in ("/maintenance", "/maintenance.html", "/zorven-maintenance"):
            with opener.open(f"http://127.0.0.1:{httpd.server_port}{path}") as response:
                assert response.status == 302
                assert response.headers["Location"] == "/admin"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        monkeypatch.setattr(server, "DATA", original_data)


def test_maintenance_mode_still_serves_maintenance_page_on_community_routes(monkeypatch):
    original_data = server.DATA
    test_data = {
        "users": {},
        "sessions": {},
        "queue": [],
        "orders": [],
        "messages": [],
        "voice": {},
        "servers": {"zorven": {"id": "zorven", "name": "Zorven Community", "description": "The official Zorven community.", "owner": "system", "status": "active"}},
        "maintenanceMode": True,
        "directMessages": [],
        "serverReviews": [],
    }
    monkeypatch.setattr(server, "DATA", test_data)

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.ZorvenHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{httpd.server_port}/server") as response:
            html = response.read().decode("utf-8")
        assert "We are polishing the next community release." in html
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        monkeypatch.setattr(server, "DATA", original_data)
