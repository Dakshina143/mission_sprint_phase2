import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/client", async () => ({ ...(await vi.importActual("../api/client")), get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), downloadCsv: vi.fn() }));
vi.mock("react-chartjs-2", () => ({ Line: () => <canvas />, Bar: () => <canvas />, Doughnut: () => <canvas /> }));

import { del, downloadCsv, get, patch, post } from "../api/client";
import { apiError, mission, mockGet, ok, renderApp, task } from "./helpers";

// look inside the open dialog when there is one (page filters can share labels with form fields)
const field = (label) => within(screen.queryByRole("dialog") || document.body).getByLabelText(new RegExp(`^${label}`));

describe("form interactions", () => {
  beforeEach(() => { [get, post, patch, del, downloadCsv].forEach((m) => m.mockReset()); vi.spyOn(window, "confirm").mockReturnValue(true); });

  it("creates a mission: opens the form, submits the entered values, closes and reloads", async () => {
    mockGet(get);
    post.mockImplementation(() => ok(mission()));
    renderApp("/missions");
    fireEvent.click(await screen.findByText("New mission"));
    fireEvent.change(field("Title"), { target: { value: "Ship v1" } });
    fireEvent.change(field("Priority"), { target: { value: "critical" } });
    fireEvent.change(field("Start date"), { target: { value: "2026-11-01" } });
    fireEvent.click(screen.getByText("Create mission"));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/missions", expect.objectContaining({ title: "Ship v1", priority: "critical", start_date: "2026-11-01", end_date: null })));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(await screen.findByText("Mission created")).toBeTruthy();
  });

  it("shows field-level server validation errors and keeps the form open", async () => {
    mockGet(get);
    post.mockImplementation(() => apiError(422, "Validation failed", { title: "is required" }));
    renderApp("/missions");
    fireEvent.click(await screen.findByText("New mission"));
    fireEvent.click(screen.getByText("Create mission"));
    expect(await screen.findByText("Title is required")).toBeTruthy();
    expect(screen.getByText("Validation failed")).toBeTruthy();
    expect(screen.getByRole("dialog")).toBeTruthy();
  });

  it("edit prefilled form saves with PATCH to the record's URL", async () => {
    mockGet(get, { "/missions": [mission({ id: 7, title: "Old name" })] });
    patch.mockImplementation(() => ok({}));
    renderApp("/missions");
    fireEvent.click(await screen.findByText("Edit"));
    expect(field("Title").value).toBe("Old name");
    fireEvent.change(field("Title"), { target: { value: "New name" } });
    fireEvent.click(screen.getByText("Save changes"));
    await waitFor(() => expect(patch).toHaveBeenCalledWith("/missions/7", expect.objectContaining({ title: "New name" })));
  });

  it("delete asks for confirmation and calls DELETE only when confirmed", async () => {
    mockGet(get, { "/missions": [mission({ id: 7 })] });
    del.mockImplementation(() => ok({ deleted: true }));
    renderApp("/missions");
    window.confirm.mockReturnValueOnce(false);
    fireEvent.click(await screen.findByText("Delete"));
    expect(del).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Delete"));
    await waitFor(() => expect(del).toHaveBeenCalledWith("/missions/7"));
  });

  it("closing the modal with Cancel or Escape does not save", async () => {
    mockGet(get);
    renderApp("/missions");
    fireEvent.click(await screen.findByText("New mission"));
    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.click(screen.getByText("New mission"));
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(post).not.toHaveBeenCalled();
  });

  it("story form sends story points as a number and links the chosen mission", async () => {
    mockGet(get, { "/missions": [mission({ id: 4, title: "Portal" })] });
    post.mockImplementation(() => ok({}));
    renderApp("/backlog");
    fireEvent.click(await screen.findByText("New story"));
    fireEvent.change(field("Story title"), { target: { value: "Reset password" } });
    fireEvent.change(field("Story points"), { target: { value: "5" } });
    await waitFor(() => expect(within(field("Mission")).getByText("Portal")).toBeTruthy());
    fireEvent.change(field("Mission"), { target: { value: "4" } });
    fireEvent.click(screen.getByText("Create story"));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/stories", expect.objectContaining({ title: "Reset password", story_points: 5, mission_id: 4, sprint_id: null })));
  });
});

