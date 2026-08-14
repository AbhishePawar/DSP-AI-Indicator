"use client";

import { useEffect } from "react";

import { Button, Switch } from "@/components/ds";
import {
  DASHBOARD_WIDGETS,
  useDashboardPrefsStore,
  type DashboardWidgetId,
} from "@/lib/dashboard";

export function DashboardCustomizePanel({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const widgetOrder = useDashboardPrefsStore((s) => s.widgetOrder);
  const hiddenWidgets = useDashboardPrefsStore((s) => s.hiddenWidgets);
  const toggleWidgetVisible = useDashboardPrefsStore(
    (s) => s.toggleWidgetVisible,
  );
  const moveWidget = useDashboardPrefsStore((s) => s.moveWidget);
  const resetLayout = useDashboardPrefsStore((s) => s.resetLayout);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <section
      className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4"
      aria-label="Customize dashboard layout"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-lg tracking-tight">
            Customize layout
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Widget order and visibility are stored locally. Theme persists via
            Theme Switcher.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={() => resetLayout()}>
            Reset layout
          </Button>
          <Button size="sm" variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>

      <ul className="mt-4 space-y-2">
        {widgetOrder.map((id) => {
          const meta = DASHBOARD_WIDGETS.find((w) => w.id === id);
          if (!meta) return null;
          const visible = !hiddenWidgets.includes(id);
          return (
            <li
              key={id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium">{meta.title}</p>
                <p className="text-xs text-[var(--muted)]">{meta.section}</p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Move ${meta.title} up`}
                  onClick={() => moveWidget(id as DashboardWidgetId, "up")}
                >
                  ↑
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Move ${meta.title} down`}
                  onClick={() => moveWidget(id as DashboardWidgetId, "down")}
                >
                  ↓
                </Button>
                <label className="flex items-center gap-2 text-xs text-[var(--muted)]">
                  <span className="sr-only">Show {meta.title}</span>
                  <Switch
                    checked={visible}
                    onCheckedChange={() =>
                      toggleWidgetVisible(id as DashboardWidgetId)
                    }
                    aria-label={`Toggle ${meta.title} visibility`}
                  />
                  Visible
                </label>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
