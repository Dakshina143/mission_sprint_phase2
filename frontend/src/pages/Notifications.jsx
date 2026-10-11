import { useState } from "react";
import { del, get, parseError, patch, post } from "../api/client";
import { useFetch } from "../hooks";
import { DataState, PageHeader } from "../components/ui";
import { useToast } from "../components/Toast";

const LABEL = { task_assigned: "Assignment", due_date: "Due date", sprint_change: "Sprint", blocker: "Blocker" };

export default function Notifications() {
  const toast = useToast();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { body, data, loading, error, reload } = useFetch(() => get("/notifications", { is_read: unreadOnly ? "false" : undefined }), [unreadOnly]);
  const changed = () => { reload(); window.dispatchEvent(new Event("notifications-changed")); };
  const run = (p) => p.then(changed).catch((e) => toast.error(parseError(e).message));
  return (
    <section>
      <PageHeader title="Notifications" subtitle="Assignments, due dates, sprint changes and new blockers.">
        <label className="check"><input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} /> Unread only</label>
        <button className="btn" disabled={!body?.unread_count} onClick={() => run(post("/notifications/mark-all-read"))}>Mark all as read</button>
      </PageHeader>
      <DataState loading={loading} error={error} onRetry={reload} empty={data?.length === 0} emptyText={unreadOnly ? "You’re all caught up." : "No notifications yet."} emptyHint="They appear when tasks are assigned, deadlines near, sprints change or blockers are reported.">
        <ul className="notif-list">
          {data?.map((n) => (
            <li key={n.id} className={n.is_read ? "read" : "unread"}>
              <div><span className="tag">{LABEL[n.type] || n.type}</span><p>{n.message}</p><time className="muted">{new Date(n.created_at).toLocaleString()}</time></div>
              <div className="row-actions">
                <button className="btn btn-sm" onClick={() => run(patch(`/notifications/${n.id}`, { is_read: !n.is_read }))}>{n.is_read ? "Mark unread" : "Mark read"}</button>
                <button className="btn btn-sm btn-danger" onClick={() => run(del(`/notifications/${n.id}`))}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      </DataState>
    </section>
  );
}
