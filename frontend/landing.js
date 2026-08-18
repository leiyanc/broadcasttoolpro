const landingMenuToggle = document.querySelector("#landing-menu-toggle");
const landingNav = document.querySelector("#landing-nav");
const landingContactForm = document.querySelector("#landing-contact-form");
const landingContactStatus = document.querySelector("#landing-contact-status");

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

landingContactForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = landingContactForm.querySelector("button[type='submit']");
  const payload = Object.fromEntries(new FormData(landingContactForm));
  payload.include_stream_monitoring = false;
  button.disabled = true;
  landingContactStatus.classList.remove("is-error");
  landingContactStatus.textContent = window.BTPi18n?.t(
    "landing.contact.sending",
    "Sending…",
  ) || "Sending…";
  try {
    const response = await fetch("/api/auth/access-requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.detail || "The request could not be sent.");
    }
    landingContactForm.reset();
    landingContactStatus.textContent = window.BTPi18n?.t(
      "landing.contact.sent",
      "Thank you. Our team will contact you shortly.",
    ) || "Thank you. Our team will contact you shortly.";
  } catch (error) {
    landingContactStatus.textContent = error.message;
    landingContactStatus.classList.add("is-error");
  } finally {
    button.disabled = false;
  }
});
