const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const statusEl = document.querySelector("#status");
const patientSummary = document.querySelector("#patientSummary");
const severityEl = document.querySelector("#severity");
const departmentEl = document.querySelector("#department");
const awaitingEl = document.querySelector("#awaiting");
const quickActions = document.querySelector("#quickActions");
const resetBtn = document.querySelector("#resetBtn");
const logoutBtn = document.querySelector("#logoutBtn");
const chatClosedModal = document.querySelector("#chatClosedModal");
const startNewChatBtn = document.querySelector("#startNewChatBtn");

const showLoginBtn = document.querySelector("#showLoginBtn");
const showSignupBtn = document.querySelector("#showSignupBtn");
const loginForm = document.querySelector("#loginForm");
const signupForm = document.querySelector("#signupForm");
const signupStepOne = document.querySelector("#signupStepOne");
const signupStepTwo = document.querySelector("#signupStepTwo");
const signupNextBtn = document.querySelector("#signupNextBtn");
const signupBackBtn = document.querySelector("#signupBackBtn");
const authMessage = document.querySelector("#authMessage");

let state = null;
let currentUser = JSON.parse(localStorage.getItem("currentUser") || "null");
let accessToken = localStorage.getItem("accessToken");
let patientId = currentUser?.patient_id || null;

const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

function setAuthMessage(text) {
  authMessage.textContent = text || "";
}

function showAuthMode(mode) {
  const isLogin = mode === "login";
  loginForm.classList.toggle("hidden", !isLogin);
  signupForm.classList.toggle("hidden", isLogin);
  showLoginBtn.classList.toggle("active", isLogin);
  showSignupBtn.classList.toggle("active", !isLogin);
  setAuthMessage("");
}

function setAuthenticated(user, token) {
  currentUser = user;
  accessToken = token;
  patientId = user.patient_id;
  localStorage.setItem("currentUser", JSON.stringify(user));
  localStorage.setItem("accessToken", token);
  document.body.classList.add("authenticated");
  patientSummary.textContent = `${user.name} - Blood group ${user.blood_group}${
    user.health_issues ? ` - Health issues: ${user.health_issues}` : ""
  }`;
  resetChat();
}

function clearAuthenticated() {
  hideChatClosed();
  currentUser = null;
  accessToken = null;
  patientId = null;
  state = null;
  localStorage.removeItem("currentUser");
  localStorage.removeItem("accessToken");
  document.body.classList.remove("authenticated");
  patientSummary.textContent = "AI triage, doctor selection, and appointment booking";
  messages.replaceChildren();
  addMessage("assistant", "Please login or sign up to continue.");
}

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
  if (state?.chat_closed) {
    awaitingEl.textContent = "Closed";
    return;
  }
  awaitingEl.textContent = state?.awaiting || "Describe symptoms";
}

function setStatus(text) {
  statusEl.textContent = text;
}

function setComposerDisabled(disabled) {
  input.disabled = disabled;
  form.querySelector("button[type='submit']").disabled = disabled;
}

function showChatClosed() {
  clearQuickActions();
  setComposerDisabled(true);
  setStatus("Closed");
  chatClosedModal.classList.remove("hidden");
  startNewChatBtn.focus();
}

function hideChatClosed() {
  chatClosedModal.classList.add("hidden");
  setComposerDisabled(false);
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

  if (state.awaiting === "cancellation_selection" && Array.isArray(state.cancellation_options)) {
    state.cancellation_options.forEach((booking, index) => {
      addQuickAction(`${index + 1}. ${booking.doctor}`, String(index + 1));
    });
  }
}