describe("user workflows", () => {
  beforeEach(() => { [get, post, patch, del, downloadCsv].forEach((m) => m.mockReset()); vi.spyOn(window, "confirm").mockReturnValue(true); });

  it("kanban: changing a card's status persists via PATCH", async () => {
    mockGet(get, { "/tasks": [task({ id: 5 })] });
    patch.mockImplementation(() => ok({}));
    renderApp("/board");
    fireEvent.change(await screen.findByLabelText("Status of Build login"), { target: { value: "in_progress" } });
    await waitFor(() => expect(patch).toHaveBeenCalledWith("/tasks/5", { status: "in_progress" }));
  });

  it("kanban: a failed move is rolled back and reported", async () => {
    mockGet(get, { "/tasks": [task({ id: 5 })] });
    patch.mockImplementation(() => apiError(500, "Database error"));
    renderApp("/board");
    const select = await screen.findByLabelText("Status of Build login");
    fireEvent.change(select, { target: { value: "done" } });
    expect(await screen.findByText(/Move failed: Database error/)).toBeTruthy();
    await waitFor(() => expect(screen.getByLabelText("Status of Build login").value).toBe("todo"));
  });

  it("kanban: tasks appear in the column for their status; new task is created through the form", async () => {
    mockGet(get, { "/tasks": [task({ id: 1, status: "done", title: "Shipped" }), task({ id: 2, title: "Waiting" })] });
    post.mockImplementation(() => ok({}));
    renderApp("/board");
    await screen.findByText("Shipped");
    const columns = document.querySelectorAll(".column");
    expect(within(columns[0]).getByText("Waiting")).toBeTruthy();
    expect(within(columns[3]).getByText("Shipped")).toBeTruthy();
    fireEvent.click(screen.getByText("New task"));
    fireEvent.change(field("Title"), { target: { value: "Write docs" } });
    fireEvent.change(field("Assignee"), { target: { value: "Ravi" } });
    fireEvent.click(screen.getByText("Create task"));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/tasks", expect.objectContaining({ title: "Write docs", assignee: "Ravi", status: "todo" })));
  });

  it("blockers: resolving an unresolved blocker PATCHes its status and the summary counts unresolved", async () => {
    mockGet(get, { "/blockers": [{ id: 3, title: "No staging DB", description: "", severity: "high", status: "open", reported_date: "2026-10-01", task_id: null }] });
    patch.mockImplementation(() => ok({}));
    renderApp("/blockers");
    expect(await screen.findByText("1 unresolved of 1 shown")).toBeTruthy();
    fireEvent.click(screen.getByText("Resolve"));
    await waitFor(() => expect(patch).toHaveBeenCalledWith("/blockers/3", { status: "resolved" }));
  });

  it("sprints: Start posts to the start action; Complete is offered for an active sprint and confirmed first", async () => {
    const sp = (o) => ({ id: 1, name: "Sprint 1", goal: "", status: "planned", start_date: "2026-10-01", end_date: "2026-10-14", total_points: 8, completed_points: 3, story_count: 2, ...o });
    mockGet(get, { "/sprints": [sp({}), sp({ id: 2, name: "Sprint 2", status: "active" })] });
    post.mockImplementation(() => ok({}));
    renderApp("/sprints");
    fireEvent.click(await screen.findByText("Start"));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/sprints/1/start", undefined));
    fireEvent.click(screen.getByText("Complete"));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/sprints/2/complete", { carry_over: true }));
  });

  it("sprints: a conflict from the server (another sprint active) is shown to the user", async () => {
    mockGet(get, { "/sprints": [{ id: 1, name: "S", goal: "", status: "planned", start_date: "2026-10-01", end_date: "2026-10-14", total_points: 0, completed_points: 0, story_count: 0 }] });
    post.mockImplementation(() => apiError(409, "Another sprint is already active. Complete it first."));
    renderApp("/sprints");
    fireEvent.click(await screen.findByText("Start"));
    expect(await screen.findByText(/Another sprint is already active/)).toBeTruthy();
  });

  it("notifications: mark read, mark all read and delete call the API", async () => {
    const n = (id, read) => ({ id, type: "task_assigned", message: `msg ${id}`, is_read: read, created_at: "2026-10-10T10:00:00Z" });
    mockGet(get, { "/notifications": [n(1, false), n(2, true)] });
    patch.mockImplementation(() => ok({})); post.mockImplementation(() => ok({ updated: 1 })); del.mockImplementation(() => ok({}));
    renderApp("/notifications");
    fireEvent.click(await screen.findByText("Mark read"));
    await waitFor(() => expect(patch).toHaveBeenCalledWith("/notifications/1", { is_read: true }));
    fireEvent.click(screen.getByText("Mark all as read"));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/notifications/mark-all-read"));
    fireEvent.click(screen.getAllByText("Delete")[0]);
    await waitFor(() => expect(del).toHaveBeenCalledWith("/notifications/1"));
  });

  it("retrospectives: lists went-well, improvements and action items; adding an action item posts to the retro", async () => {
    const retro = { id: 9, sprint_id: 1, sprint_name: "Sprint 1", went_well: "Fast reviews", needs_improvement: "Flaky tests", created_at: "2026-10-10T10:00:00Z",
      action_items: [{ id: 1, retrospective_id: 9, description: "Fix flaky tests", owner: "Sam", status: "open" }] };
    mockGet(get, { "/retrospectives": [retro], "/sprints": [{ id: 1, name: "Sprint 1", status: "completed" }] });
    post.mockImplementation(() => ok({}));
    renderApp("/retrospectives");
    expect(await screen.findByText("Fast reviews")).toBeTruthy();
    expect(screen.getByText("Flaky tests")).toBeTruthy();
    expect(screen.getByText("Fix flaky tests")).toBeTruthy();
    fireEvent.click(screen.getByText("Add action item"));
    fireEvent.change(field("Action item"), { target: { value: "Add retry policy" } });
    fireEvent.click(within(screen.getByRole("dialog")).getByText("Save"));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/action-items", expect.objectContaining({ description: "Add retry policy", retrospective_id: 9 })));
  });

  it("reports: preview loads the real rows and CSV download is requested", async () => {
    mockGet(get, { "/reports/missions": { report: "missions", generated_on: "2026-10-11", columns: ["id", "title"], rows: [["1", "Portal"]] } });
    get.mockImplementationOnce(() => ok({})); // first call is the health check
    downloadCsv.mockImplementation(() => Promise.resolve());
    renderApp("/reports");
    fireEvent.click((await screen.findAllByText("Preview"))[0]);
    expect(await screen.findByText("Portal")).toBeTruthy();
    fireEvent.click(screen.getAllByText("Download CSV")[0]);
    await waitFor(() => expect(downloadCsv).toHaveBeenCalledWith("missions"));
  });
});
