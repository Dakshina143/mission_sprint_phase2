import CrudPage from "../components/CrudPage";
import { Badge, ProgressBar, fmtDate } from "../components/ui";

const PRIORITY = ["low", "medium", "high", "critical"];
const STATUS = ["planning", "active", "on_hold", "completed"];
const opts = (a) => a.map((v) => ({ value: v, label: v.replace(/_/g, " ") }));

export default function Missions() {
  return (
    <CrudPage title="Missions" subtitle="Large goals that group backlog stories and tasks. Progress comes from completed tasks." noun="Mission" endpoint="missions"
      filters={[{ name: "status", label: "Status", options: STATUS }, { name: "priority", label: "Priority", options: PRIORITY }]}
      fields={[
        { name: "title", label: "Title", required: true },
        { name: "description", label: "Description", type: "textarea" },
        { name: "priority", label: "Priority", type: "select", options: opts(PRIORITY), default: "medium" },
        { name: "status", label: "Status", type: "select", options: opts(STATUS), default: "planning" },
        { name: "start_date", label: "Start date", type: "date" },
        { name: "end_date", label: "End date", type: "date" },
      ]}
      columns={[
        { key: "title", label: "Mission", render: (r) => <><strong>{r.title}</strong>{r.description && <div className="muted clamp">{r.description}</div>}</> },
        { key: "priority", label: "Priority", render: (r) => <Badge value={r.priority} /> },
        { key: "status", label: "Status", render: (r) => <Badge value={r.status} /> },
        { key: "dates", label: "Dates", render: (r) => `${fmtDate(r.start_date)} – ${fmtDate(r.end_date)}` },
        { key: "progress", label: "Progress", render: (r) => <><ProgressBar value={r.progress} /><div className="muted">{r.task_count} task{r.task_count === 1 ? "" : "s"}</div></> },
      ]} />
  );
}
