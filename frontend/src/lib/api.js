import axios from "axios";

const getBaseURL = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  if (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
    // In production (Vercel), use relative path — both frontend & backend on same domain
    return "/api";
  }
  return "http://localhost:8000/api";
};

const api = axios.create({ 
  baseURL: getBaseURL() 
});


api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ci_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function formatApiError(error) {
  if (!error) return { message: "An unexpected error occurred.", details: [] };
  if (error.response && error.response.data) {
    const data = error.response.data;
    if (data.error) {
      return {
        message: data.error.message || "An error occurred",
        code: data.error.code || "ERROR",
        statusCode: data.error.status_code || error.response.status,
        details: Array.isArray(data.error.details) ? data.error.details : [],
        requestId: data.error.request_id || "",
      };
    }
    if (data.detail) {
      const msg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      return { message: msg, statusCode: error.response.status, details: [] };
    }
  }
  return { message: error.message || "Network error. Please check your connection.", details: [] };
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    error.formattedError = formatApiError(error);
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("ci_token");
      localStorage.removeItem("ci_user");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);


export async function login(email, password) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const { data } = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  localStorage.setItem("ci_token", data.access_token);
  localStorage.setItem("ci_user", JSON.stringify(data.user));
  return data.user;
}

export function logout() {
  localStorage.removeItem("ci_token");
  localStorage.removeItem("ci_user");
}

export function getCurrentUser() {
  const raw = localStorage.getItem("ci_user");
  return raw ? JSON.parse(raw) : null;
}

export function getToken() {
  return localStorage.getItem("ci_token");
}


export async function fetchDashboardStats() {
  const { data } = await api.get("/dashboard/stats");
  return data;
}

export async function fetchCases(params = {}) {
  const { data } = await api.get("/cases", { params });
  return data;
}

export async function fetchCaseInvestigation(caseId) {
  const { data } = await api.get(`/cases/${caseId}/investigation`);
  return data;
}

export async function updateCaseInvestigation(caseId, payload) {
  const { data } = await api.put(`/cases/${caseId}/investigation`, payload);
  return data;
}

export async function fetchSimilarCases(caseId) {
  const { data } = await api.get(`/cases/${caseId}/similar`);
  return data;
}

export async function exportCaseReport(caseId, format = "pdf") {
  const response = await api.get(`/export/cases/${caseId}/report`, {
    params: { format },
    responseType: "blob",
  });
  return response;
}

// ── Career Plans & Learning Search ──────────────────────────────────────────

export async function fetchCareerPlans(params = {}) {
  const { data } = await api.get("/career-plans", { params });
  return data;
}

export async function fetchCareerPlan(planId) {
  const { data } = await api.get(`/career-plans/${planId}`);
  return data;
}

export async function createCareerPlan(payload) {
  const { data } = await api.post("/career-plans", payload);
  return data;
}

export async function updateCareerPlan(planId, payload) {
  const { data } = await api.put(`/career-plans/${planId}`, payload);
  return data;
}

export async function deleteCareerPlan(planId) {
  const { data } = await api.delete(`/career-plans/${planId}`);
  return data;
}

export async function fetchNetworkGraph(params = {}) {
  const { data } = await api.get("/network/graph", { params });
  return data;
}

export async function fetchPredictions() {
  const { data } = await api.get("/dashboard/predictions");
  return data;
}

export async function createChatSession() {
  const { data } = await api.post("/chat/sessions");
  return data;
}

export async function listChatSessions() {
  const { data } = await api.get("/chat/sessions");
  return data;
}

export async function getChatMessages(sessionId) {
  const { data } = await api.get(`/chat/sessions/${sessionId}/messages`);
  return data;
}

export async function sendChatMessage(sessionId, content, language = "en") {
  const { data } = await api.post(`/chat/sessions/${sessionId}/messages`, { content, language });
  return data;
}

export async function confirmAgentAction(actionId) {
  const { data } = await api.post(`/chat/assistant/actions/${actionId}/confirm`);
  return data;
}

export async function cancelAgentAction(actionId) {
  const { data } = await api.post(`/chat/assistant/actions/${actionId}/cancel`);
  return data;
}



