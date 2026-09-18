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
const voiceDiscardBtn = document.querySelector("#voiceDiscardBtn");
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
const adminAuditPane = document.querySelector("#adminAuditPane");
const adminAuditLogType = document.querySelector("#adminAuditLogType");
const adminAuditDoctorFilterField = document.querySelector("#adminAuditDoctorFilterField");
const adminAuditIdentifierFilterField = document.querySelector("#adminAuditIdentifierFilterField");
const adminAuditIdentifierFilter = document.querySelector("#adminAuditIdentifierFilter");
const adminAuditIdentifierLabel = document.querySelector("#adminAuditIdentifierLabel");
const adminAuditDoctorFilter = document.querySelector("#adminAuditDoctorFilter");
const adminAuditStartDate = document.querySelector("#adminAuditStartDate");
const adminAuditEndDate = document.querySelector("#adminAuditEndDate");
const adminAuditFilterBtn = document.querySelector("#adminAuditFilterBtn");
const adminAuditLogList = document.querySelector("#adminAuditLogList");
const adminAuditResultCount = document.querySelector("#adminAuditResultCount");
const adminAuditPrevPageBtn = document.querySelector("#adminAuditPrevPageBtn");
const adminAuditNextPageBtn = document.querySelector("#adminAuditNextPageBtn");
const adminAuditPageIndicator = document.querySelector("#adminAuditPageIndicator");
const adminStatusButtons = Array.from(document.querySelectorAll("[data-admin-status]"));
const adminRefreshLabel = adminRefreshBtn?.querySelector(".admin-action-label") || null;
const adminToast = document.querySelector("#adminToast");
const appToast = document.querySelector("#appToast");
let adminRefreshResetTimer = null;
let adminToastTimer = null;
let appToastTimer = null;
const profilePanel = document.querySelector("#profilePanel");
const profilePanelTitle = document.querySelector("#profilePanelTitle");
const profilePanelBody = document.querySelector("#profilePanelBody");
const closeProfilePanelBtn = document.querySelector("#closeProfilePanelBtn");
const chatClosedModal = document.querySelector("#chatClosedModal");
const startNewChatBtn = document.querySelector("#startNewChatBtn");
const endChatBtn = document.querySelector("#endChatBtn");
const endChatConfirmModal = document.querySelector("#endChatConfirmModal");
const endChatCancelBtn = document.querySelector("#endChatCancelBtn");
const endChatConfirmBtn = document.querySelector("#endChatConfirmBtn");

const showLoginBtn = document.querySelector("#showLoginBtn");
const showSignupBtn = document.querySelector("#showSignupBtn");
const showAdminBtn = document.querySelector("#showAdminBtn");
const authTabs = document.querySelector(".auth-tabs");
const authView = document.querySelector("#authView");
const loginForm = document.querySelector("#loginForm");
const signupForm = document.querySelector("#signupForm");
const adminLoginForm = document.querySelector("#adminLoginForm");
const doctorMfaForm = document.querySelector("#doctorMfaForm");
const doctorMfaFormHint = document.querySelector("#doctorMfaFormHint");
const doctorMfaCode = document.querySelector("#doctorMfaCode");
const doctorMfaRecoveryToggle = document.querySelector("#doctorMfaRecoveryToggle");
const adminBackBtn = document.querySelector("#adminBackBtn");
const doctorOnboardingView = document.querySelector("#doctorOnboardingView");
const doctorOnboardingMessage = document.querySelector("#doctorOnboardingMessage");
const doctorSetPasswordForm = document.querySelector("#doctorSetPasswordForm");
const doctorNewPassword = document.querySelector("#doctorNewPassword");
const doctorConfirmPassword = document.querySelector("#doctorConfirmPassword");
const doctorMfaEnrollStep = document.querySelector("#doctorMfaEnrollStep");
const doctorMfaQrContainer = document.querySelector("#doctorMfaQrContainer");
const doctorMfaProvisioningUri = document.querySelector("#doctorMfaProvisioningUri");
const doctorMfaEnrollForm = document.querySelector("#doctorMfaEnrollForm");
const doctorMfaEnrollCode = document.querySelector("#doctorMfaEnrollCode");
const doctorMfaEnrollMessage = document.querySelector("#doctorMfaEnrollMessage");
const doctorRecoveryCodesStep = document.querySelector("#doctorRecoveryCodesStep");
const doctorRecoveryCodesList = document.querySelector("#doctorRecoveryCodesList");
const doctorRecoveryDownloadBtn = document.querySelector("#doctorRecoveryDownloadBtn");
const doctorRecoveryAckCheckbox = document.querySelector("#doctorRecoveryAckCheckbox");
const doctorRecoveryContinueBtn = document.querySelector("#doctorRecoveryContinueBtn");
const doctorDashboardView = document.querySelector("#doctorDashboardView");
const doctorProfileName = document.querySelector("#doctorProfileName");
const doctorProfileDepartment = document.querySelector("#doctorProfileDepartment");
const doctorProfileExperience = document.querySelector("#doctorProfileExperience");
const doctorProfileMfaStatus = document.querySelector("#doctorProfileMfaStatus");
const doctorRecoveryLowNotice = document.querySelector("#doctorRecoveryLowNotice");
const doctorLogoutBtn = document.querySelector("#doctorLogoutBtn");
const doctorViewButtons = document.querySelectorAll("[data-doctor-view]");
const doctorStatToday = document.querySelector("#doctorStatToday");
const doctorOverviewPane = document.querySelector("#doctorOverviewPane");
const doctorUpcomingPane = document.querySelector("#doctorUpcomingPane");
const doctorPastPane = document.querySelector("#doctorPastPane");
const doctorPatientsPane = document.querySelector("#doctorPatientsPane");
const doctorPatientDetailPane = document.querySelector("#doctorPatientDetailPane");
const doctorAppointmentDetailPane = document.querySelector("#doctorAppointmentDetailPane");
const doctorUpcomingList = document.querySelector("#doctorUpcomingList");
const doctorPastList = document.querySelector("#doctorPastList");
const doctorPatientsList = document.querySelector("#doctorPatientsList");
const doctorPatientSearchInput = document.querySelector("#doctorPatientSearchInput");
const doctorUpcomingCount = document.querySelector("#doctorUpcomingCount");
const doctorPastCount = document.querySelector("#doctorPastCount");
const doctorPatientsCount = document.querySelector("#doctorPatientsCount");
const doctorPatientDetailName = document.querySelector("#doctorPatientDetailName");
const doctorPatientDetailFields = document.querySelector("#doctorPatientDetailFields");
const doctorPatientDetailVisits = document.querySelector("#doctorPatientDetailVisits");
const doctorPatientDetailBackBtn = document.querySelector("#doctorPatientDetailBackBtn");
const doctorAppointmentDetailFields = document.querySelector("#doctorAppointmentDetailFields");
const doctorAppointmentDetailBackBtn = document.querySelector("#doctorAppointmentDetailBackBtn");
const doctorConsultStatusBadge = document.querySelector("#doctorConsultStatusBadge");
const doctorConsultIdLabel = document.querySelector("#doctorConsultIdLabel");
const doctorConsultDurationLabel = document.querySelector("#doctorConsultDurationLabel");
const doctorConsultMessage = document.querySelector("#doctorConsultMessage");
const doctorConsultStartRow = document.querySelector("#doctorConsultStartRow");
const doctorConsultStartBtn = document.querySelector("#doctorConsultStartBtn");
const doctorConsultConsentBlock = document.querySelector("#doctorConsultConsentBlock");
const doctorConsultConsentCheckbox = document.querySelector("#doctorConsultConsentCheckbox");
const doctorConsultConsentConfirmBtn = document.querySelector("#doctorConsultConsentConfirmBtn");
const doctorConsultRecordRow = document.querySelector("#doctorConsultRecordRow");
const doctorConsultBeginRecordingBtn = document.querySelector("#doctorConsultBeginRecordingBtn");
const doctorConsultStopRow = document.querySelector("#doctorConsultStopRow");
const doctorConsultStopRecordingBtn = document.querySelector("#doctorConsultStopRecordingBtn");
const doctorConsultLiveTimer = document.querySelector("#doctorConsultLiveTimer");
const doctorConsultLevelFill = document.querySelector("#doctorConsultLevelFill");
const doctorConsultOrphanedRow = document.querySelector("#doctorConsultOrphanedRow");
const doctorConsultOrphanedEndBtn = document.querySelector("#doctorConsultOrphanedEndBtn");
const doctorConsultProcessingNote = document.querySelector("#doctorConsultProcessingNote");
const doctorConsultTranscriptBlock = document.querySelector("#doctorConsultTranscriptBlock");
const doctorConsultTranscriptList = document.querySelector("#doctorConsultTranscriptList");
const doctorConsultSwapSpeakersBtn = document.querySelector("#doctorConsultSwapSpeakersBtn");
const doctorConsultFallbackNotice = document.querySelector("#doctorConsultFallbackNotice");
const doctorConsultNoteBlock = document.querySelector("#doctorConsultNoteBlock");
const doctorNoteStatusBadge = document.querySelector("#doctorNoteStatusBadge");
const doctorNoteMessage = document.querySelector("#doctorNoteMessage");
const doctorNoteFallbackNotice = document.querySelector("#doctorNoteFallbackNotice");
const doctorNoteGenerateRow = document.querySelector("#doctorNoteGenerateRow");
const doctorNoteGenerateBtn = document.querySelector("#doctorNoteGenerateBtn");
const doctorNoteGenerateConfirm = document.querySelector("#doctorNoteGenerateConfirm");
const doctorNoteGenerateConfirmBtn = document.querySelector("#doctorNoteGenerateConfirmBtn");
const doctorNoteGenerateCancelBtn = document.querySelector("#doctorNoteGenerateCancelBtn");
const doctorNoteDraftBlock = document.querySelector("#doctorNoteDraftBlock");
const doctorNoteFieldsContainer = document.querySelector("#doctorNoteFieldsContainer");
const doctorNoteSaveBtn = document.querySelector("#doctorNoteSaveBtn");
const doctorNoteSignBtn = document.querySelector("#doctorNoteSignBtn");
const doctorNoteSignConfirm = document.querySelector("#doctorNoteSignConfirm");
const doctorNoteSignConfirmBtn = document.querySelector("#doctorNoteSignConfirmBtn");
const doctorNoteSignCancelBtn = document.querySelector("#doctorNoteSignCancelBtn");
const doctorNoteSignedBlock = document.querySelector("#doctorNoteSignedBlock");
const doctorNoteCopyBtn = document.querySelector("#doctorNoteCopyBtn");
const doctorNoteSignedFieldsContainer = document.querySelector("#doctorNoteSignedFieldsContainer");
const doctorNoteAddendaList = document.querySelector("#doctorNoteAddendaList");
const doctorNoteAddendumRow = document.querySelector("#doctorNoteAddendumRow");
const doctorNoteAddAddendumBtn = document.querySelector("#doctorNoteAddAddendumBtn");
const doctorNoteAddendumForm = document.querySelector("#doctorNoteAddendumForm");
const doctorNoteAddendumText = document.querySelector("#doctorNoteAddendumText");
const doctorNoteAddendumSaveBtn = document.querySelector("#doctorNoteAddendumSaveBtn");
const doctorNoteAddendumCancelBtn = document.querySelector("#doctorNoteAddendumCancelBtn");
const doctorConsultDiscardRow = document.querySelector("#doctorConsultDiscardRow");
const doctorConsultDiscardBtn = document.querySelector("#doctorConsultDiscardBtn");
const doctorConsultDiscardConfirm = document.querySelector("#doctorConsultDiscardConfirm");
const doctorConsultDiscardConfirmBtn = document.querySelector("#doctorConsultDiscardConfirmBtn");
const doctorConsultDiscardCancelBtn = document.querySelector("#doctorConsultDiscardCancelBtn");
const pageAssistant = document.querySelector("#pageAssistant");
const pageDashboard = document.querySelector("#pageDashboard");
const pageAppointments = document.querySelector("#pageAppointments");
const pageRecords = document.querySelector("#pageRecords");
const pageAdmin = document.querySelector("#pageAdmin");
const signupStepOne = document.querySelector("#signupStepOne");
const signupStepTwo = document.querySelector("#signupStepTwo");
const signupNextBtn = document.querySelector("#signupNextBtn");
const signupBackBtn = document.querySelector("#signupBackBtn");
const patientVerifyForm = document.querySelector("#patientVerifyForm");
const patientVerifyHint = document.querySelector("#patientVerifyHint");
const patientVerifyCode = document.querySelector("#patientVerifyCode");
const patientVerifyResendBtn = document.querySelector("#patientVerifyResendBtn");
const patientMfaForm = document.querySelector("#patientMfaForm");
const patientMfaCode = document.querySelector("#patientMfaCode");
const patientMfaBackBtn = document.querySelector("#patientMfaBackBtn");
const showForgotPasswordBtn = document.querySelector("#showForgotPasswordBtn");
const forgotPasswordStartForm = document.querySelector("#forgotPasswordStartForm");
const forgotPasswordIdentifier = document.querySelector("#forgotPasswordIdentifier");
const forgotPasswordStartBackBtn = document.querySelector("#forgotPasswordStartBackBtn");
const forgotPasswordConfirmEmailForm = document.querySelector("#forgotPasswordConfirmEmailForm");
const forgotPasswordConfirmEmailHint = document.querySelector("#forgotPasswordConfirmEmailHint");
const forgotPasswordConfirmEmail = document.querySelector("#forgotPasswordConfirmEmail");
const forgotPasswordConfirmEmailBackBtn = document.querySelector("#forgotPasswordConfirmEmailBackBtn");
const resetPasswordForm = document.querySelector("#resetPasswordForm");
const resetPasswordCode = document.querySelector("#resetPasswordCode");
const resetPasswordNew = document.querySelector("#resetPasswordNew");
const resetPasswordConfirm = document.querySelector("#resetPasswordConfirm");
const resetPasswordResendBtn = document.querySelector("#resetPasswordResendBtn");
const resetPasswordCountdown = document.querySelector("#resetPasswordCountdown");
const resetPasswordBackBtn = document.querySelector("#resetPasswordBackBtn");
const authMessage = document.querySelector("#authMessage");
const adminAuthMessage = document.querySelector("#adminAuthMessage");
let doctorMfaToken = null;
let doctorMfaUsingRecoveryCode = false;
let patientVerifyToken = null;
let patientMfaToken = null;
let resetPasswordCountdownCancel = null;
let secChangePasswordCountdownCancel = null;
let loginLockoutCountdownCancel = null;
const loginLockoutCountdown = document.querySelector("#loginLockoutCountdown");
let resetEmail = null;
let resetPendingMobileNumber = null;
let pendingInviteToken = null;
let doctorMfaEnrollmentToken = null;
let doctorRecoveryCodesInMemory = null;
let doctorLowRecoveryNoticePending = false;
let doctorCurrentView = "overview";
let doctorUpcomingAppointments = [];
let doctorPastAppointments = [];
let doctorPatientsCache = [];
let doctorPatientSearchTerm = "";
let doctorDetailReturnView = "upcoming";
let doctorDetailAppointment = null;
let doctorActiveConsult = null;
let doctorConsultPollTimer = null;
let doctorRecordingTimerInterval = null;
let doctorRecordingStartedAtMs = null;
let doctorConsultSegmentsById = {};
let doctorCurrentNote = null;
let consultAudioContext = null;
let consultMicStream = null;
let consultWorkletNode = null;
let consultSocket = null;
let consultPendingFrames = [];

let state = null;
let currentUser = JSON.parse(localStorage.getItem("currentUser") || "null");
let accessToken = localStorage.getItem("accessToken");
let refreshToken = localStorage.getItem("refreshToken");
let currentAdmin = JSON.parse(localStorage.getItem("currentAdmin") || "null");
let adminAccessToken = localStorage.getItem("adminAccessToken");
let adminRefreshToken = localStorage.getItem("adminRefreshToken");
let doctorAccessToken = localStorage.getItem("doctorAccessToken");
let patientId = currentUser?.patient_id || null;
let adminAuditPage = 1;
const adminAuditPageSize = 20;
let adminAuditTotal = 0;
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
let voiceCommittedTranscript = "";
let voiceListening = false;
let voicePendingFrames = [];
let voiceStopping = false;
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

function showAppToast(message, tone = "success", timeoutMs = 3000) {
  if (!appToast || !message) return;

  if (appToastTimer) {
    window.clearTimeout(appToastTimer);
    appToastTimer = null;
  }

  appToast.textContent = message;
  appToast.className = `app-toast is-${tone} enter`;
  appToast.classList.remove("hidden");

  appToastTimer = window.setTimeout(() => {
    appToast.classList.add("hidden");
    appToast.classList.remove("enter");
    appToastTimer = null;
  }, timeoutMs);
}

// Mirrors app/services/password_reset.py::RESEND_COOLDOWN_SECONDS — the initial
// otp_sent responses (forgot-password/start, confirm-email) don't echo back
// retry_after_seconds (only an explicit resend does), so this is the known starting
// point for the countdown; every actual resend then re-syncs to the server's real value.
const OTP_RESEND_COOLDOWN_SECONDS = 240;

function beginLoginLockoutCountdown(seconds) {
  if (loginLockoutCountdownCancel) {
    loginLockoutCountdownCancel();
    loginLockoutCountdownCancel = null;
  }
  const submitBtn = loginForm?.querySelector("button[type='submit']");
  if (submitBtn) submitBtn.disabled = true;
  loginLockoutCountdownCancel = startCountdown(
    loginLockoutCountdown,
    seconds,
    () => {
      if (submitBtn) submitBtn.disabled = false;
      loginLockoutCountdownCancel = null;
    },
    "Too many failed attempts. Try again in",
  );
}

function beginResetPasswordCountdown(seconds) {
  if (resetPasswordCountdownCancel) {
    resetPasswordCountdownCancel();
    resetPasswordCountdownCancel = null;
  }
  if (resetPasswordResendBtn) resetPasswordResendBtn.disabled = true;
  resetPasswordCountdownCancel = startCountdown(resetPasswordCountdown, seconds, () => {
    if (resetPasswordResendBtn) resetPasswordResendBtn.disabled = false;
  });
}

function attachPasswordToggle(input) {
  if (!input || input.dataset.toggleAttached) return;
  input.dataset.toggleAttached = "true";

  const wrap = document.createElement("span");
  wrap.className = "password-field-wrap";
  input.parentNode.insertBefore(wrap, input);
  wrap.appendChild(input);

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "password-toggle-btn";
  btn.textContent = "Show";
  btn.setAttribute("aria-label", "Show password");
  btn.addEventListener("click", () => {
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    btn.textContent = showing ? "Show" : "Hide";
    btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
  });
  wrap.appendChild(btn);
}

function wireAllPasswordToggles(root = document) {
  root.querySelectorAll('input[type="password"]').forEach(attachPasswordToggle);
}

