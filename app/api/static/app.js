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
const doctorMfaBackBtn = document.querySelector("#doctorMfaBackBtn");
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
const doctorReviewsPane = document.querySelector("#doctorReviewsPane");
const doctorReviewsList = document.querySelector("#doctorReviewsList");
const doctorReviewsCount = document.querySelector("#doctorReviewsCount");
const doctorReviewSearchInput = document.querySelector("#doctorReviewSearchInput");
const doctorReviewScopeButtons = document.querySelectorAll("[data-review-scope]");
const doctorReviewNavCount = document.querySelector("#doctorReviewNavCount");
const doctorStatReviews = document.querySelector("#doctorStatReviews");
const doctorStatAttention = document.querySelector("#doctorStatAttention");
const doctorStatReviewsCard = document.querySelector("#doctorStatReviewsCard");
const doctorStatAttentionCard = document.querySelector("#doctorStatAttentionCard");
const doctorTodaySchedule = document.querySelector("#doctorTodaySchedule");
const doctorTodayScheduleCount = document.querySelector("#doctorTodayScheduleCount");
const doctorOverviewReviews = document.querySelector("#doctorOverviewReviews");
const doctorOverviewReviewsBtn = document.querySelector("#doctorOverviewReviewsBtn");
// ── AI workspace (docs/ai-redesign/) ──────────────────────────────────────────
const doctorSidebarName = document.querySelector("#doctorSidebarName");
const doctorSidebarDepartment = document.querySelector("#doctorSidebarDepartment");
const doctorSidebarInitials = document.querySelector("#doctorSidebarInitials");
const doctorOverviewDate = document.querySelector("#doctorOverviewDate");
const doctorOverviewGreeting = document.querySelector("#doctorOverviewGreeting");
const doctorOverviewSubhead = document.querySelector("#doctorOverviewSubhead");
const doctorStartReviewBtn = document.querySelector("#doctorStartReviewBtn");
const doctorActivityHeadline = document.querySelector("#doctorActivityHeadline");
const doctorActivityTiles = document.querySelector("#doctorActivityTiles");
const doctorActivityDrill = document.querySelector("#doctorActivityDrill");
const doctorActivityDrillTitle = document.querySelector("#doctorActivityDrillTitle");
const doctorActivityDrillSub = document.querySelector("#doctorActivityDrillSub");
const doctorActivityDrillList = document.querySelector("#doctorActivityDrillList");
const doctorActivityDrillClose = document.querySelector("#doctorActivityDrillClose");
const doctorActivityWindowText = document.querySelector("#doctorActivityWindowText");
const doctorActivityWindowButtons = document.querySelectorAll("[data-activity-window]");
const doctorActivityLog = document.querySelector("#doctorActivityLog");
const doctorActivityLogToggle = document.querySelector("#doctorActivityLogToggle");
// Rows shown before "Full audit" is pressed, and the most the endpoint returns after.
const DOCTOR_ACTIVITY_LOG_COLLAPSED = 8;
const DOCTOR_ACTIVITY_LOG_MAX = 100;
let doctorActivityLogExpanded = false;
const doctorTodayChip = document.querySelector("#doctorTodayChip");
const doctorTodayChipText = document.querySelector("#doctorTodayChipText");
const doctorReviewLanes = document.querySelector("#doctorReviewLanes");
const doctorLaneQuick = document.querySelector("#doctorLaneQuick");
const doctorLaneAttention = document.querySelector("#doctorLaneAttention");
const doctorLaneNotDrafted = document.querySelector("#doctorLaneNotDrafted");
const doctorLaneQuickCount = document.querySelector("#doctorLaneQuickCount");
const doctorLaneAttentionCount = document.querySelector("#doctorLaneAttentionCount");
const doctorLaneNotDraftedCount = document.querySelector("#doctorLaneNotDraftedCount");
const doctorDraftAllBtn = document.querySelector("#doctorDraftAllBtn");
const doctorDraftAllLabel = document.querySelector("#doctorDraftAllLabel");
const doctorDraftAllMessage = document.querySelector("#doctorDraftAllMessage");
const doctorAskAiBar = document.querySelector("#doctorAskAiBar");
const doctorAskAiInput = document.querySelector("#doctorAskAiInput");
const doctorNoteVerifyLabel = document.querySelector("#doctorNoteVerifyLabel");
const doctorNoteVerifyFill = document.querySelector("#doctorNoteVerifyFill");
const doctorNoteVerifyBar = document.querySelector("#doctorNoteVerifyBar");
const doctorNoteProvenanceList = document.querySelector("#doctorNoteProvenanceList");
const doctorNoteSuggestedChecks = document.querySelector("#doctorNoteSuggestedChecks");
const doctorNoteAuditTrail = document.querySelector("#doctorNoteAuditTrail");
const doctorInsertFromPlanBtn = document.querySelector("#doctorInsertFromPlanBtn");
const doctorNoteSignWarning = document.querySelector("#doctorNoteSignWarning");
const doctorInsertFromPlanRow = document.querySelector("#doctorInsertFromPlanRow");
const doctorClinicalItemAllergyAlert = document.querySelector("#doctorClinicalItemAllergyAlert");
const doctorClinicalItemAllergyBody = document.querySelector("#doctorClinicalItemAllergyBody");

const doctorPatientDocumentsList = document.querySelector("#doctorPatientDocumentsList");
const doctorPatientDocumentsCount = document.querySelector("#doctorPatientDocumentsCount");
const doctorPatientDocumentsMessage = document.querySelector("#doctorPatientDocumentsMessage");
const doctorNoteShareRow = document.querySelector("#doctorNoteShareRow");
const doctorNoteShareBtn = document.querySelector("#doctorNoteShareBtn");
const doctorNoteShareConfirm = document.querySelector("#doctorNoteShareConfirm");
const doctorNoteShareConfirmBtn = document.querySelector("#doctorNoteShareConfirmBtn");
const doctorNoteShareCancelBtn = document.querySelector("#doctorNoteShareCancelBtn");
const doctorNoteSharedNotice = document.querySelector("#doctorNoteSharedNotice");
const doctorNoteEmptyState = document.querySelector("#doctorNoteEmptyState");
const doctorNoteStyleToggle = document.querySelector("#doctorNoteStyleToggle");
const doctorNoteStyleButtons = document.querySelectorAll("[data-note-style]");
const doctorPatientAlert = document.querySelector("#doctorPatientAlert");
const doctorPatientAlertBody = document.querySelector("#doctorPatientAlertBody");
const doctorPatientTabButtons = document.querySelectorAll("[data-patient-tab]");
const doctorPatientTabHistory = document.querySelector("#doctorPatientTabHistory");
const doctorPatientTabDocuments = document.querySelector("#doctorPatientTabDocuments");
const doctorPatientTabTimeline = document.querySelector("#doctorPatientTabTimeline");
const doctorClinicalItemsBlock = document.querySelector("#doctorClinicalItemsBlock");
const doctorClinicalItemTabButtons = document.querySelectorAll("[data-clinical-item]");
const doctorClinicalItemText = document.querySelector("#doctorClinicalItemText");
const doctorClinicalItemStatus = document.querySelector("#doctorClinicalItemStatus");
const doctorClinicalItemMessage = document.querySelector("#doctorClinicalItemMessage");
const doctorClinicalItemActions = document.querySelector("#doctorClinicalItemActions");
const doctorClinicalItemSaveBtn = document.querySelector("#doctorClinicalItemSaveBtn");
const doctorClinicalItemApproveBtn = document.querySelector("#doctorClinicalItemApproveBtn");
const doctorClinicalItemApproveConfirm = document.querySelector("#doctorClinicalItemApproveConfirm");
const doctorClinicalItemApproveConfirmBtn = document.querySelector("#doctorClinicalItemApproveConfirmBtn");
const doctorClinicalItemApproveCancelBtn = document.querySelector("#doctorClinicalItemApproveCancelBtn");
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
let doctorReviewsCache = [];
let doctorReviewCounts = {};
let doctorReviewScope = "pending";
// Which window the overview's AI activity counts cover: "last_visit" | "24h" | "7d".
// Server-validated; it rejects anything else rather than defaulting, so a bad value here
// surfaces as an error instead of silently changing what a clinical figure counts.
let doctorActivityWindow = "last_visit";
// Which activity tile's drill-down is open, or null. Survives the tiles being re-rendered
// by a refresh, so a doctor reading the list does not have it snap shut under them.
let doctorActivityDrillTile = null;
// Guards against two drill-down requests racing: a slow response for the tile or window
// the doctor has since left must not overwrite the list for the one they are now on.
let doctorActivityDrillRequest = 0;
// Consultation ids in the server's AI-ranked order (doctor_workspace.rank_pending_items).
// Held separately from doctorReviewsCache so the cache keeps the server's own row order
// and the ranking stays a view concern, applied by applyServerRanking().
let doctorReviewRanking = [];
// The PENDING queue, ranked, held apart from whatever the Reviews pane is showing. The
// Overview's "Your next actions" and "Start AI review" read from here. They used to read
// doctorReviewsCache, which holds the SIGNED history whenever the doctor last left Reviews
// on that tab — so the Overview said "Nothing is waiting for your review" with work waiting.
let doctorPendingQueue = [];
// "loading" | "ready" | "error": three different things to say, and an empty queue is only
// one of them.
let doctorPendingState = "loading";
// Whether the upcoming appointments have arrived at least once — "no appointments today" is
// only a true statement after they have.
let doctorUpcomingLoaded = false;
let doctorReviewSearchTerm = "";
let doctorPatientDetailId = null;
let doctorPatientTab = "history";
let doctorNoteStyle = "concise";
// A note is being drafted: the controls are disabled and a status line is shown, so a
// minute-long model call is visibly in progress and cannot be started twice.
let doctorNoteGenerating = false;
let doctorClinicalItemKind = "prescription";
let doctorClinicalItem = null;
let doctorDetailReturnView = "upcoming";
let doctorPatientDetailReturnView = "patients";
let doctorDetailAppointment = null;
let doctorActiveConsult = null;
let doctorConsultPollTimer = null;
let doctorRecordingTimerInterval = null;
let doctorRecordingStartedAtMs = null;
let doctorConsultSegmentsById = {};
let doctorCurrentNote = null;
// True while the draft's text fields hold edits that have not been saved. Three things
// depend on it, and each was a way to lose or misrecord clinical text before it existed:
//   - re-rendering the draft (Mark verified) keeps the typed text instead of reverting it
//   - signing saves first, so what is signed is what the doctor is looking at
//   - leaving the note asks first
// Set by the textareas' input event; cleared whenever the fields are (re)loaded from a
// server response, because at that point what is on screen IS what is saved.
let doctorNoteDirty = false;
// Which SOAP sections the doctor has marked as checked on the open draft. Server is the
// source of truth; this mirrors its last response (plan §4.6).
let doctorNoteVerifiedSections = [];
// Patient-reported health issues for the open appointment, shown on the clinical-actions
// tab. Unverified free text; nothing cross-checks it against what the doctor writes.
let doctorDetailPatientIssues = "";
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
    formatDocumentType(doc.document_type),
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
  // This path also hides the doctor dashboard; the viewer sits outside it and must close
  // with it, or a patient document stays over the login screen.
  closeDoctorViewer();
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

// Calls that wait on a language model get longer than the default: one note is one model
// call over a whole consultation; "draft all" is up to ten of them in sequence.
// Up to two model attempts on the server (one retry on an unreadable reply), each of
// which can take a minute on a long consult with a reasoning model.
const DOCTOR_GENERATE_TIMEOUT_MS = 300000;
const DOCTOR_DRAFT_ALL_TIMEOUT_MS = 300000;

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
  // Reveal the shell immediately so the workspace does not sit blank behind the
  // /doctor/me round-trip. refetch:false because loadDoctorDashboard -> enterDoctorWorkspace
  // owns the loading; without it every overview request would be issued twice on login.
  doctorOnboardingView?.classList.add("hidden");
  doctorDashboardView?.classList.remove("hidden");
  showDoctorView("overview", { refetch: false });
  loadDoctorDashboard();
}

function clearDoctorAuthenticated() {
  // Read before the class is removed below: was a doctor actually in the workspace? False
  // at start-up, when /doctor/me fails before the workspace ever opened.
  const wasInWorkspace = document.body.classList.contains("doctor-authenticated");
  // The document viewer lives OUTSIDE the dashboard view, so hiding the dashboard left a
  // patient's document open over the login screen after log-out or an expired session.
  closeDoctorViewer();
  stopConsultRecording();
  stopConsultStatusPolling();
  // The refresh timer outlives the page otherwise, and would keep polling doctor
  // endpoints with a cleared token until the tab closed.
  stopDoctorRefresh();
  doctorAccessToken = null;
  localStorage.removeItem("doctorAccessToken");
  document.body.classList.remove("doctor-authenticated");
  doctorDashboardView?.classList.add("hidden");
  doctorUpcomingAppointments = [];
  doctorPastAppointments = [];
  doctorPatientsCache = [];
  // Clinical data must not survive logout in module state — this is a shared-workstation
  // context, and the next person to sign in must start from nothing.
  doctorReviewsCache = [];
  doctorReviewCounts = {};
  doctorReviewScope = "pending";
  doctorReviewSearchTerm = "";
  doctorPatientDetailId = null;
  doctorPatientTab = "history";
  doctorClinicalItem = null;
  doctorClinicalItemKind = "prescription";
  doctorActivityWindow = "last_visit";
  doctorLastRefreshAt = null;
  resetDoctorActivityDrill();
  doctorNoteDirty = false;

  // Then start the page over. Resetting variables is not enough on a shared workstation:
  // every screen the doctor visited — patient lists, a patient's page, a transcript, a note
  // — is still in the DOM, merely hidden, for the next person at this computer. Emptying
  // each container by hand would need a list that goes stale the day a screen is added; a
  // reload cannot miss one. The token is already gone, so the reload lands on the login
  // screen, and the beforeunload guard stays quiet because it checks for that token.
  if (wasInWorkspace) window.location.reload();
}

/** The drill-down lists patient names. Closing it is not enough on a shared workstation —
 *  the rows would still be in the DOM for the next person — so the list is emptied too. */
function resetDoctorActivityDrill() {
  closeDoctorActivityDrill();
  doctorActivityDrillList?.replaceChildren();
  if (doctorActivityDrillTitle) doctorActivityDrillTitle.textContent = "";
  if (doctorActivityDrillSub) doctorActivityDrillSub.textContent = "";
}

/** THE one way into the doctor workspace, for every route in: a fresh login and a page
 *  reload both land here.
 *
 *  It exists because they did not. Login went through loadDoctorDashboard, which loaded
 *  appointments, reviews AND the AI panels; a reload went through bootstrapSession, which
 *  loaded appointments only. So a hard refresh silently dropped the AI activity summary,
 *  the activity feed and the entire review queue — including the sidebar's pending badge —
 *  and the doctor saw a workspace that looked loaded but was not. Two paths that must
 *  agree cannot be kept in agreement by remembering to edit both, so there is now one.
 *
 *  @param doctor - the profile from /doctor/me, or null if that call failed. The workspace
 *                  still opens and still loads its data in that case; only the profile
 *                  fields stay at their placeholders. */
function enterDoctorWorkspace(doctor) {
  // Start with every drill-down closed and empty, whatever the previous session left —
  // not every sign-out path runs clearDoctorAuthenticated.
  resetDoctorActivityDrill();
  document.body.classList.add("doctor-authenticated");
  doctorOnboardingView?.classList.add("hidden");
  doctorDashboardView?.classList.remove("hidden");
  // refetch:false — the loaders below are this view's initial load.
  showDoctorView("overview", { refetch: false });
  if (doctor) renderDoctorDashboard(doctor);

  // Fired without awaiting, and alongside each other rather than in sequence: the review
  // queue must not add its latency to first paint of the appointments list. The AI panels
  // join the same set — they are the first thing the doctor reads, but the workspace must
  // still paint and be usable if they fail.
  // Stamped when they settle, not now: "Updated 16:05" printed before the data arrives
  // would be the one thing on the panel that is definitely wrong. allSettled, so a failed
  // panel still lets the others report their freshness.
  Promise.allSettled([
    loadDoctorAppointments("upcoming"),
    loadDoctorReviews(),
    loadDoctorAiActivity(),
  ]).then(() => {
    doctorLastRefreshAt = new Date();
    renderDoctorFreshness();
  });

  startDoctorRefresh();
}

async function loadDoctorDashboard() {
  let doctor = null;
  try {
    const data = await doctorAuthedJson("/doctor/me");
    doctor = data.doctor;
  } catch (error) {
    // A 401 is already handled inside doctorAuthedJson (logs the doctor out);
    // any other failure just leaves the dashboard fields at their placeholders.
  }
  enterDoctorWorkspace(doctor);
}

// ── Keeping the workspace current (issue 4) ──────────────────────────────────
// Before this, every doctor view was load-once: the only timer in the panel was the 4s
// transcript poll during an active consult. A doctor who left the tab open saw whatever
// was true when they signed in, with nothing to tell them it had aged.
//
// Polling, not push: there is no event bus or SSE endpoint in this app, and adding one
// would not survive being run with more than one worker.

const DOCTOR_REFRESH_MS = 30000;
// Past appointments are history — they change when a consult completes, not continuously.
const DOCTOR_REFRESH_SLOW_MS = 60000;
const DOCTOR_SLOW_VIEWS = new Set(["past"]);

let doctorRefreshTimer = null;
let doctorLastRefreshAt = null;
// Guards against a slow request and a tick overlapping into two concurrent refreshes.
let doctorRefreshInFlight = false;

/** Whether a background refresh may run right now.
 *
 *  Three hazards, all of them real:
 *
 *  1. UNSAVED CLINICAL TEXT. The SOAP editor saves on an explicit button press and has no
 *     dirty-tracking and no beforeunload guard, so re-rendering a note under the doctor
 *     would silently discard whatever they had typed into it. The appointment-detail and
 *     patient-detail panes are work surfaces and are never refreshed from a timer.
 *  2. AN ACTIVE CONSULT owns its own screen and its own 4s poll; a second refresher
 *     fighting it can only cause flicker and duplicate work.
 *  3. A HIDDEN TAB should cost nothing. */
function canRefreshDoctorViewNow() {
  if (!doctorAccessToken) return false;
  if (document.hidden) return false;
  if (doctorRefreshInFlight) return false;
  if (doctorActiveConsult || doctorRecordingStartedAtMs) return false;
  if (doctorAppointmentDetailPane && !doctorAppointmentDetailPane.classList.contains("hidden")) return false;
  if (doctorPatientDetailPane && !doctorPatientDetailPane.classList.contains("hidden")) return false;
  return true;
}

/** Refetches whatever the doctor is actually looking at — not every view, so a doctor on
 *  Reviews never pays for the Patients query. Every loader is called in background mode,
 *  which is what stops a failed refresh replacing good data with an empty state. */
async function refreshActiveDoctorView({ force = false } = {}) {
  if (!force && !canRefreshDoctorViewNow()) return;
  if (doctorRefreshInFlight) return;
  doctorRefreshInFlight = true;
  try {
    const view = doctorCurrentView;
    if (view === "overview") {
      await Promise.all([
        loadDoctorAiActivity({ background: true }),
        loadDoctorReviews({ background: true }),
        loadDoctorAppointments("upcoming", { background: true }),
      ]);
    } else if (view === "reviews") {
      await loadDoctorReviews({ background: true });
    } else if (view === "upcoming" || view === "past") {
      await loadDoctorAppointments(view, { background: true });
    } else if (view === "patients") {
      await loadDoctorPatientsList({ background: true });
    }
    doctorLastRefreshAt = new Date();
    renderDoctorFreshness();
  } finally {
    doctorRefreshInFlight = false;
  }
}

/** Called after any action that changes the clinical record.
 *
 *  Not refreshActiveDoctorView: signing a note changes the review queue and the activity
 *  feed whatever pane happens to be in front, and a doctor who has just signed something
 *  must not still see it listed as awaiting their signature. Background mode throughout —
 *  these panes are usually hidden behind the appointment detail, and a failed refresh
 *  must leave the queue they are working from intact. */
async function refreshAfterClinicalAction() {
  await Promise.all([
    loadDoctorReviews({ background: true }),
    loadDoctorAiActivity({ background: true }),
  ]);
  doctorLastRefreshAt = new Date();
  renderDoctorFreshness();
}

function startDoctorRefresh() {
  stopDoctorRefresh();
  // No timestamp here — enterDoctorWorkspace stamps it when its loads actually settle.
  doctorRefreshTimer = window.setInterval(() => {
    // The slow views are polled by skipping ticks rather than by a second timer, so there
    // is only ever one interval to start, stop and reason about.
    const slow = DOCTOR_SLOW_VIEWS.has(doctorCurrentView);
    if (slow && doctorLastRefreshAt
        && Date.now() - doctorLastRefreshAt.getTime() < DOCTOR_REFRESH_SLOW_MS - 1000) {
      return;
    }
    void refreshActiveDoctorView();
  }, DOCTOR_REFRESH_MS);
}

function stopDoctorRefresh() {
  if (doctorRefreshTimer) window.clearInterval(doctorRefreshTimer);
  doctorRefreshTimer = null;
}

/** "Updated 15:42". On a dashboard that changes by itself, the doctor must be able to see
 *  how old the numbers are — otherwise auto-refresh just removes their last cue that the
 *  data might be stale. Also the only way to verify the feature by eye. */
