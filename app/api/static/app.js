const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const voiceBtn = document.querySelector("#voiceBtn");
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
const dashboardDocsList = document.querySelector("#dashboardDocsList");
const documentUpload = document.querySelector("#documentUpload");
const uploadStatus = document.querySelector("#uploadStatus");
const attachPills = document.querySelector("#attachPills");
const analyzedDocsList = document.querySelector("#analyzedDocsList");
const voiceTranscriptPreview = document.querySelector("#voiceTranscriptPreview");
const voiceStatusPreview = document.querySelector("#voiceStatusPreview");
const voiceStatusText = voiceStatusPreview?.querySelector(".voice-status-text") || null;
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
const adminDoctorFilter = document.querySelector("#adminDoctorFilter");
const adminRefreshBtn = document.querySelector("#adminRefreshBtn");
const adminLogoutBtn = document.querySelector("#adminLogoutBtn");
const adminAppointmentsList = document.querySelector("#adminAppointmentsList");
const adminResultCount = document.querySelector("#adminResultCount");
const adminFilterHint = document.querySelector("#adminFilterHint");
const adminPrevPageBtn = document.querySelector("#adminPrevPageBtn");
const adminNextPageBtn = document.querySelector("#adminNextPageBtn");
const adminPageIndicator = document.querySelector("#adminPageIndicator");
const adminStatTotal = document.querySelector("#adminStatTotal");
const adminStatUpcoming = document.querySelector("#adminStatUpcoming");
const adminStatPast = document.querySelector("#adminStatPast");
const adminStatDoctors = document.querySelector("#adminStatDoctors");
const adminStatPatients = document.querySelector("#adminStatPatients");
const adminDoctorsList = document.querySelector("#adminDoctorsList");
const adminSlotsList = document.querySelector("#adminSlotsList");
const adminHolidaysList = document.querySelector("#adminHolidaysList");
const adminDepartmentsList = document.querySelector("#adminDepartmentsList");
const adminDoctorForm = document.querySelector("#adminDoctorForm");
const adminDoctorSelect = document.querySelector("#adminDoctorSelect");
const adminDoctorName = document.querySelector("#adminDoctorName");
const adminDoctorDepartment = document.querySelector("#adminDoctorDepartment");
const adminDoctorExperience = document.querySelector("#adminDoctorExperience");
const adminDoctorActive = document.querySelector("#adminDoctorActive");
const adminDoctorResetBtn = document.querySelector("#adminDoctorResetBtn");
const adminDoctorMessage = document.querySelector("#adminDoctorMessage");
const adminSlotForm = document.querySelector("#adminSlotForm");
const adminSlotDoctorSelect = document.querySelector("#adminSlotDoctorSelect");
const adminSlotWorkStart = document.querySelector("#adminSlotWorkStart");
const adminSlotLunchStart = document.querySelector("#adminSlotLunchStart");
const adminSlotLunchEnd = document.querySelector("#adminSlotLunchEnd");
const adminSlotWorkEnd = document.querySelector("#adminSlotWorkEnd");
const adminSlotStartDate = document.querySelector("#adminSlotStartDate");
const adminSlotEndDate = document.querySelector("#adminSlotEndDate");
const adminSlotDuration = document.querySelector("#adminSlotDuration");
const adminSlotActive = document.querySelector("#adminSlotActive");
const adminSlotMessage = document.querySelector("#adminSlotMessage");
const adminHolidayForm = document.querySelector("#adminHolidayForm");
const adminHolidayScope = document.querySelector("#adminHolidayScope");
const adminHolidayDoctorSelect = document.querySelector("#adminHolidayDoctorSelect");
const adminHolidayStart = document.querySelector("#adminHolidayStart");
const adminHolidayEnd = document.querySelector("#adminHolidayEnd");
const adminHolidayReason = document.querySelector("#adminHolidayReason");
const adminHolidayActive = document.querySelector("#adminHolidayActive");
const adminHolidayMessage = document.querySelector("#adminHolidayMessage");
const adminViewButtons = Array.from(document.querySelectorAll("[data-admin-view]"));
const adminOverviewPane = document.querySelector("#adminOverviewPane");
const adminAppointmentsPane = document.querySelector("#adminAppointmentsPane");
const adminManagePane = document.querySelector("#adminManagePane");
const adminInventoryPane = document.querySelector("#adminInventoryPane");
const adminStatusButtons = Array.from(document.querySelectorAll("[data-admin-status]"));
const adminRefreshLabel = adminRefreshBtn?.querySelector(".admin-action-label") || null;
const adminToast = document.querySelector("#adminToast");
let adminRefreshResetTimer = null;
let adminToastTimer = null;
const profilePanel = document.querySelector("#profilePanel");
const profilePanelTitle = document.querySelector("#profilePanelTitle");
const profilePanelBody = document.querySelector("#profilePanelBody");
const closeProfilePanelBtn = document.querySelector("#closeProfilePanelBtn");
const chatClosedModal = document.querySelector("#chatClosedModal");
const startNewChatBtn = document.querySelector("#startNewChatBtn");

const showLoginBtn = document.querySelector("#showLoginBtn");
const showSignupBtn = document.querySelector("#showSignupBtn");
const showAdminBtn = document.querySelector("#showAdminBtn");
const authTabs = document.querySelector(".auth-tabs");
const loginForm = document.querySelector("#loginForm");
const signupForm = document.querySelector("#signupForm");
const adminLoginForm = document.querySelector("#adminLoginForm");
const adminBackBtn = document.querySelector("#adminBackBtn");
const pageAssistant = document.querySelector("#pageAssistant");
const pageDashboard = document.querySelector("#pageDashboard");
const pageAppointments = document.querySelector("#pageAppointments");
const pageRecords = document.querySelector("#pageRecords");
const pageAdmin = document.querySelector("#pageAdmin");
const signupStepOne = document.querySelector("#signupStepOne");
const signupStepTwo = document.querySelector("#signupStepTwo");
const signupNextBtn = document.querySelector("#signupNextBtn");
const signupBackBtn = document.querySelector("#signupBackBtn");
const authMessage = document.querySelector("#authMessage");
const adminAuthMessage = document.querySelector("#adminAuthMessage");

let state = null;
let currentUser = JSON.parse(localStorage.getItem("currentUser") || "null");
let accessToken = localStorage.getItem("accessToken");
let currentAdmin = JSON.parse(localStorage.getItem("currentAdmin") || "null");
let adminAccessToken = localStorage.getItem("adminAccessToken");
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
let adminAppointments = [];
let adminAppointmentsLoaded = false;
let adminAppointmentsLoading = false;
let adminAppointmentsLoadPromise = null;
let adminSelectedStatus = "all";
let adminAppointmentsPage = 1;
const adminAppointmentsPageSize = 6;
let adminDoctors = [];
let adminSlots = [];
let adminHolidays = [];
let adminDepartments = [];
let adminDoctorEditingId = "";
let adminManagementLoaded = false;
let adminSelectedAppointment = null;
let voiceStream = null;
let voiceRecorder = null;
let voiceAudioContext = null;
let voiceSocket = null;
let voiceFinalTranscript = "";
let voiceLiveTranscript = "";
let voiceListening = false;
let voicePendingFrames = [];
let voiceStopping = false;
let voiceCommitTimer = null;
let voiceWorkletNode = null;
let recordsArchive = {
  documents: [],
  sessionsById: new Map(),
  loaded: false,
  loading: false,
};

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

function normalizeDocumentEntry(doc) {
  if (!doc || typeof doc !== "object") return null;
  return {
    document_id: String(doc.document_id || ""),
    user_id: String(doc.user_id || ""),
    session_id: String(doc.session_id || ""),
    original_filename: doc.original_filename || doc.file_name || "uploaded-file",
    file_name: doc.original_filename || doc.file_name || "uploaded-file",
    document_type: doc.document_type || "document",
    clinical_date: doc.clinical_date || null,
    created_at: doc.created_at || null,
    ingestion_status: doc.ingestion_status || "complete",
  };
}

function documentsForSession(sessionId) {
  const docs = recordsArchive.documents || [];
  if (!sessionId) return docs;
  return docs.filter((doc) => String(doc.session_id || "") === String(sessionId));
}

