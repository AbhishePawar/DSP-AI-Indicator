"use client";

import {
  createContext,
  memo,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import {
  buildCollaborationOverview,
  buildRecentActivity,
  collaborationPinnedCatalog,
  COLLAB_TRUST,
} from "@/lib/advisor/collaborationModels";
import {
  getCollaborationSnapshot,
  navLabelForHref,
  recordNavigation,
  resolveNavId,
  setMainPanelWidthPct,
  setSelectedWorkspace,
  setSidebarCollapsed,
  setWorkspaceFilter,
  subscribeCollaboration,
  togglePinnedItem,
  toggleSidebarCollapsed,
} from "@/lib/advisor/collaborationSession";
import {
  COLLAB_NAV,
  type CollaborationSessionState,
} from "@/lib/advisor/collaborationTypes";
import { listTasks } from "@/lib/advisor/advisorViewModel";

/* ── Session provider (memoized snapshot) ───────────────────────── */

const CollaborationSessionContext = createContext<CollaborationSessionState | null>(
  null,
);

export function CollaborationSessionProvider({ children }: { children: ReactNode }) {
  const snapshot = useSyncExternalStore(
    subscribeCollaboration,
    getCollaborationSnapshot,
    getCollaborationSnapshot,
  );
  return (
    <CollaborationSessionContext.Provider value={snapshot}>
      {children}
    </CollaborationSessionContext.Provider>
  );
}

export function useCollaborationSession(): CollaborationSessionState {
  const store = useSyncExternalStore(
    subscribeCollaboration,
    getCollaborationSnapshot,
    getCollaborationSnapshot,
  );
  const ctx = useContext(CollaborationSessionContext);
  return ctx ?? store;
}

/* ── Overview cards ─────────────────────────────────────────────── */

export const WorkspaceOverviewCard = memo(function WorkspaceOverviewCard() {
  const overview = useMemo(() => buildCollaborationOverview(), []);
  return (
    <Card>
      <CardHeader
        title="Workspace Overview"
        description="Summaries from existing DSP advisor demos"
      />
      <CardBody className="grid gap-3 sm:grid-cols-2">
        {(
          [
            ["Workspace", overview.workspaceSummary],
            ["Research", overview.researchSummary],
            ["Reviews", overview.reviewSummary],
            ["Portfolios", overview.portfolioSummary],
            ["Presentations", overview.presentationSummary],
            ["Session state", overview.sessionStateSummary],
          ] as const
        ).map(([label, text]) => (
          <div
            key={label}
            className="rounded-md border border-[var(--border)] bg-[var(--surface-2)]/40 p-3"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              {label}
            </p>
            <p className="mt-1 text-sm">{text}</p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
});

export const RecentActivityCard = memo(function RecentActivityCard() {
  const items = useMemo(() => buildRecentActivity(), []);
  return (
    <Card>
      <CardHeader title="Recent Activity" description="Demo timeline — not live" />
      <CardBody>
        <ul className="space-y-2" aria-label="Recent collaboration activity">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                href={item.href}
                className="flex min-h-11 flex-col gap-0.5 rounded-md px-2 py-2 hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="text-sm">{item.label}</span>
                <span className="flex items-center gap-2 text-xs text-[var(--muted)]">
                  <Badge>{item.kind}</Badge>
                  <time dateTime={item.at}>{item.at.slice(0, 10)}</time>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
});

export const SessionSummaryCard = memo(function SessionSummaryCard() {
  const session = useCollaborationSession();
  const pinned = useMemo(
    () =>
      collaborationPinnedCatalog.filter((p) =>
        session.pinnedItemIds.includes(p.id),
      ),
    [session.pinnedItemIds],
  );
  return (
    <Card>
      <CardHeader
        title="Session State Summary"
        description="In-memory only — clears on refresh"
      />
      <CardBody className="space-y-3 text-sm">
        <p>
          Workspace:{" "}
          <Badge>
            {session.selectedWorkspace === "my" ? "My Workspace" : "Shared Workspace"}
          </Badge>
        </p>
        <p>
          Sidebar:{" "}
          <Badge>{session.sidebarCollapsed ? "Collapsed" : "Expanded"}</Badge>
          {" · "}
          Main width: <Badge>{session.mainPanelWidthPct}%</Badge>
        </p>
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-[var(--muted)]">
            Pinned items
          </p>
          <ul className="flex flex-wrap gap-2" aria-label="Pinned collaboration items">
            {pinned.length === 0 ? (
              <li className="text-[var(--muted)]">None pinned</li>
            ) : (
              pinned.map((p) => (
                <li key={p.id}>
                  <Link
                    href={p.href}
                    className="rounded-md border border-[var(--border)] px-2 py-1 text-xs hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  >
                    {p.label}
                  </Link>
                </li>
              ))
            )}
          </ul>
        </div>
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-[var(--muted)]">
            Recent navigation
          </p>
          {session.recentNavigation.length === 0 ? (
            <p className="text-[var(--muted)]">Navigate team sections to populate</p>
          ) : (
            <ul className="space-y-1" aria-label="Recent team navigation">
              {session.recentNavigation.map((n) => (
                <li key={`${n.href}-${n.at}`}>
                  <Link
                    href={n.href}
                    className="text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  >
                    {n.label}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardBody>
    </Card>
  );
});

/* ── Header / Sidebar / Layout ──────────────────────────────────── */

export const TeamHeader = memo(function TeamHeader({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  const session = useCollaborationSession();
  const pathname = usePathname();
  const navId = resolveNavId(pathname);
  const crumb = COLLAB_NAV.find((n) => n.id === navId);

  return (
    <header
      className="sticky top-0 z-20 space-y-3 border-b border-[var(--border)] bg-[var(--bg)]/95 pb-3 backdrop-blur-sm"
      aria-label="Team collaboration header"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-[var(--muted)]">
            Team Collaboration
          </p>
          <h1 className="font-[family-name:var(--font-display)] text-3xl tracking-tight">
            {title}
          </h1>
          {description ? (
            <p className="mt-1 text-[var(--muted)]">{description}</p>
          ) : null}
        </div>
        <div
          className="flex flex-wrap gap-2"
          role="group"
          aria-label="Workspace selection"
        >
          <Button
            variant={session.selectedWorkspace === "my" ? "primary" : "secondary"}
            size="sm"
            aria-pressed={session.selectedWorkspace === "my"}
            onClick={() => setSelectedWorkspace("my")}
          >
            My Workspace
          </Button>
          <Button
            variant={session.selectedWorkspace === "shared" ? "primary" : "secondary"}
            size="sm"
            aria-pressed={session.selectedWorkspace === "shared"}
            onClick={() => setSelectedWorkspace("shared")}
          >
            Shared Workspace
          </Button>
          <Button
            variant="ghost"
            size="sm"
            aria-expanded={!session.sidebarCollapsed}
            aria-controls="team-sidebar"
            onClick={() => toggleSidebarCollapsed()}
          >
            {session.sidebarCollapsed ? "Show nav" : "Hide nav"}
          </Button>
        </div>
      </div>
      <nav aria-label="Breadcrumb" className="text-sm text-[var(--muted)]">
        <ol className="flex flex-wrap items-center gap-1">
          <li>
            <Link
              href="/advisor"
              className="hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              Advisor
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li>
            <Link
              href="/advisor/team"
              className="hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              Team
            </Link>
          </li>
          {crumb && crumb.href !== "/advisor/team" ? (
            <>
              <li aria-hidden="true">/</li>
              <li aria-current="page" className="text-[var(--fg)]">
                {crumb.label}
              </li>
            </>
          ) : (
            <>
              <li aria-hidden="true">/</li>
              <li aria-current="page" className="text-[var(--fg)]">
                Overview
              </li>
            </>
          )}
        </ol>
      </nav>
    </header>
  );
});

export const TeamSidebar = memo(function TeamSidebar() {
  const pathname = usePathname();
  const session = useCollaborationSession();
  const filter = session.workspaceFilter.trim().toLowerCase();

  const links = useMemo(() => {
    if (!filter) return COLLAB_NAV;
    return COLLAB_NAV.filter((n) => n.label.toLowerCase().includes(filter));
  }, [filter]);

  if (session.sidebarCollapsed) return null;

  return (
    <aside
      id="team-sidebar"
      className="sticky top-24 flex max-h-[calc(100vh-7rem)] w-full shrink-0 flex-col gap-3 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 lg:w-56"
      aria-label="Team collaboration navigation"
    >
      <label className="block text-xs text-[var(--muted)]">
        Filter sections
        <input
          type="search"
          value={session.workspaceFilter}
          onChange={(e) => setWorkspaceFilter(e.target.value)}
          className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          placeholder="Quick filter…"
          aria-label="Filter team navigation"
        />
      </label>
      <nav aria-label="Team sections" className="flex flex-col gap-1">
        {links.map((link) => {
          const active =
            link.href === "/advisor/team"
              ? pathname === link.href
              : pathname === link.href || pathname.startsWith(`${link.href}/`);
          return (
            <Link
              key={link.id}
              href={link.href}
              aria-current={active ? "page" : undefined}
              onClick={() => recordNavigation(link.href, link.label)}
              className={`min-h-11 rounded-md px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                active
                  ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
      <div>
        <p className="mb-1 text-xs uppercase tracking-wide text-[var(--muted)]">
          Pinned Items
        </p>
        <ul className="space-y-1" aria-label="Toggle pinned items">
          {collaborationPinnedCatalog.map((pin) => {
            const pinned = session.pinnedItemIds.includes(pin.id);
            return (
              <li key={pin.id}>
                <button
                  type="button"
                  aria-pressed={pinned}
                  onClick={() => togglePinnedItem(pin.id)}
                  className="flex min-h-11 w-full items-center justify-between rounded-md px-2 text-left text-xs text-[var(--muted)] hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                >
                  <span>{pin.label}</span>
                  <Badge>{pinned ? "Pinned" : "Pin"}</Badge>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
});

export function WorkspaceContainer({
  children,
  widthPct,
}: {
  children: ReactNode;
  widthPct: number;
}) {
  return (
    <div
      className="min-w-0 flex-1 space-y-4 overflow-y-auto"
      style={{ flexBasis: `${widthPct}%` }}
      role="region"
      aria-label="Team workspace content"
    >
      {children}
    </div>
  );
}

function ContextNavPanel() {
  const session = useCollaborationSession();
  const pathname = usePathname();
  const quick = useMemo(
    () => [
      { href: "/advisor/team/dashboard", label: "Collab Dashboard" },
      { href: "/advisor/team/shared-research", label: "Shared Research" },
      { href: "/advisor/team/shared-portfolios", label: "Shared Portfolios" },
      { href: "/advisor/team/shared-reviews", label: "Shared Reviews" },
      { href: "/advisor/team/shared-reviews/board", label: "Assignments" },
      { href: "/advisor/presentations", label: "Presentations" },
      { href: "/advisor/reviews", label: "Client Reviews" },
      { href: "/advisor/team/validation", label: "Validation" },
    ],
    [],
  );

  if (!session.expandedPanels.context) return null;

  return (
    <aside
      className="sticky top-24 hidden max-h-[calc(100vh-7rem)] w-48 shrink-0 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 xl:block"
      aria-label="Context navigation"
    >
      <p className="mb-2 text-xs uppercase tracking-wide text-[var(--muted)]">
        Quick Navigation
      </p>
      <nav className="flex flex-col gap-1" aria-label="Quick links to advisor modules">
        {quick.map((q) => (
          <Link
            key={q.href}
            href={q.href}
            className="min-h-11 rounded-md px-2 py-2 text-sm text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            {q.label}
          </Link>
        ))}
      </nav>
      <p className="mt-4 text-xs text-[var(--muted)]">
        Context: {navLabelForHref(pathname)}
      </p>
    </aside>
  );
}

function ResizeHandle() {
  const session = useCollaborationSession();
  const dragging = useRef(false);

  const onPointerMove = useCallback((e: PointerEvent) => {
    if (!dragging.current) return;
    const pct = (e.clientX / window.innerWidth) * 100;
    // Rough main panel share after sidebar (~14rem ≈ 14%)
    setMainPanelWidthPct(pct - 14);
  }, []);

  const onPointerUp = useCallback(() => {
    dragging.current = false;
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerUp);
  }, [onPointerMove]);

  return (
    <div
      role="slider"
      tabIndex={0}
      aria-label="Resize main workspace panel"
      aria-valuemin={40}
      aria-valuemax={85}
      aria-valuenow={session.mainPanelWidthPct}
      className="hidden h-auto w-2 shrink-0 cursor-col-resize rounded-full bg-[var(--border)] hover:bg-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] lg:block"
      onPointerDown={(e) => {
        dragging.current = true;
        (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
        window.addEventListener("pointermove", onPointerMove);
        window.addEventListener("pointerup", onPointerUp);
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          setMainPanelWidthPct(session.mainPanelWidthPct - 2);
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          setMainPanelWidthPct(session.mainPanelWidthPct + 2);
        }
      }}
    />
  );
}

function CollaborationLayoutInner({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  const session = useCollaborationSession();
  const pathname = usePathname();

  useEffect(() => {
    const label = navLabelForHref(pathname);
    if (pathname.startsWith("/advisor/team")) {
      recordNavigation(pathname, label);
    }
  }, [pathname]);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const apply = () => {
      if (mq.matches) setSidebarCollapsed(true);
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  return (
    <div className="space-y-4">
      <p
        role="note"
        className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm"
      >
        {COLLAB_TRUST}
      </p>
      <TeamHeader title={title} description={description} />
      <div className="flex flex-col gap-3 lg:flex-row">
        <TeamSidebar />
        <ResizeHandle />
        <WorkspaceContainer widthPct={session.mainPanelWidthPct}>
          {children}
        </WorkspaceContainer>
        <ContextNavPanel />
      </div>
    </div>
  );
}

export function CollaborationLayout({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <CollaborationSessionProvider>
      <CollaborationLayoutInner title={title} description={description}>
        {children}
      </CollaborationLayoutInner>
    </CollaborationSessionProvider>
  );
}

/* ── Section workspaces ─────────────────────────────────────────── */

export const TeamWorkspace = memo(function TeamWorkspace() {
  return (
    <CollaborationLayout
      title="Team Collaboration"
      description="Shared navigation shell · session state · reusable DSP demos · EPIC complete"
    >
      <div className="grid gap-4">
        <Card>
          <CardHeader
            title="Collaboration Dashboard"
            description="Unified team visibility — Sprint 7.5"
          />
          <CardBody className="flex flex-wrap gap-2">
            <Link href="/advisor/team/dashboard">
              <Button variant="primary" size="md">
                Open dashboard
              </Button>
            </Link>
            <Link href="/advisor/team/validation">
              <Button variant="secondary" size="md">
                Production validation
              </Button>
            </Link>
            <Link href="/advisor/team/shared-research">
              <Button variant="ghost" size="md">
                Shared Research
              </Button>
            </Link>
            <Link href="/advisor/team/shared-portfolios">
              <Button variant="ghost" size="md">
                Shared Portfolios
              </Button>
            </Link>
            <Link href="/advisor/team/shared-reviews">
              <Button variant="ghost" size="md">
                Shared Reviews
              </Button>
            </Link>
          </CardBody>
        </Card>
        <WorkspaceOverviewCard />
        <div className="grid gap-4 lg:grid-cols-2">
          <RecentActivityCard />
          <SessionSummaryCard />
        </div>
      </div>
    </CollaborationLayout>
  );
});

function TeamPage({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <CollaborationLayout title={title} description={description}>
      {children}
    </CollaborationLayout>
  );
}

function MyWorkBody() {
  const tasks = useMemo(() => listTasks().slice(0, 8), []);
  const session = useCollaborationSession();
  return (
    <Card>
      <CardHeader
        title="Open tasks"
        description={
          session.selectedWorkspace === "my"
            ? "Personal demo tasks and follow-ups"
            : "Shared view of demo assignments (session)"
        }
      />
      <CardBody>
        <ul className="space-y-2" aria-label="My work tasks">
          {tasks.map((t) => (
            <li
              key={t.id}
              className="flex min-h-11 items-center justify-between rounded-md border border-[var(--border)] px-3 text-sm"
            >
              <span>{t.title}</span>
              <Badge>{t.status}</Badge>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

export const MyWorkSection = memo(function MyWorkSection() {
  return (
    <TeamPage title="My Work" description="Personal and shared demo work items">
      <MyWorkBody />
    </TeamPage>
  );
});

export const SharedResearchSection = memo(function SharedResearchSection() {
  return (
    <TeamPage
      title="Shared Research"
      description="Collaborative organization over existing DSP research envelopes"
    >
      <Card>
        <CardHeader
          title="Shared Research Workspace"
          description="Library · Collections · Compare · Bookmarks · Activity"
        />
        <CardBody className="space-y-3 text-sm">
          <p className="text-[var(--muted)]">
            Sprint 7.2 workspace reuses demo research envelopes only — conclusions unchanged.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link href="/advisor/team/shared-research">
              <Button variant="primary" size="md">
                Open workspace
              </Button>
            </Link>
            <Link href="/advisor/team/shared-research/library">
              <Button variant="secondary" size="md">
                Library
              </Button>
            </Link>
            <Link href="/advisor/team/shared-research/compare">
              <Button variant="secondary" size="md">
                Compare
              </Button>
            </Link>
          </div>
        </CardBody>
      </Card>
    </TeamPage>
  );
});

export const SharedReviewsSection = memo(function SharedReviewsSection() {
  return (
    <TeamPage
      title="Shared Reviews"
      description="Team review coordination over existing client review demos"
    >
      <Card>
        <CardHeader
          title="Team Review & Assignment"
          description="Board · Discussion · Timeline · Progress · Activity"
        />
        <CardBody className="space-y-3 text-sm">
          <p className="text-[var(--muted)]">
            Sprint 7.4 workspace reuses Client Review demos only — research and portfolio outputs
            unchanged.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link href="/advisor/team/shared-reviews">
              <Button variant="primary" size="md">
                Open workspace
              </Button>
            </Link>
            <Link href="/advisor/team/shared-reviews/board">
              <Button variant="secondary" size="md">
                Assignment Board
              </Button>
            </Link>
            <Link href="/advisor/team/shared-reviews/progress">
              <Button variant="secondary" size="md">
                Progress
              </Button>
            </Link>
          </div>
        </CardBody>
      </Card>
    </TeamPage>
  );
});

export const SharedPortfoliosSection = memo(function SharedPortfoliosSection() {
  return (
    <TeamPage
      title="Shared Portfolios"
      description="Collaborative review of existing model portfolio demos"
    >
      <Card>
        <CardHeader
          title="Shared Portfolio Workspace"
          description="Library · Compare · Scenarios · Discussion · Activity"
        />
        <CardBody className="space-y-3 text-sm">
          <p className="text-[var(--muted)]">
            Sprint 7.3 workspace reuses demo model portfolios only — allocations and risk are not
            recalculated.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link href="/advisor/team/shared-portfolios">
              <Button variant="primary" size="md">
                Open workspace
              </Button>
            </Link>
            <Link href="/advisor/team/shared-portfolios/compare">
              <Button variant="secondary" size="md">
                Compare
              </Button>
            </Link>
            <Link href="/advisor/team/shared-portfolios/scenarios">
              <Button variant="secondary" size="md">
                Scenarios
              </Button>
            </Link>
          </div>
        </CardBody>
      </Card>
    </TeamPage>
  );
});

export const DiscussionsSection = memo(function DiscussionsSection() {
  return (
    <TeamPage
      title="Discussions"
      description="Placeholder shell for Sprint 7.2 — no chat backend"
    >
      <Card>
        <CardHeader title="Discussions foundation" />
        <CardBody className="text-sm text-[var(--muted)]">
          Threaded discussions and mentions are deferred. This route establishes
          navigation and session context only.
        </CardBody>
      </Card>
    </TeamPage>
  );
});

export const AssignmentsSection = memo(function AssignmentsSection() {
  const tasks = useMemo(
    () => listTasks().filter((t) => t.status !== "done").slice(0, 6),
    [],
  );
  return (
    <TeamPage
      title="Assignments"
      description="Demo task assignment view — links to Team Review board"
    >
      <Card>
        <CardHeader title="Open assignments" description="Mapped from demo tasks" />
        <CardBody className="space-y-3">
          <ul className="space-y-2" aria-label="Assignments">
            {tasks.map((t) => (
              <li
                key={t.id}
                className="flex min-h-11 items-center justify-between rounded-md border border-[var(--border)] px-3 text-sm"
              >
                <span>{t.title}</span>
                <Badge>{t.kind}</Badge>
              </li>
            ))}
          </ul>
          <Link href="/advisor/team/shared-reviews/board">
            <Button variant="secondary" size="md">
              Open Assignment Board
            </Button>
          </Link>
        </CardBody>
      </Card>
    </TeamPage>
  );
});

export const ActivitySection = memo(function ActivitySection() {
  return (
    <TeamPage
      title="Activity"
      description="Workspace activity feed from existing demo timelines"
    >
      <RecentActivityCard />
      <SessionSummaryCard />
    </TeamPage>
  );
});
