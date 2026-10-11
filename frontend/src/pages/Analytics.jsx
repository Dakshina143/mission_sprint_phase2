import { useState } from "react";
import { Bar } from "react-chartjs-2";
import { get } from "../api/client";
import { useFetch } from "../hooks";
import { COLORS, baseOptions } from "../charts";
import BurndownChart from "../components/BurndownChart";
import VelocityChart from "../components/VelocityChart";
import { DataState, PageHeader, isDemo } from "../components/ui";

export default function Analytics() {
  const [sprintId, setSprintId] = useState("");
  const sprints = useFetch(() => get("/sprints"), []);
  const burn = useFetch(() => get("/analytics/burndown", { sprint_id: sprintId || undefined }), [sprintId]);
  const vel = useFetch(() => get("/analytics/velocity"), []);
  const comp = useFetch(() => get("/analytics/sprint-completion"), []);
  const mis = useFetch(() => get("/analytics/mission-progress"), []);
  const demo = [...(sprints.data || []), ...(mis.data || []).map((m) => ({ name: m.title }))].some((x) => isDemo(x.name));

  return (
    <section>
      <PageHeader title="Analytics" subtitle="Every figure is calculated from your stored sprint, story and task records.">
        <select value={sprintId} onChange={(e) => setSprintId(e.target.value)} aria-label="Sprint for burndown">
          <option value="">Current or latest sprint</option>
          {(sprints.data || []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </PageHeader>
      {demo && <div className="notice">Some records here are demo data (“[DEMO]”). Their history is minimal because measurements are only recorded when work actually changes.</div>}
      <div className="grid-2">
        <section className="panel"><header><h2>Burndown</h2></header>
          <DataState loading={burn.loading} error={burn.error} onRetry={burn.reload}><BurndownChart data={burn.data} /></DataState></section>
        <section className="panel"><header><h2>Velocity</h2></header>
          <DataState loading={vel.loading} error={vel.error} onRetry={vel.reload}><VelocityChart data={vel.data} /></DataState></section>
      </div>
      <div className="grid-2">
        <section className="panel"><header><h2>Sprint completion</h2></header>
          <DataState loading={comp.loading} error={comp.error} onRetry={comp.reload} empty={comp.data?.length === 0} emptyText="No sprints yet.">
            <div className="chart"><Bar data={{ labels: (comp.data || []).map((s) => s.name),
              datasets: [{ label: "Points completed %", data: (comp.data || []).map((s) => s.points_pct), backgroundColor: COLORS.cyan },
                { label: "Tasks done %", data: (comp.data || []).map((s) => s.tasks_pct), backgroundColor: COLORS.violet }] }}
              options={baseOptions({ scales: { y: { beginAtZero: true, max: 100 } } })} /></div>
          </DataState></section>
        <section className="panel"><header><h2>Mission progress</h2></header>
          <DataState loading={mis.loading} error={mis.error} onRetry={mis.reload} empty={mis.data?.length === 0} emptyText="No missions yet.">
            <div className="chart"><Bar data={{ labels: (mis.data || []).map((m) => m.title),
              datasets: [{ label: "Progress %", data: (mis.data || []).map((m) => m.progress), backgroundColor: COLORS.green }] }}
              options={baseOptions({ indexAxis: "y", scales: { x: { beginAtZero: true, max: 100 } }, plugins: { legend: { display: false } } })} /></div>
          </DataState></section>
      </div>
    </section>
  );
}