function buildDocumentCard(doc, options = {}) {
  const card = document.createElement("article");
  card.className = "analyzed-doc-item";

  const title = document.createElement("button");
  title.type = "button";
  title.className = "doc-session-link";
  title.textContent = options.sessionLabel || `Chat ${doc.session_id || "n/a"}`;
  title.title = "Open the matching chat history";
  title.addEventListener("click", () => {
    showWorkspacePage("records");
    showChatHistory(String(doc.session_id || ""));
  });

  const name = document.createElement("div");
  name.className = "analyzed-doc-name";
  name.title = doc.file_name || "Unknown file";
  name.textContent = doc.file_name || "Unknown file";

  const meta = document.createElement("div");
  meta.className = "analyzed-doc-meta";
  const parts = [
    (doc.document_type || "document").replaceAll("_", " "),
    doc.clinical_date ? `Date: ${doc.clinical_date}` : null,
  ].filter(Boolean);
  meta.textContent = parts.join(" · ");

  const status = document.createElement("div");
  status.className = "analyzed-doc-dept";
  status.textContent = `Chat ${doc.session_id || "n/a"}`;

  card.append(title, name, meta, status);
  return card;
}

function renderDocumentsPanel(docs, container = analyzedDocsList) {
  if (!container) return;
  container.replaceChildren();

  const normalized = (Array.isArray(docs) ? docs : [])
    .map(normalizeDocumentEntry)
    .filter(Boolean);

  if (!normalized.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No documents analyzed yet. Use 📎 in the chat to attach a file.";
    container.appendChild(note);
    return;
  }

  normalized.forEach((doc) => {
    container.appendChild(buildDocumentCard(doc));
  });
}

function renderChatSessionDocuments(session, container) {
  const docs = documentsForSession(session?.chat_session_id);
  const box = document.createElement("section");
  box.className = "history-session-docs";

  const heading = document.createElement("div");
  heading.className = "history-session-docs-head";

  const title = document.createElement("h4");
  title.textContent = "Documents in this chat";

  const count = document.createElement("span");
  count.textContent = `${docs.length} file${docs.length === 1 ? "" : "s"}`;

  heading.append(title, count);
  box.appendChild(heading);

  const row = document.createElement("div");
  row.className = "history-doc-row";

  const label = document.createElement("span");
  label.className = "history-doc-label";
  label.textContent = "Docs";
  row.appendChild(label);

  if (!docs.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No documents were uploaded in this conversation.";
    row.appendChild(note);
  } else {
    docs.forEach((doc) => {
      row.appendChild(buildDocumentCard(doc, { sessionLabel: `Chat ${session.chat_session_id}` }));
    });
  }

  box.appendChild(row);
  container.appendChild(box);
}

function showUploadMessage(filename, status = "Uploading...") {
  const { node, body } = addAssistantMessage(status, { noAnimation: false });
  node.classList.add("uploading-message");
  body.innerHTML = "";

  const label = document.createElement("div");
  label.className = "uploading-message-label";
  label.textContent = status;

  const file = document.createElement("div");
  file.className = "uploading-message-file";
  file.textContent = filename;

  body.append(label, file);
  return {
    node,
    body,
    setStatus(nextStatus) {
      label.textContent = nextStatus;
    },
    setFile(nextFile) {
      file.textContent = nextFile;
    },
    remove() {
      node.remove();
    },
  };
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

function setAdminAuthMessage(text) {
  if (adminAuthMessage) {
    adminAuthMessage.textContent = text || "";
  }
}

function setAdminDoctorMessage(text) {
  if (adminDoctorMessage) {
    adminDoctorMessage.textContent = text || "";
  }
}

function setAdminSlotMessage(text) {
  if (adminSlotMessage) {
    adminSlotMessage.textContent = text || "";
  }
}

function setAdminHolidayMessage(text) {
  if (adminHolidayMessage) {
    adminHolidayMessage.textContent = text || "";
  }
}

function showAdminToast(message, tone = "success", timeoutMs = 1800) {
  if (!adminToast || !message) return;

  if (adminToastTimer) {
    window.clearTimeout(adminToastTimer);
    adminToastTimer = null;
  }

  adminToast.textContent = message;
  adminToast.className = `admin-toast is-${tone} enter`;
  adminToast.classList.remove("hidden");

  adminToastTimer = window.setTimeout(() => {
    adminToast.classList.add("hidden");
    adminToast.classList.remove("enter");
    adminToastTimer = null;
  }, timeoutMs);
}

function showWorkspacePage(page) {
  const pages = {
    assistant: pageAssistant,
    dashboard: pageDashboard,
    appointments: pageAppointments,
    records: pageRecords,
    admin: pageAdmin,
  };

  Object.entries(pages).forEach(([key, element]) => {
    if (!element) return;
    element.classList.toggle("hidden", key !== page);
  });

  document.querySelectorAll("[data-nav]").forEach((element) => {
    element.classList.toggle("is-active", element.dataset.nav === page);
  });
}

function preferredAdminView() {
  const saved = localStorage.getItem("adminView");
  return ["overview", "appointments", "manage", "inventory"].includes(saved) ? saved : "overview";
}

function showAdminView(view) {
  const nextView = ["overview", "appointments", "manage", "inventory"].includes(view) ? view : "overview";
  const panes = {
    overview: adminOverviewPane,
    appointments: adminAppointmentsPane,
    manage: adminManagePane,
    inventory: adminInventoryPane,
  };

  Object.entries(panes).forEach(([key, element]) => {
    if (!element) return;
    element.classList.toggle("hidden", key !== nextView);
  });

  adminViewButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.adminView === nextView);
  });

  localStorage.setItem("adminView", nextView);
  if (nextView === "manage" || nextView === "inventory") {
    loadAdminManagement();
  }
  if (nextView === "appointments") {
    loadAdminAppointments();
  }
}

