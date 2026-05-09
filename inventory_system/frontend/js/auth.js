// FIX #1: toast.js MUST be loaded before this file on every page that uses auth.js.
//          login.html and signup.html now include toast.js first.

const API_LOGIN  = "http://127.0.0.1:5000/login";
const API_SIGNUP = "http://127.0.0.1:5000/signup";
const API_LOGOUT = "http://127.0.0.1:5000/logout";

/* ---- FIX #6: helper to build auth headers for every fetch call ---- */
function authHeaders(extra = {}) {
  const token = sessionStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    ...extra,
  };
}

/* ---- redirect if not logged in ---- */
const userId = sessionStorage.getItem("user_id");
const onPublicPage =
  window.location.href.includes("login.html") ||
  window.location.href.includes("signup.html");

if (!userId && !onPublicPage) {
  window.location.href = "login.html";
}

/* ---- Login ---- */
const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async e => {
    e.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    try {
      const res  = await fetch(API_LOGIN, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (data.user_id) {
        sessionStorage.setItem("user_id",  data.user_id);
        sessionStorage.setItem("username", data.username);
        sessionStorage.setItem("token",    data.token);   // FIX #6
        window.location.href = "index.html";
      } else {
        showToast(data.error || "Login failed", "danger");
      }
    } catch {
      showToast("Could not reach server", "danger");
    }
  });
}

/* ---- Signup ---- */
const signupForm = document.getElementById("signupForm");
if (signupForm) {
  signupForm.addEventListener("submit", async e => {
    e.preventDefault();
    const username        = document.getElementById("signupUsername").value.trim();
    const email           = document.getElementById("signupEmail").value.trim();
    const password        = document.getElementById("signupPassword").value.trim();
    const confirmPassword = document.getElementById("signupConfirmPassword").value.trim();

    if (password !== confirmPassword) {
      showToast("Passwords do not match", "danger");
      return;
    }

    try {
      const res  = await fetch(API_SIGNUP, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });
      const data = await res.json();
      if (data.user_id) {
        sessionStorage.setItem("user_id",  data.user_id);
        sessionStorage.setItem("username", data.username);
        sessionStorage.setItem("token",    data.token);   // FIX #6
        window.location.href = "index.html";
      } else {
        showToast(data.error || "Signup failed", "danger");
      }
    } catch {
      showToast("Could not reach server", "danger");
    }
  });
}

/* ---- Logout ---- */
const logoutBtn = document.getElementById("logoutBtn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    try {
      // Tell the server to invalidate the token
      await fetch(API_LOGOUT, {
        method: "POST",
        headers: authHeaders(),
      });
    } catch { /* server unreachable — clear locally anyway */ }

    sessionStorage.clear();
    window.location.href = "login.html";
  });
}

/* ---- Sidebar username ---- */
const usernameSpan = document.getElementById("userInfo");
if (usernameSpan) {
  const stored = sessionStorage.getItem("username");
  if (stored) usernameSpan.textContent = stored;
}
