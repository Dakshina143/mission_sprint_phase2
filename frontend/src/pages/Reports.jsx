import { useState } from "react";
import { downloadCsv, get, parseError } from "../api/client";
import { DataState, PageHeader } from "../components/ui";
import { useToast } from "../components/Toast";

const KINDS = [["missions", "Missions"], ["tasks", "Tasks"], ["sprints", "Sprints"], ["blockers", "Blockers"], ["retrospectives", "Retrospectives"]];

export default function Reports() {
  const toast = useToast();
  const [kind, setKind] = useState(null);
  const [state, setState] = useState({ loading: false, error: null, body: null });

  function preview(k) {
    setKind(k); setState({ loading: true, error: null, body: null });
    get(`/reports/${k}`).then((b) => setState({ loading: false, error: null, body: b })).catch((e) => setState({ loading: false, error: parseError(e).message, body: null }));
  }
  const download = (k) => downloadCsv(k).then(() => toast.success("CSV downloaded")).catch((e) => toast.error(parseError(e).message));
  const d = state.body?.data;

  return (
    <section>
      <PageHeader title="Reports" subtitle="Live exports of the records stored in the database." />
      <div className="report-cards">
        {KINDS.map(([k, label]) => (
          <div key={k} className={`panel ${kind === k ? "selected" : ""}`}>
            <h2>{label}</h2>
            <div className="row-actions"><button className="btn btn-sm" onClick={() => preview(k)}>Preview</button><button className="btn btn-sm btn-primary" onClick={() => download(k)}>Download CSV</button></div>
          </div>
        ))}
      </div>
      {kind && (
        <section className="panel">
          <header><h2>{KINDS.find(([k]) => k === kind)[1]} report</h2>{d && <span className="muted">{state.body.count} rows · generated {d.generated_on}</span>}</header>
          <DataState loading={state.loading} error={state.error} onRetry={() => preview(kind)} empty={d && d.rows.length === 0} emptyText="No records to report yet.">
            {d && <div className="table-wrap"><table><thead><tr>{d.columns.map((c) => <th key={c}>{c.replace(/_/g, " ")}</th>)}</tr></thead>
              <tbody>{d.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c ?? ""}</td>)}</tr>)}</tbody></table></div>}
          </DataState>
        </section>
      )}
    </section>
  );
}
