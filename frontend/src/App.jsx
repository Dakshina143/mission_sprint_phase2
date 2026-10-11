import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Missions from "./pages/Missions";
import Backlog from "./pages/Backlog";
import Sprints from "./pages/Sprints";
import Kanban from "./pages/Kanban";
import Analytics from "./pages/Analytics";
import Blockers from "./pages/Blockers";
import Retrospectives from "./pages/Retrospectives";
import Notifications from "./pages/Notifications";
import Reports from "./pages/Reports";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="missions" element={<Missions />} />
        <Route path="backlog" element={<Backlog />} />
        <Route path="sprints" element={<Sprints />} />
        <Route path="board" element={<Kanban />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="blockers" element={<Blockers />} />
        <Route path="retrospectives" element={<Retrospectives />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="reports" element={<Reports />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
