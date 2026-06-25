const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const statusEl = document.querySelector("#status");
const patientSummary = document.querySelector("#patientSummary");
const patientName = document.querySelector("#patientName");
const patientAge = document.querySelector("#patientAge");
const patientBlood = document.querySelector("#patientBlood");
const patientIssues = document.querySelector("#patientIssues");
const severityEl = document.querySelector("#severity");
const departmentEl = document.querySelector("#department");
const awaitingEl = document.querySelector("#awaiting");
const workflowStateEl = document.querySelector("#workflowState");
const workflowRail = document.querySelector("#workflowRail");
const sidebarToggleBtn = document.querySelector("#sidebarToggleBtn");
const appSidebar = document.querySelector("#appSidebar");
const sidebarHandleBtn = document.querySelector("#sidebarHandleBtn");
const sidebarHandleLabel = document.querySelector("#sidebarHandleLabel");
const scrollTopBtn = document.querySelector("#scrollTopBtn");
const routingMeta = document.querySelector("#routingMeta");
const topbarCopy = document.querySelector("#topbarCopy");
const activeAppointmentsPreview = document.querySelector("#activeAppointmentsPreview");
const documentUpload = document.querySelector("#documentUpload");
const uploadStatus = document.querySelector("#uploadStatus");
const attachPills = document.querySelector("#attachPills");
const analyzedDocsList = document.querySelector("#analyzedDocsList");
const tokenInput = document.querySelector("#tokenInput");
const tokenOutput = document.querySelector("#tokenOutput");
const tokenTotal = document.querySelector("#tokenTotal");
const tokenCalls = document.querySelector("#tokenCalls");
const quickActions = document.querySelector("#quickActions");
const editProfileBtn = document.querySelector("#editProfileBtn");
const resetBtn = document.querySelector("#resetBtn");
const logoutBtn = document.querySelector("#logoutBtn");
const bookAppointmentBtn = document.querySelector("#bookAppointmentBtn");
const modifyAppointmentBtn = document.querySelector("#modifyAppointmentBtn");
const previousBookingsBtn = document.querySelector("#previousBookingsBtn");
const upcomingBookingsBtn = document.querySelector("#upcomingBookingsBtn");
const chatHistoryBtn = document.querySelector("#chatHistoryBtn");
const profilePanel = document.querySelector("#profilePanel");
const profilePanelTitle = document.querySelector("#profilePanelTitle");
const profilePanelBody = document.querySelector("#profilePanelBody");
const closeProfilePanelBtn = document.querySelector("#closeProfilePanelBtn");
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
let sidebarOpen = localStorage.getItem("sidebarOpen");
sidebarOpen = sidebarOpen === null ? true : sidebarOpen === "true";
let bookingStudioState = {
  departments: [],
  department: null,
  doctors: [],
  doctor: null,
  date: null,
  slots: [],
  slotId: null,
  mode: "book",
};
let pendingUploadFiles = [];

const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

function newChatSessionId() {
  if (crypto?.randomUUID) {
    return crypto.randomUUID();
  }
  return "session-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
}

function currentSessionId() {
  return state?.session_id || state?.chat_session_id || newChatSessionId();
}

function setUploadStatus(text, tone = "default") {
  if (!uploadStatus) return;
  uploadStatus.textContent = text || "";
  uploadStatus.dataset.tone = tone;
}

function showAttachPill(file) {
  if (!attachPills) return;

  const pill = document.createElement("div");
  pill.className = "attach-pill";

  const icon = document.createElement("span");
  icon.textContent = file.name.toLowerCase().endsWith(".pdf") ? "📄" : "🖼";

  const name = document.createElement("span");
  name.className = "attach-pill-name";
  name.textContent = file.name;
  name.title = file.name;

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "attach-pill-remove";
  remove.textContent = "×";
  remove.title = "Remove file";
  remove.addEventListener("click", () => {
    const idx = pendingUploadFiles.indexOf(file);
    if (idx > -1) pendingUploadFiles.splice(idx, 1);
    pill.remove();
    if (documentUpload && pendingUploadFiles.length === 0) documentUpload.value = "";
    setUploadStatus("", "default");
  });

  pill.append(icon, name, remove);
  attachPills.appendChild(pill);
}

function clearAttachPill() {
  if (attachPills) attachPills.replaceChildren();
  pendingUploadFiles = [];
}

function renderAnalyzedDocs(docs) {
  if (!analyzedDocsList) return;
  analyzedDocsList.replaceChildren();

  if (!Array.isArray(docs) || !docs.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No documents analyzed yet. Use 📎 in the chat to attach a file.";
    analyzedDocsList.appendChild(note);
    return;
  }

  [...docs].reverse().forEach((doc) => {
    const item = document.createElement("article");
    item.className = "analyzed-doc-item";

    const name = document.createElement("div");
    name.className = "analyzed-doc-name";
    name.title = doc.file_name || "Unknown file";
    name.textContent = doc.file_name || "Unknown file";

    const type = document.createElement("div");
    type.className = "analyzed-doc-type";
    type.textContent = (doc.document_type || "document").replaceAll("_", " ");

    const dept = document.createElement("div");
    dept.className = "analyzed-doc-dept";
    dept.textContent = `→ ${doc.department || "?"}`;

    item.append(name, type, dept);
    analyzedDocsList.appendChild(item);
  });
}

function addUserMessageWithFile(text, filenames) {
  const { node, body } = createMessageNode("user", "", {});
  const names = Array.isArray(filenames) ? filenames : [filenames];
  for (const filename of names) {
    const chip = document.createElement("div");
    chip.className = "msg-file-chip";
    const ext = (filename || "").toLowerCase();
    chip.textContent = (ext.endsWith(".pdf") ? "📄 " : "🖼 ") + filename;
    body.appendChild(chip);
  }
  if (text) {
    const textNode = document.createTextNode(text);
    body.appendChild(textNode);
  }
}

function scrollMessages(smooth = true) {
  messages.scrollTo({
    top: messages.scrollHeight,
    behavior: smooth ? "smooth" : "auto",
  });
}

function scrollMessagesToTop(smooth = true) {
  messages.scrollTo({
    top: 0,
    behavior: smooth ? "smooth" : "auto",
  });
}

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

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return new Intl.NumberFormat().format(Number(value));
}

function safeText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function mergeBookingLists(existing = [], incoming = []) {
  // Use a Map so a booking appearing in both lists is merged, with `incoming`
  // fields overwriting `existing` — this ensures an updated booking_note from
  // the backend replaces the stale version already held in client state.
  const map = new Map();

  [...(existing || [])].forEach((booking) => {
    if (!booking || typeof booking !== "object") return;
    const key = `${booking.booking_id || ""}::${booking.slot_id || ""}`;
    map.set(key, booking);
  });

  [...(incoming || [])].forEach((booking) => {
    if (!booking || typeof booking !== "object") return;
    const key = `${booking.booking_id || ""}::${booking.slot_id || ""}`;
    map.set(key, map.has(key) ? { ...map.get(key), ...booking } : booking);
  });

  return Array.from(map.values());
}