function renderDoctorFreshness() {
  const stamp = doctorLastRefreshAt
    ? `Updated ${doctorLastRefreshAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
    : "";
  document.querySelectorAll("[data-doctor-updated]").forEach((element) => {
    element.textContent = stamp;
  });
}

// Coming back to the tab is the moment stale data is most likely and most visible, so it
// refreshes immediately rather than waiting for the next tick.
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) void refreshActiveDoctorView();
});
window.addEventListener("focus", () => {
  void refreshActiveDoctorView();
});

/** @param refetch - false only for the initial reveal in enterDoctorWorkspace, which does
 *                   its own loading. Without it, opening the workspace would show the
 *                   overview and fire every overview request twice. */
// EVERY pane in the doctor workspace, in one place. Three functions used to keep their own
// list of which panes to hide, and two of them had left the Reviews pane out — so opening a
// note from the review queue showed the whole queue stacked above the note. With one list,
// a pane added later is hidden everywhere or nowhere.
const DOCTOR_PANES = {
  overview: doctorOverviewPane,
  reviews: doctorReviewsPane,
  upcoming: doctorUpcomingPane,
  past: doctorPastPane,
  patients: doctorPatientsPane,
  patientDetail: doctorPatientDetailPane,
  appointmentDetail: doctorAppointmentDetailPane,
};

/** Shows exactly one pane and hides every other. */
function showDoctorPane(key) {
  Object.entries(DOCTOR_PANES).forEach(([name, element]) => {
    element?.classList.toggle("hidden", name !== key);
  });
}

/** Asks before a doctor-initiated navigation would throw away consult work. Returns true
 *  when it is fine to leave.
 *
 *  Two things are lost silently otherwise:
 *    - a LIVE RECORDING: leaving closes the audio socket, and the server ends the consult
 *      when it closes (consult.py's finally -> end_consult). A misclick on the sidebar
 *      ended the visit's recording with nothing said.
 *    - UNSAVED NOTE TEXT: the draft is only saved on an explicit button press.
 *
 *  Called from the handlers of the controls a doctor can reach while the appointment is
 *  open (sidebar, Back, log out, closing the tab) — deliberately NOT from showDoctorView
 *  itself, which also runs programmatically where a prompt would make no sense. */
function isConsultRecordingLive() {
  // The socket itself, not doctorRecordingStartedAtMs: that timestamp outlives the
  // recording (it is only reset when another appointment opens) and is also set for an
  // orphaned recording with no socket at all, where leaving ends nothing. What leaving
  // destroys is an open audio socket, so that is what is checked. A socket the server
  // already closed lingers in CLOSED until stopConsultRecording nulls it.
  return Boolean(consultSocket)
    && (consultSocket.readyState === WebSocket.OPEN || consultSocket.readyState === WebSocket.CONNECTING);
}

/** Unsaved text in either place: the SOAP draft, or the prescription/care plan/referral.
 *  Only while the appointment is open — the fields keep their last contents after it
 *  closes, and a hidden screen has nothing left to lose. */
function consultHasUnsavedText() {
  const detailOpen = doctorAppointmentDetailPane
    && !doctorAppointmentDetailPane.classList.contains("hidden");
  return Boolean(detailOpen) && (doctorNoteDirty || clinicalItemHasUnsavedText());
}

/** Makes "leave without saving" true: the flag is cleared and the prescription box goes
 *  back to what the server holds, so neither can prompt again for edits already abandoned. */
function abandonUnsavedConsultText() {
  doctorNoteDirty = false;
  if (doctorClinicalItemText && !doctorClinicalItemText.disabled) {
    doctorClinicalItemText.value = (doctorClinicalItem && doctorClinicalItem.content) || "";
  }
}

function confirmLeavingConsultWork() {
  const recording = isConsultRecordingLive();
  const dirty = consultHasUnsavedText();
  if (!recording && !dirty) return true;
  const message = recording
    ? "A recording is in progress. Leaving will end it."
      + (dirty ? " Your unsaved changes will also be lost." : "")
      + " Leave anyway?"
    : "You have unsaved changes to this consultation. Leave without saving them?";
  const leave = window.confirm(message);
  // Leaving means those edits are abandoned; a later re-render must not resurrect them.
  if (leave) abandonUnsavedConsultText();
  return leave;
}

// Closing or reloading the tab is the same loss by another route. Browsers show their own
// generic wording here; setting returnValue is what asks them to.
window.addEventListener("beforeunload", (event) => {
  if (!doctorAccessToken) return;
  if (isConsultRecordingLive() || consultHasUnsavedText()) {
    event.preventDefault();
    event.returnValue = "";
  }
});

function showDoctorView(view, { refetch = true } = {}) {
  const validViews = ["overview", "reviews", "upcoming", "past", "patients"];
  const nextView = validViews.includes(view) ? view : "overview";
  doctorCurrentView = nextView;

  // Any navigation away from the appointment detail pane must release the mic/socket —
  // this is the sidebar-nav path, distinct from (and previously missed by) the
  // dedicated "Back" button and showDoctorAppointmentDetail's own cleanup calls. Both
  // functions are safe no-ops when nothing is actually recording.
  stopConsultRecording();
  stopConsultStatusPolling();

  showDoctorPane(nextView);

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

  // Every view refetches on entry. It used to load only when its cache was EMPTY, so a
  // pane the doctor had already opened kept showing whatever was true the first time they
  // looked — switching away and back was not a way to get current data, which is most of
  // what "the app doesn't update" meant.
  //
  // With data already on screen the refetch runs in background mode, so the doctor sees
  // the numbers they had until the new ones land, rather than a "Loading…" flash over
  // figures that were perfectly good. With nothing on screen it runs in the foreground,
  // where "Loading…" is the honest thing to show.
  if (!refetch) return;

  const cached = {
    overview: true,
    upcoming: doctorUpcomingAppointments.length > 0,
    past: doctorPastAppointments.length > 0,
    patients: doctorPatientsCache.length > 0,
    reviews: doctorReviewsCache.length > 0,
  }[nextView];
  const mode = { background: Boolean(cached) };

  if (nextView === "upcoming") loadDoctorAppointments("upcoming", mode);
  if (nextView === "past") loadDoctorAppointments("past", mode);
  if (nextView === "patients") loadDoctorPatientsList(mode);
  if (nextView === "reviews") loadDoctorReviews(mode);
  if (nextView === "overview") void refreshActiveDoctorView({ force: true });
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

/** `background` marks an automatic refresh — see loadDoctorAiActivity. */
async function loadDoctorAppointments(scope, { background = false } = {}) {
  const listEl = scope === "upcoming" ? doctorUpcomingList : doctorPastList;
  const countEl = scope === "upcoming" ? doctorUpcomingCount : doctorPastCount;
  if (!background && countEl) countEl.textContent = "Loading...";
  try {
    const data = await doctorAuthedJson(`/doctor/appointments?scope=${scope}`);
    const appointments = Array.isArray(data.appointments) ? data.appointments : [];
    if (scope === "upcoming") {
      doctorUpcomingAppointments = appointments;
      doctorUpcomingLoaded = true;
      updateDoctorTodayStat(appointments);
      renderDoctorTodaySchedule();
    } else {
      doctorPastAppointments = appointments;
    }
    renderDoctorAppointmentsList(listEl, appointments, scope);
    if (countEl) countEl.textContent = `${appointments.length} appointment${appointments.length === 1 ? "" : "s"}`;
  } catch (error) {
    if (!background && countEl) countEl.textContent = "Unable to load.";
  }
}

// ── AI review queue ───────────────────────────────────────────────────────────

const REVIEW_ITEM_LABELS = {
  not_generated: "No note yet",
  draft: "AI generated",
  stale: "Needs regenerating",
  signed: "Doctor verified",
};

// Maps an item type to one of the existing admin-status-pill modifiers, so the queue
// reads with the same visual vocabulary as every other status badge in this app.
const REVIEW_ITEM_PILL = {
  not_generated: "",
  draft: "is-upcoming",
  stale: "is-cancelled",
  signed: "is-completed",
};

function relativeAge(isoString) {
  if (!isoString) return "";
  const elapsedMs = Date.now() - new Date(isoString).getTime();
  if (!Number.isFinite(elapsedMs) || elapsedMs < 0) return "";
  const minutes = Math.floor(elapsedMs / 60000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

/** `background` marks an automatic refresh — see loadDoctorAiActivity. A failed refresh
 *  must not wipe a queue the doctor is working from. */
async function loadDoctorReviews({ background = false } = {}) {
  if (!background && doctorReviewsCount) doctorReviewsCount.textContent = "Loading...";
  const scope = doctorReviewScope;
  try {
    const data = await doctorAuthedJson(`/doctor/reviews?scope=${scope}`);
    doctorReviewsCache = Array.isArray(data.reviews) ? data.reviews : [];
    doctorReviewCounts = data.counts || {};
    doctorReviewRanking = Array.isArray(data.ranked_consultation_ids)
      ? data.ranked_consultation_ids : [];
    renderDoctorReviews();
    // One request serves both when the Reviews pane is on Pending; on Signed, the pending
    // queue behind "Your next actions" is fetched on its own rather than left stale.
    if (scope === "pending") {
      acceptPendingPayload(data);
    } else {
      void loadDoctorPendingQueue({ background });
    }
    renderDoctorReviewCounts();
  } catch (error) {
    if (background) return;
    if (scope === "pending") {
      doctorPendingState = "error";
      renderDoctorOverviewReviews();
    }
    doctorReviewsCache = [];
    doctorReviewRanking = [];
    if (doctorReviewsCount) doctorReviewsCount.textContent = "Unable to load.";
    if (doctorReviewsList) {
      doctorReviewsList.replaceChildren();
      doctorReviewsList.classList.remove("hidden");
      doctorReviewsList.appendChild(
        buildDoctorEmptyState("Could not load your review queue. Try again shortly.")
      );
    }
    doctorReviewLanes?.classList.add("hidden");
  }
}

function acceptPendingPayload(data) {
  const rows = Array.isArray(data && data.reviews) ? data.reviews : [];
  const ranking = Array.isArray(data && data.ranked_consultation_ids) ? data.ranked_consultation_ids : [];
  doctorPendingQueue = rankRows(rows, ranking);
  doctorPendingState = "ready";
}

/** The pending queue on its own, for the Overview. `background` as everywhere else: a
 *  failed refresh keeps what is on screen rather than replacing it with an error. */
async function loadDoctorPendingQueue({ background = false } = {}) {
  if (!background) {
    doctorPendingState = "loading";
    renderDoctorOverviewReviews();
  }
  try {
    const data = await doctorAuthedJson("/doctor/reviews?scope=pending");
    acceptPendingPayload(data);
    // The counts describe pending work whichever tab is open, so these are current too.
    doctorReviewCounts = data.counts || doctorReviewCounts;
    renderDoctorReviewCounts();
  } catch (error) {
    if (background) return;
    doctorPendingState = "error";
    renderDoctorOverviewReviews();
  }
}

// The counts always describe PENDING work, whichever scope is being viewed — they are
// the "what still needs me" signal, and must not change meaning when the doctor flips to
// their signed history.
function renderDoctorReviewCounts() {
  const pending = Number(doctorReviewCounts.pending || 0);
  const attention = Number(doctorReviewCounts.stale || 0) + Number(doctorReviewCounts.low_quality_transcript || 0);

  if (doctorStatReviews) doctorStatReviews.textContent = String(pending);
  if (doctorStatAttention) doctorStatAttention.textContent = String(attention);
  if (doctorReviewNavCount) {
    doctorReviewNavCount.textContent = String(pending);
    doctorReviewNavCount.classList.toggle("hidden", pending === 0);
  }
  renderDoctorOverviewReviews();
}

function filteredDoctorReviews() {
  const term = doctorReviewSearchTerm.trim().toLowerCase();
  if (!term) return doctorReviewsCache;
  return doctorReviewsCache.filter((review) =>
    String(review.patient_name || "").toLowerCase().includes(term)
  );
}

/** A status chip. Text always via textContent — these carry AI-derived strings and a
 *  patient name, and must never become an XSS path (same rule as renderClinicalNote). */
function buildAiChip(text, modifier) {
  const chip = document.createElement("span");
  chip.className = `doctor-ai-chip${modifier ? ` ${modifier}` : ""}`;
  chip.textContent = text;
  return chip;
}

/** Which of the four SOAP sections are cited, and which are flagged (plan §4.5).
 *  Renders nothing at all when the note carries neither map, rather than four
 *  meaningless grey chips — an absent signal is not a negative one. */
function buildSectionChips(review) {
  const row = document.createElement("div");
  row.className = "doctor-ai-item-chips";
  const flags = review.confidence_flags && typeof review.confidence_flags === "object"
    ? review.confidence_flags : null;
  const citations = review.field_citations && typeof review.field_citations === "object"
    ? review.field_citations : null;
  if (!flags && !citations) return row;

  ["subjective", "objective", "assessment", "plan"].forEach((section) => {
    const flagged = flags ? flags[section] === true : false;
    const cited = citations ? Boolean(citations[section]) : false;
    const chip = buildAiChip(section[0].toUpperCase(), flagged ? "is-warn" : cited ? "is-ok" : "");
    chip.title = flagged
      ? `${section}: flagged for checking`
      : cited ? `${section}: cited to the transcript` : `${section}: no citation recorded`;
    row.appendChild(chip);
  });
  return row;
}

/** The action a row offers, derived from its state. Deliberately one action per row:
 *  a blocked note can only be regenerated, an undrafted one can only be generated, and
 *  everything else is reviewed. There is no bulk "sign" anywhere — signing is always a
 *  per-note act after reading it. */
function reviewPrimaryAction(review) {
  // Every action OPENS the note; none of them generates anything on its own. The labels
  // used to say "Generate" and "Regenerate", which is not what pressing them did — the
  // doctor generates on the note screen, where concise or detailed is chosen.
  if (review.is_stale) return { label: "Open to regenerate", className: "is-soft" };
  if (review.item_type === "not_generated") return { label: "Open to draft", className: "is-soft" };
  if (review.item_type === "signed") return { label: "View signed", className: "is-ghost" };
  return { label: "Review", className: "" };
}

function buildReviewCard(review) {
  const card = document.createElement("article");
  card.className = "doctor-ai-item";

  const icon = document.createElement("div");
  icon.className = "doctor-ai-item-ico";
  if (review.is_stale) icon.classList.add("is-bad");
  else if (review.low_quality_transcript || review.low_confidence_fields > 0) icon.classList.add("is-warn");
  else if (review.item_type === "signed") icon.classList.add("is-ok");
  icon.innerHTML = '<svg class="ai-i" viewBox="0 0 24 24" aria-hidden="true">'
    + '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    + '<path d="M14 2v6h6"/></svg>';

  const body = document.createElement("div");
  body.className = "doctor-ai-item-body";

  const title = document.createElement("div");
  title.className = "doctor-ai-item-title";
  title.textContent = review.patient_name || "Unknown patient";

  const when = review.appointment_start ? formatDateTime(review.appointment_start) : "Unscheduled";
  const meta = document.createElement("span");
  meta.className = "doctor-ai-item-meta";
  meta.textContent = ` · ${when}`;
  title.appendChild(meta);
  body.appendChild(title);

  const chips = document.createElement("div");
  chips.className = "doctor-ai-item-chips";

  // Ordered by how much each should change the doctor's behaviour before they open it.
  if (review.is_stale) {
    chips.appendChild(buildAiChip("Blocked", "is-bad"));
  } else if (review.item_type === "not_generated") {
    chips.appendChild(buildAiChip("No note yet", ""));
  } else if (review.item_type === "signed") {
    chips.appendChild(buildAiChip("Signed", "is-ok"));
  } else {
    chips.appendChild(buildAiChip("AI draft", "is-ai"));
  }
  if (review.low_quality_transcript) chips.appendChild(buildAiChip("Lower-quality transcript", "is-warn"));
  if (review.low_confidence_fields > 0) {
    chips.appendChild(buildAiChip(
      `${review.low_confidence_fields} field${review.low_confidence_fields === 1 ? "" : "s"} to check`,
      "is-warn"
    ));
  }
  if (review.is_edited && review.item_type !== "signed") chips.appendChild(buildAiChip("Edits in progress", ""));

  const age = review.item_type === "signed"
    ? relativeAge(review.signed_at)
    : relativeAge(review.generated_at || review.consult_ended_at);
  if (age) {
    const waited = document.createElement("span");
    waited.className = "doctor-ai-item-meta";
    waited.textContent = review.item_type === "signed" ? `Signed ${age} ago` : `Waiting ${age}`;
    chips.appendChild(waited);
  }
  body.appendChild(chips);

  // The server's one-line explanation of WHY this row is in the state it is
  // (doctor_workspace.explain_item_status). Absent on the completed scope.
  if (review.ai_explanation) {
    const explanation = document.createElement("div");
    explanation.className = "doctor-ai-item-meta";
    explanation.style.marginTop = "6px";
    explanation.textContent = review.ai_explanation;
    body.appendChild(explanation);
  }

  const sectionChips = buildSectionChips(review);
  if (sectionChips.childElementCount) body.appendChild(sectionChips);

  const action = reviewPrimaryAction(review);
  const actionBtn = document.createElement("button");
  actionBtn.type = "button";
  actionBtn.className = `doctor-ai-btn is-sm ${action.className}`.trim();
  actionBtn.textContent = action.label;
  actionBtn.setAttribute(
    "aria-label",
    `${action.label}: ${review.patient_name || "this patient"}, ${when}`
  );
  actionBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    openReviewFromQueue(review);
  });

  // The whole card opens the note too — it looked clickable (it highlights on hover) and
  // only its small button was. The card stays an <article> with a mouse handler rather than
  // becoming a button itself: it already CONTAINS a button, and a button inside a button is
  // invalid and confuses screen readers. Keyboard and screen-reader users have the inner
  // button, which does the same thing and is named for the patient.
  card.classList.add("is-clickable");
  card.addEventListener("click", () => openReviewFromQueue(review));

  card.append(icon, body, actionBtn);
  return card;
}

function buildDoctorEmptyState(message) {
  const note = document.createElement("p");
  note.className = "doctor-ai-empty";
  note.textContent = message;
  return note;
}

/** Orders a set of rows by the server's ranking (doctor_workspace.rank_pending_items,
 *  delivered as ranked_consultation_ids). The ranking rules live server-side so they are
 *  unit-tested in one place; this only applies the order it is given. Rows the server did
 *  not rank (the completed scope) keep their existing order. */
function applyServerRanking(reviews) {
  return rankRows(reviews, doctorReviewRanking);
}

function rankRows(reviews, ranking) {
  if (!ranking.length) return reviews;
  const position = new Map(ranking.map((id, index) => [id, index]));
  return [...reviews].sort(
    (a, b) =>
      (position.has(a.consultation_id) ? position.get(a.consultation_id) : Number.MAX_SAFE_INTEGER) -
      (position.has(b.consultation_id) ? position.get(b.consultation_id) : Number.MAX_SAFE_INTEGER)
  );
}

function renderDoctorReviewLanes(reviews) {
  const lanes = [
    { key: "quick_review", list: doctorLaneQuick, count: doctorLaneQuickCount,
      empty: "Nothing to review right now." },
    { key: "needs_attention", list: doctorLaneAttention, count: doctorLaneAttentionCount,
      empty: "Nothing is blocked." },
    { key: "not_drafted", list: doctorLaneNotDrafted, count: doctorLaneNotDraftedCount,
      empty: "Every transcript has a draft." },
  ];

  lanes.forEach(({ key, list, count, empty }) => {
    if (!list) return;
    list.replaceChildren();
    // Grouped by the server (doctor_workspace.group_into_lanes) and filtered here only by
    // the doctor's own search term, so lane membership cannot drift from the server's rule.
    const rows = applyServerRanking(reviews.filter((review) => review.lane === key));
    if (count) count.textContent = String(rows.length);
    if (!rows.length) {
      list.appendChild(buildDoctorEmptyState(empty));
      return;
    }
    rows.forEach((review) => list.appendChild(buildReviewCard(review)));
  });
}

function renderDoctorReviews() {
  if (!doctorReviewsList) return;
  doctorReviewsList.replaceChildren();

  const reviews = filteredDoctorReviews();
  const isPending = doctorReviewScope === "pending";

  if (doctorReviewsCount) {
    doctorReviewsCount.textContent = `${reviews.length} item${reviews.length === 1 ? "" : "s"}`;
  }

  // Lanes are a triage view of outstanding work; signed history has no triage, so that
  // scope renders as a flat list instead.
  doctorReviewLanes?.classList.toggle("hidden", !isPending);
  doctorReviewsList.classList.toggle("hidden", isPending);

  const undrafted = reviews.filter((review) => review.item_type === "not_generated").length;
  if (doctorDraftAllBtn) {
    doctorDraftAllBtn.classList.toggle("hidden", !isPending || undrafted === 0);
    if (doctorDraftAllLabel) {
      doctorDraftAllLabel.textContent =
        `Draft ${undrafted} missing note${undrafted === 1 ? "" : "s"}`;
    }
  }

  if (isPending) {
    renderDoctorReviewLanes(reviews);
    return;
  }

  if (!reviews.length) {
    // An empty pending queue is a good state, not an error or a loading state.
    doctorReviewsList.appendChild(buildDoctorEmptyState(
      doctorReviewSearchTerm
        ? "No reviews match that patient name."
        : "You have not signed any clinical notes yet."
    ));
    return;
  }

  reviews.forEach((review) => doctorReviewsList.appendChild(buildReviewCard(review)));
}

function renderDoctorOverviewReviews() {
  renderDoctorStartReviewButton();
  // Today's cards carry a "Drafted" chip read from this same queue. They were drawn only
  // when appointments loaded, so the chip depended on which request happened to finish
  // first; redrawn here, it always reflects the queue. Only once appointments have loaded:
  // before that, an empty list would render as "No appointments scheduled today".
  if (doctorUpcomingLoaded) renderDoctorTodaySchedule();
  if (!doctorOverviewReviews) return;
  doctorOverviewReviews.replaceChildren();

  // Overview shows only the head of the AI-ranked queue — the full list lives in the
  // Reviews pane, and this preview must not become a second place to work through it.
  // Always the PENDING queue, whatever tab the Reviews pane was left on.
  const preview = doctorPendingQueue.slice(0, 4);

  if (!preview.length) {
    // Three different statements. "Nothing is waiting" is a claim about the doctor's work
    // and must not be made while the queue is still loading or could not be loaded.
    doctorOverviewReviews.appendChild(buildDoctorEmptyState(
      doctorPendingState === "loading" ? "Loading your next actions…"
        : doctorPendingState === "error" ? "Your next actions could not be loaded. They will retry shortly."
          : "Nothing is waiting for your review."
    ));
    return;
  }

  preview.forEach((review) => doctorOverviewReviews.appendChild(buildReviewCard(review)));
}

/** "Start AI review" opens the top-ranked item directly. It used to do exactly what "See
 *  all" and both stat cards do — switch to the Reviews pane — so four controls on one
 *  screen shared one action. Disabled, and saying so, when there is nothing to start. */
function renderDoctorStartReviewButton() {
  if (!doctorStartReviewBtn) return;
  const first = doctorPendingQueue[0];
  doctorStartReviewBtn.disabled = !first;
  const label = doctorStartReviewBtn.querySelector("[data-start-review-label]");
  if (label) {
    label.textContent = first ? "Start AI review"
      : doctorPendingState === "ready" ? "Nothing to review" : "Start AI review";
  }
  doctorStartReviewBtn.title = first
    ? `Opens the first item in your queue: ${first.patient_name || "a patient"}`
    : "";
}

/** Opens a queue row on the existing appointment detail screen rather than a parallel
 *  one, so the doctor works in a single mental model. The queue row carries booking_id,
 *  so the matching cached appointment is preferred; if it isn't cached (a past visit the
 *  doctor never opened this session), the row itself carries enough to render the pane. */
/** @param status     - the appointment's own status, when the caller knows it (a visit from
 *                       a patient's history may be booked, not completed).
 *  @param returnView - where Back goes. Defaults to the current top-level view; the patient
 *                       page passes "patientDetail" so Back returns to that patient. */
async function openReviewFromQueue(review, { status = null, returnView = null } = {}) {
  const back = returnView || doctorCurrentView;
  const cached =
    doctorUpcomingAppointments.find((appt) => appt.booking_id === review.booking_id) ||
    doctorPastAppointments.find((appt) => appt.booking_id === review.booking_id);

  if (cached) {
    showDoctorAppointmentDetail(cached, back);
    return;
  }

  // Synthesised from the queue row. consult_id/consult_status come straight from the
  // same query, so the consult and note blocks render exactly as they would from a
  // refetched appointments list.
  //
  // Also used by the activity drill-down, whose rows share these field names and carry
  // the consult's real status. Review rows do not send one — the review queue only ever
  // contains transcript_ready consults — hence the fallback.
  showDoctorAppointmentDetail(
    {
      booking_id: review.booking_id,
      patient_id: review.patient_id,
      patient_name: review.patient_name,
      department: review.department,
      start_time: review.appointment_start,
      status: status || "completed",
      booking_note: null,
      consult_id: review.consultation_id,
      consult_status: review.consult_status || "transcript_ready",
      consult_started_at: null,
      consult_ended_at: review.consult_ended_at,
    },
    back
  );
}

/** @param load - false when the caller is about to load the Reviews pane itself (switching
 *                views does), so the queue is not fetched twice. */
function setDoctorReviewScope(scope, { load = true } = {}) {
  const next = scope === "completed" ? "completed" : "pending";
  syncDoctorReviewScopeTabs(next);
  if (next === doctorReviewScope) return;
  doctorReviewScope = next;
  if (load) loadDoctorReviews();
}

function syncDoctorReviewScopeTabs(scope) {
  doctorReviewScopeButtons.forEach((button) => {
    const isActive = button.dataset.reviewScope === scope;
    button.classList.toggle("is-active", isActive);
    // role="tab" promises this state to assistive technology; it was set once in the
    // markup and never updated, so "Signed" was announced as unselected while showing.
    button.setAttribute("aria-selected", isActive ? "true" : "false");
  });
}

/** Opens the Reviews pane on its Pending tab, optionally at one lane. Used by "See all" and
 *  the two stat cards, which used to open Reviews on whatever tab it was last left on. */
function openDoctorReviews({ lane = null } = {}) {
  if (doctorReviewScope !== "pending") {
    // The cache holds SIGNED rows. Emptied, so the view switch below loads in the
    // foreground ("Loading…") instead of treating signed rows as a pending queue.
    doctorReviewsCache = [];
  }
  setDoctorReviewScope("pending", { load: false });
  // The lanes are the Pending view; shown now so a lane can be scrolled to before the
  // queue arrives (they were hidden if Reviews was last left on Signed).
  doctorReviewLanes?.classList.remove("hidden");
  doctorReviewsList?.classList.add("hidden");
  showDoctorView("reviews");
  if (!lane) return;
  // The lanes are static sections, so this does not wait for the queue to load.
  const heading = document.querySelector(
    { needs_attention: "#doctorLaneAttentionTitle", quick_review: "#doctorLaneQuickTitle",
      not_drafted: "#doctorLaneNotDraftedTitle" }[lane]
  );
  if (!heading) return;
  heading.setAttribute("tabindex", "-1");
  heading.scrollIntoView({ block: "start", behavior: "smooth" });
  heading.focus({ preventScroll: true });
}

// ── Today's schedule (Overview) ───────────────────────────────────────────────
// Rendered from doctorUpcomingAppointments, which the dashboard already holds — this
// costs no additional request.
function renderDoctorTodaySchedule() {
  if (!doctorTodaySchedule) return;
  // This list is redrawn on every refresh. Remember which control had focus so a keyboard
  // user is not thrown back to the top of the page each time it redraws.
  const focused = doctorTodaySchedule.contains(document.activeElement)
    ? document.activeElement.getAttribute("aria-controls") : null;
  doctorTodaySchedule.replaceChildren();
  if (focused) {
    queueMicrotask(() => doctorTodaySchedule.querySelector(`[aria-controls="${focused}"]`)?.focus());
  }

  const today = _istToday();
  const todays = doctorUpcomingAppointments.filter(
    (appt) => String(appt.start_time || "").slice(0, 10) === today
  );

  if (doctorTodayScheduleCount) {
    doctorTodayScheduleCount.textContent = `${todays.length} visit${todays.length === 1 ? "" : "s"}`;
  }

  if (!todays.length) {
    const note = document.createElement("p");
    note.className = "panel-note";
    note.textContent = "No appointments scheduled today.";
    doctorTodaySchedule.appendChild(note);
    return;
  }

  todays.forEach((appt) => {
    const card = document.createElement("article");
    card.className = "doctor-ai-item";

    const icon = document.createElement("div");
    icon.className = "doctor-ai-item-ico";
    icon.innerHTML = '<svg class="ai-i" viewBox="0 0 24 24" aria-hidden="true">'
      + '<circle cx="9" cy="8" r="4"/><path d="M2 21c0-4 3-7 7-7s7 3 7 7"/></svg>';

    // The row's main area opens the appointment. A <button>, not a clickable <div>: the
    // div could not be reached or activated from the keyboard at all. It contains only text,
    // so it can be a button without nesting the "AI brief" control inside it.
    const body = document.createElement("button");
    body.type = "button";
    body.className = "doctor-ai-item-body doctor-ai-item-link";
    const title = document.createElement("span");
    title.className = "doctor-ai-item-title";
    title.textContent = appt.patient_name || "Unknown patient";
    const meta = document.createElement("span");
    meta.className = "doctor-ai-item-meta";
    meta.textContent = `${formatDateTime(appt.start_time)} · ${appt.department || "Department"}`;
    body.append(title, meta);
    body.setAttribute("aria-label",
      `Open appointment: ${appt.patient_name || "patient"}, ${formatDateTime(appt.start_time)}`);

    card.append(icon, body);

    // AI status for this visit, derived only from state the appointments payload already
    // carries. A visit with no consult yet gets no AI chip at all rather than a
    // speculative one — AI has genuinely not done anything for it.
    //
    // From the PENDING queue, not doctorReviewsCache: that holds whatever tab Reviews was
    // left on, so the chip depended on it.
    const review = doctorPendingQueue.find((row) => row.booking_id === appt.booking_id);
    if (review && review.item_type !== "not_generated") {
      card.appendChild(buildAiChip("Drafted", "is-ai"));
    } else if (appt.consult_status === "transcript_ready") {
      card.appendChild(buildAiChip("Transcript captured", "is-ok"));
    } else if (appt.consult_status === "transcribing") {
      card.appendChild(buildAiChip("Drafting", "is-ai"));
    }

    const durationBadge = buildDurationBadge(appt);
    if (durationBadge) card.appendChild(durationBadge);

    // The visit brief, inline. It used to be an "AI brief" button that opened the whole
    // patient page — a summary of the patient, not of this visit — and only for visits with
    // no consult yet. Preparing for the next patient should not mean leaving the schedule.
    const isOpen = doctorTodayBriefOpen === appt.booking_id;
    const panelId = `doctorTodayBrief-${appt.booking_id}`;
    const briefBtn = document.createElement("button");
    briefBtn.type = "button";
    briefBtn.className = "doctor-ai-btn is-ghost is-sm";
    briefBtn.textContent = isOpen ? "Brief ▴" : "Brief ▾";
    briefBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    briefBtn.setAttribute("aria-controls", panelId);
    briefBtn.setAttribute("aria-label",
      `${isOpen ? "Hide" : "Show"} the visit brief for ${appt.patient_name || "this patient"}`);
    briefBtn.addEventListener("click", () => toggleDoctorTodayBrief(appt.booking_id));
    card.appendChild(briefBtn);

    body.addEventListener("click", () => showDoctorAppointmentDetail(appt, "overview"));
    doctorTodaySchedule.appendChild(card);

    if (isOpen) {
      const panel = document.createElement("div");
      panel.id = panelId;
      panel.className = "doctor-today-brief";
      panel.setAttribute("role", "region");
      panel.setAttribute("aria-label", `Visit brief for ${appt.patient_name || "this patient"}`);
      const content = document.createElement("div");
      content.className = "doctor-today-brief-body";
      const cached = doctorTodayBriefCache.get(appt.booking_id);
      const failed = doctorTodayBriefErrors.get(appt.booking_id);
      if (cached) renderDoctorVisitBrief(content, cached);
      else if (failed) renderDoctorVisitBrief(content, null, { error: failed });
      else renderDoctorVisitBrief(content, null, { loading: true });
      const open = document.createElement("button");
      open.type = "button";
      open.className = "doctor-ai-btn is-soft is-sm";
      open.textContent = "Open appointment →";
      open.addEventListener("click", () => showDoctorAppointmentDetail(appt, "overview"));
      panel.append(content, open);
      doctorTodaySchedule.appendChild(panel);
    }
  });
}

// ── AI activity summary and log (Overview, plan §4.1 and §4.3) ────────────────
// Every figure rendered here comes from /doctor/ai/activity-summary. Nothing is
// hard-coded, and a count the backend could not measure renders as 0, never as a
// plausible-looking placeholder.

const DOCTOR_ACTIVITY_TILES = [
  {
    key: "notes_drafted",
    label: "SOAP notes drafted from consultation transcripts",
    title: "Notes AI drafted",
    // Counts drafting EVENTS, so a note regenerated twice appears twice — said up front
    // so two rows for one patient does not read as a duplicate or an error.
    explain: "Each time AI drafted a note. A note regenerated more than once appears once per draft.",
    empty: "AI drafted no notes in this period.",
  },
  {
    key: "documents_summarized",
    label: "Patient documents read and summarised",
    title: "Documents AI summarised",
    // Honest about what this is: the patient's uploads, for anyone this doctor treats,
    // which is why a colleague sharing the patient sees the same documents.
    explain: "Documents your patients uploaded in this period that finished processing.",
    empty: "No documents from your patients finished processing in this period.",
  },
  {
    key: "fields_flagged",
    label: "Fields flagged where evidence was thin",
    title: "Sections flagged for a closer look",
    explain: "Note sections where the transcript did not clearly support what AI wrote. Check these before signing.",
    empty: "No sections were flagged in this period.",
  },
  {
    key: "notes_blocked",
    label: "Notes held back: transcript too weak to sign",
    title: "Notes held back",
    // Current state, not the window — the only tile where that is true, so the list says
    // so rather than letting the period label above imply otherwise.
    explain: "Notes held back right now because the transcript could not support them. This does not change with the period.",
    empty: "No notes are being held back.",
  },
];

const DOCTOR_WINDOW_LABELS = { last_visit: "since your last visit", "24h": "last 24 hours", "7d": "last 7 days" };

function doctorActivityTileSpec(key) {
  return DOCTOR_ACTIVITY_TILES.find((tile) => tile.key === key) || null;
}

function renderDoctorActivitySummary(summary, { loading = false } = {}) {
  const counts = (summary && summary.counts) || {};

  if (doctorActivityHeadline) {
    doctorActivityHeadline.textContent = summary
      ? summary.headline || ""
      : loading
        ? "Checking what AI did while you were away…"
        // Failure must be stated, never dressed up as "no activity" — those mean very
        // different things to a doctor deciding whether anything needs them.
        : "AI activity could not be loaded right now.";
  }
  if (doctorActivityWindowText) {
    // Labelled from `window` — the period the server ACTUALLY applied — not from the one
    // that was requested. They differ when "since last visit" cannot be honoured because
    // the previous login is too recent to be a real visit, and saying "since your last
    // visit" over 24h figures would misdescribe every number beside it.
    // Falls back to the window we asked for if the payload does not name one. Safe
    // because the two differ only on a fallback, and that case is handled above.
    const applied = (summary && summary.window) || doctorActivityWindow;
    const label = { last_visit: "since your last visit", "24h": "last 24 hours", "7d": "last 7 days" }[applied];
    doctorActivityWindowText.textContent = !summary
      ? "AI activity"
      : summary.window_is_fallback
        // Said plainly: the doctor asked for one window and is reading another.
        ? "AI activity · last 24 hours (you were here very recently)"
        : `AI activity · ${label || "recent"}`;
  }
  if (doctorOverviewSubhead) {
    doctorOverviewSubhead.textContent = summary
      ? summary.headline || "AI worked through your consultations."
      : loading
        ? "Checking what AI did while you were away…"
        : "Your workspace is usable; the AI summary could not be loaded.";
  }

  if (!doctorActivityTiles) return;
  doctorActivityTiles.replaceChildren();
  DOCTOR_ACTIVITY_TILES.forEach(({ key, label }) => {
    // A disclosure button, not a link: it reveals the list in place, it does not navigate.
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "doctor-ai-tile";
    tile.dataset.activityTile = key;
    tile.setAttribute("aria-controls", "doctorActivityDrill");
    const isOpen = doctorActivityDrillTile === key;
    tile.setAttribute("aria-expanded", isOpen ? "true" : "false");
    tile.classList.toggle("is-open", isOpen);
    // Nothing to open until the number is real. A drill-down under an em dash would be a
    // list for a figure the doctor was never shown.
    tile.disabled = !summary;

    const value = document.createElement("div");
    value.className = "ai-big";
    // An em dash, not 0, when there is no measurement: "0 notes drafted" is a claim, and
    // it must not be made on the strength of a request that never answered.
    value.textContent = summary ? String(Number(counts[key] || 0)) : "—";
    const caption = document.createElement("span");
    caption.textContent = label;
    const affordance = document.createElement("span");
    affordance.className = "doctor-ai-tile-more";
    affordance.setAttribute("aria-hidden", "true");
    affordance.textContent = isOpen ? "Hide ▴" : "View ▾";
    tile.append(value, caption, affordance);
    tile.addEventListener("click", () => toggleDoctorActivityDrill(key));
    doctorActivityTiles.appendChild(tile);
  });
}

// ── What is behind each tile ─────────────────────────────────────────────────
// Every list comes from /doctor/ai/activity-items, which builds it from the same SQL
// predicate as the tile's number. The two are reconciled by test_doctor_activity_items, so
// clicking "2" shows two things — never a different set that happens to share the label.

function toggleDoctorActivityDrill(key) {
  if (doctorActivityDrillTile === key) {
    closeDoctorActivityDrill();
    return;
  }
  doctorActivityDrillTile = key;
  syncDoctorActivityTileState();
  doctorActivityDrill?.classList.remove("hidden");
  void loadDoctorActivityDrill();
}

function closeDoctorActivityDrill({ restoreFocus = false } = {}) {
  const was = doctorActivityDrillTile;
  doctorActivityDrillTile = null;
  // Invalidate anything in flight, so a late response cannot reopen what was just closed.
  doctorActivityDrillRequest += 1;
  doctorActivityDrill?.classList.add("hidden");
  syncDoctorActivityTileState();
  if (restoreFocus && was) {
    doctorActivityTiles?.querySelector(`[data-activity-tile="${was}"]`)?.focus();
  }
}

/** Updates the open/closed state on the existing tiles without rebuilding them, so a
 *  keyboard user's focus stays on the tile they just pressed. */
function syncDoctorActivityTileState() {
  doctorActivityTiles?.querySelectorAll("[data-activity-tile]").forEach((tile) => {
    const isOpen = tile.dataset.activityTile === doctorActivityDrillTile;
    tile.setAttribute("aria-expanded", isOpen ? "true" : "false");
    tile.classList.toggle("is-open", isOpen);
    const affordance = tile.querySelector(".doctor-ai-tile-more");
    if (affordance) affordance.textContent = isOpen ? "Hide ▴" : "View ▾";
  });
}

/** `background` has the same meaning as in loadDoctorAiActivity: an automatic refresh must
 *  never replace a list that is on screen and correct with a loading or error state. */
async function loadDoctorActivityDrill({ background = false } = {}) {
  const key = doctorActivityDrillTile;
  if (!key) return;
  const requestId = ++doctorActivityDrillRequest;
  if (!background) renderDoctorActivityDrill(key, null, { loading: true });
  try {
    const query = `?tile=${encodeURIComponent(key)}&window=${encodeURIComponent(doctorActivityWindow)}`;
    const payload = await doctorAuthedJson(`/doctor/ai/activity-items${query}`);
    // The doctor may have switched tile, switched window or closed the panel while this
    // was in flight. Only the newest request is allowed to paint.
    if (requestId !== doctorActivityDrillRequest || doctorActivityDrillTile !== key) return;
    renderDoctorActivityDrill(key, payload);
  } catch (error) {
    if (requestId !== doctorActivityDrillRequest || doctorActivityDrillTile !== key) return;
    if (!background) renderDoctorActivityDrill(key, null, { error: error.message });
  }
}

function describeDoctorNoteState(item) {
  if (item.consult_status === "discarded") return "Consult discarded — note no longer available";
  return {
    draft: "Draft — awaiting your review",
    stale: "Held back — needs regenerating",
    signed: "Signed",
  }[item.note_status] || "Not drafted";
}

function renderDoctorActivityDrill(key, payload, { loading = false, error = "" } = {}) {
  if (!doctorActivityDrill || !doctorActivityDrillList) return;
  const spec = doctorActivityTileSpec(key);
  if (!spec) return;

  if (doctorActivityDrillTitle) doctorActivityDrillTitle.textContent = spec.title;
  if (doctorActivityDrillSub) {
    // Labelled from the window the server actually applied, as the chip above is.
    const applied = (payload && payload.window) || doctorActivityWindow;
    const period = key === "notes_blocked"
      ? "Right now"
      : `${(DOCTOR_WINDOW_LABELS[applied] || "recent").replace(/^./, (c) => c.toUpperCase())}`;
    doctorActivityDrillSub.textContent = `${period} · ${spec.explain}`;
  }

  doctorActivityDrillList.replaceChildren();
  if (loading) {
    doctorActivityDrillList.appendChild(buildDoctorDrillMessage("Loading…"));
    return;
  }
  if (error) {
    // Stated as a failure, never shown as an empty list: "nothing here" and "we could not
    // check" mean very different things to a doctor deciding whether anything needs them.
    doctorActivityDrillList.appendChild(buildDoctorDrillMessage(`Could not load this list. ${error}`));
    return;
  }

  const items = (payload && payload.items) || [];
  if (!items.length) {
    doctorActivityDrillList.appendChild(buildDoctorDrillMessage(spec.empty));
    return;
  }

  items.forEach((item) => doctorActivityDrillList.appendChild(buildDoctorDrillRow(key, item)));
  if (payload.truncated) {
    doctorActivityDrillList.appendChild(buildDoctorDrillMessage(
      `Showing the ${items.length} most recent. Narrow the period to see older ones.`
    ));
  }
}

function buildDoctorDrillMessage(text) {
  const message = document.createElement("p");
  message.className = "doctor-ai-drill-message";
  message.textContent = text;
  return message;
}

function buildDoctorDrillRow(key, item) {
  const isDocument = key === "documents_summarized";
  const openable = Boolean(item.openable);
  // A row that cannot be opened is not a button: a control that does nothing when
  // pressed is worse than plain text that says why.
  const row = document.createElement(openable ? "button" : "div");
  row.className = "doctor-ai-drill-row";
  if (openable) row.type = "button";
  else row.classList.add("is-inert");

  const main = document.createElement("div");
  main.className = "doctor-ai-drill-main";
  const name = document.createElement("div");
  name.className = "doctor-ai-drill-name";
  name.textContent = item.patient_name || "Unknown patient";
  main.appendChild(name);

  const meta = document.createElement("div");
  meta.className = "doctor-ai-drill-meta";
  const bits = [];
  if (isDocument) {
    bits.push(item.original_filename || "Document");
    if (item.document_type && item.document_type !== "other") bits.push(formatDocumentType(item.document_type));
    if (item.clinical_date) bits.push(`dated ${item.clinical_date}`);
  } else {
    if (item.occurred_at) bits.push(formatDateTime(item.occurred_at));
    if (item.style) bits.push(`${item.style} note`);
  }
  meta.textContent = bits.join(" · ");
  main.appendChild(meta);

  // The one line that answers "so what do I do with this".
  const state = document.createElement("div");
  state.className = "doctor-ai-drill-state";
  if (isDocument) {
    // What the verifier did to the model's summary...
    state.textContent = {
      passed: "Every AI sentence matched to the document",
      partial: "AI summary partly matched — some sentences were removed",
      failed: "No AI sentence could be matched — read the original",
    }[item.summary_verification] || "No AI summary yet";
    // ...and, separately, whether a clinician has checked it.
    state.appendChild(document.createTextNode(" "));
    state.appendChild(buildDocumentReviewChip(item.document_id, item.review));
  } else if (key === "fields_flagged") {
    const sections = (item.flagged_sections || []).map((s) => s.charAt(0).toUpperCase() + s.slice(1));
    state.textContent = `Flagged: ${sections.join(", ")} · ${describeDoctorNoteState(item)}`;
  } else {
    state.textContent = describeDoctorNoteState(item);
  }
  main.appendChild(state);
  row.appendChild(main);

  if (openable) {
    const go = document.createElement("span");
    go.className = "doctor-ai-drill-go";
    go.setAttribute("aria-hidden", "true");
    go.textContent = isDocument ? "View document →" : "Open note →";
    row.appendChild(go);
    // The accessible name is the whole row's text plus what pressing it does.
    row.setAttribute("aria-label", `${isDocument ? "View document" : "Open note"}: ${[name.textContent, meta.textContent, state.textContent].filter(Boolean).join(", ")}`);
    row.addEventListener("click", () => {
      if (isDocument) {
        void openDoctorDocumentViewer(item.patient_id, item);
      } else {
        void openReviewFromQueue(item);
      }
    });
  }
  return row;
}

function renderDoctorActivityLog(events, { loading = false, error = false } = {}) {
  if (!doctorActivityLog) return;
  doctorActivityLog.replaceChildren();

  if (loading) {
    doctorActivityLog.appendChild(buildDoctorEmptyState("Loading…"));
    return;
  }
  if (error) {
    doctorActivityLog.appendChild(buildDoctorEmptyState("The activity log could not be loaded right now."));
    return;
  }
  if (!events || !events.length) {
    doctorActivityLog.appendChild(buildDoctorEmptyState("No recorded AI activity yet."));
    return;
  }

  // Collapsed: the latest few. Expanded ("Full audit"): everything fetched, up to the
  // endpoint's maximum. It used to fetch 25, show 8, and offer no way to see the rest.
  const shown = doctorActivityLogExpanded ? events : events.slice(0, DOCTOR_ACTIVITY_LOG_COLLAPSED);
  shown.forEach((event) => {
    // A row that can open its appointment is a button; one that cannot (a document event,
    // or a consult since discarded) stays plain text rather than a control that does nothing.
    const openable = Boolean(event.openable);
    const row = document.createElement(openable ? "button" : "div");
    row.className = "doctor-ai-feed-row";
    if (openable) {
      row.type = "button";
      row.classList.add("is-openable");
      // The accessible name says what opens, without the patient's name — the log does not
      // show names on the dashboard, and a screen reader announcing them would.
      row.setAttribute("aria-label",
        `${event.label || "Activity"}, ${event.occurred_at ? formatDateTime(event.occurred_at) : ""}. Open this consultation`);
      row.addEventListener("click", () => { void openReviewFromQueue(event); });
    }

    const time = document.createElement("div");
    time.className = "doctor-ai-feed-time";
    time.textContent = event.occurred_at ? formatDateTime(event.occurred_at) : "";

    const body = document.createElement("div");
    body.className = "doctor-ai-grow";
    const title = document.createElement("div");
    title.className = "doctor-ai-item-title";
    title.style.fontSize = "13.5px";
    title.textContent = event.label || event.action || "";
    body.appendChild(title);

    // Only the allowlisted detail keys the server chose to expose are rendered, and each
    // is labelled — never the raw audit metadata blob.
    // No model name: which model wrote a note is recorded in the audit log, but it is not
    // something the doctor is shown. The server no longer sends it either
    // (doctor_ai_activity._FEED_ACTIONS), so this is the second of two gates.
    const detail = event.detail || {};
    const bits = [];
    // "detailed note" / "concise note" — reads as a phrase. It used to sit beside the
    // model name as "detailed detail level · gpt-4o-mini"; with the model gone it is the
    // only thing on this line, so the clumsiness shows.
    if (detail.style) bits.push(`${detail.style} note`);
    if (detail.section) bits.push(detail.section);
    if (detail.reason === "transcript_labels_corrected") bits.push("transcript labels were corrected");
    // Said on the row, so "Drafted a clinical note" for a consult that was later discarded
    // does not send the doctor looking for a note that is no longer anywhere to be found.
    if (event.consult_status === "discarded" && event.action !== "consult_discarded") {
      bits.push("consult later discarded");
    }
    if (bits.length) {
      const meta = document.createElement("div");
      meta.className = "doctor-ai-item-meta";
      meta.textContent = bits.join(" · ");
      body.appendChild(meta);
    }

    if (!event.is_ai) {
      const chip = buildAiChip("You", "");
      chip.style.marginLeft = "auto";
      row.append(time, body, chip);
    } else {
      row.append(time, body);
    }
    doctorActivityLog.appendChild(row);
  });
}

/** Loads the overview's AI panels. Deliberately non-fatal: the rest of the dashboard is
 *  usable without them, so a failure renders an honest empty state rather than blocking
 *  the doctor's actual work or showing a fabricated summary.
 *
 *  `background` marks an automatic refresh rather than a load the doctor asked for. It
 *  changes the failure behaviour, not the request: on a first load, "could not load" is
 *  the honest thing to show, but on a refresh it would replace figures that are on screen
 *  and correct with an empty panel, purely because one poll lost the network. So a
 *  background failure keeps what is already there. */
async function loadDoctorAiActivity({ background = false } = {}) {
  if (!background) {
    // Paint the tiles immediately, so the hero is never a flat empty panel while the
    // request is in flight. They show zeros with a "checking" caption rather than numbers
    // presented as measured — a placeholder figure on a clinical dashboard would be read
    // as fact.
    renderDoctorActivitySummary(null, { loading: true });
    renderDoctorActivityLog(null, { loading: true });
  }

  // The two panels are loaded independently: one failing must not blank the other.
  try {
    const query = `?window=${encodeURIComponent(doctorActivityWindow)}`;
    renderDoctorActivitySummary(await doctorAuthedJson(`/doctor/ai/activity-summary${query}`));
  } catch (error) {
    if (!background) renderDoctorActivitySummary(null);
  }
  // An open list refreshes with its tile — otherwise the number would move and the list
  // under it would not, which is exactly the disagreement the drill-down must never show.
  // Not awaited: the activity log below is independent of it.
  if (doctorActivityDrillTile) void loadDoctorActivityDrill({ background });
  await loadDoctorActivityLogOnly({ background });
}

/** "Full audit": expands the log to everything the endpoint will return, or back. */
function toggleDoctorActivityLog() {
  doctorActivityLogExpanded = !doctorActivityLogExpanded;
  if (doctorActivityLogToggle) {
    doctorActivityLogToggle.textContent = doctorActivityLogExpanded ? "Show recent" : "Full audit";
    doctorActivityLogToggle.setAttribute("aria-expanded", doctorActivityLogExpanded ? "true" : "false");
  }
  void loadDoctorActivityLogOnly();
}

async function loadDoctorActivityLogOnly({ background = false } = {}) {
  try {
    const limit = doctorActivityLogExpanded ? DOCTOR_ACTIVITY_LOG_MAX : 25;
    const log = await doctorAuthedJson(`/doctor/ai/activity-log?limit=${limit}`);
    renderDoctorActivityLog((log && log.events) || []);
  } catch (error) {
    // Not "No recorded AI activity yet" — that is a statement about the doctor's record,
    // and a failed request says nothing about it. A background refresh keeps what is shown.
    if (!background) renderDoctorActivityLog(null, { error: true });
  }
}

/** Switches which period the activity counts cover. Only the three windowed counts move;
 *  notes_blocked and awaiting_signature are current state and are the same in every
 *  window, which is why their captions do not name a period. */
function setDoctorActivityWindow(window_) {
  const next = ["last_visit", "24h", "7d"].includes(window_) ? window_ : "last_visit";
  doctorActivityWindow = next;
  doctorActivityWindowButtons.forEach((button) => {
    const isActive = button.dataset.activityWindow === next;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
  // Foreground: the doctor asked for this, so "checking…" is the honest response and a
  // failure must be reported rather than leaving the previous window's numbers on screen
  // under the new label.
  void loadDoctorAiActivity();
}

/** Bulk "draft all missing notes". The server enforces the batch cap, the rate limit and
 *  idempotency; this only reflects the result honestly, including partial failure. */
async function draftAllMissingNotes() {
  if (!doctorDraftAllBtn) return;
  doctorDraftAllBtn.disabled = true;
  if (doctorDraftAllMessage) {
    doctorDraftAllMessage.classList.remove("hidden");
    // Said up front: up to ten notes, one model call each, one after another.
    doctorDraftAllMessage.textContent = "Drafting concise notes… this can take a few minutes.";
  }
  try {
    // Up to BULK_DRAFT_MAX_ITEMS sequential model calls. Under the default 15s timeout the
    // browser reported failure while the server carried on drafting — the doctor was told
    // it had not worked, and found drafts appearing anyway.
    const result = await doctorAuthedJson("/doctor/reviews/draft-all?style=concise", {
      method: "POST", timeoutMs: DOCTOR_DRAFT_ALL_TIMEOUT_MS,
    });
    const drafted = (result.drafted || []).length;
    const failed = (result.failed || []).length;
    let message = `Drafted ${drafted} note${drafted === 1 ? "" : "s"}.`;
    if (failed) message += ` ${failed} could not be drafted — open them individually.`;
    if (result.remaining) message += ` ${result.remaining} still to do.`;
    if (doctorDraftAllMessage) doctorDraftAllMessage.textContent = message;
    await loadDoctorReviews();
    await loadDoctorAiActivity();
  } catch (error) {
    if (doctorDraftAllMessage) {
      doctorDraftAllMessage.textContent =
        error && error.message ? error.message : "Could not draft these notes right now.";
    }
  } finally {
    doctorDraftAllBtn.disabled = false;
  }
}

function renderDoctorSidebarProfile(doctor) {
  // Both lines are ellipsised to one line in the fixed-width sidebar, so the full value
  // is kept on the title attribute rather than being lost.
  if (doctorSidebarName) {
    doctorSidebarName.textContent = doctor?.name || "Doctor";
    doctorSidebarName.title = doctor?.name || "";
  }
  if (doctorSidebarDepartment) {
    doctorSidebarDepartment.textContent = doctor?.department || "—";
    doctorSidebarDepartment.title = doctor?.department || "";
  }
  if (doctorSidebarInitials) {
    const initials = String(doctor?.name || "")
      .split(/\s+/).filter(Boolean).slice(0, 2)
      .map((part) => part[0].toUpperCase()).join("");
    doctorSidebarInitials.textContent = initials || "DR";
  }
  if (doctorOverviewGreeting) {
    const surname = String(doctor?.name || "").split(/\s+/).filter(Boolean).pop();
    doctorOverviewGreeting.textContent = surname ? `Good day, Dr. ${surname}` : "Your workspace";
  }
  const today = new Date();
  const longDate = new Intl.DateTimeFormat("en-GB", {
    weekday: "long", day: "numeric", month: "long", timeZone: "Asia/Kolkata",
  }).format(today);
  if (doctorOverviewDate) doctorOverviewDate.textContent = longDate;
  if (doctorTodayChipText) doctorTodayChipText.textContent = longDate;
}

function renderDoctorAppointmentsList(listEl, appointments, scope) {
  if (!listEl) return;
  listEl.replaceChildren();

  if (!appointments.length) {
    listEl.appendChild(buildDoctorEmptyState(
      scope === "upcoming" ? "No upcoming appointments." : "No past appointments."
    ));
    return;
  }

  appointments.forEach((appt) => {
    // A real <button>, not a clickable <article>: the whole row is the control, so it
    // must be reachable and operable from the keyboard like any other button.
    const card = document.createElement("button");
    card.type = "button";
    card.className = "doctor-ai-item";
    card.style.width = "100%";
    card.style.cursor = "pointer";
    card.setAttribute(
      "aria-label",
      `Open the ${formatDateTime(appt.start_time)} appointment with ${appt.patient_name || "this patient"}`
    );

    const icon = document.createElement("div");
    icon.className = "doctor-ai-item-ico";
    icon.innerHTML = '<svg class="ai-i" viewBox="0 0 24 24" aria-hidden="true">'
      + '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>';

    const body = document.createElement("div");
    body.className = "doctor-ai-item-body";
    const title = document.createElement("div");
    title.className = "doctor-ai-item-title";
    title.textContent = appt.patient_name || "Unknown patient";
    const meta = document.createElement("div");
    meta.className = "doctor-ai-item-meta";
    meta.textContent = `${appt.department || "Department"} · ${formatDateTime(appt.start_time)}`;
    body.append(title, meta);

    card.append(icon, body);

    const statusValue = adminStatusLabel(appt);
    if (statusValue || appt.status) {
      card.appendChild(buildAiChip(statusValue || appt.status, ""));
    }
    const durationBadge = buildDurationBadge(appt);
    if (durationBadge) card.appendChild(durationBadge);

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

/** Fetches the patient-reported health issues for the open appointment, so the
 *  clinical-actions tab can repeat them where a prescription is written. Non-fatal: if it
 *  fails the notice is simply absent — it must never block the consult screen, and an
 *  empty notice is safer than a stale one from a previous patient. */
async function loadDetailPatientIssues(patientId) {
  doctorDetailPatientIssues = "";
  if (!patientId) return;
  let issues = "";
  try {
    const detail = await doctorAuthedJson(`/doctor/patients/${encodeURIComponent(patientId)}`);
    issues = (detail && detail.health_issues) || "";
  } catch (error) {
    issues = "";
  }
  // These are shown beside the prescription box as the patient's reported allergies and
  // conditions. Another patient's, arriving late after the doctor moved on, would be the
  // worst possible thing to show there.
  if (doctorDetailAppointment?.patient_id !== patientId) return;
  doctorDetailPatientIssues = issues;
  renderClinicalItem();
}

// ── The visit brief (review phase 3) ─────────────────────────────────────────
// What a doctor needs for ONE appointment: why the patient booked, what changed since this
// doctor last saw them, and their last plan. Built by app/services/visit_brief.py from the
// record; nothing in it is generated. Shown at the top of the appointment and, inline, on
// the Today card — one builder for both, so the two can never say different things.
//
// It replaces two things: the "Before this visit" booking-context block (now its first
// section) and the patient-page "AI brief", which summarised the whole patient a second
// time beside "At a glance".

const doctorVisitBriefBlock = document.querySelector("#doctorVisitBriefBlock");
const doctorVisitBriefBody = document.querySelector("#doctorVisitBriefBody");

function formatBriefDate(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? String(iso)
    : date.toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });
}

/** One section: a small heading and its rows. Returns null when there is nothing to put in
 *  it and no empty-state to say, so the caller can leave it out entirely. */
function buildBriefSection(title, rows, emptyText) {
  if (!rows.length && !emptyText) return null;
  const section = document.createElement("section");
  section.className = "doctor-brief-section";
  const heading = document.createElement("h4");
  heading.className = "doctor-brief-heading";
  heading.textContent = title;
  section.appendChild(heading);
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "doctor-brief-empty";
    empty.textContent = emptyText;
    section.appendChild(empty);
    return section;
  }
  const list = document.createElement("ul");
  list.className = "doctor-brief-list";
  rows.forEach((row) => list.appendChild(row));
  section.appendChild(list);
  return section;
}

/** Renders the small markdown subset the booking assistant writes into a booking note —
 *  "## heading", "**bold**", "- item" / "1. item" lists, blank-line paragraphs — as real
 *  elements. The note used to be shown as plain text, so a doctor read "## PRE-APPOINTMENT
 *  CLINICAL SUMMARY **Patient:** ..." with every symbol showing and no line breaks.
 *
 *  Built node by node with textContent, never by handing the string to the browser as HTML:
 *  the note is derived from a chat with the patient, and markdown-to-HTML on text like that
 *  is how a "<img onerror=...>" becomes script on a doctor's screen. Anything outside the subset is
 *  shown exactly as written. Rendering happens at display time, so notes already stored
 *  are fixed along with every future one. */
function renderBookingNoteMarkdown(text) {
  const root = document.createElement("div");
  root.className = "doctor-md";

  const appendInline = (parent, line) => {
    // **bold** spans; everything else literal.
    line.split(/(\*\*[^*]+\*\*)/g).forEach((part) => {
      if (!part) return;
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        const strong = document.createElement("strong");
        strong.textContent = part.slice(2, -2);
        parent.appendChild(strong);
      } else {
        parent.appendChild(document.createTextNode(part));
      }
    });
  };

  let list = null;       // the <ul>/<ol> currently being filled, if any
  let paragraph = null;  // the <p> currently being filled, if any
  const closeBlocks = () => { list = null; paragraph = null; };

  String(text || "").replace(/\r\n?/g, "\n").split("\n").forEach((raw) => {
    const line = raw.trim();
    if (!line) { closeBlocks(); return; }

    const heading = line.match(/^#{1,6}\s+(.*)$/);
    if (heading) {
      closeBlocks();
      const h = document.createElement("p");
      h.className = "doctor-md-heading";
      // Notes written before the prompts said "AI" carry the old heading; the summary is
      // AI-written either way, so it is labelled that way whenever it is shown.
      const title = /^pre-appointment clinical summary$/i.test(heading[1].trim())
        ? "Pre-Appointment AI Clinical Summary" : heading[1];
      appendInline(h, title);
      root.appendChild(h);
      return;
    }

    const bullet = line.match(/^(?:[-*•]|(\d+)[.)])\s+(.*)$/);
    if (bullet) {
      const ordered = Boolean(bullet[1]);
      if (!list || (list.tagName === "OL") !== ordered) {
        list = document.createElement(ordered ? "ol" : "ul");
        root.appendChild(list);
      }
      paragraph = null;
      const item = document.createElement("li");
      appendInline(item, bullet[2]);
      list.appendChild(item);
      return;
    }

    list = null;
    if (!paragraph) {
      paragraph = document.createElement("p");
      root.appendChild(paragraph);
    } else {
      // A line break inside one paragraph is kept, as the author wrote it.
      paragraph.appendChild(document.createElement("br"));
    }
    appendInline(paragraph, line);
  });
  return root;
}

/** A row: its text, optional chips, optional action button. Text via textContent only —
 *  every string here comes from the record, some of it typed by the patient. */
function buildBriefRow(text, { chips = [], action = null, tone = "", content = null } = {}) {
  const item = document.createElement("li");
  item.className = `doctor-brief-row${tone ? ` is-${tone}` : ""}${content ? " is-block" : ""}`;
  if (content) {
    // Pre-built content (a formatted booking note) rather than a single line of text.
    item.appendChild(content);
  } else {
    const span = document.createElement("span");
    span.className = "doctor-brief-text";
    span.textContent = text;
    item.appendChild(span);
  }
  chips.forEach((chip) => item.appendChild(buildAiChip(chip.text, chip.modifier || "")));
  if (action) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "doctor-ai-btn is-ghost is-sm";
    button.textContent = action.label;
    if (action.ariaLabel) button.setAttribute("aria-label", action.ariaLabel);
    button.addEventListener("click", action.onClick);
    item.appendChild(button);
  }
  return item;
}

function buildVisitBrief(brief) {
  const root = document.createElement("div");
  root.className = "doctor-visit-brief-content";

  // 1. Why they're here — the booking itself. Everything here came from the patient.
  const why = brief.why || {};
  const whyRows = [];
  if (why.booking_note) {
    whyRows.push(buildBriefRow("", {
      content: renderBookingNoteMarkdown(why.booking_note),
      chips: [{ text: why.label || "Patient reports", modifier: "is-warn" }],
    }));
  }
  if (why.recorded) {
    if (why.chosen_department) whyRows.push(buildBriefRow(`Booked into ${why.chosen_department}`));
    // The disagreement is the single most clinically useful thing here, so it is said, not
    // left for the doctor to notice by comparing two lines.
    if (why.suggested_department && why.chosen_department
        && why.suggested_department !== why.chosen_department) {
      whyRows.push(buildBriefRow(
        `The assistant suggested ${why.suggested_department}; the patient chose ${why.chosen_department}.`
        + (why.department_match_reason ? ` (${why.department_match_reason})` : ""),
        { tone: "warn" },
      ));
    }
    const messages = Number(why.messages || 0);
    const brought = Number(why.documents_brought || 0);
    whyRows.push(buildBriefRow(
      (messages ? `${messages} message${messages === 1 ? "" : "s"} while booking` : "Booked without a conversation")
      + ` · ${brought ? `${brought} document${brought === 1 ? "" : "s"} brought` : "no documents brought"}`,
    ));
  }
  root.appendChild(buildBriefSection("Why they're here", whyRows,
    // Said plainly: an appointment booked before this was captured has no context, which
    // is not the same as a patient who said nothing.
    why.recorded ? "" : "No booking conversation was recorded for this appointment."));

  // 2. Since you last saw them — or, on a first visit, the recent record, saying which.
  const since = brief.since || {};
  const sinceRows = [];
  (since.documents || []).forEach((doc) => {
    const parts = [doc.original_filename || "Document"];
    if (doc.document_type && doc.document_type !== "other") parts.push(formatDocumentType(doc.document_type));
    if (doc.clinical_date) parts.push(`dated ${formatBriefDate(doc.clinical_date)}`);
    if (doc.copies > 1) parts.push(`uploaded ${doc.copies} times`);
    const chips = [];
    if (doc.summary_verification === "failed") chips.push({ text: "No verified summary", modifier: "is-warn" });
    const briefRow = buildBriefRow(`New document: ${parts.join(" · ")}`, {
      chips,
      action: {
        label: "View",
        ariaLabel: `View ${doc.original_filename || "document"}`,
        onClick: () => { void openDoctorDocumentViewer(brief.patient_id, doc); },
      },
    });
    // Verified / reported by the patient's doctors — before the View button.
    briefRow.insertBefore(buildDocumentReviewChip(doc.document_id, doc.review), briefRow.querySelector("button"));
    sinceRows.push(briefRow);
  });
  (since.abnormal || []).forEach((result) => {
    const value = result.value != null ? ` ${result.value}${result.unit ? ` ${result.unit}` : ""}` : "";
    sinceRows.push(buildBriefRow(
      `${result.name} ${result.flag}:${value}${result.clinical_date ? ` (${formatBriefDate(result.clinical_date)})` : ""}`,
      {
        tone: "warn",
        // Read from a document a doctor has reported inaccurate: not to be taken at face value.
        chips: result.source_reported_inaccurate
          ? [{ text: "Source reported inaccurate", modifier: "is-bad" }] : [],
      },
    ));
  });
  (since.colleague_notes || []).forEach((note) => {
    const who = `${note.doctor_name || "A colleague"} (${note.department || "—"}), ${formatBriefDate(note.signed_at)}`;
    // A restricted specialty's encounter is disclosed — hiding it would mislead — and its
    // content withheld, exactly as the timeline does.
    sinceRows.push(note.restricted
      ? buildBriefRow(`${who} — note restricted`, { chips: [{ text: "Restricted", modifier: "" }] })
      : buildBriefRow(`${who}: ${note.summary || "signed a note"}`));
  });
  (since.colleague_prescriptions || []).forEach((item) => {
    const who = `${item.doctor_name || "A colleague"} (${item.department || "—"})`;
    sinceRows.push(item.restricted
      ? buildBriefRow(`${who} approved a prescription — restricted`)
      : buildBriefRow(`${who} prescribed: ${item.content}`));
  });
  const sinceTitle = since.first_visit
    ? `First visit with you — their record from the last ${Math.round((since.lookback_days || 365) / 30)} months`
    : `Since you last saw them (${formatBriefDate(since.boundary)})`;
  root.appendChild(buildBriefSection(sinceTitle, sinceRows,
    since.first_visit ? "Nothing on their record in that time." : "Nothing new since you last saw them."));

  // 3. Your last plan — only when there is one; a first visit has none to show.
  const plan = brief.last_plan;
  if (plan) {
    const planRows = [];
    if (plan.plan) planRows.push(buildBriefRow(plan.plan));
    (plan.approved_items || []).forEach((item) => {
      planRows.push(buildBriefRow(`Approved ${item.kind.replace(/_/g, " ")}: ${item.content}`));
    });
    root.appendChild(buildBriefSection(`Your last plan (${formatBriefDate(plan.signed_at)})`, planRows,
      "Your last note had no plan recorded."));
  }

  // 4. The AI nutritionist — when the patient has documents. Loaded on request, so the
  // brief itself stays a fast read with no model behind it.
  if (brief.has_documents && brief.booking_id) {
    root.appendChild(buildNutritionSection(
      `/doctor/appointments/${encodeURIComponent(brief.booking_id)}/nutrition`,
      "From their latest abnormal results and the symptoms in the booking note.",
    ));
  }
  return root;
}

// ---- the AI nutritionist ----
//
// app/services/nutrition.py: guidance is written once per finding or symptom and reused
// for every patient, checked by code (no meat, fish or egg in the vegetarian list; food
// only; no numbers). What is patient-specific — which terms apply, the evidence, and the
// foods removed because of another result — is decided in code.

// Which diet the doctor last looked at; the same for every nutrition panel on the page.
let nutritionDiet = "veg";

/** A collapsed "AI nutritionist" section that loads its guidance the first time it opens. */
function buildNutritionSection(url, intro) {
  const section = document.createElement("section");
  section.className = "doctor-brief-section doctor-nutrition";

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "doctor-ai-btn is-ghost is-sm doctor-nutrition-toggle";
  toggle.textContent = "AI nutritionist";
  toggle.setAttribute("aria-expanded", "false");
  const body = document.createElement("div");
  body.className = "doctor-nutrition-body hidden";
  const bodyId = `doctorNutrition-${Math.random().toString(36).slice(2, 10)}`;
  body.id = bodyId;
  toggle.setAttribute("aria-controls", bodyId);
  section.append(toggle, body);

  let loaded = false;
  toggle.addEventListener("click", async () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    body.classList.toggle("hidden", !open);
    if (!open || loaded) return;
    loaded = true;
    body.replaceChildren(Object.assign(document.createElement("p"), {
      className: "doctor-brief-empty",
      textContent: "Preparing food guidance… the first time a result is seen this can take a little while.",
    }));
    try {
      // Generous: guidance for a result nobody has had before is written on this request.
      const payload = await doctorAuthedJson(url, { timeoutMs: 120000 });
      renderNutritionGuidance(body, payload, intro);
    } catch (error) {
      loaded = false;
      body.replaceChildren(Object.assign(document.createElement("p"), {
        className: "doctor-brief-empty",
        textContent: error && error.message ? error.message : "Food guidance could not be loaded.",
      }));
    }
  });
  return section;
}

function describeNutritionEvidence(because) {
  if (because.symptom) return `${because.symptom} — mentioned in the booking note`;
  const where = [
    formatDocumentType(because.document_type),
    because.clinical_date ? formatBriefDate(because.clinical_date) : "",
    because.page_no ? `p${because.page_no}` : "",
  ].filter(Boolean).join(", ");
  return `${because.printed_name} ${because.value_text}, ${because.flag}${where ? ` — ${where}` : ""}`;
}

function renderNutritionGuidance(host, payload, intro = "") {
  host.replaceChildren();
  const items = (payload && payload.items) || [];

  const label = document.createElement("p");
  label.className = "doctor-nutrition-label";
  label.textContent = "AI generated · food suggestions to discuss, not a diet prescription";
  host.appendChild(label);
  if (intro) {
    const lead = document.createElement("p");
    lead.className = "doctor-brief-empty";
    lead.textContent = intro;
    host.appendChild(lead);
  }

  const notices = [...((payload && payload.cautions) || [])];
  if (payload && payload.reported_inaccurate) {
    notices.push("This document was reported inaccurate by a clinician, so no guidance is based on it.");
  }
  if (payload && payload.excluded_documents) {
    notices.push(`Results from ${payload.excluded_documents} document${payload.excluded_documents === 1 ? "" : "s"} reported inaccurate are left out.`);
  }
  notices.forEach((text) => {
    const caution = document.createElement("p");
    caution.className = "doctor-nutrition-caution";
    caution.textContent = text;
    host.appendChild(caution);
  });

  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "doctor-brief-empty";
    empty.textContent = payload && payload.reported_inaccurate
      ? "No food guidance for this document."
      : "Nothing on the record calls for specific dietary changes.";
    host.appendChild(empty);
  } else {
    // Vegetarian / non-vegetarian: one choice, applied to every item.
    const diets = document.createElement("div");
    diets.className = "doctor-nutrition-diets";
    diets.setAttribute("role", "group");
    diets.setAttribute("aria-label", "Diet");
    [["veg", "Vegetarian"], ["non_veg", "Non-vegetarian"]].forEach(([value, text]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "doctor-nutrition-diet";
      button.textContent = text;
      button.setAttribute("aria-pressed", String(nutritionDiet === value));
      button.addEventListener("click", () => {
        nutritionDiet = value;
        renderNutritionGuidance(host, payload, intro);
        host.querySelector(".doctor-nutrition-diet[aria-pressed='true']")?.focus();
      });
      diets.appendChild(button);
    });
    host.appendChild(diets);

    const list = document.createElement("div");
    list.className = "doctor-nutrition-list";
    items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "doctor-nutrition-item";
      const title = document.createElement("h5");
      title.className = "doctor-nutrition-term";
      const direction = item.kind === "symptom" ? "symptom"
        : item.direction === "abnormal" ? "outside range" : item.direction;
      title.textContent = `${item.term.charAt(0).toUpperCase()}${item.term.slice(1)} · ${direction}`;
      card.appendChild(title);

      (item.because || []).forEach((because) => {
        const line = document.createElement("p");
        line.className = "doctor-nutrition-because";
        line.textContent = `Because: ${describeNutritionEvidence(because)}`;
        card.appendChild(line);
      });

      const focus = document.createElement("p");
      focus.className = "doctor-nutrition-focus";
      focus.textContent = item.nutrient_focus || "";
      card.appendChild(focus);

      const foods = nutritionDiet === "veg" ? item.veg_foods : item.non_veg_foods;
      const eat = document.createElement("p");
      eat.className = "doctor-nutrition-foods";
      const eatLabel = document.createElement("strong");
      eatLabel.textContent = nutritionDiet === "veg" ? "Vegetarian: " : "Non-vegetarian: ";
      eat.append(eatLabel, document.createTextNode((foods || []).length ? foods.join(", ") : "—"));
      card.appendChild(eat);

      if ((item.limit || []).length) {
        const limit = document.createElement("p");
        limit.className = "doctor-nutrition-foods";
        const limitLabel = document.createElement("strong");
        limitLabel.textContent = "Limit: ";
        limit.append(limitLabel, document.createTextNode(item.limit.join(", ")));
        card.appendChild(limit);
      }
      if (item.note) {
        const note = document.createElement("p");
        note.className = "doctor-nutrition-note";
        note.textContent = item.note;
        card.appendChild(note);
      }
      list.appendChild(card);
    });
    host.appendChild(list);
  }

  if (payload && (payload.unavailable || []).length) {
    const missing = document.createElement("p");
    missing.className = "doctor-brief-empty";
    missing.textContent = `No guidance could be prepared for: ${payload.unavailable.join(", ")}.`;
    host.appendChild(missing);
  }
}

function renderDoctorVisitBrief(host, brief, { loading = false, error = "" } = {}) {
  if (!host) return;
  host.replaceChildren();
  if (loading) {
    host.appendChild(buildDoctorEmptyState("Loading the visit brief…"));
    return;
  }
  if (error) {
    // Not "nothing to show" — a failed request is not a statement about the patient.
    host.appendChild(buildDoctorEmptyState(`The visit brief could not be loaded. ${error}`));
    return;
  }
  host.appendChild(buildVisitBrief(brief));
}

/** The brief at the top of the appointment. */
async function loadDoctorVisitBrief(bookingId) {
  if (!doctorVisitBriefBlock) return;
  if (!bookingId) {
    doctorVisitBriefBlock.classList.add("hidden");
    return;
  }
  doctorVisitBriefBlock.classList.remove("hidden");
  renderDoctorVisitBrief(doctorVisitBriefBody, null, { loading: true });
  try {
    const brief = await doctorAuthedJson(`/doctor/appointments/${encodeURIComponent(bookingId)}/brief`);
    // A late answer for an appointment the doctor has already left must not paint under the
    // one they are on — the same guard every per-patient loader now has.
    if (doctorDetailAppointment?.booking_id !== bookingId) return;
    doctorTodayBriefCache.set(bookingId, brief);
    renderDoctorVisitBrief(doctorVisitBriefBody, brief);
  } catch (error) {
    if (doctorDetailAppointment?.booking_id !== bookingId) return;
    renderDoctorVisitBrief(doctorVisitBriefBody, null, { error: error.message || "" });
  }
}

// Briefs fetched this session, by booking. The Today card is redrawn on every refresh; an
// open brief is redrawn from here rather than refetched, because every fetch is an audited
// read and the doctor did not ask to read it again every 30 seconds.
const doctorTodayBriefCache = new Map();
// The Today card whose brief is open, or null.
let doctorTodayBriefOpen = null;
// A failed load, by booking — shown as a failure, never as an empty brief.
const doctorTodayBriefErrors = new Map();

/** Opens or closes a Today card's brief. Opening always fetches afresh — the doctor asked
 *  for it now — while showing any cached copy meanwhile, so there is no loading flash over
 *  a brief they already had. */
function toggleDoctorTodayBrief(bookingId) {
  doctorTodayBriefOpen = doctorTodayBriefOpen === bookingId ? null : bookingId;
  renderDoctorTodaySchedule();
  // The list was redrawn, so hand focus back to the button that was pressed.
  doctorTodaySchedule?.querySelector(`[aria-controls="doctorTodayBrief-${bookingId}"]`)?.focus();
  if (doctorTodayBriefOpen === bookingId) void loadDoctorTodayBrief(bookingId);
}

async function loadDoctorTodayBrief(bookingId) {
  try {
    const brief = await doctorAuthedJson(`/doctor/appointments/${encodeURIComponent(bookingId)}/brief`);
    doctorTodayBriefCache.set(bookingId, brief);
    doctorTodayBriefErrors.delete(bookingId);
  } catch (error) {
    doctorTodayBriefErrors.set(bookingId, error.message || "");
  }
  // Painted in place rather than by redrawing the whole list, so the answer arriving does
  // not move the doctor's focus. If the brief was closed meanwhile, there is nothing to do.
  if (doctorTodayBriefOpen !== bookingId) return;
  const host = document.querySelector(`#doctorTodayBrief-${bookingId} .doctor-today-brief-body`);
  if (!host) return;
  const brief = doctorTodayBriefCache.get(bookingId);
  const failed = doctorTodayBriefErrors.get(bookingId);
  if (failed !== undefined && !brief) renderDoctorVisitBrief(host, null, { error: failed });
  else if (brief) renderDoctorVisitBrief(host, brief);
}

