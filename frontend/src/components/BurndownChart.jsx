import { Line } from "react-chartjs-2";
import { COLORS, baseOptions } from "../charts";

export default function BurndownChart({ data }) {
  if (!data) return <p className="muted">No active or completed sprint yet. Start a sprint to see its burndown.</p>;
  const hasActual = data.actual.some((v) => v !== null);
  return (
    <>
      <div className="chart">
        <Line data={{
          labels: data.labels.map((l) => l.slice(5)),
          datasets: [
            { label: "Ideal (calculated)", data: data.ideal, borderColor: COLORS.grey, borderDash: [6, 6], pointRadius: 0, tension: 0 },
            { label: "Remaining points (measured)", data: data.actual, borderColor: COLORS.cyan, backgroundColor: "rgba(34,229,255,.12)", fill: true, spanGaps: false, tension: 0.15, pointRadius: 3 },
          ],
        }} options={baseOptions({ scales: { y: { beginAtZero: true, title: { display: true, text: "Story points" } } } })} />
      </div>
      {!hasActual && <p className="muted">No measurements recorded for this sprint yet. Points are recorded whenever stories or tasks change.</p>}
      <p className="muted small">{data.note}</p>
    </>
  );
}
