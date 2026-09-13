import axios from "axios";

const BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;

const http = axios.create({ baseURL: BASE, timeout: 30000 });

export const api = {
  health: () => http.get("/health").then((r) => r.data),
  users: () => http.get("/users").then((r) => r.data),
  user: (id) => http.get(`/users/${id}`).then((r) => r.data),
  timeline: (id) => http.get(`/users/${id}/timeline`).then((r) => r.data),
  reset: () => http.post("/demo/reset").then((r) => r.data),
  nextEvent: (force = false) =>
    http.post("/demo/next-event", null, { params: force ? { force: true } : {} }).then((r) => r.data),
  investigate: (user_id, event_id = null) =>
    http.post("/investigate", { user_id, event_id }).then((r) => r.data),
  assistant: (user_id, question, event_id = null) =>
    http.post("/assistant/chat", { user_id, question, event_id }).then((r) => r.data),
  audit: (user_id = null) =>
    http.get("/audit", { params: user_id ? { user_id } : {} }).then((r) => r.data),
  action: (payload) => http.post("/audit/action", payload).then((r) => r.data),
  evaluation: () => http.get("/evaluation").then((r) => r.data),
  userEvidence: (id) => http.get(`/users/${id}/evidence`).then((r) => r.data),
  userAlerts: (id) => http.get(`/users/${id}/alerts`).then((r) => r.data),
};