function showDoctorAppointmentDetail(appt, scope) {
  doctorDetailReturnView = scope;
  doctorDetailAppointment = appt;
  // A different appointment is a different note. Without this, an abandoned edit's flag
  // would survive into an appointment with no note at all and prompt on leaving it.
  doctorNoteDirty = false;
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
  // Patient-reported issues for the allergy notice on the clinical-actions tab. Read from
  // the existing, treating-relationship-scoped patient endpoint rather than widening the
  // appointments payload, which is used on screens that have no business carrying it.
  loadDetailPatientIssues(appt.patient_id);
  // What happened before the visit. Fired without awaiting — the consult below is the
  // doctor's actual work and must paint regardless.
  void loadDoctorVisitBrief(appt.booking_id);

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

  showDoctorPane("appointmentDetail");

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
  if (!doctorConsultMessage) return;
  doctorConsultMessage.textContent = text || "";
  doctorConsultMessage.classList.remove("is-notice");
}

/** The same line, for news rather than an error — it is styled as an error otherwise. */
function setDoctorConsultNotice(text) {
  setDoctorConsultMessage(text);
  doctorConsultMessage?.classList.add("is-notice");
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
    // Only a consult that still stands is identified. A discarded one kept its ID — and,
    // below, its recording duration — on screen after the doctor discarded it, which read
    // as if it were still this appointment's consult. The discard is in the audit log.
    doctorConsultIdLabel.textContent = status ? `Consult ID: ${doctorActiveConsult.id}` : "";
    doctorConsultIdLabel.classList.toggle("hidden", !status);
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
  // Clinical actions live alongside the note and share its precondition: they belong to a
  // consultation that actually happened.
  doctorClinicalItemsBlock?.classList.toggle("hidden", status !== "transcript_ready");
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
    if (status && doctorActiveConsult?.started_at && doctorActiveConsult?.ended_at) {
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
    loadClinicalItem();
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

  const isFlagged = !!(note.confidence_flags && note.confidence_flags[fieldKey]);
  const citationsForField = (note.field_citations && note.field_citations[fieldKey]) || [];

  if (isFlagged) {
    const flag = document.createElement("span");
    flag.className = "clinical-note-flag";
    flag.textContent = "Needs review";
    head.appendChild(flag);
  }

  // Per-section verification. Draft only: once signed, the signature is the record of
  // review, and the API rejects a mark on a signed note anyway.
  if (!readOnly) {
    const isVerified = doctorNoteVerifiedSections.includes(fieldKey);
    const verifyBtn = document.createElement("button");
    verifyBtn.type = "button";
    verifyBtn.className = `doctor-ai-btn is-sm ${isVerified ? "is-soft" : "is-ghost"}`;
    verifyBtn.textContent = isVerified ? "Verified" : "Mark verified";
    verifyBtn.setAttribute("aria-pressed", isVerified ? "true" : "false");
    verifyBtn.setAttribute(
      "aria-label",
      `${isVerified ? "Unmark" : "Mark"} the ${SOAP_FIELD_LABELS[fieldKey]} section as verified`
    );
    verifyBtn.style.marginLeft = "auto";
    verifyBtn.addEventListener("click", () => toggleSectionVerified(fieldKey, !isVerified));
    head.appendChild(verifyBtn);
  }

  wrap.appendChild(head);
  if (!readOnly) {
    wrap.classList.toggle("doctor-ai-section", true);
    wrap.classList.toggle("is-verified", doctorNoteVerifiedSections.includes(fieldKey));
    wrap.classList.toggle("is-flagged", isFlagged && !doctorNoteVerifiedSections.includes(fieldKey));
  }

  // Why the section was flagged, in plain words. Derived from what is actually recorded —
  // a flag with no citation means the model found nothing in the transcript to support
  // the text, which is a different problem from a flag that does have a quote behind it.
  if (isFlagged) {
    const why = document.createElement("p");
    why.className = "panel-note";
    why.textContent = citationsForField.length
      ? "Flagged: the model was not confident this matches the transcript. Check the citation below."
      : "Flagged: no supporting transcript quote was found for this section.";
    wrap.appendChild(why);
  }

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
    // The section name is in the head above, but nothing associated it with the control,
    // so a screen reader announced these four as an unnamed "edit text". It only showed
    // up once a field had content: the placeholder below doubles as an accessible name,
    // so an EMPTY note passed and a real one — the normal case — did not.
    value.setAttribute("aria-label", `${SOAP_FIELD_LABELS[fieldKey]} section of the clinical note`);
    value.addEventListener("input", () => { doctorNoteDirty = true; });
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

/** "n of 4 sections verified" (plan §4.6). Counts only the four real sections, once
 *  each, so a stray value can never push the bar past 100%. Mirrors the server-side
 *  doctor_workspace.verification_progress, which is the unit-tested definition. */
function renderNoteVerifyProgress() {
  const verified = SOAP_FIELDS.filter((f) => doctorNoteVerifiedSections.includes(f)).length;
  const total = SOAP_FIELDS.length;
  if (doctorNoteVerifyLabel) {
    doctorNoteVerifyLabel.textContent = `${verified} of ${total} sections verified`;
  }
  if (doctorNoteVerifyFill) {
    doctorNoteVerifyFill.style.width = `${Math.round((verified * 100) / total)}%`;
  }
  if (doctorNoteVerifyBar) doctorNoteVerifyBar.setAttribute("aria-valuenow", String(verified));
}

/** The provenance of this draft: when it was written, and from what kind of transcript.
 *  Any value the backend could not evidence renders as "Not recorded" — never a guess.
 *
 *  The model name and prompt version are deliberately NOT here. They are still recorded
 *  against the note for audit, but naming the model on screen invites the doctor to weigh
 *  the draft by which model produced it, which is not a clinical judgement they can make
 *  and not one this panel should invite. What matters to them is when it was written and
 *  whether the transcript behind it was sound. */
function renderNoteAssistantPanel(note) {
  if (doctorNoteProvenanceList) {
    doctorNoteProvenanceList.replaceChildren();
    const rows = [
      ["Generated", note.generated_at ? formatDateTime(note.generated_at) : "Not recorded"],
      ["Transcript", note.source_transcript_type === "live_fallback"
        ? "Lower-quality (live fallback)"
        : note.source_transcript_type === "batch" ? "Standard (batch)" : "Not recorded"],
    ];
    rows.forEach(([term, value]) => {
      const dt = document.createElement("dt");
      dt.className = "ai-muted";
      dt.textContent = term;
      const dd = document.createElement("dd");
      dd.style.margin = "0";
      dd.textContent = value;
      doctorNoteProvenanceList.append(dt, dd);
    });
  }

  if (!doctorNoteSuggestedChecks) return;
  doctorNoteSuggestedChecks.replaceChildren();
  // Taken from the flags already on the note — this list invents nothing.
  const checks = [];
  if (note.status === "stale") {
    checks.push("This note is blocked. Regenerate it before it can be signed.");
  }
  if (note.source_transcript_type === "live_fallback") {
    checks.push("Drafted from a lower-quality transcript — check it against the recording.");
  }
  SOAP_FIELDS.forEach((field) => {
    if (note.confidence_flags && note.confidence_flags[field]) {
      checks.push(`Check the ${SOAP_FIELD_LABELS[field]} section — the model was not confident.`);
    }
  });
  if (!checks.length) {
    doctorNoteSuggestedChecks.appendChild(
      buildDoctorEmptyState("No flags on this draft. Read it through before signing.")
    );
    return;
  }
  checks.forEach((text) => {
    const row = document.createElement("div");
    row.className = "doctor-ai-item-meta";
    row.textContent = `• ${text}`;
    doctorNoteSuggestedChecks.appendChild(row);
  });
}

/** Marks one section verified, or clears it. The server is the source of truth for the
 *  resulting set, so the UI re-renders from its response rather than assuming success. */
async function toggleSectionVerified(field, verified) {
  if (!doctorActiveConsult?.id) return;
  try {
    const result = await doctorAuthedJson(
      `/doctor/consult/${doctorActiveConsult.id}/soap/sections/${field}/verify`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verified }),
      }
    );
    doctorNoteVerifiedSections = result.verified_sections || [];
    if (doctorCurrentNote) renderNoteDraft(doctorCurrentNote);
    renderNoteVerifyProgress();
  } catch (error) {
    if (doctorNoteMessage) {
      doctorNoteMessage.textContent =
        error && error.message ? error.message : "Could not update this section.";
      doctorNoteMessage.classList.remove("hidden");
    }
  }
}