function showAuthMode(mode) {
  const isLogin = mode === "login";
  const isSignup = mode === "signup";
  const isAdmin = mode === "admin";
  loginForm.classList.toggle("hidden", !isLogin);
  signupForm.classList.toggle("hidden", !isSignup);
  if (adminLoginForm) {
    adminLoginForm.classList.toggle("hidden", !isAdmin);
  }
  showLoginBtn.classList.toggle("active", isLogin);
  showSignupBtn.classList.toggle("active", isSignup);
  if (showAdminBtn) {
    showAdminBtn.classList.toggle("active", isAdmin);
  }
  setAuthMessage("");
  setAdminAuthMessage("");
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

function setPatientAuthenticated(user, token) {
  currentUser = user;
  accessToken = token;
  currentAdmin = null;
  adminAccessToken = null;
  patientId = user.patient_id;
  localStorage.setItem("currentUser", JSON.stringify(user));
  localStorage.setItem("accessToken", token);
  localStorage.removeItem("currentAdmin");
  localStorage.removeItem("adminAccessToken");
  localStorage.setItem("activePage", "assistant");
  document.body.classList.add("authenticated");
  document.body.classList.remove("admin-authenticated");
  showWorkspacePage("assistant");
  setPatientSummary(user);
  resetChat();
  refreshActiveAppointments();
  setSidebarOpen(sidebarOpen);
}

function setAdminAuthenticated(admin, token) {
  currentAdmin = admin;
  adminAccessToken = token;
  currentUser = null;
  accessToken = null;
  patientId = null;
  localStorage.setItem("currentAdmin", JSON.stringify(admin));
  localStorage.setItem("adminAccessToken", token);
  localStorage.removeItem("currentUser");
  localStorage.removeItem("accessToken");
  localStorage.setItem("activePage", "admin");
  document.body.classList.add("admin-authenticated");
  document.body.classList.remove("authenticated");
  showWorkspacePage("admin");
  showAuthMode("admin");
  showAdminView(preferredAdminView());
  renderAdminAppointments();
  loadAdminAppointments();
  if (preferredAdminView() !== "overview") {
    loadAdminManagement();
  }
}

function clearAuthenticated() {
  hideChatClosed();
  hideProfilePanel();
  if (documentUpload) documentUpload.value = "";
  clearAttachPill();
  setUploadStatus("", "default");
  renderDocumentsPanel([]);
  currentUser = null;
  currentAdmin = null;
  accessToken = null;
  adminAccessToken = null;
  patientId = null;
  state = null;
  adminAppointments = [];
  adminAppointmentsLoaded = false;
  adminManagementLoaded = false;
  adminDoctors = [];
  adminSlots = [];
  adminHolidays = [];
  adminDepartments = [];
  adminDoctorEditingId = "";
  localStorage.removeItem("currentUser");
  localStorage.removeItem("accessToken");
  localStorage.removeItem("currentAdmin");
  localStorage.removeItem("adminAccessToken");
  document.body.classList.remove("authenticated");
  document.body.classList.remove("admin-authenticated");
  showWorkspacePage("assistant");
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
      // DB is authoritative — replace, don't merge, so stale bookings from a
      // previous user's session cannot survive a login with a different account.
      state = normalizeChatState({
        active_appointments: bookings,
        upcoming_bookings: bookings,
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

function adminAuthHeaders() {
  return {
    Authorization: `Bearer ${adminAccessToken}`,
  };
}

async function authedJson(url, options = {}) {
  const timeoutMs = options.timeoutMs ?? 15000;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
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
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function adminAuthedJson(url, options = {}) {
  const timeoutMs = options.timeoutMs ?? 15000;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        ...adminAuthHeaders(),
        ...(options.headers || {}),
      },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) {
        clearAuthenticated();
      }
      throw new Error(data.detail || `Request failed with ${response.status}`);
    }
    return data;
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Admin request timed out. Please retry.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
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
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function formatBookingDateTime(value) {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
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

function formatClinicalSummary(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch (error) {
    return String(value);
  }
}

function adminAppointmentState(appointment) {
  const status = String(appointment?.status || "").toLowerCase();
  if (status === "cancelled" || status === "completed") {
    return "past";
  }

  const timeValue = appointment?.appointment_time || appointment?.time || appointment?.start_time;
  const parsed = timeValue ? new Date(timeValue) : null;
  if (parsed && !Number.isNaN(parsed.getTime()) && parsed <= new Date()) {
    return "past";
  }

  return "upcoming";
}

function adminStatusLabel(appointment) {
  const state = appointment?.appointment_state || adminAppointmentState(appointment);
  const rawStatus = String(appointment?.status || "").toLowerCase();
  if (rawStatus === "cancelled" || rawStatus === "completed") {
    return rawStatus;
  }
  return state;
}

function renderAdminDoctorOptions(doctorSource = adminDoctors) {
  if (!adminDoctorFilter) return;

  const currentValue = adminDoctorFilter.value || "";
  const doctors = new Map();
  (doctorSource || []).forEach((doctor) => {
    if (!doctor || !doctor.doctor_id) return;
    doctors.set(doctor.doctor_id, doctor.name || doctor.doctor_name || "Doctor");
  });

  const options = Array.from(doctors.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  adminDoctorFilter.replaceChildren();

  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = "All doctors";
  adminDoctorFilter.appendChild(allOption);

  options.forEach(([doctorId, doctorName]) => {
    const option = document.createElement("option");
    option.value = doctorId;
    option.textContent = doctorName;
    adminDoctorFilter.appendChild(option);
  });

  adminDoctorFilter.value = options.some(([doctorId]) => doctorId === currentValue) ? currentValue : "";
}

function updateAdminStats(scopeAppointments) {
  const appointments = Array.isArray(scopeAppointments) ? scopeAppointments : [];
  const upcoming = appointments.filter((appointment) => adminAppointmentState(appointment) === "upcoming");
  const past = appointments.filter((appointment) => adminAppointmentState(appointment) === "past");
  const doctors = new Set(appointments.map((appointment) => appointment.doctor_id).filter(Boolean));
  const patients = new Set(appointments.map((appointment) => appointment.patient_id || appointment.patient_name).filter(Boolean));

  if (adminStatTotal) adminStatTotal.textContent = String(appointments.length);
  if (adminStatUpcoming) adminStatUpcoming.textContent = String(upcoming.length);
  if (adminStatPast) adminStatPast.textContent = String(past.length);
  if (adminStatDoctors) adminStatDoctors.textContent = String(doctors.size);
  if (adminStatPatients) adminStatPatients.textContent = String(patients.size);
}

function resetAdminAppointmentPaging() {
  adminAppointmentsPage = 1;
}

function renderAdminAppointmentCard(appointment) {
  const item = document.createElement("article");
  item.className = "booking-item admin-appointment-card";

  const head = document.createElement("div");
  head.className = "admin-appointment-head";

  const titleWrap = document.createElement("div");
  titleWrap.className = "admin-appointment-title";

  const patientName = document.createElement("strong");
  patientName.textContent = appointment.patient_name || "Patient";

  const summary = document.createElement("span");
  summary.className = "admin-appointment-summary";
  summary.textContent = formatClinicalSummary(appointment.clinical_summary) || "No clinical summary submitted.";

  titleWrap.append(patientName, summary);

  const badge = document.createElement("span");
  const statusValue = adminStatusLabel(appointment);
  badge.className = `admin-status-pill ${statusValue ? `is-${statusValue}` : ""}`;
  badge.textContent = statusValue || "booked";

  head.append(titleWrap, badge);
  item.appendChild(head);

  const meta = document.createElement("div");
  meta.className = "admin-appointment-meta";

  const time = document.createElement("span");
  time.textContent = formatDateTime(appointment.time || appointment.appointment_time);

  const divider = document.createElement("span");
  divider.className = "admin-appointment-separator";
  divider.textContent = "\u2022";

  const doctor = document.createElement("span");
  doctor.textContent = appointment.doctor_name || "Doctor";

  meta.append(time, divider, doctor);
  item.appendChild(meta);
  item.appendChild(
    buildClinicalNotesBlock(
      formatClinicalSummary(appointment.clinical_summary),
      true,
      "Pre-Appointment Clinical Summary"
    )
  );

  return item;
}

function renderAdminAppointments() {
  if (!adminAppointmentsList) return;

  const selectedDoctorId = adminDoctorFilter?.value || "";
  const visibleAppointments = (adminAppointments || [])
    .filter((appointment) => !selectedDoctorId || appointment.doctor_id === selectedDoctorId)
    .sort((left, right) => new Date(left.time || left.appointment_time || 0) - new Date(right.time || right.appointment_time || 0));

  updateAdminStats(visibleAppointments);

  const filtered = adminSelectedStatus === "all"
    ? visibleAppointments
    : visibleAppointments.filter((appointment) => adminAppointmentState(appointment) === adminSelectedStatus);
  const totalPages = Math.max(1, Math.ceil(filtered.length / adminAppointmentsPageSize));
  adminAppointmentsPage = Math.min(Math.max(1, adminAppointmentsPage), totalPages);
  const startIndex = (adminAppointmentsPage - 1) * adminAppointmentsPageSize;
  const pageItems = filtered.slice(startIndex, startIndex + adminAppointmentsPageSize);

  if (adminResultCount) {
    const statusLabel = adminSelectedStatus === "all" ? "all" : adminSelectedStatus;
    adminResultCount.textContent = `${filtered.length} ${filtered.length === 1 ? "appointment" : "appointments"} \u00b7 ${statusLabel}`;
  }

  if (adminFilterHint) {
    const doctorName = selectedDoctorId
      ? (adminDoctorFilter?.selectedOptions?.[0]?.textContent || "selected doctor")
      : "all doctors";
    adminFilterHint.textContent = `Showing ${filtered.length} appointment${filtered.length === 1 ? "" : "s"} for ${doctorName}.`;
  }

  if (adminPageIndicator) {
    const firstItem = filtered.length ? startIndex + 1 : 0;
    const lastItem = Math.min(startIndex + adminAppointmentsPageSize, filtered.length);
    adminPageIndicator.textContent = filtered.length
      ? `Page ${adminAppointmentsPage} of ${totalPages} \u00b7 ${firstItem}-${lastItem} of ${filtered.length}`
      : "Page 1 of 1";
  }

  if (adminPrevPageBtn) {
    adminPrevPageBtn.disabled = adminAppointmentsPage <= 1;
  }
  if (adminNextPageBtn) {
    adminNextPageBtn.disabled = adminAppointmentsPage >= totalPages;
  }

  adminAppointmentsList.replaceChildren();

  if (!filtered.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No appointments match the current filter.";
    adminAppointmentsList.appendChild(note);
    return;
  }

  pageItems.forEach((appointment) => {
    adminAppointmentsList.appendChild(renderAdminAppointmentCard(appointment));
  });
}

async function loadAdminAppointments(force = false) {
  if (!currentAdmin || !adminAccessToken) {
    return [];
  }

  if (adminAppointmentsLoading) {
    return adminAppointmentsLoadPromise || adminAppointments;
  }

  if (adminAppointmentsLoaded && !force) {
    renderAdminDoctorOptions(adminDoctors);
    renderAdminAppointments();
    return adminAppointments;
  }

  adminAppointmentsLoading = true;
  if (adminAppointmentsList) {
    adminAppointmentsList.replaceChildren();
    const loading = document.createElement("p");
    loading.className = "panel-note";
    loading.textContent = "Loading appointment data...";
    adminAppointmentsList.appendChild(loading);
  }

  adminAppointmentsLoadPromise = (async () => {
    try {
      const data = await adminAuthedJson("/admin/appointments");
      adminAppointments = Array.isArray(data) ? data : (data?.appointments || []);
      adminAppointmentsLoaded = true;
      renderAdminDoctorOptions(adminDoctors);
      renderAdminAppointments();
      return adminAppointments;
    } catch (error) {
      adminAppointments = [];
      adminAppointmentsLoaded = false;
      if (adminAppointmentsList) {
        adminAppointmentsList.replaceChildren();
        const note = document.createElement("p");
        note.className = "panel-note";
        note.textContent = error.message;
        adminAppointmentsList.appendChild(note);
      }
      return [];
    } finally {
      adminAppointmentsLoading = false;
      adminAppointmentsLoadPromise = null;
    }
  })();

  return adminAppointmentsLoadPromise;
}

function syncAdmin() {
  loadAdminAppointments();
  if (preferredAdminView() !== "overview") {
    loadAdminManagement();
  }
  showAdminView(preferredAdminView());
}

function toDatetimeLocalValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function toDateInputValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 10);
}

const ADMIN_TIME_DEFAULTS = {
  workStart: "09:00",
  lunchStart: "13:00",
  lunchEnd: "13:30",
  workEnd: "17:00",
};

function formatAdminTimeLabel(value) {
  const [hoursRaw, minutesRaw] = String(value).split(":");
  const hours = Number(hoursRaw);
  const minutes = Number(minutesRaw);
  if (!Number.isInteger(hours) || !Number.isInteger(minutes)) return value;
  const period = hours >= 12 ? "PM" : "AM";
  const displayHours = hours % 12 || 12;
  return `${String(displayHours).padStart(2, "0")}:${String(minutes).padStart(2, "0")} ${period}`;
}

function populateAdminTimeSelect(select, { defaultValue = "", allowEmpty = false } = {}) {
  if (!select) return;
  const currentValue = select.value || defaultValue;
  select.replaceChildren();

  if (allowEmpty) {
    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = "No lunch break";
    select.appendChild(emptyOption);
  }

  for (let hour = 0; hour < 24; hour += 1) {
    for (let minute = 0; minute < 60; minute += 15) {
      const value = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
      const option = document.createElement("option");
      option.value = value;
      option.textContent = formatAdminTimeLabel(value);
      select.appendChild(option);
    }
  }

  select.value = currentValue || defaultValue;
}

function initAdminTimeSelects() {
  populateAdminTimeSelect(adminSlotWorkStart, { defaultValue: ADMIN_TIME_DEFAULTS.workStart });
  populateAdminTimeSelect(adminSlotLunchStart, { defaultValue: ADMIN_TIME_DEFAULTS.lunchStart, allowEmpty: true });
  populateAdminTimeSelect(adminSlotLunchEnd, { defaultValue: ADMIN_TIME_DEFAULTS.lunchEnd, allowEmpty: true });
  populateAdminTimeSelect(adminSlotWorkEnd, { defaultValue: ADMIN_TIME_DEFAULTS.workEnd });
}

function clearAdminDoctorForm() {
  adminDoctorEditingId = "";
  if (adminDoctorSelect) adminDoctorSelect.value = "";
  if (adminDoctorName) adminDoctorName.value = "";
  if (adminDoctorDepartment) adminDoctorDepartment.value = "";
  if (adminDoctorExperience) adminDoctorExperience.value = "0";
  if (adminDoctorActive) adminDoctorActive.checked = true;
  setAdminDoctorMessage("");
}

function fillAdminDoctorForm(doctor) {
  if (!doctor) {
    clearAdminDoctorForm();
    return;
  }
  adminDoctorEditingId = doctor.doctor_id || "";
  if (adminDoctorSelect) adminDoctorSelect.value = doctor.doctor_id || "";
  if (adminDoctorName) adminDoctorName.value = doctor.name || "";
  if (adminDoctorDepartment) adminDoctorDepartment.value = doctor.department || "";
  if (adminDoctorExperience) adminDoctorExperience.value = String(doctor.experience_years ?? 0);
  if (adminDoctorActive) adminDoctorActive.checked = Boolean(doctor.is_active);
  setAdminDoctorMessage("");
}

function renderAdminSelectOptions() {
  const doctors = Array.isArray(adminDoctors) ? adminDoctors : [];
  const optionSets = [adminDoctorSelect, adminSlotDoctorSelect, adminHolidayDoctorSelect].filter(Boolean);
  optionSets.forEach((select) => {
    const currentValue = select.value || "";
    select.replaceChildren();

    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = select === adminDoctorSelect ? "Create new doctor" : "Select doctor";
    select.appendChild(blank);

    doctors.forEach((doctor) => {
      const option = document.createElement("option");
      option.value = doctor.doctor_id;
      option.textContent = `${doctor.name || "Doctor"} · ${doctor.department || "Department"}`;
      select.appendChild(option);
    });

    if (currentValue && doctors.some((doctor) => doctor.doctor_id === currentValue)) {
      select.value = currentValue;
    } else {
      select.value = "";
    }
  });
}

function renderAdminDoctorsPanel() {
  if (!adminDoctorsList) return;
  adminDoctorsList.replaceChildren();

  if (!Array.isArray(adminDoctors) || !adminDoctors.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No doctors found.";
    adminDoctorsList.appendChild(note);
    return;
  }

  adminDoctors.forEach((doctor) => {
    const card = document.createElement("article");
    card.className = "admin-inline-card";

    const head = document.createElement("div");
    head.className = "admin-inline-card-head";

    const titleWrap = document.createElement("div");
    const title = document.createElement("div");
    title.className = "admin-inline-title";
    title.textContent = doctor.name || "Doctor";
    const meta = document.createElement("div");
    meta.className = "admin-inline-meta";
    meta.textContent = `${doctor.department || "Department"} · ${doctor.experience_years || 0} years`;
    titleWrap.append(title, meta);

    const badge = document.createElement("span");
    badge.className = `admin-status-pill ${doctor.is_active ? "is-upcoming" : "is-cancelled"}`;
    badge.textContent = doctor.is_active ? "active" : "inactive";

    head.append(titleWrap, badge);
    card.appendChild(head);

    const counts = document.createElement("div");
    counts.className = "admin-inline-meta";
    counts.textContent = `${doctor.available_slots || 0} available of ${doctor.total_slots || 0} slots`;
    card.appendChild(counts);

    if (doctor.next_available_time) {
      const next = document.createElement("div");
      next.className = "admin-inline-meta";
      next.textContent = `Next availability: ${formatDateTime(doctor.next_available_time)}`;
      card.appendChild(next);
    }

    const actions = document.createElement("div");
    actions.className = "admin-inline-actions";

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "secondary compact";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => {
      showAdminView("manage");
      fillAdminDoctorForm(doctor);
      adminDoctorName?.focus();
    });

    const toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "secondary compact";
    toggleBtn.textContent = doctor.is_active ? "Deactivate" : "Activate";
    toggleBtn.addEventListener("click", async () => {
      setAdminDoctorMessage("");
      try {
        await adminAuthedJson(`/admin/doctors/${doctor.doctor_id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: doctor.name,
            department: doctor.department,
            experience_years: doctor.experience_years,
            is_active: !doctor.is_active,
          }),
        });
        await loadAdminManagement(true);
      } catch (error) {
        setAdminDoctorMessage(error.message);
      }
    });

    actions.append(editBtn, toggleBtn);
    card.appendChild(actions);
    adminDoctorsList.appendChild(card);
  });
}

function renderAdminSlotsPanel() {
  if (!adminSlotsList) return;
  adminSlotsList.replaceChildren();

  if (!Array.isArray(adminSlots) || !adminSlots.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No slots found.";
    adminSlotsList.appendChild(note);
    return;
  }

  adminSlots.forEach((slot) => {
    const card = document.createElement("article");
    card.className = "admin-inline-card";

    const head = document.createElement("div");
    head.className = "admin-inline-card-head";

    const titleWrap = document.createElement("div");
    const title = document.createElement("div");
    title.className = "admin-inline-title";
    title.textContent = slot.doctor_name || "Doctor";
    const meta = document.createElement("div");
    meta.className = "admin-inline-meta";
    meta.textContent = `${formatDateTime(slot.start_time)} to ${formatDateTime(slot.end_time)}`;
    titleWrap.append(title, meta);

    const badge = document.createElement("span");
    badge.className = `admin-status-pill ${slot.is_active ? "is-upcoming" : "is-cancelled"}`;
    badge.textContent = slot.is_active ? (slot.is_booked ? "booked" : "active") : "inactive";

    head.append(titleWrap, badge);
    card.appendChild(head);

    const details = document.createElement("div");
    details.className = "admin-inline-meta";
    details.textContent = `${slot.department || "Department"} · ${slot.booked_by_patient_id ? "Booked" : "Open"}`;
    card.appendChild(details);

    const actions = document.createElement("div");
    actions.className = "admin-inline-actions";

    const toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "secondary compact";
    toggleBtn.textContent = slot.is_active ? "Deactivate" : "Activate";
    toggleBtn.addEventListener("click", async () => {
      setAdminSlotMessage("");
      try {
        await adminAuthedJson(`/admin/slots/${slot.slot_id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_active: !slot.is_active }),
        });
        await loadAdminManagement(true);
      } catch (error) {
        setAdminSlotMessage(error.message);
      }
    });

    actions.append(toggleBtn);
    card.appendChild(actions);
    adminSlotsList.appendChild(card);
  });
}

