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
const chatSummary = document.querySelector("#chatSummary");
const recentHistory = document.querySelector("#recentHistory");
const activeAppointmentsPreview = document.querySelector("#activeAppointmentsPreview");
const tokenInput = document.querySelector("#tokenInput");
const tokenOutput = document.querySelector("#tokenOutput");
const tokenTotal = document.querySelector("#tokenTotal");
const tokenCalls = document.querySelector("#tokenCalls");
const quickActions = document.querySelector("#quickActions");
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

const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

function newChatSessionId() {
  if (crypto?.randomUUID) {
    return crypto.randomUUID();
  }
  return "session-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
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
  setSidebarOpen(sidebarOpen);
}

function clearAuthenticated() {
  hideChatClosed();
  hideProfilePanel();
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

function appendAssistantToken(messageNode, token) {
  if (!token) {
    return;
  }

  if (!messageNode.textStarted) {
    messageNode.body.replaceChildren();
    messageNode.textStarted = true;
  }

  messageNode.body.textContent += token;
  scrollMessages();
}

function finishStreamingMessage(messageNode) {
  messageNode.node.classList.remove("streaming");
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
      experience.textContent = `${doctor.experience_years || 0} years experience`;

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

  if (booking.booking_note) {
    const notePanel = document.createElement("details");
    notePanel.className = "clinical-notes-block";

    const noteSummary = document.createElement("summary");
    noteSummary.textContent = "Clinical Notes";

    const noteBody = document.createElement("div");
    noteBody.className = "clinical-notes-body";
    noteBody.textContent = booking.booking_note;

    notePanel.append(noteSummary, noteBody);
    summary.appendChild(notePanel);
  }

  return summary;
}

function renderTokenUsage(usage) {
  const summary = usage || {};
  tokenInput.textContent = formatNumber(summary.input_tokens);
  tokenOutput.textContent = formatNumber(summary.output_tokens);
  tokenTotal.textContent = formatNumber(summary.total_tokens);
  tokenCalls.textContent = formatNumber(summary.llm_calls);
}

function renderChatSummary(summary) {
  chatSummary.textContent = summary && String(summary).trim() ? summary : "Waiting for a little context.";
}

function renderRecentHistory(history) {
  recentHistory.replaceChildren();

  if (!Array.isArray(history) || !history.length) {
    const empty = document.createElement("p");
    empty.className = "panel-note";
    empty.textContent = "No recent turns yet.";
    recentHistory.appendChild(empty);
    return;
  }

  history.slice(-5).forEach((turn, index) => {
    const item = document.createElement("article");
    item.className = "history-turn";

    const meta = document.createElement("div");
    meta.className = "history-turn-meta";

    const role = document.createElement("span");
    role.textContent = turn.role || turn.sender || (index % 2 === 0 ? "patient" : "assistant");

    const time = document.createElement("span");
    time.textContent = formatDateTime(turn.created_at || turn.timestamp);

    meta.append(role, time);

    const text = document.createElement("p");
    text.textContent = turn.text || turn.content || turn.message || "";

    item.append(meta, text);
    recentHistory.appendChild(item);
  });
}

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

    if (booking.booking_note) {
      const notePanel = document.createElement("details");
      notePanel.className = "clinical-notes-block compact";

      const noteSummary = document.createElement("summary");
      noteSummary.textContent = "Clinical Notes";

      const noteBody = document.createElement("div");
      noteBody.className = "clinical-notes-body";
      noteBody.textContent = booking.booking_note;

      notePanel.append(noteSummary, noteBody);
      item.appendChild(notePanel);
    }

    activeAppointmentsPreview.appendChild(item);
  });
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
  const awaiting = nextState?.chat_closed ? "Closed" : nextState?.awaiting || "Describe symptoms";
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
    : nextState?.awaiting === "doctor_selection" || nextState?.awaiting === "slot_selection"
      ? "Booking"
      : nextState?.target_department
        ? "RAG"
        : "Conversation";

  workflowStateEl.textContent = activeLabel;
  updateWorkflowRail(activeLabel);

  const copy = nextState?.chat_closed
    ? "Care flow paused or completed."
    : nextState?.chat_summary
      ? nextState.chat_summary
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
}

