import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(__file__)
WEB_ROOT = os.path.join(ROOT, "web")
DATA_FILE = os.environ.get("DATA_FILE") or os.path.join(ROOT, "zorven_data.json")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8765"))
SETUP_KEY = os.environ.get("SETUP_KEY", "")
ALL_PERMISSIONS = [
    "manage_members",
    "manage_channels",
    "moderate_chat",
    "publish_updates",
    "send_as_bot",
    "manage_servers",
    "use_internal_tools",
]


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            pass
    return {"users": {}, "sessions": {}, "queue": [], "orders": [], "messages": [], "voice": {}, "servers": {"zorven": {"id": "zorven", "name": "Zorven Community", "description": "The official Zorven community.", "owner": "system", "status": "active"}}}


DATA = load_data()
DATA.setdefault("messages", [])
DATA.setdefault("voice", {})
DATA.setdefault("maintenanceMode", False)
DATA.setdefault("directMessages", [])
DATA.setdefault("serverReviews", [])
DATA.setdefault("servers", {"zorven": {"id": "zorven", "name": "Zorven Community", "description": "The official Zorven community.", "owner": "system", "status": "active"}})
for stored_server in DATA["servers"].values():
    stored_server.setdefault("description", "A Zorven community server.")


GAMES = [
    {
        "id": "zorven-first-light",
        "title": "Zorven: First Light",
        "genre": "Action RPG",
        "status": "In development",
        "players": 0,
        "description": "Explore a new world, gather Shards, and build your first loadout.",
    },
    {
        "id": "zorven-arena",
        "title": "Zorven Arena",
        "genre": "Competitive",
        "status": "Coming soon",
        "players": 0,
        "description": "Fast matches, clean competition, and seasonal rankings.",
    },
]

CHANNELS = [
    {"id": "general", "name": "general", "description": "Talk about anything Zorven."},
    {"id": "announcements", "name": "announcements", "description": "Official development updates."},
    {"id": "feedback", "name": "feedback", "description": "Help shape the game."},
]

def server_channels(server):
    return server.get("channels", CHANNELS if server.get("id") == "zorven" else [])


for stored_server in DATA["servers"].values():
    stored_server.setdefault("channels", CHANNELS.copy() if stored_server.get("id") == "zorven" else [])
    stored_server.setdefault("roles", [])
    stored_server.setdefault("categories", [])

STAFF_PROFILES = {
    "admin": {"tag": "FOUNDER", "badge": "founder", "color": "#f0b232", "permissions": ALL_PERMISSIONS},
    "staff": {"tag": "BUILDER", "badge": "builder", "color": "#c5ed59", "permissions": ["publish_updates", "moderate_chat"]},
    "moderator": {"tag": "GUARDIAN", "badge": "guardian", "color": "#78b7ff", "permissions": ["moderate_chat"]},
    "zorven": {"tag": "CREATOR", "badge": "creator", "color": "#ed7d68", "permissions": ALL_PERMISSIONS},
    "zorvenbot": {"tag": "AUTOMATION", "badge": "automation", "color": "#9b8cff", "permissions": ["publish_updates", "moderate_chat", "send_as_bot"]},
    "zorven-team": {"tag": "ZORVEN TEAM", "badge": "team", "color": "#57e0c0", "permissions": ALL_PERMISSIONS},
}

STAFF_PROFILES["zorvenbot"] = {"tag": "AUTOMATION", "color": "#9b8cff", "permissions": ALL_PERMISSIONS}


def save_data():
    data_directory = os.path.dirname(os.path.abspath(DATA_FILE))
    os.makedirs(data_directory, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=data_directory, delete=False) as file:
        json.dump(DATA, file, indent=2)
        temporary_file = file.name
    os.replace(temporary_file, DATA_FILE)


if "zorvenbot" in DATA["users"]:
    DATA["users"]["zorvenbot"]["role"] = "staff"
    DATA["users"]["zorvenbot"]["staffProfile"] = STAFF_PROFILES["zorvenbot"].copy()
    save_data()


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310000)
    return "pbkdf2_sha256$310000$" + salt.hex() + "$" + digest.hex()