async function loadNoteVerifiedSections() {
  if (!doctorActiveConsult?.id) return;
  try {
    const result = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/soap/sections`);
    doctorNoteVerifiedSections = result.verified_sections || [];
  } catch (error) {
    // Non-fatal: the note is still reviewable and signable without its progress marks.
    doctorNoteVerifiedSections = [];
  }
  if (doctorCurrentNote && doctorCurrentNote.status !== "signed") renderNoteDraft(doctorCurrentNote);
  renderNoteVerifyProgress();
}

function renderNoteDraft(note) {
  if (!doctorNoteFieldsContainer) return;
  // Unsaved text survives a re-render. This function is called for reasons that have
  // nothing to do with the text — marking a section verified, the verified marks arriving
  // after the note — and it used to rebuild every field from the last SAVED note, silently
  // reverting whatever the doctor had typed since. Only the four text fields are carried
  // over; flags and citations still come from the note.
  const shown = doctorNoteDirty ? { ...note, ...collectNoteFieldValues() } : note;
  doctorNoteFieldsContainer.replaceChildren();
  SOAP_FIELDS.forEach((field) => {
    doctorNoteFieldsContainer.appendChild(buildNoteFieldRow(field, shown, { readOnly: false }));
  });
  // A blocked ('stale') note cannot be signed. Disabling the button is a convenience, NOT
  // the control: soap_notes.sign_soap_note rejects it at the API too, so bypassing this
  // in the browser achieves nothing.
  if (doctorNoteSignBtn) doctorNoteSignBtn.disabled = note.status === "stale";
  renderNoteVerifyProgress();
  renderNoteAssistantPanel(note);
}

/** The note's life story: AI drafted -> you reviewed and signed -> shared with patient
 *  (plan §4.11). Built only from timestamps recorded on the note itself; a step that has
 *  not happened is simply absent rather than shown as pending, because this is a record
 *  of what occurred, not a checklist of what might. */
function renderNoteAuditTrail(note) {
  if (!doctorNoteAuditTrail) return;
  doctorNoteAuditTrail.replaceChildren();

  const steps = [];
  if (note.generated_at) {
    // No model/prompt detail line — see renderNoteAssistantPanel. The timestamp and the
    // "AI drafted this note" label are the parts of this step that matter clinically.
    steps.push([note.generated_at, "AI drafted this note", ""]);
  }
  if (note.edited_at) {
    steps.push([note.edited_at, "You edited the draft", ""]);
  }
  if (note.signed_at) {
    steps.push([note.signed_at, "You reviewed and signed it", "It became part of the clinical record"]);
  }
  if (note.shared_with_patient_at) {
    steps.push([note.shared_with_patient_at, "Shared with the patient", "This cannot be withdrawn"]);
  }

  if (!steps.length) {
    doctorNoteAuditTrail.appendChild(buildDoctorEmptyState("Nothing recorded yet."));
    return;
  }

  steps.forEach(([when, label, detail]) => {
    const row = document.createElement("div");
    row.className = "doctor-ai-feed-row";
    const time = document.createElement("div");
    time.className = "doctor-ai-feed-time";
    time.textContent = formatDateTime(when);
    const body = document.createElement("div");
    body.className = "doctor-ai-grow";
    const title = document.createElement("div");
    title.className = "doctor-ai-item-title";
    title.style.fontSize = "13.5px";
    title.textContent = label;
    body.appendChild(title);
    if (detail) {
      const meta = document.createElement("div");
      meta.className = "doctor-ai-item-meta";
      meta.textContent = detail;
      body.appendChild(meta);
    }
    row.append(time, body);
    doctorNoteAuditTrail.appendChild(row);
  });
}

function renderNoteSigned(note) {
  renderNoteAuditTrail(note);
  if (doctorNoteSignedFieldsContainer) {
    doctorNoteSignedFieldsContainer.replaceChildren();
    SOAP_FIELDS.forEach((field) => {
      doctorNoteSignedFieldsContainer.appendChild(buildNoteFieldRow(field, note, { readOnly: true }));
    });
  }

  // Sharing is one-way: once shared, the button is replaced by a permanent statement of
  // when it happened, because there is no way to withdraw it.
  const alreadyShared = !!note.shared_with_patient_at;
  doctorNoteShareRow?.classList.toggle("hidden", alreadyShared);
  doctorNoteShareConfirm?.classList.add("hidden");
  if (doctorNoteSharedNotice) {
    doctorNoteSharedNotice.textContent = alreadyShared
      ? `Shared with the patient on ${new Date(note.shared_with_patient_at).toLocaleString()}.`
      : "";
    doctorNoteSharedNotice.classList.toggle("hidden", !alreadyShared);
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
  // Signing is what makes "Insert from plan" available on the prescription.
  updateInsertFromPlanVisibility();

  doctorNoteGenerateRow?.classList.toggle("hidden", isSigned);
  doctorNoteGenerateConfirm?.classList.add("hidden");
  if (doctorNoteGenerateBtn) {
    updateNoteGenerateLabel();
  }

  // The explanatory empty state and the detail-level choice are only meaningful before a
  // note exists; once one does, the button reads "Regenerate" and the toggle would imply
  // the existing note can be restyled in place, which it cannot — it would be replaced.
  doctorNoteEmptyState?.classList.toggle("hidden", !!note);
  doctorNoteStyleToggle?.classList.toggle("hidden", isSigned);

  if (!note) {
    doctorNoteStatusBadge?.classList.add("hidden");
    doctorNoteDraftBlock?.classList.add("hidden");
    doctorNoteSignedBlock?.classList.add("hidden");
    doctorNoteFallbackNotice?.classList.add("hidden");
    renderNoteProvenance(null);
    return;
  }

  if (doctorNoteStatusBadge) {
    doctorNoteStatusBadge.textContent = NOTE_STATUS_LABELS[note.status] || note.status;
    const modifier = note.status === "signed" ? "is-completed" : note.status === "stale" ? "is-upcoming" : "";
    doctorNoteStatusBadge.className = `admin-status-pill ${modifier}`.trim();
    doctorNoteStatusBadge.classList.remove("hidden");
  }

  renderNoteFallbackNotice(note.source_transcript_type);
  renderNoteProvenance(note);

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
  // Reset before refetching: these marks belong to ONE note, and leaving the previous
  // note's progress on screen while the new one loads would be actively misleading.
  doctorNoteVerifiedSections = [];
  // A freshly loaded note is, by definition, what is saved.
  doctorNoteDirty = false;
  renderSoapNote();
  if (doctorCurrentNote && doctorCurrentNote.status !== "signed") loadNoteVerifiedSections();
}

/** "Regenerate Clinical Note (Detailed)": the button says which length it will draft, so
 *  choosing Concise or Detailed visibly changes something — the choice applies to the
 *  NEXT draft, and nothing on screen used to say so. */
function updateNoteGenerateLabel() {
  if (!doctorNoteGenerateBtn) return;
  const length = doctorNoteStyle === "detailed" ? "Detailed" : "Concise";
  doctorNoteGenerateBtn.textContent = doctorNoteGenerating
    ? "Drafting…"
    : `${doctorCurrentNote ? "Regenerate" : "Generate"} Clinical Note (${length})`;
}

function setNoteGenerating(on) {
  doctorNoteGenerating = on;
  [doctorNoteGenerateBtn, doctorNoteGenerateConfirmBtn, ...doctorNoteStyleButtons].forEach((button) => {
    if (button) button.disabled = on;
  });
  doctorNoteGenerateBtn?.setAttribute("aria-busy", String(on));
  const status = document.querySelector("#doctorNoteGeneratingStatus");
  if (status) {
    status.textContent = on
      ? `Drafting a ${doctorNoteStyle} note from the transcript — this can take up to a minute.`
      : "";
    status.classList.toggle("hidden", !on);
  }
  updateNoteGenerateLabel();
}

async function generateSoapNote() {
  if (!doctorActiveConsult || doctorNoteGenerating) return;
  const consultId = doctorActiveConsult.id;
  const hadNote = Boolean(doctorCurrentNote);
  setDoctorNoteMessage("");
  setNoteGenerating(true);
  try {
    const note = await doctorAuthedJson(`/doctor/consult/${consultId}/soap/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ style: doctorNoteStyle }),
      // A model call over a whole consultation can outlast the default 15s. Timing out on
      // the client does not stop the server, so the note would be drafted anyway while the
      // doctor was told it had failed.
      timeoutMs: DOCTOR_GENERATE_TIMEOUT_MS,
    });
    // The doctor moved to another consult while this was drafting: this note is not
    // theirs to show there.
    if (!doctorActiveConsult || doctorActiveConsult.id !== consultId) return;
    doctorCurrentNote = note;
    // Regenerating replaces the draft wholesale; the doctor confirmed that before this ran.
    doctorNoteDirty = false;
    renderSoapNote();
    // A new draft is a new pending item and a new activity event.
    void refreshAfterClinicalAction();
  } catch (error) {
    if (!doctorActiveConsult || doctorActiveConsult.id !== consultId) return;
    // A failed REGENERATE leaves the previous note on screen; say so, or the error reads as
    // if that note were broken.
    setDoctorNoteMessage(hadNote
      ? `The note was not regenerated — the note below is still the previous version. ${error.message}`
      : error.message);
  } finally {
    setNoteGenerating(false);
  }
}

