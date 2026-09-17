import { lazy } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/AppShell";
import { TriageView } from "@/views/TriageView";
import { NotFoundView, RouteErrorView } from "@/views/RouteStates";

// The Triage Queue is the landing page and ships in the main bundle. Every
// other screen (and Recharts, which only they use) loads on first visit.
const SandboxView = lazy(() => import("@/views/SandboxView").then((m) => ({ default: m.SandboxView })));
const ReportDetailView = lazy(() =>
  import("@/views/ReportDetailView").then((m) => ({ default: m.ReportDetailView })),
);
const PrecursorMapView = lazy(() =>
  import("@/views/PrecursorMapView").then((m) => ({ default: m.PrecursorMapView })),
);
const LifeSavingRulesView = lazy(() =>
  import("@/views/LifeSavingRulesView").then((m) => ({ default: m.LifeSavingRulesView })),
);
const OntologyView = lazy(() => import("@/views/OntologyView").then((m) => ({ default: m.OntologyView })));

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    errorElement: <RouteErrorView />,
    children: [
      { index: true, element: <TriageView /> },
      { path: "sandbox", element: <SandboxView /> },
      { path: "reports/:id", element: <ReportDetailView /> },
      { path: "map", element: <PrecursorMapView /> },
      { path: "rules", element: <LifeSavingRulesView /> },
      { path: "ontology", element: <OntologyView /> },
      { path: "*", element: <NotFoundView /> },
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