def ensure_default_admin_account():
    if any(user.get("role") in {"staff", "admin"} for user in DATA["users"].values()):
        return
    DATA["users"]["admin"] = {
        "username": "admin",
        "password": hash_password("admin123"),
        "role": "admin",
        "displayName": "Admin",
        "bio": "Primary administrator",
        "staffProfile": {"tag": "ADMIN", "badge": "founder", "color": "#f0b232", "permissions": ALL_PERMISSIONS},
        "createdAt": int(time.time()),
    }
    save_data()


ensure_default_admin_account()


def verify_password(password, stored):
    if stored.startswith("pbkdf2_sha256$"):
        _, iterations, salt_hex, digest_hex = stored.split("$", 3)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored)


def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def get_user(handler):
    token = handler.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    username = DATA["sessions"].get(token)
    return DATA["users"].get(username) if username else None


def public_user(user):
    if user.get("username") == "admin" or user.get("role") == "admin":
        profile = {"tag": "ADMIN", "badge": "founder", "color": "#f0b232", "permissions": ALL_PERMISSIONS}
    else:
        profile = user.get("staffProfile", {}) if user.get("role") == "staff" else {}
        if user.get("role") == "staff" and not profile:
            profile = STAFF_PROFILES.get(user.get("username"), {})
        if user.get("role") == "staff" and not profile.get("badge"):
            profile = {**profile, "badge": STAFF_PROFILES.get(user.get("username"), {}).get("badge", "member")}
    return {
        "username": user["username"],
        "role": user.get("role", "member"),
        "tag": profile.get("tag", "MEMBER"),
        "badge": profile.get("badge", "member"),
        "badgeColor": profile.get("color", "#949ba4"),
        "displayName": user.get("displayName", user["username"]),
        "bio": user.get("bio", ""),
        "permissions": profile.get("permissions", []),
        "banned": bool(user.get("banned")),
        "deactivated": bool(user.get("deactivated")),
    }


def can_run(user, permission):
    return bool(user and (user.get("username") == "admin" or user.get("role") == "admin" or permission in public_user(user)["permissions"]))


def find_user(username):
    return DATA["users"].get(str(username).strip().lower())


def is_banned(user):
    return bool(user and user.get("banned"))


def has_full_access(user):
    return user and set(ALL_PERMISSIONS).issubset(public_user(user)["permissions"])


def can_manage_server(user, server):
    return user and server and (server.get("owner") == user["username"] or can_run(user, "manage_servers"))


def resolve_web_route(path):
    normalized = path or "/"
    if normalized == "/":
        return "login.html"
    route_map = {
        "/index.html": "index.html",
        "/login": "login.html",
        "/login.html": "login.html",
        "/server": "index.html",
        "/server.html": "index.html",
        "/app": "index.html",
        "/app.html": "index.html",
        "/home": "index.html",
        "/account": "index.html",
        "/zorven-server": "index.html",
        "/zorven-account": "index.html",
        "/admin": "admin.html",
        "/admin.html": "admin.html",
        "/zorven-admin": "admin.html",
        "/maintenance": "maintenance.html",
        "/maintenance.html": "maintenance.html",
        "/zorven-maintenance": "maintenance.html",
    }
    return route_map.get(normalized)


class ZorvenHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_name, content_type):
        path = os.path.join(WEB_ROOT, file_name)
        if not os.path.isfile(path):
            self.send_error(404)
            return
        with open(path, "rb") as file:
            body = file.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Security-Policy", "default-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; script-src 'self' 'unsafe-inline'; img-src 'self' data:")
        self.end_headers()
        self.wfile.write(body)

    def _send_download(self):
        body = b"ZORVEN CLIENT\nDevelopment client placeholder. Connect this launcher to the production client build before release.\n"
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", "attachment; filename=zorven-client.txt")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        if path != "/":
            path = path.rstrip("/")
        maintenance_routes = {"/", "/index.html", "/login", "/login.html", "/server", "/server.html", "/app", "/app.html", "/home", "/account", "/zorven-server", "/zorven-account"}
        if DATA.get("maintenanceMode") and path in maintenance_routes:
            self._send_file("maintenance.html", "text/html; charset=utf-8")
        elif path == "/api/health":
            self._send_json({"platform": "Zorven", "status": "online", "mode": "development"})
        elif path == "/api/games":
            self._send_json({"games": GAMES})
        elif path == "/api/me":
            user = get_user(self)
            self._send_json({"authenticated": bool(user), "user": public_user(user) if user else None})
        elif path == "/api/matchmaking/status":
            self._send_json({"queuedPlayers": len(DATA["queue"]), "status": "open"})
        elif path == "/api/servers":
            self._send_json({"servers": list(DATA["servers"].values())})
        elif path == "/api/dms":
            user = get_user(self)
            if not user:
                self._send_json({"error": "Login required"}, 401)
                return
            self._send_json({"messages": [message for message in DATA["directMessages"] if message["to"] == user["username"] or message["from"] == user["username"]]})
        elif path == "/api/team":
            team = [public_user(user) for user in DATA["users"].values() if user.get("role") == "staff" and not is_banned(user)]
            self._send_json({"team": team})
        elif path == "/api/voice":
            rooms = {}
            for username, presence in DATA["voice"].items():
                user = DATA["users"].get(username)
                if user:
                    rooms.setdefault(presence["channelId"], []).append({"user": public_user(user), "muted": bool(presence.get("muted"))})
            self._send_json({"rooms": rooms})
        elif path == "/api/channels":
            server = DATA["servers"].get(query.get("serverId", ["zorven"])[0])
            self._send_json({"channels": server_channels(server) if server else []})
        elif path.startswith("/api/channels/") and path.endswith("/messages"):
            channel_id = path.split("/")[3]
            server_id = query.get("serverId", ["zorven"])[0]
            messages = [message for message in DATA["messages"] if message["channelId"] == channel_id and message.get("serverId", "zorven") == server_id]
            self._send_json({"messages": messages[-100:]})
        elif path == "/download/zorven-client":
            self._send_download()
        elif path in {"/", "/index.html"}:
            self._send_file("login.html", "text/html; charset=utf-8")
        elif path in {"/server", "/zorven-server", "/account", "/zorven-account", "/app", "/home"}:
            self._send_file("index.html", "text/html; charset=utf-8")
        elif path in {"/login", "/zorven-login", "/login.html"}:
            self._send_file("login.html", "text/html; charset=utf-8")
        elif path in {"/admin", "/zorven-admin", "/admin.html"}:
            self._send_file("admin.html", "text/html; charset=utf-8")
        elif path in {"/maintenance", "/zorven-maintenance", "/maintenance.html"}:
            self._send_file("maintenance.html", "text/html; charset=utf-8")
        elif path in {"/server.html", "/app.html"}:
            self._send_file("index.html", "text/html; charset=utf-8")
        elif path == "/app.js":
            self._send_file("app.js", "text/javascript; charset=utf-8")
        elif path == "/login.js":
            self._send_file("login.js", "text/javascript; charset=utf-8")
        elif path == "/admin.js":
            self._send_file("admin.js", "text/javascript; charset=utf-8")
        elif path == "/admin.css":
            self._send_file("admin.css", "text/css; charset=utf-8")
        elif path == "/maintenance.css":
            self._send_file("maintenance.css", "text/css; charset=utf-8")
        elif path == "/styles.css":
            self._send_file("styles.css", "text/css; charset=utf-8")
        elif path == "/login.css":
            self._send_file("login.css", "text/css; charset=utf-8")
        elif path == "/discord.css":
            self._send_file("discord.css", "text/css; charset=utf-8")
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = read_json(self)
        except (ValueError, json.JSONDecodeError):
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        if path == "/api/dms/read":
            user = get_user(self)
            if not user:
                self._send_json({"error": "Login required"}, 401)
                return
            for message in DATA["directMessages"]:
                if message["to"] == user["username"]:
                    message["read"] = True
            save_data()
            self._send_json({"read": True})
        elif path == "/api/auth/register":
            username = str(payload.get("username", "")).strip().lower()
            password = str(payload.get("password", ""))
            if len(username) < 3 or len(password) < 8:
                self._send_json({"error": "Username must be 3+ characters and password 8+ characters"}, 400)
                return
            if username in DATA["users"]:
                self._send_json({"error": "Username already exists"}, 409)
                return
            DATA["users"][username] = {"username": username, "password": hash_password(password), "role": "member", "createdAt": int(time.time())}
            try:
                save_data()
            except OSError:
                DATA["users"].pop(username, None)
                self._send_json({"error": "Account storage is unavailable. Check the Render persistent disk and DATA_FILE setting."}, 503)
                return
            self._send_json({"created": True, "user": public_user(DATA["users"][username])}, 201)
        elif path == "/api/auth/login":
            username = str(payload.get("username", "")).strip().lower()
            user = DATA["users"].get(username)
            password = str(payload.get("password", ""))
            if not user or not verify_password(password, user["password"]):
                self._send_json({"error": "Invalid username or password"}, 401)
                return
            if is_banned(user):
                self._send_json({"error": "This account is banned", "reason": user.get("banReason", "No reason provided")}, 403)
                return
            if user.get("deactivated"):
                self._send_json({"error": "This account has been deactivated"}, 403)
                return
            if not user["password"].startswith("pbkdf2_sha256$"):
                user["password"] = hash_password(password)
            token = secrets.token_urlsafe(24)
            DATA["sessions"][token] = username
            save_data()
            self._send_json({"token": token, "user": public_user(user)})
        elif path == "/api/auth/logout":
            token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if token:
                DATA["sessions"].pop(token, None)
                save_data()
            self._send_json({"loggedOut": True})
        elif path == "/api/account/settings":
            user = get_user(self)
            if not user:
                self._send_json({"error": "Login required"}, 401)
                return
            display_name = str(payload.get("displayName", user["username"])).strip()[:40]
            bio = str(payload.get("bio", "")).strip()[:190]
            if not display_name:
                self._send_json({"error": "Display name is required"}, 400)
                return
            user["displayName"] = display_name
            user["bio"] = bio
            current_password = str(payload.get("currentPassword", ""))
            new_password = str(payload.get("newPassword", ""))
            if current_password or new_password:
                if not verify_password(current_password, user["password"]):
                    self._send_json({"error": "Your current password is incorrect"}, 403)
                    return
                if len(new_password) < 8:
                    self._send_json({"error": "New password must be 8+ characters"}, 400)
                    return
                user["password"] = hash_password(new_password)
                current_token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                DATA["sessions"] = {token: username for token, username in DATA["sessions"].items() if token == current_token}
            save_data()
            self._send_json({"user": public_user(user)})
        elif path.startswith("/api/servers/") and path.endswith("/settings"):
            user = get_user(self)
            server_id = path.split("/")[3]
            server = DATA["servers"].get(server_id)
            if not can_manage_server(user, server):
                self._send_json({"error": "You need server management permission"}, 403)
                return
            name = str(payload.get("name", server["name"])).strip()[:60]
            description = str(payload.get("description", server.get("description", ""))).strip()[:180]
            channel_names = [str(item).strip()[:40] for item in str(payload.get("channels", "")).splitlines() if str(item).strip()]
            role_names = [str(item).strip()[:40] for item in str(payload.get("roles", "")).splitlines() if str(item).strip()]
            category_names = [str(item).strip()[:40] for item in str(payload.get("categories", "")).splitlines() if str(item).strip()]
            if len(name) < 2:
                self._send_json({"error": "Server name must be at least 2 characters"}, 400)
                return
            server["name"] = name
            server["description"] = description
            existing_channels = {channel["name"].lower(): channel for channel in server_channels(server)}
            server["channels"] = [{"id": existing_channels.get(channel_name.lower(), {}).get("id", secrets.token_hex(5)), "name": channel_name, "description": existing_channels.get(channel_name.lower(), {}).get("description", "")} for channel_name in channel_names]
            server["roles"] = role_names
            server["categories"] = category_names
            save_data()
            self._send_json({"server": server})
        elif path.startswith("/api/servers/") and path.endswith("/channels"):
            user = get_user(self)
            server_id = path.split("/")[3]
            server = DATA["servers"].get(server_id)
            if not can_manage_server(user, server):
                self._send_json({"error": "Only the server owner can create channels"}, 403)
                return
            name = str(payload.get("name", "")).strip()[:40]
            if len(name) < 2:
                self._send_json({"error": "Channel name must be at least 2 characters"}, 400)
                return
            if any(channel["name"].lower() == name.lower() for channel in server_channels(server)):
                self._send_json({"error": "That channel already exists"}, 409)
                return
            channel = {"id": secrets.token_hex(5), "name": name, "description": str(payload.get("description", "")).strip()[:120]}
            server.setdefault("channels", []).append(channel)
            save_data()
            self._send_json({"channel": channel, "server": server}, 201)
        elif path.startswith("/api/servers/") and path.endswith("/categories"):
            user = get_user(self)
            server_id = path.split("/")[3]
            server = DATA["servers"].get(server_id)
            if not can_manage_server(user, server):
                self._send_json({"error": "Only the server owner can create categories"}, 403)
                return
            name = str(payload.get("name", "")).strip()[:40]
            if len(name) < 2:
                self._send_json({"error": "Category name must be at least 2 characters"}, 400)
                return
            if any(category.lower() == name.lower() for category in server.get("categories", [])):
                self._send_json({"error": "That category already exists"}, 409)
                return
            server.setdefault("categories", []).append(name)
            save_data()
            self._send_json({"category": name, "server": server}, 201)
        elif path.startswith("/api/servers/") and path.endswith("/review"):
            user = get_user(self)
            server_id = path.split("/")[3]
            server = DATA["servers"].get(server_id)
            if not user or not server or server.get("owner") != user.get("username"):
                self._send_json({"error": "Only the server owner can request a review"}, 403)
                return
            if not any(review["serverId"] == server_id and review["status"] == "pending" for review in DATA["serverReviews"]):
                DATA["serverReviews"].append({"serverId": server_id, "serverName": server["name"], "owner": user["username"], "status": "pending", "createdAt": int(time.time())})
                save_data()
            self._send_json({"requested": True})
        elif path == "/api/voice":
            user = get_user(self)
            if not user or is_banned(user):
                self._send_json({"error": "Login required"}, 401)
                return
            action = str(payload.get("action", "join"))
            channel_id = str(payload.get("channelId", ""))
            if action == "leave":
                DATA["voice"].pop(user["username"], None)
            elif action in {"join", "mute"} and channel_id in {channel["id"] for channel in CHANNELS}:
                DATA["voice"][user["username"]] = {"channelId": channel_id, "muted": bool(payload.get("muted"))}
            else:
                self._send_json({"error": "A valid voice action and channel are required"}, 400)
                return
            save_data()
            self._send_json({"voice": DATA["voice"].get(user["username"]), "rooms": DATA["voice"]})
        elif path == "/api/staff/bootstrap":
            if any(user.get("role") == "staff" for user in DATA["users"].values()):
                self._send_json({"error": "A staff account already exists"}, 409)
                return
            if SETUP_KEY and not hmac.compare_digest(str(payload.get("setupKey", "")), SETUP_KEY):
                self._send_json({"error": "A valid setup key is required"}, 403)
                return
            username = str(payload.get("username", "")).strip().lower()
            password = str(payload.get("password", ""))
            if len(username) < 3 or len(password) < 8:
                self._send_json({"error": "Username must be 3+ characters and password 8+ characters"}, 400)
                return
            if username in DATA["users"]:
                self._send_json({"error": "Username already exists"}, 409)
                return
            DATA["users"][username] = {"username": username, "password": hash_password(password), "role": "staff", "staffProfile": {"tag": "FOUNDER", "color": "#f0b232", "permissions": ALL_PERMISSIONS}, "createdAt": int(time.time())}
            save_data()
            self._send_json({"created": True, "user": public_user(DATA["users"][username])}, 201)
        elif path == "/api/staff/claim-team-account":
            if SETUP_KEY and not hmac.compare_digest(str(payload.get("setupKey", "")), SETUP_KEY):
                self._send_json({"error": "A valid setup key is required"}, 403)
                return
            password = str(payload.get("password", ""))
            if len(password) < 8:
                self._send_json({"error": "Password must be 8+ characters"}, 400)
                return
            username = "zorven-team"
            existing = DATA["users"].get(username, {})
            DATA["users"][username] = {"username": username, "password": hash_password(password), "role": "staff", "staffProfile": STAFF_PROFILES["zorven-team"].copy(), "displayName": existing.get("displayName", "Zorven Team"), "bio": existing.get("bio", ""), "createdAt": existing.get("createdAt", int(time.time()))}
            DATA["sessions"] = {token: name for token, name in DATA["sessions"].items() if name != username}
            save_data()
            self._send_json({"created": True, "user": public_user(DATA["users"][username])}, 201)
        elif path == "/api/staff/reset-accounts":
            if SETUP_KEY and not hmac.compare_digest(str(payload.get("setupKey", "")), SETUP_KEY):
                self._send_json({"error": "A valid setup key is required"}, 403)
                return
            removed = len(DATA["users"])
            DATA["users"] = {}
            DATA["sessions"] = {}
            save_data()
            self._send_json({"cleared": True, "removed": removed})
        elif path == "/api/staff/recover-admin":
            if SETUP_KEY and not hmac.compare_digest(str(payload.get("setupKey", "")), SETUP_KEY):
                self._send_json({"error": "A valid setup key is required"}, 403)
                return
            if "admin" not in DATA["users"]:
                self._send_json({"error": "The admin account was not found"}, 404)
                return
            del DATA["users"]["admin"]
            DATA["sessions"] = {token: username for token, username in DATA["sessions"].items() if username != "admin"}
            save_data()
            self._send_json({"deleted": True, "username": "admin"})
        elif path == "/api/staff/accounts":
            creator = get_user(self)
            creator_identity = public_user(creator) if creator else None
            if not creator or "manage_members" not in creator_identity["permissions"]:
                self._send_json({"error": "Only an authorized account can create staff accounts"}, 403)
                return
            username = str(payload.get("username", "")).strip().lower()
            password = str(payload.get("password", ""))
            tag = str(payload.get("tag", "CREW")).strip()[:20].upper()
            badge = str(payload.get("badge", "member")).strip()[:20]
            color = str(payload.get("color", "#c5ed59")).strip()
            permissions = ALL_PERMISSIONS if bool(payload.get("fullAccess")) else ["publish_updates", "moderate_chat"]
            if bool(payload.get("fullAccess")) and not has_full_access(creator):
                self._send_json({"error": "Only a full-access staff account can grant full access"}, 403)
                return
            if len(username) < 3 or len(password) < 8 or not tag:
                self._send_json({"error": "Username 3+ characters, password 8+ characters, and a tag are required"}, 400)
                return
            if username in DATA["users"]:
                self._send_json({"error": "Username already exists"}, 409)
                return
            DATA["users"][username] = {"username": username, "password": hash_password(password), "role": "staff", "staffProfile": {"tag": tag, "badge": badge, "color": color, "permissions": permissions}, "createdAt": int(time.time())}
            save_data()
            self._send_json({"created": True, "user": public_user(DATA["users"][username])}, 201)
        elif path == "/api/servers":
            owner = get_user(self)
            if not owner or is_banned(owner):
                self._send_json({"error": "Login required"}, 401)
                return
            name = str(payload.get("name", "")).strip()[:60]
            if len(name) < 2:
                self._send_json({"error": "Server name must be at least 2 characters"}, 400)
                return
            server_id = secrets.token_urlsafe(8).replace("-", "").replace("_", "").lower()
            description = str(payload.get("description", "")).strip()[:180]
            server = {"id": server_id, "name": name, "description": description, "owner": owner["username"], "status": "active", "channels": [], "roles": [], "categories": []}
            DATA["servers"][server_id] = server
            save_data()
            self._send_json({"created": True, "server": server}, 201)
        elif path == "/api/admin/command":
            actor = get_user(self)
            command = str(payload.get("command", "")).strip().lower()
            args = payload.get("args", {})
            if not actor:
                self._send_json({"error": "Login required"}, 401)
                return
            if not can_run(actor, "manage_members"):
                self._send_json({"error": "You need manage_members permission"}, 403)
                return
            if command == "list_users":
                self._send_json({"users": [public_user(user) for user in DATA["users"].values()]})
                return
            if command == "list_servers":
                self._send_json({"servers": list(DATA["servers"].values())})
                return
            if command == "internal_stats":
                self._send_json({"stats": {"users": len(DATA["users"]), "servers": len(DATA["servers"]), "messages": len(DATA["messages"]), "queuedPlayers": len(DATA["queue"]), "activeSessions": len(DATA["sessions"]), "service": "online", "maintenanceMode": bool(DATA.get("maintenanceMode"))}})
                return
            if command == "toggle_maintenance":
                DATA["maintenanceMode"] = bool(args.get("enabled"))
                save_data()
                self._send_json({"maintenanceMode": DATA["maintenanceMode"]})
                return
            if command == "clear_queue":
                removed = len(DATA["queue"])
                DATA["queue"] = []
                save_data()
                self._send_json({"cleared": True, "removed": removed})
                return
            if command == "clear_messages":
                removed = len(DATA["messages"])
                DATA["messages"] = []
                save_data()
                self._send_json({"cleared": True, "removed": removed})
                return
            if command == "delete_user":
                username = str(args.get("username", "")).strip().lower()
                if username in {"", actor["username"], "admin"} or username not in DATA["users"]:
                    self._send_json({"error": "That account cannot be deleted"}, 400)
                    return
                del DATA["users"][username]
                DATA["sessions"] = {token: name for token, name in DATA["sessions"].items() if name != username}
                DATA["queue"] = [item for item in DATA["queue"] if item["username"] != username]
                DATA["voice"].pop(username, None)
                save_data()
                self._send_json({"deleted": True, "username": username})
                return
            if command == "export_data":
                self._send_json({"export": {"users": [public_user(user) for user in DATA["users"].values()], "servers": list(DATA["servers"].values()), "messageCount": len(DATA["messages"]), "queueCount": len(DATA["queue"])}})
                return
            if command == "list_server_reviews":
                self._send_json({"reviews": DATA["serverReviews"]})
                return

            target = find_user(args.get("username"))
            if command == "assign_badge":
                if not target:
                    self._send_json({"error": "Target account was not found"}, 404)
                    return
                tag = str(args.get("tag", "CREW")).strip()[:20].upper()
                color = str(args.get("color", "#c5ed59")).strip()
                permissions = args.get("permissions", ["publish_updates", "moderate_chat"])
                if not tag or not isinstance(permissions, list):
                    self._send_json({"error": "A tag and permissions list are required"}, 400)
                    return
                target["role"] = "staff"
                target["staffProfile"] = {"tag": tag, "color": color, "permissions": [str(item) for item in permissions]}
                save_data()
                self._send_json({"updated": True, "user": public_user(target)})
            elif command == "remove_badge":
                if not target:
                    self._send_json({"error": "Target account was not found"}, 404)
                    return
                target["role"] = "member"
                target.pop("staffProfile", None)
                save_data()
                self._send_json({"updated": True, "user": public_user(target)})
            elif command == "set_permissions":
                if not target or target.get("role") != "staff":
                    self._send_json({"error": "Target must be an existing staff account"}, 404)
                    return
                permissions = args.get("permissions", [])
                if not isinstance(permissions, list):
                    self._send_json({"error": "Permissions must be a list"}, 400)
                    return
                target.setdefault("staffProfile", {})["permissions"] = [str(item) for item in permissions]
                save_data()
                self._send_json({"updated": True, "user": public_user(target)})
            elif command == "ban_user":
                if not target:
                    self._send_json({"error": "Target account was not found"}, 404)
                    return
                if target["username"] == actor["username"]:
                    self._send_json({"error": "You cannot ban your own account"}, 400)
                    return
                target["banned"] = True
                target["banReason"] = str(args.get("reason", "Banned by an administrator"))[:200]
                DATA["sessions"] = {token: username for token, username in DATA["sessions"].items() if username != target["username"]}
                save_data()
                self._send_json({"updated": True, "user": public_user(target), "reason": target["banReason"]})
            elif command == "unban_user":
                if not target:
                    self._send_json({"error": "Target account was not found"}, 404)
                    return
                target["banned"] = False
                target.pop("banReason", None)
                save_data()
                self._send_json({"updated": True, "user": public_user(target)})
            elif command in {"deactivate_user", "reactivate_user"}:
                if not target or target["username"] in {actor["username"], "admin"}:
                    self._send_json({"error": "That account cannot be changed"}, 400)
                    return
                target["deactivated"] = command == "deactivate_user"
                if target["deactivated"]:
                    DATA["sessions"] = {token: username for token, username in DATA["sessions"].items() if username != target["username"]}
                save_data()
                self._send_json({"updated": True, "user": public_user(target), "deactivated": target["deactivated"]})
            elif command == "delete_server":
                server_id = str(args.get("serverId", ""))
                if server_id not in DATA["servers"]:
                    self._send_json({"error": "Server was not found"}, 404)
                    return
                if server_id == "zorven":
                    self._send_json({"error": "The main Zorven server cannot be deleted"}, 400)
                    return
                deleted = DATA["servers"].pop(server_id)
                DATA["serverReviews"] = [review for review in DATA["serverReviews"] if review["serverId"] != server_id]
                owner = deleted.get("owner")
                if owner and owner in DATA["users"]:
                    DATA["directMessages"].append({"from": "zorven", "to": owner, "subject": "Community removed", "content": f"Your community server, {deleted['name']}, was removed by Zorven staff after review.", "createdAt": int(time.time()), "read": False})
                save_data()
                self._send_json({"deleted": True, "server": deleted})
            else:
                self._send_json({"error": "Unknown admin command"}, 400)
        elif path == "/api/matchmaking/join":
            user = get_user(self)
            if not user:
                self._send_json({"error": "Login required"}, 401)
                return
            game_id = str(payload.get("gameId", "zorven-first-light"))
            DATA["queue"] = [item for item in DATA["queue"] if item["username"] != user["username"]]
            DATA["queue"].append({"username": user["username"], "gameId": game_id, "joinedAt": int(time.time())})
            save_data()
            self._send_json({"queued": True, "position": len(DATA["queue"]), "gameId": game_id})
        elif path == "/api/store/checkout":
            user = get_user(self)
            if not user:
                self._send_json({"error": "Login required"}, 401)
                return
            order = {"id": secrets.token_hex(8), "username": user["username"], "item": payload.get("item", "Zorven Founder Pack"), "status": "test-approved", "createdAt": int(time.time())}
            DATA["orders"].append(order)
            save_data()
            self._send_json({"order": order, "message": "Test checkout approved. No real payment was processed."}, 201)
        elif path == "/api/messages":
            user = get_user(self)
            if not user:
                self._send_json({"error": "Login required"}, 401)
                return
            if is_banned(user):
                self._send_json({"error": "This account is banned"}, 403)
                return
            channel_id = str(payload.get("channelId", "general"))
            server_id = str(payload.get("serverId", "zorven"))
            server = DATA["servers"].get(server_id)
            content = str(payload.get("content", "")).strip()
            if not server or channel_id not in {channel["id"] for channel in server_channels(server)} or not content:
                self._send_json({"error": "A valid channel and message are required"}, 400)
                return
            identity = public_user(user)
            message = {"id": secrets.token_hex(8), "serverId": server_id, "channelId": channel_id, "username": user["username"], "role": identity["role"], "tag": identity["tag"], "badge": identity["badge"], "badgeColor": identity["badgeColor"], "content": content[:2000], "createdAt": int(time.time())}
            DATA["messages"].append(message)
            save_data()
            self._send_json({"message": message}, 201)
        else:
            self.send_error(404)

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), ZorvenHandler)
    print(f"Zorven platform running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Zorven platform")
    finally:
        server.server_close()
