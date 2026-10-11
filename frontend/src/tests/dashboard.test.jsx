import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual("../api/client");
  return { ...actual, get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn() };
});
vi.mock("react-chartjs-2", () => ({ Line: () => <canvas />, Bar: () => <canvas />, Doughnut: () => <canvas /> }));

import { get } from "../api/client";
import { ToastProvider } from "../components/Toast";
import Dashboard from "../pages/Dashboard";
import Missions from "../pages/Missions";

const wrap = (ui) => render(<MemoryRouter><ToastProvider>{ui}</ToastProvider></MemoryRouter>);
const ok = (data, extra = {}) => Promise.resolve({ success: true, data, ...extra });

const dashboard = {
  totals: { missions: 3, active_missions: 2, tasks: 7, completed_tasks: 4 }, current_sprint: null, backlog_stories: 2, open_blockers: 1,
  open_blocker_list: [], task_status_distribution: { todo: 1, in_progress: 1, in_review: 1, done: 4 }, recent_activity: [], demo_data_present: false,
};

describe("pages use backend data", () => {
  beforeEach(() => { get.mockReset(); });

  it("dashboard renders totals from the API", async () => {
    get.mockImplementation((url) => ({
      "/dashboard": ok(dashboard), "/analytics/burndown": ok(null), "/analytics/velocity": ok({ sprints: [], average_velocity: null }),
      "/integrations/cicd": ok({ configured: false, status: "not_configured" }),
    }[url] ?? Promise.reject(new Error("unexpected " + url))));
    wrap(<Dashboard />);
    expect(await screen.findByText("Total missions")).toBeTruthy();
    expect(screen.getByText("7")).toBeTruthy();
    expect(screen.getByText(/No sprint is active/)).toBeTruthy();
    expect(screen.getByText("not connected")).toBeTruthy();
  });

  it("dashboard shows an error, not fabricated numbers, when the API fails", async () => {
    get.mockRejectedValue({ request: {}, message: "Network Error" });
    wrap(<Dashboard />);
    expect(await screen.findByText("Could not load data.")).toBeTruthy();
    expect(screen.queryByText("Total missions")).toBeNull();
  });

  it("missions page shows an empty state and a list", async () => {
    get.mockImplementation(() => ok([]));
    const { unmount } = wrap(<Missions />);
    expect(await screen.findByText("No missions yet.")).toBeTruthy();
    unmount();
    get.mockImplementation(() => ok([{ id: 1, title: "Launch portal", description: "", priority: "high", status: "active", start_date: null, end_date: null, progress: 50, task_count: 2 }]));
    wrap(<Missions />);
    await waitFor(() => expect(screen.getByText("Launch portal")).toBeTruthy());
    expect(screen.getByText("50%")).toBeTruthy();
  });
});