function collectNoteFieldValues() {
  const values = {};
  doctorNoteFieldsContainer?.querySelectorAll("textarea[data-field]").forEach((el) => {
    values[el.dataset.field] = el.value;
  });
  return values;
}

/** Saves the draft's text. Returns true only if the server accepted it, so a caller that
 *  must not proceed on unsaved text — signing — can tell. */
async function saveSoapNote() {
  if (!doctorActiveConsult) return false;
  setDoctorNoteMessage("");
  try {
    doctorCurrentNote = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/soap`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectNoteFieldValues()),
    });
    doctorNoteDirty = false;
    renderSoapNote();
    return true;
  } catch (error) {
    setDoctorNoteMessage(error.message);
    return false;
  }
}

/** "Generated <date/time>" under the note header.
 *
 *  Gated on generated_at, NOT on ai_model: this line used to be shown only when the note
 *  carried a model name, so removing the model name from the text without moving the gate
 *  would have deleted the line entirely, timestamp and all. */
function renderNoteProvenance(note) {
  const host = document.querySelector("#doctorNoteProvenance");
  if (!host) return;
  if (!note || !note.generated_at) {
    host.textContent = "";
    host.classList.add("hidden");
    return;
  }
  host.textContent = `Generated ${formatDateTime(note.generated_at)}`;
  host.classList.remove("hidden");
}

function setDoctorNoteStyle(style) {
  const next = style === "detailed" ? "detailed" : "concise";
  doctorNoteStyle = next;
  doctorNoteStyleButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.noteStyle === next);
    button.setAttribute("aria-pressed", String(button.dataset.noteStyle === next));
  });
  updateNoteGenerateLabel();
}

async function confirmSignSoapNote() {
  if (!doctorActiveConsult) return;
  setDoctorNoteMessage("");
  // Sign what is on screen. The server signs the last SAVED text, so signing with unsaved
  // edits used to put a different note into the record than the one the doctor had just
  // read and approved — with nothing to tell them. Saving first closes that; if the save
  // fails, nothing is signed, because signing the older text is exactly the failure.
  if (doctorNoteDirty) {
    const saved = await saveSoapNote();
    if (!saved) {
      // saveSoapNote has already put the server's reason in the message line; keep it.
      const reason = (doctorNoteMessage?.textContent || "").trim();
      setDoctorNoteMessage(
        `Your changes could not be saved${reason ? ` (${reason})` : ""}, so the note was not signed.`
        + " Nothing has changed in the record."
      );
      return;
    }
  }
  try {
    doctorCurrentNote = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/soap/sign`, { method: "POST" });
    renderSoapNote();
    // Signing removes an item from the pending queue, so the queue, its counts and the
    // activity feed are refetched rather than left showing work already done.
    void refreshAfterClinicalAction();
  } catch (error) {
    setDoctorNoteMessage(error.message);
  }
}

async function confirmShareSoapNote() {
  if (!doctorActiveConsult) return;
  setDoctorNoteMessage("");
  try {
    doctorCurrentNote = await doctorAuthedJson(`/doctor/consult/${doctorActiveConsult.id}/soap/share`, { method: "POST" });
    renderSoapNote();
    showAppToast("Shared with the patient.");
    void refreshAfterClinicalAction();
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
    void refreshAfterClinicalAction();
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
    setDoctorConsultNotice("Consult discarded. You can start a new one.");
  } catch (error) {
    setDoctorConsultMessage(error.message);
  }
}

/** `background` marks an automatic refresh — see loadDoctorAiActivity. */
async function loadDoctorPatientsList({ background = false } = {}) {
  if (!background && doctorPatientsCount) doctorPatientsCount.textContent = "Loading...";
  try {
    const data = await doctorAuthedJson("/doctor/patients");
    doctorPatientsCache = Array.isArray(data.patients) ? data.patients : [];
    renderDoctorPatientsList();
    if (doctorPatientsCount) {
      doctorPatientsCount.textContent = `${doctorPatientsCache.length} patient${doctorPatientsCache.length === 1 ? "" : "s"}`;
    }
  } catch (error) {
    if (!background && doctorPatientsCount) doctorPatientsCount.textContent = "Unable to load.";
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
    doctorPatientsList.appendChild(buildDoctorEmptyState(
      doctorPatientsCache.length ? "No patients match your search." : "No patients yet."
    ));
    return;
  }

  filtered.forEach((patient) => {
    // A real <button> for the same reason as the appointment rows: the whole card is the
    // control, so it must be keyboard-operable rather than a click handler on a <div>.
    const card = document.createElement("button");
    card.type = "button";
    card.className = "doctor-ai-item";
    card.style.width = "100%";
    card.style.cursor = "pointer";
    card.setAttribute("aria-label", `Open ${patient.patient_name || "this patient"}`);

    const icon = document.createElement("div");
    icon.className = "doctor-ai-item-ico";
    icon.innerHTML = '<svg class="ai-i" viewBox="0 0 24 24" aria-hidden="true">'
      + '<circle cx="9" cy="8" r="4"/><path d="M2 21c0-4 3-7 7-7s7 3 7 7"/></svg>';

    const body = document.createElement("div");
    body.className = "doctor-ai-item-body";
    const title = document.createElement("div");
    title.className = "doctor-ai-item-title";
    title.textContent = patient.patient_name || "Unknown patient";
    const meta = document.createElement("div");
    meta.className = "doctor-ai-item-meta";
    meta.textContent = `${patient.visit_count || 0} visit${patient.visit_count === 1 ? "" : "s"} · Last: ${formatDateTime(patient.last_visit)}`;
    body.append(title, meta);

    card.append(icon, body);
    card.addEventListener("click", () => loadDoctorPatientDetail(patient.patient_id));
    doctorPatientsList.appendChild(card);
  });
}

async function loadDoctorPatientDetail(patientId) {
  // Back returns to where the doctor came from. It always went to Patients, so opening
  // a patient from the Overview's Today card and pressing Back left the Overview behind.
  doctorPatientDetailReturnView = doctorCurrentView;
  if (doctorPatientDetailBackBtn) {
    doctorPatientDetailBackBtn.textContent = {
      overview: "Back to overview", reviews: "Back to reviews",
      upcoming: "Back to appointments", past: "Back to appointments",
    }[doctorPatientDetailReturnView] || "Back to patients";
  }
  doctorPatientDetailId = patientId;
  try {
    const detail = await doctorAuthedJson(`/doctor/patients/${encodeURIComponent(patientId)}`);
    renderDoctorPatientDetail(detail);
    // Fired after the profile renders rather than awaited alongside it: the documents
    // list is supplementary, and a slow or failing storage backend must not delay (or
    // prevent) the patient's own details appearing.
    loadDoctorPatientDocuments(patientId);

    // The at-a-glance card. Fired without awaiting for the same reason as the others: it
    // may involve a model call on a cold cache, and the patient's own details must not
    // wait behind it.
    loadDoctorOverview(patientId);

    // The timeline itself is NOT fetched here — it is a wider disclosure and is audited,
    // so it loads when the doctor opens that tab. Only the filter options, which contain
    // no clinical content, are prepared in advance.
    resetDoctorTimelineForPatient(patientId);
    void loadDoctorTimelineFilters(patientId);
  } catch (error) {
    if (doctorPatientsCount) doctorPatientsCount.textContent = error.message || "Unable to load patient.";
  }
}

function setDoctorPatientTab(tab) {
  const next = ["documents", "timeline"].includes(tab) ? tab : "history";
  doctorPatientTab = next;
  doctorPatientTabButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.patientTab === next);
  });
  doctorPatientTabHistory?.classList.toggle("hidden", next !== "history");
  doctorPatientTabDocuments?.classList.toggle("hidden", next !== "documents");
  doctorPatientTabTimeline?.classList.toggle("hidden", next !== "timeline");

  // Loaded on demand, not with the patient: this is a wider disclosure and it is audited,
  // so it should be fetched when a doctor asks for it rather than on every patient open.
  if (next === "timeline" && timelineState.patientId && !timelineState.loaded) {
    void loadDoctorTimeline();
  }
  // The filter options load with the patient; if that failed, try again now that the
  // doctor is actually looking at them.
  if (next === "timeline" && timelineState.patientId
      && timelineState.filtersFor !== timelineState.patientId) {
    void loadDoctorTimelineFilters(timelineState.patientId);
  }
}

function describeVisitNote(visit) {
  if (visit.status === "cancelled") return "Cancelled";
  if (visit.note_status === "signed") return "Note signed";
  if (visit.note_status === "draft") return "Draft note awaiting your review";
  if (visit.note_status === "stale") return "Note held back — needs regenerating";
  if (visit.consult_status === "transcript_ready") return "Transcript ready, no note yet";
  if (visit.consult_status) return "Consultation in progress";
  return "No consultation recorded";
}

function renderDoctorPatientDetail(detail) {
  if (!detail) return;
  if (doctorPatientDetailName) doctorPatientDetailName.textContent = detail.name || "Patient";

  // Surfaced above the fold because it is the one thing here a clinician must not miss.
  // Rendered as the patient's own words, NOT as a structured allergy record — health_issues
  // is unvalidated free text, and styling it as a coded allergy would misrepresent it.
  const healthIssues = (detail.health_issues || "").trim();
  if (doctorPatientAlert && doctorPatientAlertBody) {
    doctorPatientAlertBody.textContent = healthIssues;
    doctorPatientAlert.classList.toggle("hidden", !healthIssues);
  }

  setDoctorPatientTab("history");

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
        // Opens that appointment — the visit list used to be read-only, with no way from a
        // patient's history to the note of a visit in it. A cancelled visit has nothing to
        // open, so it stays plain text rather than a button that leads nowhere.
        const openable = visit.status !== "cancelled";
        const card = document.createElement(openable ? "button" : "article");
        card.className = "admin-inline-card doctor-visit-card";
        if (openable) {
          card.type = "button";
          card.classList.add("is-openable");
          card.addEventListener("click", () => {
            void openReviewFromQueue({
              booking_id: visit.booking_id,
              patient_id: detail.patient_id,
              patient_name: detail.name,
              department: visit.department,
              appointment_start: visit.start_time,
              consultation_id: visit.consult_id,
              consult_status: visit.consult_status,
              consult_ended_at: visit.consult_ended_at,
            }, { status: visit.status, returnView: "patientDetail" });
          });
        }
        const head = document.createElement("div");
        head.className = "admin-inline-card-head";
        const titleWrap = document.createElement("div");
        const title = document.createElement("div");
        title.className = "admin-inline-title";
        title.textContent = formatDateTime(visit.start_time);
        const meta = document.createElement("div");
        meta.className = "admin-inline-meta";
        // What actually happened at this visit. It used to say "No clinical note yet" for
        // every visit, including ones with a signed note.
        meta.textContent = `${visit.department || "Department"} · ${describeVisitNote(visit)}`;
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

  showDoctorPane("patientDetail");
}

// ── Patient documents (treating-relationship scoped) ──────────────────────────

function setDoctorDocumentsMessage(text) {
  if (!doctorPatientDocumentsMessage) return;
  doctorPatientDocumentsMessage.textContent = text || "";
  doctorPatientDocumentsMessage.classList.toggle("hidden", !text);
}

async function loadDoctorPatientDocuments(patientId) {
  if (!doctorPatientDocumentsList) return;
  doctorPatientDocumentsList.replaceChildren();
  setDoctorDocumentsMessage("");
  if (doctorPatientDocumentsCount) doctorPatientDocumentsCount.textContent = "Loading...";

  try {
    const data = await doctorAuthedJson(`/doctor/patients/${encodeURIComponent(patientId)}/documents`);
    const documents = Array.isArray(data.documents) ? data.documents : [];

    // A slow request for a previously-opened patient must not overwrite the list of the
    // patient the doctor has since navigated to.
    if (doctorPatientDetailId !== patientId) return;

    if (doctorPatientDocumentsCount) {
      doctorPatientDocumentsCount.textContent = `${documents.length} document${documents.length === 1 ? "" : "s"}`;
    }
    if (!documents.length) {
      const note = document.createElement("p");
      note.className = "panel-note";
      note.textContent = "This patient has not uploaded any documents.";
      doctorPatientDocumentsList.appendChild(note);
      return;
    }
    documents.forEach((doc) =>
      doctorPatientDocumentsList.appendChild(buildPatientDocumentCard(patientId, doc))
    );
  } catch (error) {
    if (doctorPatientDetailId !== patientId) return;
    if (doctorPatientDocumentsCount) doctorPatientDocumentsCount.textContent = "Unable to load.";
    setDoctorDocumentsMessage(error.message);
  }
}

function buildPatientDocumentCard(patientId, doc) {
  const card = document.createElement("article");
  card.className = "admin-inline-card";

  const head = document.createElement("div");
  head.className = "admin-inline-card-head";

  const titleWrap = document.createElement("div");
  const title = document.createElement("div");
  title.className = "admin-inline-title";
  title.textContent = doc.original_filename || "Document";
  const meta = document.createElement("div");
  meta.className = "admin-inline-meta";
  const when = doc.clinical_date || (doc.uploaded_at ? formatDateTime(doc.uploaded_at) : "Date unknown");
  meta.textContent = `${formatDocumentType(doc.document_type)} · ${when}`;
  titleWrap.append(title, meta);

  // Whether any doctor treating this patient has verified it against the original — or
  // reported it inaccurate. Unverified model output still says so.
  const badge = buildDocumentReviewChip(doc.document_id, doc.review);

  head.append(titleWrap, badge);
  card.appendChild(head);

  const actions = document.createElement("div");
  actions.className = "form-actions";

  const summaryBtn = document.createElement("button");
  summaryBtn.type = "button";
  summaryBtn.className = "secondary compact";
  summaryBtn.textContent = "Show summary";

  const summaryBox = document.createElement("div");
  summaryBox.className = "panel-note clinical-note-citation-box hidden";

  let summaryLoaded = false;
  summaryBtn.addEventListener("click", async () => {
    if (summaryLoaded) {
      summaryBox.classList.toggle("hidden");
      return;
    }
    summaryBtn.disabled = true;
    summaryBox.textContent = "Loading summary...";
    summaryBox.classList.remove("hidden");
    try {
      // The clinician view: verified sentences plus independently parsed values. The
      // older endpoint returned the patient-register impression and the raw nested
      // findings blob, which rendered as JSON on a clinical screen.
      const payload = await doctorAuthedJson(
        `/doctor/patients/${encodeURIComponent(patientId)}/documents/${encodeURIComponent(doc.document_id)}/clinical`
      );
      renderDocumentClinical(summaryBox, payload);
      summaryLoaded = true;
    } catch (error) {
      summaryBox.textContent = error.message;
    } finally {
      summaryBtn.disabled = false;
    }
  });

  // Viewing is the primary action now; downloading is the fallback for anything the
  // browser will not render, and for taking a copy away.
  const viewBtn = document.createElement("button");
  viewBtn.type = "button";
  viewBtn.className = "secondary compact";
  viewBtn.textContent = "View";
  viewBtn.addEventListener("click", () => openDoctorDocumentViewer(patientId, doc));

  const downloadBtn = document.createElement("button");
  downloadBtn.type = "button";
  downloadBtn.className = "secondary compact";
  downloadBtn.textContent = "Download";
  downloadBtn.addEventListener("click", () =>
    downloadPatientDocument(patientId, doc, downloadBtn)
  );

  actions.append(viewBtn, summaryBtn, downloadBtn);
  card.append(actions, summaryBox);
  return card;
}

// ── Patient overview: the at-a-glance card ───────────────────────────────────
//
// Two renderings, and the doctor is always told which one they are reading:
//
//   phrased    — model prose that passed verification. Every line cites the facts it came
//                from, so a claim can be traced without leaving the card.
//   structured — the plain fact list, shown whenever the phrasing was rejected or could
//                not be produced. Drier, and completely faithful.
//
// Presenting the fallback as though it were the summary would hide that verification
// failed, which is precisely the signal a doctor should have.

const doctorOverviewBlock = document.querySelector("#doctorOverviewBlock");
const doctorOverviewLines = document.querySelector("#doctorOverviewLines");
const doctorOverviewMode = document.querySelector("#doctorOverviewMode");
const doctorOverviewNote = document.querySelector("#doctorOverviewNote");
const doctorOverviewUpdated = document.querySelector("#doctorOverviewUpdated");

function buildOverviewLabel(label) {
  // "Patient reports" and "Reported, unverified" are load-bearing: they say how far a
  // line can be relied on. Rendered as a chip so they cannot be skimmed past.
  const chip = document.createElement("span");
  chip.className = "doctor-ai-chip is-warn";
  chip.textContent = label;
  return chip;
}