function normalizeChatState(nextState, fallbackState = null) {
  const merged = {
    ...(fallbackState || {}),
    ...(nextState || {}),
  };

  const history = nextState?.messages || nextState?.conversation_history || fallbackState?.messages || fallbackState?.conversation_history || [];
  const upcomingBookings = mergeBookingLists(
    nextState?.upcoming_bookings || nextState?.confirmed_bookings || fallbackState?.upcoming_bookings || fallbackState?.confirmed_bookings || [],
    nextState?.active_appointments || fallbackState?.active_appointments || []
  );
  const activeIntent = nextState?.active_intent || nextState?.intent || fallbackState?.active_intent || fallbackState?.intent || null;
  const collectedData = nextState?.collected_data || nextState?.collected_info || fallbackState?.collected_data || fallbackState?.collected_info || {};
  const sessionId = nextState?.session_id || nextState?.chat_session_id || fallbackState?.session_id || fallbackState?.chat_session_id || null;

  return {
    ...merged,
    messages: Array.isArray(history) ? history.slice(-6) : [],
    recent_history: Array.isArray(nextState?.recent_history)
      ? nextState.recent_history.slice(-6)
      : Array.isArray(history)
        ? history.slice(-6)
        : [],
    upcoming_bookings: upcomingBookings,
    confirmed_bookings: upcomingBookings,
    confirmed_booking: upcomingBookings[upcomingBookings.length - 1] || null,
    active_appointments: upcomingBookings,
    active_intent: activeIntent,
    intent: activeIntent,
    session_id: sessionId,
    chat_session_id: sessionId,
    pending_file_data: nextState?.pending_file_data ?? fallbackState?.pending_file_data ?? null,
    pending_file_name: nextState?.pending_file_name ?? fallbackState?.pending_file_name ?? null,
    pending_file_mime_type: nextState?.pending_file_mime_type ?? fallbackState?.pending_file_mime_type ?? null,
    file_clarification_context: nextState?.file_clarification_context ?? fallbackState?.file_clarification_context ?? null,
    collected_data: collectedData,
    collected_info: collectedData,
    analyzed_documents: Array.isArray(nextState?.analyzed_documents)
      ? nextState.analyzed_documents
      : Array.isArray(fallbackState?.analyzed_documents)
        ? fallbackState.analyzed_documents
        : [],
  };
}

function setPatientSummary(user) {
  if (!user) {
    patientName.textContent = "Guest";
    patientSummary.textContent = "AI triage, doctor selection, and appointment booking.";
    patientAge.textContent = "-";
    patientBlood.textContent = "-";
    patientIssues.textContent = "-";
    return;
  }

  patientName.textContent = safeText(user.name, "Guest");
  patientSummary.textContent = `${safeText(user.name, "Patient")} is ready for triage and booking support.`;
  patientAge.textContent = safeText(user.age);
  patientBlood.textContent = safeText(user.blood_group);
  patientIssues.textContent = safeText(user.health_issues, "None reported");
}

function setAuthenticated(user, token) {
  currentUser = user;
  accessToken = token;
  patientId = user.patient_id;
  localStorage.setItem("currentUser", JSON.stringify(user));
  localStorage.setItem("accessToken", token);
  document.body.classList.add("authenticated");
  setPatientSummary(user);
  resetChat();
  refreshActiveAppointments();
  setSidebarOpen(sidebarOpen);
}

function clearAuthenticated() {
  hideChatClosed();
  hideProfilePanel();
  if (documentUpload) documentUpload.value = "";
  clearAttachPill();
  setUploadStatus("", "default");
  renderAnalyzedDocs([]);
  currentUser = null;
  accessToken = null;
  patientId = null;
  state = null;
  localStorage.removeItem("currentUser");
  localStorage.removeItem("accessToken");
  document.body.classList.remove("authenticated");
  setPatientSummary(null);
  updateWorkflowPanel(null);
  renderChatSummary("");
  renderRecentHistory([]);
  renderTokenUsage(null);
  renderActiveAppointments([]);
  clearQuickActions();
  messages.replaceChildren();
  addAssistantMessage(
    "Please login or sign up to continue.",
    { intro: true, noAnimation: true }
  );
}

async function refreshActiveAppointments() {
  if (!patientId || !accessToken) {
    renderActiveAppointments([]);
    return [];
  }

  try {
    const data = await authedJson("/appointments/upcoming");
    const bookings = data.bookings || [];

    if (state) {
      state = normalizeChatState({
        active_appointments: bookings,
        upcoming_bookings: mergeBookingLists(state.upcoming_bookings, bookings),
      }, state);
    }

    const activeBookings = state?.upcoming_bookings || bookings;
    renderActiveAppointments(activeBookings);
    return activeBookings;
  } catch (error) {
    renderActiveAppointments([]);
    return [];
  }
}