function renderAdminHolidaysPanel() {
  if (!adminHolidaysList) return;
  adminHolidaysList.replaceChildren();

  if (!Array.isArray(adminHolidays) || !adminHolidays.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No holidays found.";
    adminHolidaysList.appendChild(note);
    return;
  }

  adminHolidays.forEach((holiday) => {
    const card = document.createElement("article");
    card.className = "admin-inline-card";

    const head = document.createElement("div");
    head.className = "admin-inline-card-head";

    const titleWrap = document.createElement("div");
    const title = document.createElement("div");
    title.className = "admin-inline-title";
    title.textContent = holiday.scope === "doctor"
      ? `${holiday.doctor_name || "Doctor"} holiday`
      : "Universal holiday";
    const meta = document.createElement("div");
    meta.className = "admin-inline-meta";
    meta.textContent = `${holiday.start_date || "-"} to ${holiday.end_date || "-"}`;
    titleWrap.append(title, meta);

    const badge = document.createElement("span");
    badge.className = `admin-status-pill ${holiday.is_active ? "is-upcoming" : "is-cancelled"}`;
    badge.textContent = holiday.is_active ? holiday.scope : "inactive";

    head.append(titleWrap, badge);
    card.appendChild(head);

    if (holiday.reason) {
      const details = document.createElement("div");
      details.className = "admin-inline-meta";
      details.textContent = holiday.reason;
      card.appendChild(details);
    }

    const actions = document.createElement("div");
    actions.className = "admin-inline-actions";

    const toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "secondary compact";
    toggleBtn.textContent = holiday.is_active ? "Deactivate" : "Activate";
    toggleBtn.addEventListener("click", async () => {
      setAdminHolidayMessage("");
      try {
        await adminAuthedJson(`/admin/holidays/${holiday.holiday_id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_active: !holiday.is_active }),
        });
        await loadAdminManagement(true);
      } catch (error) {
        setAdminHolidayMessage(error.message);
      }
    });

    actions.append(toggleBtn);
    card.appendChild(actions);
    adminHolidaysList.appendChild(card);
  });
}

function renderAdminDepartments() {
  if (!adminDepartmentsList) return;
  adminDepartmentsList.replaceChildren();

  if (!Array.isArray(adminDepartments) || !adminDepartments.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No departments have been added yet.";
    adminDepartmentsList.appendChild(note);
    return;
  }

  adminDepartments.forEach((department) => {
    const chip = document.createElement("span");
    chip.className = "admin-dept-chip";
    chip.textContent = `${department.department} (${department.doctor_count || 0})`;
    adminDepartmentsList.appendChild(chip);
  });
}

async function loadAdminManagement(force = false) {
  if (!currentAdmin || !adminAccessToken) {
    return;
  }

  if (adminManagementLoaded && !force) {
    renderAdminSelectOptions();
    renderAdminDoctorsPanel();
    renderAdminSlotsPanel();
    renderAdminHolidaysPanel();
    renderAdminDepartments();
    return;
  }

  try {
    const [doctorResp, slotResp, holidayResp, departmentResp] = await Promise.all([
      adminAuthedJson("/admin/doctors"),
      adminAuthedJson("/admin/slots"),
      adminAuthedJson("/admin/holidays"),
      adminAuthedJson("/admin/departments"),
    ]);

    adminDoctors = Array.isArray(doctorResp?.doctors) ? doctorResp.doctors : [];
    adminSlots = Array.isArray(slotResp?.slots) ? slotResp.slots : [];
    adminHolidays = Array.isArray(holidayResp?.holidays) ? holidayResp.holidays : [];
    adminDepartments = Array.isArray(departmentResp?.departments) ? departmentResp.departments : [];
    adminManagementLoaded = true;

    renderAdminSelectOptions();
    if (adminHolidayDoctorSelect && adminHolidayScope) {
      adminHolidayDoctorSelect.disabled = adminHolidayScope.value !== "doctor";
    }
    renderAdminDoctorsPanel();
    renderAdminSlotsPanel();
    renderAdminHolidaysPanel();
    renderAdminDepartments();
    renderAdminDoctorOptions(adminDoctors);
  } catch (error) {
    adminManagementLoaded = false;
    setAdminDoctorMessage(error.message);
  }
}

async function saveAdminDoctor(event) {
  event.preventDefault();
  setAdminDoctorMessage("");
  const editingDoctorId = adminDoctorEditingId;
  const isEditing = Boolean(editingDoctorId);

  const payload = {
    name: adminDoctorName?.value.trim() || "",
    department: adminDoctorDepartment?.value.trim() || "",
    experience_years: Number(adminDoctorExperience?.value || 0),
    is_active: Boolean(adminDoctorActive?.checked),
  };

  try {
    if (editingDoctorId) {
      await adminAuthedJson(`/admin/doctors/${editingDoctorId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      await adminAuthedJson("/admin/doctors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    showAdminToast(isEditing ? "Doctor updated successfully." : "Doctor created successfully.");
    clearAdminDoctorForm();
    await loadAdminManagement(true);
    await loadAdminAppointments(true);
  } catch (error) {
    setAdminDoctorMessage(error.message);
    showAdminToast(error.message, "error", 2500);
  }
}

async function saveAdminSlot(event) {
  event.preventDefault();
  setAdminSlotMessage("");

  const doctorId = adminSlotDoctorSelect?.value || "";
  if (!doctorId) {
    setAdminSlotMessage("Please choose a doctor.");
    return;
  }

  const workStartTime = adminSlotWorkStart?.value || "";
  const lunchStartTime = adminSlotLunchStart?.value || "";
  const lunchEndTime = adminSlotLunchEnd?.value || "";
  const workEndTime = adminSlotWorkEnd?.value || "";

  if (!workStartTime || !workEndTime) {
    setAdminSlotMessage("Please choose working hours.");
    return;
  }

  try {
    await adminAuthedJson("/admin/slots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        doctor_id: doctorId,
        start_date: adminSlotStartDate?.value || null,
        end_date: adminSlotEndDate?.value || null,
        work_start_time: workStartTime,
        lunch_start_time: lunchStartTime,
        lunch_end_time: lunchEndTime,
        work_end_time: workEndTime,
        slot_duration_minutes: adminSlotDuration?.value ? Number(adminSlotDuration.value) : null,
        is_active: Boolean(adminSlotActive?.checked),
      }),
    });

    showAdminToast("Slots generated successfully.");
    if (adminSlotStartDate) adminSlotStartDate.value = "";
    if (adminSlotEndDate) adminSlotEndDate.value = "";
    if (adminSlotWorkStart) adminSlotWorkStart.value = ADMIN_TIME_DEFAULTS.workStart;
    if (adminSlotLunchStart) adminSlotLunchStart.value = ADMIN_TIME_DEFAULTS.lunchStart;
    if (adminSlotLunchEnd) adminSlotLunchEnd.value = ADMIN_TIME_DEFAULTS.lunchEnd;
    if (adminSlotWorkEnd) adminSlotWorkEnd.value = ADMIN_TIME_DEFAULTS.workEnd;
    if (adminSlotDuration) adminSlotDuration.value = "30";
    await loadAdminManagement(true);
  } catch (error) {
    setAdminSlotMessage(error.message);
    showAdminToast(error.message, "error", 2500);
  }
}

async function saveAdminHoliday(event) {
  event.preventDefault();
  setAdminHolidayMessage("");

  const scope = adminHolidayScope?.value || "universal";
  const doctorId = adminHolidayDoctorSelect?.value || "";
  if (scope === "doctor" && !doctorId) {
    setAdminHolidayMessage("Choose a doctor for a doctor-specific holiday.");
    return;
  }

  try {
    await adminAuthedJson("/admin/holidays", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope,
        doctor_id: scope === "doctor" ? doctorId : null,
        start_date: adminHolidayStart?.value || null,
        end_date: adminHolidayEnd?.value || null,
        reason: adminHolidayReason?.value.trim() || null,
        is_active: Boolean(adminHolidayActive?.checked),
      }),
    });

    showAdminToast("Holiday saved successfully.");
    if (adminHolidayStart) adminHolidayStart.value = "";
    if (adminHolidayEnd) adminHolidayEnd.value = "";
    if (adminHolidayReason) adminHolidayReason.value = "";
    await loadAdminManagement(true);
  } catch (error) {
    setAdminHolidayMessage(error.message);
    showAdminToast(error.message, "error", 2500);
  }
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

function buildClinicalNotesBlock(note, compact = false, label = "Clinical Notes") {
  if (!note) {
    return document.createDocumentFragment();
  }

  const notePanel = document.createElement("details");
  notePanel.className = compact ? "clinical-notes-block compact" : "clinical-notes-block";
  notePanel.open = !compact;

  const noteSummary = document.createElement("summary");
  noteSummary.textContent = label;

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
  renderDocumentsPanel(state?.analyzed_documents || []);
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
      const time = formatDateTime(slot.start_time);
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
      const time = formatDateTime(slot.start_time);
      addQuickAction(`${index + 1}. ${time}`, String(index + 1));
    });
  }
}