export async function downloadChatTranscript(sessionId, filenameHint) {
  const response = await api.get(`/export/chat/${sessionId}/report`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `${filenameHint || sessionId}_transcript.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function fetchAuditLogs(params = {}) {
  const { data } = await api.get("/audit/logs", { params });
  return data;
}

export async function listUsers() {
  const { data } = await api.get("/admin/users");
  return data;
}

export async function createUser(payload) {
  const { data } = await api.post("/admin/users", payload);
  return data;
}

export async function updateUser(userId, payload) {
  const { data } = await api.patch(`/admin/users/${userId}`, payload);
  return data;
}

export async function deactivateUser(userId) {
  await api.delete(`/admin/users/${userId}`);
}

export async function importCasesCSV(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/import/cases/csv", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function fetchOffenders(params = {}) {
  const { data } = await api.get("/offenders", { params });
  return data;
}

export async function fetchOffenderProfile(personId) {
  const { data } = await api.get(`/offenders/${personId}`);
  return data;
}

export async function fetchDemographicInsights() {
  const { data } = await api.get("/analytics/demographics");
  return data;
}

export async function fetchSocioeconomicCorrelation() {
  const { data } = await api.get("/analytics/socioeconomic-correlation");
  return data;
}

export async function fetchFinancialTrail(caseId) {
  const { data } = await api.get(`/finance/trail/${caseId}`);
  return data;
}

export async function fetchFinancialTransactions(params = {}) {
  const { data } = await api.get("/finance/transactions", { params });
  return data;
}

export async function fetchFIRDetails(caseId) {
  const { data } = await api.get(`/cases/${caseId}/fir-details`);
  return data;
}

export async function saveFIRDetails(caseId, payload) {
  const { data } = await api.post(`/cases/${caseId}/fir-details`, payload);
  return data;
}

export async function fetchComplainantDetails(caseId) {
  const { data } = await api.get(`/cases/${caseId}/complainant`);
  return data;
}

export async function saveComplainantDetails(caseId, payload) {
  const { data } = await api.post(`/cases/${caseId}/complainant`, payload);
  return data;
}

export async function fetchArrestSurrenderEvents(caseId) {
  const { data } = await api.get(`/cases/${caseId}/arrest-surrender`);
  return data;
}

export async function fetchActSections(caseId) {
  const { data } = await api.get(`/cases/${caseId}/act-sections`);
  return data;
}

export async function fetchChargesheetDetails(caseId) {
  const { data } = await api.get(`/cases/${caseId}/chargesheet`);
  return data;
}

export async function fetchMasterLookup(type, params = {}) {
  const { data } = await api.get(`/masters/${type}`, { params });
  return data;
}

export async function fetchCaseTimeline(caseId) {
  const { data } = await api.get(`/cases/${caseId}/timeline`);
  return data;
}

export async function fetchNetworkGroups() {
  const { data } = await api.get("/network/groups");
  return data;
}

export async function fetchSeasonalTrends() {
  const { data } = await api.get("/analytics/seasonal-trends");
  return data;
}

// ── Sprint 6: Collaboration & My Work APIs ───────────────────────────────────

export async function fetchCaseComments(caseId) {
  const { data } = await api.get(`/cases/${caseId}/comments`);
  return data;
}

export async function createCaseComment(caseId, payload) {
  const { data } = await api.post(`/cases/${caseId}/comments`, payload);
  return data;
}

export async function deleteCaseComment(caseId, commentId) {
  const { data } = await api.delete(`/cases/${caseId}/comments/${commentId}`);
  return data;
}

export async function fetchCaseAssignments(caseId) {
  const { data } = await api.get(`/cases/${caseId}/assignments`);
  return data;
}

export async function createCaseAssignment(caseId, payload) {
  const { data } = await api.post(`/cases/${caseId}/assignments`, payload);
  return data;
}

export async function removeCaseAssignment(caseId, assignmentId) {
  const { data } = await api.delete(`/cases/${caseId}/assignments/${assignmentId}`);
  return data;
}

export async function fetchCaseTasks(caseId) {
  const { data } = await api.get(`/cases/${caseId}/tasks`);
  return data;
}

export async function createCaseTask(caseId, payload) {
  const { data } = await api.post(`/cases/${caseId}/tasks`, payload);
  return data;
}

export async function updateCaseTask(caseId, taskId, payload) {
  const { data } = await api.patch(`/cases/${caseId}/tasks/${taskId}`, payload);
  return data;
}

export async function deleteCaseTask(caseId, taskId) {
  const { data } = await api.delete(`/cases/${caseId}/tasks/${taskId}`);
  return data;
}

export async function fetchMyTasks() {
  const { data } = await api.get("/me/tasks");
  return data;
}

export async function fetchMyAssignedCases() {
  const { data } = await api.get("/me/assigned-cases");
  return data;
}

export async function fetchOfficers() {
  const { data } = await api.get("/users/officers");
  return data;
}

export async function downloadImportTemplate() {
  const response = await api.get("/import/cases/csv/template", {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", "crime_cases_template.csv");
  document.body.appendChild(link);
  link.click();
  link.remove();
}

// ── Citizen Crime Reporting APIs ──────────────────────────────────────────

export async function submitCitizenReport(payload) {
  const { data } = await api.post("/citizen-reports", payload);
  return data;
}

export async function trackCitizenReport(trackingId) {
  const { data } = await api.get(`/citizen-reports/track/${encodeURIComponent(trackingId)}`);
  return data;
}

export async function fetchCitizenReports(status = "") {
  const params = status ? { status } : {};
  const { data } = await api.get("/citizen-reports", { params });
  return data;
}

export async function fetchCitizenReportById(reportId) {
  const { data } = await api.get(`/citizen-reports/${reportId}`);
  return data;
}

export async function verifyCitizenReport(reportId, action, rejectionReason = "") {
  const { data } = await api.post(`/citizen-reports/${reportId}/verify`, {
    action,
    rejection_reason: rejectionReason,
  });
  return data;
}

export async function analyzeReportAI(reportId) {
  const { data } = await api.post(`/citizen-reports/${reportId}/analyze-ai`);
  return data;
}

// ── Activity History APIs ──────────────────────────────────────────────────

export async function fetchActivityHistory(params = {}) {
  const { data } = await api.get("/activity-history", { params });
  return data;
}

export async function fetchActivityDetail(activityId) {
  const { data } = await api.get(`/activity-history/${activityId}`);
  return data;
}

export async function fetchActivityStats() {
  const { data } = await api.get("/activity-history/stats/summary");
  return data;
}

export async function deleteActivityRecord(activityId) {
  const { data } = await api.delete(`/activity-history/${activityId}`);
  return data;
}

// ── Background Jobs APIs ────────────────────────────────────────────────────

export async function submitBackgroundJob(payload) {
  const { data } = await api.post("/jobs", payload);
  return data;
}

export async function fetchJobs(params = {}) {
  const { data } = await api.get("/jobs", { params });
  return data;
}

export async function fetchJobDetail(jobId) {
  const { data } = await api.get(`/jobs/${jobId}`);
  return data;
}

export async function fetchJobLogs(jobId) {
  const { data } = await api.get(`/jobs/${jobId}/logs`);
  return data;
}

export async function retryJob(jobId) {
  const { data } = await api.post(`/jobs/${jobId}/retry`);
  return data;
}

export async function cancelJob(jobId) {
  const { data } = await api.post(`/jobs/${jobId}/cancel`);
  return data;
}

export async function fetchJobStats() {
  const { data } = await api.get("/jobs/stats/summary");
  return data;
}

// ── Observability & Agent Runs APIs ─────────────────────────────────────────

export async function fetchAgentRuns(params = {}) {
  const { data } = await api.get("/observability/runs", { params });
  return data;
}

export async function fetchAgentRunDetail(runId) {
  const { data } = await api.get(`/observability/runs/${runId}`);
  return data;
}

export async function fetchAgentRunTree(runId) {
  const { data } = await api.get(`/observability/runs/${runId}/tree`);
  return data;
}

export async function fetchObservabilityStats() {
  const { data } = await api.get("/observability/stats/summary");
  return data;
}

export async function fetchToolStats() {
  const { data } = await api.get("/observability/tools");
  return data;
}

// ── Multi-Step Workflows & Approval Gates APIs ──────────────────────────────

export async function createWorkflow(payload) {
  const { data } = await api.post("/workflows", payload);
  return data;
}

export async function fetchWorkflows(params = {}) {
  const { data } = await api.get("/workflows", { params });
  return data;
}

export async function fetchWorkflowDetail(workflowId) {
  const { data } = await api.get(`/workflows/${workflowId}`);
  return data;
}

export async function executeWorkflow(workflowId) {
  const { data } = await api.post(`/workflows/${workflowId}/execute`);
  return data;
}

export async function cancelWorkflow(workflowId) {
  const { data } = await api.post(`/workflows/${workflowId}/cancel`);
  return data;
}

export async function fetchPendingApprovals() {
  const { data } = await api.get("/workflows/approvals/pending");
  return data;
}

export async function submitApprovalDecision(approvalId, payload) {
  const { data } = await api.post(`/workflows/approvals/${approvalId}/decision`, payload);
  return data;
}

export async function fetchWorkflowStats() {
  const { data } = await api.get("/workflows/stats/summary");
  return data;
}

export default api;