function createMessageNode(role, text = "", options = {}) {
  const node = document.createElement("article");
  node.className = `message ${role}`;
  if (!options.noAnimation) {
    node.classList.add("enter");
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (role === "assistant") {
    const meta = document.createElement("div");
    meta.className = "message-meta";

    const avatar = document.createElement("span");
    avatar.className = "bubble-avatar";
    avatar.textContent = "+";

    const label = document.createElement("span");
    label.textContent = options.intro ? "Medical assistant" : "Triage assistant";

    meta.append(avatar, label);
    node.appendChild(meta);
  }

  const body = document.createElement("div");
  body.className = "message-text";
  body.textContent = text || "";

  bubble.appendChild(body);
  node.appendChild(bubble);
  messages.appendChild(node);
  scrollMessages();

  return { node, bubble, body };
}

function addUserMessage(text) {
  return createMessageNode("user", text);
}

function addAssistantMessage(text, options = {}) {
  return createMessageNode("assistant", text, options);
}

function addTypingAssistantMessage() {
  const { node, bubble, body } = addAssistantMessage("", { noAnimation: false });
  node.classList.add("streaming");

  const typing = document.createElement("div");
  typing.className = "typing-indicator";
  typing.setAttribute("aria-hidden", "true");
  typing.innerHTML = "<span></span><span></span><span></span>";
  body.replaceChildren(typing);
  return { node, bubble, body, typing, textStarted: false };
}

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function streamAssistantText(messageNode, text) {
  const target = messageNode.body;
  target.textContent = "";
  messageNode.node.classList.add("streaming");

  for (let index = 0; index < text.length; index += 3) {
    target.textContent += text.slice(index, index + 3);
    scrollMessages();
    await wait(14);
  }

  finishStreamingMessage(messageNode);
}

// ── Inline markdown renderer ────────────────────────────────────────────────
function _escHtml(t) {
  return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function _inlineMd(t) {
  t = _escHtml(t);
  t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/\*([^*\n]+?)\*/g, "<em>$1</em>");
  t = t.replace(/`([^`\n]+?)`/g, "<code>$1</code>");
  return t;
}
function renderMarkdown(raw) {
  const lines = raw.split("\n");
  const out = [];
  let inUl = false, inTable = false, tableHead = false, pBuf = [];

  function flushP() { if (pBuf.length) { out.push(`<p>${pBuf.join(" ")}</p>`); pBuf = []; } }
  function closeUl() { if (inUl) { out.push("</ul>"); inUl = false; } }
  function closeTable() { if (inTable) { out.push("</tbody></table>"); inTable = false; tableHead = false; } }

  for (const line of lines) {
    // Tables
    if (inTable || line.match(/^\|.+\|/)) {
      if (line.match(/^\|[\s\-:|]+\|/)) {
        out.push("</thead><tbody>"); tableHead = true; continue;
      }
      if (line.match(/^\|.+\|/)) {
        if (!inTable) { flushP(); closeUl(); out.push('<div class="md-table-wrap"><table class="md-table"><thead>'); inTable = true; tableHead = false; }
        const cells = line.split("|").slice(1, -1);
        const tag = tableHead ? "td" : "th";
        out.push("<tr>" + cells.map(c => `<${tag}>${_inlineMd(c.trim())}</${tag}>`).join("") + "</tr>");
        continue;
      }
    }
    closeTable();

    if (line.startsWith("### ")) {
      flushP(); closeUl(); out.push(`<h3>${_inlineMd(line.slice(4))}</h3>`);
    } else if (line.startsWith("## ")) {
      flushP(); closeUl(); out.push(`<h2>${_inlineMd(line.slice(3))}</h2>`);
    } else if (line.startsWith("# ")) {
      flushP(); closeUl(); out.push(`<h1>${_inlineMd(line.slice(2))}</h1>`);
    } else if (line.match(/^(\s{0,4})[-*•]\s/)) {
      flushP();
      const indent = (line.match(/^(\s*)/)||["",""])[1].length;
      const content = line.replace(/^\s*[-*•]\s/, "");
      if (!inUl) { out.push("<ul>"); inUl = true; }
      out.push(`<li style="margin-left:${Math.min(indent,4)*10}px">${_inlineMd(content)}</li>`);
    } else if (line.match(/^-{3,}\s*$/)) {
      flushP(); closeUl(); out.push("<hr>");
    } else if (!line.trim()) {
      flushP(); closeUl();
    } else {
      closeUl(); pBuf.push(_inlineMd(line));
    }
  }
  flushP(); closeUl();
  if (inTable) out.push("</tbody></table></div>");
  return out.join("");
}
// ────────────────────────────────────────────────────────────────────────────

function appendAssistantToken(messageNode, token) {
  if (!token) return;
  if (!messageNode.textStarted) {
    messageNode.body.replaceChildren();
    messageNode.textStarted = true;
    messageNode._mdBuf = "";
  }
  messageNode._mdBuf = (messageNode._mdBuf || "") + token;
  if (!messageNode._rafId) {
    messageNode._rafId = requestAnimationFrame(() => {
      messageNode.body.innerHTML = renderMarkdown(messageNode._mdBuf || "");
      scrollMessages();
      messageNode._rafId = null;
    });
  }
}

function finishStreamingMessage(messageNode) {
  if (messageNode._rafId) { cancelAnimationFrame(messageNode._rafId); messageNode._rafId = null; }
  if (messageNode._mdBuf !== undefined) {
    messageNode.body.innerHTML = renderMarkdown(messageNode._mdBuf || "");
  }
  messageNode.node.classList.remove("streaming");
  scrollMessages(false);
}

async function readChatStream(response, assistantMessage) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalPayload = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }

      const event = JSON.parse(line);
      if (event.type === "status_token") {
        continue;
      }
      if (event.type === "start_response") {
        assistantMessage.body.replaceChildren();
        assistantMessage.textStarted = true;
      }
      if (event.type === "token") {
        appendAssistantToken(assistantMessage, event.token || "");
      }
      if (event.type === "final") {
        finalPayload = event;
      }
      if (event.type === "error") {
        throw new Error(event.message || "Streaming request failed");
      }
    }
  }

  if (buffer.trim()) {
    const event = JSON.parse(buffer);
    if (event.type === "status_token") {
      // Don't return early - still need to finish the message
      finishStreamingMessage(assistantMessage);
      return finalPayload;
    }
    if (event.type === "start_response") {
      assistantMessage.body.replaceChildren();
      assistantMessage.textStarted = true;
    } else if (event.type === "token") {
      appendAssistantToken(assistantMessage, event.token || "");
    } else if (event.type === "final") {
      finalPayload = event;
    } else if (event.type === "error") {
      throw new Error(event.message || "Streaming request failed");
    }
  }

  finishStreamingMessage(assistantMessage);
  return finalPayload;
}

function authHeaders() {
  return {
    Authorization: `Bearer ${accessToken}`,
  };
}

async function authedJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthenticated();
      showAuthMode("login");
    }
    throw new Error(data.detail || `Request failed with ${response.status}`);
  }
  return data;
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

function showProfilePanel(title) {
  profilePanelTitle.textContent = title;
  profilePanel.classList.remove("hidden");
  profilePanel.scrollIntoView({ behavior: "smooth", block: "start" });
  profilePanelBody.scrollTo({ top: 0, behavior: "auto" });
}

function hideProfilePanel() {
  profilePanel.classList.add("hidden");
  profilePanelBody.replaceChildren();
}

function scrollProfilePanelToTop() {
  profilePanelBody.scrollTo({ top: 0, behavior: "auto" });
}

function setProfilePanelLoading(title) {
  showProfilePanel(title);
  profilePanelBody.replaceChildren();
  const loading = document.createElement("p");
  loading.className = "panel-note";
  loading.textContent = "Loading...";
  profilePanelBody.appendChild(loading);
  scrollProfilePanelToTop();
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

function formatBookingDateTime(value) {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString();
}

function localDateString(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDateLabel(value) {
  if (!value) {
    return "Unknown date";
  }
  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function setSidebarOpen(isOpen) {
  sidebarOpen = Boolean(isOpen);
  document.body.classList.toggle("sidebar-collapsed", !sidebarOpen);
  if (sidebarToggleBtn) {
    sidebarToggleBtn.textContent = sidebarOpen ? "Hide menu" : "Show menu";
    sidebarToggleBtn.setAttribute("aria-expanded", String(sidebarOpen));
  }
  if (sidebarHandleBtn) {
    sidebarHandleBtn.setAttribute("aria-expanded", String(sidebarOpen));
    sidebarHandleBtn.classList.toggle("is-open", sidebarOpen);
  }
  if (sidebarHandleLabel) {
    sidebarHandleLabel.textContent = sidebarOpen
      ? "Menu"
      : (currentUser?.name ? `${currentUser.name}` : "Menu");
  }
  localStorage.setItem("sidebarOpen", String(sidebarOpen));
}

function setChatTopButtonVisible(visible) {
  if (!scrollTopBtn) {
    return;
  }
  scrollTopBtn.classList.toggle("hidden", !visible);
}

function renderEmptyPanel(message) {
  profilePanelBody.replaceChildren();
  const note = document.createElement("p");
  note.className = "panel-note";
  note.textContent = message;
  profilePanelBody.appendChild(note);
  scrollProfilePanelToTop();
}

function appointmentDateOptions(days = 7) {
  const options = [];
  const today = new Date();

  for (let index = 0; index < days; index += 1) {
    const date = new Date(today);
    date.setDate(today.getDate() + index);
    options.push({
      label:
        index === 0
          ? "Today"
          : index === 1
            ? "Tomorrow"
            : date.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }),
      value: localDateString(date),
    });
  }

  return options;
}

function buildBookingPanelSummary() {
  const summary = document.createElement("section");
  summary.className = "glass-panel booking-summary-card";

  const label = document.createElement("p");
  label.className = "card-kicker";
  label.textContent = "DIRECT BOOKING";

  const title = document.createElement("h3");
  title.textContent = "Departments > doctors > appointment";

  const text = document.createElement("p");
  text.className = "panel-note";
  text.textContent =
    "Choose a department first, then pick a doctor and a slot. No chat is needed for this path.";

  summary.append(label, title, text);
  return summary;
}

function renderBookingStudio() {
  profilePanelBody.replaceChildren();
  scrollProfilePanelToTop();

  const shell = document.createElement("div");
  shell.className = "booking-studio";

  const left = document.createElement("section");
  left.className = "booking-column";

  const right = document.createElement("section");
  right.className = "booking-column booking-column-strong";

  const departmentCard = document.createElement("article");
  departmentCard.className = "glass-panel booking-step-card";
  const departmentTitle = document.createElement("h3");
  departmentTitle.textContent = "1. Department";
  const departmentNote = document.createElement("p");
  departmentNote.className = "panel-note";
  departmentNote.textContent = "Pick the department that best matches the concern.";
  const departmentSelect = document.createElement("select");
  departmentSelect.innerHTML = '<option value="">Loading departments...</option>';
  departmentCard.append(departmentTitle, departmentNote, departmentSelect);

  const doctorCard = document.createElement("article");
  doctorCard.className = "glass-panel booking-step-card";
  const doctorTitle = document.createElement("h3");
  doctorTitle.textContent = "2. Doctor";
  const doctorNote = document.createElement("p");
  doctorNote.className = "panel-note";
  doctorNote.textContent = "Available doctors will appear after a department is chosen.";
  const doctorList = document.createElement("div");
  doctorList.className = "booking-list";
  doctorCard.append(doctorTitle, doctorNote, doctorList);

  const slotCard = document.createElement("article");
  slotCard.className = "glass-panel booking-step-card";
  const slotTitle = document.createElement("h3");
  slotTitle.textContent = "3. Appointment";
  const slotNote = document.createElement("p");
  slotNote.className = "panel-note";
  slotNote.textContent = "Choose a date within the next 7 days and book the slot.";
  const dateRow = document.createElement("div");
  dateRow.className = "date-chip-row";
  const slotList = document.createElement("div");
  slotList.className = "booking-list";
  slotCard.append(slotTitle, slotNote, dateRow, slotList);

  const actionCard = document.createElement("article");
  actionCard.className = "glass-panel booking-step-card booking-action-card";
  const actionTitle = document.createElement("h3");
  actionTitle.textContent = "Booking summary";
  const actionText = document.createElement("p");
  actionText.className = "panel-note";
  actionText.textContent = "Select a slot to enable booking.";
  const actionMeta = document.createElement("div");
  actionMeta.className = "booking-meta";
  const actionButton = document.createElement("button");
  actionButton.type = "button";
  actionButton.textContent = "Book selected slot";
  actionButton.disabled = true;
  actionCard.append(actionTitle, actionText, actionMeta, actionButton);

  const state = {
    departmentSelect,
    doctorList,
    slotList,
    dateRow,
    actionText,
    actionMeta,
    actionButton,
  };

  const setSummary = () => {
    const department = bookingStudioState.department || "No department selected";
    const doctor = bookingStudioState.doctor?.doctor_name || "No doctor selected";
    const slot = bookingStudioState.slotId
      ? formatDateTime(bookingStudioState.slots.find((item) => item.slot_id === bookingStudioState.slotId)?.start_time)
      : "No slot selected";
    actionMeta.replaceChildren();
    const dept = document.createElement("div");
    dept.innerHTML = `<span>Department</span><strong>${department}</strong>`;
    const doc = document.createElement("div");
    doc.innerHTML = `<span>Doctor</span><strong>${doctor}</strong>`;
    const slotNode = document.createElement("div");
    slotNode.innerHTML = `<span>Slot</span><strong>${slot}</strong>`;
    actionMeta.append(dept, doc, slotNode);
    actionButton.disabled = !bookingStudioState.slotId;
    actionText.textContent = bookingStudioState.slotId
      ? "You can book immediately from here."
      : "Select a slot to enable booking.";
  };

  const renderDates = () => {
    dateRow.replaceChildren();
    appointmentDateOptions().forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "chip-button";
      button.textContent = option.label;
      button.dataset.value = option.value;
      button.classList.toggle("active", bookingStudioState.date === option.value);
      button.addEventListener("click", () => {
        bookingStudioState.date = option.value;
        renderDates();
        loadDoctors();
      });
      dateRow.appendChild(button);
    });
  };

  const renderDoctors = () => {
    doctorList.replaceChildren();
    if (!bookingStudioState.departments.length) {
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = "No departments are currently available.";
      doctorList.appendChild(note);
      return;
    }

    if (!bookingStudioState.doctors.length) {
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = "Select a department to see available doctors.";
      doctorList.appendChild(note);
      return;
    }

    bookingStudioState.doctors.forEach((doctor) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "booking-card-button";
      button.classList.toggle("active", bookingStudioState.doctor?.doctor_id === doctor.doctor_id);
      const title = document.createElement("strong");
      title.className = "booking-card-title";
      title.textContent = doctor.doctor_name;

      const department = document.createElement("span");
      department.className = "booking-card-meta";
      department.textContent = doctor.department || bookingStudioState.department;

      const experience = document.createElement("span");
      experience.className = "booking-card-meta";
      experience.textContent = formatDoctorExperience(doctor);

      const availability = document.createElement("span");
      availability.className = "booking-card-meta";
      availability.textContent = `${doctor.available_slot_count || 0} open slots`;

      const nextSlot = document.createElement("span");
      nextSlot.className = "booking-card-meta";
      nextSlot.textContent = doctor.next_available_time
        ? `Next: ${formatDateTime(doctor.next_available_time)}`
        : "Next slot not listed";

      button.append(title, department, experience, availability, nextSlot);
      button.addEventListener("click", () => {
        bookingStudioState.doctor = doctor;
        bookingStudioState.slotId = null;
        loadSlots();
        renderDoctors();
        setSummary();
      });
      doctorList.appendChild(button);
    });
  };

  const renderSlots = () => {
    slotList.replaceChildren();
    if (!bookingStudioState.doctor) {
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = "Pick a doctor to view slots.";
      slotList.appendChild(note);
      return;
    }

    if (!bookingStudioState.slots.length) {
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = "No slots are available for this doctor on the selected date.";
      slotList.appendChild(note);
      return;
    }

    bookingStudioState.slots.forEach((slot) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "booking-card-button slot";
      button.classList.toggle("active", bookingStudioState.slotId === slot.slot_id);
      const title = document.createElement("strong");
      title.className = "booking-card-title";
      title.textContent = formatDateTime(slot.start_time);

      const doctorName = document.createElement("span");
      doctorName.className = "booking-card-meta";
      doctorName.textContent = slot.doctor_name || bookingStudioState.doctor.doctor_name;

      button.append(title, doctorName);
      button.addEventListener("click", () => {
        bookingStudioState.slotId = slot.slot_id;
        renderSlots();
        setSummary();
      });
      slotList.appendChild(button);
    });
  };

  const loadDepartments = async () => {
    departmentSelect.disabled = true;
    try {
      const data = await authedJson("/appointments/departments");
      bookingStudioState.departments = data.departments || [];
      departmentSelect.replaceChildren();
      departmentSelect.appendChild(new Option("Choose a department", ""));
      bookingStudioState.departments.forEach((item) => {
        const label = `${item.department} (${item.doctor_count || 0} doctors, ${item.available_slot_count || 0} slots)`;
        departmentSelect.appendChild(new Option(label, item.department));
      });
      if (bookingStudioState.departments.length) {
        bookingStudioState.department = bookingStudioState.departments[0].department;
        departmentSelect.value = bookingStudioState.department;
      }
      departmentSelect.disabled = false;
      renderDates();
      await loadDoctors();
      scrollProfilePanelToTop();
    } catch (error) {
      renderEmptyPanel(error.message);
    }
  };

  const loadDoctors = async () => {
    if (!bookingStudioState.department) {
      bookingStudioState.doctors = [];
      bookingStudioState.doctor = null;
      bookingStudioState.slots = [];
      bookingStudioState.slotId = null;
      renderDoctors();
      renderSlots();
      setSummary();
      return;
    }

    doctorList.replaceChildren();
    const loading = document.createElement("p");
    loading.className = "panel-note";
    loading.textContent = "Loading doctors...";
    doctorList.appendChild(loading);

    try {
      const params = new URLSearchParams({ department: bookingStudioState.department, limit: "8" });
      if (bookingStudioState.date) {
        params.set("date", bookingStudioState.date);
      }
      const data = await authedJson(`/appointments/doctors?${params.toString()}`);
      bookingStudioState.doctors = data.doctors || [];
      bookingStudioState.doctor = bookingStudioState.doctors[0] || null;
      bookingStudioState.slotId = null;
      await loadSlots();
      renderDoctors();
      setSummary();
      scrollProfilePanelToTop();
    } catch (error) {
      renderEmptyPanel(error.message);
    }
  };

  const loadSlots = async () => {
    if (!bookingStudioState.doctor) {
      bookingStudioState.slots = [];
      renderSlots();
      setSummary();
      return;
    }

    slotList.replaceChildren();
    const loading = document.createElement("p");
    loading.className = "panel-note";
    loading.textContent = "Loading slots...";
    slotList.appendChild(loading);

    try {
      const params = new URLSearchParams({ doctor_id: bookingStudioState.doctor.doctor_id, limit: "8" });
      if (bookingStudioState.date) {
        params.set("date", bookingStudioState.date);
      }
      const data = await authedJson(`/appointments/slots?${params.toString()}`);
      bookingStudioState.slots = data.slots || [];
      bookingStudioState.slotId = null;
      renderSlots();
      setSummary();
      scrollProfilePanelToTop();
    } catch (error) {
      renderEmptyPanel(error.message);
    }
  };

  departmentSelect.addEventListener("change", async (event) => {
    bookingStudioState.department = event.target.value || null;
    bookingStudioState.doctor = null;
    bookingStudioState.slotId = null;
    bookingStudioState.doctors = [];
    bookingStudioState.slots = [];
    renderDoctors();
    renderSlots();
    setSummary();
    await loadDoctors();
  });

  actionButton.addEventListener("click", async () => {
    if (!bookingStudioState.slotId) {
      return;
    }
    actionButton.disabled = true;
    actionText.textContent = "Booking slot...";
    try {
      const data = await authedJson("/appointments/book", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slot_id: bookingStudioState.slotId }),
      });
      await showUpcomingBookings("Modify appointment");
      if (data?.booking) {
        const booking = data.booking;
        const doctorName = booking.doctor || booking.doctor_name || "Doctor";
        const departmentName = booking.department || "-";
        const appointmentTime = booking.time || booking.start_time;
        const referenceId = booking.booking_id || booking.slot_id || "-";
        addAssistantMessage(
          [
            "Your appointment is booked and confirmed.",
            "",
            `Doctor: ${doctorName}`,
            `Department: ${departmentName}`,
            `Date & Time: ${formatBookingDateTime(appointmentTime)}`,
            `Reference ID: ${referenceId}`,
            "",
            "Please arrive 10 minutes early. If you need anything else, you can continue chatting or close the session.",
          ].join("\n")
        );
      }
      scrollProfilePanelToTop();
    } catch (error) {
      actionText.textContent = error.message;
      actionButton.disabled = false;
      return;
    }
  });

  shell.append(left, right);
  left.append(buildBookingPanelSummary(), departmentCard, doctorCard);
  right.append(slotCard, actionCard);
  profilePanelBody.appendChild(shell);

  renderDates();
  setSummary();
  loadDepartments();
}

function bookingSummary(booking) {
  const shell = document.createElement("div");
  shell.className = "booking-summary-shell";

  const summary = document.createElement("div");
  summary.className = "booking-summary";

  const doctor = document.createElement("strong");
  doctor.textContent = booking.doctor || booking.doctor_name || "Doctor";
  const department = document.createElement("span");
  department.textContent = booking.department || "-";
  const time = document.createElement("span");
  time.textContent = formatDateTime(booking.time || booking.start_time);
  const status = document.createElement("span");
  status.textContent = `Status: ${booking.status || "booked"}`;

  summary.append(doctor, department, time, status);
  shell.appendChild(summary);
  shell.appendChild(buildClinicalNotesBlock(booking.booking_note));

  return shell;
}

function renderTokenUsage(usage) {
  const summary = usage || {};
  tokenInput.textContent = formatNumber(summary.input_tokens);
  tokenOutput.textContent = formatNumber(summary.output_tokens);
  tokenTotal.textContent = formatNumber(summary.total_tokens);
  tokenCalls.textContent = formatNumber(summary.llm_calls);
}

function renderChatSummary() {}
function renderRecentHistory() {}

function renderActiveAppointments(bookings) {
  activeAppointmentsPreview.replaceChildren();

  if (!Array.isArray(bookings) || !bookings.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No active appointments loaded.";
    activeAppointmentsPreview.appendChild(note);
    return;
  }

  bookings.slice(0, 3).forEach((booking) => {
    const item = document.createElement("article");
    item.className = "appointment-card";

    const title = document.createElement("strong");
    title.textContent = booking.doctor || booking.doctor_name || "Doctor";
    const dept = document.createElement("span");
    dept.textContent = booking.department || "-";
    const time = document.createElement("span");
    time.textContent = formatDateTime(booking.time || booking.start_time);

    item.append(title, dept, time);
    item.appendChild(buildClinicalNotesBlock(booking.booking_note, true));

    activeAppointmentsPreview.appendChild(item);
  });
}

function renderMarkdown(text) {
  // Escape HTML first to prevent XSS
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return escaped
    // Headings: ## and ###
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    // Bold
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    // Horizontal rule
    .replace(/^---+$/gm, "<hr>")
    // Bullet list items
    .replace(/^[-•] (.+)$/gm, "<li>$1</li>")
    // Wrap consecutive <li> in <ul>
    .replace(/(<li>[\s\S]*?<\/li>)(\s*(?!<li>))/g, "<ul>$1</ul>$2")
    // Paragraphs: blank lines become breaks
    .replace(/\n{2,}/g, "<br><br>")
    .replace(/\n/g, "<br>");
}

function buildClinicalNotesBlock(note, compact = false) {
  if (!note) {
    return document.createDocumentFragment();
  }

  const notePanel = document.createElement("details");
  notePanel.className = compact ? "clinical-notes-block compact" : "clinical-notes-block";
  notePanel.open = true;

  const noteSummary = document.createElement("summary");
  noteSummary.textContent = "Clinical Notes";

  const noteBody = document.createElement("div");
  noteBody.className = "clinical-notes-body";
  noteBody.innerHTML = renderMarkdown(note);

  notePanel.append(noteSummary, noteBody);
  return notePanel;
}

function updateWorkflowRail(activeLabel) {
  const steps = Array.from(workflowRail.querySelectorAll(".workflow-step"));
  steps.forEach((step) => {
    const text = step.textContent.trim().toLowerCase();
    const isActive =
      text === String(activeLabel || "").toLowerCase() ||
      (activeLabel === "RAG" && text === "rag") ||
      (activeLabel === "Booking" && text === "booking");
    step.classList.toggle("active", isActive);
  });
}

function updateWorkflowPanel(nextState) {
  const severity = nextState?.severity || "-";
  const department = nextState?.target_department || "-";
  const candidateCount = Array.isArray(nextState?.candidate_departments) ? nextState.candidate_departments.length : 0;
  const awaiting = nextState?.chat_closed ? "Closed" : nextState?.awaiting || "Describe symptoms";
  const activeIntent = nextState?.active_intent || nextState?.intent || null;
  const routingSource = nextState?.department_match_source || null;
  const routingConfidence = Number.isFinite(Number(nextState?.department_match_confidence))
    ? Number(nextState.department_match_confidence)
    : null;
  const retrievalAttempted = Boolean(nextState?.retrieval_attempted);
  const retrievalConfidence = Number.isFinite(Number(nextState?.retrieval_confidence))
    ? Number(nextState.retrieval_confidence)
    : null;

  severityEl.textContent = severity;
  departmentEl.textContent = department;
  awaitingEl.textContent = awaiting;

  const activeLabel = nextState?.chat_closed
    ? "Booking"
    : candidateCount > 1
      ? "Multi-dept"
    : activeIntent === "direct_booking" || nextState?.awaiting === "doctor_selection" || nextState?.awaiting === "slot_selection"
      ? "Booking"
      : activeIntent === "triage_symptoms" || nextState?.target_department
        ? "RAG"
        : "Conversation";

  workflowStateEl.textContent = activeLabel;
  updateWorkflowRail(activeLabel);

  const copy = nextState?.chat_closed
    ? "Care flow paused or completed."
    : nextState?.chat_summary
      ? nextState.chat_summary
      : candidateCount > 1
        ? "I found more than one likely department. The assistant is helping you keep the thread together and decide what to book first."
      : activeIntent
        ? `Current intent: ${activeIntent.replaceAll("_", " ")}.`
        : nextState?.awaiting
          ? `The assistant is waiting for ${nextState.awaiting.replaceAll("_", " ")}.`
          : "Describe symptoms, ask for care, or continue the booking flow.";
  topbarCopy.textContent = copy;

  if (routingMeta) {
    if (!routingSource && !retrievalAttempted && !nextState?.target_department) {
      routingMeta.textContent = "Department routing has not run yet.";
    } else {
      const sourceLabel = routingSource ? routingSource.toUpperCase() : "UNKNOWN";
      const confidenceLabel = routingConfidence === null ? "-" : routingConfidence.toFixed(2);
      const retrievalLabel = retrievalAttempted
        ? `retrieval attempted${retrievalConfidence === null ? "" : `, score ${retrievalConfidence.toFixed(2)}`}`
        : "no retrieval";
      routingMeta.textContent = `Department routing: ${department}\nSource: ${sourceLabel}\nConfidence: ${confidenceLabel}\nRetrieval: ${retrievalLabel}`;
    }
  }

  if (nextState?.candidate_departments && nextState.candidate_departments.length > 1) {
    const labels = nextState.candidate_departments
      .map((candidate) => candidate?.department)
      .filter(Boolean)
      .join(", ");
    routingMeta.textContent += `\nPossible departments: ${labels}`;
  }
}

function renderState(nextState) {
  state = normalizeChatState(nextState, state);
  updateWorkflowPanel(state);
  renderChatSummary(state?.chat_summary || "");
  renderRecentHistory(state?.messages || state?.recent_history || []);
  renderActiveAppointments(state?.upcoming_bookings || state?.active_appointments || []);
  renderTokenUsage(state?.token_usage || null);
  renderAnalyzedDocs(state?.analyzed_documents || []);
  if (pendingUploadFiles.length === 0 && !state?.pending_file_name) {
    setUploadStatus("", "default");
  }
  scrollMessages(false);
  setChatTopButtonVisible(messages.scrollTop > 180);
}

function addQuickAction(label, value) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", () => {
    input.value = value;
    autoResizeComposer();
    form.requestSubmit();
  });
  quickActions.appendChild(button);
}

function formatDoctorExperience(doctor) {
  const years = Number(doctor?.experience_years ?? doctor?.years_of_experience ?? 0);
  const label = Number.isFinite(years) ? years : 0;
  return `Experience: ${label} year${label === 1 ? "" : "s"}`;
}

function renderQuickActions() {
  clearQuickActions();

  if (!state?.awaiting) {
    return;
  }

  if (state.awaiting === "file_clarification") {
    addQuickAction("Regarding current symptom", "Regarding current symptom");
    addQuickAction("New symptom", "New symptom");
    addQuickAction("Please analyze this file", "Please analyze this file");
    return;
  }

  if (state.awaiting === "appointment_resolver" && Array.isArray(state.upcoming_bookings) && state.upcoming_bookings.length) {
    state.upcoming_bookings.forEach((booking, index) => {
      const label = `${index + 1}. ${booking.doctor || booking.doctor_name || "Doctor"} • ${formatDateTime(booking.time || booking.start_time)}`;
      addQuickAction(label, String(index + 1));
    });
    addQuickAction("Cancel", "cancel");
    addQuickAction("Change", "change");
    return;
  }

  if (state.awaiting === "doctor_selection" && Array.isArray(state.doctor_options)) {
    state.doctor_options.forEach((doctor, index) => {
      const years = Number(doctor?.experience_years ?? doctor?.years_of_experience ?? 0);
      const experienceLabel = Number.isFinite(years) ? `${years} years experience` : "0 years experience";
      addQuickAction(`${index + 1}. ${doctor.doctor_name} | ${experienceLabel}`, String(index + 1));
    });
    addQuickAction("No appointment", "no");
  }

  if (state.awaiting === "slot_selection" && Array.isArray(state.slot_options)) {
    state.slot_options.forEach((slot, index) => {
      const time = new Date(slot.start_time).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
      addQuickAction(`${index + 1}. ${time}`, String(index + 1));
    });
    addQuickAction("No appointment", "no");
  }

  if (state.awaiting === "cancellation_selection" && Array.isArray(state.cancellation_options)) {
    state.cancellation_options.forEach((booking, index) => {
      addQuickAction(`${index + 1}. ${booking.doctor}`, String(index + 1));
    });
  }

  if (state.awaiting === "reschedule_selection" && Array.isArray(state.reschedule_options)) {
    state.reschedule_options.forEach((booking, index) => {
      addQuickAction(`${index + 1}. ${booking.doctor}`, String(index + 1));
    });
  }

  if (state.awaiting === "date_selection" && Array.isArray(state.date_options)) {
    state.date_options.forEach((option, index) => {
      addQuickAction(`${index + 1}. ${option.label}`, String(index + 1));
    });
  }

  if (state.awaiting === "department_selection" && Array.isArray(state.candidate_departments)) {
    state.candidate_departments.forEach((candidate, index) => {
      addQuickAction(`${index + 1}. ${candidate.department}`, String(index + 1));
    });
    addQuickAction("No, not now", "no");
  }

  if (state.awaiting === "reschedule_date_selection" && Array.isArray(state.reschedule_date_options)) {
    state.reschedule_date_options.forEach((option, index) => {
      addQuickAction(`${index + 1}. ${option.label}`, String(index + 1));
    });
  }

  if (state.awaiting === "reschedule_slot_selection" && Array.isArray(state.reschedule_slot_options)) {
    state.reschedule_slot_options.forEach((slot, index) => {
      const time = new Date(slot.start_time).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
      addQuickAction(`${index + 1}. ${time}`, String(index + 1));
    });
  }
}

function autoResizeComposer() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
}

function buildChatRequest(message, nextState = null) {
  const sessionId = nextState?.session_id || nextState?.chat_session_id || currentSessionId();

  // File was already cached server-side during /chat/upload — always send JSON,
  // never re-send the file in FormData to /chat/stream.

  return {
    body: JSON.stringify({
      message,
      session_id: sessionId,
      state: nextState || state || {},
    }),
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

async function sendMessage(message) {
  if (!patientId || !accessToken) {
    setStatus("Login required");
    return;
  }

  setStatus("Working");
  setComposerDisabled(true);
  const assistantMessage = addTypingAssistantMessage();

  try {
    const requestPayload = buildChatRequest(message, state);
    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: requestPayload.headers,
      body: requestPayload.body,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Request failed with ${response.status}`);
    }

    const data = await readChatStream(response, assistantMessage);
    if (!data?.state) {
      throw new Error("The assistant did not return a final chat state.");
    }

    const nextState = {
      ...data.state,
      token_usage: data.token_usage || data.state.token_usage || state?.token_usage || null,
    };

    renderState(nextState);
    if (nextState?.chat_closed) {
      showChatClosed();
    } else {
      renderQuickActions();
      if (pendingUploadFiles.length > 0) {
        if (documentUpload) documentUpload.value = "";
        clearAttachPill();
        setUploadStatus("", "default");
      }
      setStatus("Ready");
    }
  } catch (error) {
    if (String(error.message).includes("401")) {
      clearAuthenticated();
      showAuthMode("login");
    }
    if (assistantMessage?.node?.parentNode) {
      await streamAssistantText(assistantMessage, `Request failed: ${error.message}`);
    } else {
      addAssistantMessage(`Request failed: ${error.message}`);
    }
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
  if (documentUpload) documentUpload.value = "";
  clearAttachPill();
  setUploadStatus("", "default");
  renderAnalyzedDocs([]);
  const greeting = currentUser
    ? `Hello ${currentUser.name}. Describe your symptoms, book an appointment, or ask to cancel an appointment.`
    : "Please sign in to begin.";
  state = {
    patient_profile: currentUser,
    session_id: newChatSessionId(),
    chat_session_id: null,
    messages: [{ role: "assistant", text: greeting }],
    recent_history: [{ role: "assistant", text: greeting }],
    conversation_history: [{ role: "assistant", text: greeting }],
    chat_summary: "",
    chat_closed: false,
    awaiting: null,
    active_intent: null,
    collected_data: {},
    upcoming_bookings: [],
    analyzed_documents: [],
    token_usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0, llm_calls: 0 },
  };
  messages.replaceChildren();
  addAssistantMessage(greeting, { intro: true, noAnimation: true });
  renderState(state);
  clearQuickActions();
  setStatus("Ready");
  input.focus();
  scrollMessages(false);
  setChatTopButtonVisible(false);
}

