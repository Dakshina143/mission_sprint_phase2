import { Bar } from "react-chartjs-2";
import { COLORS, baseOptions } from "../charts";

export default function VelocityChart({ data }) {
  if (!data || data.sprints.length === 0) return <p className="muted">Velocity appears after you complete your first sprint.</p>;
  return (
    <>
      <div className="chart">
        <Bar data={{
          labels: data.sprints.map((s) => s.name),
          datasets: [
            { label: "Committed", data: data.sprints.map((s) => s.committed), backgroundColor: COLORS.grey },
            { label: "Delivered", data: data.sprints.map((s) => s.delivered), backgroundColor: COLORS.cyan },
          ],
        }} options={baseOptions({ scales: { y: { beginAtZero: true, title: { display: true, text: "Story points" } } } })} />
      </div>
      <p className="muted small">Average velocity: {data.average_velocity} points per sprint.</p>
    </>
  );
}
