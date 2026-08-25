import json
import os
import sys
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox
from urllib import request

DEFAULT_API = "http://127.0.0.1:8765"

BG = "#0b0d12"
PANEL = "#12141c"
PANEL_LINE = "#1f2430"
INK = "#edf2f7"
MUTED = "#8b93a1"
ACCENT_GREEN = "#22c55e"
ACCENT_PURPLE = "#8b7bff"
ACCENT_BLUE = "#38bdf8"
ACCENT_GOLD = "#eab308"
ACCENT_RED = "#ef4444"


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


def format_duration(total_seconds):
    total_seconds = max(0, int(total_seconds))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes:02d}:{seconds:02d}"


class StatCard(tk.Frame):
    """A dashboard tile showing a big value and a small caption."""

    def __init__(self, parent, caption, value="0", color=ACCENT_GREEN):
        super().__init__(parent, bg=PANEL, highlightbackground=PANEL_LINE, highlightthickness=1)
        self.value_label = tk.Label(self, text=value, bg=PANEL, fg=color, font=("Segoe UI", 20, "bold"))
        self.value_label.pack(pady=(16, 2))
        tk.Label(
            self, text=caption.upper(), bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")
        ).pack(pady=(0, 14))

    def set_value(self, value):
        self.value_label.config(text=value)


class CountdownRing(tk.Canvas):
    """Circular countdown indicator to the next auto-refresh."""

    def __init__(self, parent, size=140):
        super().__init__(parent, width=size, height=size, bg=PANEL, highlightthickness=0)
        self.size = size

    def render(self, remaining, total, caption):
        self.delete("all")
        pad = 8
        fraction = 0 if total <= 0 else max(0.0, min(1.0, remaining / total))
        self.create_oval(pad, pad, self.size - pad, self.size - pad, outline=PANEL_LINE, width=8)
        if fraction > 0:
            self.create_arc(
                pad, pad, self.size - pad, self.size - pad,
                start=90, extent=-360 * fraction,
                style="arc", outline=ACCENT_PURPLE, width=8,
            )
        self.create_text(self.size / 2, self.size / 2 - 10, text=caption, fill=INK, font=("Segoe UI", 15, "bold"))
        self.create_text(self.size / 2, self.size / 2 + 16, text="Next refresh", fill=MUTED, font=("Segoe UI", 8, "bold"))


