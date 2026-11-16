// Owner lead board: leads ranked by the advisory conversion score.
// DOM is built with h() (textContent only), so lead data can never inject markup.
import { api } from "/js/api.js";
import { clear, h } from "/js/lib/dom.js";

const STATUS = {
  new: "חדש",
  contacted: "נוצר קשר",
  quote_sent: "נשלחה הצעה",
  won: "נסגר",
  lost: "אבד",
};
const EVENT = {
  wedding: "חתונה",
  corporate: "אירוע עסקי",
  birthday: "יום הולדת",
  bar_mitzvah: "בר/בת מצווה",
  private: "אירוע פרטי",
  other: "אחר",
};
const SOURCE = {
  referral: "המלצה",
  website: "אתר",
  social: "רשתות חברתיות",
  phone: "טלפון",
  ads: "פרסום",
  returning: "לקוח חוזר",
};

const KEY_STORAGE = "yummai-admin-key";
const state = { key: "", status: "", sort: "score" };

const form = document.getElementById("key-form");
const keyInput = document.getElementById("admin-key");
const board = document.getElementById("board");
const message = document.getElementById("message");
const statusFilter = document.getElementById("status-filter");
const sortSelect = document.getElementById("sort");

function storage(action, value) {
  try {
    if (action === "get") return sessionStorage.getItem(KEY_STORAGE) ?? "";
    if (action === "set") sessionStorage.setItem(KEY_STORAGE, value);
    if (action === "clear") sessionStorage.removeItem(KEY_STORAGE);
  } catch {
    // Storage can be blocked; the key then only lives for this page view.
  }
  return "";
}

function say(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("is-error", isError);
}

function request(path, options = {}) {
  return api(path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Admin-Key": state.key },
  });
}

export function scoreBand(score) {
  if (score == null) return { label: "לא נוקד", level: "none" };
  if (score >= 0.6) return { label: "סיכוי גבוה", level: "high" };
  if (score >= 0.35) return { label: "סיכוי בינוני", level: "mid" };
  return { label: "סיכוי נמוך", level: "low" };
}

function scoreCell(lead) {
  const band = scoreBand(lead.conversion_score);
  if (lead.conversion_score == null) return h("span", { class: "score score-none" }, band.label);
  const pct = Math.round(lead.conversion_score * 100);
  return h(
    "span",
    { class: `score score-${band.level}` },
    h("span", { class: "score-bar", "aria-hidden": "true" }, h("span", { style: `inline-size:${pct}%` })),
    h("span", { class: "score-text" }, `${pct}%`, " ", h("span", { class: "score-label" }, band.label)),
  );
}

function statusSelect(lead) {
  const select = h(
    "select",
    { "aria-label": `סטטוס עבור ${lead.name}`, onchange: () => changeStatus(lead, select) },
    Object.entries(STATUS).map(([value, label]) => h("option", { value, selected: value === lead.status }, label)),
  );
  return select;
}

async function changeStatus(lead, select) {
  select.disabled = true;
  try {
    await request(`/api/admin/leads/${lead.id}`, { method: "PATCH", body: JSON.stringify({ status: select.value }) });
    say(`הסטטוס של ${lead.name} עודכן ל"${STATUS[select.value]}".`);
  } catch (error) {
    select.value = lead.status;
    say(`העדכון נכשל: ${error.message}`, true);
  } finally {
    select.disabled = false;
  }
}

function renderTable(leads) {
  clear(board);
  if (!leads.length) {
    board.append(h("p", { class: "empty" }, "אין לידים להצגה."));
    return;
  }
  const head = ["שם", "טלפון", "סוג אירוע", "מקור", "תאריך אירוע", "אורחים", "סיכוי להזמנה", "סטטוס"];
  board.append(
    h(
      "table",
      { class: "leads" },
      h("caption", { class: "visually-hidden" }, "רשימת לידים לפי סיכוי להזמנה"),
      h("thead", {}, h("tr", {}, head.map((t) => h("th", { scope: "col" }, t)))),
      h(
        "tbody",
        {},
        leads.map((lead) =>
          h(
            "tr",
            {},
            h("th", { scope: "row" }, lead.name),
            h("td", {}, h("bdi", { dir: "ltr" }, lead.phone)),
            h("td", {}, EVENT[lead.event_type] ?? lead.event_type),
            h("td", {}, SOURCE[lead.source] ?? lead.source),
            h("td", {}, lead.event_date ?? "—"),
            h("td", {}, lead.guest_count ?? "—"),
            h("td", {}, scoreCell(lead)),
            h("td", {}, statusSelect(lead)),
          ),
        ),
      ),
    ),
  );
}

async function load() {
  const params = new URLSearchParams({ sort: state.sort });
  if (state.status) params.set("lead_status", state.status);
  say("טוען לידים…");
  try {
    const leads = await request(`/api/admin/leads?${params}`);
    renderTable(leads);
    say(`${leads.length} לידים.`);
  } catch (error) {
    clear(board);
    if (error.status === 401) {
      storage("clear");
      say("מפתח הגישה שגוי או חסר.", true);
    } else {
      say(`הטעינה נכשלה: ${error.message}`, true);
    }
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  state.key = keyInput.value.trim();
  if (!state.key) return say("יש להזין מפתח גישה.", true);
  storage("set", state.key);
  keyInput.value = "";
  load();
});
statusFilter.addEventListener("change", () => {
  state.status = statusFilter.value;
  if (state.key) load();
});
sortSelect.addEventListener("change", () => {
  state.sort = sortSelect.value;
  if (state.key) load();
});

state.key = storage("get");
if (state.key) load();
else say("הזינו מפתח גישה כדי לראות את הלידים.");
