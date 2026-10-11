import { ArcElement, BarElement, CategoryScale, Chart, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip } from "chart.js";

Chart.register(ArcElement, BarElement, CategoryScale, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip);
Chart.defaults.color = "#9aa4af";
Chart.defaults.borderColor = "#2b3036";
Chart.defaults.font.family = "'IBM Plex Sans', system-ui, sans-serif";

export const COLORS = { cyan: "#22e5ff", amber: "#ffb454", green: "#5ce6a1", red: "#ff5c70", grey: "#59626d", violet: "#a58bff" };

export const baseOptions = (extra = {}) => ({ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } }, ...extra });
