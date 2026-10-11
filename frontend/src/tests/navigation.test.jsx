import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/client", async () => ({ ...(await vi.importActual("../api/client")), get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn() }));
vi.mock("react-chartjs-2", () => ({ Line: () => <canvas />, Bar: () => <canvas />, Doughnut: () => <canvas /> }));

import { get } from "../api/client";
import { apiError, mockGet, networkError, renderApp } from "./helpers";

describe("navigation and layout", () => {
  beforeEach(() => { get.mockReset(); mockGet(get); });

  it("renders the dashboard first and navigates to every section from the sidebar", async () => {
    renderApp("/");
    expect(await screen.findByText("Total missions")).toBeTruthy();
    const nav = within(screen.getByRole("navigation"));
    const targets = { Missions: "No missions yet.", Backlog: "No backlog yet.", Sprints: "No sprints yet.", Board: "New task",
      Blockers: "No blockers yet.", Retrospectives: "No retrospectives yet.", Notifications: "No notifications yet.", Reports: "Download CSV" };
    for (const [link, expected] of Object.entries(targets)) {
      fireEvent.click(nav.getByText(link));
      expect((await screen.findAllByText(expected)).length).toBeGreaterThan(0);
    }
    fireEvent.click(nav.getByText("Analytics"));
    expect(await screen.findByText("Mission progress")).toBeTruthy();
    fireEvent.click(nav.getByText("Dashboard"));
    expect(await screen.findByText("Total missions")).toBeTruthy();
  });

  it("unknown routes redirect to the dashboard", async () => {
    renderApp("/does-not-exist");
    expect(await screen.findByText("Total missions")).toBeTruthy();
  });

  it("health indicator shows healthy when the API answers", async () => {
    renderApp("/");
    expect(await screen.findByText("API and database healthy")).toBeTruthy();
  });

  it("health indicator distinguishes a down database from an unreachable API", async () => {
    mockGet(get, { "/health": () => apiError(503, "Database unreachable", "OperationalError").catch((e) => { e.response.data.data = { database: "unreachable" }; throw e; }) });
    const { unmount } = renderApp("/");
    expect(await screen.findByText("API up, database unreachable")).toBeTruthy();
    unmount();
    mockGet(get, { "/health": () => networkError() });
    renderApp("/");
    expect(await screen.findByText("API unreachable")).toBeTruthy();
  });

  it("shows the unread notification count in the sidebar", async () => {
    get.mockImplementation((url) => (url === "/notifications"
      ? Promise.resolve({ success: true, data: [], unread_count: 3 })
      : url === "/health" ? Promise.resolve({ success: true, data: {} }) : Promise.reject(new Error("x"))));
    renderApp("/notifications");
    await waitFor(() => expect(within(screen.getByRole("navigation")).getByText("3")).toBeTruthy());
  });
});
