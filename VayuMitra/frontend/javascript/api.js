/* VayuMitra Frontend API Client */
(function (window) {
  "use strict";

  function buildQuery(params) {
    const qs = new URLSearchParams();
    Object.keys(params || {}).forEach((key) => {
      const val = params[key];
      if (val !== undefined && val !== null && val !== "") {
        qs.set(key, String(val));
      }
    });
    const str = qs.toString();
    return str ? `?${str}` : "";
  }

  async function requestJson(url, options) {
    const opts = Object.assign({}, options || {});
    const token = window.localStorage.getItem("vayumitra_auth_token");
    if (token) {
      const hdrs = new Headers(opts.headers || {});
      if (!hdrs.has("Authorization")) {
        hdrs.set("Authorization", `Bearer ${token}`);
      }
      opts.headers = hdrs;
    }
    const resp = await fetch(url, opts);
    const text = await resp.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (_err) {
      data = { error: "Unexpected response from server." };
    }
    if (!resp.ok) {
      throw new Error(data.error || `Request failed (${resp.status})`);
    }
    return data;
  }

  window.VayuApi = {
    login(payload) {
      return requestJson("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    register(payload) {
      return requestJson("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    logout() {
      return requestJson("/api/auth/logout", {
        method: "POST",
      });
    },
    getAuthMe() {
      return requestJson("/api/auth/me");
    },
    getDashboard(params) {
      return requestJson(`/api/dashboard${buildQuery(params)}`);
    },
    getIndiaLocations() {
      return requestJson("/api/locations/india");
    },
    getAirQuality(params) {
      return requestJson(`/api/air-quality${buildQuery(params)}`);
    },
    getForecast(params) {
      return requestJson(`/api/air-quality/forecast${buildQuery(params)}`);
    },
    getHistory(params) {
      return requestJson(`/api/air-quality/history${buildQuery(params)}`);
    },
    getInsights(params) {
      return requestJson(`/api/insights${buildQuery(params)}`);
    },
    getTimeMachine(params) {
      return requestJson(`/api/insights/time-machine${buildQuery(params)}`);
    },
    simulateWhatIf(payload) {
      return requestJson("/api/insights/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    getRoutes(params) {
      return requestJson(`/api/routes${buildQuery(params)}`);
    },
    getAlerts(params) {
      return requestJson(`/api/alerts${buildQuery(params)}`);
    },
    getReports(params) {
      return requestJson(`/api/reports${buildQuery(params)}`);
    },
    getExportCsvUrl(params) {
      return `/api/reports/export${buildQuery(params)}`;
    },
    getCommunityReports(params) {
      return requestJson(`/api/community/reports${buildQuery(params)}`);
    },
    submitCommunityReport(formData) {
      return requestJson("/api/community/report", {
        method: "POST",
        body: formData,
      });
    },
    updateReportStatus(reportId, status) {
      return requestJson(`/api/community/reports/${reportId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
    },
    getProfile() {
      return requestJson("/api/profile");
    },
    updateProfile(payload) {
      return requestJson("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    getAirTwin() {
      return requestJson("/api/air-twin");
    },
    addTwinLocation(payload) {
      return requestJson("/api/air-twin/locations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    deleteTwinLocation(id) {
      return requestJson(`/api/air-twin/locations/${id}`, { method: "DELETE" });
    },
    addTwinActivity(payload) {
      return requestJson("/api/air-twin/activities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    deleteTwinActivity(id) {
      return requestJson(`/api/air-twin/activities/${id}`, { method: "DELETE" });
    },
    addTwinDiary(payload) {
      return requestJson("/api/air-twin/diary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    getAirTwinExportUrl() {
      return "/api/air-twin/export";
    },
    sendContact(payload) {
      return requestJson("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
  };
})(window);