async function refreshAdminPanel() {
  if (!currentAdmin || !adminAccessToken) {
    return;
  }

  if (adminRefreshResetTimer) {
    window.clearTimeout(adminRefreshResetTimer);
    adminRefreshResetTimer = null;
  }

  if (adminRefreshBtn) {
    adminRefreshBtn.disabled = true;
    adminRefreshBtn.setAttribute("aria-busy", "true");
  }
  if (adminRefreshLabel) {
    adminRefreshLabel.textContent = "Refreshing...";
  }

  try {
    const activeView = preferredAdminView();
    if (activeView === "overview" || activeView === "appointments") {
      await Promise.all([
        loadAdminAppointments(true),
        activeView === "overview" ? loadAdminManagement(true) : Promise.resolve(),
      ]);
      return;
    }

    await loadAdminManagement(true);
    if (activeView === "appointments") {
      await loadAdminAppointments(true);
    }
  } finally {
    if (adminRefreshLabel) {
      adminRefreshLabel.textContent = "Updated";
    }
    if (adminRefreshBtn) {
      adminRefreshBtn.disabled = false;
      adminRefreshBtn.removeAttribute("aria-busy");
    }

    adminRefreshResetTimer = window.setTimeout(() => {
      if (adminRefreshLabel) {
        adminRefreshLabel.textContent = "Refresh";
      }
      adminRefreshResetTimer = null;
    }, 1200);
  }
}

