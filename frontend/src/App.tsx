import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { useEffect } from "react";
import { useAuthStore } from "@/lib/auth";
import { initSync } from "@/lib/sync";
import { useDirection } from "@/hooks/useDirection";
import "@/lib/i18n";
import Login from "@/pages/Login";
import Home from "@/pages/Home";
import CapturePage from "@/features/capture/pages/CapturePage";
import DraftReviewPage from "@/features/capture/pages/DraftReviewPage";
import ReviewQueuePage from "@/features/review/pages/ReviewQueuePage";
import ReviewDetailPage from "@/features/review/pages/ReviewDetailPage";
import AiMetricsPage from "@/features/review/pages/AiMetricsPage";
import AnalyticsDashboard from "@/features/analytics/pages/AnalyticsDashboard";
import IntegrationSettings from "@/features/integrations/pages/IntegrationSettings";
import AnomalyMetrics from "@/features/integrations/pages/AnomalyMetrics";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function AccountantRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (user?.role !== "accountant" && user?.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (user?.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const logout = useAuthStore((s) => s.logout);

  useDirection();

  useEffect(() => {
    initSync();
  }, []);

  useEffect(() => {
    if (isAuthenticated && !accessToken) {
      fetch("/api/v1/auth/refresh", {
        method: "POST",
        credentials: "include",
      })
        .then((res) => {
          if (res.ok) return res.json();
          throw new Error("refresh failed");
        })
        .then((data) => setAccessToken(data.access_token))
        .catch(() => logout());
    }
  }, [isAuthenticated, accessToken, setAccessToken, logout]);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Home />
            </ProtectedRoute>
          }
        />
        <Route
          path="/capture"
          element={
            <ProtectedRoute>
              <CapturePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/drafts"
          element={
            <ProtectedRoute>
              <DraftReviewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/review"
          element={
            <AccountantRoute>
              <ReviewQueuePage />
            </AccountantRoute>
          }
        />
        <Route
          path="/review/:expenseId"
          element={
            <AccountantRoute>
              <ReviewDetailPage />
            </AccountantRoute>
          }
        />
        <Route
          path="/review/metrics"
          element={
            <AdminRoute>
              <AiMetricsPage />
            </AdminRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <AccountantRoute>
              <AnalyticsDashboard />
            </AccountantRoute>
          }
        />
        <Route
          path="/settings/integrations"
          element={
            <AccountantRoute>
              <IntegrationSettings />
            </AccountantRoute>
          }
        />
        <Route
          path="/settings/anomaly-metrics"
          element={
            <AdminRoute>
              <AnomalyMetrics />
            </AdminRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
