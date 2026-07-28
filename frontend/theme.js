const themeToggle = document.querySelector("#theme-toggle");
const themeIcon = document.querySelector("#theme-icon");
const themeLabel = document.querySelector("#theme-label");
const themePreferenceKey = "broadcastToolPro.theme";

function applyTheme(theme) {
  const dark = theme === "dark";
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  themeToggle.setAttribute("aria-pressed", String(dark));
  themeToggle.setAttribute(
    "aria-label",
    dark ? "Switch to light mode" : "Switch to dark mode",
  );
  themeIcon.textContent = dark ? "☀" : "☾";
  themeLabel.textContent = dark ? "Light Mode" : "Dark Mode";
}

themeToggle.addEventListener("click", () => {
  const nextTheme = document.documentElement.dataset.theme === "dark"
    ? "light"
    : "dark";
  localStorage.setItem(themePreferenceKey, nextTheme);
  applyTheme(nextTheme);
});

applyTheme(document.documentElement.dataset.theme || "light");
