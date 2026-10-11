import { useState } from "react";
import { del, get, parseError, patch, post } from "../api/client";
import { useFetch } from "../hooks";
import FormModal from "../components/FormModal";
import { Badge, DataState, PageHeader, fmtDate } from "../components/ui";
import { useToast } from "../components/Toast";

const ACTION_STATUS = ["open", "in_progress", "done"];

export default function Retrospectives() {
  const toast = useToast();
  const retros = useFetch(() => get("/retrospectives"), []);
  const sprints = useFetch(() => get("/sprints"), []);
  const [modal, setModal] = useState(null); // {kind:'retro'|'action', item}
  const reload = retros.reload;
  const guard = (p, msg) => p.then(() => { if (msg) toast.success(msg); reload(); }).catch((e) => toast.error(parseError(e).message));

  const usedSprints = new Set((retros.data || []).map((r) => r.sprint_id));
  const sprintOptions = (sprints.data || []).filter((s) => modal?.item?.id ? s.id === modal.item.sprint_id : !usedSprints.has(s.id))
    .map((s) => ({ value: s.id, label: `${s.name} (${s.status})` }));

  const retroFields = [
    { name: "sprint_id", label: "Sprint", type: "select", numeric: true, required: true, options: sprintOptions, hint: sprintOptions.length ? undefined : "Every sprint already has a retrospective, or no sprints exist yet." },
    { name: "went_well", label: "What went well", type: "textarea" },
    { name: "needs_improvement", label: "What needs improvement", type: "textarea" },
  ];
  const actionFields = [
    { name: "description", label: "Action item", required: true },
    { name: "owner", label: "Owner (optional)" },
    { name: "status", label: "Status", type: "select", default: "open", options: ACTION_STATUS.map((v) => ({ value: v, label: v.replace(/_/g, " ") })) },
  ];

  return (
    <section>
      <PageHeader title="Retrospectives" subtitle="Review each sprint and track the improvements you commit to.">
        <button className="btn btn-primary" onClick={() => setModal({ kind: "retro", item: {} })}>New retrospective</button>
      </PageHeader>
      <DataState loading={retros.loading} error={retros.error} onRetry={reload} empty={retros.data?.length === 0} emptyText="No retrospectives yet." emptyHint="Add one after a sprint to capture what to keep and what to change.">
        <div className="retro-list">
          {retros.data?.map((r) => (
            <article key={r.id} className="panel">
              <header><h2>{r.sprint_name}</h2><span className="muted">Recorded {fmtDate(r.created_at)}</span></header>
              <div className="grid-2">
                <div><h3>What went well</h3><p className="pre">{r.went_well || "—"}</p></div>
                <div><h3>What needs improvement</h3><p className="pre">{r.needs_improvement || "—"}</p></div>
              </div>
              <h3>Action items</h3>
              {r.action_items.length === 0 ? <p className="muted">No action items yet.</p> : (
                <ul className="list">
                  {r.action_items.map((a) => (
                    <li key={a.id}>
                      <span>{a.description}{a.owner && <span className="muted"> — {a.owner}</span>}</span>
                      <span className="row-actions">
                        <select value={a.status} aria-label="Action item status" onChange={(e) => guard(patch(`/action-items/${a.id}`, { status: e.target.value }))}>
                          {ACTION_STATUS.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                        </select>
                        <button className="btn btn-sm" onClick={() => setModal({ kind: "action", item: a, retro: r })}>Edit</button>
                        <button className="btn btn-sm btn-danger" onClick={() => window.confirm("Delete this action item?") && guard(del(`/action-items/${a.id}`), "Action item deleted")}>Delete</button>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="row-actions">
                <button className="btn btn-sm" onClick={() => setModal({ kind: "action", item: {}, retro: r })}>Add action item</button>
                <button className="btn btn-sm" onClick={() => setModal({ kind: "retro", item: r })}>Edit retrospective</button>
                <button className="btn btn-sm btn-danger" onClick={() => window.confirm("Delete this retrospective and its action items?") && guard(del(`/retrospectives/${r.id}`), "Retrospective deleted")}>Delete</button>
              </div>
            </article>
          ))}
        </div>
      </DataState>
      {modal?.kind === "retro" && (
        <FormModal title={modal.item.id ? "Edit retrospective" : "New retrospective"} fields={retroFields} initial={modal.item} onClose={() => setModal(null)}
          onSubmit={async (p) => { if (modal.item.id) await patch(`/retrospectives/${modal.item.id}`, p); else await post("/retrospectives", p); toast.success("Retrospective saved"); reload(); }} />
      )}
      {modal?.kind === "action" && (
        <FormModal title={modal.item.id ? "Edit action item" : "New action item"} fields={actionFields} initial={modal.item} onClose={() => setModal(null)}
          onSubmit={async (p) => { if (modal.item.id) await patch(`/action-items/${modal.item.id}`, p); else await post("/action-items", { ...p, retrospective_id: modal.retro.id }); toast.success("Action item saved"); reload(); }} />
      )}
    </section>
  );
}
