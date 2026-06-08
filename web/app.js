const fontToggle = document.querySelector("#fontToggle");
const contrastToggle = document.querySelector("#contrastToggle");

function setPressed(button, pressed) {
  button.setAttribute("aria-pressed", String(pressed));
}

fontToggle?.addEventListener("click", () => {
  const active = document.body.classList.toggle("large-text");
  setPressed(fontToggle, active);
});

contrastToggle?.addEventListener("click", () => {
  const active = document.body.classList.toggle("high-contrast");
  setPressed(contrastToggle, active);
});
