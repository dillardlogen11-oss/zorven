import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from zorven import server


def api_request(port, path, *, method="GET", token="", payload=None):
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            **({"Content-Type": "application/json"} if payload is not None else {}),
            **({"Authorization": "Bearer " + token} if token else {}),
        },
        method=method,
    )
    with urlopen(request) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_members_can_send_public_direct_messages(monkeypatch):
    original_data = server.DATA
    test_data = {
        "users": {
            "alice": {"username": "alice", "password": "unused", "role": "member", "displayName": "Alice"},
            "bob": {"username": "bob", "password": "unused", "role": "member", "displayName": "Bob"},
        },
        "sessions": {"alice-token": "alice", "bob-token": "bob"},
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
        status, payload = api_request(httpd.server_port, "/api/dms", method="POST", token="alice-token", payload={"to": "bob", "content": "hello @bob"})
        assert status == 201
        assert payload["message"]["from"] == "alice"
        assert payload["message"]["to"] == "bob"
        assert payload["message"]["content"] == "hello @bob"
        assert payload["message"]["read"] is False

        _, inbox = api_request(httpd.server_port, "/api/dms", token="bob-token")
        assert inbox["messages"] == [payload["message"]]

        _, directory = api_request(httpd.server_port, "/api/users", token="alice-token")
        assert [user["username"] for user in directory["users"]] == ["bob"]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        monkeypatch.setattr(server, "DATA", original_data)


def test_public_direct_messages_reject_invalid_targets(monkeypatch):
    original_data = server.DATA
    test_data = {
        "users": {
            "alice": {"username": "alice", "password": "unused", "role": "member"},
            "bob": {"username": "bob", "password": "unused", "role": "member", "deactivated": True},
        },
        "sessions": {"alice-token": "alice"},
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
            f"http://127.0.0.1:{httpd.server_port}/api/dms",
            data=json.dumps({"to": "bob", "content": "hey"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + "alice-token"},
            method="POST",
        )
        try:
            urlopen(request)
            assert False, "Expected an HTTPError"
        except HTTPError as error:
            payload = json.loads(error.read().decode("utf-8"))
            assert error.code == 404
            assert payload == {"error": "That account is unavailable for direct messages"}
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        monkeypatch.setattr(server, "DATA", original_data)