function startCountdown(el, seconds, onExpire, label = "Resend available in") {
  if (!el) return () => {};
  let remaining = Math.max(0, Math.ceil(seconds));

  const render = () => {
    const mm = String(Math.floor(remaining / 60)).padStart(2, "0");
    const ss = String(remaining % 60).padStart(2, "0");
    el.textContent = remaining > 0 ? `${label} ${mm}:${ss}` : "";
  };

  render();
  const intervalId = window.setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      remaining = 0;
      render();
      window.clearInterval(intervalId);
      if (onExpire) onExpire();
      return;
    }
    render();
  }, 1000);

  return () => window.clearInterval(intervalId);
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
  return ["overview", "appointments", "manage", "inventory", "audit"].includes(saved) ? saved : "overview";
}

function showAdminView(view) {
  const nextView = ["overview", "appointments", "manage", "inventory", "audit"].includes(view) ? view : "overview";
  const panes = {
    overview: adminOverviewPane,
    appointments: adminAppointmentsPane,
    manage: adminManagePane,
    inventory: adminInventoryPane,
    audit: adminAuditPane,
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
  if (nextView === "audit") {
    if (!adminManagementLoaded) loadAdminManagement();
    renderAdminAuditDoctorOptions();
    updateAdminAuditFilterVisibility();
    loadAdminAuditLog(1);
  }
}

function showAuthMode(mode) {
  const isLogin = mode === "login";
  const isSignup = mode === "signup";
  loginForm.classList.toggle("hidden", !isLogin);
  signupForm.classList.toggle("hidden", !isSignup);
  if (doctorMfaForm) doctorMfaForm.classList.add("hidden");
  if (patientVerifyForm) patientVerifyForm.classList.add("hidden");
  if (patientMfaForm) patientMfaForm.classList.add("hidden");
  if (forgotPasswordStartForm) forgotPasswordStartForm.classList.add("hidden");
  if (forgotPasswordConfirmEmailForm) forgotPasswordConfirmEmailForm.classList.add("hidden");
  if (resetPasswordForm) resetPasswordForm.classList.add("hidden");
  if (resetPasswordCountdownCancel) {
    resetPasswordCountdownCancel();
    resetPasswordCountdownCancel = null;
  }
  showLoginBtn.classList.toggle("active", isLogin);
  showSignupBtn.classList.toggle("active", isSignup);
  if (showAdminBtn) showAdminBtn.classList.remove("active");
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
  // When the backend supplies active_appointments (for example from
  // /appointments/upcoming), it is the database-authoritative list. Do not
  // merge it with an older client/chat list, otherwise a newly booked item
  // can be hidden by stale entries in the three-card preview.
  const authoritativeAppointments = Array.isArray(nextState?.active_appointments)
    ? nextState.active_appointments
    : null;
  const upcomingBookings = authoritativeAppointments
    ? authoritativeAppointments
    : mergeBookingLists(
      nextState?.upcoming_bookings || nextState?.confirmed_bookings || fallbackState?.upcoming_bookings || fallbackState?.confirmed_bookings || [],
      fallbackState?.active_appointments || []
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
    preferred_language: nextState?.preferred_language ?? fallbackState?.preferred_language ?? currentUser?.preferred_language ?? "en",
    active_language: nextState?.active_language ?? fallbackState?.active_language ?? null,
    detected_language: nextState?.detected_language ?? fallbackState?.detected_language ?? null,
    language_confidence: nextState?.language_confidence ?? fallbackState?.language_confidence ?? null,
    language_switch_candidate: nextState?.language_switch_candidate ?? fallbackState?.language_switch_candidate ?? null,
    language_switch_count: nextState?.language_switch_count ?? fallbackState?.language_switch_count ?? 0,
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

function setPatientAuthenticated(user, token, refreshTokenValue) {
  currentUser = user;
  accessToken = token;
  refreshToken = refreshTokenValue || null;
  currentAdmin = null;
  adminAccessToken = null;
  patientId = user.patient_id;
  localStorage.setItem("currentUser", JSON.stringify(user));
  localStorage.setItem("accessToken", token);
  if (refreshToken) {
    localStorage.setItem("refreshToken", refreshToken);
  } else {
    localStorage.removeItem("refreshToken");
  }
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

function setAdminAuthenticated(admin, token, refreshTokenValue) {
  currentAdmin = admin;
  adminAccessToken = token;
  adminRefreshToken = refreshTokenValue || null;
  currentUser = null;
  accessToken = null;
  patientId = null;
  localStorage.setItem("currentAdmin", JSON.stringify(admin));
  localStorage.setItem("adminAccessToken", token);
  if (adminRefreshToken) {
    localStorage.setItem("adminRefreshToken", adminRefreshToken);
  } else {
    localStorage.removeItem("adminRefreshToken");
  }
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
  refreshToken = null;
  adminAccessToken = null;
  adminRefreshToken = null;
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
  doctorAccessToken = null;
  localStorage.removeItem("currentUser");
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("currentAdmin");
  localStorage.removeItem("adminAccessToken");
  localStorage.removeItem("adminRefreshToken");
  localStorage.removeItem("doctorAccessToken");
  document.body.classList.remove("authenticated");
  document.body.classList.remove("admin-authenticated");
  document.body.classList.remove("doctor-authenticated");
  doctorDashboardView?.classList.add("hidden");
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

function doctorAuthHeaders() {
  return { Authorization: `Bearer ${doctorAccessToken}` };
}

async function doctorAuthedJson(url, options = {}) {
  const timeoutMs = options.timeoutMs ?? 15000;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        ...doctorAuthHeaders(),
        ...(options.headers || {}),
      },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) {
        clearDoctorAuthenticated();
        showAuthMode("login");
      }
      const requestError = new Error(data.detail || `Request failed with ${response.status}`);
      requestError.status = response.status;
      throw requestError;
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

function setDoctorAuthenticated(token) {
  doctorAccessToken = token;
  currentUser = null;
  accessToken = null;
  currentAdmin = null;
  adminAccessToken = null;
  patientId = null;
  localStorage.setItem("doctorAccessToken", token);
  localStorage.removeItem("currentUser");
  localStorage.removeItem("accessToken");
  localStorage.removeItem("currentAdmin");
  localStorage.removeItem("adminAccessToken");
  document.body.classList.add("doctor-authenticated");
  document.body.classList.remove("authenticated");
  document.body.classList.remove("admin-authenticated");
  doctorOnboardingView?.classList.add("hidden");
  doctorDashboardView?.classList.remove("hidden");
  showDoctorView("overview");
  loadDoctorDashboard();
}

function clearDoctorAuthenticated() {
  stopConsultRecording();
  stopConsultStatusPolling();
  doctorAccessToken = null;
  localStorage.removeItem("doctorAccessToken");
  document.body.classList.remove("doctor-authenticated");
  doctorDashboardView?.classList.add("hidden");
  doctorUpcomingAppointments = [];
  doctorPastAppointments = [];
  doctorPatientsCache = [];
}

async function loadDoctorDashboard() {
  try {
    const data = await doctorAuthedJson("/doctor/me");
    renderDoctorDashboard(data.doctor);
  } catch (error) {
    // A 401 is already handled inside doctorAuthedJson (logs the doctor out);
    // any other failure just leaves the dashboard fields at their placeholders.
  }
  loadDoctorAppointments("upcoming");
}

function showDoctorView(view) {
  const validViews = ["overview", "upcoming", "past", "patients"];
  const nextView = validViews.includes(view) ? view : "overview";
  doctorCurrentView = nextView;

  // Any navigation away from the appointment detail pane must release the mic/socket —
  // this is the sidebar-nav path, distinct from (and previously missed by) the
  // dedicated "Back" button and showDoctorAppointmentDetail's own cleanup calls. Both
  // functions are safe no-ops when nothing is actually recording.
  stopConsultRecording();
  stopConsultStatusPolling();

  const panes = {
    overview: doctorOverviewPane,
    upcoming: doctorUpcomingPane,
    past: doctorPastPane,
    patients: doctorPatientsPane,
  };
  Object.entries(panes).forEach(([key, element]) => {
    if (!element) return;
    element.classList.toggle("hidden", key !== nextView);
  });
  doctorPatientDetailPane?.classList.add("hidden");
  doctorAppointmentDetailPane?.classList.add("hidden");

  doctorViewButtons.forEach((button) => {
    const isActive = button.dataset.doctorView === nextView;
    button.classList.toggle("is-active", isActive);
    // is-active alone is a purely visual cue — aria-current gives screen reader users
    // the same "which section am I in" signal sighted users get from the highlight.
    if (isActive) {
      button.setAttribute("aria-current", "page");
    } else {
      button.removeAttribute("aria-current");
    }
  });

  if (nextView === "upcoming" && !doctorUpcomingAppointments.length) loadDoctorAppointments("upcoming");
  if (nextView === "past" && !doctorPastAppointments.length) loadDoctorAppointments("past");
  if (nextView === "patients" && !doctorPatientsCache.length) loadDoctorPatientsList();
}

function _istToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
}

function updateDoctorTodayStat(upcomingAppointments) {
  if (!doctorStatToday) return;
  const today = _istToday();
  const count = upcomingAppointments.filter((appt) => String(appt.start_time || "").slice(0, 10) === today).length;
  doctorStatToday.textContent = String(count);
}

async function loadDoctorAppointments(scope) {
  const listEl = scope === "upcoming" ? doctorUpcomingList : doctorPastList;
  const countEl = scope === "upcoming" ? doctorUpcomingCount : doctorPastCount;
  if (countEl) countEl.textContent = "Loading...";
  try {
    const data = await doctorAuthedJson(`/doctor/appointments?scope=${scope}`);
    const appointments = Array.isArray(data.appointments) ? data.appointments : [];
    if (scope === "upcoming") {
      doctorUpcomingAppointments = appointments;
      updateDoctorTodayStat(appointments);
    } else {
      doctorPastAppointments = appointments;
    }
    renderDoctorAppointmentsList(listEl, appointments, scope);
    if (countEl) countEl.textContent = `${appointments.length} appointment${appointments.length === 1 ? "" : "s"}`;
  } catch (error) {
    if (countEl) countEl.textContent = "Unable to load.";
  }
}

function renderDoctorAppointmentsList(listEl, appointments, scope) {
  if (!listEl) return;
  listEl.replaceChildren();

  if (!appointments.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = scope === "upcoming" ? "No upcoming appointments." : "No past appointments.";
    listEl.appendChild(note);
    return;
  }

  appointments.forEach((appt) => {
    const card = document.createElement("article");
    card.className = "admin-inline-card doctor-clickable-card";

    const head = document.createElement("div");
    head.className = "admin-inline-card-head";

    const titleWrap = document.createElement("div");
    const title = document.createElement("div");
    title.className = "admin-inline-title";
    title.textContent = appt.patient_name || "Unknown patient";
    const meta = document.createElement("div");
    meta.className = "admin-inline-meta";
    meta.textContent = `${appt.department || "Department"} · ${formatDateTime(appt.start_time)}`;
    titleWrap.append(title, meta);

    const statusValue = adminStatusLabel(appt);
    const badge = document.createElement("span");
    badge.className = `admin-status-pill ${statusValue ? `is-${statusValue}` : ""}`;
    badge.textContent = statusValue || appt.status || "";

    head.append(titleWrap, badge);
    const durationBadge = buildDurationBadge(appt);
    if (durationBadge) head.appendChild(durationBadge);
    card.appendChild(head);
    card.addEventListener("click", () => showDoctorAppointmentDetail(appt, scope));
    listEl.appendChild(card);
  });
}

// Static text only — "Recording…" while in progress, the fixed final duration once
// ended. No live-ticking here; only the detail page (where the doctor is actually
// watching it record) gets a live timer, via renderConsultState/tickRecordingTimer.
function buildDurationBadge(appt) {
  if (appt.consult_status === "recording") {
    const badge = document.createElement("span");
    badge.className = "admin-status-pill is-upcoming";
    badge.textContent = "Recording…";
    return badge;
  }
  if (appt.consult_started_at && appt.consult_ended_at) {
    const seconds = (new Date(appt.consult_ended_at) - new Date(appt.consult_started_at)) / 1000;
    const badge = document.createElement("span");
    badge.className = "admin-status-pill";
    badge.textContent = formatDuration(seconds);
    return badge;
  }
  return null;
}

// Renders a lightly-markdown-formatted clinical note (headings, **bold**, "- " bullets)
// as real DOM elements — never via innerHTML/raw HTML string concatenation. Every piece
// of text passes through document.createTextNode or element.textContent, both of which
// the browser always treats as literal text, never as markup, no matter what characters
// it contains. This note is partly derived from patient-supplied input, so this must
// never become an XSS path regardless of what the LLM echoes back or what a patient
// originally typed.
function renderClinicalNote(container, rawText) {
  container.replaceChildren();
  if (!rawText || rawText === "-") {
    container.textContent = rawText || "-";
    return;
  }

  // Normalize both real and LITERAL escaped newlines to real newlines. The LLM that
  // generates these summaries (app/agents/checkup_report.py) occasionally emits a
  // literal two-character "\n" (backslash + n) in its raw text output instead of an
  // actual newline control character — a generation-time quirk, not a display bug, but
  // a doctor should never see a literal backslash-n either way, so both representations
  // are normalized identically here.
  const normalized = String(rawText)
    .replace(/\\r\\n/g, "\n")
    .replace(/\\n/g, "\n")
    .replace(/\\r/g, "\n")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n");

  normalized.split("\n").forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) return; // collapse blank lines rather than rendering empty paragraphs

    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(line);
    const bulletMatch = /^[-*]\s+(.*)$/.exec(line);
    const text = headingMatch ? headingMatch[2] : bulletMatch ? bulletMatch[1] : line;

    const lineEl = document.createElement(headingMatch ? "h4" : "p");
    lineEl.className = "clinical-note-line";
    if (headingMatch) lineEl.classList.add("clinical-note-heading");
    if (bulletMatch) lineEl.classList.add("clinical-note-bullet");

    appendInlineMarkdown(lineEl, text);
    container.appendChild(lineEl);
  });
}

// Renders **bold** spans as real <strong> elements. Text outside **...** and the bold
// text itself are both inserted via createTextNode/textContent only.
function appendInlineMarkdown(parent, text) {
  const boldPattern = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match;
  while ((match = boldPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parent.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
    }
    const strong = document.createElement("strong");
    strong.textContent = match[1];
    parent.appendChild(strong);
    lastIndex = boldPattern.lastIndex;
  }
  if (lastIndex < text.length) {
    parent.appendChild(document.createTextNode(text.slice(lastIndex)));
  }
}

function showDoctorAppointmentDetail(appt, scope) {
  doctorDetailReturnView = scope;
  doctorDetailAppointment = appt;
  stopConsultRecording();
  stopConsultStatusPolling();
  doctorActiveConsult = appt.consult_id
    ? {
        id: appt.consult_id, status: appt.consult_status,
        started_at: appt.consult_started_at, ended_at: appt.consult_ended_at,
      }
    : null;
  doctorRecordingStartedAtMs = null;
  stopRecordingTimer();
  setDoctorConsultMessage("");

  if (doctorAppointmentDetailFields) {
    doctorAppointmentDetailFields.replaceChildren();
    const fields = [
      ["Patient", appt.patient_name || "Unknown patient"],
      ["Department", appt.department || "-"],
      ["Time", formatDateTime(appt.start_time)],
      ["Status", appt.status || "-"],
    ];
    fields.forEach(([label, value]) => {
      const field = document.createElement("div");
      field.className = "admin-field";
      const span = document.createElement("span");
      span.textContent = label;
      const strong = document.createElement("strong");
      strong.textContent = value;
      field.append(span, strong);
      doctorAppointmentDetailFields.appendChild(field);
    });

    // The note (often an LLM-generated pre-appointment clinical summary — see
    // app/agents/checkup_report.py) can be long, multi-line, lightly-markdown-formatted
    // text, partly derived from patient-supplied input — rendered via renderClinicalNote,
    // never innerHTML, so it can never become an XSS path regardless of its content.
    const noteField = document.createElement("div");
    noteField.className = "admin-field";
    const noteLabel = document.createElement("span");
    noteLabel.textContent = "Note";
    const noteBody = document.createElement("div");
    noteBody.className = "clinical-note-body";
    renderClinicalNote(noteBody, appt.booking_note);
    noteField.append(noteLabel, noteBody);
    doctorAppointmentDetailFields.appendChild(noteField);
  }

  [doctorOverviewPane, doctorUpcomingPane, doctorPastPane, doctorPatientsPane, doctorPatientDetailPane].forEach((pane) =>
    pane?.classList.add("hidden")
  );
  doctorAppointmentDetailPane?.classList.remove("hidden");

  renderConsultState();
  if (doctorActiveConsult && (doctorActiveConsult.status === "ended" || doctorActiveConsult.status === "transcribing")) {
    startConsultStatusPolling();
  }
}

// ── Consult recording (Part 2/3 wiring) ──────────────────────────────────────

const DOCTOR_CONSULT_STATUS_LABELS = {
  not_started: "Not started",
  consented: "Consented",
  recording: "Recording",
  ended: "Ended",
  transcribing: "Transcribing",
  transcript_ready: "Transcript ready",
};

function setDoctorConsultMessage(text) {
  if (doctorConsultMessage) doctorConsultMessage.textContent = text || "";
}

