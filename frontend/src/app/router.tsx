import { createBrowserRouter, Navigate } from "react-router-dom";

import { AnalysisPage } from "@/observatory/AnalysisPage";
import { ExplorePage } from "@/observatory/ExplorePage";
import { HomePage } from "@/observatory/HomePage";
import { NewAnalysisPage } from "@/observatory/NewAnalysisPage";
import { Shell } from "@/observatory/Shell";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Shell />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "analisis/:id", element: <AnalysisPage /> },
      { path: "nuevo", element: <NewAnalysisPage /> },
      { path: "explorar", element: <ExplorePage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