async function showPreviousBookings(title = "Previous bookings") {
  setProfilePanelLoading(title);
  try {
    const data = await authedJson("/appointments/previous");
    const bookings = data.bookings || [];
    if (!bookings.length) {
      renderEmptyPanel("No previous bookings found for your account.");
      return;
    }

    profilePanelBody.replaceChildren();
    bookings.forEach((booking) => {
      const item = document.createElement("article");
      item.className = "booking-item";
      item.appendChild(bookingSummary(booking));
      profilePanelBody.appendChild(item);
    });
    scrollProfilePanelToTop();
  } catch (error) {
    renderEmptyPanel(error.message);
  }
}

async function showUpcomingBookings(title = "Upcoming bookings") {
  setProfilePanelLoading(title);
  try {
    const data = await authedJson("/appointments/upcoming");
    renderUpcomingBookings(data.bookings || []);
    scrollProfilePanelToTop();
  } catch (error) {
    renderEmptyPanel(error.message);
  }
}

function renderUpcomingBookings(bookings) {
  if (!bookings.length) {
    renderEmptyPanel("No upcoming bookings found for your account.");
    return;
  }

  profilePanelBody.replaceChildren();
  bookings.forEach((booking) => {
    const item = document.createElement("article");
    item.className = "booking-item";
    item.appendChild(bookingSummary(booking));

    const actions = document.createElement("div");
    actions.className = "booking-actions";

    if (booking.can_modify) {
      const cancelBtn = document.createElement("button");
      cancelBtn.className = "secondary compact";
      cancelBtn.type = "button";
      cancelBtn.textContent = "Cancel";
      cancelBtn.addEventListener("click", () => cancelBooking(booking.booking_id));

      const changeBtn = document.createElement("button");
      changeBtn.className = "secondary compact";
      changeBtn.type = "button";
      changeBtn.textContent = "Change date";
      changeBtn.addEventListener("click", () => showRescheduleControls(item, booking));

      actions.append(cancelBtn, changeBtn);
    } else {
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = "Changes are locked because this appointment is within 24 hours.";
      actions.appendChild(note);
    }

    item.appendChild(actions);
    profilePanelBody.appendChild(item);
  });
  scrollProfilePanelToTop();
}

