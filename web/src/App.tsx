import { Navigate, Route, Routes } from "react-router-dom";
import { ToastHost } from "./components/ToastHost";
import { useAuth } from "./state/auth";
import { AlertsPage } from "./pages/AlertsPage";
import { CanteenPage } from "./pages/CanteenPage";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { CommercialPage } from "./pages/CommercialPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { FinancePage } from "./pages/FinancePage";
import { InboxPage } from "./pages/InboxPage";
import { JobWorkPage } from "./pages/JobWorkPage";
import { LoginPage } from "./pages/LoginPage";
import { MastersPage } from "./pages/MastersPage";
import { MorePage } from "./pages/MorePage";
import { OfflinePage } from "./pages/OfflinePage";
import { ReportsPage } from "./pages/ReportsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StockPage } from "./pages/StockPage";
import { VehicleEntryPage } from "./pages/VehicleEntryPage";
import { WeighmentPage } from "./pages/WeighmentPage";
import { YardFlowPage } from "./pages/YardFlowPage";

function Private({ children }: { children: React.ReactNode }) {
  const token = useAuth((s) => s.token);
  const user = useAuth((s) => s.user);
  if (!token) return <Navigate to="/login" replace />;
  if (user?.must_change_password) return <Navigate to="/change-password" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <>
    <ToastHost />
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/change-password" element={<ChangePasswordPage />} />
      <Route
        path="/"
        element={
          <Private>
            <DashboardPage />
          </Private>
        }
      />
      <Route
        path="/yard"
        element={
          <Private>
            <YardFlowPage />
          </Private>
        }
      />
      <Route
        path="/yard/:transactionPk"
        element={
          <Private>
            <YardFlowPage />
          </Private>
        }
      />
      <Route path="/vehicle-entry" element={<Navigate to="/yard" replace />} />
      <Route
        path="/vehicle-entry-legacy"
        element={
          <Private>
            <VehicleEntryPage />
          </Private>
        }
      />
      <Route
        path="/weighment"
        element={
          <Private>
            <WeighmentPage />
          </Private>
        }
      />
      <Route
        path="/weighment/:transactionPk"
        element={
          <Private>
            <WeighmentPage />
          </Private>
        }
      />
      <Route
        path="/documents"
        element={
          <Private>
            <DocumentsPage />
          </Private>
        }
      />
      <Route
        path="/documents/:transactionPk"
        element={
          <Private>
            <DocumentsPage />
          </Private>
        }
      />
      <Route
        path="/stock"
        element={
          <Private>
            <StockPage />
          </Private>
        }
      />
      <Route
        path="/stock/:transactionPk"
        element={
          <Private>
            <StockPage />
          </Private>
        }
      />
      <Route
        path="/job-work"
        element={
          <Private>
            <JobWorkPage />
          </Private>
        }
      />
      <Route
        path="/inbox"
        element={
          <Private>
            <InboxPage />
          </Private>
        }
      />
      <Route
        path="/alerts"
        element={
          <Private>
            <AlertsPage />
          </Private>
        }
      />
      <Route
        path="/equipment"
        element={
          <Private>
            <EquipmentPage />
          </Private>
        }
      />
      <Route
        path="/canteen"
        element={
          <Private>
            <CanteenPage />
          </Private>
        }
      />
      <Route
        path="/reports"
        element={
          <Private>
            <ReportsPage />
          </Private>
        }
      />
      <Route
        path="/commercial"
        element={
          <Private>
            <CommercialPage />
          </Private>
        }
      />
      <Route
        path="/finance"
        element={
          <Private>
            <FinancePage />
          </Private>
        }
      />
      <Route
        path="/offline"
        element={
          <Private>
            <OfflinePage />
          </Private>
        }
      />
      <Route
        path="/more"
        element={
          <Private>
            <MorePage />
          </Private>
        }
      />
      <Route
        path="/masters"
        element={
          <Private>
            <MastersPage />
          </Private>
        }
      />
      <Route
        path="/settings"
        element={
          <Private>
            <SettingsPage />
          </Private>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </>
  );
}
