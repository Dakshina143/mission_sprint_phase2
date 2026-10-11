import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import App from "../App";
import { ToastProvider } from "../components/Toast";

export const ok = (data, extra = {}) => Promise.resolve({ success: true, data, ...extra });

/** Mimics an axios error carrying the backend's error envelope. */
export const apiError = (status, message, details = null) =>
  Promise.reject({ response: { status, data: { success: false, error: { message, details } } } });
export const networkError = () => Promise.reject({ request: {}, message: "Network Error" });

/** Default GET responses for every endpoint the app reads; override per test. */
export const baseData = {
  "/health": { status: "ok" },
  "/notifications": [],
  "/dashboard": {
    totals: { missions: 3, active_missions: 2, tasks: 7, completed_tasks: 4 }, current_sprint: null, backlog_stories: 2, open_blockers: 1,
    open_blocker_list: [], task_status_distribution: { todo: 1, in_progress: 1, in_review: 1, done: 4 }, recent_activity: [], demo_data_present: false,
  },
  "/analytics/burndown": null,
  "/analytics/velocity": { sprints: [], average_velocity: null },
  "/analytics/sprint-completion": [],
  "/analytics/mission-progress": [],
  "/integrations/cicd": { configured: false, status: "not_configured" },
  "/missions": [], "/stories": [], "/sprints": [], "/tasks": [], "/blockers": [], "/retrospectives": [],
};

export function mockGet(get, overrides = {}) {
  const data = { ...baseData, ...overrides };
  get.mockImplementation((url) => {
    const v = data[url];
    if (typeof v === "function") return v();
    if (v === undefined) return Promise.reject(new Error(`unmocked GET ${url}`));
    return ok(v, url === "/notifications" ? { unread_count: v.filter?.((n) => !n.is_read).length ?? 0 } : {});
  });
}

export const renderApp = (path = "/") =>
  render(<MemoryRouter initialEntries={[path]}><ToastProvider><App /></ToastProvider></MemoryRouter>);

export const mission = (o = {}) => ({ id: 1, title: "Launch portal", description: "", priority: "high", status: "active", start_date: null, end_date: null, progress: 50, task_count: 2, ...o });
export const task = (o = {}) => ({ id: 1, title: "Build login", description: "", status: "todo", priority: "high", assignee: "Asha", due_date: null, mission_id: null, story_id: null, sprint_id: null, ...o });

export function setup(vi_) { vi_.spyOn(window, "confirm").mockReturnValue(true); }
export { vi };
