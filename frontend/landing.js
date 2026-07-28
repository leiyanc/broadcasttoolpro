const landingMenuToggle = document.querySelector("#landing-menu-toggle");
const landingNav = document.querySelector("#landing-nav");

landingMenuToggle.addEventListener("click", () => {
  const open = landingNav.classList.toggle("is-open");
  landingMenuToggle.setAttribute("aria-expanded", String(open));
  landingMenuToggle.setAttribute(
    "aria-label",
    open ? "Close navigation" : "Open navigation",
  );
});

landingNav.addEventListener("click", (event) => {
  if (!event.target.closest("a")) return;
  landingNav.classList.remove("is-open");
  landingMenuToggle.setAttribute("aria-expanded", "false");
  landingMenuToggle.setAttribute("aria-label", "Open navigation");
});