function renderDoctorOverview(payload) {
  if (!doctorOverviewBlock || !doctorOverviewLines) return;
  doctorOverviewBlock.classList.remove("hidden");
  doctorOverviewLines.replaceChildren();

  const phrased = payload && payload.mode === "phrased";
  if (doctorOverviewMode) {
    doctorOverviewMode.textContent = phrased ? "AI drafted" : "Facts only";
    doctorOverviewMode.classList.toggle("is-ai", phrased);
  }
  if (doctorOverviewUpdated) {
    doctorOverviewUpdated.textContent = payload && payload.generated_at
      ? `Updated ${new Date(payload.generated_at).toLocaleString()}`
      : "";
  }

  const lines = (payload && payload.lines) || [];
  if (!lines.length) {
    const empty = document.createElement("p");
    empty.className = "panel-note";
    empty.textContent = "Nothing on record for this patient yet.";
    doctorOverviewLines.appendChild(empty);
  } else if (phrased) {
    const factsById = new Map(((payload && payload.facts) || []).map((fact) => [fact.id, fact]));
    lines.forEach((line) => {
      const row = document.createElement("p");
      row.className = "clinical-note-line";
      row.appendChild(document.createTextNode(String(line.text || "")));
      const cite = document.createElement("span");
      cite.className = "doctor-cite";
      cite.textContent = ` [${(line.fact_ids || []).join(", ")}]`;
      cite.title = "The facts this line was written from";
      row.appendChild(cite);
      // The labels of the facts this line cites, taken from the FACTS, not the prose.
      // "Patient reports" and "Reported, unverified" must never be hidden, and prose only
      // keeps them if the model chose to write them — verification checks fact ids and
      // numbers, not wording. Reading them off the cited facts makes them unconditional.
      const cited = (line.fact_ids || []).map((id) => factsById.get(String(id))).filter(Boolean);
      new Set(cited.map((fact) => fact.label).filter(Boolean))
        .forEach((label) => row.appendChild(buildOverviewLabel(label)));
      if (cited.some((fact) => fact.scanned)) row.appendChild(buildOverviewLabel("From a scanned document"));
      doctorOverviewLines.appendChild(row);
    });
  } else {
    // Structured fallback: heading, then each fact with its label.
    lines.forEach((group) => {
      const heading = document.createElement("div");
      heading.className = "admin-inline-meta";
      heading.textContent = group.heading;
      doctorOverviewLines.appendChild(heading);
      (group.items || []).forEach((item) => {
        const row = document.createElement("p");
        row.className = "clinical-note-line";
        row.appendChild(document.createTextNode(`• ${item.text}`));
        if (item.label) row.appendChild(buildOverviewLabel(item.label));
        // Read off a photograph: two AI passes over the same image have been seen to read a
        // drug name two different ways, so this is said, not assumed.
        if (item.scanned) row.appendChild(buildOverviewLabel("From a scanned document"));
        doctorOverviewLines.appendChild(row);
      });
    });
  }

  if (doctorOverviewNote) {
    doctorOverviewNote.textContent = phrased
      ? "Drafted by AI from this patient's record and checked against it line by line. "
        + "Open the source before acting on anything here."
      : (payload && payload.reason
          ? `Showing the facts directly: the AI summary could not be verified (${payload.reason}).`
          : "Showing the facts directly from this patient's record.");
  }
}

async function loadDoctorOverview(patientId) {
  if (!doctorOverviewBlock) return;
  // Clear the previous patient's card FIRST. It used to stay on screen, under the new
  // patient's name, for as long as this request took.
  doctorOverviewBlock.classList.remove("hidden");
  doctorOverviewLines?.replaceChildren();
  if (doctorOverviewMode) doctorOverviewMode.textContent = "Loading…";
  if (doctorOverviewNote) doctorOverviewNote.textContent = "";
  try {
    const overview = await doctorAuthedJson(
      `/doctor/patients/${encodeURIComponent(patientId)}/overview`
    );
    // A late answer for a patient the doctor has since left must never paint. This is not
    // hypothetical: a card that needs the model takes seconds, a cached one milliseconds, so
    // opening A then B quickly delivers A's diagnoses AFTER B's — under B's name.
    if (doctorPatientDetailId !== patientId) return;
    renderDoctorOverview(overview);
  } catch (error) {
    if (doctorPatientDetailId !== patientId) return;
    // A failed request says nothing about the patient. It must not render as "nothing on
    // record", which is a claim about them.
    doctorOverviewBlock.classList.remove("hidden");
    doctorOverviewLines?.replaceChildren();
    if (doctorOverviewMode) doctorOverviewMode.textContent = "Unavailable";
    if (doctorOverviewNote) {
      doctorOverviewNote.textContent = "The overview could not be loaded right now.";
    }
  }
}

// ── Cross-doctor patient timeline ────────────────────────────────────────────
//
// "Visit history" is this doctor's own appointments. This is every encounter the patient
// has had with anyone, which is a wider disclosure than the workspace previously made —
// hence the audit notice on the panel and the audit row on the server.
//
// Two things must never blur on this screen: an encounter with no signed note, and one
// whose note is being WITHHELD. They are rendered differently and worded differently,
// because a doctor who reads "no note" when the truth is "restricted" concludes there is
// no history when there is.

const doctorTimelineList = document.querySelector("#doctorTimelineList");
const doctorTimelineCount = document.querySelector("#doctorTimelineCount");
const doctorTimelineMore = document.querySelector("#doctorTimelineMore");

// rerun: a filter changed while a load was in flight, so load again once it finishes with
// the filters as they are NOW. The in-flight guard used to simply drop the change, leaving
// the list showing results for filters the doctor had already moved away from.
// filtersFor: the patient whose filter options loaded successfully, so opening the tab can
// retry them if they did not — a failed load used to leave the dropdowns empty until a
// hard refresh.
// facets / unlinkedTypes: what the filter dropdowns narrow from (narrowTimelineFilters).
const timelineState = {
  patientId: null, cursor: null, loading: false, loaded: 0, rerun: false, filtersFor: null,
  facets: null, unlinkedTypes: [],
};

/** A new patient's timeline starts empty and unfiltered. The date inputs used to keep the
 *  previous patient's range, and the previous patient's encounters stayed in the (hidden)
 *  timeline tab until it was next opened. The dropdowns are refilled by
 *  loadDoctorTimelineFilters. */
function resetDoctorTimelineForPatient(patientId) {
  timelineState.patientId = patientId;
  timelineState.loaded = 0;
  timelineState.cursor = null;
  // A change queued for the previous patient must not fire a load for this one — the
  // timeline is audited, and loads only when the doctor opens the tab.
  timelineState.rerun = false;
  timelineState.filtersFor = null;
  // Another patient's visits must not narrow this one's dropdowns.
  timelineState.facets = null;
  timelineState.unlinkedTypes = [];
  ["#doctorTimelineFrom", "#doctorTimelineTo"].forEach((selector) => {
    const input = document.querySelector(selector);
    if (input) input.value = "";
  });
  doctorTimelineList?.replaceChildren();
  doctorTimelineMore?.classList.add("hidden");
  if (doctorTimelineCount) doctorTimelineCount.textContent = "";
}

function timelineFilterValues() {
  return {
    department: document.querySelector("#doctorTimelineDepartment")?.value || "",
    doctor_id: document.querySelector("#doctorTimelineDoctor")?.value || "",
    document_type: document.querySelector("#doctorTimelineDocType")?.value || "",
    date_from: document.querySelector("#doctorTimelineFrom")?.value || "",
    date_to: document.querySelector("#doctorTimelineTo")?.value || "",
  };
}

function buildTimelineEncounter(encounter) {
  const card = document.createElement("article");
  card.className = "admin-inline-card doctor-timeline-card";

  // <details> rather than a custom toggle: keyboard and screen-reader behaviour come for
  // free, and the brief asked for collapsible entries.
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.className = "doctor-timeline-summary";

  const when = document.createElement("strong");
  when.textContent = encounter.start_time ? formatDateTime(encounter.start_time) : "Date unknown";

  const who = document.createElement("span");
  who.className = "admin-inline-meta";
  who.textContent = `${encounter.doctor_name || "Unknown doctor"} · ${encounter.department || "—"}`;

  summary.append(when, who);

  const status = document.createElement("span");
  status.className = "admin-status-pill";
  status.textContent = encounter.status || "unknown";
  summary.appendChild(status);

  if (encounter.is_own) {
    const own = document.createElement("span");
    own.className = "doctor-ai-chip";
    own.textContent = "Your appointment";
    summary.appendChild(own);
  }
  if (encounter.restricted) {
    const flag = document.createElement("span");
    flag.className = "doctor-ai-chip is-warn";
    flag.textContent = "Restricted";
    summary.appendChild(flag);
  }
  if ((encounter.documents || []).length) {
    const docs = document.createElement("span");
    docs.className = "doctor-ai-chip";
    docs.textContent = `${encounter.documents.length} document${encounter.documents.length === 1 ? "" : "s"}`;
    summary.appendChild(docs);
  }

  details.appendChild(summary);

  const body = document.createElement("div");
  body.className = "doctor-timeline-body";

  if (encounter.reason) {
    // The booking note — often the assistant's formatted summary, rendered the same way
    // as in the visit brief rather than showing its markdown symbols.
    const reason = document.createElement("div");
    reason.className = "clinical-note-line";
    const label = document.createElement("strong");
    label.textContent = "Reason for booking";
    reason.append(label, renderBookingNoteMarkdown(encounter.reason));
    body.appendChild(reason);
  }

  const note = document.createElement("p");
  note.className = encounter.restricted ? "clinical-note-flag" : "clinical-note-line";
  if (!encounter.note) {
    // Said explicitly. An absent line here would read as "nothing happened".
    note.textContent = "No signed note for this visit.";
  } else if (encounter.note.restricted) {
    note.textContent = encounter.note.summary;
  } else {
    const label = document.createElement("strong");
    label.textContent = "Note: ";
    note.append(label, document.createTextNode(encounter.note.summary || "Signed, no assessment recorded."));
  }
  body.appendChild(note);

  if (encounter.prescription) {
    const prescription = document.createElement("p");
    prescription.className = "clinical-note-line";
    const label = document.createElement("strong");
    label.textContent = "Prescription: ";
    prescription.append(label, document.createTextNode(encounter.prescription));
    body.appendChild(prescription);
  }

  (encounter.documents || []).forEach((doc) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary compact";
    button.textContent = `${doc.original_filename || "Document"}`;
    button.addEventListener("click", () =>
      openDoctorDocumentViewer(timelineState.patientId, {
        ...doc, content_type: doc.content_type || "",
      })
    );
    body.appendChild(button);
  });

  details.appendChild(body);
  card.appendChild(details);
  return card;
}

/** A document the patient uploaded that no visit record ties to a booking — shown on its
 *  own, dated by the report, rather than guessed onto whichever visit came next. */
function buildTimelineDocument(item) {
  const card = document.createElement("article");
  card.className = "admin-inline-card doctor-timeline-card doctor-timeline-document";

  const head = document.createElement("div");
  head.className = "doctor-timeline-summary";
  const when = document.createElement("strong");
  when.textContent = item.clinical_date ? formatBriefDate(item.clinical_date) : formatDateTime(item.uploaded_at);
  const what = document.createElement("span");
  what.className = "admin-inline-meta";
  const bits = [formatDocumentType(item.document_type), "uploaded by the patient, not linked to a visit"];
  if (item.copies > 1) bits.push(`uploaded ${item.copies} times`);
  what.textContent = bits.join(" · ");
  head.append(when, what);
  card.appendChild(head);

  const open = document.createElement("button");
  open.type = "button";
  open.className = "secondary compact";
  open.textContent = item.original_filename || "Document";
  open.setAttribute("aria-label", `View ${item.original_filename || "document"}`);
  open.addEventListener("click", () =>
    openDoctorDocumentViewer(timelineState.patientId, { ...item, content_type: item.content_type || "" })
  );
  card.appendChild(open);
  return card;
}

async function loadDoctorTimeline({ append = false } = {}) {
  if (!doctorTimelineList || !timelineState.patientId) return;
  if (timelineState.loading) {
    // "Show older" pressed twice is just ignored; a changed filter is remembered.
    if (!append) timelineState.rerun = true;
    return;
  }
  const patientId = timelineState.patientId;
  timelineState.loading = true;
  if (!append) {
    timelineState.cursor = null;
    timelineState.loaded = 0;
    doctorTimelineList.replaceChildren();
  }
  if (doctorTimelineCount) doctorTimelineCount.textContent = "Loading…";

  try {
    const filters = timelineFilterValues();
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => { if (value) query.set(key, value); });
    if (append && timelineState.cursor) query.set("cursor", timelineState.cursor);

    const data = await doctorAuthedJson(
      `/doctor/patients/${encodeURIComponent(patientId)}/timeline?${query}`
    );
    // The doctor opened another patient while this was in flight: these are the previous
    // patient's encounters and must not appear under the new one.
    if (timelineState.patientId !== patientId) return;
    // Visits and the documents that belong to no visit, in one date order.
    const items = data.items || (data.encounters || []).map((encounter) => ({ kind: "encounter", ...encounter }));
    items.forEach((item) => doctorTimelineList.appendChild(
      item.kind === "document" ? buildTimelineDocument(item) : buildTimelineEncounter(item)
    ));
    timelineState.loaded += items.length;
    timelineState.cursor = data.next_cursor;

    if (doctorTimelineCount) {
      doctorTimelineCount.textContent = timelineState.loaded
        ? `${timelineState.loaded} entr${timelineState.loaded === 1 ? "y" : "ies"}`
          + (data.has_more ? " so far" : "")
        : "Nothing matches these filters.";
    }
    doctorTimelineMore?.classList.toggle("hidden", !data.has_more);
  } catch (error) {
    if (timelineState.patientId !== patientId) return;
    if (doctorTimelineCount) {
      doctorTimelineCount.textContent =
        error && error.message ? error.message : "The timeline could not be loaded.";
    }
  } finally {
    timelineState.loading = false;
    if (timelineState.rerun) {
      timelineState.rerun = false;
      void loadDoctorTimeline();
    }
  }
}

/** Department narrows the doctors; department and doctor narrow the document types —
 *  so every option offered matches something. From the facets the server sent with the
 *  filter lists (visits per department and doctor, with the document types they hold, and
 *  the types of documents that belong to no visit). A choice the new narrowing no longer
 *  offers falls back to "All" rather than silently matching nothing. */
function narrowTimelineFilters() {
  const facets = timelineState.facets;
  if (!facets) return;
  const departmentSelect = document.querySelector("#doctorTimelineDepartment");
  const doctorSelect = document.querySelector("#doctorTimelineDoctor");
  const typeSelect = document.querySelector("#doctorTimelineDocType");
  if (!departmentSelect || !doctorSelect || !typeSelect) return;

  const refill = (select, options) => {
    const keep = select.value;
    const first = select.querySelector("option");
    select.replaceChildren(first);
    options.forEach(({ value, label }) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      select.appendChild(option);
    });
    select.value = options.some((option) => option.value === keep) ? keep : "";
  };

  const department = departmentSelect.value;
  const inDepartment = facets.filter((facet) => !department || facet.department === department);
  const doctors = [];
  inDepartment.forEach((facet) => {
    if (!doctors.some((d) => d.value === facet.doctor_id)) doctors.push({ value: facet.doctor_id, label: facet.doctor_name });
  });
  refill(doctorSelect, doctors);

  const doctor = doctorSelect.value;
  const chosen = inDepartment.filter((facet) => !doctor || facet.doctor_id === doctor);
  const types = new Set(chosen.flatMap((facet) => facet.document_types || []));
  // Documents that belong to no visit have no department or doctor: offered only while
  // neither is chosen, exactly when the timeline includes them.
  if (!department && !doctor) (timelineState.unlinkedTypes || []).forEach((type) => types.add(type));
  refill(typeSelect, [...types].sort().map((type) => ({ value: type, label: formatDocumentType(type) })));
}

async function loadDoctorTimelineFilters(patientId) {
  // `format` names the option for display; the value stays what the server filters on.
  const fill = (selector, values, labelKey, valueKey, format = null) => {
    const select = document.querySelector(selector);
    if (!select) return;
    const first = select.querySelector("option");
    select.replaceChildren(first);
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = valueKey ? value[valueKey] : value;
      const label = labelKey ? value[labelKey] : value;
      option.textContent = format ? format(label) : label;
      select.appendChild(option);
    });
  };
  // Emptied up front, so a failed request cannot leave the PREVIOUS patient's doctors and
  // departments offered as filters for this one.
  ["#doctorTimelineDepartment", "#doctorTimelineDoctor", "#doctorTimelineDocType"]
    .forEach((selector) => fill(selector, []));
  try {
    const filters = await doctorAuthedJson(
      `/doctor/patients/${encodeURIComponent(patientId)}/timeline/filters`
    );
    // Same late-answer guard as the overview: these name another patient's doctors.
    if (timelineState.patientId !== patientId) return;
    timelineState.filtersFor = patientId;
    timelineState.facets = filters.facets || null;
    timelineState.unlinkedTypes = filters.unlinked_document_types || [];
    fill("#doctorTimelineDepartment", filters.departments || []);
    fill("#doctorTimelineDoctor", filters.doctors || [], "name", "doctor_id");
    fill("#doctorTimelineDocType", filters.document_types || [], null, null, formatDocumentType);
    narrowTimelineFilters();
  } catch (error) {
    // A failed filter list must not stop the timeline itself loading — the doctor can
    // still read the history, just without narrowing it.
  }
}

// ── In-app document viewer ───────────────────────────────────────────────────
//
// Doctors could previously only DOWNLOAD a patient's documents, which means leaving the
// workspace, opening a file from disk, and reading it with no summary beside it.
//
// HOW THIS STAYS SAFE. The file route keeps Content-Disposition: attachment and its
// four-entry type allowlist, both unchanged — a stored file the browser renders inline is
// stored XSS against the doctor's authenticated session on this same origin, and that
// decision is documented at document_catalog._content_type_for. Nothing here weakens it:
// the bytes are fetched with fetch() and drawn into a <canvas>, so the browser never
// navigates to document content and the disposition header is irrelevant. It also means
// every byte still passes our auth and our audit, which a signed storage URL would not.

const doctorViewer = document.querySelector("#doctorViewer");
const doctorViewerCanvas = document.querySelector("#doctorViewerCanvas");
const doctorViewerStage = document.querySelector("#doctorViewerStage");
const doctorViewerStatus = document.querySelector("#doctorViewerStatus");
const doctorViewerPageLabel = document.querySelector("#doctorViewerPage");
const doctorViewerBrightness = document.querySelector("#doctorViewerBrightness");
const doctorViewerContrast = document.querySelector("#doctorViewerContrast");

const VIEWER_ZOOM_MIN = 0.4;
const VIEWER_ZOOM_MAX = 5;
const VIEWER_ZOOM_STEP = 1.25;

// PDF.js is ~1.4 MB and most sessions never open a document, so it is loaded on first use
// rather than on page load. The promise is cached, so a second open does not re-fetch it.
//
// A script tag, not import(): this is the UMD build, which sets window.pdfjsLib. The ESM
// build was tried first and its worker silently never starts when the files are served
// as .js — getDocument() neither resolves nor rejects. See scripts/fetch_pdfjs.py.
let pdfjsPromise = null;
function loadPdfJs() {
  if (!pdfjsPromise) {
    pdfjsPromise = new Promise((resolve, reject) => {
      if (window.pdfjsLib) return resolve(window.pdfjsLib);
      const script = document.createElement("script");
      script.src = "/static/vendor/pdfjs/pdf.min.js";
      script.onload = () => {
        if (!window.pdfjsLib) return reject(new Error("The PDF viewer could not be loaded."));
        // The worker keeps parsing off the UI thread; without it a large PDF freezes the
        // whole workspace while it renders.
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.js";
        resolve(window.pdfjsLib);
      };
      script.onerror = () => reject(new Error("The PDF viewer could not be loaded."));
      document.head.appendChild(script);
    }).catch((error) => {
      // Do not cache a failure — a transient load error must not disable the viewer for
      // the rest of the session.
      pdfjsPromise = null;
      throw error;
    });
  }
  return pdfjsPromise;
}

const viewerState = {
  kind: null, pdf: null, image: null, page: 1, pages: 1,
  zoom: 1, rotation: 0, patientId: null, doc: null, objectUrl: null,
};

/** "pdf" | "image" | "unsupported", decided from the file's own magic bytes.
 *
 *  The declared content type is only a hint, and a weak one: it is derived from the
 *  filename's extension against a four-entry allowlist, so a perfectly valid JPEG stored
 *  without a recognised extension is reported as application/octet-stream.
 *
 *  Signatures rather than a library: three formats, four checks, no dependency.
 */
async function sniffDocumentKind(blob, declaredType) {
  try {
    const head = new Uint8Array(await blob.slice(0, 8).arrayBuffer());
    const startsWith = (bytes) => bytes.every((byte, index) => head[index] === byte);

    if (startsWith([0x25, 0x50, 0x44, 0x46])) return "pdf";                    // %PDF
    if (startsWith([0x89, 0x50, 0x4E, 0x47])) return "image";                  // \x89PNG
    if (startsWith([0xFF, 0xD8, 0xFF])) return "image";                        // JPEG SOI
  } catch (error) {
    // Fall through to the declared type rather than failing the open outright.
  }

  const declared = String(declaredType || "");
  if (declared.startsWith("image/")) return "image";
  if (declared === "application/pdf") return "pdf";
  return "unsupported";
}

function setViewerStatus(message) {
  if (!doctorViewerStatus) return;
  doctorViewerStatus.textContent = message || "";
  doctorViewerStatus.classList.toggle("hidden", !message);
}

function applyViewerFilter() {
  if (!doctorViewerCanvas) return;
  const brightness = Number(doctorViewerBrightness?.value || 100);
  const contrast = Number(doctorViewerContrast?.value || 100);
  doctorViewerCanvas.style.filter = `brightness(${brightness}%) contrast(${contrast}%)`;
}

async function renderViewerPage() {
  if (!doctorViewerCanvas) return;
  const context = doctorViewerCanvas.getContext("2d");

  if (viewerState.kind === "image") {
    const image = viewerState.image;
    const swap = viewerState.rotation % 180 !== 0;
    const width = (swap ? image.height : image.width) * viewerState.zoom;
    const height = (swap ? image.width : image.height) * viewerState.zoom;
    doctorViewerCanvas.width = Math.max(1, Math.round(width));
    doctorViewerCanvas.height = Math.max(1, Math.round(height));
    context.save();
    context.translate(doctorViewerCanvas.width / 2, doctorViewerCanvas.height / 2);
    context.rotate((viewerState.rotation * Math.PI) / 180);
    context.drawImage(
      image,
      (-image.width * viewerState.zoom) / 2, (-image.height * viewerState.zoom) / 2,
      image.width * viewerState.zoom, image.height * viewerState.zoom,
    );
    context.restore();
    if (doctorViewerPageLabel) doctorViewerPageLabel.textContent = "Image";
    applyViewerFilter();
    return;
  }

  if (viewerState.kind !== "pdf" || !viewerState.pdf) return;
  const page = await viewerState.pdf.getPage(viewerState.page);
  const viewport = page.getViewport({ scale: viewerState.zoom, rotation: viewerState.rotation });
  doctorViewerCanvas.width = Math.max(1, Math.round(viewport.width));
  doctorViewerCanvas.height = Math.max(1, Math.round(viewport.height));
  await page.render({ canvasContext: context, viewport }).promise;
  if (doctorViewerPageLabel) {
    doctorViewerPageLabel.textContent = `${viewerState.page} / ${viewerState.pages}`;
  }
  applyViewerFilter();
}

function closeDoctorViewer() {
  if (!doctorViewer) return;
  doctorViewer.classList.add("hidden");
  // Release the decoded document. A patient's record must not sit in memory behind a
  // closed overlay for the rest of the session.
  if (viewerState.objectUrl) URL.revokeObjectURL(viewerState.objectUrl);
  if (viewerState.pdf && typeof viewerState.pdf.destroy === "function") viewerState.pdf.destroy();
  Object.assign(viewerState, {
    kind: null, pdf: null, image: null, page: 1, pages: 1,
    zoom: 1, rotation: 0, patientId: null, doc: null, objectUrl: null,
  });
  if (doctorViewerBrightness) doctorViewerBrightness.value = "100";
  if (doctorViewerContrast) doctorViewerContrast.value = "100";
  const context = doctorViewerCanvas?.getContext("2d");
  if (context) context.clearRect(0, 0, doctorViewerCanvas.width, doctorViewerCanvas.height);
}