function renderConsultState() {
  // A 'discarded' consult is treated exactly like no consult at all — the backend
  // itself allows a fresh Start to supersede it, so the UI offers that too.
  const status = doctorActiveConsult && doctorActiveConsult.status !== "discarded" ? doctorActiveConsult.status : null;

  // doctorDetailAppointment is the SAME object reference sitting in the cached
  // doctorUpcomingAppointments/doctorPastAppointments array (see
  // showDoctorAppointmentDetail, which sets both from the same click-handler closure) —
  // mutating it here keeps that cached list's entry in sync with every consult
  // lifecycle transition (start/consent/begin-recording/end/discard, all of which call
  // this function), so re-clicking the same card later (without an intervening
  // GET /doctor/appointments refetch) never resurrects stale pre-transition state. Uses
  // the already-normalized `status` (not raw doctorActiveConsult.status) so a discarded
  // consult mirrors exactly what a real refetch would show: nothing, since
  // list_latest_consult_status_by_booking excludes discarded rows entirely.
  if (doctorDetailAppointment) {
    doctorDetailAppointment.consult_id = status ? doctorActiveConsult.id : null;
    doctorDetailAppointment.consult_status = status;
    doctorDetailAppointment.consult_started_at = status ? doctorActiveConsult.started_at : null;
    doctorDetailAppointment.consult_ended_at = status ? doctorActiveConsult.ended_at : null;
  }

  if (doctorConsultStatusBadge) {
    doctorConsultStatusBadge.textContent = status ? (DOCTOR_CONSULT_STATUS_LABELS[status] || status) : "No consult yet";
    const modifier = status === "consented" || status === "recording" ? "is-upcoming" : status === "transcript_ready" ? "is-completed" : "";
    doctorConsultStatusBadge.className = `admin-status-pill ${modifier}`.trim();
  }

  if (doctorConsultIdLabel) {
    // Uses doctorActiveConsult directly (not the discarded-normalized `status` above) —
    // the id remains a meaningful cross-reference even for a discarded consult.
    doctorConsultIdLabel.textContent = doctorActiveConsult ? `Consult ID: ${doctorActiveConsult.id}` : "";
    doctorConsultIdLabel.classList.toggle("hidden", !doctorActiveConsult);
  }

  // status === "recording" splits into two distinct UIs: this tab is the one actually
  // holding the live mic/socket (consultSocket is set, e.g. right after clicking Begin
  // Recording), vs. a recording that shows as in-progress but this tab has no live
  // connection to it — e.g. after a reload, or opening the same appointment in a
  // different tab. The latter must never offer a "Stop Recording" button, since there
  // is nothing live in this tab to stop, and reconnecting to a live Deepgram stream
  // isn't something this design supports.
  const isLiveLocalRecording = status === "recording" && !!consultSocket;
  const isOrphanedRecording = status === "recording" && !consultSocket;

  doctorConsultStartRow?.classList.toggle("hidden", !!status);
  doctorConsultConsentBlock?.classList.toggle("hidden", status !== "not_started");
  doctorConsultRecordRow?.classList.toggle("hidden", status !== "consented");
  doctorConsultStopRow?.classList.toggle("hidden", !isLiveLocalRecording);
  doctorConsultOrphanedRow?.classList.toggle("hidden", !isOrphanedRecording);
  doctorConsultProcessingNote?.classList.toggle("hidden", status !== "ended" && status !== "transcribing");
  doctorConsultTranscriptBlock?.classList.toggle("hidden", status !== "transcript_ready");
  doctorConsultNoteBlock?.classList.toggle("hidden", status !== "transcript_ready");
  doctorConsultDiscardRow?.classList.toggle("hidden", !status);
  doctorConsultDiscardConfirm?.classList.add("hidden");

  if (doctorConsultConsentCheckbox) doctorConsultConsentCheckbox.checked = false;
  if (doctorConsultConsentConfirmBtn) doctorConsultConsentConfirmBtn.disabled = true;

  if (isLiveLocalRecording || isOrphanedRecording) {
    doctorConsultDurationLabel?.classList.remove("hidden");
    // An orphaned recording (reload mid-recording, or opened in a fresh tab) has no
    // client-captured start instant — recover it from the server's started_at instead.
    // Guarded so this only fires once per orphaned-recording sighting, not on every
    // render (e.g. every 4s status-poll tick).
    if (isOrphanedRecording && doctorRecordingStartedAtMs === null && doctorActiveConsult?.started_at) {
      doctorRecordingStartedAtMs = new Date(doctorActiveConsult.started_at).getTime();
      startRecordingTimer();
    }
  } else {
    stopRecordingTimer();
    if (doctorActiveConsult?.started_at && doctorActiveConsult?.ended_at) {
      const seconds = (new Date(doctorActiveConsult.ended_at) - new Date(doctorActiveConsult.started_at)) / 1000;
      if (doctorConsultDurationLabel) {
        doctorConsultDurationLabel.textContent = `Duration: ${formatDuration(seconds)}`;
        doctorConsultDurationLabel.classList.remove("hidden");
      }
    } else if (doctorConsultDurationLabel) {
      doctorConsultDurationLabel.textContent = "";
      doctorConsultDurationLabel.classList.add("hidden");
    }
  }

  if (status === "transcript_ready") {
    loadConsultTranscript();
    loadSoapNote();
  }
}

function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Math.round(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`;
}

function tickRecordingTimer() {
  if (doctorRecordingStartedAtMs === null) return;
  const text = formatDuration((Date.now() - doctorRecordingStartedAtMs) / 1000);
  if (doctorConsultDurationLabel) doctorConsultDurationLabel.textContent = `Duration: ${text}`;
  if (doctorConsultLiveTimer) doctorConsultLiveTimer.textContent = text;
}

function startRecordingTimer() {
  stopRecordingTimer();
  tickRecordingTimer();
  doctorRecordingTimerInterval = window.setInterval(tickRecordingTimer, 1000);
}

function stopRecordingTimer() {
  if (doctorRecordingTimerInterval) {
    window.clearInterval(doctorRecordingTimerInterval);
    doctorRecordingTimerInterval = null;
  }
}

function stopConsultStatusPolling() {
  if (doctorConsultPollTimer) {
    window.clearInterval(doctorConsultPollTimer);
    doctorConsultPollTimer = null;
  }
}

function startConsultStatusPolling() {
  stopConsultStatusPolling();
  doctorConsultPollTimer = window.setInterval(async () => {
    if (!doctorActiveConsult) {
      stopConsultStatusPolling();
      return;
    }
    try {
      const transcript = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/transcript`);
      if (transcript.status !== doctorActiveConsult.status) {
        doctorActiveConsult = { ...doctorActiveConsult, status: transcript.status };
        renderConsultState();
      }
      if (transcript.status === "transcript_ready" || transcript.status === "discarded") {
        stopConsultStatusPolling();
      }
    } catch (error) {
      stopConsultStatusPolling();
    }
  }, 4000);
}

async function loadConsultTranscript() {
  if (!doctorActiveConsult) return;
  try {
    const transcript = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/transcript`);
    renderConsultFallbackNotice(transcript.transcript_source, transcript.transcript_fallback_error);
    renderConsultTranscript(transcript.segments || []);
  } catch (error) {
    setDoctorConsultMessage(error.message);
  }
}

function renderConsultFallbackNotice(transcriptSource, fallbackError) {
  if (!doctorConsultFallbackNotice) return;
  if (transcriptSource === "live_fallback") {
    doctorConsultFallbackNotice.textContent =
      `Automated re-transcription failed, so this is the raw live capture instead of the higher-accuracy version` +
      (fallbackError ? ` (${fallbackError})` : "") + ".";
    doctorConsultFallbackNotice.classList.remove("hidden");
  } else {
    doctorConsultFallbackNotice.classList.add("hidden");
    doctorConsultFallbackNotice.textContent = "";
  }
}

function renderConsultTranscript(segments) {
  if (!doctorConsultTranscriptList) return;
  doctorConsultTranscriptList.replaceChildren();

  doctorConsultSegmentsById = {};
  segments.forEach((segment) => {
    if (segment.id) doctorConsultSegmentsById[segment.id] = segment;
  });

  if (!segments.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No transcript segments.";
    doctorConsultTranscriptList.appendChild(note);
    return;
  }

  segments.forEach((segment) => {
    const card = document.createElement("article");
    card.className = "admin-inline-card";
    const head = document.createElement("div");
    head.className = "admin-inline-card-head";
    const titleWrap = document.createElement("div");

    // Speaker label is itself the correction control — click to cycle
    // doctor -> patient -> unknown -> doctor. Per-segment fix for diarization drift
    // mid-conversation; "These look swapped" (above the list) is the cheaper bulk fix
    // for the whole mapping being backwards.
    const title = document.createElement("button");
    title.type = "button";
    title.className = "admin-inline-title clinical-note-speaker-btn";
    title.title = "Click to relabel this segment's speaker";
    title.textContent = speakerLabel(segment.speaker);
    if (segment.id) {
      title.addEventListener("click", () => cycleSegmentSpeaker(segment.id, segment.speaker));
    } else {
      title.disabled = true;
    }

    const meta = document.createElement("div");
    meta.className = "admin-inline-meta";
    meta.textContent = segment.text;
    titleWrap.append(title, meta);
    head.appendChild(titleWrap);
    card.appendChild(head);
    doctorConsultTranscriptList.appendChild(card);
  });
}

function speakerLabel(speaker) {
  return speaker === "doctor" ? "Doctor" : speaker === "patient" ? "Patient" : "Unknown speaker";
}

async function swapConsultSpeakers() {
  if (!doctorActiveConsult) return;
  setDoctorConsultMessage("");
  try {
    await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/transcript/swap-speakers`, { method: "POST" });
    await loadConsultTranscript();
  } catch (error) {
    setDoctorConsultMessage(error.message);
  }
}

const SEGMENT_SPEAKER_CYCLE = ["doctor", "patient", "unknown"];

async function cycleSegmentSpeaker(segmentId, currentSpeaker) {
  if (!doctorActiveConsult) return;
  const currentIndex = SEGMENT_SPEAKER_CYCLE.indexOf(currentSpeaker);
  const nextSpeaker = SEGMENT_SPEAKER_CYCLE[(currentIndex + 1) % SEGMENT_SPEAKER_CYCLE.length];
  setDoctorConsultMessage("");
  try {
    await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/transcript/segments/${segmentId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speaker: nextSpeaker }),
    });
    await loadConsultTranscript();
  } catch (error) {
    setDoctorConsultMessage(error.message);
  }
}

// ── SOAP clinical note (Part 3) ──────────────────────────────────────────────

const SOAP_FIELDS = ["subjective", "objective", "assessment", "plan"];
const SOAP_FIELD_LABELS = { subjective: "Subjective", objective: "Objective", assessment: "Assessment", plan: "Plan" };
const NOTE_STATUS_LABELS = { draft: "Draft", stale: "Stale — regenerate", signed: "Signed" };

function setDoctorNoteMessage(text) {
  if (!doctorNoteMessage) return;
  doctorNoteMessage.textContent = text || "";
  doctorNoteMessage.classList.toggle("hidden", !text);
}

function renderNoteFallbackNotice(sourceTranscriptType) {
  if (!doctorNoteFallbackNotice) return;
  if (sourceTranscriptType === "live_fallback") {
    doctorNoteFallbackNotice.textContent =
      "This note was generated from a live-only transcript — automated re-transcription failed for this consult, so the underlying transcript is lower-confidence and was never proofread by the batch pass.";
    doctorNoteFallbackNotice.classList.remove("hidden");
  } else {
    doctorNoteFallbackNotice.classList.add("hidden");
    doctorNoteFallbackNotice.textContent = "";
  }
}

function citationExcerpt(citationIds) {
  if (!Array.isArray(citationIds) || !citationIds.length) return "No citation for this field.";
  const lines = citationIds
    .map((id) => {
      const segment = doctorConsultSegmentsById[id];
      return segment ? `${speakerLabel(segment.speaker)}: "${segment.text}"` : null;
    })
    .filter(Boolean);
  return lines.length ? lines.join("\n") : "No citation for this field.";
}

// Shared by the editable draft form and the read-only signed view — citations and
// confidence flags are just as relevant once signed, so both render them identically;
// only whether the value is a <textarea> or plain text differs.
function buildNoteFieldRow(fieldKey, note, { readOnly }) {
  const wrap = document.createElement("div");
  wrap.className = "clinical-note-field";

  const head = document.createElement("div");
  head.className = "admin-inline-card-head";
  const label = document.createElement("span");
  label.className = "admin-inline-title";
  label.textContent = SOAP_FIELD_LABELS[fieldKey];
  head.appendChild(label);

  if (note.confidence_flags && note.confidence_flags[fieldKey]) {
    const flag = document.createElement("span");
    flag.className = "clinical-note-flag";
    flag.textContent = "Needs review";
    head.appendChild(flag);
  }
  wrap.appendChild(head);

  const fieldText = note[fieldKey] || "";
  if (readOnly) {
    const value = document.createElement("p");
    value.className = fieldText ? "clinical-note-value" : "clinical-note-value clinical-note-value--empty";
    // Distinct from a real (possibly short) entry — a signed note's empty field is a
    // fact about the visit, not a loading/error state, and can no longer be filled in
    // except via an addendum.
    value.textContent = fieldText || "Not addressed in this conversation.";
    wrap.appendChild(value);
  } else {
    const value = document.createElement("textarea");
    value.className = "clinical-note-textarea";
    value.rows = 3;
    value.dataset.field = fieldKey;
    value.value = fieldText;
    if (!fieldText) {
      // A genuinely empty field (nothing in the transcript to extract) must never look
      // like a loading/error state — the placeholder makes clear this is a prompt to
      // fill in, not saved content, and disappears the instant the doctor types
      // anything (e.g. an exam finding, diagnosis, or plan they gave/decided but never
      // said aloud during the recorded conversation).
      value.placeholder = "Not addressed in this conversation — add manually.";
    }
    wrap.appendChild(value);
  }

  const citations = (note.field_citations && note.field_citations[fieldKey]) || [];
  const citeBtn = document.createElement("button");
  citeBtn.type = "button";
  citeBtn.className = "secondary compact clinical-note-citation-btn";
  citeBtn.textContent = `Show citation${citations.length ? ` (${citations.length})` : ""}`;
  citeBtn.disabled = !citations.length;

  const citeBox = document.createElement("div");
  citeBox.className = "panel-note clinical-note-citation-box hidden";
  citeBox.textContent = citationExcerpt(citations);

  citeBtn.addEventListener("click", () => citeBox.classList.toggle("hidden"));

  wrap.append(citeBtn, citeBox);
  return wrap;
}

function renderNoteDraft(note) {
  if (!doctorNoteFieldsContainer) return;
  doctorNoteFieldsContainer.replaceChildren();
  SOAP_FIELDS.forEach((field) => {
    doctorNoteFieldsContainer.appendChild(buildNoteFieldRow(field, note, { readOnly: false }));
  });
  if (doctorNoteSignBtn) doctorNoteSignBtn.disabled = note.status === "stale";
}

function renderNoteSigned(note) {
  if (doctorNoteSignedFieldsContainer) {
    doctorNoteSignedFieldsContainer.replaceChildren();
    SOAP_FIELDS.forEach((field) => {
      doctorNoteSignedFieldsContainer.appendChild(buildNoteFieldRow(field, note, { readOnly: true }));
    });
  }

  if (!doctorNoteAddendaList) return;
  doctorNoteAddendaList.replaceChildren();
  const addenda = note.addenda || [];
  if (!addenda.length) {
    const empty = document.createElement("p");
    empty.className = "panel-note";
    empty.textContent = "No addenda yet.";
    doctorNoteAddendaList.appendChild(empty);
    return;
  }
  addenda.forEach((addendum) => {
    const card = document.createElement("article");
    card.className = "admin-inline-card";
    const content = document.createElement("div");
    content.className = "admin-inline-meta";
    content.textContent = addendum.content;
    const when = document.createElement("p");
    when.className = "panel-note";
    when.textContent = addendum.created_at ? new Date(addendum.created_at).toLocaleString() : "";
    card.append(content, when);
    doctorNoteAddendaList.appendChild(card);
  });
}

function renderSoapNote() {
  const note = doctorCurrentNote;
  const isSigned = !!note && note.status === "signed";

  doctorNoteGenerateRow?.classList.toggle("hidden", isSigned);
  doctorNoteGenerateConfirm?.classList.add("hidden");
  if (doctorNoteGenerateBtn) {
    doctorNoteGenerateBtn.textContent = note ? "Regenerate Clinical Note" : "Generate Clinical Note";
  }

  if (!note) {
    doctorNoteStatusBadge?.classList.add("hidden");
    doctorNoteDraftBlock?.classList.add("hidden");
    doctorNoteSignedBlock?.classList.add("hidden");
    doctorNoteFallbackNotice?.classList.add("hidden");
    return;
  }

  if (doctorNoteStatusBadge) {
    doctorNoteStatusBadge.textContent = NOTE_STATUS_LABELS[note.status] || note.status;
    const modifier = note.status === "signed" ? "is-completed" : note.status === "stale" ? "is-upcoming" : "";
    doctorNoteStatusBadge.className = `admin-status-pill ${modifier}`.trim();
    doctorNoteStatusBadge.classList.remove("hidden");
  }

  renderNoteFallbackNotice(note.source_transcript_type);

  doctorNoteDraftBlock?.classList.toggle("hidden", isSigned);
  doctorNoteSignedBlock?.classList.toggle("hidden", !isSigned);
  doctorNoteSignConfirm?.classList.add("hidden");
  doctorNoteAddendumForm?.classList.add("hidden");

  if (isSigned) {
    renderNoteSigned(note);
  } else {
    renderNoteDraft(note);
  }
}

async function loadSoapNote() {
  if (!doctorActiveConsult) return;
  try {
    doctorCurrentNote = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/soap`);
  } catch (error) {
    // A 404 just means no note has been generated yet — not a real error to surface.
    doctorCurrentNote = null;
    if (error.status && error.status !== 404) setDoctorNoteMessage(error.message);
  }
  renderSoapNote();
}

async function generateSoapNote() {
  if (!doctorActiveConsult) return;
  setDoctorNoteMessage("");
  try {
    doctorCurrentNote = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/soap/generate`, { method: "POST" });
    renderSoapNote();
  } catch (error) {
    setDoctorNoteMessage(error.message);
  }
}

function collectNoteFieldValues() {
  const values = {};
  doctorNoteFieldsContainer?.querySelectorAll("textarea[data-field]").forEach((el) => {
    values[el.dataset.field] = el.value;
  });
  return values;
}

async function saveSoapNote() {
  if (!doctorActiveConsult) return;
  setDoctorNoteMessage("");
  try {
    doctorCurrentNote = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/soap`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectNoteFieldValues()),
    });
    renderSoapNote();
  } catch (error) {
    setDoctorNoteMessage(error.message);
  }
}

async function confirmSignSoapNote() {
  if (!doctorActiveConsult) return;
  setDoctorNoteMessage("");
  try {
    doctorCurrentNote = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/soap/sign`, { method: "POST" });
    renderSoapNote();
  } catch (error) {
    setDoctorNoteMessage(error.message);
  }
}

async function saveNoteAddendum() {
  if (!doctorActiveConsult || !doctorNoteAddendumText) return;
  const content = doctorNoteAddendumText.value.trim();
  if (!content) return;
  setDoctorNoteMessage("");
  try {
    doctorCurrentNote = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/soap/addendum`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    doctorNoteAddendumText.value = "";
    renderSoapNote();
  } catch (error) {
    setDoctorNoteMessage(error.message);
  }
}

function buildNotePlainText(note) {
  const lines = SOAP_FIELDS.map(
    (field) => `${SOAP_FIELD_LABELS[field]}:\n${note[field] || "Not addressed in this conversation."}`
  );
  const addenda = note.addenda || [];
  if (addenda.length) {
    lines.push("Addenda:");
    addenda.forEach((addendum) => {
      const when = addendum.created_at ? new Date(addendum.created_at).toLocaleString() : "";
      lines.push(`- [${when}] ${addendum.content}`);
    });
  }
  return lines.join("\n\n");
}

async function copyTextWithFallback(text) {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text);
    return;
  }
  // Legacy fallback for browsers/contexts without navigator.clipboard — it requires a
  // secure context (HTTPS, or specifically localhost) and isn't available everywhere.
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    if (!document.execCommand("copy")) throw new Error("execCommand('copy') was rejected.");
  } finally {
    document.body.removeChild(textarea);
  }
}

async function copySignedNoteToClipboard() {
  if (!doctorCurrentNote || !doctorNoteCopyBtn) return;
  const text = buildNotePlainText(doctorCurrentNote);
  try {
    await copyTextWithFallback(text);
    const original = doctorNoteCopyBtn.textContent;
    doctorNoteCopyBtn.textContent = "Copied!";
    window.setTimeout(() => { doctorNoteCopyBtn.textContent = original; }, 1500);
  } catch (error) {
    setDoctorNoteMessage("Couldn't copy to clipboard — your browser may be blocking clipboard access on this connection.");
  }
}

async function startConsultForCurrentAppointment() {
  if (!doctorDetailAppointment) return;
  setDoctorConsultMessage("");
  try {
    const consult = await doctorAuthedJson("/doctor/consult/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ booking_id: doctorDetailAppointment.booking_id }),
    });
    doctorActiveConsult = consult;
    renderConsultState();
  } catch (error) {
    setDoctorConsultMessage(error.message);
  }
}

async function confirmConsultConsent() {
  if (!doctorActiveConsult) return;
  setDoctorConsultMessage("");
  try {
    const consult = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/consent`, { method: "POST" });
    doctorActiveConsult = consult;
    renderConsultState();
  } catch (error) {
    setDoctorConsultMessage(error.message);
  }
}