function autoResizeComposer() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
}

function buildDeepgramWsUrl(sampleRate = 16000) {
  const token = accessToken || "";
  return `${location.origin.replace(/^http/, "ws")}/chat/deepgram?token=${encodeURIComponent(token)}&sample_rate=${encodeURIComponent(sampleRate)}`;
}

function setVoiceState(listening, label) {
  voiceListening = listening;
  if (voiceBtn) {
    voiceBtn.classList.toggle("is-active", listening);
    voiceBtn.title = label || (listening ? "Stop recording" : "Speak a message");
  }
  if (statusEl && listening) {
    statusEl.textContent = label || "Listening";
  }
  if (voiceStatusPreview) {
    voiceStatusPreview.classList.toggle("is-active", listening);
  }
  if (voiceStatusText) {
    voiceStatusText.textContent = label || (listening ? "Listening..." : "");
  } else if (voiceStatusPreview) {
    voiceStatusPreview.textContent = label || (listening ? "Listening..." : "");
    voiceStatusPreview.classList.toggle("hidden", !listening && !voiceStatusPreview.textContent);
  }
  console.debug("[voice]", label || (listening ? "listening" : "stopped"));
}

async function stopVoiceCapture() {
  if (voiceStopping) return;
  voiceStopping = true;
  if (voiceCommitTimer) {
    window.clearTimeout(voiceCommitTimer);
    voiceCommitTimer = null;
  }
  if (voiceRecorder && voiceRecorder.state !== "inactive") {
    try {
      if (typeof voiceRecorder.stop === "function") {
        voiceRecorder.stop();
      } else if (typeof voiceRecorder.disconnect === "function") {
        voiceRecorder.disconnect();
      }
    } catch (error) {}
  }

  if (voiceSocket && voiceSocket.readyState === WebSocket.OPEN) {
    try {
      voiceSocket.send(new Uint8Array());
    } catch (error) {}
    try {
      voiceSocket.close();
    } catch (error) {}
  }

  if (voiceStream) {
    voiceStream.getTracks().forEach((track) => track.stop());
    voiceStream = null;
  }

  if (voiceWorkletNode) {
    try {
      voiceWorkletNode.port.onmessage = null;
      voiceWorkletNode.disconnect();
    } catch (error) {}
    voiceWorkletNode = null;
  }

  if (voiceAudioContext) {
    try {
      await voiceAudioContext.close();
    } catch (error) {}
    voiceAudioContext = null;
  }

  voiceRecorder = null;
  voiceSocket = null;
  voicePendingFrames = [];
  setVoiceState(false, "Speak a message");
  voiceStopping = false;

  const transcriptToKeep = (voiceFinalTranscript || voiceLiveTranscript || input?.value || "").trim();
  if (transcriptToKeep && input) {
    input.value = transcriptToKeep;
    autoResizeComposer();
  }
  if (voiceTranscriptPreview) {
    voiceTranscriptPreview.textContent = transcriptToKeep;
    voiceTranscriptPreview.classList.toggle("hidden", !transcriptToKeep);
  }
  if (voiceStatusPreview) {
    voiceStatusPreview.textContent = transcriptToKeep
      ? "Transcript ready. Use Send to submit."
      : "Recording stopped.";
    voiceStatusPreview.classList.remove("hidden");
  }
}

