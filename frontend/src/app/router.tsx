import { createBrowserRouter, Navigate } from "react-router-dom";

import { AnalysisPage } from "@/observatory/AnalysisPage";
import { EvidencePage } from "@/observatory/EvidencePage";
import { ExplorePage } from "@/observatory/ExplorePage";
import { HomePage } from "@/observatory/HomePage";
import { InsightsPage } from "@/observatory/InsightsPage";
import { MethodologyPage } from "@/observatory/MethodologyPage";
import { NewAnalysisPage } from "@/observatory/NewAnalysisPage";
import { Shell } from "@/observatory/Shell";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Shell />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "explorar", element: <ExplorePage /> },
      { path: "nuevo", element: <NewAnalysisPage /> },
      { path: "analisis/:id", element: <AnalysisPage /> },
      { path: "analisis/:id/evidencia/:changeId", element: <EvidencePage /> },
      { path: "insights", element: <InsightsPage /> },
      { path: "metodologia", element: <MethodologyPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