async function sendMessage(message) {
  if (!patientId || !accessToken) {
    setStatus("Login required");
    return;
  }

  setStatus("Working");
  setComposerDisabled(true);
  const loadingMessage = addLoadingMessage();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        message,
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
    if (state?.chat_closed) {
      showChatClosed();
    } else {
      renderQuickActions();
      setStatus("Ready");
    }
  } catch (error) {
    removeLoadingMessage(loadingMessage);
    if (String(error.message).includes("401")) {
      clearAuthenticated();
      showAuthMode("login");
    }
    addMessage("assistant", `Request failed: ${error.message}`);
    setStatus("Error");
  } finally {
    if (!state?.chat_closed) {
      setComposerDisabled(false);
      input.focus();
    }
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed with ${response.status}`);
  }
  return data;
}

function validateSignupStepOne() {
  const email = document.querySelector("#signupEmail");
  const password = document.querySelector("#signupPassword");
  const confirmPassword = document.querySelector("#signupConfirmPassword");

  if (!email.reportValidity() || !password.reportValidity() || !confirmPassword.reportValidity()) {
    return false;
  }

  if (!passwordPattern.test(password.value)) {
    setAuthMessage(
      "Password must include uppercase, lowercase, number, special character, and be at least 8 characters."
    );
    password.focus();
    return false;
  }

  if (password.value !== confirmPassword.value) {
    setAuthMessage("Password and confirmed password do not match.");
    confirmPassword.focus();
    return false;
  }

  document.querySelector("#profileEmail").value = email.value;
  setAuthMessage("");
  return true;
}

function resetChat() {
  hideChatClosed();
  state = {
    patient_profile: currentUser,
    conversation_history: [],
    chat_closed: false,
  };
  messages.replaceChildren();
  addMessage(
    "assistant",
    `Hello ${currentUser.name}. Describe your symptoms, book an appointment, or ask to cancel an appointment.`
  );
  updateCasePanel();
  clearQuickActions();
  setStatus("Ready");
  input.focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();

  if (!message) {
    return;
  }

  if (state?.chat_closed) {
    showChatClosed();
    return;
  }

  input.value = "";
  addMessage("user", message);
  clearQuickActions();
  await sendMessage(message);
});

resetBtn.addEventListener("click", () => {
  resetChat();
});

startNewChatBtn.addEventListener("click", () => {
  resetChat();
});

showLoginBtn.addEventListener("click", () => showAuthMode("login"));
showSignupBtn.addEventListener("click", () => showAuthMode("signup"));

signupNextBtn.addEventListener("click", () => {
  if (!validateSignupStepOne()) {
    return;
  }

  signupStepOne.classList.add("hidden");
  signupStepTwo.classList.remove("hidden");
  document.querySelector("#profileName").focus();
});

signupBackBtn.addEventListener("click", () => {
  signupStepTwo.classList.add("hidden");
  signupStepOne.classList.remove("hidden");
  document.querySelector("#signupEmail").focus();
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setAuthMessage("");

  try {
    const data = await postJson("/auth/login", {
      email: document.querySelector("#loginEmail").value.trim(),
      password: document.querySelector("#loginPassword").value,
    });
    setAuthenticated(data.user, data.access_token);
  } catch (error) {
    setAuthMessage(error.message);
  }
});

signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateSignupStepOne()) {
    signupStepTwo.classList.add("hidden");
    signupStepOne.classList.remove("hidden");
    return;
  }

  try {
    const data = await postJson("/auth/signup", {
      email: document.querySelector("#signupEmail").value.trim(),
      password: document.querySelector("#signupPassword").value,
      confirm_password: document.querySelector("#signupConfirmPassword").value,
      name: document.querySelector("#profileName").value.trim(),
      age: Number(document.querySelector("#profileAge").value),
      mobile_number: document.querySelector("#profileMobile").value.trim(),
      address: document.querySelector("#profileAddress").value.trim(),
      profile_email: document.querySelector("#profileEmail").value.trim(),
      blood_group: document.querySelector("#profileBloodGroup").value,
      health_issues: document.querySelector("#profileHealthIssues").value.trim() || null,
    });
    setAuthenticated(data.user, data.access_token);
  } catch (error) {
    setAuthMessage(error.message);
  }
});

logoutBtn.addEventListener("click", () => {
  clearAuthenticated();
  showAuthMode("login");
});

if (currentUser && accessToken) {
  setAuthenticated(currentUser, accessToken);
} else {
  clearAuthenticated();
}
