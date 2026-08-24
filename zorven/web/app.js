(() => {
  const state = { token: localStorage.getItem("zorven-token") || "", user: null, channels: [], channel: "general", registerMode: false };
  const elements = {
    authDialog: document.querySelector("#authDialog"), authForm: document.querySelector("#authForm"), authHeading: document.querySelector("#authHeading"), authCopy: document.querySelector("#authCopy"), authSubmit: document.querySelector("#authSubmit"), authSwitch: document.querySelector("#authSwitch"), authError: document.querySelector("#authError"), username: document.querySelector("#usernameInput"), password: document.querySelector("#passwordInput"),
    serverDialog: document.querySelector("#serverDialog"), serverForm: document.querySelector("#serverForm"), serverName: document.querySelector("#serverNameInput"), serverError: document.querySelector("#serverError"),
    staffDialog: document.querySelector("#staffDialog"), staffForm: document.querySelector("#staffForm"), staffEyebrow: document.querySelector("#staffEyebrow"), staffHeading: document.querySelector("#staffHeading"), staffCopy: document.querySelector("#staffCopy"), staffSetupKey: document.querySelector("#setupKeyInput"), staffSetupKeyLabel: document.querySelector("#setupKeyLabel"), staffUsername: document.querySelector("#staffUsernameInput"), staffPassword: document.querySelector("#staffPasswordInput"), fullAccess: document.querySelector("#fullAccessInput"), fullAccessLabel: document.querySelector("#fullAccessLabel"), staffSubmit: document.querySelector("#staffSubmit"), staffError: document.querySelector("#staffError"),
    channelList: document.querySelector("#channelList"), title: document.querySelector("#channelTitle"), description: document.querySelector("#channelDescription"), messages: document.querySelector("#messages"), form: document.querySelector("#messageForm"), input: document.querySelector("#messageInput"), selfName: document.querySelector("#selfName"), selfStatus: document.querySelector("#selfStatus"), selfAvatar: document.querySelector("#selfAvatar"), memberList: document.querySelector("#memberList"), memberCount: document.querySelector("#memberCount"), onlineCount: document.querySelector("#onlineCount"), toast: document.querySelector("#toast"), panel: document.querySelector("#channelPanel")
  };

  async function api(path, options = {}) {
    const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}) };
    const response = await fetch(path, { ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 404 && path === "/api/staff/bootstrap") throw new Error("Staff setup is not deployed yet. Deploy the latest Zorven version, then try again.");
      throw new Error(data.error || "The request could not be completed.");
    }
    return data;
  }

  function initials(name) { return (name || "?").slice(0, 1).toUpperCase(); }
  function escapeHtml(value) { const node = document.createElement("span"); node.textContent = value; return node.innerHTML; }
  function formatTime(timestamp) { return timestamp ? new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(timestamp * 1000)) : "now"; }
  function notify(message) { elements.toast.textContent = message; elements.toast.classList.add("show"); window.clearTimeout(notify.timer); notify.timer = window.setTimeout(() => elements.toast.classList.remove("show"), 3200); }

  function renderIdentity() {
    const user = state.user;
    elements.selfName.textContent = user ? user.username : "Guest";
    elements.selfStatus.textContent = user ? (user.tag || "MEMBER") : "Sign in to join in";
    elements.selfAvatar.textContent = initials(user?.username);
    elements.memberList.innerHTML = user ? `<div class="member"><span class="avatar">${escapeHtml(initials(user.username))}</span><span>${escapeHtml(user.username)}</span></div><div class="member"><span class="avatar">Z</span><span>Zorven Team</span></div>` : `<div class="member"><span class="avatar">Z</span><span>Zorven Team</span></div>`;
    const count = user ? 2 : 1;
    elements.memberCount.textContent = count;
    elements.onlineCount.textContent = `${count} online`;
  }

  function renderChannels() {
    elements.channelList.innerHTML = state.channels.map(channel => `<button class="channel-button ${channel.id === state.channel ? "active" : ""}" type="button" data-channel="${escapeHtml(channel.id)}"><span class="hash">#</span>${escapeHtml(channel.name)}</button>`).join("");
    document.querySelectorAll("[data-channel]").forEach(button => button.addEventListener("click", () => selectChannel(button.dataset.channel)));
  }

  async function selectChannel(channelId) {
    state.channel = channelId;
    const channel = state.channels.find(item => item.id === channelId);
    elements.title.textContent = channel?.name || channelId;
    elements.description.textContent = channel?.description || "Community conversation.";
    elements.input.placeholder = `Message #${channel?.name || channelId}`;
    elements.panel.classList.remove("open");
    renderChannels();
    await loadMessages();
  }

  function messageMarkup(message) {
    const tag = message.role === "staff" ? `<span class="role-tag" style="--badge-color:${escapeHtml(message.badgeColor || "#d6f24a")}" aria-label="${escapeHtml(message.tag || "STAFF")} staff"><span class="staff-emblem" aria-hidden="true"><i></i><b></b></span><span>${escapeHtml(message.tag || "STAFF")}</span></span>` : "";
    return `<article class="message"><span class="avatar">${escapeHtml(initials(message.username))}</span><div><div class="message-meta"><strong>${escapeHtml(message.username)}</strong>${tag}<span class="message-time">${formatTime(message.createdAt)}</span></div><p class="message-body">${escapeHtml(message.content)}</p></div></article>`;
  }

  async function loadMessages() {
    elements.messages.innerHTML = `<section class="welcome"><div class="welcome-mark">#</div><h3>Welcome to #${escapeHtml(elements.title.textContent)}</h3><p>This is the start of the ${escapeHtml(elements.title.textContent)} channel.</p></section>`;
    try {
      const { messages } = await api(`/api/channels/${encodeURIComponent(state.channel)}/messages`);
      elements.messages.insertAdjacentHTML("beforeend", messages.map(messageMarkup).join(""));
      elements.messages.scrollTop = elements.messages.scrollHeight;
    } catch (error) { notify(error.message); }
  }

  async function bootstrap() {
    try {
      const [channelData, identity] = await Promise.all([api("/api/channels"), api("/api/me")]);
      state.channels = channelData.channels;
      state.user = identity.user;
      renderIdentity();
      await selectChannel(state.channels.some(channel => channel.id === state.channel) ? state.channel : state.channels[0]?.id);
    } catch (error) { elements.description.textContent = "Unable to reach the Zorven service."; notify(error.message); }
  }

  function openAuth(register = false) {
    state.registerMode = register;
    elements.authHeading.textContent = register ? "Create your Zorven account" : "Sign in to the community";
    elements.authCopy.textContent = register ? "Choose a name and a secure password to start chatting." : "Use your account to post messages and create servers.";
    elements.authSubmit.textContent = register ? "Create account" : "Sign in";
    elements.authSwitch.textContent = register ? "Already have an account? Sign in" : "Need an account? Create one";
    elements.authError.textContent = "";
    elements.password.autocomplete = register ? "new-password" : "current-password";
    elements.authDialog.showModal();
    elements.username.focus();
  }

  function openStaffPanel() {
    const canManage = state.user?.permissions?.includes("manage_members");
    const isBootstrap = !state.user;
    if (state.user && !canManage) return notify("You need staff management permission.");
    elements.staffEyebrow.textContent = isBootstrap ? "STAFF SETUP" : "STAFF PANEL";
    elements.staffHeading.textContent = isBootstrap ? "Create the first staff account" : "Create a staff account";
    elements.staffCopy.textContent = isBootstrap ? "Use the one-time setup key configured for this service." : "Create a staff account. Full-access staff can manage the community.";
    elements.staffSetupKeyLabel.hidden = !isBootstrap;
    elements.staffSetupKey.required = isBootstrap;
    elements.fullAccessLabel.hidden = isBootstrap;
    elements.fullAccess.checked = true;
    elements.staffError.textContent = "";
    elements.staffDialog.showModal();
    elements.staffUsername.focus();
  }

  document.querySelector("#accountButton").addEventListener("click", () => state.user?.permissions?.includes("manage_members") ? openStaffPanel() : state.user ? notify(`Signed in as ${state.user.username}`) : openAuth());
  document.querySelector("#newServerButton").addEventListener("click", () => state.user ? elements.serverDialog.showModal() : openAuth());
  document.querySelector(".add-server").addEventListener("click", () => state.user ? elements.serverDialog.showModal() : openAuth());
  document.querySelector("#menuButton").addEventListener("click", () => elements.panel.classList.toggle("open"));
  elements.authSwitch.addEventListener("click", () => openAuth(!state.registerMode));
  document.querySelector("#staffSetupButton").addEventListener("click", () => { elements.authDialog.close(); openStaffPanel(); });

  elements.authForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (event.submitter?.value === "cancel") return elements.authDialog.close();
    elements.authError.textContent = "";
    try {
      const payload = { username: elements.username.value.trim(), password: elements.password.value };
      if (state.registerMode) {
        await api("/api/auth/register", { method: "POST", body: JSON.stringify(payload) });
        notify("Account created. Please sign in."); openAuth(false); return;
      }
      const result = await api("/api/auth/login", { method: "POST", body: JSON.stringify(payload) });
      state.token = result.token; state.user = result.user; localStorage.setItem("zorven-token", state.token); renderIdentity(); elements.authDialog.close(); notify("You are signed in.");
    } catch (error) { elements.authError.textContent = error.message; }
  });

  elements.serverForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (event.submitter?.value === "cancel") return elements.serverDialog.close();
    try {
      const result = await api("/api/servers", { method: "POST", body: JSON.stringify({ name: elements.serverName.value.trim() }) });
      elements.serverDialog.close(); elements.serverName.value = ""; notify(`${result.server.name} created.`);
    } catch (error) { elements.serverError.textContent = error.message; }
  });

  elements.staffForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (event.submitter?.value === "cancel") return elements.staffDialog.close();
    elements.staffError.textContent = "";
    const payload = { username: elements.staffUsername.value.trim(), password: elements.staffPassword.value };
    try {
      if (state.user) {
        const result = await api("/api/staff/accounts", { method: "POST", body: JSON.stringify({ ...payload, tag: "STAFF", color: "#c5ed59", fullAccess: elements.fullAccess.checked }) });
        notify(`${result.user.username} is now staff.`);
      } else {
        const result = await api("/api/staff/bootstrap", { method: "POST", body: JSON.stringify({ ...payload, setupKey: elements.staffSetupKey.value }) });
        notify(`${result.user.username} was created. Sign in to open the staff panel.`);
      }
      elements.staffForm.reset();
      elements.staffDialog.close();
    } catch (error) { elements.staffError.textContent = error.message; }
  });

  elements.form.addEventListener("submit", async event => {
    event.preventDefault();
    const content = elements.input.value.trim();
    if (!state.user) return openAuth();
    if (!content) return;
    elements.input.disabled = true;
    try { await api("/api/messages", { method: "POST", body: JSON.stringify({ channelId: state.channel, content }) }); elements.input.value = ""; await loadMessages(); }
    catch (error) { notify(error.message); }
    finally { elements.input.disabled = false; elements.input.focus(); }
  });

  bootstrap();
  window.setInterval(() => { if (document.visibilityState === "visible") loadMessages(); }, 15000);
})();