function appendPcm16Frame(buffer) {
  const inputData = buffer?.length ? buffer : buffer?.inputBuffer?.getChannelData?.(0);
  if (!inputData || typeof inputData.length !== "number") {
    console.warn("[voice] no audio input data on frame", buffer);
    return;
  }
  const pcm = new Int16Array(inputData.length);
  for (let index = 0; index < inputData.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, inputData[index]));
    pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  if (!voiceSocket || voiceSocket.readyState !== WebSocket.OPEN) {
    voicePendingFrames.push(pcm.buffer.slice(0));
    voicePendingFrames = voicePendingFrames.slice(-12);
    if (voiceStatusPreview) {
      voiceStatusPreview.textContent = `Buffering audio... ${voicePendingFrames.length} frame(s) queued`;
      voiceStatusPreview.classList.remove("hidden");
    }
    return;
  }
  if (voiceStatusPreview) {
    voiceStatusPreview.textContent = "Streaming audio frames to Deepgram...";
    voiceStatusPreview.classList.remove("hidden");
  }
  console.debug("[voice] frame sent", pcm.length);
  voiceSocket.send(pcm.buffer);
}

async function startVoiceCapture() {
  if (!navigator.mediaDevices?.getUserMedia) {
    setStatus("Microphone unavailable");
    return;
  }
  if (!accessToken) {
    setStatus("Login required");
    return;
  }
  if (voiceListening) {
    await stopVoiceCapture();
    return;
  }

  try {
    voiceFinalTranscript = "";
    voiceLiveTranscript = "";
    if (voiceTranscriptPreview) {
      voiceTranscriptPreview.textContent = "";
      voiceTranscriptPreview.classList.add("hidden");
    }
    if (voiceStatusPreview) {
      voiceStatusPreview.classList.remove("hidden");
      voiceStatusPreview.classList.add("is-active");
    }
    if (voiceStatusText) {
      voiceStatusText.textContent = "Starting a fresh recording...";
    } else if (voiceStatusPreview) {
      voiceStatusPreview.textContent = "Starting a fresh recording...";
    }

    voiceStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    voiceAudioContext = new (window.AudioContext || window.webkitAudioContext)();
    if (voiceAudioContext.state === "suspended") {
      await voiceAudioContext.resume();
    }
    const source = voiceAudioContext.createMediaStreamSource(voiceStream);
    const silentGain = voiceAudioContext.createGain();
    silentGain.gain.value = 0;

    const contextSampleRate = voiceAudioContext.sampleRate || 16000;
    voiceSocket = new WebSocket(buildDeepgramWsUrl(contextSampleRate));
    voiceSocket.binaryType = "arraybuffer";
    voicePendingFrames = [];
    setVoiceState(true, "Listening");
    setStatus("Listening");
    console.debug("[voice] audio context sample rate", contextSampleRate);

    await voiceAudioContext.audioWorklet.addModule("/static/voice-worklet.js");
    voiceWorkletNode = new AudioWorkletNode(voiceAudioContext, "voice-capture-processor");
    voiceWorkletNode.port.onmessage = (event) => {
      appendPcm16Frame(event.data);
    };

    voiceSocket.onmessage = (event) => {
      let payload = null;
      try {
        payload = JSON.parse(event.data);
      } catch (error) {
        return;
      }
      console.debug("[voice] deepgram message", payload?.type, payload);
      if (payload?.type !== "Results") return;
      const alt = payload?.channel?.alternatives?.[0];
      const transcript = (alt?.transcript || "").trim();
      if (!transcript) return;
      if (payload?.is_final) {
        voiceFinalTranscript = transcript;
        voiceLiveTranscript = transcript;
        if (input) {
          input.value = voiceFinalTranscript;
          autoResizeComposer();
        }
      } else {
        voiceLiveTranscript = transcript;
        if (input) {
          input.value = transcript;
          autoResizeComposer();
        }
      }
      if (voiceTranscriptPreview) {
        voiceTranscriptPreview.textContent = transcript;
        voiceTranscriptPreview.classList.remove("hidden");
      }
      if (voiceStatusPreview) {
        voiceStatusPreview.classList.remove("hidden");
        voiceStatusPreview.classList.add("is-active");
      }
      if (voiceStatusText) {
        voiceStatusText.textContent = payload?.is_final ? "Final transcript received" : "Transcribing...";
      } else if (voiceStatusPreview) {
        voiceStatusPreview.textContent = payload?.is_final ? "Final transcript received" : "Transcribing...";
      }
      if (statusEl && voiceListening) {
        statusEl.textContent = transcript;
      }
    };

    voiceSocket.onopen = () => {
      console.debug("[voice] deepgram socket open");
      if (voiceStatusPreview) {
        voiceStatusPreview.classList.remove("hidden");
        voiceStatusPreview.classList.add("is-active");
      }
      if (voiceStatusText) {
        voiceStatusText.textContent = "Deepgram connected. Speaking now...";
      } else if (voiceStatusPreview) {
        voiceStatusPreview.textContent = "Deepgram connected. Speaking now...";
      }
      while (voicePendingFrames.length && voiceSocket?.readyState === WebSocket.OPEN) {
        voiceSocket.send(voicePendingFrames.shift());
      }
    };

    voiceSocket.onerror = () => {
      console.error("[voice] deepgram socket error");
      setStatus("Voice error");
      if (input) {
        input.value = voiceLiveTranscript || voiceFinalTranscript || input.value || "";
        autoResizeComposer();
      }
      if (voiceTranscriptPreview) {
        voiceTranscriptPreview.textContent = voiceLiveTranscript || voiceFinalTranscript || "";
        voiceTranscriptPreview.classList.remove("hidden");
      }
      if (voiceStatusPreview) {
        voiceStatusPreview.classList.remove("hidden");
        voiceStatusPreview.classList.remove("is-active");
      }
      if (voiceStatusText) {
        voiceStatusText.textContent = "Voice error";
      } else if (voiceStatusPreview) {
        voiceStatusPreview.textContent = "Voice error";
      }
    };

    voiceSocket.onclose = () => {
      console.debug("[voice] deepgram socket closed");
      if (voiceListening && !voiceStopping) {
        if (input && (voiceLiveTranscript || voiceFinalTranscript)) {
          input.value = voiceFinalTranscript || voiceLiveTranscript;
          autoResizeComposer();
          if (voiceTranscriptPreview) {
            voiceTranscriptPreview.textContent = input.value;
            voiceTranscriptPreview.classList.remove("hidden");
          }
          if (voiceStatusPreview) {
            voiceStatusPreview.classList.remove("hidden");
            voiceStatusPreview.classList.remove("is-active");
          }
          if (voiceStatusText) {
            voiceStatusText.textContent = "Socket closed. Transcript kept in the box.";
          } else if (voiceStatusPreview) {
            voiceStatusPreview.textContent = "Socket closed. Transcript kept in the box.";
          }
        } else {
          setStatus("No transcript received");
          if (voiceStatusPreview) {
            voiceStatusPreview.classList.remove("hidden");
            voiceStatusPreview.classList.remove("is-active");
          }
          if (voiceStatusText) {
            voiceStatusText.textContent = "No transcript received";
          } else if (voiceStatusPreview) {
            voiceStatusPreview.textContent = "No transcript received";
          }
        }
        void stopVoiceCapture();
      }
    };

    source.connect(voiceWorkletNode);
    voiceWorkletNode.connect(silentGain);
    silentGain.connect(voiceAudioContext.destination);
    voiceRecorder = voiceWorkletNode;
    if (voiceStatusPreview) {
      voiceStatusPreview.classList.remove("hidden");
      voiceStatusPreview.classList.add("is-active");
    }
    if (voiceStatusText) {
      voiceStatusText.textContent = `Audio context: ${voiceAudioContext.state}. Frames streaming...`;
    } else if (voiceStatusPreview) {
      voiceStatusPreview.textContent = `Audio context: ${voiceAudioContext.state}. Frames streaming...`;
    }
  } catch (error) {
    setStatus(error.message || "Could not access microphone");
    await stopVoiceCapture();
  }
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
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(url, {
      method: "POST",
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `Request failed with ${response.status}`);
    }
    return data;
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
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
  renderDocumentsPanel([]);
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

async function loadRecordsArchive(force = false) {
  if (!accessToken || !patientId) {
    recordsArchive = { documents: [], sessionsById: new Map(), loaded: false, loading: false };
    renderDocumentsPanel([]);
    return recordsArchive;
  }

  if (recordsArchive.loading) return recordsArchive;
  if (recordsArchive.loaded && !force) {
    renderDocumentsPanel(recordsArchive.documents);
    return recordsArchive;
  }

  recordsArchive.loading = true;
  try {
    const data = await authedJson("/chat/history");
    const docs = Array.isArray(data.documents) ? data.documents.map(normalizeDocumentEntry).filter(Boolean) : [];
    const sessions = Array.isArray(data.sessions) ? data.sessions : [];
    recordsArchive = {
      documents: docs,
      sessionsById: new Map(sessions.map((session) => [String(session.chat_session_id || ""), session])),
      loaded: true,
      loading: false,
    };
    renderDocumentsPanel(recordsArchive.documents);
    return recordsArchive;
  } catch (error) {
    renderDocumentsPanel([]);
    recordsArchive.loading = false;
    throw error;
  } finally {
    recordsArchive.loading = false;
  }
}

async function showChatHistory(preferredSessionId = "") {
  setProfilePanelLoading("Chat history by case");
  try {
    const data = await authedJson("/chat/history");
    const sessions = data.sessions || [];
    const documents = Array.isArray(data.documents) ? data.documents.map(normalizeDocumentEntry).filter(Boolean) : [];
    recordsArchive = {
      documents,
      sessionsById: new Map(sessions.map((session) => [String(session.chat_session_id || ""), session])),
      loaded: true,
      loading: false,
    };
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
    let renderedPreferredSession = false;

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

      renderChatSessionDocuments(session, transcript);
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

      if ((preferredSessionId && String(session.chat_session_id || "") === String(preferredSessionId)) || (!preferredSessionId && index === 0)) {
        renderSession(session, card);
        card.scrollIntoView({ block: "nearest" });
        renderedPreferredSession = true;
      }
    });

    if (!renderedPreferredSession && sessions[0]) {
      const firstCard = sidebar.querySelector(".history-session-card");
      renderSession(sessions[0], firstCard);
    }

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
  if (voiceListening) {
    await stopVoiceCapture(false);
  }
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
    const uploadPreview = showUploadMessage(
      pendingUploadFiles.map((file) => file.name).join(", "),
      "Uploading document..."
    );
    addUserMessageWithFile(message, pendingUploadFiles.map(f => f.name));
    uploadPreview.setStatus("Document attached and sent to the assistant.");
    uploadPreview.setFile(pendingUploadFiles.map((file) => file.name).join(", "));
  } else {
    addUserMessage(message);
  }

  await sendMessage(effectiveMessage);
});

