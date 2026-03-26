import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Index from "./pages/Index.tsx";
import ThreatMapPage from "./pages/ThreatMapPage.tsx";
import AlertsPage from "./pages/AlertsPage.tsx";
import CamerasPage from "./pages/CamerasPage.tsx";
import AnalyticsPage from "./pages/AnalyticsPage.tsx";
import NotificationsPage from "./pages/NotificationsPage.tsx";
import ReportsPage from "./pages/ReportsPage.tsx";
import SettingsPage from "./pages/SettingsPage.tsx";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/threat-map" element={<ThreatMapPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/cameras" element={<CamerasPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
