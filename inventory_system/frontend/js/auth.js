const API_LOGIN = "http://127.0.0.1:5000/login";
const API_SIGNUP = "http://127.0.0.1:5000/signup";

// ---------------- LOGIN CHECK (for all protected pages) ----------------
const userId = sessionStorage.getItem("user_id");
if (!userId && !window.location.href.includes("login.html") && !window.location.href.includes("signup.html")) {
  // redirect to login if not logged in and not on login/signup page
  window.location.href = "login.html";
}

// ---------------- Login ----------------
const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", e => {
    e.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    fetch(API_LOGIN, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    })
    .then(res => res.json())
    .then(data => {
      if (data.user_id) {
        sessionStorage.setItem("user_id", data.user_id);
        sessionStorage.setItem("username", data.username);
        window.location.href = "index.html";
      } else {
        alert(data.error || "Login failed");
      }
    });
  });
}

// ---------------- Signup ----------------
const signupForm = document.getElementById("signupForm");
if (signupForm) {
  signupForm.addEventListener("submit", e => {
    e.preventDefault();
    const username = document.getElementById("signupUsername").value.trim();
    const email = document.getElementById("signupEmail").value.trim();
    const password = document.getElementById("signupPassword").value.trim();
    const confirmPassword = document.getElementById("signupConfirmPassword").value.trim();

    if (password !== confirmPassword) {
      alert("Passwords do not match!");
      return;
    }

    fetch(API_SIGNUP, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password })
    })
    .then(res => res.json())
    .then(data => {
      if (data.user_id) {
        // Automatically log the user in
        sessionStorage.setItem("user_id", data.user_id);
        sessionStorage.setItem("username", data.username);
        window.location.href = "index.html";
      } else {
        alert(data.error || "Signup failed");
      }
    });
  });
}

// ---------------- Logout ----------------
const logoutBtn = document.getElementById("logoutBtn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    sessionStorage.clear();
    window.location.href = "login.html";
  });
}

// ---------------- Display logged-in username ----------------
const usernameSpan = document.getElementById("userInfo");
if (usernameSpan) {
  const storedUsername = sessionStorage.getItem("username");
  if (storedUsername) {
    usernameSpan.textContent = `Logged in as: ${storedUsername}`;
    usernameSpan.style.color = "#ffffff"; // visible
  }
}