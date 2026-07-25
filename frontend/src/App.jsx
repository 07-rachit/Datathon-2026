import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Cases from "./pages/Cases.jsx";
import CaseDetail from "./pages/CaseDetail.jsx";
import MapView from "./pages/MapView.jsx";
import NetworkGraph from "./pages/NetworkGraph.jsx";
import AuditTrail from "./pages/AuditTrail.jsx";
import Admin from "./pages/Admin.jsx";
import Import from "./pages/Import.jsx";
import Offenders from "./pages/Offenders.jsx";
import Insights from "./pages/Insights.jsx";
import Assistant from "./pages/Assistant.jsx";
import MyWork from "./pages/MyWork.jsx";
import Layout from "./components/Layout.jsx";
import { NotificationProvider } from "./context/NotificationContext.jsx";
import { getCurrentUser } from "./lib/api.js";


function ProtectedRoute({ children }) {
  const user = getCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <NotificationProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/cases" element={<Cases />} />
                  <Route path="/cases/:id" element={<CaseDetail />} />
                  <Route path="/map" element={<MapView />} />
                  <Route path="/network" element={<NetworkGraph />} />
                  <Route path="/assistant" element={<Assistant />} />
                  <Route path="/my-work" element={<MyWork />} />
                  <Route path="/audit" element={<AuditTrail />} />
                  <Route path="/admin" element={<Admin />} />
                  <Route path="/import" element={<Import />} />
                  <Route path="/offenders" element={<Offenders />} />
                  <Route path="/insights" element={<Insights />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </NotificationProvider>
  );
}


