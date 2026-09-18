import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from zorven import server


def request_json(port, path, method="GET", token=None, payload=None):
    headers = {}
    if token:
        headers["Authorization"] = " ".join(("Bearer", token))
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def run_server():
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.ZorvenHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def test_authenticated_users_can_send_reply_and_read_only_their_dms(monkeypatch):
    original_data = server.DATA
    test_data = {
        "users": {
            "alice": {"username": "alice", "password": "unused", "role": "member"},
            "bob": {"username": "bob", "password": "unused", "role": "member"},
            "eve": {"username": "eve", "password": "unused", "role": "member"},
        },
        "sessions": {"alice-token": "alice", "bob-token": "bob", "eve-token": "eve"},
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

    httpd, thread = run_server()
    try:
        status, payload = request_json(
            httpd.server_port,
            "/api/dms",
            method="POST",
            token="alice-token",
            payload={"to": "bob", "subject": "hello", "content": "hi bob", "from": "eve"},
        )
        assert status == 201
        assert payload["message"]["from"] == "alice"
        assert payload["message"]["to"] == "bob"

        status, payload = request_json(httpd.server_port, "/api/dms", token="bob-token")
        assert status == 200
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["content"] == "hi bob"

        status, payload = request_json(
            httpd.server_port,
            "/api/dms",
            method="POST",
            token="bob-token",
            payload={"to": "alice", "content": "reply"},
        )
        assert status == 201

        status, payload = request_json(httpd.server_port, "/api/dms", token="alice-token")
        assert status == 200
        assert len(payload["messages"]) == 2

        status, payload = request_json(httpd.server_port, "/api/dms", token="eve-token")
        assert status == 200
        assert payload["messages"] == []
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        monkeypatch.setattr(server, "DATA", original_data)


def test_dm_user_discovery_and_validation(monkeypatch):
    original_data = server.DATA
    test_data = {
        "users": {
            "alice": {"username": "alice", "password": "unused", "role": "member"},
            "bob": {"username": "bob", "password": "unused", "role": "member", "displayName": "Bobby"},
            "banned": {"username": "banned", "password": "unused", "role": "member", "banned": True},
            "deactivated": {"username": "deactivated", "password": "unused", "role": "member", "deactivated": True},
        },
        "sessions": {"alice-token": "alice", "banned-token": "banned"},
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

    httpd, thread = run_server()
    try:
        status, payload = request_json(httpd.server_port, "/api/dms/recipients", token="alice-token")
        assert status == 200
        assert payload["users"] == [{"username": "bob", "displayName": "Bobby"}]

        status, payload = request_json(
            httpd.server_port,
            "/api/dms",
            method="POST",
            token="alice-token",
            payload={"to": "alice", "content": "self"},
        )
        assert status == 400
        assert payload["error"] == "You cannot send a direct message to yourself"

        status, payload = request_json(
            httpd.server_port,
            "/api/dms",
            method="POST",
            token="alice-token",
            payload={"to": "missing", "content": "hello"},
        )
        assert status == 400
        assert payload["error"] == "A valid recipient is required"

        status, payload = request_json(
            httpd.server_port,
            "/api/dms",
            method="POST",
            token="alice-token",
            payload={"to": "bob", "content": "   "},
        )
        assert status == 400
        assert payload["error"] == "Message content is required"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        monkeypatch.setattr(server, "DATA", original_data)


def test_banned_users_cannot_access_dm_endpoints(monkeypatch):
    original_data = server.DATA
    test_data = {
        "users": {
            "banned": {"username": "banned", "password": "unused", "role": "member", "banned": True},
            "bob": {"username": "bob", "password": "unused", "role": "member"},
        },
        "sessions": {"banned-token": "banned"},
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

    httpd, thread = run_server()
    try:
        status, payload = request_json(httpd.server_port, "/api/dms", token="banned-token")
        assert status == 403
        assert payload["error"] == "This account is banned"

        status, payload = request_json(httpd.server_port, "/api/dms/recipients", token="banned-token")
        assert status == 403
        assert payload["error"] == "This account is banned"

        status, payload = request_json(httpd.server_port, "/api/dms/read", method="POST", token="banned-token", payload={})
        assert status == 403
        assert payload["error"] == "This account is banned"

        status, payload = request_json(
            httpd.server_port,
            "/api/dms",
            method="POST",
            token="banned-token",
            payload={"to": "bob", "content": "hi"},
        )
        assert status == 403
        assert payload["error"] == "This account is banned"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        monkeypatch.setattr(server, "DATA", original_data)