async function cancelBooking(bookingId) {
  setStatus("Working");
  try {
    await authedJson(`/appointments/${bookingId}/cancel`, { method: "POST" });
    await showUpcomingBookings();
    setStatus("Ready");
  } catch (error) {
    setStatus("Error");
    renderEmptyPanel(error.message);
  }
}

function showRescheduleControls(container, booking) {
  let controls = container.querySelector(".reschedule-controls");
  if (controls) {
    controls.remove();
  }

  controls = document.createElement("div");
  controls.className = "reschedule-controls";

  const label = document.createElement("label");
  label.textContent = "Choose new date";
  const dateInput = document.createElement("input");
  dateInput.type = "date";
  dateInput.required = true;
  const today = new Date();
  const maxDate = new Date(today);
  maxDate.setDate(today.getDate() + 7);
  dateInput.min = localDateString(today);
  dateInput.max = localDateString(maxDate);
  label.appendChild(dateInput);

  const loadBtn = document.createElement("button");
  loadBtn.className = "secondary compact";
  loadBtn.type = "button";
  loadBtn.textContent = "Show slots";

  const slots = document.createElement("div");
  slots.className = "slot-options";

  loadBtn.addEventListener("click", async () => {
    if (!dateInput.value) {
      slots.textContent = "Please choose a date first.";
      return;
    }
    if (dateInput.value < dateInput.min || dateInput.value > dateInput.max) {
      slots.textContent = "Please choose a date within the next 7 days.";
      return;
    }
    slots.textContent = "Loading slots...";
    try {
      const data = await authedJson(
        `/appointments/${booking.booking_id}/reschedule-options?date=${encodeURIComponent(dateInput.value)}`
      );
      renderRescheduleSlots(slots, booking.booking_id, data.slots || []);
    } catch (error) {
      slots.textContent = error.message;
    }
  });

  controls.append(label, loadBtn, slots);
  container.appendChild(controls);
}

