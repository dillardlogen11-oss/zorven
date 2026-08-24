import json
import tkinter as tk
from tkinter import messagebox, ttk
from urllib import request

API = "http://127.0.0.1:8765"


class ZorvenChat(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Zorven Community")
        self.geometry("900x600")
        self.token = ""
        self.channel = "general"
        self._build_ui()
        self.load_channels()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        sidebar = ttk.Frame(self, padding=12)
        sidebar.grid(row=0, column=0, sticky="nsew")
        ttk.Label(sidebar, text="ZORVEN", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 16))
        ttk.Label(sidebar, text="Community").pack(anchor="w")
        self.channels = tk.Listbox(sidebar, width=22, height=18, activestyle="none")
        self.channels.pack(fill="y", expand=True, pady=8)
        self.channels.bind("<<ListboxSelect>>", self.select_channel)

        content = ttk.Frame(self, padding=(0, 12, 12, 12))
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)
        self.channel_title = ttk.Label(content, text="# general", font=("Segoe UI", 16, "bold"))
        self.channel_title.grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.messages = tk.Text(content, state="disabled", wrap="word", font=("Segoe UI", 10))
        self.messages.grid(row=1, column=0, sticky="nsew")
        composer = ttk.Frame(content)
        composer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        composer.columnconfigure(0, weight=1)
        self.message_entry = ttk.Entry(composer)
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.message_entry.bind("<Return>", lambda _event: self.send_message())
        ttk.Button(composer, text="Send", command=self.send_message).grid(row=0, column=1)

        auth = ttk.Frame(self, padding=12)
        auth.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttk.Label(auth, text="Username").pack(side="left")
        self.username = ttk.Entry(auth, width=16)
        self.username.pack(side="left", padx=6)
        ttk.Label(auth, text="Password").pack(side="left")
        self.password = ttk.Entry(auth, width=16, show="*")
        self.password.pack(side="left", padx=6)
        ttk.Button(auth, text="Register", command=self.register).pack(side="left", padx=4)
        ttk.Button(auth, text="Log in", command=self.login).pack(side="left", padx=4)
        self.status = ttk.Label(auth, text="Not signed in")
        self.status.pack(side="right")

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
            self.channels.delete(0, tk.END)
            for channel in channels:
                self.channels.insert(tk.END, channel["name"])
            self.channels.selection_set(0)
            self.refresh_messages()
        except Exception as error:
            self.status.config(text="Start start_zorven.bat first")
            self.log_local(str(error))

    def select_channel(self, _event):
        selection = self.channels.curselection()
        if selection:
            self.channel = self.channels.get(selection[0])
            self.channel_title.config(text=f"# {self.channel}")
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
            self.status.config(text=f"Signed in as {data['user']['username']} [{data['user']['tag']}]")
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
            self.refresh_messages()
        except Exception as error:
            messagebox.showerror("Message failed", str(error))

    def log_local(self, message):
        self.messages.config(state="normal")
        self.messages.insert(tk.END, message)
        self.messages.config(state="disabled")


if __name__ == "__main__":
    ZorvenChat().mainloop()
