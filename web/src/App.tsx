import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/AppShell";
import { TriageView } from "@/views/TriageView";
import { ReportDetailView } from "@/views/ReportDetailView";
import { PrecursorMapView } from "@/views/PrecursorMapView";
import { LifeSavingRulesView } from "@/views/LifeSavingRulesView";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <TriageView /> },
      { path: "reports/:id", element: <ReportDetailView /> },
      { path: "map", element: <PrecursorMapView /> },
      { path: "rules", element: <LifeSavingRulesView /> },
    ],
  },
]);

export default function App() {
  return (
    <TooltipProvider delayDuration={200} skipDelayDuration={400}>
      <RouterProvider router={router} />
    </TooltipProvider>
  );
}