function renderRescheduleSlots(container, bookingId, slots) {
  container.replaceChildren();
  if (!slots.length) {
    container.textContent = "No available slots for that date.";
    return;
  }

  slots.forEach((slot) => {
    const button = document.createElement("button");
    button.className = "secondary compact";
    button.type = "button";
    button.textContent = formatDateTime(slot.start_time);
    button.addEventListener("click", async () => {
      setStatus("Working");
      try {
        await authedJson(`/appointments/${bookingId}/reschedule`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slot_id: slot.slot_id }),
        });
        await showUpcomingBookings();
        setStatus("Ready");
      } catch (error) {
        setStatus("Error");
        container.textContent = error.message;
      }
    });
    container.appendChild(button);
  });
}

async function showChatHistory() {
  setProfilePanelLoading("Chat history by case");
  try {
    const data = await authedJson("/chat/history");
    const sessions = data.sessions || [];
    if (!sessions.length) {
      renderEmptyPanel("No previous chat history found for your account.");
      return;
    }

    profilePanelBody.replaceChildren();
    const shell = document.createElement("div");
    shell.className = "history-browser";

    const sidebar = document.createElement("nav");
    sidebar.className = "history-sidebar";
    sidebar.setAttribute("aria-label", "Chat sessions");

    const transcript = document.createElement("section");
    transcript.className = "history-transcript";

    const buildMeta = (session) => ({
      dateLabel: formatDateLabel(session.started_at || session.date),
      messageCount: session.message_count || (session.messages || []).length,
    });

    const renderMessage = (message) => {
      const isPatient = message.role === "patient" || message.role === "user";
      const item = document.createElement("div");
      item.className = `hx-bubble ${isPatient ? "hx-bubble--patient" : "hx-bubble--assistant"}`;

      const bubble = document.createElement("div");
      bubble.className = "hx-bubble-body";
      bubble.innerHTML = renderMarkdown(message.text || "");

      const time = document.createElement("time");
      time.className = "hx-bubble-time";
      time.textContent = message.created_at
        ? new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : "";

      item.append(bubble, time);
      return item;
    };

    function renderSession(session, selectedCard) {
      sidebar.querySelectorAll(".history-session-card").forEach((c) => {
        c.classList.toggle("active", c === selectedCard);
      });

      transcript.replaceChildren();

      const header = document.createElement("div");
      header.className = "history-transcript-header";

      const titleEl = document.createElement("h3");
      titleEl.className = "history-transcript-title";
      titleEl.textContent = session.title || "Conversation";

      const details = buildMeta(session);
      const metaEl = document.createElement("span");
      metaEl.className = "history-transcript-meta";
      metaEl.textContent = `${details.dateLabel} · ${details.messageCount} messages`;

      header.append(titleEl, metaEl);
      transcript.appendChild(header);

      const thread = document.createElement("div");
      thread.className = "history-thread";
      (session.messages || []).forEach((message) => {
        thread.appendChild(renderMessage(message));
      });
      transcript.appendChild(thread);
    }

    sessions.forEach((session, index) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "history-session-card";

      const details = buildMeta(session);

      const cardTitle = document.createElement("span");
      cardTitle.className = "hsc-title";
      cardTitle.textContent = session.title || "Conversation";

      const cardMeta = document.createElement("span");
      cardMeta.className = "hsc-meta";
      cardMeta.textContent = `${details.dateLabel} · ${details.messageCount} messages`;

      card.append(cardTitle, cardMeta);
      card.addEventListener("click", () => renderSession(session, card));
      sidebar.appendChild(card);

      if (index === 0) {
        renderSession(session, card);
      }
    });

    shell.append(sidebar, transcript);
    profilePanelBody.appendChild(shell);
  } catch (error) {
    renderEmptyPanel(error.message);
  }
}

