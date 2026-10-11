import { useState } from "react";
import CrudPage from "../components/CrudPage";
import { Badge, DataState, Modal, ProgressBar, fmtDate } from "../components/ui";
import { useToast } from "../components/Toast";
import { useFetch } from "../hooks";
import { get, parseError, post } from "../api/client";

const STATUS = ["planned", "active", "completed"];

function AssignModal({ sprint, onClose, onDone }) {
  const toast = useToast();
  const { data, loading, error, reload } = useFetch(() => get("/stories"), []);
  const [picked, setPicked] = useState([]);
  const available = (data || []).filter((s) => s.status === "backlog" && s.sprint_id !== sprint.id);
  const toggle = (id) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  async function save() {
    try { await post(`/sprints/${sprint.id}/assign-stories`, { story_ids: picked }); toast.success(`${picked.length} stories assigned`); onDone(); onClose(); }
    catch (e) { toast.error(parseError(e).message); }
  }
  return (
    <Modal title={`Assign stories to ${sprint.name}`} onClose={onClose}>
      <div className="form">
        <DataState loading={loading} error={error} onRetry={reload} empty={available.length === 0} emptyText="No unassigned backlog stories." emptyHint="Create stories on the Backlog page first.">
          <ul className="check-list">
            {available.map((s) => (
              <li key={s.id}><label><input type="checkbox" checked={picked.includes(s.id)} onChange={() => toggle(s.id)} /> {s.title} <span className="muted">({s.story_points} pts)</span></label></li>
            ))}
          </ul>
        </DataState>
        <footer><button className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={!picked.length} onClick={save}>Assign {picked.length || ""} stories</button></footer>
      </div>
    </Modal>
  );
}

export default function Sprints() {
  const toast = useToast();
  const [assigning, setAssigning] = useState(null);
  const act = (row, action, reload, body) =>
    post(`/sprints/${row.id}/${action}`, body).then(() => { toast.success(`Sprint ${action === "start" ? "started" : "completed"}`); window.dispatchEvent(new Event("notifications-changed")); reload(); })
      .catch((e) => toast.error(parseError(e).message));
  return (
    <>
      <CrudPage title="Sprints" subtitle="Plan, run and review time-boxed iterations. Completed sprints keep their committed and delivered points." noun="Sprint" endpoint="sprints"
        filters={[{ name: "status", label: "Status", options: STATUS }]}
        fields={[
          { name: "name", label: "Sprint name", required: true },
          { name: "goal", label: "Sprint goal", type: "textarea" },
          { name: "start_date", label: "Start date", type: "date", required: true },
          { name: "end_date", label: "End date", type: "date", required: true },
        ]}
        columns={[
          { key: "name", label: "Sprint", render: (r) => <><strong>{r.name}</strong>{r.goal && <div className="muted clamp">{r.goal}</div>}</> },
          { key: "status", label: "Status", render: (r) => <Badge value={r.status} /> },
          { key: "dates", label: "Dates", render: (r) => `${fmtDate(r.start_date)} – ${fmtDate(r.end_date)}` },
          { key: "points", label: "Points", render: (r) => (<><ProgressBar value={r.total_points ? Math.round((100 * r.completed_points) / r.total_points) : 0} /><div className="muted">{r.completed_points}/{r.total_points} pts · {r.story_count} stories</div></>) },
        ]}
        rowActions={(row, { reload }) => (
          <>
            {row.status !== "completed" && <button className="btn btn-sm" onClick={() => setAssigning({ row, reload })}>Assign stories</button>}
            {row.status === "planned" && <button className="btn btn-sm btn-primary" onClick={() => act(row, "start", reload)}>Start</button>}
            {row.status === "active" && <button className="btn btn-sm btn-primary" onClick={() => {
              const carry = window.confirm("Complete this sprint?\n\nOK = return unfinished stories to the backlog.\nCancel = keep the sprint open.");
              if (carry) act(row, "complete", reload, { carry_over: true });
            }}>Complete</button>}
          </>
        )} />
      {assigning && <AssignModal sprint={assigning.row} onClose={() => setAssigning(null)} onDone={assigning.reload} />}
    </>
  );
}