class ZorvenChat(tk.Tk):
    REFRESH_SECONDS = 15

    def __init__(self):
        super().__init__()
        self.title("Zorven Desktop")
        self.geometry("980x680")
        self.configure(bg=BG)
        self.token = ""
        self.current_user = None
        self.channel = "general"
        self.channels = []
        self.sent_count = 0
        self.start_time = time.time()
        self.next_refresh_at = time.time() + self.REFRESH_SECONDS
        self._build_ui()
        self.load_channels()
        self.load_team()
        self._tick()

    # -- UI construction -------------------------------------------------
    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(header, text="Zorven Desktop", bg=BG, fg=INK, font=("Segoe UI", 16, "bold")).pack(side="left")
        self.connection_dot = tk.Label(header, text="\u25cf", bg=BG, fg=MUTED, font=("Segoe UI", 12))
        self.connection_dot.pack(side="right")
        tk.Label(header, text="Status", bg=BG, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="right", padx=(0, 6))

        stats_row = tk.Frame(self, bg=BG)
        stats_row.pack(fill="x", padx=20, pady=8)
        for index in range(4):
            stats_row.columnconfigure(index, weight=1)
        self.sent_card = StatCard(stats_row, "Sent", "0", ACCENT_GREEN)
        self.uptime_card = StatCard(stats_row, "Uptime", "00:00", ACCENT_PURPLE)
        self.refresh_card = StatCard(stats_row, "Next refresh", f"{self.REFRESH_SECONDS}s", ACCENT_BLUE)
        self.channels_card = StatCard(stats_row, "Channels", "0", ACCENT_GOLD)
        for column, card in enumerate((self.sent_card, self.uptime_card, self.refresh_card, self.channels_card)):
            card.grid(row=0, column=column, sticky="nsew", padx=6)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=0)
        body.rowconfigure(1, weight=1)

        # Account card
        account_card = tk.Frame(body, bg=PANEL, highlightbackground=PANEL_LINE, highlightthickness=1)
        account_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        tk.Label(account_card, text="ACCOUNT", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6)
        )
        self.account_rows = tk.Frame(account_card, bg=PANEL)
        self.account_rows.pack(fill="x", padx=16, pady=(0, 14))
        self.account_labels = {}
        for key, label in (("user", "User"), ("server", "Server"), ("channel", "Channel"), ("status", "Status")):
            row = tk.Frame(self.account_rows, bg=PANEL)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label.upper(), bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold"), width=10, anchor="w").pack(side="left")
            value = tk.Label(row, text="-", bg=PANEL, fg=INK, font=("Segoe UI", 10, "bold"), anchor="w")
            value.pack(side="left", fill="x", expand=True)
            self.account_labels[key] = value

        # Countdown card
        countdown_card = tk.Frame(body, bg=PANEL, highlightbackground=PANEL_LINE, highlightthickness=1)
        countdown_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
        tk.Label(countdown_card, text="AUTO-REFRESH", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6)
        )
        self.countdown_ring = CountdownRing(countdown_card)
        self.countdown_ring.pack(pady=(0, 14))

        # Channels + team panel
        side_panel = tk.Frame(body, bg=PANEL, highlightbackground=PANEL_LINE, highlightthickness=1)
        side_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(side_panel, text="CHANNELS", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6)
        )
        self.channel_list = tk.Listbox(
            side_panel, bg="#181b24", fg=INK, bd=0, highlightthickness=0, activestyle="none", height=8
        )
        self.channel_list.pack(fill="x", padx=16)
        self.channel_list.bind("<<ListboxSelect>>", self._select_channel)
        tk.Label(side_panel, text="TEAM ONLINE", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6)
        )
        self.team_list = tk.Listbox(
            side_panel, bg="#181b24", fg=INK, bd=0, highlightthickness=0, activestyle="none", height=6
        )
        self.team_list.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # Chat + activity log panel
        chat_card = tk.Frame(body, bg=PANEL, highlightbackground=PANEL_LINE, highlightthickness=1)
        chat_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        header_row = tk.Frame(chat_card, bg=PANEL)
        header_row.pack(fill="x", padx=16, pady=(14, 6))
        self.channel_title = tk.Label(header_row, text="# general", bg=PANEL, fg=INK, font=("Segoe UI", 12, "bold"))
        self.channel_title.pack(side="left")
        self.messages = tk.Text(chat_card, bg="#181b24", fg=INK, bd=0, wrap="word", state="disabled", font=("Segoe UI", 10))
        self.messages.pack(fill="both", expand=True, padx=16)

        composer = tk.Frame(chat_card, bg=PANEL)
        composer.pack(fill="x", padx=16, pady=12)
        self.message_entry = tk.Entry(composer, bg="#181b24", fg=INK, insertbackground=INK, bd=0)
        self.message_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.message_entry.bind("<Return>", lambda _event: self.send_message())
        tk.Button(
            composer, text="Send", command=self.send_message, bg=ACCENT_GREEN, fg="#062012",
            font=("Segoe UI", 10, "bold"), bd=0, padx=16,
        ).pack(side="left")

        # Auth bar
        auth = tk.Frame(self, bg=BG)
        auth.pack(fill="x", padx=20, pady=(4, 16))
        tk.Label(auth, text="Username", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        self.username = tk.Entry(auth, bg=PANEL, fg=INK, insertbackground=INK, bd=0, width=16)
        self.username.pack(side="left", padx=6, ipady=4)
        tk.Label(auth, text="Password", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        self.password = tk.Entry(auth, bg=PANEL, fg=INK, insertbackground=INK, bd=0, width=16, show="*")
        self.password.pack(side="left", padx=6, ipady=4)
        tk.Button(auth, text="Register", command=self.register, bg=PANEL, fg=INK, bd=0, padx=10).pack(side="left", padx=4)
        tk.Button(auth, text="Log in", command=self.login, bg=ACCENT_PURPLE, fg="#0d0620", bd=0, padx=10).pack(side="left", padx=4)
        self.status = tk.Label(auth, text="Not signed in", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.status.pack(side="right")

        self._update_account_labels()

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
            self.channels = self.api("/api/channels")["channels"]
            self.channel_list.delete(0, tk.END)
            for channel in self.channels:
                self.channel_list.insert(tk.END, channel["name"])
            self.channel_list.selection_set(0)
            self.channels_card.set_value(str(len(self.channels)))
            self.connection_dot.config(fg=ACCENT_GREEN)
            self.refresh_messages()
        except Exception as error:
            self.status.config(text="Start start_zorven.bat first")
            self.connection_dot.config(fg=ACCENT_RED)
            self.log_local(str(error))

    def load_team(self):
        try:
            team = self.api("/api/team")["team"]
            self.team_list.delete(0, tk.END)
            for member in team:
                self.team_list.insert(tk.END, f"{member['username']} [{member.get('tag', 'CREW')}]")
        except Exception:
            pass

    def _select_channel(self, _event):
        selection = self.channel_list.curselection()
        if selection:
            self.channel = self.channel_list.get(selection[0])
            self.channel_title.config(text=f"# {self.channel}")
            self._update_account_labels()
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
            self.status.config(text=f"Signed in as {data['user']['username']} [{data['user']['tag']}]")
            self._update_account_labels()
        except Exception as error:
            messagebox.showerror("Login failed", str(error))

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
            self.sent_count += 1
            self.sent_card.set_value(str(self.sent_count))
            self.refresh_messages()
        except Exception as error:
            messagebox.showerror("Message failed", str(error))

    def log_local(self, message):
        self.messages.config(state="normal")
        self.messages.insert(tk.END, message)
        self.messages.config(state="disabled")

    def _update_account_labels(self):
        user = self.current_user["username"] if self.current_user else "Guest"
        status = f"Signed in as {user}" if self.current_user else "Not signed in"
        self.account_labels["user"].config(text=user)
        self.account_labels["server"].config(text="Zorven")
        self.account_labels["channel"].config(text=f"#{self.channel}")
        self.account_labels["status"].config(text=status)

    # -- periodic refresh --------------------------------------------
    def _tick(self):
        elapsed = time.time() - self.start_time
        self.uptime_card.set_value(format_duration(elapsed))
        remaining = self.next_refresh_at - time.time()
        if remaining <= 0:
            self.refresh_messages()
            self.next_refresh_at = time.time() + self.REFRESH_SECONDS
            remaining = self.REFRESH_SECONDS
        self.refresh_card.set_value(f"{int(remaining)}s")
        self.countdown_ring.render(remaining, self.REFRESH_SECONDS, f"{int(remaining)}s")
        self.after(1000, self._tick)


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
