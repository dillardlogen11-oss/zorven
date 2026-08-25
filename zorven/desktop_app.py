import json
import os
import sys
import tkinter as tk
import webbrowser
from tkinter import messagebox
from urllib import request

DEFAULT_API = "http://127.0.0.1:8765"

# Palette matches the website's Discord-style theme (zorven/web/styles.css).
RAIL = "#1e1f22"
CHANNEL_PANEL = "#2b2d31"
CHAT_PANEL = "#313338"
INPUT_BG = "#383a40"
LINE = "#202225"
INK = "#edf2f7"
MUTED = "#a7aab0"
ACCENT = "#5865f2"
ONLINE = "#57e0c0"


def resolve_api_base_url(default=DEFAULT_API, argv=None):
    argv = sys.argv if argv is None else argv
    override = os.environ.get("ZORVEN_API_URL", "").strip()
    if not override:
        for index, value in enumerate(argv):
            if value in {"--host", "--api-url", "--base-url"} and index + 1 < len(argv):
                override = argv[index + 1].strip()
                break
    base_url = override or (default or DEFAULT_API)
    return base_url.rstrip("/")


API = resolve_api_base_url()


class ZorvenChat(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Zorven")
        self.geometry("1000x640")
        self.configure(bg=CHAT_PANEL)
        self.token = ""
        self.current_user = None
        self.channel = "general"
        self._build_ui()
        self.load_channels()
        self.load_team()
        self.after(15000, self._poll)

    # -- UI construction -------------------------------------------------
    def _build_ui(self):
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        # Server rail
        rail = tk.Frame(self, bg=RAIL, width=64)
        rail.grid(row=0, column=0, sticky="ns")
        rail.grid_propagate(False)
        tk.Label(rail, text="Z", bg=ACCENT, fg="white", font=("Segoe UI", 16, "bold"), width=2, height=1).pack(pady=14)

        # Channel panel
        channel_panel = tk.Frame(self, bg=CHANNEL_PANEL, width=240)
        channel_panel.grid(row=0, column=1, sticky="ns")
        channel_panel.grid_propagate(False)
        header = tk.Frame(channel_panel, bg=CHANNEL_PANEL, height=48)
        header.pack(fill="x")
        tk.Label(header, text="Zorven", bg=CHANNEL_PANEL, fg=INK, font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=12)
        tk.Label(header, text="\u25cf", bg=CHANNEL_PANEL, fg=ONLINE, font=("Segoe UI", 8)).pack(side="left")

        tk.Label(channel_panel, text="TEXT CHANNELS", bg=CHANNEL_PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(
            anchor="w", padx=14, pady=(10, 4)
        )
        self.channel_list = tk.Listbox(
            channel_panel, bg=CHANNEL_PANEL, fg=MUTED, selectbackground="#3f4148", selectforeground=INK,
            bd=0, highlightthickness=0, activestyle="none", font=("Segoe UI", 10),
        )
        self.channel_list.pack(fill="x", padx=8)
        self.channel_list.bind("<<ListboxSelect>>", self._select_channel)

        tk.Label(channel_panel, text="TEAM", bg=CHANNEL_PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(
            anchor="w", padx=14, pady=(16, 4)
        )
        self.team_list = tk.Listbox(
            channel_panel, bg=CHANNEL_PANEL, fg=MUTED, bd=0, highlightthickness=0, activestyle="none",
            font=("Segoe UI", 10), height=6,
        )
        self.team_list.pack(fill="both", expand=True, padx=8)

        # User bar (bottom of channel panel)
        user_bar = tk.Frame(channel_panel, bg="#232428", height=62)
        user_bar.pack(fill="x", side="bottom")
        self.self_avatar = tk.Label(user_bar, text="?", bg="#e7765f", fg="white", font=("Segoe UI", 10, "bold"), width=3, height=1)
        self.self_avatar.pack(side="left", padx=(10, 8), pady=10)
        name_box = tk.Frame(user_bar, bg="#232428")
        name_box.pack(side="left", fill="x", expand=True, pady=10)
        self.self_name = tk.Label(name_box, text="Guest", bg="#232428", fg=INK, font=("Segoe UI", 10, "bold"), anchor="w")
        self.self_name.pack(fill="x")
        self.self_status = tk.Label(name_box, text="Sign in to join in", bg="#232428", fg=MUTED, font=("Segoe UI", 8), anchor="w")
        self.self_status.pack(fill="x")
        self.logout_button = tk.Button(
            user_bar, text="\u23fb", command=self.logout, bg="#232428", fg=MUTED, bd=0, font=("Segoe UI", 10)
        )

        # Chat panel
        chat_panel = tk.Frame(self, bg=CHAT_PANEL)
        chat_panel.grid(row=0, column=2, sticky="nsew")
        chat_panel.rowconfigure(1, weight=1)
        chat_panel.columnconfigure(0, weight=1)

        chat_header = tk.Frame(chat_panel, bg=CHAT_PANEL, height=48, highlightbackground=LINE, highlightthickness=0)
        chat_header.grid(row=0, column=0, sticky="ew")
        tk.Label(chat_header, text="#", bg=CHAT_PANEL, fg="#7e8998", font=("Segoe UI", 15, "bold")).pack(side="left", padx=(20, 6), pady=12)
        self.channel_title = tk.Label(chat_header, text="general", bg=CHAT_PANEL, fg=INK, font=("Segoe UI", 12, "bold"))
        self.channel_title.pack(side="left", pady=12)

        self.messages = tk.Text(
            chat_panel, bg=CHAT_PANEL, fg="#d4cbd9", bd=0, wrap="word", state="disabled",
            font=("Segoe UI", 10), padx=20, pady=10,
        )
        self.messages.grid(row=1, column=0, sticky="nsew")

        composer = tk.Frame(chat_panel, bg=CHAT_PANEL)
        composer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.message_entry = tk.Entry(composer, bg=INPUT_BG, fg=INK, insertbackground=INK, bd=0)
        self.message_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.message_entry.bind("<Return>", lambda _event: self.send_message())
        tk.Button(
            composer, text="Send", command=self.send_message, bg=ACCENT, fg="white",
            font=("Segoe UI", 10, "bold"), bd=0, padx=16,
        ).pack(side="left")

        # Auth bar
        auth = tk.Frame(chat_panel, bg=CHAT_PANEL)
        auth.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 14))
        tk.Label(auth, text="Username", bg=CHAT_PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        self.username = tk.Entry(auth, bg=INPUT_BG, fg=INK, insertbackground=INK, bd=0, width=14)
        self.username.pack(side="left", padx=6, ipady=4)
        tk.Label(auth, text="Password", bg=CHAT_PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        self.password = tk.Entry(auth, bg=INPUT_BG, fg=INK, insertbackground=INK, bd=0, width=14, show="*")
        self.password.pack(side="left", padx=6, ipady=4)
        tk.Button(auth, text="Register", command=self.register, bg=CHANNEL_PANEL, fg=INK, bd=0, padx=10).pack(side="left", padx=4)
        tk.Button(auth, text="Log in", command=self.login, bg=ACCENT, fg="white", bd=0, padx=10).pack(side="left", padx=4)
        self.status = tk.Label(auth, text="Not signed in", bg=CHAT_PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.status.pack(side="right")

        # Members panel
        members_panel = tk.Frame(self, bg=CHANNEL_PANEL, width=200)
        members_panel.grid(row=0, column=3, sticky="ns")
        members_panel.grid_propagate(False)
        tk.Label(members_panel, text="ONLINE", bg=CHANNEL_PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=14, pady=(18, 8)
        )
        self.member_list = tk.Listbox(
            members_panel, bg=CHANNEL_PANEL, fg="#c4ccd5", bd=0, highlightthickness=0, activestyle="none",
            font=("Segoe UI", 10),
        )
        self.member_list.pack(fill="both", expand=True, padx=8)

    def api(self, path, method="GET", payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(API + path, data=data, headers=headers, method=method)
        with request.urlopen(req) as response:
            return json.loads(response.read().decode())

    def load_channels(self):
        try:
            channels = self.api("/api/channels")["channels"]
            self.channel_list.delete(0, tk.END)
            for channel in channels:
                self.channel_list.insert(tk.END, channel["name"])
            self.channel_list.selection_set(0)
            self.refresh_messages()
        except Exception as error:
            self.status.config(text="Start start_zorven_chat.bat first")
            self.log_local(str(error))

    def load_team(self):
        try:
            team = self.api("/api/team")["team"]
            self.team_list.delete(0, tk.END)
            self.member_list.delete(0, tk.END)
            for member in team:
                label = f"{member['username']} [{member.get('tag', 'CREW')}]"
                self.team_list.insert(tk.END, label)
                self.member_list.insert(tk.END, label)
            if self.current_user and not any(member["username"] == self.current_user["username"] for member in team):
                self.member_list.insert(tk.END, f"{self.current_user['username']} [{self.current_user['tag']}]")
        except Exception:
            pass

    def _select_channel(self, _event):
        selection = self.channel_list.curselection()
        if selection:
            self.channel = self.channel_list.get(selection[0])
            self.channel_title.config(text=self.channel)
            self.refresh_messages()

    def refresh_messages(self):
        try:
            messages = self.api(f"/api/channels/{self.channel}/messages")["messages"]
            self.messages.config(state="normal")
            self.messages.delete("1.0", tk.END)
            for message in messages:
                tag = f" [{message.get('tag', 'CREW')}]" if message.get("role") == "staff" else ""
                self.messages.insert(tk.END, f"{message['username']}{tag}  {message['content']}\n\n")
            self.messages.config(state="disabled")
        except Exception:
            pass

    def register(self):
        try:
            self.api("/api/auth/register", "POST", {"username": self.username.get(), "password": self.password.get()})
            self.status.config(text="Account created; log in")
        except Exception as error:
            messagebox.showerror("Register failed", str(error))

    def login(self):
        try:
            data = self.api("/api/auth/login", "POST", {"username": self.username.get(), "password": self.password.get()})
            self.token = data["token"]
            self.current_user = data["user"]
            self._apply_identity()
            self.status.config(text=f"Signed in as {data['user']['username']}")
            self.username.delete(0, tk.END)
            self.password.delete(0, tk.END)
            self.load_team()
        except Exception as error:
            messagebox.showerror("Login failed", str(error))

    def logout(self):
        if self.token:
            try:
                self.api("/api/auth/logout", "POST")
            except Exception:
                pass
        self.token = ""
        self.current_user = None
        self._apply_identity()
        self.status.config(text="Not signed in")
        self.load_team()

    def _apply_identity(self):
        user = self.current_user
        self.self_name.config(text=user["displayName"] if user else "Guest")
        self.self_status.config(text=user["tag"] if user else "Sign in to join in")
        self.self_avatar.config(text=(user["username"][:1].upper() if user else "?"), bg=(ACCENT if user else "#e7765f"))
        if user:
            self.logout_button.pack(side="right", padx=(0, 10))
        else:
            self.logout_button.pack_forget()

    def send_message(self):
        if not self.token:
            messagebox.showwarning("Sign in required", "Log in before sending a message.")
            return
        content = self.message_entry.get().strip()
        if not content:
            return
        try:
            self.api("/api/messages", "POST", {"channelId": self.channel, "content": content})
            self.message_entry.delete(0, tk.END)
            self.refresh_messages()
        except Exception as error:
            messagebox.showerror("Message failed", str(error))

    def log_local(self, message):
        self.messages.config(state="normal")
        self.messages.insert(tk.END, message)
        self.messages.config(state="disabled")

    # -- live sync, mirrors the website's 15s polling loop --------------
    def _poll(self):
        self.refresh_messages()
        self.load_team()
        self.after(15000, self._poll)


def main():
    try:
        ZorvenChat().mainloop()
        return 0
    except tk.TclError as error:
        if "display" in str(error).lower() or "no display" in str(error).lower():
            login_url = f"{API}/login"
            if webbrowser.open(login_url):
                return 0
            print(
                "Zorven desktop app requires a graphical desktop session. "
                "The browser version opened instead, or you can run the app on a machine with a display."
                "\n"
                f"Login URL: {login_url}\n"
                f"Details: {error}",
                file=sys.stderr,
            )
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