if (voiceBtn) {
  voiceBtn.addEventListener("click", () => {
    if (voiceListening) {
      void stopVoiceCapture();
      return;
    }
    void startVoiceCapture();
  });
}

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

if (adminDoctorFilter) {
  adminDoctorFilter.addEventListener("change", () => {
    resetAdminAppointmentPaging();
    renderAdminAppointments();
  });
}

if (adminPrevPageBtn) {
  adminPrevPageBtn.addEventListener("click", () => {
    adminAppointmentsPage = Math.max(1, adminAppointmentsPage - 1);
    renderAdminAppointments();
  });
}

if (adminNextPageBtn) {
  adminNextPageBtn.addEventListener("click", () => {
    adminAppointmentsPage += 1;
    renderAdminAppointments();
  });
}

if (adminRefreshBtn) {
  adminRefreshBtn.addEventListener("click", () => {
    adminAppointmentsLoaded = false;
    void refreshAdminPanel();
  });
}

adminViewButtons.forEach((button) => {
  button.addEventListener("click", () => {
    showAdminView(button.dataset.adminView || "overview");
  });
});

if (adminDoctorSelect) {
  adminDoctorSelect.addEventListener("change", () => {
    const selected = adminDoctors.find((doctor) => doctor.doctor_id === adminDoctorSelect.value);
    fillAdminDoctorForm(selected || null);
  });
}

if (adminDoctorResetBtn) {
  adminDoctorResetBtn.addEventListener("click", clearAdminDoctorForm);
}

if (adminDoctorForm) {
  adminDoctorForm.addEventListener("submit", saveAdminDoctor);
}

if (adminSlotForm) {
  adminSlotForm.addEventListener("submit", saveAdminSlot);
}

if (adminHolidayForm) {
  adminHolidayForm.addEventListener("submit", saveAdminHoliday);
}

if (adminHolidayScope) {
  adminHolidayScope.addEventListener("change", () => {
    if (!adminHolidayDoctorSelect) return;
    const isDoctor = adminHolidayScope.value === "doctor";
    adminHolidayDoctorSelect.disabled = !isDoctor;
    if (!isDoctor) {
      adminHolidayDoctorSelect.value = "";
    }
  });
}

if (adminLogoutBtn) {
  adminLogoutBtn.addEventListener("click", () => {
    clearAuthenticated();
    showAuthMode("login");
  });
}

adminStatusButtons.forEach((button) => {
  button.addEventListener("click", () => {
    adminStatusButtons.forEach((item) => item.classList.toggle("is-active", item === button));
    adminSelectedStatus = button.dataset.adminStatus || "all";
    resetAdminAppointmentPaging();
    renderAdminAppointments();
  });
});

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
if (showAdminBtn) {
  showAdminBtn.addEventListener("click", () => showAuthMode("admin"));
}

if (authTabs) {
  authTabs.addEventListener("click", (event) => {
    const tab = event.target.closest(".tab");
    if (!tab || !authTabs.contains(tab)) {
      return;
    }

    if (tab === showLoginBtn) {
      showAuthMode("login");
      return;
    }
    if (tab === showSignupBtn) {
      showAuthMode("signup");
      return;
    }
    if (tab === showAdminBtn) {
      showAuthMode("admin");
    }
  });
}

if (adminBackBtn) {
  adminBackBtn.addEventListener("click", () => showAuthMode("login"));
}

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
    setPatientAuthenticated(data.user, data.access_token);
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
    setPatientAuthenticated(data.user, data.access_token);
  } catch (error) {
    setAuthMessage(error.message);
  }
});

if (adminLoginForm) {
  adminLoginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setAdminAuthMessage("");

    try {
      const data = await postJson("/auth/admin/login", {
        email: document.querySelector("#adminLoginEmail").value.trim(),
        password: document.querySelector("#adminLoginPassword").value,
      });
      setAdminAuthenticated({ email: data.email, name: data.name, role: data.role }, data.access_token);
    } catch (error) {
      setAdminAuthMessage(error.message);
    }
  });
}

logoutBtn.addEventListener("click", () => {
  clearAuthenticated();
  showAuthMode("login");
});

window.addEventListener("resize", adjustComposerHeight);

if (documentUpload) {
  documentUpload.addEventListener("change", async () => {
    const file = documentUpload.files?.[0] || null;
    if (!file) return;

    const uploadNotice = showUploadMessage(file.name, "Uploading document...");
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
        uploadNotice.setStatus("Document discarded.");
        clearAttachPill();
        documentUpload.value = "";
        setComposerDisabled(false);
        return;
      }

      // Step 4: Stage pill — wait for user to type a question or just click Send
      pendingUploadFiles.push(file);
      showAttachPill(file);
      uploadNotice.setStatus("Document ready to send in chat.");
      setUploadStatus("", "default");
      setComposerDisabled(false);
      input.focus();

    } catch (err) {
      setUploadStatus(`Upload error: ${err.message}`, "error");
      uploadNotice.setStatus(`Upload failed: ${err.message}`);
      documentUpload.value = "";
      setComposerDisabled(false);
    }
  });
}

async function bootstrapSession() {
  try {
    initAdminTimeSelects();
    if (currentUser && accessToken) {
      const data = await authedJson("/auth/me");
      setPatientAuthenticated(data.user, accessToken);
      return;
    }

    if (currentAdmin && adminAccessToken) {
      const data = await adminAuthedJson("/admin/me");
      setAdminAuthenticated(data.admin, adminAccessToken);
      return;
    }

    clearAuthenticated();
    showAuthMode("login");
  } catch (error) {
    clearAuthenticated();
    showAuthMode("login");
    setAuthMessage("Your session expired. Please sign in again.");
  }
}

bootstrapSession();
setSidebarOpen(sidebarOpen);

document.querySelectorAll("[data-nav]").forEach((button) => {
  if (button.dataset.nav === "records") {
    button.addEventListener("click", () => {
      void loadRecordsArchive();
    });
  }
});






