// Public lead form. Validation mirrors backend/app/schemas/lead.py (the server stays authoritative).
import { api } from "/js/api.js";

const form = document.getElementById("lead-form");
const submit = document.getElementById("submit");
const formError = document.getElementById("form-error");
const thanks = document.getElementById("thanks");

const PHONE = /^\+?[0-9\-\s]{7,20}$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validate(values) {
  const errors = {};
  if (!values.name) errors.name = "יש להזין שם.";
  else if (values.name.length > 120) errors.name = "השם ארוך מדי.";
  if (!values.phone) errors.phone = "יש להזין מספר טלפון.";
  else if (!PHONE.test(values.phone)) errors.phone = "מספר הטלפון אינו תקין. אפשר להשתמש בספרות, רווחים ומקף.";
  if (values.email && !EMAIL.test(values.email)) errors.email = "כתובת האימייל אינה תקינה.";
  if (!values.event_type) errors.event_type = "יש לבחור סוג אירוע.";
  if (values.guest_count !== "" && !(Number.isInteger(+values.guest_count) && +values.guest_count >= 1 && +values.guest_count <= 5000)) {
    errors.guest_count = "מספר האורחים צריך להיות בין 1 ל־5000.";
  }
  return errors;
}

export function buildPayload(values) {
  const payload = { name: values.name, phone: values.phone, event_type: values.event_type, source: "website" };
  if (values.email) payload.email = values.email;
  if (values.event_date) payload.event_date = values.event_date;
  if (values.guest_count !== "") payload.guest_count = Number(values.guest_count);
  return payload;
}

function readValues() {
  const data = new FormData(form);
  const get = (key) => String(data.get(key) ?? "").trim();
  return {
    name: get("name"),
    phone: get("phone"),
    email: get("email"),
    event_type: get("event_type"),
    event_date: get("event_date"),
    guest_count: get("guest_count"),
    company: get("company"),
  };
}

function showErrors(errors) {
  for (const field of form.querySelectorAll("[data-field]")) {
    const key = field.dataset.field;
    const input = field.querySelector("input, select");
    const note = document.getElementById(`${key}-error`);
    const message = errors[key];
    field.classList.toggle("invalid", Boolean(message));
    note.hidden = !message;
    note.textContent = message ?? "";
    if (message) {
      input.setAttribute("aria-invalid", "true");
      input.setAttribute("aria-describedby", note.id);
    } else {
      input.removeAttribute("aria-invalid");
      input.removeAttribute("aria-describedby");
    }
  }
  const first = Object.keys(errors)[0];
  if (first) document.getElementById(first).focus();
}

function showThanks() {
  form.hidden = true;
  thanks.hidden = false;
  document.getElementById("thanks-title").focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.hidden = true;
  const values = readValues();
  const errors = validate(values);
  showErrors(errors);
  if (Object.keys(errors).length) return;
  if (values.company) return showThanks(); // honeypot filled: pretend success, send nothing

  submit.disabled = true;
  try {
    await api("/api/leads", { method: "POST", body: JSON.stringify(buildPayload(values)) });
    showThanks();
  } catch {
    formError.textContent = "לא הצלחנו לשלוח את הפרטים. נסו שוב בעוד רגע.";
    formError.hidden = false;
    submit.disabled = false;
  }
});
