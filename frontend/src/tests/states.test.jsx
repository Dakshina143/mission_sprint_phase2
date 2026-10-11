import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/client", async () => ({ ...(await vi.importActual("../api/client")), get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn() }));
vi.mock("react-chartjs-2", () => ({ Line: () => <canvas />, Bar: () => <canvas />, Doughnut: () => <canvas /> }));

import { get } from "../api/client";
import { apiError, mission, mockGet, networkError, renderApp } from "./helpers";

const PAGES = [["/missions", "No missions yet."], ["/backlog", "No backlog yet."], ["/sprints", "No sprints yet."], ["/blockers", "No blockers yet."],
  ["/retrospectives", "No retrospectives yet."], ["/notifications", "No notifications yet."]];

describe("loading, empty and failure states", () => {
  beforeEach(() => { get.mockReset(); });

  it.each(PAGES)("%s shows an empty state when there are no records", async (path, text) => {
    mockGet(get);
    renderApp(path);
    expect(await screen.findByText(text)).toBeTruthy();
  });

  it.each(PAGES.map((p) => p[0]))("%s shows an error message and retry instead of data when the API is down", async (path) => {
    mockGet(get, { "/missions": () => networkError(), "/stories": () => networkError(), "/sprints": () => networkError(), "/blockers": () => networkError(),
      "/retrospectives": () => networkError(), "/notifications": () => networkError() });
    renderApp(path);
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/Could not load data/);
    expect(alert.textContent).toMatch(/Cannot reach the API/);
    expect(screen.getByText("Try again")).toBeTruthy();
  });

  it("shows a loading indicator while data is in flight", async () => {
    mockGet(get, { "/missions": () => new Promise(() => {}) });
    renderApp("/missions");
    expect(await screen.findByText("Loading…")).toBeTruthy();
  });

  it("retry reloads and then shows the data", async () => {
    let calls = 0;
    mockGet(get, { "/missions": () => (++calls === 1 ? networkError() : Promise.resolve({ success: true, data: [mission()] })) });
    renderApp("/missions");
    fireEvent.click(await screen.findByText("Try again"));
    expect(await screen.findByText("Launch portal")).toBeTruthy();
  });

  it("surfaces the server's error message for non-network failures", async () => {
    mockGet(get, { "/missions": () => apiError(500, "Database error") });
    renderApp("/missions");
    expect((await screen.findByRole("alert")).textContent).toMatch(/Database error/);
  });

  it("search and filters call the API with the chosen parameters", async () => {
    mockGet(get, { "/missions": [mission()] });
    renderApp("/missions");
    await screen.findByText("Launch portal");
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "port" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "active" } });
    await waitFor(() => expect(get).toHaveBeenCalledWith("/missions", expect.objectContaining({ q: "port", status: "active" })));
  });

  it("shows a filtered-empty message distinct from the first-use empty state", async () => {
    mockGet(get, { "/missions": [] });
    renderApp("/missions");
    await screen.findByText("No missions yet.");
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "completed" } });
    expect(await screen.findByText(/match these filters/)).toBeTruthy();
  });

  it("dashboard shows the demo-data notice only when demo records exist", async () => {
    mockGet(get, { "/dashboard": { ...(await import("./helpers")).baseData["/dashboard"], demo_data_present: true } });
    renderApp("/");
    expect(await screen.findByText(/contains demo records/)).toBeTruthy();
  });
});
