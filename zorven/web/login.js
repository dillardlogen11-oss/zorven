(() => {
  const form = document.querySelector("#loginForm");
  const username = document.querySelector("#loginUsername");
  const password = document.querySelector("#loginPassword");
  const error = document.querySelector("#loginError");
  document.querySelector("#registerButton").addEventListener("click", () => { window.location.href = "/server?register=1"; });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    error.textContent = "";
    try {
      const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: username.value.trim(), password: password.value }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "The request could not be completed.");
      localStorage.setItem("zorven-token", data.token);
      window.location.href = "/server";
    } catch (loginError) { error.textContent = loginError.message; }
  });
})();