function buildConsultAudioWsUrl(consultationId, sampleRate) {
  return `${location.origin.replace(/^http/, "ws")}/doctor/consult/${encodeURIComponent(consultationId)}/audio?token=${encodeURIComponent(doctorAccessToken || "")}&sample_rate=${encodeURIComponent(sampleRate)}`;
}

function appendConsultPcm16Frame(float32Frame) {
  const pcm = new Int16Array(float32Frame.length);
  for (let i = 0; i < float32Frame.length; i++) {
    const sample = Math.max(-1, Math.min(1, float32Frame[i]));
    pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  if (consultSocket && consultSocket.readyState === WebSocket.OPEN) {
    consultSocket.send(pcm.buffer);
  } else {
    // ~128 samples/frame (a Web Audio render quantum) means 12 frames is only ~32ms
    // at 48kHz — far less than a real WS handshake (TLS + auth) takes, so audio
    // spoken while the socket is still connecting was getting silently dropped.
    // 750 frames covers a couple of seconds even at 48kHz, comfortably more at
    // lower sample rates, while still bounding memory if the socket never opens.
    consultPendingFrames.push(pcm.buffer);
    if (consultPendingFrames.length > 750) consultPendingFrames.shift();
  }
}

async function startConsultRecording(consultationId) {
  consultMicStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  consultAudioContext = new (window.AudioContext || window.webkitAudioContext)();
  if (consultAudioContext.state === "suspended") await consultAudioContext.resume();
  const sampleRate = consultAudioContext.sampleRate || 16000;

  consultSocket = new WebSocket(buildConsultAudioWsUrl(consultationId, sampleRate));
  consultSocket.binaryType = "arraybuffer";
  consultSocket.addEventListener("open", () => {
    consultPendingFrames.forEach((buf) => consultSocket.send(buf));
    consultPendingFrames = [];
  });
  consultSocket.addEventListener("error", () => {
    setDoctorConsultMessage("Recording connection error.");
  });

  await consultAudioContext.audioWorklet.addModule("/static/voice-worklet.js");
  consultWorkletNode = new AudioWorkletNode(consultAudioContext, "voice-capture-processor");
  const source = consultAudioContext.createMediaStreamSource(consultMicStream);
  source.connect(consultWorkletNode);
  let consultLevelFrameCounter = 0;
  consultWorkletNode.port.onmessage = (event) => {
    appendConsultPcm16Frame(event.data);
    // A worklet frame arrives roughly every ~3ms — updating the DOM that often would be
    // wasteful and imperceptible; throttle the visible level meter to ~every 5th frame.
    if (++consultLevelFrameCounter % 5 === 0) updateConsultLevelMeter(event.data);
  };
}

function updateConsultLevelMeter(float32Frame) {
  if (!doctorConsultLevelFill) return;
  let sumSquares = 0;
  for (let i = 0; i < float32Frame.length; i++) sumSquares += float32Frame[i] * float32Frame[i];
  const rms = Math.sqrt(sumSquares / float32Frame.length);
  const pct = Math.min(100, rms * 400); // tunable — not a calibrated meter, just visual feedback
  doctorConsultLevelFill.style.width = `${pct}%`;
}

function stopConsultRecording() {
  if (consultSocket) {
    if (consultSocket.readyState === WebSocket.OPEN) {
      try {
        consultSocket.send(new Uint8Array());
      } catch (error) {
        // ignore — socket may already be closing
      }
    }
    try {
      consultSocket.close();
    } catch (error) {
      // ignore
    }
    consultSocket = null;
  }
  consultPendingFrames = [];
  if (consultMicStream) {
    consultMicStream.getTracks().forEach((track) => track.stop());
    consultMicStream = null;
  }
  if (consultWorkletNode) {
    try {
      consultWorkletNode.disconnect();
    } catch (error) {
      // ignore
    }
    consultWorkletNode = null;
  }
  if (consultAudioContext) {
    try {
      consultAudioContext.close();
    } catch (error) {
      // ignore
    }
    consultAudioContext = null;
  }
  if (doctorConsultLevelFill) doctorConsultLevelFill.style.width = "0%";
}

async function beginConsultRecordingClick() {
  if (!doctorActiveConsult) return;
  setDoctorConsultMessage("");
  try {
    await startConsultRecording(doctorActiveConsult.id);
    playConsultTone("start");
    doctorRecordingStartedAtMs = Date.now();
    startRecordingTimer();
    doctorActiveConsult = { ...doctorActiveConsult, status: "recording" };
    renderConsultState();
  } catch (error) {
    setDoctorConsultMessage(error.message || "Could not access the microphone.");
  }
}

async function stopConsultRecordingClick() {
  // Also the handler for the orphaned-recording "End this recording" button — both
  // paths get the same audible end-of-recording confirmation.
  playConsultTone("end");
  stopConsultRecording();
  stopRecordingTimer();
  if (!doctorActiveConsult) return;
  setDoctorConsultMessage("");
  try {
    const consult = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/end`, { method: "POST" });
    doctorActiveConsult = consult;
    renderConsultState();
    if (consult.status === "ended" || consult.status === "transcribing") {
      startConsultStatusPolling();
    }
  } catch (error) {
    setDoctorConsultMessage(error.message);
  }
}

function playConsultTone(kind) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    const now = ctx.currentTime;
    const [f1, f2] = kind === "start" ? [440, 880] : [880, 440];
    osc.frequency.setValueAtTime(f1, now);
    osc.frequency.linearRampToValueAtTime(f2, now + 0.12);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.2, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);
    osc.start(now);
    osc.stop(now + 0.25);
    osc.onended = () => ctx.close();
  } catch (error) {
    // Sound is a nice-to-have — never let it block the recording start/stop flow.
  }
}

async function confirmDiscardConsult() {
  if (!doctorActiveConsult) return;
  setDoctorConsultMessage("");
  stopConsultRecording();
  stopConsultStatusPolling();
  try {
    const consult = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/discard`, { method: "POST" });
    doctorActiveConsult = consult;
    renderConsultState();
  } catch (error) {
    setDoctorConsultMessage(error.message);
  }
}

async function loadDoctorPatientsList() {
  if (doctorPatientsCount) doctorPatientsCount.textContent = "Loading...";
  try {
    const data = await doctorAuthedJson("/doctor/patients");
    doctorPatientsCache = Array.isArray(data.patients) ? data.patients : [];
    renderDoctorPatientsList();
    if (doctorPatientsCount) {
      doctorPatientsCount.textContent = `${doctorPatientsCache.length} patient${doctorPatientsCache.length === 1 ? "" : "s"}`;
    }
  } catch (error) {
    if (doctorPatientsCount) doctorPatientsCount.textContent = "Unable to load.";
  }
}

function renderDoctorPatientsList() {
  if (!doctorPatientsList) return;
  doctorPatientsList.replaceChildren();

  const term = doctorPatientSearchTerm.trim().toLowerCase();
  const filtered = term
    ? doctorPatientsCache.filter((p) =>
        [p.patient_name, p.email, p.mobile_number].some((v) => v && String(v).toLowerCase().includes(term))
      )
    : doctorPatientsCache;

  if (!filtered.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = doctorPatientsCache.length ? "No patients match your search." : "No patients yet.";
    doctorPatientsList.appendChild(note);
    return;
  }

  filtered.forEach((patient) => {
    const card = document.createElement("article");
    card.className = "admin-inline-card doctor-clickable-card";

    const head = document.createElement("div");
    head.className = "admin-inline-card-head";
    const titleWrap = document.createElement("div");
    const title = document.createElement("div");
    title.className = "admin-inline-title";
    title.textContent = patient.patient_name || "Unknown patient";
    const meta = document.createElement("div");
    meta.className = "admin-inline-meta";
    meta.textContent = `${patient.visit_count || 0} visit${patient.visit_count === 1 ? "" : "s"} · Last: ${formatDateTime(patient.last_visit)}`;
    titleWrap.append(title, meta);
    head.appendChild(titleWrap);
    card.appendChild(head);
    card.addEventListener("click", () => loadDoctorPatientDetail(patient.patient_id));
    doctorPatientsList.appendChild(card);
  });
}

async function loadDoctorPatientDetail(patientId) {
  try {
    const detail = await doctorAuthedJson(`/doctor/patients/${encodeURIComponent(patientId)}`);
    renderDoctorPatientDetail(detail);
  } catch (error) {
    if (doctorPatientsCount) doctorPatientsCount.textContent = error.message || "Unable to load patient.";
  }
}

function renderDoctorPatientDetail(detail) {
  if (!detail) return;
  if (doctorPatientDetailName) doctorPatientDetailName.textContent = detail.name || "Patient";

  if (doctorPatientDetailFields) {
    doctorPatientDetailFields.replaceChildren();
    const fields = [
      ["Age", detail.age != null ? String(detail.age) : "-"],
      ["Mobile", detail.mobile_number || "-"],
      ["Email", detail.email || "-"],
      ["Blood group", detail.blood_group || "-"],
      ["Health issues", detail.health_issues || "-"],
    ];
    fields.forEach(([label, value]) => {
      const field = document.createElement("div");
      field.className = "admin-field";
      const span = document.createElement("span");
      span.textContent = label;
      const strong = document.createElement("strong");
      strong.textContent = value;
      field.append(span, strong);
      doctorPatientDetailFields.appendChild(field);
    });
  }

  if (doctorPatientDetailVisits) {
    doctorPatientDetailVisits.replaceChildren();
    const visits = Array.isArray(detail.visits) ? detail.visits : [];
    if (!visits.length) {
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = "No visits on record.";
      doctorPatientDetailVisits.appendChild(note);
    } else {
      visits.forEach((visit) => {
        const card = document.createElement("article");
        card.className = "admin-inline-card";
        const head = document.createElement("div");
        head.className = "admin-inline-card-head";
        const titleWrap = document.createElement("div");
        const title = document.createElement("div");
        title.className = "admin-inline-title";
        title.textContent = formatDateTime(visit.start_time);
        const meta = document.createElement("div");
        meta.className = "admin-inline-meta";
        meta.textContent = `${visit.department || "Department"} · No clinical note yet`;
        titleWrap.append(title, meta);
        const badge = document.createElement("span");
        badge.className = `admin-status-pill is-${visit.status || "completed"}`;
        badge.textContent = visit.status || "";
        head.append(titleWrap, badge);
        card.appendChild(head);
        doctorPatientDetailVisits.appendChild(card);
      });
    }
  }

  [doctorOverviewPane, doctorUpcomingPane, doctorPastPane, doctorPatientsPane, doctorAppointmentDetailPane].forEach((pane) =>
    pane?.classList.add("hidden")
  );
  doctorPatientDetailPane?.classList.remove("hidden");
}

function renderDoctorDashboard(doctor) {
  if (!doctor) return;
  if (doctorProfileName) doctorProfileName.textContent = doctor.name || "-";
  if (doctorProfileDepartment) doctorProfileDepartment.textContent = doctor.department || "-";
  if (doctorProfileExperience) {
    doctorProfileExperience.textContent = doctor.experience_years != null ? `${doctor.experience_years} years` : "-";
  }
  if (doctorProfileMfaStatus) doctorProfileMfaStatus.textContent = doctor.mfa_enabled ? "Enabled" : "Not enabled";
  if (doctorLowRecoveryNoticePending && doctorRecoveryLowNotice) {
    doctorRecoveryLowNotice.textContent =
      "You signed in with a recovery code. Consider re-enrolling MFA soon if you're running low on codes. (Tap to dismiss.)";
    doctorRecoveryLowNotice.classList.remove("hidden");
    doctorLowRecoveryNoticePending = false;
  }
}

function setDoctorOnboardingMessage(text) {
  if (doctorOnboardingMessage) doctorOnboardingMessage.textContent = text || "";
}

function showDoctorOnboardingStep(step) {
  doctorSetPasswordForm?.classList.toggle("hidden", step !== "password");
  doctorMfaEnrollStep?.classList.toggle("hidden", step !== "enroll");
  doctorRecoveryCodesStep?.classList.toggle("hidden", step !== "recovery");
}

function doctorEnrollmentErrorMessage(error) {
  const message = error?.message || "";
  if (message.includes("MFA authentication token")) {
    return "Your enrollment link has expired. Please contact your admin for a new link.";
  }
  return message || "Something went wrong. Please try again.";
}

function initDoctorInviteRouting() {
  if (window.location.pathname !== "/doctor/set-password") return false;
  const token = new URLSearchParams(window.location.search).get("token");
  authView?.classList.add("hidden");
  doctorOnboardingView?.classList.remove("hidden");
  showDoctorOnboardingStep("password");
  if (!token) {
    setDoctorOnboardingMessage(
      "This invite link is missing required details. Please ask your admin to resend your invite."
    );
    doctorSetPasswordForm?.classList.add("hidden");
    return true;
  }
  pendingInviteToken = token;
  return true;
}

async function startDoctorMfaEnrollment() {
  setDoctorOnboardingMessage("");
  try {
    const data = await postJson("/doctor/auth/mfa/enroll", {}, doctorMfaEnrollmentToken);
    if (doctorMfaProvisioningUri) doctorMfaProvisioningUri.textContent = data.provisioning_uri;
    if (doctorMfaQrContainer) {
      doctorMfaQrContainer.innerHTML = "";
      try {
        const qr = qrcode(0, "M");
        qr.addData(data.provisioning_uri);
        qr.make();
        doctorMfaQrContainer.innerHTML = qr.createSvgTag(4);
      } catch (qrError) {
        // Manual code text above still lets the doctor complete enrollment.
      }
    }
  } catch (error) {
    setDoctorOnboardingMessage(doctorEnrollmentErrorMessage(error));
  }
}

function renderRecoveryCodes(codes) {
  doctorRecoveryCodesInMemory = codes;
  if (doctorRecoveryCodesList) {
    doctorRecoveryCodesList.replaceChildren();
    codes.forEach((code) => {
      const li = document.createElement("li");
      li.textContent = code;
      doctorRecoveryCodesList.appendChild(li);
    });
  }
  if (doctorRecoveryAckCheckbox) doctorRecoveryAckCheckbox.checked = false;
  if (doctorRecoveryContinueBtn) doctorRecoveryContinueBtn.disabled = true;
}

