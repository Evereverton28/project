/* shared toast notification — replaces all alert() / showMessage() calls
   Usage: showToast("message")  or  showToast("message", "success"|"danger")
*/
function showToast(msg, type = "default") {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = type;
  toast.style.display = "block";
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => { toast.style.display = "none"; }, 2800);
}