/** Opens one document beside its verified summary. */
async function openDoctorDocumentViewer(patientId, doc) {
  if (!doctorViewer) return;
  viewerState.patientId = patientId;
  viewerState.doc = doc;
  viewerState.zoom = 1;
  viewerState.rotation = 0;
  viewerState.page = 1;

  doctorViewer.classList.remove("hidden");
  document.querySelector("#doctorViewerTitle").textContent = doc.original_filename || "Document";
  document.querySelector("#doctorViewerMeta").textContent =
    `${formatDocumentType(doc.document_type)} · ${doc.clinical_date || "date unknown"}`;
  setViewerStatus("Loading document…");
  doctorViewerStage?.focus();

  // The summary loads independently of the file: a document that will not render is
  // still worth reading about, and a summary that fails must not blank the document.
  const summaryHost = document.querySelector("#doctorViewerSummary");
  if (summaryHost) {
    summaryHost.replaceChildren();
    doctorAuthedJson(
      `/doctor/patients/${encodeURIComponent(patientId)}/documents/${encodeURIComponent(doc.document_id)}/clinical`
    ).then((payload) => {
      // A late answer for a document the doctor has since moved away from must not be
      // shown — least of all with a Verify button — beside a different document's file.
      if (viewerState.doc !== doc) return;
      renderDocumentClinical(summaryHost, payload, { patientId });
    })
     .catch(() => {
       if (viewerState.doc === doc) summaryHost.textContent = "The summary could not be loaded.";
     });
  }

  try {
    // Same authenticated, audited route the download button uses. Fetched as bytes, so
    // its attachment disposition is irrelevant and nothing is rendered by the browser.
    const response = await fetch(
      `/doctor/patients/${encodeURIComponent(patientId)}/documents/${encodeURIComponent(doc.document_id)}/file`,
      { headers: doctorAuthHeaders() },
    );
    if (!response.ok) {
      throw new Error(
        response.status === 404
          ? "The original file for this document is no longer available."
          : "This document could not be opened right now."
      );
    }
    const blob = await response.blob();

    // Decide from the BYTES, not from the filename's extension.
    //
    // content_type comes from document_catalog._content_type_for, which maps a four-entry
    // extension allowlist and returns application/octet-stream for anything else — so a
    // JPEG stored without a usable extension arrives as octet-stream, fell into the PDF
    // branch, and showed the doctor "Invalid PDF structure." about a file that is not a
    // PDF and renders perfectly well. Sniffing fixes the file rather than the message.
    //
    // Safe to sniff here precisely because the result only ever chooses between "draw on
    // a canvas" and "parse as PDF". It never sets a Content-Type, never reaches the
    // server, and cannot cause anything to be rendered as a document.
    const kind = await sniffDocumentKind(blob, doc.content_type);

    if (kind === "unsupported") {
      throw new Error(
        "This file type cannot be previewed in the browser. Use Download to open it."
      );
    }

    // Paging belongs to PDFs. Leaving the controls live on an image gives the doctor two
    // buttons that silently do nothing.
    const isPdf = kind === "pdf";
    document.querySelector("#doctorViewerPrev")?.classList.toggle("hidden", !isPdf);
    document.querySelector("#doctorViewerNext")?.classList.toggle("hidden", !isPdf);

    if (kind === "image") {
      const image = new Image();
      viewerState.objectUrl = URL.createObjectURL(blob);
      await new Promise((resolve, reject) => {
        image.onload = resolve;
        image.onerror = () => reject(new Error("This image could not be decoded."));
        image.src = viewerState.objectUrl;
      });
      viewerState.kind = "image";
      viewerState.image = image;
      viewerState.pages = 1;
      // Fit a large scan to the stage on open, rather than showing its top-left corner.
      const available = (doctorViewerStage?.clientWidth || image.width) - 32;
      if (image.width > available) viewerState.zoom = Math.max(VIEWER_ZOOM_MIN, available / image.width);
    } else {
      const pdfjs = await loadPdfJs();
      const data = new Uint8Array(await blob.arrayBuffer());
      viewerState.pdf = await pdfjs.getDocument({ data }).promise;
      viewerState.kind = "pdf";
      viewerState.pages = viewerState.pdf.numPages;
      const first = await viewerState.pdf.getPage(1);
      const available = (doctorViewerStage?.clientWidth || 900) - 32;
      viewerState.zoom = Math.max(
        VIEWER_ZOOM_MIN, Math.min(2, available / first.getViewport({ scale: 1 }).width)
      );
    }

    setViewerStatus("");
    await renderViewerPage();
  } catch (error) {
    // Says what failed. "Download original" stays available, so a document that will not
    // render in the browser is still reachable.
    setViewerStatus(error && error.message ? error.message : "This document could not be opened.");
  }
}

function stepViewerPage(delta) {
  if (viewerState.kind !== "pdf") return;
  const next = Math.min(viewerState.pages, Math.max(1, viewerState.page + delta));
  if (next === viewerState.page) return;
  viewerState.page = next;
  void renderViewerPage();
}

function zoomViewer(factor) {
  viewerState.zoom = Math.min(VIEWER_ZOOM_MAX, Math.max(VIEWER_ZOOM_MIN, viewerState.zoom * factor));
  void renderViewerPage();
}

/** The clinician view of a document: a verified summary beside independently parsed values.
 *
 *  The two halves come from different pipelines on purpose. The prose is model output that
 *  survived quote-and-number verification; the chips are values parsed by code and
 *  classified against code-owned reference ranges. A doctor reading "Vitamin D is deficient
 *  at 13.8 ng/mL" sees 13.8 beside it, arrived at independently — so a plausible-sounding
 *  sentence always has something to be checked against.
 *
 *  Text nodes only, never innerHTML: every string here is derived from a patient's
 *  document and from model output.
 */
function renderDocumentClinical(container, payload, context = {}) {
  container.replaceChildren();
  const summary = payload && payload.summary;
  const findings = Array.isArray(payload && payload.findings) ? payload.findings : [];

  // Whether a clinician has checked this against the original — shared by every doctor
  // treating the patient. Replaces the fixed "not reviewed by a clinician" line.
  const reviewHost = document.createElement("div");
  container.appendChild(reviewHost);
  renderDocumentReview(reviewHost, context.patientId, payload && payload.document_id, payload && payload.review);

  // What the verifier did to the model's summary — a different fact from whether a
  // clinician has checked it, so it is said separately.
  let verificationNote = "";
  if (!summary) {
    // Never generated is not the same as generated-and-unverifiable, and a doctor should
    // not have to guess which they are looking at.
    verificationNote = "No AI summary has been generated for this document.";
  } else if (summary.verification === "failed") {
    verificationNote =
      "No part of the AI summary could be matched to this document, so none is shown. "
      + "The values below are read directly from the document.";
  } else if (summary.verification === "partial") {
    // The verb agrees too, not just the noun: "1 sentence ... was removed".
    const one = summary.rejected_count === 1;
    verificationNote =
      `${summary.rejected_count} AI sentence${one ? "" : "s"} could not be matched to the `
      + `document and ${one ? "was" : "were"} removed.`;
  }
  if (verificationNote) {
    const note = document.createElement("p");
    note.className = "clinical-note-flag";
    note.textContent = verificationNote;
    container.appendChild(note);
  }

  // A scanned document's quotes were checked against a transcription of an image, not a
  // text layer. That is a materially weaker guarantee and must not be presented as equal.
  if (summary && summary.source_kind === "vision_transcription") {
    const scanned = document.createElement("p");
    scanned.className = "clinical-note-flag";
    scanned.textContent =
      "From a scanned document — the summary was checked against a transcription of the "
      + "image, not the document's own text. Verify against the original.";
    container.appendChild(scanned);
  }

  (summary && Array.isArray(summary.sentences) ? summary.sentences : []).forEach((sentence) => {
    const line = document.createElement("p");
    line.className = "clinical-note-line";
    line.appendChild(document.createTextNode(String(sentence.text || "")));
    if (sentence.page_no) {
      // The page the verifier LOCATED the quote on, not the one the model claimed.
      const cite = document.createElement("span");
      cite.className = "doctor-cite";
      cite.textContent = ` [p${sentence.page_no}]`;
      cite.title = String(sentence.quote || "");
      line.appendChild(cite);
    }
    container.appendChild(line);
  });

  renderDocumentCoverage(container, payload && payload.coverage, summary);

  renderDocumentAbnormalResults(container, findings, payload && payload.completeness);

  // The AI nutritionist for this document's abnormal results — only when it has some.
  const hasAbnormal = findings.some((row) => row.abnormal === "low" || row.abnormal === "high");
  if (hasAbnormal && context.patientId && payload && payload.document_id) {
    container.appendChild(buildNutritionSection(
      `/doctor/patients/${encodeURIComponent(context.patientId)}/documents/${encodeURIComponent(payload.document_id)}/nutrition`,
      "From this document's abnormal results.",
    ));
  }
}

/** "Nothing missed", for any kind of document: every line of it is in a verified sentence,
 *  a parsed result, or was set aside as non-clinical. Lines in none of those are shown here
 *  exactly as the document has them — a medication the summary forgot, or a sentence
 *  dropped at verification, appears rather than disappearing. The set-aside lines are
 *  shown on request, so what was left out as "letterhead" can be checked too. */
function renderDocumentCoverage(container, coverage, summary) {
  if (!coverage) return;
  const uncovered = coverage.uncovered || [];
  // Set aside by the model as non-clinical (checked verbatim, and refused if clinical), and
  // the layout of a results table recognised by code: shown together, on request.
  const setAside = [...(coverage.not_clinical || []), ...(coverage.structural || [])];
  const scanned = summary && summary.source_kind === "vision_transcription";

  if (uncovered.length) {
    const heading = document.createElement("h4");
    heading.className = "doctor-abnormal-heading";
    heading.textContent = `Also in the document — not in the summary (${uncovered.length})`;
    container.appendChild(heading);
    const note = document.createElement("p");
    note.className = "doctor-coverage-note";
    note.textContent = scanned
      ? "As transcribed from the scan, word for word. Check against the original."
      : "Word for word from the document.";
    container.appendChild(note);
    const list = document.createElement("ul");
    list.className = "doctor-coverage-list";
    uncovered.forEach((line) => {
      const item = document.createElement("li");
      if (line.context) {
        // The line a wrapped sentence continues, so its second half reads as a sentence.
        const context = document.createElement("span");
        context.className = "doctor-coverage-context";
        context.textContent = `${line.context} `;
        item.appendChild(context);
      }
      item.appendChild(document.createTextNode(String(line.text || "")));
      if (line.page_no) {
        const cite = document.createElement("span");
        cite.className = "doctor-cite";
        cite.textContent = ` [p${line.page_no}]`;
        item.appendChild(cite);
      }
      list.appendChild(item);
    });
    container.appendChild(list);
  } else if (summary && (summary.sentences || []).length) {
    const done = document.createElement("p");
    done.className = "doctor-coverage-note";
    done.textContent = "Every line of the document is in the summary, the results below, or was set aside as a heading or non-clinical.";
    container.appendChild(done);
  }

  if (setAside.length) {
    const details = document.createElement("details");
    details.className = "doctor-coverage-aside";
    const label = document.createElement("summary");
    label.textContent = `Set aside as headings or non-clinical (${setAside.length} lines)`;
    details.appendChild(label);
    const list = document.createElement("ul");
    list.className = "doctor-coverage-list";
    setAside.forEach((text) => {
      const item = document.createElement("li");
      item.textContent = String(text);
      list.appendChild(item);
    });
    details.appendChild(list);
    container.appendChild(details);
  }
}

// ---- verifying a document, shared by every doctor treating the patient ----
//
// app/services/document_reviews.py holds the rules: each doctor verifies (or reports) on
// their own name, everyone sees who did, a report outranks any number of verifications,
// and a doctor can undo only their own.

const DOCUMENT_REVIEW_STATUS_TEXT = {
  flagged: "Reported inaccurate by a clinician",
  verified: "Verified against the original",
  unverified: "AI generated — not yet verified by a clinician",
};

/** The short form used on cards, brief rows and drill rows. */
function describeDocumentReview(review) {
  const status = review && review.status;
  if (status === "flagged") return { text: "Reported inaccurate", modifier: "is-bad" };
  if (status === "verified") {
    const people = review.verified_by || [];
    const first = people[0];
    const who = first ? (first.is_me ? "you" : first.name || "a clinician") : "a clinician";
    const more = people.length > 1 ? ` +${people.length - 1}` : "";
    return { text: `Verified · ${who}${more}`, modifier: "is-ok" };
  }
  return { text: "AI generated · not verified", modifier: "is-ai" };
}

function buildDocumentReviewChip(documentId, review) {
  const { text, modifier } = describeDocumentReview(review);
  const chip = buildAiChip(text, modifier);
  chip.classList.add("doctor-review-chip");
  chip.dataset.documentId = documentId || "";
  return chip;
}

/** After a doctor verifies or reports in the viewer, every chip for that document on the
 *  page says so — the card, the brief row, the drill row — without a reload. */
function refreshDocumentReviewChips(documentId, review) {
  document.querySelectorAll(".doctor-review-chip").forEach((chip) => {
    if (chip.dataset.documentId === documentId) chip.replaceWith(buildDocumentReviewChip(documentId, review));
  });
}

function formatReviewer(person) {
  const who = person.is_me ? "You" : person.name || "A clinician";
  const department = !person.is_me && person.department ? ` (${person.department})` : "";
  const when = person.at ? `, ${formatBriefDate(person.at)}` : "";
  return `${who}${department}${when}`;
}

/** The status and the doctor's own controls, at the top of the viewer's side panel. */
function renderDocumentReview(host, patientId, documentId, review) {
  host.replaceChildren();
  const state = review || { status: "unverified", verified_by: [], flagged_by: [], mine: null };
  host.className = `doctor-review-block is-${state.status}`;

  const status = document.createElement("p");
  status.className = "doctor-review-status";
  status.textContent = DOCUMENT_REVIEW_STATUS_TEXT[state.status] || DOCUMENT_REVIEW_STATUS_TEXT.unverified;
  host.appendChild(status);

  (state.flagged_by || []).forEach((person) => {
    const line = document.createElement("p");
    line.className = "doctor-review-line";
    line.textContent = `${formatReviewer(person)}: “${person.reason || ""}”`;
    host.appendChild(line);
  });
  if ((state.verified_by || []).length) {
    const line = document.createElement("p");
    line.className = "doctor-review-line";
    line.textContent = `Verified by ${state.verified_by.map(formatReviewer).join(" · ")}`;
    host.appendChild(line);
  }
  if (!patientId || !documentId) return;

  const actions = document.createElement("div");
  actions.className = "doctor-review-actions";
  const message = document.createElement("p");
  message.className = "doctor-review-message";
  message.setAttribute("role", "status");

  const buttons = [];
  const makeButton = (label, onClick, variant = "secondary") => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `${variant} compact`;
    button.textContent = label;
    button.addEventListener("click", onClick);
    buttons.push(button);
    actions.appendChild(button);
    return button;
  };

  const send = async (action, reason = null) => {
    buttons.forEach((button) => { button.disabled = true; });
    message.textContent = "Saving…";
    try {
      const data = await doctorAuthedJson(
        `/doctor/patients/${encodeURIComponent(patientId)}/documents/${encodeURIComponent(documentId)}/review`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, reason }) },
      );
      // Only if the viewer still shows this document.
      if (viewerState.doc && viewerState.doc.document_id !== documentId) return;
      renderDocumentReview(host, patientId, documentId, data.review);
      refreshDocumentReviewChips(documentId, data.review);
    } catch (error) {
      message.textContent = error && error.message ? error.message : "That could not be saved.";
      buttons.forEach((button) => { button.disabled = false; });
    }
  };

  if (state.mine === "verified") {
    makeButton("Withdraw my verification", () => { void send("withdraw"); });
  } else {
    makeButton("Mark verified", () => {
      const ok = window.confirm(
        "Mark verified?\n\nThis records, under your name, that you have checked this summary and "
        + "these values against the original document. It is not a clinical interpretation. "
        + "Every doctor treating this patient will see it."
      );
      if (ok) void send("verify");
    }, "primary");
  }

  if (state.mine === "flagged") {
    makeButton("Clear my report", () => { void send("clear_flag"); });
  } else {
    const reportButton = makeButton("Report inaccurate", () => {
      form.classList.remove("hidden");
      reportButton.classList.add("hidden");
      reasonInput.focus();
    });
    const form = document.createElement("form");
    form.className = "doctor-review-form hidden";
    const reasonId = `doctorReviewReason-${documentId}`;
    const label = document.createElement("label");
    label.setAttribute("for", reasonId);
    label.textContent = "What is inaccurate? Every doctor treating this patient will see this.";
    const reasonInput = document.createElement("textarea");
    reasonInput.id = reasonId;
    reasonInput.rows = 3;
    reasonInput.maxLength = 500;
    reasonInput.required = true;
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "danger compact";
    submit.textContent = "Submit report";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "secondary compact";
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", () => {
      form.classList.add("hidden");
      reportButton.classList.remove("hidden");
    });
    buttons.push(submit, cancel);
    const row = document.createElement("div");
    row.className = "form-actions";
    row.append(submit, cancel);
    form.append(label, reasonInput, row);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const reason = reasonInput.value.trim();
      if (reason.length < 5) {
        message.textContent = "Say what is inaccurate, so other doctors know what to check.";
        reasonInput.focus();
        return;
      }
      void send("flag", reason);
    });
    host.append(actions, form, message);
    return;
  }
  host.append(actions, message);
}

/** Every abnormal result, grouped Critical / High / Low, each saying whose range decided it.
 *
 *  The report's own flag and printed range come first (read by the server from the line
 *  the value is printed on); the standard adult range is used only where the report prints
 *  neither, and says so. The completeness line compares the results the REPORT marks with
 *  the ones listed, so a short list is never presented as complete. */
function renderDocumentAbnormalResults(container, findings, completeness) {
  const isFlagged = (row) => row.abnormal === "low" || row.abnormal === "high" || Boolean(row.report_flag);
  const flagged = findings.filter(isFlagged);

  const groups = [
    { title: "Critical", rows: flagged.filter((row) => row.critical) },
    { title: "High", rows: flagged.filter((row) => !row.critical && row.abnormal === "high") },
    { title: "Low", rows: flagged.filter((row) => !row.critical && row.abnormal === "low") },
    {
      title: "Flagged by the report, direction not printed",
      rows: flagged.filter((row) => !row.critical && row.abnormal !== "high" && row.abnormal !== "low"),
    },
  ];

  if (flagged.length) {
    const heading = document.createElement("h4");
    heading.className = "doctor-abnormal-heading";
    heading.textContent = `Abnormal results (${flagged.length})`;
    container.appendChild(heading);
  }

  groups.filter((group) => group.rows.length).forEach((group) => {
    const label = document.createElement("div");
    label.className = "admin-inline-meta";
    label.textContent = `${group.title} (${group.rows.length})`;
    container.appendChild(label);

    const list = document.createElement("ul");
    list.className = "doctor-abnormal-list";
    group.rows.forEach((row) => {
      const item = document.createElement("li");
      item.className = `doctor-ai-chip ${row.critical || row.abnormal === "high" ? "is-bad" : "is-warn"}`;
      const arrow = row.abnormal === "high" ? "↑ " : row.abnormal === "low" ? "↓ " : "";
      item.appendChild(document.createTextNode(
        `${row.printed_name || row.canonical_name} ${arrow}${row.value_text || row.value_num}`
      ));
      const ref = describeFindingRange(row);
      if (ref) {
        const note = document.createElement("span");
        note.className = "doctor-abnormal-ref";
        note.textContent = ` (${ref})`;
        item.appendChild(note);
      }
      if (row.page_no) {
        const cite = document.createElement("span");
        cite.className = "doctor-cite";
        cite.textContent = ` [p${row.page_no}]`;
        item.appendChild(cite);
      }
      list.appendChild(item);
    });
    container.appendChild(list);
  });

  // "Nothing missed", made checkable: the report marks N results; we list M of them.
  if (completeness && completeness.report_flagged > completeness.listed_from_report) {
    const warn = document.createElement("p");
    warn.className = "doctor-completeness-warn";
    warn.textContent =
      `The report marks ${completeness.report_flagged} results as abnormal; `
      + `${completeness.listed_from_report} could be matched and are listed here. `
      + "Check the original for the rest.";
    container.appendChild(warn);
  }

  // Values with no range at all are counted, not hidden: "not flagged" must not be
  // mistaken for "checked and normal".
  // Only MEASUREMENTS are counted. A prescription's extracted items ("Medication: Tab ...")
  // are text; "4 values read, 4 with no reference range" said nothing true about them.
  const measurements = findings.filter((row) => row.value_num !== null && row.value_num !== undefined);
  if (!measurements.length) return;
  const fromReport = measurements.filter((row) => row.flag_source === "report_flag" || row.flag_source === "report_range").length;
  const fromStandard = measurements.filter((row) => row.flag_source === "standard_range").length;
  const noRange = measurements.filter((row) => !row.flag_source).length;
  const measured = document.createElement("div");
  measured.className = "admin-inline-meta";
  measured.textContent = [
    `${measurements.length} measurements read from this document`,
    fromReport ? `${fromReport} judged by the report's own flag or range` : "",
    fromStandard ? `${fromStandard} by the standard adult range (not printed on the report)` : "",
    noRange ? `${noRange} with no reference range, so not flagged either way` : "",
  ].filter(Boolean).join(" · ");
  container.appendChild(measured);
}

/** "ref 11.6 - 14.0" as the report printed it, or "standard range 30–100" when it is ours. */
function describeFindingRange(row) {
  if (row.ref_source === "report" && row.report_ref_text) return `ref ${row.report_ref_text}`;
  if (row.ref_source !== "standard") return "";
  const low = row.ref_low;
  const high = row.ref_high;
  let text = "";
  if (low !== null && low !== undefined && high !== null && high !== undefined) text = `${low}–${high}`;
  else if (high !== null && high !== undefined) text = `< ${high}`;
  else if (low !== null && low !== undefined) text = `> ${low}`;
  return text ? `standard range ${text}, not printed on this report` : "";
}

// Every value here is model output about a patient's document — rendered as text nodes
// only, never innerHTML, exactly as renderClinicalNote requires for LLM-derived content.
function renderDocumentSummary(container, summary) {
  container.replaceChildren();

  const disclaimer = document.createElement("p");
  disclaimer.className = "clinical-note-flag";
  disclaimer.textContent = "AI generated — not reviewed by a clinician";
  container.appendChild(disclaimer);

  const impression = document.createElement("p");
  impression.className = "clinical-note-line";
  impression.textContent = summary.overall_impression || "No overall impression was extracted.";
  container.appendChild(impression);

  const findings = summary.findings && typeof summary.findings === "object" ? summary.findings : {};
  Object.entries(findings).forEach(([key, value]) => {
    const line = document.createElement("p");
    line.className = "clinical-note-line";
    const label = document.createElement("strong");
    label.textContent = `${key}: `;
    line.appendChild(label);
    line.appendChild(
      document.createTextNode(typeof value === "object" ? JSON.stringify(value) : String(value))
    );
    container.appendChild(line);
  });
}

/** Fetched through doctorAuthedJson's sibling path rather than a plain anchor href: the
 *  endpoint requires an Authorization header, which a link navigation cannot send. The
 *  blob URL is revoked immediately after the click so the document does not linger in
 *  memory or remain reachable from the page. */
async function downloadPatientDocument(patientId, doc, button) {
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "Opening...";
  let objectUrl = null;
  try {
    const response = await fetch(
      `/doctor/patients/${encodeURIComponent(patientId)}/documents/${encodeURIComponent(doc.document_id)}/file`,
      { headers: doctorAuthHeaders() }
    );
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Could not open this document (${response.status}).`);
    }
    const blob = await response.blob();
    objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = doc.original_filename || "document";
    document.body.appendChild(link);
    link.click();
    link.remove();
  } catch (error) {
    setDoctorDocumentsMessage(error.message);
  } finally {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

// ── Clinical actions: prescription / care plan / referral ─────────────────────
// Doctor-authored, never AI-generated. There is no formulary, dose or interaction
// checking behind any of this — it records what the clinician decided, nothing more.

const CLINICAL_ITEM_LABELS = {
  prescription: "Prescription",
  care_plan: "Care plan",
  referral: "Referral",
};

function setClinicalItemMessage(text) {
  if (!doctorClinicalItemMessage) return;
  doctorClinicalItemMessage.textContent = text || "";
  doctorClinicalItemMessage.classList.toggle("hidden", !text);
}

async function loadClinicalItem() {
  if (!doctorActiveConsult) return;
  setClinicalItemMessage("");
  try {
    doctorClinicalItem = await doctorAuthedJson(
      `/doctor/consult/${doctorActiveConsult.id}/clinical-items/${doctorClinicalItemKind}`
    );
    renderClinicalItem();
  } catch (error) {
    doctorClinicalItem = null;
    setClinicalItemMessage(error.message);
  }
}

function renderClinicalItem() {
  const item = doctorClinicalItem;
  const approved = !!item && item.status === "approved";

  if (doctorClinicalItemText) {
    doctorClinicalItemText.value = (item && item.content) || "";
    // Approved records are immutable, mirroring a signed SOAP note.
    doctorClinicalItemText.disabled = approved;
    doctorClinicalItemText.placeholder = approved
      ? ""
      : `Record the ${(CLINICAL_ITEM_LABELS[doctorClinicalItemKind] || "record").toLowerCase()} you decided on during this consultation...`;
  }

  if (doctorClinicalItemStatus) {
    doctorClinicalItemStatus.textContent = approved
      ? `Approved ${item.approved_at ? new Date(item.approved_at).toLocaleString() : ""}`.trim()
      : "Draft";
    doctorClinicalItemStatus.className = `admin-status-pill ${approved ? "is-completed" : ""}`.trim();
    doctorClinicalItemStatus.classList.remove("hidden");
  }

  doctorClinicalItemActions?.classList.toggle("hidden", approved);
  doctorClinicalItemApproveConfirm?.classList.add("hidden");

  updateInsertFromPlanVisibility();

  // The patient's own reported issues, surfaced on the screen where a prescription is
  // written. Unverified free text — nothing cross-checks it.
  const reported = doctorDetailPatientIssues || "";
  if (doctorClinicalItemAllergyAlert) {
    doctorClinicalItemAllergyAlert.classList.toggle("hidden", !reported);
    if (doctorClinicalItemAllergyBody) doctorClinicalItemAllergyBody.textContent = reported;
  }
}

/** "Insert from plan" only makes sense on a prescription, on an editable record, and only
 *  once a note has actually been signed — the endpoint refuses an unsigned draft.
 *
 *  Its own function so the NOTE can call it: this was computed only when the prescription
 *  box rendered, so signing the note (which does not re-render that box) left the button
 *  hidden until the doctor switched tabs, and a note that loaded after the box never showed
 *  it at all. Re-rendering the box instead would have reset its text, discarding whatever
 *  the doctor had typed. */
function updateInsertFromPlanVisibility() {
  const approved = !!doctorClinicalItem && doctorClinicalItem.status === "approved";
  const canInsert = !approved
    && doctorClinicalItemKind === "prescription"
    && !!doctorCurrentNote && doctorCurrentNote.status === "signed";
  doctorInsertFromPlanRow?.classList.toggle("hidden", !canInsert);
}

/** Copies the signed plan's medication lines into the prescription box as an editable
 *  draft. Appends rather than replaces, so it can never destroy something the doctor has
 *  already typed. Parsing happens server-side (one tested implementation); this only
 *  places the text and never alters it. */
async function insertFromSignedPlan() {
  if (!doctorActiveConsult?.id || !doctorClinicalItemText) return;
  try {
    const result = await doctorAuthedJson(
      `/doctor/consult/${doctorActiveConsult.id}/soap/plan-medications`
    );
    const lines = result.lines || [];
    if (!lines.length) {
      setClinicalItemMessage("The signed plan has no medication lines to copy.");
      return;
    }
    const existing = doctorClinicalItemText.value.trim();
    doctorClinicalItemText.value = (existing ? `${existing}\n` : "") + lines.join("\n");
    doctorClinicalItemText.focus();
    setClinicalItemMessage(
      `Copied ${lines.length} line${lines.length === 1 ? "" : "s"} from your signed plan. `
      + "Nothing has been checked or corrected — review before approving."
    );
  } catch (error) {
    setClinicalItemMessage(
      error && error.message ? error.message : "Could not read the signed plan."
    );
  }
}

/** Whether the clinical-item box holds text the server does not have. An approved record
 *  is read-only, so it can never be "unsaved". */
function clinicalItemHasUnsavedText() {
  if (!doctorClinicalItemText || doctorClinicalItemText.disabled) return false;
  return doctorClinicalItemText.value !== ((doctorClinicalItem && doctorClinicalItem.content) || "");
}

function setClinicalItemKind(kind) {
  if (!CLINICAL_ITEM_LABELS[kind] || kind === doctorClinicalItemKind) return;
  // Switching tabs reloads the box from the server for the other kind, which discarded a
  // half-written prescription without a word.
  if (clinicalItemHasUnsavedText()) {
    const label = (CLINICAL_ITEM_LABELS[doctorClinicalItemKind] || "record").toLowerCase();
    if (!window.confirm(`You have unsaved text in the ${label}. Switch without saving it?`)) return;
  }
  doctorClinicalItemKind = kind;
  doctorClinicalItemTabButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.clinicalItem === kind);
  });
  loadClinicalItem();
}

/** Saves the clinical-item text. Returns true only if the server accepted it.
 *  @param quiet - no "Saved." toast; approve uses this so the doctor sees one outcome. */
async function saveClinicalItem({ quiet = false } = {}) {
  if (!doctorActiveConsult) return false;
  setClinicalItemMessage("");
  try {
    doctorClinicalItem = await doctorAuthedJson(
      `/doctor/consult/${doctorActiveConsult.id}/clinical-items/${doctorClinicalItemKind}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: doctorClinicalItemText ? doctorClinicalItemText.value : "" }),
      }
    );
    renderClinicalItem();
    if (!quiet) showAppToast("Saved.");
    return true;
  } catch (error) {
    setClinicalItemMessage(error.message);
    return false;
  }
}

