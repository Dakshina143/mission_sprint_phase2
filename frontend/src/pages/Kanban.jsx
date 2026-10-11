import { useEffect, useState } from "react";
import { del, get, parseError, patch, post } from "../api/client";
import FormModal from "../components/FormModal";
import { Badge, DataState, PageHeader, fmtDate } from "../components/ui";
import { useToast } from "../components/Toast";

const COLUMNS = [["todo", "To Do"], ["in_progress", "In Progress"], ["in_review", "In Review"], ["done", "Done"]];
const PRIORITY = ["low", "medium", "high", "critical"];
const opts = (a) => a.map((v) => ({ value: v, label: v.replace(/_/g, " ") }));

export default function Kanban() {
  const toast = useToast();
  const [tasks, setTasks] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refs, setRefs] = useState({ missions: [], stories: [], sprints: [] });
  const [sprintFilter, setSprintFilter] = useState("");
  const [editing, setEditing] = useState(null);
  const [dragOver, setDragOver] = useState(null);

  const load = () => {
    setLoading(true); setError(null);
    get("/tasks", { sprint_id: sprintFilter || undefined }).then((r) => setTasks(r.data)).catch((e) => setError(parseError(e).message)).finally(() => setLoading(false));
  };
  useEffect(load, [sprintFilter]);
  useEffect(() => {
    Promise.all([get("/missions"), get("/stories"), get("/sprints")]).then(([m, s, sp]) => setRefs({ missions: m.data, stories: s.data, sprints: sp.data }))
      .catch((e) => toast.error(`Could not load options: ${parseError(e).message}`));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function move(task, status) {
    if (task.status === status) return;
    const prev = tasks;
    setTasks((ts) => ts.map((t) => (t.id === task.id ? { ...t, status } : t))); // optimistic
    try { await patch(`/tasks/${task.id}`, { status }); load(); } // reload to reflect server-derived fields
    catch (e) { setTasks(prev); toast.error(`Move failed: ${parseError(e).message}`); }
  }

  const ref = (list, label) => [{ value: "", label: "None" }, ...list.map((x) => ({ value: x.id, label: label(x) }))];
  const fields = [
    { name: "title", label: "Title", required: true },
    { name: "description", label: "Description", type: "textarea" },
    { name: "status", label: "Status", type: "select", options: COLUMNS.map(([v, l]) => ({ value: v, label: l })), default: "todo" },
    { name: "priority", label: "Priority", type: "select", options: opts(PRIORITY), default: "medium" },
    { name: "assignee", label: "Assignee" },
    { name: "due_date", label: "Due date", type: "date" },
    { name: "mission_id", label: "Mission", type: "select", numeric: true, options: ref(refs.missions, (m) => m.title) },
    { name: "story_id", label: "Story", type: "select", numeric: true, options: ref(refs.stories, (s) => s.title) },
    { name: "sprint_id", label: "Sprint", type: "select", numeric: true, options: ref(refs.sprints, (s) => s.name) },
  ];

  async function save(payload) {
    if (editing.id) await patch(`/tasks/${editing.id}`, payload); else await post("/tasks", payload);
    toast.success(editing.id ? "Task updated" : "Task created");
    window.dispatchEvent(new Event("notifications-changed"));
    load();
  }
  async function remove(t) {
    if (!window.confirm(`Delete task “${t.title}”?`)) return;
    try { await del(`/tasks/${t.id}`); toast.success("Task deleted"); load(); } catch (e) { toast.error(parseError(e).message); }
  }

  const today = new Date().toISOString().slice(0, 10);
  return (
    <section>
      <PageHeader title="Board" subtitle="Drag cards between columns, or use the status menu on a card. Changes are saved immediately.">
        <select value={sprintFilter} onChange={(e) => setSprintFilter(e.target.value)} aria-label="Filter by sprint">
          <option value="">All sprints</option>
          {refs.sprints.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <button className="btn btn-primary" onClick={() => setEditing({ sprint_id: sprintFilter ? Number(sprintFilter) : null })}>New task</button>
      </PageHeader>
      <DataState loading={loading && !tasks} error={error} onRetry={load}>
        <div className="board">
          {COLUMNS.map(([status, label]) => {
            const items = (tasks || []).filter((t) => t.status === status);
            return (
              <div key={status} className={`column ${dragOver === status ? "drag-over" : ""}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(status); }} onDragLeave={() => setDragOver(null)}
                onDrop={(e) => { e.preventDefault(); setDragOver(null); const t = tasks.find((x) => x.id === Number(e.dataTransfer.getData("text/plain"))); if (t) move(t, status); }}>
                <h3>{label}<span className="count">{items.length}</span></h3>
                {items.length === 0 && <p className="muted empty-col">No tasks</p>}
                {items.map((t) => (
                  <article key={t.id} className="card-task" draggable onDragStart={(e) => e.dataTransfer.setData("text/plain", String(t.id))}>
                    <strong>{t.title}</strong>
                    <div className="meta"><Badge value={t.priority} />{t.assignee && <span>{t.assignee}</span>}
                      {t.due_date && <span className={t.status !== "done" && t.due_date < today ? "overdue" : ""}>Due {fmtDate(t.due_date)}</span>}</div>
                    <div className="meta muted">
                      {refs.missions.find((m) => m.id === t.mission_id)?.title}
                    </div>
                    <div className="card-actions">
                      <select value={t.status} aria-label={`Status of ${t.title}`} onChange={(e) => move(t, e.target.value)}>
                        {COLUMNS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                      <button className="btn btn-sm" onClick={() => setEditing(t)}>Edit</button>
                      <button className="btn btn-sm btn-danger" onClick={() => remove(t)}>Delete</button>
                    </div>
                  </article>
                ))}
              </div>
            );
          })}
        </div>
      </DataState>
      {editing && <FormModal title={editing.id ? "Edit task" : "New task"} fields={fields} initial={editing} onSubmit={save} onClose={() => setEditing(null)} submitLabel={editing.id ? "Save changes" : "Create task"} />}
    </section>
  );
}
