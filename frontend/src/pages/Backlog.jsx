import CrudPage from "../components/CrudPage";
import { Badge } from "../components/ui";
import { useToast } from "../components/Toast";
import { parseError, post } from "../api/client";

const PRIORITY = ["low", "medium", "high", "critical"];
const STATUS = ["backlog", "in_sprint", "done"];
const opts = (a) => a.map((v) => ({ value: v, label: v.replace(/_/g, " ") }));

export default function Backlog() {
  const toast = useToast();
  async function move(rows, i, dir, reload) {
    const ids = rows.map((r) => r.id);
    const j = i + dir;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    try { await post("/stories/reorder", { ids }); reload(); } catch (e) { toast.error(parseError(e).message); }
  }
  return (
    <CrudPage title="Backlog" subtitle="User stories in priority order. Use the arrows to re-rank (only when no filter or search is applied)." noun="Story" endpoint="stories"
      filters={[{ name: "status", label: "Status", options: STATUS }, { name: "priority", label: "Priority", options: PRIORITY }]}
      refs={{ mission_id: { endpoint: "missions", label: (m) => m.title }, sprint_id: { endpoint: "sprints", label: (s) => s.name } }}
      fields={[
        { name: "title", label: "Story title", required: true, hint: "e.g. As a user, I can reset my password" },
        { name: "description", label: "Description", type: "textarea" },
        { name: "acceptance_criteria", label: "Acceptance criteria", type: "textarea" },
        { name: "priority", label: "Priority", type: "select", options: opts(PRIORITY), default: "medium" },
        { name: "story_points", label: "Story points", type: "number", required: true, default: 1 },
        { name: "status", label: "Status", type: "select", options: opts(STATUS), default: "backlog" },
        { name: "mission_id", label: "Mission", ref: "mission_id" },
        { name: "sprint_id", label: "Sprint", ref: "sprint_id" },
      ]}
      columns={[
        { key: "title", label: "Story", render: (r) => <><strong>{r.title}</strong>{r.acceptance_criteria && <div className="muted clamp">{r.acceptance_criteria}</div>}</> },
        { key: "priority", label: "Priority", render: (r) => <Badge value={r.priority} /> },
        { key: "story_points", label: "Points" },
        { key: "status", label: "Status", render: (r) => <Badge value={r.status} /> },
        { key: "mission", label: "Mission", render: (r, ref) => (ref.mission_id || []).find((m) => m.id === r.mission_id)?.title || "—" },
        { key: "sprint", label: "Sprint", render: (r, ref) => (ref.sprint_id || []).find((s) => s.id === r.sprint_id)?.name || "Unassigned" },
      ]}
      rowActions={(row, { rows, index, reload, filtered }) => (
        <>
          <button className="btn btn-sm" aria-label="Move up" disabled={filtered || index === 0} onClick={() => move(rows, index, -1, reload)}>↑</button>
          <button className="btn btn-sm" aria-label="Move down" disabled={filtered || index === rows.length - 1} onClick={() => move(rows, index, 1, reload)}>↓</button>
        </>
      )} />
  );
}
