import CrudPage from "../components/CrudPage";
import { Badge, fmtDate } from "../components/ui";
import { useToast } from "../components/Toast";
import { patch, parseError } from "../api/client";

const SEV = ["low", "medium", "high", "critical"];
const STATUS = ["open", "in_progress", "resolved"];
const opts = (a) => a.map((v) => ({ value: v, label: v.replace(/_/g, " ") }));

export default function Blockers() {
  const toast = useToast();
  return (
    <CrudPage title="Blockers" subtitle="Anything stopping work. Unresolved blockers also appear on the dashboard." noun="Blocker" endpoint="blockers"
      filters={[{ name: "status", label: "Status", options: STATUS }, { name: "severity", label: "Severity", options: SEV }]}
      refs={{ task_id: { endpoint: "tasks", label: (t) => t.title } }}
      summary={(rows) => `${rows.filter((b) => b.status !== "resolved").length} unresolved of ${rows.length} shown`}
      fields={[
        { name: "title", label: "Title", required: true },
        { name: "description", label: "Description", type: "textarea" },
        { name: "severity", label: "Severity", type: "select", options: opts(SEV), default: "medium" },
        { name: "status", label: "Status", type: "select", options: opts(STATUS), default: "open" },
        { name: "reported_date", label: "Reported date", type: "date", default: new Date().toISOString().slice(0, 10) },
        { name: "task_id", label: "Blocked task (optional)", ref: "task_id" },
      ]}
      columns={[
        { key: "title", label: "Blocker", render: (r) => <><strong>{r.title}</strong>{r.description && <div className="muted clamp">{r.description}</div>}</> },
        { key: "severity", label: "Severity", render: (r) => <Badge value={r.severity} /> },
        { key: "status", label: "Status", render: (r) => <Badge value={r.status} /> },
        { key: "reported_date", label: "Reported", render: (r) => fmtDate(r.reported_date) },
        { key: "task", label: "Task", render: (r, ref) => (ref.task_id || []).find((t) => t.id === r.task_id)?.title || "—" },
      ]}
      rowActions={(row, { reload }) => row.status !== "resolved" && (
        <button className="btn btn-sm" onClick={() => patch(`/blockers/${row.id}`, { status: "resolved" })
          .then(() => { toast.success("Blocker resolved"); reload(); }).catch((e) => toast.error(parseError(e).message))}>Resolve</button>
      )} />
  );
}