function adjustComposerHeight() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  const hasFiles = pendingUploadFiles.length > 0;

  if (!message && !hasFiles) return;

  if (state?.chat_closed) {
    showChatClosed();
    return;
  }

  const effectiveMessage = message || (
    pendingUploadFiles.length === 1
      ? "Please analyze this medical document."
      : `Please analyze these ${pendingUploadFiles.length} medical documents.`
  );

  input.value = "";
  adjustComposerHeight();
  clearQuickActions();

  if (hasFiles) {
    addUserMessageWithFile(message, pendingUploadFiles.map(f => f.name));
  } else {
    addUserMessage(message);
  }

  await sendMessage(effectiveMessage);
});

input.addEventListener("input", adjustComposerHeight);
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

messages.addEventListener("scroll", () => {
  setChatTopButtonVisible(messages.scrollTop > 180);
});

resetBtn.addEventListener("click", () => {
  resetChat();
});

if (bookAppointmentBtn) {
  bookAppointmentBtn.addEventListener("click", () => {
    bookingStudioState = {
      departments: [],
      department: null,
      doctors: [],
      doctor: null,
      date: null,
      slots: [],
      slotId: null,
      mode: "book",
    };
    showProfilePanel("Book appointment");
    renderBookingStudio();
    scrollProfilePanelToTop();
  });
}

