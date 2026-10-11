import { useEffect, useMemo, useState } from "react";
import { del, get, parseError, patch, post } from "../api/client";
import { useFetch } from "../hooks";
import FormModal from "./FormModal";
import { DataState, PageHeader } from "./ui";
import { useToast } from "./Toast";

const NONE = { value: "", label: "None" };

/**
 * Generic list + create/edit/delete page backed by a REST resource.
 * refs: { fieldName: { endpoint, label: row => string } } fills select options from other resources.
 */
export default function CrudPage({ title, subtitle, noun, endpoint, fields, columns, filters = [], refs = {},
  searchable = true, rowActions, headerExtras, summary, emptyText, emptyHint, createDefaults = {}, onChanged }) {
  const toast = useToast();
  const [q, setQ] = useState("");
  const [filterValues, setFilterValues] = useState({});
  const [editing, setEditing] = useState(null); // null | {} (create) | row
  const [refData, setRefData] = useState({});

  const params = useMemo(() => ({ q: q || undefined, ...Object.fromEntries(Object.entries(filterValues).filter(([, v]) => v)) }), [q, filterValues]);
  const { data: rows, loading, error, reload } = useFetch(() => get(`/${endpoint}`, params), [endpoint, JSON.stringify(params)]);

  useEffect(() => {
    Object.entries(refs).forEach(([name, cfg]) =>
      get(`/${cfg.endpoint}`).then((r) => setRefData((d) => ({ ...d, [name]: r.data })))
        .catch((e) => toast.error(`Could not load ${cfg.endpoint}: ${parseError(e).message}`)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const formFields = fields.map((f) => f.ref
    ? { ...f, type: "select", numeric: true, options: [NONE, ...(refData[f.ref] || []).map((r) => ({ value: r.id, label: refs[f.ref].label(r) }))] }
    : f);

  const refresh = () => { reload(); onChanged?.(); };

  async function save(payload) {
    if (editing?.id) await patch(`/${endpoint}/${editing.id}`, payload); else await post(`/${endpoint}`, payload);
    toast.success(`${noun} ${editing?.id ? "updated" : "created"}`);
    refresh();
  }

  async function remove(row) {
    if (!window.confirm(`Delete this ${noun.toLowerCase()}? This cannot be undone.`)) return;
    try { await del(`/${endpoint}/${row.id}`); toast.success(`${noun} deleted`); refresh(); }
    catch (e) { toast.error(parseError(e).message); }
  }

  return (
    <section>
      <PageHeader title={title} subtitle={subtitle}>
        {headerExtras}
        <button className="btn btn-primary" onClick={() => setEditing({ ...createDefaults })}>New {noun.toLowerCase()}</button>
      </PageHeader>
      <div className="toolbar">
        {searchable && <input type="search" placeholder={`Search ${title.toLowerCase()}`} value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />}
        {filters.map((f) => (
          <select key={f.name} value={filterValues[f.name] || ""} aria-label={f.label}
            onChange={(e) => setFilterValues((v) => ({ ...v, [f.name]: e.target.value }))}>
            <option value="">{f.label}: all</option>
            {f.options.map((o) => <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
          </select>
        ))}
        {summary && rows && <span className="summary">{summary(rows)}</span>}
      </div>
      <DataState loading={loading} error={error} onRetry={reload} empty={rows && rows.length === 0}
        emptyText={q || Object.keys(params).length > 1 ? `No ${title.toLowerCase()} match these filters.` : emptyText || `No ${title.toLowerCase()} yet.`}
        emptyHint={emptyHint || `Use “New ${noun.toLowerCase()}” to add one.`}>
        <div className="table-wrap">
          <table>
            <thead><tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}<th /></tr></thead>
            <tbody>
              {rows?.map((row, i) => (
                <tr key={row.id}>
                  {columns.map((c) => <td key={c.key} data-label={c.label}>{c.render ? c.render(row, refData) : row[c.key] ?? "—"}</td>)}
                  <td className="row-actions">
                    {rowActions?.(row, { reload: refresh, index: i, rows, refData, filtered: Object.keys(params).length > 0 })}
                    <button className="btn btn-sm" onClick={() => setEditing(row)}>Edit</button>
                    <button className="btn btn-sm btn-danger" onClick={() => remove(row)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataState>
      {editing && (
        <FormModal title={editing.id ? `Edit ${noun.toLowerCase()}` : `New ${noun.toLowerCase()}`} fields={formFields} initial={editing}
          onSubmit={save} onClose={() => setEditing(null)} submitLabel={editing.id ? "Save changes" : `Create ${noun.toLowerCase()}`} />
      )}
    </section>
  );
}
