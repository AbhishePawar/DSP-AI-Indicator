"use client";

/**
 * EPIC-F009 — Settings & User Preferences workspace.
 * UI preferences locally; account/session from existing auth APIs only.
 */

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ds";
import {
  SETTINGS_SECTIONS,
  isSettingsSectionId,
  useSettingsPrefsStore,
} from "@/lib/settings";
import { useCollapsePanelsBelowLg } from "@/lib/a11y";
import { cn } from "@/lib/utils";
import { SettingsLeftNav } from "./LeftNav";
import { SettingsRightPanel } from "./RightPanel";
import {
  AboutSection,
  AccessibilitySection,
  AppearanceSection,
  DashboardSection,
  NotificationsSection,
  ProfileSection,
  SecuritySection,
  WorkspaceSection,
} from "./Sections";

function Toolbar({
  leftOpen,
  rightOpen,
  onToggleLeft,
  onToggleRight,
}: {
  leftOpen: boolean;
  rightOpen: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
}) {
  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] bg-[var(--surface)]/95 px-3 py-2 backdrop-blur motion-reduce:backdrop-blur-none">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleLeft}
          aria-pressed={leftOpen}
          aria-label={leftOpen ? "Hide navigation panel" : "Show navigation panel"}
        >
          {leftOpen ? "Hide nav" : "Show nav"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleRight}
          aria-pressed={rightOpen}
          aria-label={rightOpen ? "Hide context panel" : "Show context panel"}
        >
          {rightOpen ? "Hide context" : "Show context"}
        </Button>
        <span className="hidden text-xs text-[var(--muted)] md:inline">
          Shortcuts: 1–8 sections · [ / ] panels
        </span>
      </div>
    </div>
  );
}

export function SettingsWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const activeSection = useSettingsPrefsStore((s) => s.activeSection);
  const setActiveSection = useSettingsPrefsStore((s) => s.setActiveSection);
  const leftOpen = useSettingsPrefsStore((s) => s.leftOpen);
  const rightOpen = useSettingsPrefsStore((s) => s.rightOpen);
  const toggleLeft = useSettingsPrefsStore((s) => s.toggleLeft);
  const toggleRight = useSettingsPrefsStore((s) => s.toggleRight);
  const setLeftOpen = useSettingsPrefsStore((s) => s.setLeftOpen);
  const setRightOpen = useSettingsPrefsStore((s) => s.setRightOpen);

  useCollapsePanelsBelowLg(setLeftOpen, setRightOpen);

  useEffect(() => {
    const section = searchParams.get("section");
    if (section && isSettingsSectionId(section)) {
      setActiveSection(section);
    }
  }, [searchParams, setActiveSection]);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("section", activeSection);
    const next = params.toString();
    const current = searchParams.get("section");
    if (current !== activeSection) {
      router.replace(`/settings?${next}`, { scroll: false });
    }
  }, [activeSection, router, searchParams]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" || target?.isContentEditable) {
        return;
      }
      if (e.key === "[") {
        e.preventDefault();
        toggleLeft();
      } else if (e.key === "]") {
        e.preventDefault();
        toggleRight();
      } else if (/^[1-8]$/.test(e.key)) {
        const section = SETTINGS_SECTIONS.find((s) => s.shortcut === e.key);
        if (section) {
          e.preventDefault();
          setActiveSection(section.id);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setActiveSection, toggleLeft, toggleRight]);

  return (
    <div className="flex min-h-[70vh] flex-col rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg)]">
      <Toolbar
        leftOpen={leftOpen}
        rightOpen={rightOpen}
        onToggleLeft={toggleLeft}
        onToggleRight={toggleRight}
      />
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside
          aria-label="Settings navigation"
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-r",
            leftOpen ? "block" : "hidden",
          )}
        >
          <SettingsLeftNav />
        </aside>
        <div
          role="region"
          aria-label="Main settings panel"
          className="min-w-0 flex-1 overflow-auto p-4"
        >
          {activeSection === "profile" ? <ProfileSection /> : null}
          {activeSection === "appearance" ? <AppearanceSection /> : null}
          {activeSection === "dashboard" ? <DashboardSection /> : null}
          {activeSection === "workspace" ? <WorkspaceSection /> : null}
          {activeSection === "notifications" ? <NotificationsSection /> : null}
          {activeSection === "security" ? <SecuritySection /> : null}
          {activeSection === "accessibility" ? <AccessibilitySection /> : null}
          {activeSection === "about" ? <AboutSection /> : null}
        </div>
        <aside
          aria-label="Settings context panel"
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-l",
            rightOpen ? "block" : "hidden",
          )}
        >
          <SettingsRightPanel />
        </aside>
      </div>
    </div>
  );
}
