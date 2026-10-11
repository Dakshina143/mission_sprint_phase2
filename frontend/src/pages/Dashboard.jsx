import { Link } from "react-router-dom";
import { Doughnut } from "react-chartjs-2";
import { get } from "../api/client";
import { useFetch } from "../hooks";
import { COLORS, baseOptions } from "../charts";
import BurndownChart from "../components/BurndownChart";
import VelocityChart from "../components/VelocityChart";
import { Badge, DataState, PageHeader, ProgressBar, fmtDate } from "../components/ui";

function Panel({ title, children, to }) {
  return <section className="panel"><header><h2>{title}</h2>{to && <Link to={to}>Open</Link>}</header>{children}</section>;
}

function Pipeline({ d, cicd }) {
  const dist = d.task_status_distribution;
  const ci = cicd.data;
  const stages = [
    { name: "Backlog", value: d.backlog_stories, note: "stories waiting", live: true },
    { name: "Sprint", value: d.current_sprint ? 1 : 0, note: d.current_sprint ? d.current_sprint.name : "no active sprint", live: true },
    { name: "Execution", value: dist.in_progress, note: "tasks in progress", live: true },
    { name: "Testing", value: dist.in_review, note: "tasks in review", live: true },
    { name: "CI/CD", value: null, note: ci ? (ci.configured ? ci.status : "not connected") : cicd.error ? "status unavailable" : "checking…", live: !!ci?.configured },
    { name: "Deploy", value: null, note: "planned for part 2", live: false },
    { name: "Monitor", value: null, note: "planned for part 2", live: false },
    { name: "Retro", value: null, note: "see Retrospectives", live: true, to: "/retrospectives" },
  ];
  return (
    <ol className="pipeline" aria-label="Delivery pipeline">
      {stages.map((s) => (
        <li key={s.name} className={s.live ? "live" : "idle"}>
          <b>{s.name}</b>
          {s.value !== null && <strong className="big">{s.value}</strong>}
          <small>{s.note}</small>
        </li>
      ))}
    </ol>
  );
}

export default function Dashboard() {
  const dash = useFetch(() => get("/dashboard"), []);
  const burn = useFetch(() => get("/analytics/burndown"), []);
  const vel = useFetch(() => get("/analytics/velocity"), []);
  const cicd = useFetch(() => get("/integrations/cicd"), []);
  const d = dash.data;

  return (
    <section>
      <PageHeader title="Dashboard" subtitle="Where work stands from backlog to feedback." />
      <DataState loading={dash.loading} error={dash.error} onRetry={dash.reload}>
        {d && (
          <>
            {d.demo_data_present && <div className="notice">This workspace contains demo records (titles start with “[DEMO]”). Delete them or reseed with <code>flask seed --reset</code>.</div>}
            <Pipeline d={d} cicd={cicd} />
            <div className="stats">
              <div className="stat"><strong>{d.totals.missions}</strong><span>Total missions</span></div>
              <div className="stat"><strong>{d.totals.active_missions}</strong><span>Active missions</span></div>
              <div className="stat"><strong>{d.totals.tasks}</strong><span>Total tasks</span></div>
              <div className="stat"><strong>{d.totals.completed_tasks}</strong><span>Completed tasks</span></div>
              <div className={`stat ${d.open_blockers ? "stat-warn" : ""}`}><strong>{d.open_blockers}</strong><span>Open blockers</span></div>
            </div>
            <div className="grid-2">
              <Panel title="Current sprint" to="/sprints">
                {d.current_sprint ? (
                  <>
                    <h3>{d.current_sprint.name}</h3>
                    <p className="muted">{d.current_sprint.goal || "No goal set"} · ends {fmtDate(d.current_sprint.end_date)} ({d.current_sprint.days_remaining} days left)</p>
                    <ProgressBar value={d.current_sprint.progress_pct} />
                    <p className="muted">{d.current_sprint.completed_points}/{d.current_sprint.total_points} points · {d.current_sprint.tasks_done}/{d.current_sprint.tasks_total} tasks done</p>
                  </>
                ) : <p className="muted">No sprint is active. Start one on the Sprints page.</p>}
              </Panel>
              <Panel title="Task status" to="/board">
                {d.totals.tasks === 0 ? <p className="muted">No tasks yet.</p> : (
                  <div className="chart chart-sm"><Doughnut data={{ labels: ["To Do", "In Progress", "In Review", "Done"],
                    datasets: [{ data: Object.values(d.task_status_distribution), backgroundColor: [COLORS.grey, COLORS.cyan, COLORS.amber, COLORS.green], borderWidth: 0 }] }} options={baseOptions({ cutout: "62%" })} /></div>
                )}
              </Panel>
            </div>
            <div className="grid-2">
              <Panel title="Sprint burndown" to="/analytics">
                <DataState loading={burn.loading} error={burn.error} onRetry={burn.reload}><BurndownChart data={burn.data} /></DataState>
              </Panel>
              <Panel title="Sprint velocity" to="/analytics">
                <DataState loading={vel.loading} error={vel.error} onRetry={vel.reload}><VelocityChart data={vel.data} /></DataState>
              </Panel>
            </div>
            <div className="grid-2">
              <Panel title="Open blockers" to="/blockers">
                {d.open_blocker_list.length === 0 ? <p className="muted">No unresolved blockers.</p> : (
                  <ul className="list">{d.open_blocker_list.map((b) => <li key={b.id}><span>{b.title}</span><Badge value={b.severity} /></li>)}</ul>
                )}
              </Panel>
              <Panel title="Recent activity">
                {d.recent_activity.length === 0 ? <p className="muted">Activity will appear here as you work.</p> : (
                  <ul className="list">{d.recent_activity.map((a) => <li key={a.id}><span>{a.message}</span><time className="muted">{new Date(a.created_at).toLocaleString()}</time></li>)}</ul>
                )}
              </Panel>
            </div>
          </>
        )}
      </DataState>
    </section>
  );
}