if (modifyAppointmentBtn) {
  modifyAppointmentBtn.addEventListener("click", () => {
    showUpcomingBookings("Modify appointment");
  });
}

if (sidebarToggleBtn) {
  sidebarToggleBtn.addEventListener("click", () => {
    setSidebarOpen(!sidebarOpen);
  });
}

if (sidebarHandleBtn) {
  sidebarHandleBtn.addEventListener("click", () => {
    setSidebarOpen(!sidebarOpen);
  });
}

if (scrollTopBtn) {
  scrollTopBtn.addEventListener("click", () => {
    scrollMessagesToTop();
    setChatTopButtonVisible(false);
  });
}

previousBookingsBtn.addEventListener("click", () => showPreviousBookings());
upcomingBookingsBtn.addEventListener("click", () => showUpcomingBookings());
chatHistoryBtn.addEventListener("click", showChatHistory);
closeProfilePanelBtn.addEventListener("click", hideProfilePanel);

function showEditProfile() {
  if (!currentUser) return;
  showProfilePanel("Edit profile");

  const form = document.createElement("form");
  form.className = "edit-profile-form";
  form.innerHTML = `
    <label class="ep-label">
      <span>Health issues / pre-existing conditions</span>
      <textarea class="ep-textarea" id="epHealthIssues" rows="3" placeholder="e.g. Diabetes, Hypertension">${currentUser.health_issues || ""}</textarea>
    </label>
    <label class="ep-label">
      <span>Mobile number</span>
      <input class="ep-input" id="epMobile" type="tel" value="${currentUser.mobile_number || ""}" placeholder="+91 9876543210"/>
    </label>
    <label class="ep-label">
      <span>Address</span>
      <input class="ep-input" id="epAddress" type="text" value="${currentUser.address || ""}" placeholder="Street, City"/>
    </label>
    <div class="ep-actions">
      <button type="submit" class="ep-save-btn" id="epSaveBtn">Save changes</button>
      <span class="ep-msg" id="epMsg"></span>
    </div>
  `;

  profilePanelBody.replaceChildren(form);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const saveBtn = document.querySelector("#epSaveBtn");
    const msg = document.querySelector("#epMsg");
    saveBtn.disabled = true;
    msg.textContent = "Saving…";

    const payload = {
      health_issues: document.querySelector("#epHealthIssues").value.trim() || null,
      mobile_number: document.querySelector("#epMobile").value.trim() || null,
      address: document.querySelector("#epAddress").value.trim() || null,
    };

    try {
      const data = await authedJson("/auth/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      currentUser = data.user;
      localStorage.setItem("currentUser", JSON.stringify(currentUser));
      setPatientSummary(currentUser);
      msg.textContent = "Saved!";
      msg.style.color = "var(--violet)";
      setTimeout(hideProfilePanel, 900);
    } catch (err) {
      msg.textContent = err.message || "Save failed.";
      msg.style.color = "#dc2626";
      saveBtn.disabled = false;
    }
  });
}

if (editProfileBtn) {
  editProfileBtn.addEventListener("click", showEditProfile);
}

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

window.addEventListener("resize", adjustComposerHeight);

if (documentUpload) {
  documentUpload.addEventListener("change", async () => {
    const file = documentUpload.files?.[0] || null;
    if (!file) return;

    setUploadStatus(`Validating "${file.name}"…`, "sending");
    setComposerDisabled(true);
    clearAttachPill();

    try {
      // Step 1: POST /chat/upload — Azure GPT-4o medical relevance check + staging
      const uploadForm = new FormData();
      uploadForm.append("file", file);
      uploadForm.append("session_id", currentSessionId() || "");

      const uploadResp = await fetch("/chat/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: uploadForm,
      });

      if (!uploadResp.ok) {
        const errData = await uploadResp.json().catch(() => ({}));
        throw new Error(errData.detail || `Validation failed (${uploadResp.status})`);
      }

      const { document_token } = await uploadResp.json();

      // Step 2: Consent dialog
      const consent = confirm(
        `"${file.name}" has been verified as a valid medical document.\n\n` +
        `Store securely in your health vault for AI-assisted analysis?\n\n` +
        `OK = store & analyze  |  Cancel = discard`
      );

      // Step 3: Confirm/discard — fire and forget
      fetch("/chat/confirm-processing", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ document_token, consent_granted: consent }),
      }).catch(err => console.warn("confirm-processing error:", err));

      if (!consent) {
        setUploadStatus("Document discarded.", "default");
        clearAttachPill();
        documentUpload.value = "";
        setComposerDisabled(false);
        return;
      }

      // Step 4: Stage pill — wait for user to type a question or just click Send
      pendingUploadFiles.push(file);
      showAttachPill(file);
      setUploadStatus("", "default");
      setComposerDisabled(false);
      input.focus();

    } catch (err) {
      setUploadStatus(`Upload error: ${err.message}`, "error");
      documentUpload.value = "";
      setComposerDisabled(false);
    }
  });
}

async function bootstrapSession() {
  if (!currentUser || !accessToken) {
    clearAuthenticated();
    showAuthMode("login");
    return;
  }

  try {
    const data = await authedJson("/auth/me");
    setAuthenticated(data.user, accessToken);
  } catch (error) {
    clearAuthenticated();
    showAuthMode("login");
    setAuthMessage("Your session expired. Please sign in again.");
  }
}

bootstrapSession();
setSidebarOpen(sidebarOpen);


