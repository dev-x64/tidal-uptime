const form = document.getElementById("login-form");
const passwordInput = document.getElementById("password");
const submit = document.getElementById("submit");
const errorEl = document.getElementById("error");
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const password = passwordInput.value;
  if (!password) return;
  submit.disabled = true;
  errorEl.textContent = "";
  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (response.ok) { window.location.replace("/"); return; }
    let detail = "Invalid password";
    try {
      const payload = await response.json();
      if (payload && typeof payload.detail === "string") detail = payload.detail;
    } catch (_) {}
    errorEl.textContent = detail;
  } catch (err) {
    errorEl.textContent = "Sign-in failed. Try again.";
  } finally {
    submit.disabled = false;
    passwordInput.select();
  }
});