function renderState(nextState) {
  state = nextState;
  updateWorkflowPanel(nextState);
  renderChatSummary(nextState?.chat_summary || "");
  renderRecentHistory(nextState?.recent_history || nextState?.conversation_history || []);
  renderActiveAppointments(nextState?.active_appointments || nextState?.confirmed_bookings || []);
  renderTokenUsage(nextState?.token_usage || null);
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

  if (state.awaiting === "reschedule_date_selection" && Array.isArray(state.reschedule_date_options)) {
    state.reschedule_date_options.forEach((option, index) => {
      addQuickAction(`${index + 1}. ${option.label}`, String(index + 1));
    });
  }

  if (state.awaiting === "reschedule_slot_selection" && Array.isArray(state.reschedule_slot_options)) {
    state.reschedule_slot_options.forEach((slot, index) => {
      const time = new Date(slot.start_time).toLocaleString();
      addQuickAction(`${index + 1}. ${time}`, String(index + 1));
    });
  }
}

function autoResizeComposer() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
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
    const response = await fetch("/chat/stream", {
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
  state = {
    patient_profile: currentUser,
    chat_session_id: newChatSessionId(),
    recent_history: [],
    conversation_history: [],
    chat_summary: "",
    chat_closed: false,
    token_usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0, llm_calls: 0 },
  };
  messages.replaceChildren();
  addAssistantMessage(
    currentUser
      ? `Hello ${currentUser.name}. Describe your symptoms, book an appointment, or ask to cancel an appointment.`
      : "Please sign in to begin.",
    { intro: true, noAnimation: true }
  );
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

    const sessionList = document.createElement("nav");
    sessionList.className = "history-session-list";
    sessionList.setAttribute("aria-label", "Chat sessions");

    const transcript = document.createElement("section");
    transcript.className = "history-transcript";

    const buildMeta = (session) => ({
      dateLabel: formatDateLabel(session.started_at || session.date),
      messageCount: session.message_count || (session.messages || []).length,
      sessionId: session.chat_session_id || "legacy-session",
    });

    const renderMessage = (message) => {
      const item = document.createElement("article");
      item.className = `history-message ${message.role}`;

      const role = document.createElement("span");
      role.textContent = message.role;
      const text = document.createElement("p");
      text.textContent = message.text || "";
      const time = document.createElement("time");
      time.textContent = formatDateTime(message.created_at);

      item.append(role, text, time);
      return item;
    };

    function renderSession(session, selectedButton) {
      sessionList.querySelectorAll("button").forEach((button) => {
        button.classList.toggle("active", button === selectedButton);
      });

      transcript.replaceChildren();

      const header = document.createElement("div");
      header.className = "history-transcript-header";
      const title = document.createElement("h3");
      title.textContent = session.title || "Conversation";
      const meta = document.createElement("p");
      const details = buildMeta(session);
      meta.textContent = `${details.dateLabel} - ${details.messageCount} messages`;
      const sessionId = document.createElement("code");
      sessionId.textContent = details.sessionId;
      header.append(title, meta, sessionId);
      transcript.appendChild(header);

      const thread = document.createElement("div");
      thread.className = "history-thread";
      (session.messages || []).forEach((message) => {
        thread.appendChild(renderMessage(message));
      });
      transcript.appendChild(thread);
    }

    sessions.forEach((session, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "history-session-button";

      const title = document.createElement("strong");
      title.textContent = session.title || "Conversation";
      const meta = document.createElement("span");
      const details = buildMeta(session);
      meta.textContent = `${details.dateLabel} - ${details.messageCount} messages`;

      button.append(title, meta);
      button.addEventListener("click", () => renderSession(session, button));
      sessionList.appendChild(button);

      if (index === 0) {
        renderSession(session, button);
      }
    });

    shell.append(sessionList, transcript);
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

  if (!message) {
    return;
  }

  if (state?.chat_closed) {
    showChatClosed();
    return;
  }

  input.value = "";
  adjustComposerHeight();
  addUserMessage(message);
  clearQuickActions();
  await sendMessage(message);
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

previousBookingsBtn.addEventListener("click", showPreviousBookings);
upcomingBookingsBtn.addEventListener("click", showUpcomingBookings);
chatHistoryBtn.addEventListener("click", showChatHistory);
closeProfilePanelBtn.addEventListener("click", hideProfilePanel);

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


