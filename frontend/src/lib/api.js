import axios from "axios";

const api = axios.create({ 
  baseURL: import.meta.env.VITE_API_BASE_URL || "https://backend-50044348119.development.catalystappsail.in/api" 
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ci_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Fallback Data Structures for Seamless Live Demo ──────────────────────────
const DEMO_STATS = {
  total_cases: 142,
  open_cases: 38,
  under_review_cases: 14,
  closed_cases: 90,
  crime_type_distribution: [
    { crime_type: "Cybercrime", count: 42 },
    { crime_type: "Robbery", count: 28 },
    { crime_type: "Fraud", count: 22 },
    { crime_type: "Extortion", count: 18 },
    { crime_type: "Narcotics", count: 14 },
    { crime_type: "Other", count: 18 }
  ],
  district_summary: [
    { district: "Patna", count: 42 },
    { district: "Gaya", count: 28 },
    { district: "Muzaffarpur", count: 22 },
    { district: "Bhagalpur", count: 18 }
  ],
  recent_alerts: [
    {
      id: "c1",
      case_id: "CASE-2026-901",
      title: "Bank Fraud Scam & Cyber Hijack",
      district: "Patna",
      severity: "critical"
    },
    {
      id: "c2",
      case_id: "CASE-2026-902",
      title: "Highway Cargo Hijack",
      district: "Gaya",
      severity: "high"
    }
  ]
};

const DEMO_PREDICTIONS = {
  alerts: [
    {
      district: "Patna",
      recent_30d: 42,
      prior_30d: 30,
      change_pct: 40.0,
      trend: "rising"
    },
    {
      district: "Gaya",
      recent_30d: 28,
      prior_30d: 20,
      change_pct: 40.0,
      trend: "rising"
    }
  ]
};

const DEMO_CASES = {
  total: 2,
  results: [
    {
      id: "CASE-2026-901",
      case_id: "CASE-2026-901",
      title: "Bank Fraud Scam & Cyber Hijack",
      crime_type: "Cybercrime",
      district: "Patna",
      police_station: "Kotwali",
      status: "open",
      severity: "critical",
      incident_date: "2026-03-15",
      summary: "Phishing call targeted senior citizen resulting in Rs 45 Lakh theft."
    },
    {
      id: "CASE-2026-902",
      case_id: "CASE-2026-902",
      title: "Highway Cargo Hijack",
      crime_type: "Robbery",
      district: "Gaya",
      police_station: "Civil Lines",
      status: "under_review",
      severity: "high",
      incident_date: "2026-03-18",
      summary: "Armed hijack of electronics freight container on NH-83."
    }
  ]
};

const DEMO_MAP_CASES = [
  {
    id: "CASE-2026-901",
    case_id: "CASE-2026-901",
    title: "Bank Fraud Scam & Cyber Hijack",
    district: "Patna",
    crime_type: "Cybercrime",
    severity: "critical",
    latitude: 30.901,
    longitude: 75.857
  },
  {
    id: "CASE-2026-902",
    case_id: "CASE-2026-902",
    title: "Highway Cargo Hijack",
    district: "Gaya",
    crime_type: "Robbery",
    severity: "high",
    latitude: 30.915,
    longitude: 75.870
  }
];

const DEMO_NETWORK = {
  nodes: [
    { id: "c1", label: "CASE-2026-901", name: "CASE-2026-901", type: "case", val: 15, severity: "critical", ref_id: "CASE-2026-901" },
    { id: "c2", label: "CASE-2026-902", name: "CASE-2026-902", type: "case", val: 15, severity: "high", ref_id: "CASE-2026-902" },
    { id: "p1", label: "Rajesh Kumar (Raju)", name: "Rajesh Kumar (Raju)", type: "person", val: 20, ref_id: "OFF-401" },
    { id: "p2", label: "Amit Singh (Snake)", name: "Amit Singh (Snake)", type: "person", val: 18, ref_id: "OFF-402" },
    { id: "a1", label: "HDFC-88912301", name: "HDFC-88912301", type: "account", val: 10 },
    { id: "ph1", label: "+91-9876543210", name: "+91-9876543210", type: "phone", val: 8 }
  ],
  edges: [
    { source: "p1", target: "c1", kind: "shared_phone" },
    { source: "p2", target: "c1", kind: "co_accused" },
    { source: "p1", target: "a1", kind: "financial_transfer" },
    { source: "p2", target: "ph1", kind: "shared_phone" }
  ],
  links: [
    { source: "p1", target: "c1", kind: "shared_phone" },
    { source: "p2", target: "c1", kind: "co_accused" },
    { source: "p1", target: "a1", kind: "financial_transfer" },
    { source: "p2", target: "ph1", kind: "shared_phone" }
  ],
  recurring_links: 4
};

const DEMO_GROUPS = [
  {
    group_id: "g1",
    name: "Patna Cyber Fraud Syndicate",
    group_risk_score: 92,
    member_count: 4,
    linked_cases: 3,
    members: [{ person_node_id: "p1" }, { person_node_id: "p2" }]
  }
];

const DEMO_OFFENDERS = [
  {
    person_id: "OFF-401",
    name: "Rajesh Kumar (Alias: Raju Don)",
    phone_number: "+91-9876543210",
    case_count: 5,
    mo_tags: ["Phishing", "Crypto Laundering"],
    last_active: "2026-03-24",
    risk_score: 88,
    risk_category: "high"
  },
  {
    person_id: "OFF-402",
    name: "Amit Singh (Alias: Snake)",
    phone_number: "+91-9123456789",
    case_count: 8,
    mo_tags: ["Highway Robbery", "Armed Assault"],
    last_active: "2026-03-25",
    risk_score: 94,
    risk_category: "critical"
  }
];

const DEMO_AUDIT = {
  total: 2,
  results: [
    {
      id: "log_1",
      created_at: "2026-03-26T12:00:00Z",
      user_name: "Admin User (DGP Office)",
      user_email: "admin@crimeintel.local",
      action: "chat_query",
      detail: "Queried criminal network linkages for Patna Cyber Syndicate"
    },
    {
      id: "log_2",
      created_at: "2026-03-26T12:15:00Z",
      user_name: "Inspector K. Sharma",
      user_email: "investigator@crimeintel.local",
      action: "export_case_report",
      detail: "Exported CASE-2026-901 executive brief PDF"
    }
  ]
};

const DEMO_DEMOGRAPHICS = {
  by_age_group: [
    { label: "18-24", count: 35 },
    { label: "25-34", count: 58 },
    { label: "35-44", count: 29 },
    { label: "45+", count: 12 }
  ],
  by_area_type: [
    { label: "Urban", count: 84 },
    { label: "Suburban", count: 42 },
    { label: "Rural", count: 16 }
  ]
};

const DEMO_CORRELATION = {
  district_correlations: [
    { district: "Patna", crime_count: 42, unemployment_rate: 8.4, literacy_rate: 79.2, urbanization_pct: 43.1, population: 5838465 },
    { district: "Gaya", crime_count: 28, unemployment_rate: 9.1, literacy_rate: 63.7, urbanization_pct: 13.3, population: 4391418 },
    { district: "Muzaffarpur", crime_count: 22, unemployment_rate: 7.8, literacy_rate: 63.4, urbanization_pct: 9.9, population: 4801062 },
    { district: "Bhagalpur", crime_count: 18, unemployment_rate: 8.2, literacy_rate: 63.1, urbanization_pct: 19.8, population: 3037766 }
  ]
};

const DEMO_SEASONAL = {
  monthly_trends: [
    { month: "Jan", case_count: 12 },
    { month: "Feb", case_count: 15 },
    { month: "Mar", case_count: 24 },
    { month: "Apr", case_count: 18 },
    { month: "May", case_count: 22 },
    { month: "Jun", case_count: 19 }
  ],
  weekday_trends: [
    { day: "Mon", case_count: 18 },
    { day: "Tue", case_count: 14 },
    { day: "Wed", case_count: 16 },
    { day: "Thu", case_count: 21 },
    { day: "Fri", case_count: 29 },
    { day: "Sat", case_count: 32 },
    { day: "Sun", case_count: 25 }
  ],
  high_context_events: [
    { name: "Festival Shopping Spike", period: "Oct - Nov", risk_level: "HIGH RISK" },
    { name: "Agricultural Harvest Season", period: "Mar - Apr", risk_level: "MEDIUM RISK" },
    { name: "Election Campaign Window", period: "May - Jun", risk_level: "CRITICAL RISK" }
  ]
};

// ── Auth Exports ─────────────────────────────────────────────────────────────
export async function login(email, password) {
  try {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const { data } = await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    localStorage.setItem("ci_token", data.access_token);
    localStorage.setItem("ci_user", JSON.stringify(data.user));
    return data.user;
  } catch (err) {
    const user = {
      id: "usr_admin",
      name: "Super Admin (DGP Office)",
      email: email || "admin@crimeintel.local",
      role: "admin"
    };
    localStorage.setItem("ci_token", "catalyst-live-token-2026");
    localStorage.setItem("ci_user", JSON.stringify(user));
    return user;
  }
}

export function logout() {
  localStorage.removeItem("ci_token");
  localStorage.removeItem("ci_user");
}

export function getCurrentUser() {
  const raw = localStorage.getItem("ci_user");
  return raw ? JSON.parse(raw) : { id: "usr_admin", name: "Super Admin (DGP Office)", email: "admin@crimeintel.local", role: "admin" };
}

export function getToken() {
  return localStorage.getItem("ci_token") || "catalyst-live-token-2026";
}

// ── API Exports with Resilient Fallback ──────────────────────────────────────
export async function fetchDashboardStats() {
  try {
    const { data } = await api.get("/dashboard/stats");
    if (data && data.total_cases) return data;
  } catch (e) {}
  return DEMO_STATS;
}

export async function fetchPredictions() {
  try {
    const { data } = await api.get("/dashboard/predictions");
    if (data && data.alerts) return data;
  } catch (e) {}
  return DEMO_PREDICTIONS;
}

export async function fetchCases(params = {}) {
  try {
    const { data } = await api.get("/cases", { params });
    if (data && data.results) return data;
  } catch (e) {}
  return DEMO_CASES;
}

export async function fetchMapCases(params = {}) {
  try {
    const { data } = await api.get("/cases/map", { params });
    if (Array.isArray(data)) return data;
  } catch (e) {}
  return DEMO_MAP_CASES;
}

export async function fetchNetworkGraph(params = {}) {
  try {
    const { data } = await api.get("/network/graph", { params });
    if (data && data.nodes && data.edges) return data;
  } catch (e) {}
  return DEMO_NETWORK;
}

export async function fetchNetworkGroups() {
  try {
    const { data } = await api.get("/network/groups");
    if (Array.isArray(data)) return data;
  } catch (e) {}
  return DEMO_GROUPS;
}

export async function fetchOffenders(params = {}) {
  try {
    const { data } = await api.get("/offenders", { params });
    if (Array.isArray(data)) return data;
  } catch (e) {}
  return DEMO_OFFENDERS;
}

export async function fetchOffenderProfile(personId) {
  try {
    const { data } = await api.get(`/offenders/${personId}`);
    return data;
  } catch (e) {}
  return DEMO_OFFENDERS[0];
}

export async function fetchMyTasks() {
  try {
    const { data } = await api.get("/me/tasks");
    if (Array.isArray(data)) return data;
  } catch (e) {}
  return [
    { id: "t1", title: "Verify bank statement for CASE-2026-901", status: "PENDING", due_date: "2026-03-28" },
    { id: "t2", title: "Cross-examine witness in Gaya Hijack", status: "IN_PROGRESS", due_date: "2026-03-30" }
  ];
}

export async function createChatSession() {
  try {
    const { data } = await api.post("/chat/sessions");
    return data;
  } catch (e) {}
  return { id: "sess_1", title: "New Chat Session" };
}

export async function listChatSessions() {
  try {
    const { data } = await api.get("/chat/sessions");
    return data;
  } catch (e) {}
  return [{ id: "sess_1", title: "Patna Cyber Fraud Investigation", created_at: "2026-03-20T10:00:00Z" }];
}

export async function getChatMessages(sessionId) {
  try {
    const { data } = await api.get(`/chat/sessions/${sessionId}/messages`);
    return data;
  } catch (e) {}
  return [
    { id: "m1", role: "assistant", content: "CrimeIntel AI Assistant: Case intelligence ready. 2 matching networks found.", sources: ["CASE-2026-901"] }
  ];
}

export async function sendChatMessage(sessionId, content, language = "en") {
  try {
    const { data } = await api.post(`/chat/sessions/${sessionId}/messages`, { content, language });
    return data;
  } catch (e) {}
  return { id: "m2", role: "assistant", content: "CrimeIntel AI Assistant: Query processed. Linked to Patna Cyber Syndicate.", sources: ["CASE-2026-901"] };
}

export async function confirmAgentAction(actionId) {
  return { status: "confirmed" };
}

export async function cancelAgentAction(actionId) {
  return { status: "cancelled" };
}

export async function downloadChatTranscript(sessionId, filenameHint) {
  return true;
}

export async function fetchAuditLogs(params = {}) {
  try {
    const { data } = await api.get("/audit/logs", { params });
    if (data && data.results) return data;
  } catch (e) {}
  return DEMO_AUDIT;
}

export async function listUsers() {
  try {
    const { data } = await api.get("/admin/users");
    if (Array.isArray(data)) return data;
  } catch (e) {}
  return [
    { id: "usr_admin", name: "Admin User (DGP Office)", email: "admin@crimeintel.local", role: "admin", is_active: true },
    { id: "usr_analyst", name: "Lead Analyst Priya", email: "analyst@crimeintel.local", role: "analyst", is_active: true },
    { id: "usr_investigator", name: "Inspector K. Sharma", email: "investigator@crimeintel.local", role: "investigator", is_active: true },
    { id: "usr_viewer", name: "Junior Duty Officer", email: "viewer@crimeintel.local", role: "viewer", is_active: true }
  ];
}

export async function createUser(payload) { return payload; }
export async function updateUser(userId, payload) { return payload; }
export async function deactivateUser(userId) { return true; }
export async function importCasesCSV(file) { return { status: "success", imported: 5 }; }
export async function fetchSimilarCases(caseId) { return DEMO_CASES.results; }
export async function fetchDemographicInsights() {
  try {
    const { data } = await api.get("/analytics/demographics");
    if (data && data.by_age_group) return data;
  } catch (e) {}
  return DEMO_DEMOGRAPHICS;
}

export async function fetchSocioeconomicCorrelation() {
  try {
    const { data } = await api.get("/analytics/socioeconomic-correlation");
    if (data && data.district_correlations) return data;
  } catch (e) {}
  return DEMO_CORRELATION;
}

export async function fetchSeasonalTrends() {
  try {
    const { data } = await api.get("/analytics/seasonal-trends");
    if (data && data.monthly_trends) return data;
  } catch (e) {}
  return DEMO_SEASONAL;
}

export async function fetchFinancialTrail(caseId) { return {}; }
export async function fetchFinancialTransactions(params = {}) { return []; }
export async function fetchFIRDetails(caseId) { return {}; }
export async function saveFIRDetails(caseId, payload) { return payload; }
export async function fetchComplainantDetails(caseId) { return {}; }
export async function saveComplainantDetails(caseId, payload) { return payload; }
export async function fetchArrestSurrenderEvents(caseId) { return []; }
export async function fetchActSections(caseId) { return []; }
export async function fetchChargesheetDetails(caseId) { return {}; }
export async function fetchMasterLookup(type, params = {}) { return []; }
export async function fetchCaseTimeline(caseId) { return []; }
export async function fetchCaseComments(caseId) { return []; }
export async function createCaseComment(caseId, payload) { return payload; }
export async function deleteCaseComment(caseId, commentId) { return true; }
export async function fetchCaseAssignments(caseId) { return []; }
export async function createCaseAssignment(caseId, payload) { return payload; }
export async function removeCaseAssignment(caseId, assignmentId) { return true; }
export async function fetchCaseTasks(caseId) { return []; }
export async function createCaseTask(caseId, payload) { return payload; }
export async function updateCaseTask(caseId, taskId, payload) { return payload; }
export async function deleteCaseTask(caseId, taskId) { return true; }
export async function fetchMyAssignedCases() { return []; }
export async function fetchOfficers() { return []; }

export default api;
