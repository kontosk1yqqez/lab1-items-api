// Односторінковий клієнт для Items API (CRUD).
// Адреса API береться з config.js (window.APP_CONFIG.apiBaseUrl).
// За замовчуванням — відносний шлях "/api", тому в Kubernetes запити
// йдуть на той самий host, де Ingress спрямовує /api до backend.
const API = ((window.APP_CONFIG && window.APP_CONFIG.apiBaseUrl) || "/api").replace(/\/$/, "");

const $ = (id) => document.getElementById(id);
const form = $("item-form");
const fmt = new Intl.NumberFormat("uk-UA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

async function request(path, options = {}) {
  const response = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : body.detail || detail;
    } catch (_) { /* тіло не JSON */ }
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.status === 204 ? null : response.json();
}

function setStatus(text, ok = true) {
  const el = $("status");
  el.textContent = text;
  el.className = "status " + (ok ? "ok" : "bad");
}

function render(items) {
  const body = $("items-body");
  body.replaceChildren();
  for (const item of items) {
    const tr = document.createElement("tr");
    const cells = [item.id, item.name, item.description || "—", fmt.format(item.price)];
    cells.forEach((value, i) => {
      const td = document.createElement("td");
      td.textContent = value;
      if (i === 3) td.className = "num";
      tr.append(td);
    });
    const actions = document.createElement("td");
    actions.className = "row-actions";
    const edit = document.createElement("button");
    edit.textContent = "Редагувати";
    edit.className = "secondary";
    edit.onclick = () => startEdit(item);
    const del = document.createElement("button");
    del.textContent = "Видалити";
    del.className = "danger";
    del.onclick = () => removeItem(item);
    actions.append(edit, del);
    tr.append(actions);
    body.append(tr);
  }
  $("empty").hidden = items.length > 0;
}

async function load() {
  try {
    const items = await request("/items");
    render(items);
    setStatus(`з'єднано · ${items.length} шт.`);
  } catch (err) {
    setStatus("API недоступний", false);
    console.error(err);
  }
}

function resetForm() {
  form.reset();
  $("item-id").value = "";
  $("form-title").textContent = "Новий товар";
  $("submit-btn").textContent = "Додати";
  $("cancel-btn").hidden = true;
  $("form-error").hidden = true;
}

function startEdit(item) {
  $("item-id").value = item.id;
  $("name").value = item.name;
  $("description").value = item.description || "";
  $("price").value = item.price;
  $("form-title").textContent = `Редагування товару #${item.id}`;
  $("submit-btn").textContent = "Зберегти";
  $("cancel-btn").hidden = false;
  $("name").focus();
}

async function removeItem(item) {
  if (!confirm(`Видалити «${item.name}»?`)) return;
  try {
    await request(`/items/${item.id}`, { method: "DELETE" });
    if ($("item-id").value === String(item.id)) resetForm();
    await load();
  } catch (err) {
    alert(err.message);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = $("item-id").value;
  const payload = {
    name: $("name").value.trim(),
    description: $("description").value.trim() || null,
    price: Number($("price").value),
  };
  try {
    await request(id ? `/items/${id}` : "/items", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    resetForm();
    await load();
  } catch (err) {
    $("form-error").textContent = err.message;
    $("form-error").hidden = false;
  }
});

$("cancel-btn").onclick = resetForm;
$("refresh-btn").onclick = load;
$("api-base").textContent = API;
load();
