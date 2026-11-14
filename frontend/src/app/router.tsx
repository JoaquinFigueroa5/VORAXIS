import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppLayout } from "@/components/layout/AppLayout";
import { AnalysisPage } from "@/pages/AnalysisPage";
import { DataSourcesPage } from "@/pages/DataSourcesPage";
import { ExplorerPage } from "@/pages/ExplorerPage";
import { InsightsPage } from "@/pages/InsightsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/explorer" replace /> },
      { path: "explorer", element: <ExplorerPage /> },
      { path: "analysis/:id", element: <AnalysisPage /> },
      { path: "insights", element: <InsightsPage /> },
      { path: "insights/:id", element: <InsightsPage /> },
      { path: "data-sources", element: <DataSourcesPage /> },
      { path: "*", element: <Navigate to="/explorer" replace /> },
    ],
  },
]);
