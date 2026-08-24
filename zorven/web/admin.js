(() => {
  const state = { token: localStorage.getItem("zorven-token") || "", user: null, users: [] };
  const elements = {
    loginGate: document.querySelector("#loginGate"), content: document.querySelector("#adminContent"), identity: document.querySelector("#adminIdentity"),
    username: document.querySelector("#adminUsername"), password: document.querySelector("#adminPassword"), loginButton: document.querySelector("#adminLoginButton"), loginError: document.querySelector("#loginError"),
    statsGrid: document.querySelector("#statsGrid"), usersTable: document.querySelector("#usersTable"), usersError: document.querySelector("#usersError"),
    search: document.querySelector("#userSearch"), refresh: document.querySelector("#refreshUsers"), clearQueue: document.querySelector("#clearQueueButton"), exportData: document.querySelector("#exportDataButton"),
    toast: document.querySelector("#toast"),
  };

  function escapeHtml(value) { const node = document.createElement("span"); node.textContent = value; return node.innerHTML; }
  function notify(message) { elements.toast.textContent = message; elements.toast.classList.add("show"); window.clearTimeout(notify.timer); notify.timer = window.setTimeout(() => elements.toast.classList.remove("show"), 3200); }

  async function api(path, options = {}) {
    const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}) };
    const response = await fetch(path, { ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "The request could not be completed.");
    return data;
  }

  async function command(name, args = {}) {
    return api("/api/admin/command", { method: "POST", body: JSON.stringify({ command: name, args }) });
  }

  async function login() {
    elements.loginError.textContent = "";
    try {
      const result = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ username: elements.username.value.trim(), password: elements.password.value }) });
      state.token = result.token;
      localStorage.setItem("zorven-token", state.token);
      await bootstrap();
    } catch (error) { elements.loginError.textContent = error.message; }
  }

  function renderStats(stats) {
    const entries = [["Accounts", stats.users], ["Servers", stats.servers], ["Messages", stats.messages], ["Queued players", stats.queuedPlayers], ["Active sessions", stats.activeSessions]];
    elements.statsGrid.innerHTML = entries.map(([label, value]) => `<div class="admin-stat"><strong>${escapeHtml(String(value))}</strong><span>${escapeHtml(label.toUpperCase())}</span></div>`).join("");
  }

  function renderUsers() {
    const query = elements.search.value.trim().toLowerCase();
    const filtered = state.users.filter(user => user.username.includes(query));
    elements.usersTable.innerHTML = filtered.map(user => {
      const badges = `${user.role === "staff" ? `<span class="admin-badge staff">${escapeHtml(user.tag)}</span>` : ""}${user.banned ? `<span class="admin-badge banned">BANNED</span>` : ""}`;
      const actions = user.banned
        ? `<button type="button" data-action="unban" data-username="${escapeHtml(user.username)}">Unban</button>`
        : `<button type="button" class="danger" data-action="ban" data-username="${escapeHtml(user.username)}">Ban</button>`;
      const staffToggle = user.role === "staff"
        ? `<button type="button" data-action="remove-badge" data-username="${escapeHtml(user.username)}">Remove staff</button>`
        : `<button type="button" data-action="assign-badge" data-username="${escapeHtml(user.username)}">Make staff</button>`;
      return `<div class="admin-row"><div class="admin-row-identity"><strong>${escapeHtml(user.username)}</strong>${badges}</div><div class="admin-row-actions">${staffToggle}${actions}</div></div>`;
    }).join("") || `<p class="dialog-copy">No accounts match your search.</p>`;
    document.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => handleUserAction(button.dataset.action, button.dataset.username)));
  }

  async function handleUserAction(action, username) {
    elements.usersError.textContent = "";
    try {
      if (action === "ban") {
        const reason = window.prompt(`Reason for banning ${username}?`, "Violated community guidelines") || "Banned by an administrator";
        await command("ban_user", { username, reason });
      } else if (action === "unban") {
        await command("unban_user", { username });
      } else if (action === "assign-badge") {
        await command("assign_badge", { username, tag: "STAFF", color: "#c5ed59", permissions: ["publish_updates", "moderate_chat"] });
      } else if (action === "remove-badge") {
        await command("remove_badge", { username });
      }
      notify(`Updated ${username}.`);
      await loadUsers();
    } catch (error) { elements.usersError.textContent = error.message; }
  }

  async function loadUsers() {
    try {
      const result = await command("list_users");
      state.users = result.users.sort((left, right) => left.username.localeCompare(right.username));
      renderUsers();
    } catch (error) { elements.usersError.textContent = error.message; }
  }

  async function loadStats() {
    try { renderStats((await command("internal_stats")).stats); } catch (error) { notify(error.message); }
  }

  elements.clearQueue.addEventListener("click", async () => {
    try { const result = await command("clear_queue"); notify(`Cleared ${result.removed} queued players.`); await loadStats(); } catch (error) { notify(error.message); }
  });

  elements.exportData.addEventListener("click", async () => {
    try {
      const result = await command("export_data");
      const blob = new Blob([JSON.stringify(result.export, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "zorven-export.json";
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (error) { notify(error.message); }
  });

  elements.refresh.addEventListener("click", loadUsers);
  elements.search.addEventListener("input", renderUsers);
  elements.loginButton.addEventListener("click", login);
  elements.password.addEventListener("keydown", event => { if (event.key === "Enter") login(); });

  async function bootstrap() {
    if (!state.token) { elements.loginGate.hidden = false; elements.content.hidden = true; return; }
    try {
      const identity = await api("/api/me");
      if (!identity.user || !identity.user.permissions.includes("manage_members")) {
        elements.loginError.textContent = identity.user ? "This account does not have member management permission." : "";
        elements.loginGate.hidden = false;
        elements.content.hidden = true;
        return;
      }
      state.user = identity.user;
      elements.identity.textContent = `${state.user.username} - ${state.user.tag}`;
      elements.loginGate.hidden = true;
      elements.content.hidden = false;
      await Promise.all([loadStats(), loadUsers()]);
    } catch {
      elements.loginGate.hidden = false;
      elements.content.hidden = true;
    }
  }

  bootstrap();
})();
