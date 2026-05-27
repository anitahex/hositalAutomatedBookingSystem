const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const statusEl = document.querySelector("#status");
const severityEl = document.querySelector("#severity");
const departmentEl = document.querySelector("#department");
const awaitingEl = document.querySelector("#awaiting");
const quickActions = document.querySelector("#quickActions");
const resetBtn = document.querySelector("#resetBtn");

let state = null;
const patientId = `ui-${crypto.randomUUID()}`;

function addMessage(role, text) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = text;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

function addLoadingMessage() {
  const node = document.createElement("div");
  node.className = "message assistant loading";
  node.setAttribute("role", "status");
  node.setAttribute("aria-label", "Assistant is replying");

  const spinner = document.createElement("span");
  spinner.className = "loading-spinner";
  spinner.setAttribute("aria-hidden", "true");

  const label = document.createElement("span");
  label.textContent = "Assistant is replying";

  node.append(spinner, label);
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

function removeLoadingMessage(node) {
  if (node?.parentNode) {
    node.remove();
  }
}

function updateCasePanel() {
  severityEl.textContent = state?.severity || "-";
  departmentEl.textContent = state?.target_department || "-";
  awaitingEl.textContent = state?.awaiting || "Complete";
}

function setStatus(text) {
  statusEl.textContent = text;
}

function clearQuickActions() {
  quickActions.replaceChildren();
}

function addQuickAction(label, value) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", () => {
    input.value = value;
    form.requestSubmit();
  });
  quickActions.appendChild(button);
}

function renderQuickActions() {
  clearQuickActions();

  if (!state?.awaiting) {
    return;
  }

  if (state.awaiting === "doctor_selection" && Array.isArray(state.doctor_options)) {
    state.doctor_options.forEach((doctor, index) => {
      addQuickAction(`${index + 1}. ${doctor.doctor_name}`, String(index + 1));
    });
    addQuickAction("No appointment", "no");
  }

  if (state.awaiting === "slot_selection" && Array.isArray(state.slot_options)) {
    state.slot_options.forEach((slot, index) => {
      const time = new Date(slot.start_time).toLocaleString();
      addQuickAction(`${index + 1}. ${time}`, String(index + 1));
    });
    addQuickAction("No appointment", "no");
  }
}

async function sendMessage(message) {
  setStatus("Working");
  input.disabled = true;
  const loadingMessage = addLoadingMessage();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        patient_id: patientId,
        state,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Request failed with ${response.status}`);
    }

    const data = await response.json();
    state = data.state;
    removeLoadingMessage(loadingMessage);
    addMessage("assistant", data.response);
    updateCasePanel();
    renderQuickActions();
    setStatus("Ready");
  } catch (error) {
    removeLoadingMessage(loadingMessage);
    addMessage("assistant", `Request failed: ${error.message}`);
    setStatus("Error");
  } finally {
    input.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();

  if (!message) {
    return;
  }

  input.value = "";
  addMessage("user", message);
  clearQuickActions();
  await sendMessage(message);
});

resetBtn.addEventListener("click", () => {
  state = null;
  messages.replaceChildren();
  addMessage("assistant", "Describe your symptoms. I will estimate severity, recommend a department, show available doctors, then help you choose a slot.");
  updateCasePanel();
  clearQuickActions();
  setStatus("Ready");
  input.focus();
});