async function approveClinicalItem() {
  if (!doctorActiveConsult) return;
  setClinicalItemMessage("");
  // Save first, so approving never locks in something older than what is on screen — and
  // STOP if the save fails. This used to await a save that swallowed its own error and then
  // approve regardless, which locked in the server's older text under the doctor's name:
  // the exact thing the save-first step exists to prevent. For a prescription, that is a
  // different drug list from the one on screen.
  const saved = await saveClinicalItem({ quiet: true });
  if (!saved) {
    const reason = (doctorClinicalItemMessage?.textContent || "").trim();
    setClinicalItemMessage(
      `Your text could not be saved${reason ? ` (${reason})` : ""}, so nothing was approved.`
    );
    return;
  }
  try {
    doctorClinicalItem = await doctorAuthedJson(
      `/doctor/consult/${doctorActiveConsult.id}/clinical-items/${doctorClinicalItemKind}/approve`,
      { method: "POST" }
    );
    renderClinicalItem();
    showAppToast(`${CLINICAL_ITEM_LABELS[doctorClinicalItemKind]} approved.`);
  } catch (error) {
    setClinicalItemMessage(error.message);
  }
}

function renderDoctorDashboard(doctor) {
  if (!doctor) return;
  if (doctorProfileName) doctorProfileName.textContent = doctor.name || "-";
  if (doctorProfileDepartment) doctorProfileDepartment.textContent = doctor.department || "-";
  if (doctorProfileExperience) {
    doctorProfileExperience.textContent = doctor.experience_years != null ? `${doctor.experience_years} years` : "-";
  }
  if (doctorProfileMfaStatus) doctorProfileMfaStatus.textContent = doctor.mfa_enabled ? "Enabled" : "Not enabled";
  renderDoctorSidebarProfile(doctor);
  if (doctorLowRecoveryNoticePending && doctorRecoveryLowNotice) {
    const text = document.querySelector("#doctorRecoveryLowNoticeText");
    if (text) {
      text.textContent =
        "You signed in with a recovery code. Consider re-enrolling MFA soon if you're running low on codes.";
    }
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

    // Longest marker first, or "#### x" would match the "# " branch and render "### x".
    // Levels are shifted down one (# -> h2, not h1): this renders INSIDE a chat bubble or
    // a notes panel, which already sit under the page's own heading, so emitting <h1>
    // here would produce a second top-level heading on the page. #### is included
    // because the report generator emits it for per-panel subheadings.
    if (line.startsWith("#### ")) {
      flushP(); closeUl(); out.push(`<h5>${_inlineMd(line.slice(5))}</h5>`);
    } else if (line.startsWith("### ")) {
      flushP(); closeUl(); out.push(`<h4>${_inlineMd(line.slice(4))}</h4>`);
    } else if (line.startsWith("## ")) {
      flushP(); closeUl(); out.push(`<h3>${_inlineMd(line.slice(3))}</h3>`);
    } else if (line.startsWith("# ")) {
      flushP(); closeUl(); out.push(`<h2>${_inlineMd(line.slice(2))}</h2>`);
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

// ── Chat stream watchdogs ────────────────────────────────────────────────────
// A total-duration timeout would be wrong here: a long document analysis can legitimately
// stream for minutes, and cutting it off mid-answer is worse than waiting. What is never
// legitimate is SILENCE — so the primary guard trips on "no bytes at all for this long",
// and is reset by every chunk that arrives. The absolute ceiling is a backstop for a
// connection that dribbles keep-alives forever without ever completing.
//
// Without these, /chat/stream had no timeout of any kind (unlike authedJson, which uses
// 15s), so a response that never arrived left the typing indicator spinning forever with
// no error and no way to recover — the user had to reload the page.
const CHAT_STREAM_STALL_MS = 60000;
const CHAT_STREAM_MAX_MS = 300000;

/** reader.read() with a stall deadline. Rejects rather than hanging if the server goes
 *  quiet. The timer is cleared on every settle so it never leaks between chunks. */
function readChunkWithDeadline(reader, startedAt) {
  let timer;
  const stalled = new Promise((_resolve, reject) => {
    timer = window.setTimeout(() => {
      const err = new Error("CHAT_STREAM_STALLED");
      err.code = "stalled";
      reject(err);
    }, CHAT_STREAM_STALL_MS);
  });
  const overall = Date.now() - startedAt > CHAT_STREAM_MAX_MS
    ? Promise.reject(Object.assign(new Error("CHAT_STREAM_TOO_LONG"), { code: "too_long" }))
    : null;
  return Promise.race(overall ? [reader.read(), stalled, overall] : [reader.read(), stalled])
    .finally(() => window.clearTimeout(timer));
}

async function readChatStream(response, assistantMessage, controller = null) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const startedAt = Date.now();
  let buffer = "";
  let finalPayload = null;

  while (true) {
    let value, done;
    try {
      ({ value, done } = await readChunkWithDeadline(reader, startedAt));
    } catch (error) {
      // Abort the underlying request so the connection is released rather than left
      // open behind a dead reader.
      try { controller?.abort(); } catch (abortError) { /* already gone */ }
      if (error?.code === "stalled" || error?.code === "too_long") {
        throw new Error(
          "The assistant stopped responding. Your message was not lost — please try again."
        );
      }
      throw error;
    }
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

/** A refresh-aware fetch that returns the raw Response.
 *
 *  authedJson() already retries a 401 after refreshing, but it consumes the body as JSON,
 *  so the chat endpoints could not use it: /chat/stream is a streamed response the caller
 *  reads incrementally, and /chat/upload sends FormData. They therefore called fetch()
 *  directly and, in doing so, opted out of token refresh entirely — a patient who stayed
 *  inside the chat never renewed their 30-minute access token and every message failed
 *  once it expired, despite holding a refresh token valid for 30 days.
 *
 *  `buildInit` is a FUNCTION, not an object, and is called again for the retry. That is
 *  deliberate twice over: the Authorization header must be rebuilt so it carries the NEW
 *  token, and a FormData body cannot be replayed once sent, so the retry needs a fresh one.
 */
async function patientFetchWithRefresh(url, buildInit) {
  let response = await fetch(url, buildInit());
  if (response.status === 401 && await tryRefreshPatientToken()) {
    response = await fetch(url, buildInit());
  }
  return response;
}

/** Turns a failed Response into a human-readable Error.
 *
 *  The chat used to throw the raw response body, which is why a expired session surfaced
 *  in the transcript as the literal text {"detail":"Invalid or expired authentication
 *  token."}. It also broke the caller's logout check, which tested whether the message
 *  contained "401" — the JSON body never does. The status is carried on the Error object
 *  so callers branch on a number rather than on string matching.
 */
async function chatRequestError(response) {
  let detail = "";
  const raw = await response.text().catch(() => "");
  try {
    detail = (JSON.parse(raw) || {}).detail || "";
  } catch (parseError) {
    detail = raw;
  }
  if (typeof detail !== "string") detail = JSON.stringify(detail);
  const error = new Error(detail || `Request failed with ${response.status}`);
  error.status = response.status;
  return error;
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

// The names a person reads for each document type. The stored value is an identifier from
// the extraction prompt ("mri_report"); it was shown as-is, underscores and all. Every
// place that shows a type goes through here, so a type is named the same way everywhere.
const DOCUMENT_TYPE_LABELS = {
  prescription: "Prescription",
  blood_report: "Blood Report",
  mri_report: "MRI Report",
  ct_report: "CT Report",
  xray_report: "X-ray Report",
  ultrasound_report: "Ultrasound Report",
  ecg_report: "ECG Report",
  pathology_report: "Pathology Report",
  discharge_summary: "Discharge Summary",
  medical_document: "Medical Document",
  other: "Document",
  document: "Document",
};
const DOCUMENT_TYPE_ACRONYMS = new Set(["mri", "ct", "ecg", "ekg", "eeg", "usg", "pet", "cbc", "lft", "kft"]);

function formatDocumentType(type) {
  const key = String(type || "").trim().toLowerCase();
  if (!key) return "Document";
  if (DOCUMENT_TYPE_LABELS[key]) return DOCUMENT_TYPE_LABELS[key];
  // A type the prompt may add later: still readable, never "some_new_type".
  return key.split(/[_\s]+/).filter(Boolean)
    .map((word) => (DOCUMENT_TYPE_ACRONYMS.has(word) ? word.toUpperCase() : word[0].toUpperCase() + word.slice(1)))
    .join(" ");
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

    const summary = buildVisitSummaryBlock(booking.visit_summary);
    if (summary) item.appendChild(summary);

    container.appendChild(item);
  });
}

/** The doctor-verified visit summary, shown only when a clinician signed the note AND
 *  explicitly shared it (the API omits it otherwise). Deliberately presented as finalised
 *  clinical information, with the verifying doctor and date — never as "AI generated",
 *  because by this point a clinician has taken responsibility for it. The citations and
 *  confidence flags the doctor sees are not in this payload at all. */
function buildVisitSummaryBlock(visitSummary) {
  if (!visitSummary) return null;

  const wrap = document.createElement("div");
  wrap.className = "visit-summary";

  const heading = document.createElement("h4");
  heading.className = "clinical-note-heading";
  heading.textContent = "Visit summary";
  wrap.appendChild(heading);

  const provenance = document.createElement("p");
  provenance.className = "panel-note";
  const doctorName = visitSummary.doctor_name || "your doctor";
  const when = visitSummary.signed_at ? new Date(visitSummary.signed_at).toLocaleDateString() : null;
  provenance.textContent = when
    ? `Reviewed and finalised by ${doctorName} on ${when}.`
    : `Reviewed and finalised by ${doctorName}.`;
  wrap.appendChild(provenance);

  [
    ["What you described", visitSummary.subjective],
    ["What was observed", visitSummary.objective],
    ["Assessment", visitSummary.assessment],
    ["Plan", visitSummary.plan],
  ].forEach(([label, value]) => {
    if (!value) return;
    const block = document.createElement("div");
    block.className = "clinical-note-field";
    const title = document.createElement("div");
    title.className = "admin-inline-title";
    title.textContent = label;
    const body = document.createElement("p");
    body.className = "clinical-note-value";
    body.textContent = value;
    block.append(title, body);
    wrap.appendChild(block);
  });

  return wrap;
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
      "Pre-Appointment AI Clinical Summary"
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

/* A SECOND renderMarkdown() used to be declared here.
 *
 * Both were top-level function declarations in the same script, so this one silently
 * overwrote the capable renderer defined earlier in this file — including for the chat,
 * which never knew it was calling the wrong one. This version had no table support, so a
 * generated report's pipe tables and #### subheadings reached the patient as raw markdown
 * (verified in a browser: the active renderer returned "#### Haematology<br>|---|---|<br>"
 * with no <table> element at all).
 *
 * The renderer above is a superset of what this one did, and now carries this one's
 * heading levels too, so every caller keeps the output it had and gains tables.
 */

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

  // One controller for the whole turn, including the post-refresh retry. readChatStream
  // aborts it if the stream stalls, so a dead request releases its connection instead of
  // being abandoned open.
  const controller = new AbortController();

  try {
    // buildChatRequest() is re-run per attempt so the retry carries the refreshed token.
    const response = await patientFetchWithRefresh("/chat/stream", () => {
      const requestPayload = buildChatRequest(message, state);
      return {
        method: "POST",
        headers: requestPayload.headers,
        body: requestPayload.body,
        signal: controller.signal,
      };
    });

    if (!response.ok) {
      throw await chatRequestError(response);
    }

    const data = await readChatStream(response, assistantMessage, controller);
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
    // Branch on the status, not on whether the message text happens to contain "401".
    // It never did — the thrown message was the response body — so an expired session
    // used to leave the patient in a UI that still looked signed in while every message
    // failed. Reaching here with a 401 means the refresh was already tried and failed,
    // so the session is genuinely over.
    if (error?.status === 401) {
      clearAuthenticated();
      showAuthMode("login");
      setStatus("Session expired");
      return;
    }
    // An AbortError here is our own watchdog firing (readChatStream aborts the request
    // before throwing), so report the human-readable cause rather than "AbortError".
    const text = error?.name === "AbortError"
      ? "The assistant stopped responding. Your message was not lost — please try again."
      : `Request failed: ${error.message}`;
    if (assistantMessage?.node?.parentNode) {
      await streamAssistantText(assistantMessage, text);
    } else {
      addAssistantMessage(text);
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
    // Trimmed: a recovery code pasted from the downloaded file often carries a space or
    // newline. The server accepts an authenticator code or a recovery code in this one
    // field (it tries the first, then the second), so no mode needs to be sent.
    const data = await postJson("/doctor/auth/mfa/challenge", { code: doctorMfaCode.value.trim() }, doctorMfaToken);
    if (data.recovery_code_used) doctorLowRecoveryNoticePending = true;
    setDoctorAuthenticated(data.access_token);
  } catch (error) {
    // The password was already accepted to reach this step; saying "Invalid email or
    // password" for a wrong CODE sent doctors back to re-type a correct password — and hid
    // the server's own message, including "Too many attempts".
    setAuthMessage(error && error.message ? error.message : "That code was not accepted. Try again.");
  }
});

if (doctorMfaBackBtn) doctorMfaBackBtn.addEventListener("click", () => {
  // The patient MFA step always had a way back; the doctor one did not.
  doctorMfaToken = null;
  if (doctorMfaCode) doctorMfaCode.value = "";
  setAuthMessage("");
  showAuthMode("login");
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

document.querySelector("#doctorRecoveryLowNoticeDismiss")?.addEventListener("click", () => {
  doctorRecoveryLowNotice?.classList.add("hidden");
});

if (doctorLogoutBtn) doctorLogoutBtn.addEventListener("click", () => {
  if (!confirmLeavingConsultWork()) return;
  clearDoctorAuthenticated();
  showAuthMode("login");
});

doctorViewButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (!confirmLeavingConsultWork()) return;
    showDoctorView(button.dataset.doctorView);
  });
});

// ── AI workspace wiring (docs/ai-redesign/) ───────────────────────────────────

if (doctorStartReviewBtn) doctorStartReviewBtn.addEventListener("click", () => {
  const first = doctorPendingQueue[0];
  if (first) void openReviewFromQueue(first);
});

if (doctorInsertFromPlanBtn) doctorInsertFromPlanBtn.addEventListener("click", insertFromSignedPlan);

if (doctorDraftAllBtn) doctorDraftAllBtn.addEventListener("click", () => {
  draftAllMissingNotes();
});

/* Ask AI (plan §4.8) is behind a default-OFF flag. Answering questions across a doctor's
   patients safely needs authorization-filtered retrieval, per-doctor cost caps and source
   attribution on every claim — none of which exists yet. The command bar stays hidden and
   the shortcut stays unbound until there is a backend that can answer safely, because a
   visible input that silently does nothing is worse than no input at all. */
const DOCTOR_ASK_AI_ENABLED = false;

if (DOCTOR_ASK_AI_ENABLED) {
  doctorAskAiBar?.classList.remove("hidden");
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      if (doctorDashboardView?.classList.contains("hidden")) return;
      event.preventDefault();
      doctorAskAiInput?.focus();
    }
  });
}

if (doctorPatientDetailBackBtn) doctorPatientDetailBackBtn.addEventListener("click", () => {
  showDoctorView(doctorPatientDetailReturnView || "patients");
});

if (doctorPatientSearchInput) doctorPatientSearchInput.addEventListener("input", () => {
  doctorPatientSearchTerm = doctorPatientSearchInput.value;
  renderDoctorPatientsList();
});

// ── Review queue wiring ───────────────────────────────────────────────────────

doctorReviewScopeButtons.forEach((button) => {
  button.addEventListener("click", () => setDoctorReviewScope(button.dataset.reviewScope));
});

if (doctorReviewSearchInput) doctorReviewSearchInput.addEventListener("input", () => {
  // Filtered over the cached page rather than refetched — the queue is already bounded
  // at 100 rows, so a round trip per keystroke would buy nothing.
  doctorReviewSearchTerm = doctorReviewSearchInput.value;
  renderDoctorReviews();
});

if (doctorOverviewReviewsBtn) doctorOverviewReviewsBtn.addEventListener("click", () => openDoctorReviews());
if (doctorStatReviewsCard) doctorStatReviewsCard.addEventListener("click", () => openDoctorReviews());
// This card counts blocked notes and weak transcripts — the Needs attention lane — so it
// opens there, not at the top of the queue.
if (doctorStatAttentionCard) doctorStatAttentionCard.addEventListener("click", () => openDoctorReviews({ lane: "needs_attention" }));

if (doctorNoteShareBtn) doctorNoteShareBtn.addEventListener("click", () => {
  doctorNoteShareConfirm?.classList.remove("hidden");
});
if (doctorNoteShareCancelBtn) doctorNoteShareCancelBtn.addEventListener("click", () => {
  doctorNoteShareConfirm?.classList.add("hidden");
});
if (doctorNoteShareConfirmBtn) doctorNoteShareConfirmBtn.addEventListener("click", () => {
  doctorNoteShareConfirm?.classList.add("hidden");
  confirmShareSoapNote();
});

// ── Patient workspace tabs ────────────────────────────────────────────────────

doctorPatientTabButtons.forEach((button) => {
  button.addEventListener("click", () => setDoctorPatientTab(button.dataset.patientTab));
});

// ── SOAP detail level ─────────────────────────────────────────────────────────

doctorNoteStyleButtons.forEach((button) => {
  button.addEventListener("click", () => setDoctorNoteStyle(button.dataset.noteStyle));
});

doctorActivityWindowButtons.forEach((button) => {
  button.addEventListener("click", () => setDoctorActivityWindow(button.dataset.activityWindow));
});

doctorActivityDrillClose?.addEventListener("click", () => closeDoctorActivityDrill({ restoreFocus: true }));
doctorActivityLogToggle?.addEventListener("click", toggleDoctorActivityLog);
// Escape anywhere inside the open list closes it and hands focus back to its tile, the
// usual contract for a disclosure the keyboard user opened.
doctorActivityDrill?.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    event.stopPropagation();
    closeDoctorActivityDrill({ restoreFocus: true });
  }
});

// ── Clinical actions ──────────────────────────────────────────────────────────

doctorClinicalItemTabButtons.forEach((button) => {
  button.addEventListener("click", () => setClinicalItemKind(button.dataset.clinicalItem));
});

// Wrapped rather than passed directly: saveClinicalItem takes an options object, and a
// bare listener would hand it the click event in that position.
if (doctorClinicalItemSaveBtn) doctorClinicalItemSaveBtn.addEventListener("click", () => { void saveClinicalItem(); });

if (doctorClinicalItemApproveBtn) doctorClinicalItemApproveBtn.addEventListener("click", () => {
  doctorClinicalItemApproveConfirm?.classList.remove("hidden");
});
if (doctorClinicalItemApproveCancelBtn) doctorClinicalItemApproveCancelBtn.addEventListener("click", () => {
  doctorClinicalItemApproveConfirm?.classList.add("hidden");
});
if (doctorClinicalItemApproveConfirmBtn) doctorClinicalItemApproveConfirmBtn.addEventListener("click", () => {
  doctorClinicalItemApproveConfirm?.classList.add("hidden");
  approveClinicalItem();
});

if (doctorAppointmentDetailBackBtn) doctorAppointmentDetailBackBtn.addEventListener("click", () => {
  if (!confirmLeavingConsultWork()) return;
  stopConsultRecording();
  stopConsultStatusPolling();
  if (doctorDetailReturnView === "patientDetail" && doctorPatientDetailId) {
    // Opened from a visit on a patient's page: back to that page, which is still rendered
    // behind this one. Re-showing it, not reloading it, so going back does not re-fetch
    // the patient or write another view of their record to the audit log.
    showDoctorPane("patientDetail");
    return;
  }
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
  // D4 (docs/ai-redesign/plan.md): unresolved flags WARN, they do not block. The model's
  // self-assessment does not get to veto a clinician who has read the transcript — but
  // they must be told exactly what is still flagged before they commit. A blocked
  // ('stale') note is a different matter and is refused by the API regardless.
  if (doctorNoteSignWarning) {
    const note = doctorCurrentNote || {};
    const unresolved = SOAP_FIELDS.filter(
      (field) => note.confidence_flags && note.confidence_flags[field]
        && !doctorNoteVerifiedSections.includes(field)
    );
    const unverified = SOAP_FIELDS.filter((f) => !doctorNoteVerifiedSections.includes(f)).length;
    const parts = [];
    if (unresolved.length) {
      parts.push(
        `${unresolved.length} flagged section${unresolved.length === 1 ? "" : "s"} still unverified: `
        + unresolved.map((f) => SOAP_FIELD_LABELS[f]).join(", ") + "."
      );
    } else if (unverified) {
      parts.push(`${unverified} section${unverified === 1 ? "" : "s"} not yet marked verified.`);
    }
    // Said before they commit: signing will save first, so what they see is what is signed.
    if (doctorNoteDirty) parts.push("Your unsaved changes will be saved and then signed.");
    doctorNoteSignWarning.textContent = parts.join(" ");
    doctorNoteSignWarning.classList.toggle("hidden", !parts.length);
  }
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
      // Step 1: POST /chat/upload — OpenAI vision medical relevance check + staging.
      // The FormData is built inside the callback so a retry after a token refresh gets a
      // fresh body; a FormData that has already been sent cannot be replayed.
      const uploadResp = await patientFetchWithRefresh("/chat/upload", () => {
        const uploadForm = new FormData();
        uploadForm.append("file", file);
        uploadForm.append("session_id", currentSessionId() || "");
        return {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
          body: uploadForm,
        };
      });

      if (!uploadResp.ok) {
        throw await chatRequestError(uploadResp);
      }

      const { document_token } = await uploadResp.json();

      // Step 2: Consent dialog
      const consent = confirm(
        `"${file.name}" has been verified as a valid medical document.\n\n` +
        `Store securely in your health vault for AI-assisted analysis?\n\n` +
        `OK = store & analyze  |  Cancel = discard`
      );

      // Step 3: Confirm/discard — fire and forget, but still refresh-aware: this call
      // carries the patient's CONSENT decision, and silently losing it to an expired
      // token would leave the document staged with no recorded choice either way.
      patientFetchWithRefresh("/chat/confirm-processing", () => ({
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ document_token, consent_granted: consent }),
      })).catch(err => console.warn("confirm-processing error:", err));

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
      // Same entry point as a fresh login — see enterDoctorWorkspace. This path used to
      // load appointments only, which is what made a hard refresh lose the AI panels and
      // the review queue.
      const data = await doctorAuthedJson("/doctor/me");
      enterDoctorWorkspace(data.doctor);
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







// ── Document viewer controls ─────────────────────────────────────────────────

document.querySelector("#doctorViewerClose")?.addEventListener("click", closeDoctorViewer);
document.querySelector("#doctorViewerPrev")?.addEventListener("click", () => stepViewerPage(-1));
document.querySelector("#doctorViewerNext")?.addEventListener("click", () => stepViewerPage(1));
document.querySelector("#doctorViewerZoomIn")?.addEventListener("click", () => zoomViewer(VIEWER_ZOOM_STEP));
document.querySelector("#doctorViewerZoomOut")?.addEventListener("click", () => zoomViewer(1 / VIEWER_ZOOM_STEP));
document.querySelector("#doctorViewerRotate")?.addEventListener("click", () => {
  viewerState.rotation = (viewerState.rotation + 90) % 360;
  void renderViewerPage();
});
document.querySelector("#doctorViewerReset")?.addEventListener("click", () => {
  // One control that undoes every adjustment at once. On an X-ray the doctor may have
  // changed four things; making them reverse each individually invites leaving one on.
  viewerState.rotation = 0;
  viewerState.zoom = 1;
  if (doctorViewerBrightness) doctorViewerBrightness.value = "100";
  if (doctorViewerContrast) doctorViewerContrast.value = "100";
  void renderViewerPage();
});
doctorViewerBrightness?.addEventListener("input", applyViewerFilter);
doctorViewerContrast?.addEventListener("input", applyViewerFilter);
document.querySelector("#doctorViewerDownload")?.addEventListener("click", (event) => {
  if (viewerState.patientId && viewerState.doc) {
    downloadPatientDocument(viewerState.patientId, viewerState.doc, event.currentTarget);
  }
});

// Escape closes, and the arrow keys page a PDF — but only while the overlay is open, and
// never while the doctor is typing into a field somewhere behind it.
document.addEventListener("keydown", (event) => {
  if (!doctorViewer || doctorViewer.classList.contains("hidden")) return;
  const tag = (event.target && event.target.tagName) || "";
  if (tag === "INPUT" || tag === "TEXTAREA") return;
  if (event.key === "Escape") { closeDoctorViewer(); return; }
  if (event.key === "ArrowLeft") { stepViewerPage(-1); event.preventDefault(); }
  if (event.key === "ArrowRight") { stepViewerPage(1); event.preventDefault(); }
});

// ── Timeline controls ────────────────────────────────────────────────────────

["#doctorTimelineDepartment", "#doctorTimelineDoctor", "#doctorTimelineDocType",
 "#doctorTimelineFrom", "#doctorTimelineTo"].forEach((selector) => {
  // Every filter change restarts from the newest encounter: appending a filtered page
  // onto an unfiltered one would show a list that matches no single set of criteria.
  document.querySelector(selector)?.addEventListener("change", () => {
    narrowTimelineFilters();
    void loadDoctorTimeline();
  });
});

document.querySelector("#doctorTimelineClear")?.addEventListener("click", () => {
  ["#doctorTimelineDepartment", "#doctorTimelineDoctor", "#doctorTimelineDocType",
   "#doctorTimelineFrom", "#doctorTimelineTo"].forEach((selector) => {
    const field = document.querySelector(selector);
    if (field) field.value = "";
  });
  narrowTimelineFilters();
  void loadDoctorTimeline();
});

doctorTimelineMore?.addEventListener("click", () => void loadDoctorTimeline({ append: true }));