function downloadRecoveryCodesAsText(codes) {
  const content = ["Hospital Portal — MFA recovery codes", "Each code is single-use.", "", ...codes].join("\n");
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "hospital-portal-recovery-codes.txt";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
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

async function tryRefreshPatientToken() {
  if (!refreshToken) return false;
  try {
    const data = await postJson("/auth/refresh", { refresh_token: refreshToken });
    accessToken = data.access_token;
    refreshToken = data.refresh_token;
    localStorage.setItem("accessToken", accessToken);
    localStorage.setItem("refreshToken", refreshToken);
    return true;
  } catch (error) {
    return false;
  }
}

async function tryRefreshAdminToken() {
  if (!adminRefreshToken) return false;
  try {
    const data = await postJson("/auth/refresh", { refresh_token: adminRefreshToken });
    adminAccessToken = data.access_token;
    adminRefreshToken = data.refresh_token;
    localStorage.setItem("adminAccessToken", adminAccessToken);
    localStorage.setItem("adminRefreshToken", adminRefreshToken);
    return true;
  } catch (error) {
    return false;
  }
}

async function authedJson(url, options = {}) {
  const timeoutMs = options.timeoutMs ?? 15000;

  const attempt = async () => {
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
      return { response, data };
    } finally {
      window.clearTimeout(timeoutId);
    }
  };

  try {
    let refreshed = false;
    let { response, data } = await attempt();
    if (!response.ok && response.status === 401) {
      refreshed = await tryRefreshPatientToken();
      if (refreshed) {
        ({ response, data } = await attempt());
      }
    }
    if (!response.ok) {
      // A 401 that survives a successful refresh isn't an expired session (we just
      // proved the token is good) — it's the endpoint's own domain rejection (e.g. wrong
      // current password on /auth/change-password). Only treat 401 as "log out" when we
      // never got a fresh token to retry with.
      if (response.status === 401 && !refreshed) {
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
  }
}

async function adminAuthedJson(url, options = {}) {
  const timeoutMs = options.timeoutMs ?? 15000;

  const attempt = async () => {
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
      return { response, data };
    } finally {
      window.clearTimeout(timeoutId);
    }
  };

  try {
    let refreshed = false;
    let { response, data } = await attempt();
    if (!response.ok && response.status === 401) {
      refreshed = await tryRefreshAdminToken();
      if (refreshed) {
        ({ response, data } = await attempt());
      }
    }
    if (!response.ok) {
      if (response.status === 401 && !refreshed) {
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
  if (secChangePasswordCountdownCancel) {
    secChangePasswordCountdownCancel();
    secChangePasswordCountdownCancel = null;
  }
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
  // Patient appointment timestamps are India-local values or explicitly
  // marked +05:30 by the backend. Always display them in IST.
  const raw = String(value);
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
  const parsed = new Date(hasTimezone ? raw : `${raw}+05:30`);
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
    timeZone: "Asia/Kolkata",
  });
}

function formatBookingDateTime(value) {
  if (!value) {
    return "-";
  }
  const raw = String(value);
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
  const parsed = new Date(hasTimezone ? raw : `${raw}+05:30`);
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
    timeZone: "Asia/Kolkata",
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
  title.textContent = `${patientUi("department")} > ${patientUi("doctor")} > ${patientUi("appointment")}`;

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
  departmentTitle.textContent = `1. ${patientUi("department")}`;
  const departmentNote = document.createElement("p");
  departmentNote.className = "panel-note";
  departmentNote.textContent = "Pick the department that best matches the concern.";
  const departmentSelect = document.createElement("select");
  departmentSelect.innerHTML = `<option value="">${patientUi("loadingDepartments")}</option>`;
  departmentCard.append(departmentTitle, departmentNote, departmentSelect);

  const doctorCard = document.createElement("article");
  doctorCard.className = "glass-panel booking-step-card";
  const doctorTitle = document.createElement("h3");
  doctorTitle.textContent = `2. ${patientUi("doctor")}`;
  const doctorNote = document.createElement("p");
  doctorNote.className = "panel-note";
  doctorNote.textContent = "Available doctors will appear after a department is chosen.";
  const doctorList = document.createElement("div");
  doctorList.className = "booking-list";
  doctorCard.append(doctorTitle, doctorNote, doctorList);

  const slotCard = document.createElement("article");
  slotCard.className = "glass-panel booking-step-card";
  const slotTitle = document.createElement("h3");
  slotTitle.textContent = `3. ${patientUi("appointment")}`;
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
  actionTitle.textContent = patientUi("bookingSummary");
  const actionText = document.createElement("p");
  actionText.className = "panel-note";
  actionText.textContent = "Select a slot to enable booking.";
  const actionMeta = document.createElement("div");
  actionMeta.className = "booking-meta";
  const actionButton = document.createElement("button");
  actionButton.type = "button";
  actionButton.textContent = patientUi("bookSlot");
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
      ? patientUi("bookFromHere")
      : patientUi("selectSlot");
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
      note.textContent = patientUi("noDepartments");
      doctorList.appendChild(note);
      return;
    }

    if (!bookingStudioState.doctors.length) {
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = patientUi("selectDepartment");
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
      title.textContent = doctor.display_name || doctor.doctor_name;

      const department = document.createElement("span");
      department.className = "booking-card-meta";
      department.textContent = doctor.department || bookingStudioState.department;

      const experience = document.createElement("span");
      experience.className = "booking-card-meta";
      experience.textContent = formatDoctorExperience(doctor);

      const availability = document.createElement("span");
      availability.className = "booking-card-meta";
      availability.textContent = `${doctor.available_slot_count || 0} ${patientUi("openSlots")}`;

      const nextSlot = document.createElement("span");
      nextSlot.className = "booking-card-meta";
      nextSlot.textContent = doctor.next_available_time
        ? `Next: ${formatDateTime(doctor.next_available_time)}`
        : patientUi("nextSlot");

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
      note.textContent = patientUi("pickDoctor");
      slotList.appendChild(note);
      return;
    }

    if (!bookingStudioState.slots.length) {
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = patientUi("noSlots");
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
    loading.textContent = patientUi("loadingDoctors");
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
    loading.textContent = patientUi("loadingSlots");
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

  const visibleBookings = [...bookings]
    .sort((left, right) => {
      const leftTime = new Date(left?.time || left?.start_time || 0).getTime();
      const rightTime = new Date(right?.time || right?.start_time || 0).getTime();
      return rightTime - leftTime;
    })
    .slice(0, 3);

  visibleBookings.forEach((booking) => {
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

function renderAppointmentsPageList(container, bookings, { upcoming = false } = {}) {
  if (!container) return;
  container.replaceChildren();

  if (!Array.isArray(bookings) || !bookings.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = upcoming
      ? "No upcoming appointments found."
      : "No past appointments found.";
    container.appendChild(note);
    return;
  }

  bookings.forEach((booking) => {
    const item = document.createElement("article");
    item.className = "booking-item";
    item.appendChild(bookingSummary(booking));

    if (upcoming) {
      const actions = document.createElement("div");
      actions.className = "booking-actions";

      if (booking.can_modify) {
        const cancelButton = document.createElement("button");
        cancelButton.className = "secondary compact";
        cancelButton.type = "button";
        cancelButton.textContent = "Cancel";
        cancelButton.addEventListener("click", () => cancelBooking(booking.booking_id));

        const changeButton = document.createElement("button");
        changeButton.className = "secondary compact";
        changeButton.type = "button";
        changeButton.textContent = "Change date";
        changeButton.addEventListener("click", () => showRescheduleControls(item, booking));
        actions.append(cancelButton, changeButton);
      } else {
        const note = document.createElement("p");
        note.className = "panel-note";
        note.textContent = "Changes are locked because this appointment is within 24 hours.";
        actions.appendChild(note);
      }

      item.appendChild(actions);
    }

    container.appendChild(item);
  });
}

async function refreshAppointmentsPage() {
  const upcomingList = document.getElementById("upcomingApptList");
  const pastList = document.getElementById("pastApptList");
  if (!upcomingList || !pastList) return;

  const loading = document.createElement("p");
  loading.className = "panel-note";
  loading.textContent = "Loading appointments...";
  upcomingList.replaceChildren(loading);
  pastList.replaceChildren();

  try {
    const [upcomingData, pastData] = await Promise.all([
      authedJson("/appointments/upcoming"),
      authedJson("/appointments/previous"),
    ]);
    renderAppointmentsPageList(upcomingList, upcomingData.bookings || [], { upcoming: true });
    renderAppointmentsPageList(pastList, pastData.bookings || []);
  } catch (error) {
    upcomingList.replaceChildren();
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = error.message || "Unable to load appointments.";
    upcomingList.appendChild(note);
    renderAppointmentsPageList(pastList, []);
  }
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

function stripMarkdownForPreview(value) {
  if (!value) return "";
  return value
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/^[-•]\s+/gm, "")
    .replace(/^---+$/gm, "")
    .replace(/\s*\n\s*/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
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
  summary.textContent =
    stripMarkdownForPreview(formatClinicalSummary(appointment.clinical_summary)) || "No clinical summary submitted.";

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

  if (appointment.patient_id) {
    const actions = document.createElement("div");
    actions.className = "admin-inline-actions";

    const resetMfaBtn = document.createElement("button");
    resetMfaBtn.type = "button";
    resetMfaBtn.className = "secondary compact";
    resetMfaBtn.textContent = "Reset MFA";
    resetMfaBtn.addEventListener("click", async () => {
      try {
        await resetPatientMfa(appointment.patient_id);
        showAdminToast("MFA reset.");
        await loadAdminAppointments(true);
      } catch (error) {
        showAdminToast(error.message, "error", 2500);
      }
    });
    actions.appendChild(resetMfaBtn);

    const unlockBtn = document.createElement("button");
    unlockBtn.type = "button";
    unlockBtn.className = "secondary compact";
    unlockBtn.textContent = "Unlock login";
    unlockBtn.addEventListener("click", async () => {
      try {
        await unlockPatientLogin(appointment.patient_id);
        showAdminToast("Login unlocked.");
      } catch (error) {
        showAdminToast(error.message, "error", 2500);
      }
    });
    actions.appendChild(unlockBtn);

    item.appendChild(actions);
  }

  return item;
}

function renderAdminAppointments() {
  if (!adminAppointmentsList) return;

  const selectedDoctorId = adminDoctorFilter?.value || "";
  const visibleAppointments = (adminAppointments || []).filter(
    (appointment) => !selectedDoctorId || appointment.doctor_id === selectedDoctorId
  );

  updateAdminStats(visibleAppointments);

  const filtered = adminSelectedStatus === "all"
    ? visibleAppointments
    : visibleAppointments.filter((appointment) => adminAppointmentState(appointment) === adminSelectedStatus);
  // Past appointments show most recent first; upcoming/all stay soonest-first.
  const sortDirection = adminSelectedStatus === "past" ? -1 : 1;
  filtered.sort(
    (left, right) =>
      sortDirection *
      (new Date(left.time || left.appointment_time || 0) - new Date(right.time || right.appointment_time || 0))
  );
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

// Patient-facing UI labels use the same active language returned by /chat.
// Backend IDs and enum values remain unchanged.
const PATIENT_UI_TEXT = {
  en: { department: "Department", doctor: "Doctor", appointment: "Appointment", bookingSummary: "Booking summary", bookSlot: "Book selected slot", chooseDepartment: "Choose a department", loadingDepartments: "Loading departments...", loadingDoctors: "Loading doctors...", loadingSlots: "Loading slots...", today: "Today", tomorrow: "Tomorrow", bookFromHere: "You can book immediately from here.", selectSlot: "Select a slot to enable booking.", noDepartments: "No departments are currently available.", selectDepartment: "Select a department to see available doctors.", pickDoctor: "Pick a doctor to view slots.", noSlots: "No slots are available for this doctor on the selected date.", nextSlot: "Next slot not listed", openSlots: "open slots", experience: "experience" },
  hi: { department: "विभाग", doctor: "डॉक्टर", appointment: "अपॉइंटमेंट", bookingSummary: "बुकिंग सारांश", bookSlot: "चुना हुआ स्लॉट बुक करें", chooseDepartment: "विभाग चुनें", loadingDepartments: "विभाग लोड हो रहे हैं...", loadingDoctors: "डॉक्टर लोड हो रहे हैं...", loadingSlots: "स्लॉट लोड हो रहे हैं...", today: "आज", tomorrow: "कल", bookFromHere: "आप यहीं से तुरंत बुक कर सकते हैं।", selectSlot: "बुकिंग शुरू करने के लिए स्लॉट चुनें।", noDepartments: "अभी कोई विभाग उपलब्ध नहीं है।", selectDepartment: "उपलब्ध डॉक्टर देखने के लिए विभाग चुनें।", pickDoctor: "स्लॉट देखने के लिए डॉक्टर चुनें।", noSlots: "चुनी गई तारीख पर इस डॉक्टर के लिए कोई स्लॉट उपलब्ध नहीं है।", nextSlot: "अगला स्लॉट सूचीबद्ध नहीं है", openSlots: "खुले स्लॉट", experience: "अनुभव" },
  te: { department: "విభాగం", doctor: "వైద్యుడు", appointment: "అపాయింట్‌మెంట్", bookingSummary: "బుకింగ్ సారాంశం", bookSlot: "ఎంచుకున్న సమయాన్ని బుక్ చేయండి", chooseDepartment: "విభాగాన్ని ఎంచుకోండి", loadingDepartments: "విభాగాలు లోడ్ అవుతున్నాయి...", loadingDoctors: "వైద్యులు లోడ్ అవుతున్నారు...", loadingSlots: "సమయాలు లోడ్ అవుతున్నాయి...", today: "ఈరోజు", tomorrow: "రేపు", bookFromHere: "మీరు ఇక్కడి నుంచే వెంటనే బుక్ చేయవచ్చు.", selectSlot: "బుకింగ్ ప్రారంభించడానికి సమయాన్ని ఎంచుకోండి.", noDepartments: "ప్రస్తుతం విభాగాలు అందుబాటులో లేవు.", selectDepartment: "అందుబాటులో ఉన్న వైద్యులను చూడటానికి విభాగాన్ని ఎంచుకోండి.", pickDoctor: "సమయాలను చూడటానికి వైద్యుడిని ఎంచుకోండి.", noSlots: "ఎంచుకున్న తేదీన ఈ వైద్యుడికి సమయాలు అందుబాటులో లేవు.", nextSlot: "తదుపరి సమయం జాబితాలో లేదు", openSlots: "అందుబాటులో ఉన్న సమయాలు", experience: "అనుభవం" },
  ta: { department: "துறை", doctor: "மருத்துவர்", appointment: "அப்பாயின்ட்மென்ட்", bookingSummary: "பதிவு சுருக்கம்", bookSlot: "தேர்ந்தெடுத்த நேரத்தைப் பதிவு செய்க", chooseDepartment: "துறையைத் தேர்ந்தெடுக்கவும்", loadingDepartments: "துறைகள் ஏற்றப்படுகின்றன...", loadingDoctors: "மருத்துவர்கள் ஏற்றப்படுகின்றனர்...", loadingSlots: "நேரங்கள் ஏற்றப்படுகின்றன...", today: "இன்று", tomorrow: "நாளை", bookFromHere: "இங்கிருந்தே உடனடியாக பதிவு செய்யலாம்.", selectSlot: "பதிவு செய்ய ஒரு நேரத்தைத் தேர்ந்தெடுக்கவும்.", noDepartments: "தற்போது துறைகள் இல்லை.", selectDepartment: "மருத்துவர்களைக் காண ஒரு துறையைத் தேர்ந்தெடுக்கவும்.", pickDoctor: "நேரங்களைக் காண ஒரு மருத்துவரைத் தேர்ந்தெடுக்கவும்.", noSlots: "தேர்ந்தெடுத்த தேதியில் இந்த மருத்துவருக்கு நேரங்கள் இல்லை.", nextSlot: "அடுத்த நேரம் பட்டியலிடப்படவில்லை", openSlots: "கிடைக்கும் நேரங்கள்", experience: "அனுபவம்" },
  kn: { department: "ವಿಭಾಗ", doctor: "ವೈದ್ಯರು", appointment: "ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್", bookingSummary: "ಬುಕಿಂಗ್ ಸಾರಾಂಶ", bookSlot: "ಆಯ್ಕೆ ಮಾಡಿದ ಸಮಯವನ್ನು ಬುಕ್ ಮಾಡಿ", chooseDepartment: "ವಿಭಾಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ", loadingDepartments: "ವಿಭಾಗಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ...", loadingDoctors: "ವೈದ್ಯರನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ...", loadingSlots: "ಸಮಯಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ...", today: "ಇಂದು", tomorrow: "ನಾಳೆ", bookFromHere: "ಇಲ್ಲಿಂದಲೇ ತಕ್ಷಣ ಬುಕ್ ಮಾಡಬಹುದು.", selectSlot: "ಬುಕ್ ಮಾಡಲು ಸಮಯವನ್ನು ಆಯ್ಕೆಮಾಡಿ.", noDepartments: "ಪ್ರಸ್ತುತ ಯಾವುದೇ ವಿಭಾಗಗಳು ಲಭ್ಯವಿಲ್ಲ.", selectDepartment: "ಲಭ್ಯವಿರುವ ವೈದ್ಯರನ್ನು ನೋಡಲು ವಿಭಾಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ.", pickDoctor: "ಸಮಯಗಳನ್ನು ನೋಡಲು ವೈದ್ಯರನ್ನು ಆಯ್ಕೆಮಾಡಿ.", noSlots: "ಆಯ್ಕೆ ಮಾಡಿದ ದಿನಾಂಕದಂದು ಈ ವೈದ್ಯರಿಗೆ ಸಮಯಗಳು ಲಭ್ಯವಿಲ್ಲ.", nextSlot: "ಮುಂದಿನ ಸಮಯ ಪಟ್ಟಿ ಮಾಡಲಾಗಿಲ್ಲ", openSlots: "ಲಭ್ಯವಿರುವ ಸಮಯಗಳು", experience: "ಅನುಭವ" },
  mr: { department: "विभाग", doctor: "डॉक्टर", appointment: "अपॉइंटमेंट", bookingSummary: "बुकिंग सारांश", bookSlot: "निवडलेला स्लॉट बुक करा", chooseDepartment: "विभाग निवडा", loadingDepartments: "विभाग लोड होत आहेत...", loadingDoctors: "डॉक्टर लोड होत आहेत...", loadingSlots: "स्लॉट लोड होत आहेत...", today: "आज", tomorrow: "उद्या", bookFromHere: "तुम्ही येथून लगेच बुक करू शकता.", selectSlot: "बुक करण्यासाठी स्लॉट निवडा.", noDepartments: "सध्या कोणतेही विभाग उपलब्ध नाहीत.", selectDepartment: "उपलब्ध डॉक्टर पाहण्यासाठी विभाग निवडा.", pickDoctor: "स्लॉट पाहण्यासाठी डॉक्टर निवडा.", noSlots: "निवडलेल्या तारखेला या डॉक्टरसाठी स्लॉट उपलब्ध नाहीत.", nextSlot: "पुढील स्लॉट सूचीबद्ध नाही", openSlots: "उपलब्ध स्लॉट", experience: "अनुभव" },
  bn: { department: "বিভাগ", doctor: "ডাক্তার", appointment: "অ্যাপয়েন্টমেন্ট", bookingSummary: "বুকিং সারাংশ", bookSlot: "নির্বাচিত সময় বুক করুন", chooseDepartment: "একটি বিভাগ বেছে নিন", loadingDepartments: "বিভাগ লোড হচ্ছে...", loadingDoctors: "ডাক্তার লোড হচ্ছে...", loadingSlots: "সময় লোড হচ্ছে...", today: "আজ", tomorrow: "আগামীকাল", bookFromHere: "এখান থেকেই বুক করতে পারেন।", selectSlot: "বুক করতে একটি সময় বেছে নিন।", noDepartments: "এখন কোনো বিভাগ নেই।", selectDepartment: "ডাক্তার দেখতে একটি বিভাগ বেছে নিন।", pickDoctor: "সময় দেখতে একজন ডাক্তার বেছে নিন।", noSlots: "নির্বাচিত তারিখে এই ডাক্তারের কোনো সময় নেই।", nextSlot: "পরবর্তী সময় তালিকাভুক্ত নয়", openSlots: "খোলা সময়", experience: "অভিজ্ঞতা" },
  gu: { department: "વિભાગ", doctor: "ડૉક્ટર", appointment: "એપોઇન્ટમેન્ટ", bookingSummary: "બુકિંગ સારાંશ", bookSlot: "પસંદ કરેલો સમય બુક કરો", chooseDepartment: "વિભાગ પસંદ કરો", loadingDepartments: "વિભાગો લોડ થઈ રહ્યા છે...", loadingDoctors: "ડૉક્ટરો લોડ થઈ રહ્યા છે...", loadingSlots: "સમય લોડ થઈ રહ્યા છે...", today: "આજે", tomorrow: "કાલે", bookFromHere: "તમે અહીંથી તરત બુક કરી શકો છો.", selectSlot: "બુક કરવા માટે સમય પસંદ કરો.", noDepartments: "હાલ કોઈ વિભાગ ઉપલબ્ધ નથી.", selectDepartment: "ઉપલબ્ધ ડૉક્ટરો જોવા માટે વિભાગ પસંદ કરો.", pickDoctor: "સમય જોવા માટે ડૉક્ટર પસંદ કરો.", noSlots: "પસંદ કરેલી તારીખે આ ડૉક્ટર માટે સમય ઉપલબ્ધ નથી.", nextSlot: "આગળનો સમય સૂચિબદ્ધ નથી", openSlots: "ખુલ્લા સમય", experience: "અનુભવ" },
};

function activePatientLanguage() {
  const code = state?.active_language || state?.preferred_language || "en";
  return PATIENT_UI_TEXT[code] ? code : "en";
}

function patientUi(key) {
  return PATIENT_UI_TEXT[activePatientLanguage()][key] || PATIENT_UI_TEXT.en[key] || key;
}

const PATIENT_ACTION_TEXT = {
  en: { noAppointment: "No appointment" }, hi: { noAppointment: "कोई अपॉइंटमेंट नहीं" },
  te: { noAppointment: "అపాయింట్‌మెంట్ వద్దు" }, ta: { noAppointment: "அப்பாயிண்ட்மெண்ட் வேண்டாம்" },
  kn: { noAppointment: "ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಡ" }, mr: { noAppointment: "अपॉइंटमेंट नको" },
  bn: { noAppointment: "অ্যাপয়েন্টমেন্ট নয়" }, gu: { noAppointment: "એપોઇન્ટમેન્ટ નથી" },
};

function patientAction(key) {
  return PATIENT_ACTION_TEXT[activePatientLanguage()]?.[key] || PATIENT_ACTION_TEXT.en[key] || key;
}

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

    head.append(titleWrap, badge, renderDoctorLoginBadge(doctor));
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
    card.appendChild(renderDoctorAccountActions(doctor));
    adminDoctorsList.appendChild(card);
  });
}

const DOCTOR_LOGIN_STATUS_LABELS = {
  not_invited: "Login: No account",
  invited: "Login: Invited",
  active: "Login: Active",
  mfa_enrolled: "Login: MFA Enrolled",
  locked: "Login: Locked",
};

const DOCTOR_LOGIN_STATUS_PILL_CLASS = {
  not_invited: "",
  invited: "",
  active: "is-upcoming",
  mfa_enrolled: "is-upcoming",
  locked: "is-cancelled",
};

function renderDoctorLoginBadge(doctor) {
  const badge = document.createElement("span");
  const status = doctor.login_status || "not_invited";
  const modifier = DOCTOR_LOGIN_STATUS_PILL_CLASS[status] || "";
  badge.className = `admin-status-pill ${modifier}`.trim();
  badge.textContent = DOCTOR_LOGIN_STATUS_LABELS[status] || "Login: Unknown";
  return badge;
}

async function sendDoctorInvite(doctorId, email, path) {
  return adminAuthedJson(`/admin/doctors/${doctorId}/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

async function sendDoctorPasswordReset(doctorId, email) {
  return adminAuthedJson(`/admin/doctors/${doctorId}/reset-invite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, confirm_reset: true }),
  });
}

async function unlockDoctorAccount(doctorId) {
  return adminAuthedJson(`/admin/doctors/${doctorId}/unlock`, { method: "POST" });
}

async function resetPatientMfa(targetPatientId) {
  return adminAuthedJson(`/admin/patients/${targetPatientId}/mfa/reset`, { method: "POST" });
}

async function unlockPatientLogin(targetPatientId) {
  return adminAuthedJson(`/admin/patients/${targetPatientId}/unlock`, { method: "POST" });
}

function renderDoctorResetConfirm(doctor, resetBtn) {
  const confirmWrap = document.createElement("div");
  confirmWrap.className = "admin-inline-confirm";

  const hint = document.createElement("p");
  hint.className = "panel-note";
  hint.textContent = `Type ${doctor.account_email || "the doctor's email"} to confirm.`;

  const input = document.createElement("input");
  input.type = "email";
  input.placeholder = doctor.account_email || "Confirm email";
  input.className = "admin-inline-email-input";

  const actionsRow = document.createElement("div");
  actionsRow.className = "admin-inline-actions";

  const confirmBtn = document.createElement("button");
  confirmBtn.type = "button";
  confirmBtn.className = "compact";
  confirmBtn.textContent = "Confirm & Send";
  confirmBtn.disabled = true;

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "secondary compact";
  cancelBtn.textContent = "Cancel";

  input.addEventListener("input", () => {
    const typed = input.value.trim().toLowerCase();
    const expected = (doctor.account_email || "").trim().toLowerCase();
    confirmBtn.disabled = !typed || typed !== expected;
  });

  confirmBtn.addEventListener("click", async () => {
    try {
      await sendDoctorPasswordReset(doctor.doctor_id, doctor.account_email);
      showAdminToast("Password reset invite sent.");
      await loadAdminManagement(true);
    } catch (error) {
      showAdminToast(error.message, "error", 2500);
    }
  });

  cancelBtn.addEventListener("click", () => {
    confirmWrap.remove();
    if (resetBtn) resetBtn.disabled = false;
  });

  actionsRow.append(confirmBtn, cancelBtn);
  confirmWrap.append(hint, input, actionsRow);
  return confirmWrap;
}

function renderDoctorAccountActions(doctor) {
  const wrap = document.createElement("div");
  wrap.className = "admin-inline-actions";

  if (doctor.invite_action === "invite") {
    const emailInput = document.createElement("input");
    emailInput.type = "email";
    emailInput.placeholder = "Doctor's email";
    emailInput.className = "admin-inline-email-input";

    const sendBtn = document.createElement("button");
    sendBtn.type = "button";
    sendBtn.className = "secondary compact";
    sendBtn.textContent = "Send Invite";
    sendBtn.addEventListener("click", async () => {
      const email = emailInput.value.trim();
      if (!email) {
        showAdminToast("Enter the doctor's email first.", "error", 2500);
        return;
      }
      try {
        await sendDoctorInvite(doctor.doctor_id, email, "invite");
        showAdminToast("Invite sent.");
        await loadAdminManagement(true);
      } catch (error) {
        showAdminToast(error.message, "error", 2500);
      }
    });

    wrap.append(emailInput, sendBtn);
    return wrap;
  }

  if (doctor.invite_action === "resend") {
    const resendBtn = document.createElement("button");
    resendBtn.type = "button";
    resendBtn.className = "secondary compact";
    resendBtn.textContent = "Resend Invite";
    resendBtn.addEventListener("click", async () => {
      try {
        await sendDoctorInvite(doctor.doctor_id, doctor.account_email, "resend-invite");
        showAdminToast("Invite resent.");
        await loadAdminManagement(true);
      } catch (error) {
        showAdminToast(error.message, "error", 2500);
      }
    });
    wrap.appendChild(resendBtn);
  }

  if (doctor.invite_action === "reset") {
    const resetBtn = document.createElement("button");
    resetBtn.type = "button";
    resetBtn.className = "secondary compact";
    resetBtn.textContent = "Send Password Reset";
    resetBtn.addEventListener("click", () => {
      wrap.appendChild(renderDoctorResetConfirm(doctor, resetBtn));
      resetBtn.disabled = true;
    });
    wrap.appendChild(resetBtn);
  }

  if (doctor.login_status === "locked") {
    const unlockBtn = document.createElement("button");
    unlockBtn.type = "button";
    unlockBtn.className = "secondary compact";
    unlockBtn.textContent = "Unlock";
    unlockBtn.addEventListener("click", async () => {
      try {
        await unlockDoctorAccount(doctor.doctor_id);
        showAdminToast("Account unlocked.");
        await loadAdminManagement(true);
      } catch (error) {
        showAdminToast(error.message, "error", 2500);
      }
    });
    wrap.appendChild(unlockBtn);
  }

  return wrap;
}

function renderAdminAuditDoctorOptions() {
  if (!adminAuditDoctorFilter) return;
  const currentValue = adminAuditDoctorFilter.value || "";
  const doctors = new Map();
  (adminDoctors || []).forEach((doctor) => {
    if (!doctor || !doctor.doctor_id) return;
    doctors.set(doctor.doctor_id, doctor.name || "Doctor");
  });
  const options = Array.from(doctors.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  adminAuditDoctorFilter.replaceChildren();

  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = "All doctors";
  adminAuditDoctorFilter.appendChild(allOption);

  options.forEach(([doctorId, doctorName]) => {
    const option = document.createElement("option");
    option.value = doctorId;
    option.textContent = doctorName;
    adminAuditDoctorFilter.appendChild(option);
  });

  adminAuditDoctorFilter.value = options.some(([doctorId]) => doctorId === currentValue) ? currentValue : "";
}

const ADMIN_AUDIT_LOG_TYPES = {
  doctor: { endpoint: "/admin/doctor-auth-audit-log", identifierParam: null },
  patient: { endpoint: "/admin/patient-auth-audit-log", identifierParam: "patient_id" },
  admin_actions: { endpoint: "/admin/patient-actions-log", identifierParam: "patient_id" },
  login: { endpoint: "/admin/login-audit-log", identifierParam: "email" },
};

function updateAdminAuditFilterVisibility() {
  const logType = adminAuditLogType?.value || "doctor";
  const isDoctor = logType === "doctor";
  if (adminAuditDoctorFilterField) adminAuditDoctorFilterField.classList.toggle("hidden", !isDoctor);
  if (adminAuditIdentifierFilterField) adminAuditIdentifierFilterField.classList.toggle("hidden", isDoctor);
  if (adminAuditIdentifierLabel) {
    adminAuditIdentifierLabel.textContent = logType === "login" ? "Email" : "Patient ID";
  }
}

async function loadAdminAuditLog(page = 1) {
  adminAuditPage = page;
  const logType = adminAuditLogType?.value || "doctor";
  const config = ADMIN_AUDIT_LOG_TYPES[logType] || ADMIN_AUDIT_LOG_TYPES.doctor;
  const params = new URLSearchParams({ page: String(page), page_size: String(adminAuditPageSize) });

  if (logType === "doctor") {
    const doctorId = adminAuditDoctorFilter?.value || "";
    if (doctorId) params.set("doctor_id", doctorId);
  } else {
    const identifier = adminAuditIdentifierFilter?.value.trim() || "";
    if (identifier && config.identifierParam) params.set(config.identifierParam, identifier);
  }
  if (adminAuditStartDate?.value) params.set("start_date", adminAuditStartDate.value);
  if (adminAuditEndDate?.value) params.set("end_date", adminAuditEndDate.value);

  try {
    const data = await adminAuthedJson(`${config.endpoint}?${params.toString()}`);
    adminAuditTotal = data.total || 0;
    renderAdminAuditLogRows(data.entries || []);
    if (adminAuditResultCount) adminAuditResultCount.textContent = `${adminAuditTotal} entries`;
    const totalPages = Math.max(1, Math.ceil(adminAuditTotal / adminAuditPageSize));
    if (adminAuditPageIndicator) adminAuditPageIndicator.textContent = `Page ${page} of ${totalPages}`;
    if (adminAuditPrevPageBtn) adminAuditPrevPageBtn.disabled = page <= 1;
    if (adminAuditNextPageBtn) adminAuditNextPageBtn.disabled = page >= totalPages;
  } catch (error) {
    if (adminAuditLogList) {
      adminAuditLogList.replaceChildren();
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = error.message;
      adminAuditLogList.appendChild(note);
    }
  }
}

function renderAdminAuditLogRows(entries) {
  if (!adminAuditLogList) return;
  adminAuditLogList.replaceChildren();

  if (!entries.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No audit entries found.";
    adminAuditLogList.appendChild(note);
    return;
  }

  entries.forEach((entry) => {
    const card = document.createElement("article");
    card.className = "admin-inline-card";

    const head = document.createElement("div");
    head.className = "admin-inline-card-head";

    const titleWrap = document.createElement("div");
    const title = document.createElement("div");
    title.className = "admin-inline-title";
    title.textContent = entry.action_type;
    const meta = document.createElement("div");
    meta.className = "admin-inline-meta";
    meta.textContent = entry.attempted_email || "-";
    titleWrap.append(title, meta);

    const time = document.createElement("span");
    time.className = "admin-inline-meta";
    time.textContent = formatDateTime(entry.created_at);

    head.append(titleWrap, time);
    card.appendChild(head);

    if (entry.metadata && Object.keys(entry.metadata).length) {
      const metaLine = document.createElement("div");
      metaLine.className = "admin-inline-meta";
      metaLine.textContent = JSON.stringify(entry.metadata);
      card.appendChild(metaLine);
    }

    adminAuditLogList.appendChild(card);
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
    addQuickAction(`${index + 1}. ${doctor.display_name || doctor.doctor_name} | ${experienceLabel}`, String(index + 1));
    });
    addQuickAction(patientAction("noAppointment"), "no");
  }

  if (state.awaiting === "slot_selection" && Array.isArray(state.slot_options)) {
    state.slot_options.forEach((slot, index) => {
      const time = formatDateTime(slot.start_time);
      addQuickAction(`${index + 1}. ${time}`, String(index + 1));
    });
    addQuickAction(patientAction("noAppointment"), "no");
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
  if (voiceDiscardBtn) {
    voiceDiscardBtn.classList.toggle("hidden", !transcriptToKeep);
  }
}

async function discardVoiceDraft() {
  if (voiceListening) {
    await stopVoiceCapture();
  }
  voiceFinalTranscript = "";
  voiceLiveTranscript = "";
  voiceCommittedTranscript = "";
  if (input) {
    input.value = "";
    autoResizeComposer();
  }
  if (voiceTranscriptPreview) {
    voiceTranscriptPreview.textContent = "";
    voiceTranscriptPreview.classList.add("hidden");
  }
  if (voiceStatusPreview) {
    voiceStatusPreview.textContent = "";
    voiceStatusPreview.classList.add("hidden");
  }
  if (voiceDiscardBtn) {
    voiceDiscardBtn.classList.add("hidden");
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
    voiceCommittedTranscript = "";
    if (voiceTranscriptPreview) {
      voiceTranscriptPreview.textContent = "";
      voiceTranscriptPreview.classList.add("hidden");
    }
    if (voiceDiscardBtn) {
      voiceDiscardBtn.classList.add("hidden");
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
      // Deepgram finalizes and restarts a new "utterance" after every pause, so each
      // message's transcript only covers the current utterance. Keep a running buffer
      // of everything already finalized and layer the current utterance on top of it,
      // instead of overwriting the box with just the latest utterance's text.
      let combined;
      if (payload?.is_final) {
        voiceCommittedTranscript = [voiceCommittedTranscript, transcript].filter(Boolean).join(" ").trim();
        combined = voiceCommittedTranscript;
      } else {
        combined = [voiceCommittedTranscript, transcript].filter(Boolean).join(" ").trim();
      }
      voiceFinalTranscript = voiceCommittedTranscript;
      voiceLiveTranscript = combined;
      if (input) {
        input.value = combined;
        autoResizeComposer();
      }
      if (voiceTranscriptPreview) {
        voiceTranscriptPreview.textContent = combined;
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

async function postJson(url, payload, bearerToken = null) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(url, {
      method: "POST",
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(bearerToken ? { Authorization: `Bearer ${bearerToken}` } : {}) },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      // detail is an object on responses that carry structured data alongside the
      // sentence (the 423 lockout's retry_after_seconds) — surface the sentence as the
      // Error text either way, and hang status/body off the Error for callers that
      // need more than a message.
      const detail = typeof data.detail === "string" ? data.detail : data.detail?.message;
      const error = new Error(detail || `Request failed with ${response.status}`);
      error.status = response.status;
      error.data = data;
      throw error;
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

function validateSignupStepTwo() {
  const name = document.querySelector("#profileName");
  const age = document.querySelector("#profileAge");
  const mobile = document.querySelector("#profileMobile");
  const email = document.querySelector("#profileEmail");
  const bloodGroup = document.querySelector("#profileBloodGroup");
  const address = document.querySelector("#profileAddress");

  for (const field of [name, age, mobile, email, bloodGroup, address]) {
    if (!field.reportValidity()) {
      return false;
    }
  }

  if (!name.value.trim()) {
    setAuthMessage("Name cannot be blank.");
    name.focus();
    return false;
  }

  if (!address.value.trim()) {
    setAuthMessage("Address cannot be blank.");
    address.focus();
    return false;
  }

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
  // upcoming_bookings above is just a placeholder — a brand-new chat session has no
  // idea what's actually booked. Fetch the real list from the DB so a slot booked
  // earlier in this login session doesn't disappear from the dashboard preview just
  // because the user started a new chat.
  refreshActiveAppointments();
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
    await refreshAppointmentsPage();
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
        await refreshAppointmentsPage();
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

  // Clear any leftover voice-draft preview — previously only reset if still
  // actively recording at send time, so a transcript that was already stopped
  // before Send (the common case) kept showing stale "Transcript ready" text.
  voiceFinalTranscript = "";
  voiceLiveTranscript = "";
  if (voiceTranscriptPreview) {
    voiceTranscriptPreview.textContent = "";
    voiceTranscriptPreview.classList.add("hidden");
  }
  if (voiceStatusPreview) {
    voiceStatusPreview.textContent = "";
    voiceStatusPreview.classList.add("hidden");
  }
  if (voiceDiscardBtn) {
    voiceDiscardBtn.classList.add("hidden");
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

if (voiceDiscardBtn) {
  voiceDiscardBtn.addEventListener("click", () => {
    void discardVoiceDraft();
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

if (endChatBtn && endChatConfirmModal && endChatCancelBtn && endChatConfirmBtn) {
  endChatBtn.addEventListener("click", () => {
    if (state?.chat_closed) {
      showChatClosed();
      return;
    }
    endChatConfirmModal.classList.remove("hidden");
    endChatConfirmBtn.focus();
  });

  endChatCancelBtn.addEventListener("click", () => {
    endChatConfirmModal.classList.add("hidden");
  });

  endChatConfirmBtn.addEventListener("click", () => {
    endChatConfirmModal.classList.add("hidden");
    input.value = "End the chat";
    form.requestSubmit();
  });
}

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

if (adminAuditLogType) adminAuditLogType.addEventListener("change", () => {
  updateAdminAuditFilterVisibility();
  loadAdminAuditLog(1);
});

if (adminAuditFilterBtn) adminAuditFilterBtn.addEventListener("click", () => loadAdminAuditLog(1));

if (adminAuditPrevPageBtn) adminAuditPrevPageBtn.addEventListener("click", () => {
  if (adminAuditPage > 1) loadAdminAuditLog(adminAuditPage - 1);
});

if (adminAuditNextPageBtn) adminAuditNextPageBtn.addEventListener("click", () => {
  loadAdminAuditLog(adminAuditPage + 1);
});

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

function renderMfaSection(container) {
  container.replaceChildren();

  if (!currentUser.mfa_enabled) {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
      <p class="form-hint">Two-factor authentication is not enabled on your account.</p>
      <button type="button" class="secondary" id="secEnableMfaBtn">Enable MFA</button>
      <div id="secMfaEnrollBlock" class="hidden">
        <p class="form-hint">Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.), or enter the code manually.</p>
        <div id="secMfaQrContainer" class="doctor-qr-container" aria-hidden="true"></div>
        <p class="doctor-manual-code" id="secMfaProvisioningUri"></p>
        <form id="secMfaEnrollForm">
          <label>Authenticator code<input id="secMfaEnrollCode" inputmode="numeric" autocomplete="one-time-code" maxlength="6" required /></label>
          <button type="submit">Verify &amp; enable MFA</button>
        </form>
        <p class="auth-error" id="secMfaEnrollMessage"></p>
      </div>
      <div id="secMfaRecoveryBlock" class="hidden">
        <p class="form-hint">Save these recovery codes now — each is single-use, and they can never be shown again.</p>
        <ol id="secRecoveryCodesList" class="doctor-recovery-codes"></ol>
        <button class="secondary" id="secRecoveryDownloadBtn" type="button">Download as .txt</button>
        <label class="admin-checkline">
          <input id="secRecoveryAckCheckbox" type="checkbox" />
          <span>I've saved my recovery codes</span>
        </label>
        <button id="secRecoveryDoneBtn" type="button" disabled>Done</button>
      </div>
    `;
    container.appendChild(wrap);

    const enableBtn = wrap.querySelector("#secEnableMfaBtn");
    const enrollBlock = wrap.querySelector("#secMfaEnrollBlock");
    const qrContainer = wrap.querySelector("#secMfaQrContainer");
    const provisioningUriEl = wrap.querySelector("#secMfaProvisioningUri");
    const enrollForm = wrap.querySelector("#secMfaEnrollForm");
    const enrollCode = wrap.querySelector("#secMfaEnrollCode");
    const enrollMessage = wrap.querySelector("#secMfaEnrollMessage");
    const recoveryBlock = wrap.querySelector("#secMfaRecoveryBlock");
    const recoveryList = wrap.querySelector("#secRecoveryCodesList");
    const downloadBtn = wrap.querySelector("#secRecoveryDownloadBtn");
    const ackCheckbox = wrap.querySelector("#secRecoveryAckCheckbox");
    const doneBtn = wrap.querySelector("#secRecoveryDoneBtn");
    let recoveryCodesInMemory = null;

    enableBtn.addEventListener("click", async () => {
      enableBtn.disabled = true;
      try {
        const data = await authedJson("/auth/mfa/setup/start", { method: "POST" });
        provisioningUriEl.textContent = data.provisioning_uri;
        qrContainer.innerHTML = "";
        try {
          const qr = qrcode(0, "M");
          qr.addData(data.provisioning_uri);
          qr.make();
          qrContainer.innerHTML = qr.createSvgTag(4);
        } catch (qrError) {
          // Manual code text above still lets setup complete.
        }
        enableBtn.classList.add("hidden");
        enrollBlock.classList.remove("hidden");
        enrollCode.focus();
      } catch (error) {
        enableBtn.disabled = false;
      }
    });

    enrollForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      enrollMessage.textContent = "";
      try {
        const data = await authedJson("/auth/mfa/setup/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code: enrollCode.value.trim() }),
        });
        currentUser.mfa_enabled = true;
        localStorage.setItem("currentUser", JSON.stringify(currentUser));
        recoveryCodesInMemory = data.recovery_codes;
        recoveryList.replaceChildren();
        data.recovery_codes.forEach((code) => {
          const li = document.createElement("li");
          li.textContent = code;
          recoveryList.appendChild(li);
        });
        ackCheckbox.checked = false;
        doneBtn.disabled = true;
        enrollBlock.classList.add("hidden");
        recoveryBlock.classList.remove("hidden");
      } catch (error) {
        enrollMessage.textContent = error.message || "Invalid code.";
      }
    });

    downloadBtn.addEventListener("click", () => {
      if (recoveryCodesInMemory) downloadRecoveryCodesAsText(recoveryCodesInMemory);
    });

    ackCheckbox.addEventListener("change", () => {
      doneBtn.disabled = !ackCheckbox.checked;
    });

    doneBtn.addEventListener("click", () => {
      renderMfaSection(container);
    });
    return;
  }

  const wrap = document.createElement("div");
  wrap.innerHTML = `
    <p class="form-hint">Two-factor authentication is enabled on your account.</p>
    <form id="secDisableMfaForm">
      <label>Current password<input id="secDisablePassword" type="password" autocomplete="current-password" required /></label>
      <label>Authentication code<input id="secDisableCode" inputmode="text" autocomplete="one-time-code" maxlength="64" required /></label>
      <button type="submit" class="secondary">Disable MFA</button>
      <p class="auth-error" id="secDisableMessage"></p>
    </form>
    <form id="secRegenerateForm">
      <label>Authentication code<input id="secRegenerateCode" inputmode="text" autocomplete="one-time-code" maxlength="64" required /></label>
      <button type="submit" class="secondary">Regenerate backup codes</button>
      <p class="auth-error" id="secRegenerateMessage"></p>
    </form>
    <div id="secMfaRecoveryBlock" class="hidden">
      <p class="form-hint">Save these recovery codes now — each is single-use, and they can never be shown again.</p>
      <ol id="secRecoveryCodesList" class="doctor-recovery-codes"></ol>
      <button class="secondary" id="secRecoveryDownloadBtn" type="button">Download as .txt</button>
      <label class="admin-checkline">
        <input id="secRecoveryAckCheckbox" type="checkbox" />
        <span>I've saved my recovery codes</span>
      </label>
      <button id="secRecoveryDoneBtn" type="button" disabled>Done</button>
    </div>
  `;
  container.appendChild(wrap);
  wireAllPasswordToggles(wrap);

  const disableForm = wrap.querySelector("#secDisableMfaForm");
  const disableMessage = wrap.querySelector("#secDisableMessage");
  const regenerateForm = wrap.querySelector("#secRegenerateForm");
  const regenerateMessage = wrap.querySelector("#secRegenerateMessage");
  const recoveryBlock = wrap.querySelector("#secMfaRecoveryBlock");
  const recoveryList = wrap.querySelector("#secRecoveryCodesList");
  const downloadBtn = wrap.querySelector("#secRecoveryDownloadBtn");
  const ackCheckbox = wrap.querySelector("#secRecoveryAckCheckbox");
  const doneBtn = wrap.querySelector("#secRecoveryDoneBtn");
  let recoveryCodesInMemory = null;

  disableForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    disableMessage.textContent = "";
    try {
      await authedJson("/auth/mfa/disable", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: wrap.querySelector("#secDisablePassword").value,
          code: wrap.querySelector("#secDisableCode").value.trim(),
        }),
      });
      currentUser.mfa_enabled = false;
      localStorage.setItem("currentUser", JSON.stringify(currentUser));
      renderMfaSection(container);
    } catch (error) {
      disableMessage.textContent = error.message || "Could not disable MFA.";
    }
  });

  regenerateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    regenerateMessage.textContent = "";
    try {
      const data = await authedJson("/auth/mfa/backup-codes/regenerate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: wrap.querySelector("#secRegenerateCode").value.trim() }),
      });
      recoveryCodesInMemory = data.recovery_codes;
      recoveryList.replaceChildren();
      data.recovery_codes.forEach((code) => {
        const li = document.createElement("li");
        li.textContent = code;
        recoveryList.appendChild(li);
      });
      ackCheckbox.checked = false;
      doneBtn.disabled = true;
      regenerateForm.classList.add("hidden");
      disableForm.classList.add("hidden");
      recoveryBlock.classList.remove("hidden");
    } catch (error) {
      regenerateMessage.textContent = error.message || "Could not regenerate backup codes.";
    }
  });

  downloadBtn.addEventListener("click", () => {
    if (recoveryCodesInMemory) downloadRecoveryCodesAsText(recoveryCodesInMemory);
  });

  ackCheckbox.addEventListener("change", () => {
    doneBtn.disabled = !ackCheckbox.checked;
  });

  doneBtn.addEventListener("click", () => {
    renderMfaSection(container);
  });
}

function showEditProfile() {
  if (!currentUser) return;
  showProfilePanel("Edit profile");

  const shell = document.createElement("div");
  shell.innerHTML = `
    <div class="tab-bar" id="profileTabBar">
      <button type="button" class="tab-btn is-active" data-profile-tab="personal">Personal Info</button>
      <button type="button" class="tab-btn" data-profile-tab="security">Security</button>
    </div>
    <div id="profileTabPersonal"></div>
    <div id="profileTabSecurity" class="hidden"></div>
  `;
  profilePanelBody.replaceChildren(shell);

  const tabBar = shell.querySelector("#profileTabBar");
  const personalPane = shell.querySelector("#profileTabPersonal");
  const securityPane = shell.querySelector("#profileTabSecurity");

  tabBar.addEventListener("click", (event) => {
    const btn = event.target.closest(".tab-btn");
    if (!btn || !tabBar.contains(btn)) return;
    const target = btn.dataset.profileTab;
    tabBar.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("is-active", b === btn));
    personalPane.classList.toggle("hidden", target !== "personal");
    securityPane.classList.toggle("hidden", target !== "security");
  });

  // Built with createElement rather than an innerHTML template: these carry user-entered
  // values, and interpolating a name containing a quote or a tag into markup is both an
  // escaping bug and an injection risk. Assigning .value sidesteps both.
  const labelled = (text, control) => {
    const label = document.createElement("label");
    label.className = "ep-label";
    const span = document.createElement("span");
    span.textContent = text;
    label.append(span, control);
    return label;
  };

  const makeInput = (id, value, options = {}) => {
    const el = document.createElement("input");
    el.className = "ep-input";
    el.id = id;
    el.type = options.type || "text";
    if (options.placeholder) el.placeholder = options.placeholder;
    if (options.min !== undefined) el.min = options.min;
    if (options.max !== undefined) el.max = options.max;
    if (options.maxLength) el.maxLength = options.maxLength;
    el.value = value ?? "";
    return el;
  };

  // Email and mobile identify the account, so they are shown fixed rather than edited
  // here — changing either needs a verified flow of its own, not a silent profile save.
  const readOnlyRow = (text, value, badge) => {
    const wrap = document.createElement("div");
    wrap.className = "ep-label";
    const span = document.createElement("span");
    span.textContent = text;
    const box = document.createElement("div");
    box.className = "ep-readonly";
    const val = document.createElement("span");
    val.textContent = value || "—";
    box.append(val);
    if (badge) box.append(badge);
    wrap.append(span, box);
    return wrap;
  };

  const personalForm = document.createElement("form");
  personalForm.className = "edit-profile-form";

  const firstNameInput = makeInput("epFirstName", currentUser.first_name, { maxLength: 100, placeholder: "First name" });
  const lastNameInput = makeInput("epLastName", currentUser.last_name, { maxLength: 100, placeholder: "Last name" });
  const ageInput = makeInput("epAge", currentUser.age, { type: "number", min: 1, max: 129 });

  const genderSelect = document.createElement("select");
  genderSelect.className = "ep-input";
  genderSelect.id = "epGender";
  [
    ["", "Select gender"],
    ["male", "Male"],
    ["female", "Female"],
    ["other", "Other"],
    ["prefer_not_to_say", "Prefer not to say"],
  ].forEach(([value, text]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    genderSelect.appendChild(option);
  });
  genderSelect.value = currentUser.gender || "";

  const addressInput = makeInput("epAddress", currentUser.address, { placeholder: "Street, City" });

  const healthIssues = document.createElement("textarea");
  healthIssues.className = "ep-textarea";
  healthIssues.id = "epHealthIssues";
  healthIssues.rows = 3;
  healthIssues.placeholder = "e.g. Diabetes, Hypertension";
  healthIssues.value = currentUser.health_issues || "";

  const verifiedBadge = document.createElement("span");
  const isVerified = currentUser.email_verified !== false;
  verifiedBadge.className = `ep-badge ${isVerified ? "is-verified" : "is-unverified"}`;
  verifiedBadge.textContent = isVerified ? "Verified" : "Not verified";

  personalForm.append(
    labelled("First name", firstNameInput),
    labelled("Last name", lastNameInput),
    labelled("Age", ageInput),
    labelled("Gender", genderSelect),
    readOnlyRow("Email address", currentUser.login_email || currentUser.email, verifiedBadge),
    readOnlyRow("Mobile number", currentUser.mobile_number),
    labelled("Address", addressInput),
    labelled("Health issues / pre-existing conditions", healthIssues),
  );

  const dirtyBar = document.createElement("div");
  dirtyBar.className = "ep-dirty-bar hidden";
  dirtyBar.innerHTML = `
    <span class="ep-dirty-text">You have unsaved changes</span>
    <span class="ep-dirty-actions">
      <button type="button" class="secondary compact" id="epDiscardBtn">Discard</button>
      <button type="submit" class="ep-save-btn" id="epSaveBtn">Save changes</button>
    </span>
    <span class="ep-msg" id="epMsg"></span>
  `;
  personalForm.appendChild(dirtyBar);
  personalPane.appendChild(personalForm);

  const epMsg = dirtyBar.querySelector("#epMsg");
  const currentValues = () => JSON.stringify({
    first_name: firstNameInput.value.trim(),
    last_name: lastNameInput.value.trim(),
    age: ageInput.value.trim(),
    gender: genderSelect.value,
    address: addressInput.value.trim(),
    health_issues: healthIssues.value.trim(),
  });
  let savedValues = currentValues();

  const refreshDirtyState = () => {
    dirtyBar.classList.toggle("hidden", currentValues() === savedValues);
    epMsg.textContent = "";
  };
  personalForm.addEventListener("input", refreshDirtyState);
  personalForm.addEventListener("change", refreshDirtyState);

  dirtyBar.querySelector("#epDiscardBtn").addEventListener("click", () => {
    firstNameInput.value = currentUser.first_name || "";
    lastNameInput.value = currentUser.last_name || "";
    ageInput.value = currentUser.age ?? "";
    genderSelect.value = currentUser.gender || "";
    addressInput.value = currentUser.address || "";
    healthIssues.value = currentUser.health_issues || "";
    refreshDirtyState();
  });

  personalForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const saveBtn = dirtyBar.querySelector("#epSaveBtn");
    saveBtn.disabled = true;
    epMsg.textContent = "Saving…";
    epMsg.style.color = "";

    try {
      const data = await authedJson("/auth/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          first_name: firstNameInput.value.trim() || null,
          last_name: lastNameInput.value.trim() || null,
          age: ageInput.value ? Number(ageInput.value) : null,
          gender: genderSelect.value || null,
          address: addressInput.value.trim() || null,
          health_issues: healthIssues.value.trim() || null,
        }),
      });
      currentUser = data.user;
      localStorage.setItem("currentUser", JSON.stringify(currentUser));
      setPatientSummary(currentUser);
      savedValues = currentValues();
      dirtyBar.classList.add("hidden");
      showAppToast("Profile updated.");
    } catch (err) {
      epMsg.textContent = err.message || "Save failed.";
      epMsg.style.color = "#dc2626";
    } finally {
      saveBtn.disabled = false;
    }
  });

  const securityBlock = document.createElement("div");
  securityBlock.className = "edit-profile-form";
  securityBlock.innerHTML = `
    <form id="secChangePasswordStartForm">
      <label class="ep-label"><span>Current password</span><input class="ep-input" id="secCurrentPassword" type="password" autocomplete="current-password" required /></label>
      <div class="ep-actions">
        <button type="submit" class="ep-save-btn">Send verification code</button>
        <span class="ep-msg" id="secPasswordStartMsg"></span>
      </div>
    </form>
    <form id="secChangePasswordOtpForm" class="hidden">
      <p class="form-hint" id="secPasswordConfirmHint"></p>
      <label class="ep-label"><span>Verification code</span><input class="ep-input" id="secPasswordOtp" inputmode="numeric" autocomplete="one-time-code" maxlength="6" required /></label>
      <p class="form-hint" id="secPasswordCountdown"></p>
      <div class="ep-actions">
        <button type="submit" class="ep-save-btn">Verify code</button>
        <button type="button" class="secondary" id="secPasswordResendBtn">Resend code</button>
        <span class="ep-msg" id="secPasswordOtpMsg"></span>
      </div>
    </form>
    <form id="secChangePasswordConfirmForm" class="hidden">
      <p class="form-hint">Code verified. Choose your new password.</p>
      <label class="ep-label"><span>New password</span><input class="ep-input" id="secNewPassword" type="password" autocomplete="new-password" minlength="8" required /></label>
      <label class="ep-label"><span>Confirm new password</span><input class="ep-input" id="secConfirmPassword" type="password" autocomplete="new-password" required /></label>
      <div class="ep-actions">
        <button type="submit" class="ep-save-btn">Change password</button>
        <span class="ep-msg" id="secPasswordConfirmMsg"></span>
      </div>
    </form>
    <div id="secMfaSection"></div>
  `;
  securityPane.appendChild(securityBlock);
  wireAllPasswordToggles(securityBlock);

  const startForm = securityBlock.querySelector("#secChangePasswordStartForm");
  const startMsg = securityBlock.querySelector("#secPasswordStartMsg");
  const otpForm = securityBlock.querySelector("#secChangePasswordOtpForm");
  const otpMsg = securityBlock.querySelector("#secPasswordOtpMsg");
  const confirmForm = securityBlock.querySelector("#secChangePasswordConfirmForm");
  const confirmHint = securityBlock.querySelector("#secPasswordConfirmHint");
  const confirmMsg = securityBlock.querySelector("#secPasswordConfirmMsg");
  const countdownEl = securityBlock.querySelector("#secPasswordCountdown");
  const resendBtn = securityBlock.querySelector("#secPasswordResendBtn");

  const beginSecCountdown = (seconds) => {
    if (secChangePasswordCountdownCancel) {
      secChangePasswordCountdownCancel();
      secChangePasswordCountdownCancel = null;
    }
    resendBtn.disabled = true;
    secChangePasswordCountdownCancel = startCountdown(countdownEl, seconds, () => {
      resendBtn.disabled = false;
    });
  };

  startForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    startMsg.textContent = "Sending…";
    startMsg.style.color = "";
    try {
      const data = await authedJson("/auth/change-password/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: securityBlock.querySelector("#secCurrentPassword").value }),
      });
      startForm.classList.add("hidden");
      otpForm.classList.remove("hidden");
      confirmHint.textContent = `Enter the code we sent to ${data.masked_email}.`;
      showAppToast(`Verification code sent to ${data.masked_email}.`);
      beginSecCountdown(OTP_RESEND_COOLDOWN_SECONDS);
      securityBlock.querySelector("#secPasswordOtp").focus();
    } catch (error) {
      startMsg.textContent = error.message || "Could not send a verification code.";
      startMsg.style.color = "#dc2626";
    }
  });

  // Step 2 of 3 — the code is checked on its own so a wrong one surfaces here, rather
  // than after the new password has already been typed twice.
  otpForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    otpMsg.textContent = "Verifying…";
    otpMsg.style.color = "";
    try {
      await authedJson("/auth/change-password/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ otp: securityBlock.querySelector("#secPasswordOtp").value.trim() }),
      });
      otpMsg.textContent = "";
      otpForm.classList.add("hidden");
      confirmForm.classList.remove("hidden");
      securityBlock.querySelector("#secNewPassword").focus();
    } catch (error) {
      otpMsg.textContent = error.message || "That code is invalid or has expired.";
      otpMsg.style.color = "#dc2626";
    }
  });

  confirmForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (securityBlock.querySelector("#secNewPassword").value !== securityBlock.querySelector("#secConfirmPassword").value) {
      confirmMsg.textContent = "Passwords do not match.";
      confirmMsg.style.color = "#dc2626";
      return;
    }
    confirmMsg.textContent = "Saving…";
    confirmMsg.style.color = "";
    try {
      await authedJson("/auth/change-password/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          otp: securityBlock.querySelector("#secPasswordOtp").value.trim(),
          new_password: securityBlock.querySelector("#secNewPassword").value,
          confirm_password: securityBlock.querySelector("#secConfirmPassword").value,
        }),
      });
      await tryRefreshPatientToken();
      if (secChangePasswordCountdownCancel) {
        secChangePasswordCountdownCancel();
        secChangePasswordCountdownCancel = null;
      }
      // The password change commits on its own — it is never part of the profile
      // Save/Discard above, so there is nothing left for the user to confirm here.
      confirmForm.reset();
      confirmForm.classList.add("hidden");
      otpForm.reset();
      startForm.reset();
      startForm.classList.remove("hidden");
      startMsg.textContent = "Password changed successfully.";
      startMsg.style.color = "var(--violet)";
      showAppToast("Password changed successfully.");
    } catch (error) {
      confirmMsg.textContent = error.message || "Could not change password.";
      confirmMsg.style.color = "#dc2626";
    }
  });

  resendBtn.addEventListener("click", async () => {
    otpMsg.textContent = "";
    try {
      const data = await authedJson("/auth/change-password/resend", { method: "POST" });
      if (data.status === "cooldown") {
        beginSecCountdown(Number(data.retry_after_seconds) || OTP_RESEND_COOLDOWN_SECONDS);
        return;
      }
      showAppToast("A new verification code has been sent.");
      beginSecCountdown(Number(data.retry_after_seconds) || OTP_RESEND_COOLDOWN_SECONDS);
    } catch (error) {
      otpMsg.textContent = error.message || "Could not resend the code.";
      otpMsg.style.color = "#dc2626";
    }
  });

  renderMfaSection(securityBlock.querySelector("#secMfaSection"));
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
    const data = await postJson("/auth/unified-login", {
      email: document.querySelector("#loginEmail").value.trim(),
      password: document.querySelector("#loginPassword").value,
    });
    if (data.status === "mfa_required") {
      doctorMfaToken = data.mfa_token;
      loginForm.classList.add("hidden");
      doctorMfaForm?.classList.remove("hidden");
      document.querySelector("#doctorMfaCode")?.focus();
      return;
    }
    if (data.status === "patient_mfa_required") {
      patientMfaToken = data.pending_token;
      loginForm.classList.add("hidden");
      patientMfaForm?.classList.remove("hidden");
      patientMfaCode?.focus();
      return;
    }
    if (data.status === "verification_required") {
      patientVerifyToken = data.pending_token;
      loginForm.classList.add("hidden");
      if (patientVerifyHint) patientVerifyHint.textContent = `Enter the 6-digit code we emailed to ${data.email}.`;
      patientVerifyForm?.classList.remove("hidden");
      patientVerifyCode?.focus();
      return;
    }
    const payload = JSON.parse(atob(data.access_token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (payload.role === "admin") setAdminAuthenticated({ email: data.email, name: data.name, role: data.role }, data.access_token, data.refresh_token);
    else if (payload.role === "patient") setPatientAuthenticated(data.user, data.access_token, data.refresh_token);
    else setAuthMessage("Doctor Dashboard — coming soon");
  } catch (error) {
    if (error.status === 423) {
      // Locked out — say so with a live countdown instead of the generic credentials
      // message, which is what made a lockout indistinguishable from a wrong password.
      setAuthMessage("");
      beginLoginLockoutCountdown(Number(error.data?.detail?.retry_after_seconds) || 60);
      return;
    }
    setAuthMessage("Invalid email or password.");
  }
});

if (doctorMfaForm) doctorMfaForm.addEventListener("submit", async (event) => {
  event.preventDefault(); setAuthMessage("");
  try {
    const data = await postJson("/doctor/auth/mfa/challenge", { code: doctorMfaCode.value }, doctorMfaToken);
    if (data.recovery_code_used) doctorLowRecoveryNoticePending = true;
    setDoctorAuthenticated(data.access_token);
  } catch (error) { setAuthMessage("Invalid email or password."); }
});

if (patientMfaForm) patientMfaForm.addEventListener("submit", async (event) => {
  event.preventDefault(); setAuthMessage("");
  try {
    const data = await postJson("/auth/mfa/verify", { code: patientMfaCode.value.trim() }, patientMfaToken);
    setPatientAuthenticated(data.user, data.access_token, data.refresh_token);
  } catch (error) {
    setAuthMessage(error.message || "Invalid code.");
  }
});

if (patientMfaBackBtn) patientMfaBackBtn.addEventListener("click", () => showAuthMode("login"));

if (showForgotPasswordBtn) showForgotPasswordBtn.addEventListener("click", () => {
  setAuthMessage("");
  loginForm.classList.add("hidden");
  if (forgotPasswordIdentifier) forgotPasswordIdentifier.value = "";
  forgotPasswordStartForm?.classList.remove("hidden");
  forgotPasswordIdentifier?.focus();
});

if (forgotPasswordStartBackBtn) forgotPasswordStartBackBtn.addEventListener("click", () => showAuthMode("login"));
if (forgotPasswordConfirmEmailBackBtn) forgotPasswordConfirmEmailBackBtn.addEventListener("click", () => showAuthMode("login"));
if (resetPasswordBackBtn) resetPasswordBackBtn.addEventListener("click", () => showAuthMode("login"));

if (forgotPasswordStartForm) forgotPasswordStartForm.addEventListener("submit", async (event) => {
  event.preventDefault(); setAuthMessage("");
  const identifier = forgotPasswordIdentifier.value.trim();
  try {
    const data = await postJson("/auth/forgot-password/start", { identifier });
    if (data.status === "not_found") {
      setAuthMessage("We couldn't find an account with that email or mobile number.");
      return;
    }
    if (data.status === "confirm_email_required") {
      resetPendingMobileNumber = identifier;
      if (forgotPasswordConfirmEmailHint) {
        forgotPasswordConfirmEmailHint.textContent = `Confirm the email address on this account (${data.masked_email}).`;
      }
      forgotPasswordStartForm.classList.add("hidden");
      forgotPasswordConfirmEmailForm?.classList.remove("hidden");
      forgotPasswordConfirmEmail?.focus();
      return;
    }
    if (data.status === "otp_sent") {
      resetEmail = identifier;
      forgotPasswordStartForm.classList.add("hidden");
      resetPasswordForm?.classList.remove("hidden");
      resetPasswordCode?.focus();
      showAppToast(`Verification code sent to ${data.email || resetEmail}.`);
      beginResetPasswordCountdown(OTP_RESEND_COOLDOWN_SECONDS);
    }
  } catch (error) {
    setAuthMessage(error.message || "Something went wrong. Please try again.");
  }
});

if (forgotPasswordConfirmEmailForm) forgotPasswordConfirmEmailForm.addEventListener("submit", async (event) => {
  event.preventDefault(); setAuthMessage("");
  const email = forgotPasswordConfirmEmail.value.trim();
  try {
    const data = await postJson("/auth/forgot-password/confirm-email", {
      mobile_number: resetPendingMobileNumber,
      email,
    });
    if (data.status === "email_mismatch") {
      setAuthMessage("That email doesn't match this account.");
      return;
    }
    if (data.status === "otp_sent") {
      resetEmail = email;
      forgotPasswordConfirmEmailForm.classList.add("hidden");
      resetPasswordForm?.classList.remove("hidden");
      resetPasswordCode?.focus();
      showAppToast(`Verification code sent to ${data.email || resetEmail}.`);
      beginResetPasswordCountdown(OTP_RESEND_COOLDOWN_SECONDS);
    }
  } catch (error) {
    setAuthMessage(error.message || "Something went wrong. Please try again.");
  }
});

if (resetPasswordForm) resetPasswordForm.addEventListener("submit", async (event) => {
  event.preventDefault(); setAuthMessage("");
  if (resetPasswordNew.value !== resetPasswordConfirm.value) {
    setAuthMessage("Passwords do not match.");
    return;
  }
  try {
    await postJson("/auth/reset-password", {
      email: resetEmail,
      otp: resetPasswordCode.value.trim(),
      new_password: resetPasswordNew.value,
      confirm_password: resetPasswordConfirm.value,
    });
    resetEmail = null;
    resetPendingMobileNumber = null;
    if (resetPasswordCountdownCancel) {
      resetPasswordCountdownCancel();
      resetPasswordCountdownCancel = null;
    }
    showAuthMode("login");
    setAuthMessage("Password reset. Please log in with your new password.");
  } catch (error) {
    setAuthMessage(error.message || "Could not reset your password.");
  }
});

if (resetPasswordResendBtn) resetPasswordResendBtn.addEventListener("click", async () => {
  setAuthMessage("");
  resetPasswordResendBtn.disabled = true;
  try {
    const data = await postJson("/auth/resend-otp", { email: resetEmail });
    if (data.status === "cooldown") {
      beginResetPasswordCountdown(Number(data.retry_after_seconds) || OTP_RESEND_COOLDOWN_SECONDS);
      return;
    }
    showAppToast("A new verification code has been sent.");
    beginResetPasswordCountdown(Number(data.retry_after_seconds) || OTP_RESEND_COOLDOWN_SECONDS);
  } catch (error) {
    setAuthMessage(error.message || "Could not resend the code.");
    resetPasswordResendBtn.disabled = false;
  }
});

if (doctorMfaRecoveryToggle) doctorMfaRecoveryToggle.addEventListener("click", () => {
  doctorMfaUsingRecoveryCode = !doctorMfaUsingRecoveryCode;
  if (doctorMfaUsingRecoveryCode) {
    if (doctorMfaFormHint) doctorMfaFormHint.textContent = "Enter one of your recovery codes.";
    if (doctorMfaCode) doctorMfaCode.setAttribute("inputmode", "text");
    doctorMfaRecoveryToggle.textContent = "Use authenticator code instead";
  } else {
    if (doctorMfaFormHint) doctorMfaFormHint.textContent = "Enter the 6-digit code from your authenticator app.";
    if (doctorMfaCode) doctorMfaCode.setAttribute("inputmode", "numeric");
    doctorMfaRecoveryToggle.textContent = "Use a recovery code instead";
  }
  if (doctorMfaCode) {
    doctorMfaCode.value = "";
    doctorMfaCode.focus();
  }
});

if (doctorRecoveryLowNotice) doctorRecoveryLowNotice.addEventListener("click", () => {
  doctorRecoveryLowNotice.classList.add("hidden");
});

if (doctorLogoutBtn) doctorLogoutBtn.addEventListener("click", () => {
  clearDoctorAuthenticated();
  showAuthMode("login");
});

doctorViewButtons.forEach((button) => {
  button.addEventListener("click", () => showDoctorView(button.dataset.doctorView));
});

if (doctorPatientDetailBackBtn) doctorPatientDetailBackBtn.addEventListener("click", () => {
  showDoctorView("patients");
});

if (doctorPatientSearchInput) doctorPatientSearchInput.addEventListener("input", () => {
  doctorPatientSearchTerm = doctorPatientSearchInput.value;
  renderDoctorPatientsList();
});

if (doctorAppointmentDetailBackBtn) doctorAppointmentDetailBackBtn.addEventListener("click", () => {
  stopConsultRecording();
  stopConsultStatusPolling();
  showDoctorView(doctorDetailReturnView);
});

if (doctorConsultStartBtn) doctorConsultStartBtn.addEventListener("click", startConsultForCurrentAppointment);

if (doctorConsultConsentCheckbox) doctorConsultConsentCheckbox.addEventListener("change", () => {
  if (doctorConsultConsentConfirmBtn) doctorConsultConsentConfirmBtn.disabled = !doctorConsultConsentCheckbox.checked;
});

if (doctorConsultConsentConfirmBtn) doctorConsultConsentConfirmBtn.addEventListener("click", confirmConsultConsent);

if (doctorConsultBeginRecordingBtn) doctorConsultBeginRecordingBtn.addEventListener("click", beginConsultRecordingClick);

if (doctorConsultStopRecordingBtn) doctorConsultStopRecordingBtn.addEventListener("click", stopConsultRecordingClick);

if (doctorConsultSwapSpeakersBtn) doctorConsultSwapSpeakersBtn.addEventListener("click", swapConsultSpeakers);

if (doctorConsultOrphanedEndBtn) doctorConsultOrphanedEndBtn.addEventListener("click", stopConsultRecordingClick);

if (doctorNoteGenerateBtn) doctorNoteGenerateBtn.addEventListener("click", () => {
  // Only ask for confirmation when regenerating over an existing note — nothing to
  // lose on the very first generate, so that one runs immediately.
  if (doctorCurrentNote) {
    doctorNoteGenerateConfirm?.classList.remove("hidden");
  } else {
    generateSoapNote();
  }
});

if (doctorNoteGenerateConfirmBtn) doctorNoteGenerateConfirmBtn.addEventListener("click", () => {
  doctorNoteGenerateConfirm?.classList.add("hidden");
  generateSoapNote();
});

if (doctorNoteGenerateCancelBtn) doctorNoteGenerateCancelBtn.addEventListener("click", () => {
  doctorNoteGenerateConfirm?.classList.add("hidden");
});

if (doctorNoteSaveBtn) doctorNoteSaveBtn.addEventListener("click", saveSoapNote);

if (doctorNoteSignBtn) doctorNoteSignBtn.addEventListener("click", () => {
  doctorNoteSignConfirm?.classList.remove("hidden");
});

if (doctorNoteSignConfirmBtn) doctorNoteSignConfirmBtn.addEventListener("click", () => {
  doctorNoteSignConfirm?.classList.add("hidden");
  confirmSignSoapNote();
});

if (doctorNoteSignCancelBtn) doctorNoteSignCancelBtn.addEventListener("click", () => {
  doctorNoteSignConfirm?.classList.add("hidden");
});

if (doctorNoteAddAddendumBtn) doctorNoteAddAddendumBtn.addEventListener("click", () => {
  doctorNoteAddendumForm?.classList.remove("hidden");
});

if (doctorNoteAddendumSaveBtn) doctorNoteAddendumSaveBtn.addEventListener("click", saveNoteAddendum);

if (doctorNoteAddendumCancelBtn) doctorNoteAddendumCancelBtn.addEventListener("click", () => {
  doctorNoteAddendumForm?.classList.add("hidden");
  if (doctorNoteAddendumText) doctorNoteAddendumText.value = "";
});

if (doctorNoteCopyBtn) doctorNoteCopyBtn.addEventListener("click", copySignedNoteToClipboard);

if (doctorConsultDiscardBtn) doctorConsultDiscardBtn.addEventListener("click", () => {
  doctorConsultDiscardConfirm?.classList.remove("hidden");
});

if (doctorConsultDiscardCancelBtn) doctorConsultDiscardCancelBtn.addEventListener("click", () => {
  doctorConsultDiscardConfirm?.classList.add("hidden");
});

if (doctorConsultDiscardConfirmBtn) doctorConsultDiscardConfirmBtn.addEventListener("click", confirmDiscardConsult);

if (doctorSetPasswordForm) doctorSetPasswordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setDoctorOnboardingMessage("");
  const password = doctorNewPassword.value;
  const confirmPassword = doctorConfirmPassword.value;
  if (!passwordPattern.test(password)) {
    setDoctorOnboardingMessage(
      "Password must include uppercase, lowercase, number, special character, and be at least 8 characters."
    );
    return;
  }
  if (password !== confirmPassword) {
    setDoctorOnboardingMessage("Passwords do not match.");
    return;
  }
  try {
    const data = await postJson("/doctor/auth/complete-invite", { token: pendingInviteToken, password });
    if (data.status === "password_reset") {
      pendingInviteToken = null;
      history.replaceState(null, "", "/");
      doctorOnboardingView?.classList.add("hidden");
      authView?.classList.remove("hidden");
      showAuthMode("login");
      setAuthMessage("Password updated. Please log in.");
      return;
    }
    doctorMfaEnrollmentToken = data.mfa_enrollment_token;
    showDoctorOnboardingStep("enroll");
    await startDoctorMfaEnrollment();
  } catch (error) {
    setDoctorOnboardingMessage(error.message);
  }
});

if (doctorMfaEnrollForm) doctorMfaEnrollForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (doctorMfaEnrollMessage) doctorMfaEnrollMessage.textContent = "";
  try {
    const data = await postJson("/doctor/auth/mfa/verify", { code: doctorMfaEnrollCode.value }, doctorMfaEnrollmentToken);
    showDoctorOnboardingStep("recovery");
    renderRecoveryCodes(data.recovery_codes || []);
  } catch (error) {
    if (doctorMfaEnrollMessage) doctorMfaEnrollMessage.textContent = doctorEnrollmentErrorMessage(error);
  }
});

if (doctorRecoveryAckCheckbox) doctorRecoveryAckCheckbox.addEventListener("change", () => {
  if (doctorRecoveryContinueBtn) doctorRecoveryContinueBtn.disabled = !doctorRecoveryAckCheckbox.checked;
});

if (doctorRecoveryDownloadBtn) doctorRecoveryDownloadBtn.addEventListener("click", () => {
  downloadRecoveryCodesAsText(doctorRecoveryCodesInMemory || []);
});

if (doctorRecoveryContinueBtn) doctorRecoveryContinueBtn.addEventListener("click", () => {
  doctorRecoveryCodesInMemory = null;
  doctorRecoveryCodesList?.replaceChildren();
  doctorMfaEnrollmentToken = null;
  history.replaceState(null, "", "/");
  doctorOnboardingView?.classList.add("hidden");
  authView?.classList.remove("hidden");
  showAuthMode("login");
  setAuthMessage("MFA enabled. Please log in to continue.");
});

signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateSignupStepOne()) {
    signupStepTwo.classList.add("hidden");
    signupStepOne.classList.remove("hidden");
    return;
  }

  if (!validateSignupStepTwo()) {
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
    patientVerifyToken = data.pending_token;
    signupForm.classList.add("hidden");
    if (patientVerifyHint) patientVerifyHint.textContent = `Enter the 6-digit code we emailed to ${data.email}.`;
    patientVerifyForm?.classList.remove("hidden");
    patientVerifyCode?.focus();
  } catch (error) {
    setAuthMessage(error.message);
  }
});

if (patientVerifyForm) patientVerifyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setAuthMessage("");
  try {
    const data = await postJson("/auth/verify-email", { code: patientVerifyCode.value.trim() }, patientVerifyToken);
    setPatientAuthenticated(data.user, data.access_token, data.refresh_token);
  } catch (error) {
    setAuthMessage("That code is invalid or has expired.");
  }
});

if (patientVerifyResendBtn) patientVerifyResendBtn.addEventListener("click", async () => {
  setAuthMessage("");
  patientVerifyResendBtn.disabled = true;
  try {
    await postJson("/auth/resend-verification", {}, patientVerifyToken);
    setAuthMessage("A new code has been sent.");
  } catch (error) {
    setAuthMessage(error.message);
  } finally {
    setTimeout(() => { patientVerifyResendBtn.disabled = false; }, 30000);
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
      setAdminAuthenticated({ email: data.email, name: data.name, role: data.role }, data.access_token, data.refresh_token);
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
      // Step 1: POST /chat/upload — OpenAI vision medical relevance check + staging
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
      setPatientAuthenticated(data.user, accessToken, refreshToken);
      return;
    }

    if (currentAdmin && adminAccessToken) {
      const data = await adminAuthedJson("/admin/me");
      setAdminAuthenticated(data.admin, adminAccessToken, adminRefreshToken);
      return;
    }

    if (doctorAccessToken) {
      const data = await doctorAuthedJson("/doctor/me");
      document.body.classList.add("doctor-authenticated");
      doctorDashboardView?.classList.remove("hidden");
      showDoctorView("overview");
      renderDoctorDashboard(data.doctor);
      loadDoctorAppointments("upcoming");
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

if (!initDoctorInviteRouting()) {
  bootstrapSession();
}
setSidebarOpen(sidebarOpen);
wireAllPasswordToggles();

document.querySelectorAll("[data-nav]").forEach((button) => {
  if (button.dataset.nav === "records") {
    button.addEventListener("click", () => {
      void loadRecordsArchive();
    });
  }
  if (button.dataset.nav === "appointments") {
    button.addEventListener("click", () => {
      void refreshAppointmentsPage();
    });
  }
});






