import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

const client = axios.create({ baseURL: API_BASE_URL, timeout: 10000 });

/** Turns any axios failure into a readable message plus optional per-field errors. */
export function parseError(err) {
  if (err.response?.data?.error) {
    const { message, details } = err.response.data.error;
    return { message, fields: details && typeof details === "object" ? details : null };
  }
  if (err.code === "ECONNABORTED") return { message: "The API took too long to respond.", fields: null };
  if (err.request) return { message: `Cannot reach the API at ${API_BASE_URL}. Is the backend running?`, fields: null };
  return { message: err.message || "Unexpected error", fields: null };
}

export const get = (url, params) => client.get(url, { params }).then((r) => r.data);
export const post = (url, body) => client.post(url, body ?? {}).then((r) => r.data);
export const patch = (url, body) => client.patch(url, body).then((r) => r.data);
export const del = (url) => client.delete(url).then((r) => r.data);

export async function downloadCsv(kind) {
  const res = await client.get(`/reports/${kind}`, { params: { format: "csv" }, responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${kind}_report.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default client;
