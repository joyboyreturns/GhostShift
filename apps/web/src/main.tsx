import React from "react";
import ReactDOM from "react-dom/client";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useMutation,
} from "@tanstack/react-query";
import { BrowserRouter, NavLink, Route, Routes, Link } from "react-router-dom";
import {
  Ghost,
  BookOpen,
  Upload,
  Play,
  ScrollText,
  Library as LibraryIcon,
} from "lucide-react";
import { api } from "./lib/api";
import { Button } from "./components/ui/button";
import { Home } from "./routes/Home";
import {
  Bat,
  Cobweb,
  Graveyard,
  Moon,
  Pumpkin,
  Tombstone,
} from "./components/decor/Spooky";
const Studio = React.lazy(() =>
  import("./routes/Studio").then((module) => ({ default: module.Studio })),
);
import { Import } from "./routes/Import";
const SimulationStart = React.lazy(() =>
  import("./routes/SimulationStart").then((module) => ({
    default: module.SimulationStart,
  })),
);
const SimulationRoom = React.lazy(() =>
  import("./routes/SimulationRoom").then((module) => ({
    default: module.SimulationRoom,
  })),
);
const SessionReport = React.lazy(() =>
  import("./routes/SessionReport").then((module) => ({
    default: module.SessionReport,
  })),
);
const PolicyReview = React.lazy(() =>
  import("./routes/PolicyReview").then((module) => ({
    default: module.PolicyReview,
  })),
);
const ProposalDetail = React.lazy(() =>
  import("./routes/ProposalDetail").then((module) => ({
    default: module.ProposalDetail,
  })),
);
const Library = React.lazy(() =>
  import("./routes/Library").then((module) => ({ default: module.Library })),
);
const ScenarioCreate = React.lazy(() =>
  import("./routes/ScenarioCreate").then((module) => ({
    default: module.ScenarioCreate,
  })),
);
const VersionHistory = React.lazy(() =>
  import("./routes/VersionHistory").then((module) => ({
    default: module.VersionHistory,
  })),
);
const ReplayLab = React.lazy(() =>
  import("./routes/ReplayLab").then((module) => ({
    default: module.ReplayLab,
  })),
);
const ComparisonReport = React.lazy(() =>
  import("./routes/ComparisonReport").then((module) => ({
    default: module.ComparisonReport,
  })),
);
const Guide = React.lazy(() =>
  import("./routes/Guide").then((module) => ({ default: module.Guide })),
);
const SourceDocument = React.lazy(() =>
  import("./routes/SourceDocument").then((module) => ({
    default: module.SourceDocument,
  })),
);
import "./styles.css";
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});
export function App() {
  // Bootstrap before route requests so a new visitor's first concurrent API reads
  // all receive the same anonymous workspace cookie.
  const catalog = useQuery({ queryKey: ["catalog"], queryFn: api.catalog });
  const resetDemo = useMutation({
    mutationFn: api.resetDemo,
    onSuccess: () => window.location.assign("/"),
  });
  return (
    <>
      <div className="haunt" aria-hidden="true">
        <div className="haunt-stars" />
        <div className="haunt-grain" />
        <Moon className="haunt-moon" />
        <Cobweb className="haunt-web haunt-web-left" />
        <Cobweb className="haunt-web haunt-web-right" />
        <Bat className="haunt-bat haunt-bat-1" />
        <Bat className="haunt-bat haunt-bat-2" />
        <Bat className="haunt-bat haunt-bat-3" />
      </div>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="app-header">
        <Link to="/" className="brand">
          <span className="brand-icon">
            <Ghost size={23} />
          </span>
          <span className="brand-word">
            Ghost<em>Shift</em>
          </span>
          <span className="preview-label">
            <Pumpkin className="chip-pumpkin" />
            KIROWEEN 2026 · PREVIEW
          </span>
        </Link>
        <nav aria-label="Main navigation">
          <NavLink to="/studio">
            <BookOpen size={16} />
            Source Studio
          </NavLink>
          <NavLink to="/library">
            <LibraryIcon size={16} />
            Library
          </NavLink>
          <NavLink to="/simulation">
            <Play size={16} />
            Simulation
          </NavLink>
          <NavLink to="/import">
            <Upload size={16} />
            Import
          </NavLink>
        </nav>
        <Link to="/guide" className="header-note">
          <ScrollText size={14} />
          Getting started
        </Link>
      </header>
      <main id="main">
        {catalog.data?.workspace && (
          <aside className="demo-notice" aria-label="Temporary demo workspace">
            <span className="badge amber">Temporary demo</span>
            <p>
              {catalog.data.workspace.notice} Expires{" "}
              {new Date(
                catalog.data.workspace.expires_at * 1000,
              ).toLocaleString()}
              .
            </p>
            <Button
              variant="outline"
              disabled={resetDemo.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    "Start a fresh temporary workspace? Export your reports first. You will lose access to this workspace in this browser.",
                  )
                )
                  resetDemo.mutate();
              }}
            >
              Start fresh workspace
            </Button>
            {resetDemo.error && <p role="alert">{resetDemo.error.message}</p>}
          </aside>
        )}
        {catalog.isPending ? (
          <SpiritLoader label="Opening your workspace…" />
        ) : catalog.error && !catalog.data ? (
          <section className="message" role="alert">
            <h1>Workspace unavailable</h1>
            <p>{catalog.error.message}</p>
            <Button onClick={() => void catalog.refetch()}>Retry</Button>
          </section>
        ) : (
          <React.Suspense
            fallback={<SpiritLoader label="Summoning workspace…" />}
          >
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/studio" element={<Studio />} />
              <Route path="/library" element={<Library />} />
              <Route path="/sources/:documentId" element={<SourceDocument />} />
              <Route path="/guide" element={<Guide />} />
              <Route path="/history/:playbookId" element={<VersionHistory />} />
              <Route path="/scenarios/new" element={<ScenarioCreate />} />
              <Route path="/replay/:sessionId" element={<ReplayLab />} />
              <Route path="/reports/compare" element={<ComparisonReport />} />
              <Route path="/import" element={<Import />} />
              <Route path="/review/:playbookId" element={<PolicyReview />} />
              <Route
                path="/proposals/:proposalId"
                element={<ProposalDetail />}
              />
              <Route path="/simulation" element={<SimulationStart />} />
              <Route
                path="/simulation/:sessionId"
                element={<SimulationRoom />}
              />
              <Route
                path="/simulation/:sessionId/report"
                element={<SessionReport />}
              />
              <Route
                path="*"
                element={
                  <section className="message lost-ghost">
                    <div className="lost-scene">
                      <Tombstone lines={["THIS PAGE", "404"]} />
                      <Ghost aria-hidden="true" className="lost-ghost-icon" />
                    </div>
                    <span className="eyebrow">404 / Nothing haunts here</span>
                    <h1>This page gave up the ghost.</h1>
                    <p>
                      The address does not match any page in this workspace.
                    </p>
                    <Button asChild>
                      <Link to="/">Return home</Link>
                    </Button>
                  </section>
                }
              />
            </Routes>
          </React.Suspense>
        )}
      </main>
      <Graveyard className="footer-graveyard" />
      <footer className="app-footer">
        <span className="footer-brand">
          <Ghost size={14} aria-hidden="true" /> GhostShift · Kiroween 2026
        </span>
        <Link to="/guide">Getting started ↗</Link>
        <span>Evidence first. Human judgment always.</span>
      </footer>
    </>
  );
}
function SpiritLoader({ label }: { label: string }) {
  return (
    <div className="message spirit-loader" role="status">
      <Ghost aria-hidden="true" />
      {label}
    </div>
  );
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
