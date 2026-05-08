const API_LOGIN  = "http://127.0.0.1:5000/login";
const API_SIGNUP = "http://127.0.0.1:5000/signup";

/* ---- redirect if not logged in ---- */
const userId = sessionStorage.getItem("user_id");
const onPublicPage = window.location.href.includes("login.html") || window.location.href.includes("signup.html");
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
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (data.user_id) {
        sessionStorage.setItem("user_id",  data.user_id);
        sessionStorage.setItem("username", data.username);
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
        body: JSON.stringify({ username, email, password })
      });
      const data = await res.json();
      if (data.user_id) {
        sessionStorage.setItem("user_id",  data.user_id);
        sessionStorage.setItem("username", data.username);
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
  logoutBtn.addEventListener("click", () => {
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
