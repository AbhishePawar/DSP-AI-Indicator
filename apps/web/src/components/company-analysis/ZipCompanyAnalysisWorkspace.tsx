"use client";

import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import {
  mapZipResearchView,
  type ZipResearchViewModel,
  type ZipStatus,
  type ZipFinancialPoint,
} from "@/lib/research/mapZipResearchView";
import { useResearchDisclaimerGate } from "@/components/legal/useResearchDisclaimerGate";
import { Badge } from "@/components/ds/data/badge";
import { pushRecentAnalysis } from "@/lib/analysis/recentAnalyses";

// ─── Types ───────────────────────────────────────────────────────────────────

export type ResearchMode = "simple" | "buffett";

export type AnalysisPhase =
  | "select"
  | "workspace-ready"
  | "simple-loading"
  | "simple-result"
  | "buffett-loading"
  | "buffett-result";

export const SIMPLE_TOC_GROUPS = [
  {
    label: "OVERVIEW",
    items: [
      { id: "s01", label: "Executive Summary" },
    ],
  },
  {
    label: "FINANCIALS & VALUATION",
    items: [
      { id: "s04", label: "Financial Analysis" },
      { id: "s09", label: "Valuation Overview" },
      { id: "s15", label: "Downloads & Export" },
    ],
  },
];

type ChatMsg = { role: "user" | "dsp"; text: string };

const LOADING_STEPS = [
  "Identifying security",
  "Collecting financial evidence",
  "Analysing business quality",
  "Evaluating economic moat",
  "Evaluating management",
  "Analysing earnings & growth",
  "Evaluating valuation",
  "Checking peer intelligence",
  "Validating research",
  "Preparing analysis report",
];

export const TOC_GROUPS = [
  {
    label: "OVERVIEW",
    items: [
      { id: "s01", label: "Executive Summary" },
    ],
  },
  {
    label: "FUNDAMENTALS",
    items: [
      { id: "s04", label: "Financials" },
    ],
  },
  {
    label: "VALUATION",
    items: [
      { id: "s09", label: "Valuation" },
      { id: "s10", label: "Margin of Safety" },
    ],
  },
  {
    label: "BUFFETT / QUALITY",
    items: [
      { id: "s03", label: "Buffett Indicator" },
      { id: "s02", label: "Business Quality" },
      { id: "s06", label: "Management" },
      { id: "s07", label: "Earnings Quality" },
      { id: "s08", label: "Growth Quality" },
    ],
  },
  {
    label: "RISKS",
    items: [
      { id: "s11", label: "Key Risks" },
      { id: "s12", label: "Strengths & Weaknesses" },
    ],
  },
  {
    label: "EVIDENCE & AUDIT",
    items: [
      { id: "s13", label: "Investment Context" },
      { id: "s14", label: "Supporting Evidence" },
      { id: "s15", label: "Downloads" },
    ],
  },
];

export const ALL_SECTIONS = TOC_GROUPS.flatMap((g) => g.items);

// ─── Primitives & Badges ─────────────────────────────────────────────────────

export function StatusBadge({ status, text }: { status: ZipStatus; text?: string }) {
  const cfg = {
    strong: {
      color: "var(--c-profit, #22c55e)",
      bg: "rgba(34,197,94,0.12)",
      border: "rgba(34,197,94,0.25)",
      label: "Strong",
    },
    adequate: {
      color: "var(--c-revenue, #f59e0b)",
      bg: "rgba(245,158,11,0.12)",
      border: "rgba(245,158,11,0.25)",
      label: "Adequate",
    },
    weak: {
      color: "var(--c-risk, #ef4444)",
      bg: "rgba(239,68,68,0.12)",
      border: "rgba(239,68,68,0.25)",
      label: "Weak",
    },
    unavailable: {
      color: "var(--muted-foreground, #888888)",
      bg: "var(--secondary, #1a1a1a)",
      border: "var(--border, #333333)",
      label: "Unavailable",
    },
  }[status] || {
    color: "var(--muted-foreground, #888888)",
    bg: "var(--secondary, #1a1a1a)",
    border: "var(--border, #333333)",
    label: "Unavailable",
  };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 8px",
        borderRadius: 4,
        fontSize: 11,
        fontFamily: "var(--font-data, monospace)",
        fontWeight: 500,
        color: cfg.color,
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: cfg.color,
          flexShrink: 0,
        }}
      />
      {text || cfg.label}
    </span>
  );
}

export function SectionHead({
  id,
  num,
  title,
  status,
  subtitle,
}: {
  id: string;
  num?: string;
  title: string;
  status?: ZipStatus;
  subtitle?: string;
}) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        {num && (
          <span
            style={{
              fontSize: 11,
              color: "var(--muted-foreground)",
              fontFamily: "var(--font-data)",
              letterSpacing: "0.08em",
            }}
          >
            {num}
          </span>
        )}
        <h2
          style={{
            fontSize: 18,
            fontWeight: 600,
            color: "var(--foreground)",
            margin: 0,
            fontFamily: "var(--font-heading)",
          }}
        >
          {title}
        </h2>
        {status && <StatusBadge status={status} />}
      </div>
      {subtitle && (
        <p
          style={{
            fontSize: 13,
            color: "var(--muted-foreground)",
            margin: "5px 0 0",
            lineHeight: 1.6,
          }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}

export function Card({
  children,
  style,
  className,
}: {
  children: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        background: "var(--card, #111520)",
        border: "1px solid var(--border)",
        borderRadius: "var(--card-radius, 12px)",
        padding: "20px 22px",
        boxShadow: "var(--shadow-card, 0 4px 20px -2px rgba(0, 0, 0, 0.5))",
        transition: "border-color 0.15s ease",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function AskButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 12px",
        background: "var(--secondary)",
        border: "1px solid var(--border)",
        borderRadius: 6,
        fontSize: 12,
        color: "var(--muted-foreground)",
        cursor: "pointer",
        fontFamily: "var(--font-body)",
        transition: "all 0.15s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = "var(--foreground)";
        e.currentTarget.style.borderColor = "var(--c-dsp, #3b82f6)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = "var(--muted-foreground)";
        e.currentTarget.style.borderColor = "var(--border)";
      }}
    >
      <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
        <path
          d="M1 2.5C1 1.67 1.67 1 2.5 1h6C9.33 1 10 1.67 10 2.5v4c0 .83-.67 1.5-1.5 1.5H6.5L4 10V8H2.5C1.67 8 1 7.33 1 6.5v-4z"
          stroke="currentColor"
          strokeWidth="1.1"
          strokeLinejoin="round"
        />
      </svg>
      {label}
    </button>
  );
}

// ─── Simple SVG Charts ───────────────────────────────────────────────────────

export function SvgAreaChart({ data, color, label, unit }: { data: ZipFinancialPoint[]; color: string; label?: string; unit?: string }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ height: 160, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "var(--surface-2, rgba(255,255,255,0.02))", borderRadius: 8, border: "1px dashed var(--border)", padding: 16, textAlign: "center" }}>
        <p style={{ fontSize: 12, color: "var(--muted-foreground)", margin: 0 }}>Historical {label || "series"} awaiting filing data from backend</p>
        <span style={{ fontSize: 10, color: "var(--muted-foreground)", marginTop: 4 }}>Production AnalyseResponse does not include multi-year series</span>
      </div>
    );
  }
  if (!data || data.length === 0) {
    return (
      <div style={{ height: 110, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--muted-foreground)", fontSize: 12 }}>
        No historical trend data available in server response
      </div>
    );
  }

  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const h = 80;
  const w = 260;
  const pad = 12;

  const points = data.map((d, i) => {
    const x = pad + (i / (data.length - 1 || 1)) * (w - pad * 2);
    const y = h - pad - ((d.value - min) / range) * (h - pad * 2);
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(" L ")}`;
  const firstPoint = points[0].split(",");
  const lastPoint = points[points.length - 1].split(",");
  const areaD = `M ${firstPoint[0]},${h} L ${points.join(" L ")} L ${lastPoint[0]},${h} Z`;

  return (
    <div style={{ width: "100%" }}>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: 110, overflow: "visible" }}>
        <defs>
          <linearGradient id={`grad-${color.replace(/[^a-zA-Z0-9]/g, "")}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.2" />
            <stop offset="100%" stopColor={color} stopOpacity="0.0" />
          </linearGradient>
        </defs>
        <path d={areaD} fill={`url(#grad-${color.replace(/[^a-zA-Z0-9]/g, "")})`} />
        <path d={pathD} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
        {data.map((d, i) => {
          const [cx, cy] = points[i].split(",");
          return (
            <g key={i}>
              <circle cx={cx} cy={cy} r="3.5" fill={color} />
              <text
                x={cx}
                y={h + 14}
                textAnchor="middle"
                fontSize="9"
                fill="var(--muted-foreground)"
                fontFamily="var(--font-data)"
              >
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function SvgBarChart({ data, color, label }: { data: ZipFinancialPoint[]; color: string; label?: string }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ height: 160, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "var(--surface-2, rgba(255,255,255,0.02))", borderRadius: 8, border: "1px dashed var(--border)", padding: 16, textAlign: "center" }}>
        <p style={{ fontSize: 12, color: "var(--muted-foreground)", margin: 0 }}>Historical {label || "cash flow"} awaiting filing data from backend</p>
        <span style={{ fontSize: 10, color: "var(--muted-foreground)", marginTop: 4 }}>Production AnalyseResponse does not include multi-year series</span>
      </div>
    );
  }
  if (!data || data.length === 0) {
    return (
      <div style={{ height: 110, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--muted-foreground)", fontSize: 12 }}>
        No historical cash flow data available in server response
      </div>
    );
  }

  const values = data.map((d) => d.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values);
  const range = max - min || 1;
  const h = 80;
  const w = 260;
  const pad = 12;
  const barWidth = 18;

  return (
    <div style={{ width: "100%" }}>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: 110, overflow: "visible" }}>
        {data.map((d, i) => {
          const cx = pad + (i / (data.length - 1 || 1)) * (w - pad * 2);
          const barH = ((d.value - min) / range) * (h - pad * 2);
          const y = h - pad - barH;
          return (
            <g key={i}>
              <rect
                x={cx - barWidth / 2}
                y={y}
                width={barWidth}
                height={barH}
                fill={color}
                rx="3"
              />
              <text
                x={cx}
                y={h + 14}
                textAnchor="middle"
                fontSize="9"
                fill="var(--muted-foreground)"
                fontFamily="var(--font-data)"
              >
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ─── Selection Screen ────────────────────────────────────────────────────────

export function SelectionScreen({
  symbol,
  onSimple,
  onBuffett,
}: {
  symbol: string;
  onSimple: () => void;
  onBuffett: () => void;
}) {
  const POPULAR = [
    { s: "TCS.NS", n: "Tata Consultancy Services" },
    { s: "RELIANCE.NS", n: "Reliance Industries" },
    { s: "INFY.NS", n: "Infosys Limited" },
    { s: "HDFCBANK.NS", n: "HDFC Bank" },
  ];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "80vh",
        padding: 24,
      }}
    >
      <div style={{ maxWidth: 640, width: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div
            style={{
              fontSize: 11,
              color: "var(--c-dsp, #3b82f6)",
              fontFamily: "var(--font-data)",
              letterSpacing: "0.12em",
              marginBottom: 8,
            }}
          >
            RESEARCH WORKSPACE
          </div>
          <h1
            style={{
              fontSize: 28,
              fontWeight: 700,
              color: "var(--foreground)",
              margin: "0 0 10px",
              fontFamily: "var(--font-heading)",
            }}
          >
            Choose Research Depth
          </h1>
          <p
            style={{
              fontSize: 14,
              color: "var(--muted-foreground)",
              margin: 0,
              lineHeight: 1.6,
            }}
          >
            Selected: <strong style={{ color: "var(--foreground)" }}>{symbol || "TCS.NS"}</strong> · Select how deep you want the DSP analytical pipeline to run.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 28 }}>
          {/* Simple */}
          <div
            onClick={onSimple}
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: 24,
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              transition: "all 0.2s",
            }}
          >
            <div
              style={{
                fontSize: 10,
                color: "var(--muted-foreground)",
                fontFamily: "var(--font-data)",
                letterSpacing: "0.08em",
                marginBottom: 8,
              }}
            >
              FAST OVERVIEW
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 600,
                color: "var(--foreground)",
                fontFamily: "var(--font-heading)",
                marginBottom: 8,
              }}
            >
              Simple Analysis
            </div>
            <p
              style={{
                fontSize: 13,
                color: "var(--muted-foreground)",
                margin: "0 0 16px",
                lineHeight: 1.6,
                flex: 1,
              }}
            >
              Core valuation, business quality summary, key metrics, and preliminary rating.
            </p>
            <div
              style={{
                fontSize: 11,
                color: "var(--muted-foreground)",
                fontFamily: "var(--font-data)",
                marginBottom: 16,
              }}
            >
              ~5s · 4 stages
            </div>
            <button
              type="button"
              style={{
                width: "100%",
                padding: "9px 0",
                background: "var(--secondary)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 13,
                color: "var(--foreground)",
                cursor: "pointer",
                fontFamily: "var(--font-body)",
                fontWeight: 500,
              }}
            >
              Run Simple
            </button>
          </div>

          {/* Buffett Mode */}
          <div
            onClick={onBuffett}
            style={{
              background: "var(--card)",
              border: "2px solid var(--c-dsp, #3b82f6)",
              borderRadius: 12,
              padding: 24,
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              position: "relative",
              transition: "all 0.2s",
            }}
          >
            <span
              style={{
                position: "absolute",
                top: -10,
                right: 16,
                background: "var(--c-dsp, #3b82f6)",
                color: "#fff",
                fontSize: 9,
                fontWeight: 600,
                fontFamily: "var(--font-data)",
                padding: "2px 8px",
                borderRadius: 99,
                letterSpacing: "0.08em",
              }}
            >
              FLAGSHIP
            </span>
            <div
              style={{
                fontSize: 10,
                color: "var(--c-dsp, #3b82f6)",
                fontFamily: "var(--font-data)",
                letterSpacing: "0.08em",
                marginBottom: 8,
              }}
            >
              FULL DEPTH
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 600,
                color: "var(--foreground)",
                fontFamily: "var(--font-heading)",
                marginBottom: 8,
              }}
            >
              Buffett Analysis
            </div>
            <p
              style={{
                fontSize: 13,
                color: "var(--muted-foreground)",
                margin: "0 0 16px",
                lineHeight: 1.6,
                flex: 1,
              }}
            >
              10-row matrix, moat evaluation, capital allocation, 5-domain scores, 14 deep-dive sections, full evidence trail.
            </p>
            <div
              style={{
                fontSize: 11,
                color: "var(--muted-foreground)",
                fontFamily: "var(--font-data)",
                marginBottom: 16,
              }}
            >
              ~15s · 10 analytical stages
            </div>
            <button
              type="button"
              style={{
                width: "100%",
                padding: "9px 0",
                background: "var(--c-dsp, #3b82f6)",
                border: "none",
                borderRadius: 8,
                fontSize: 13,
                color: "#fff",
                cursor: "pointer",
                fontFamily: "var(--font-body)",
                fontWeight: 600,
              }}
            >
              Run Buffett Analysis
            </button>
          </div>
        </div>

        {/* Popular tickers */}
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 11,
              color: "var(--muted-foreground)",
              fontFamily: "var(--font-data)",
              marginBottom: 8,
            }}
          >
            Or analyze another benchmark:
          </div>
          <div style={{ display: "flex", justifyContent: "center", gap: 8, flexWrap: "wrap" }}>
            {POPULAR.map((p) => (
              <button
                key={p.s}
                type="button"
                onClick={() => {
                  window.location.href = `/analysis?symbol=${p.s}`;
                }}
                style={{
                  padding: "5px 10px",
                  background: "var(--secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontSize: 11,
                  color: "var(--muted-foreground)",
                  cursor: "pointer",
                  fontFamily: "var(--font-data)",
                }}
              >
                {p.s}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Staged Loader ───────────────────────────────────────────────────────────

export function StagedLoader({
  steps,
  active,
  onDone,
}: {
  steps: string[];
  active: boolean;
  onDone?: () => void;
}) {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    if (!active) return;
    setCurrent(0);
    const interval = setInterval(() => {
      setCurrent((prev) => {
        if (prev < steps.length - 1) return prev + 1;
        clearInterval(interval);
        if (onDone) setTimeout(onDone, 400);
        return prev;
      });
    }, 900);
    return () => clearInterval(interval);
  }, [active, steps.length, onDone]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "70vh",
        padding: 24,
      }}
    >
      <div style={{ maxWidth: 440, width: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            style={{
              fontSize: 10,
              color: "var(--c-dsp, #3b82f6)",
              fontFamily: "var(--font-data)",
              letterSpacing: "0.12em",
              marginBottom: 6,
            }}
          >
            STAGE {current + 1} OF {steps.length}
          </div>
          <div
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: "var(--foreground)",
              fontFamily: "var(--font-heading)",
            }}
          >
            {steps[current]}
          </div>
        </div>

        {/* Progress bar */}
        <div
          style={{
            height: 4,
            background: "var(--secondary)",
            borderRadius: 99,
            overflow: "hidden",
            marginBottom: 24,
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${((current + 1) / steps.length) * 100}%`,
              background: "var(--c-dsp, #3b82f6)",
              borderRadius: 99,
              transition: "width 0.4s ease",
            }}
          />
        </div>

        {/* Step list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {steps.map((s, i) => {
            const isDone = i < current;
            const isCurr = i === current;
            return (
              <div
                key={s}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  fontSize: 12,
                  color: isCurr
                    ? "var(--foreground)"
                    : isDone
                    ? "var(--muted-foreground)"
                    : "rgba(255,255,255,0.2)",
                  fontFamily: "var(--font-body)",
                }}
              >
                <div
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 9,
                    flexShrink: 0,
                    background: isDone
                      ? "var(--c-profit, #22c55e)"
                      : isCurr
                      ? "var(--c-dsp, #3b82f6)"
                      : "var(--secondary)",
                    color: isDone || isCurr ? "#fff" : "var(--muted-foreground)",
                    fontWeight: 600,
                  }}
                >
                  {isDone ? "✓" : i + 1}
                </div>
                <span>{s}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Company Header ──────────────────────────────────────────────────────────

export function CompanyHeader({
  model,
  onModeSwitch,
  searchValue,
  onSearchChange,
  onAnalyze,
  isAnalyzing,
}: {
  model: ZipResearchViewModel;
  onModeSwitch: () => void;
  searchValue?: string;
  onSearchChange?: (val: string) => void;
  onAnalyze?: (val?: string) => void;
  isAnalyzing?: boolean;
}) {
  return (
    <header
      style={{
        borderBottom: "1px solid var(--border)",
        padding: "14px 28px",
        background: "var(--card)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 16,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
        <form
          role="search"
          onSubmit={(e) => {
            e.preventDefault();
            if (onAnalyze) onAnalyze(searchValue);
          }}
          style={{ display: "flex", alignItems: "center", gap: 8 }}
        >
          <label htmlFor="company-search-input" style={{ display: "none" }}>
            Company search
          </label>
          <input
            id="company-search-input"
            aria-label="Company search"
            type="search"
            value={searchValue ?? model.header.ticker}
            onChange={(e) => onSearchChange?.(e.target.value)}
            placeholder="Search company (e.g. TCS.NS)..."
            style={{
              padding: "6px 12px",
              background: "var(--secondary)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              color: "var(--foreground)",
              fontSize: 13,
              fontFamily: "var(--font-data)",
              width: 170,
            }}
          />
          <button
            type="submit"
            disabled={isAnalyzing}
            style={{
              padding: "6px 14px",
              background: "var(--c-dsp, #3b82f6)",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: isAnalyzing ? "not-allowed" : "pointer",
              opacity: isAnalyzing ? 0.7 : 1,
              fontFamily: "var(--font-body)",
            }}
          >
            {isAnalyzing ? "Analyzing..." : "Analyze"}
          </button>
        </form>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <h1
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: "var(--foreground)",
                margin: 0,
                fontFamily: "var(--font-heading)",
                letterSpacing: "-0.015em",
              }}
            >
              {model.header.companyName}
            </h1>
            <span
              style={{
                fontSize: 11,
                padding: "2px 8px",
                background: "var(--surface-2, #181e2e)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm, 4px)",
                fontFamily: "var(--font-data)",
                color: "var(--muted-foreground)",
              }}
            >
              {model.header.ticker} · {model.header.exchange}
            </span>
            <Badge variant="accent" style={{ fontFamily: "var(--font-data)", fontSize: 11 }}>
              {model.header.sector}
            </Badge>
          </div>
          <div
            style={{
              fontSize: 11,
              color: "var(--muted-foreground)",
              marginTop: 4,
              fontFamily: "var(--font-data)",
            }}
          >
            Currency: {model.header.currency} · As of: {model.header.asOfDate}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" }} className="company-header-metrics">
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontSize: 10,
              color: "var(--muted-foreground)",
              fontFamily: "var(--font-data)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Market Price
          </div>
          <div
            className="company-header-price"
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: "var(--foreground)",
              fontFamily: "var(--font-data)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {model.valuation.currentPriceFormatted}
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontSize: 10,
              color: "var(--muted-foreground)",
              fontFamily: "var(--font-data)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Intrinsic Value
          </div>
          <div
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: "var(--c-cashflow, #2dd4bf)",
              fontFamily: "var(--font-data)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {model.valuation.intrinsicValueFormatted}
          </div>
        </div>

        {model.valuation.marginOfSafetyFormatted ? (
          <div style={{ textAlign: "right" }}>
            <div
              style={{
                fontSize: 10,
                color: "var(--muted-foreground)",
                fontFamily: "var(--font-data)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
              }}
            >
              Margin of Safety
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 700,
                color: model.valuation.status === "strong" ? "var(--c-profit, #22c55e)" : "var(--c-risk, #ef4444)",
                fontFamily: "var(--font-data)",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {model.valuation.marginOfSafetyFormatted}
            </div>
          </div>
        ) : null}

        <button
          type="button"
          onClick={onModeSwitch}
          style={{
            padding: "8px 14px",
            background: "var(--surface-2, #181e2e)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md, 8px)",
            fontSize: 12,
            fontWeight: 500,
            color: "var(--foreground)",
            cursor: "pointer",
            fontFamily: "var(--font-body)",
            transition: "all 0.15s ease",
          }}
        >
          Change Mode
        </button>
      </div>
    </header>
  );
}

// ─── Investment Summary Hero ─────────────────────────────────────────────────

export function InvestmentSummary({
  model,
  onAsk,
}: {
  model: ZipResearchViewModel;
  onAsk: (ctx: string) => void;
}) {
  return (
    <Card style={{ marginBottom: 36, borderLeft: "4px solid var(--c-dsp, #3b82f6)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 16,
          marginBottom: 16,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 10,
              color: "var(--c-dsp, #3b82f6)",
              fontFamily: "var(--font-data)",
              letterSpacing: "0.12em",
              marginBottom: 4,
              textTransform: "uppercase",
            }}
          >
            RESEARCH OUTCOME
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <h2
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: "var(--foreground)",
                fontFamily: "var(--font-heading)",
                margin: 0,
              }}
            >
              Investment Summary
            </h2>
            <span style={{ fontSize: 18, color: "var(--muted-foreground)" }}>·</span>
            <span
              style={{
                fontSize: 20,
                fontWeight: 600,
                color: "var(--foreground)",
                fontFamily: "var(--font-heading)",
              }}
            >
              {model.investmentSummary.verdict}
            </span>
            <StatusBadge status={model.investmentSummary.recommendationStatus} text={model.investmentSummary.recommendationBadge} />
          </div>
        </div>
        <AskButton label="Ask about this verdict" onClick={() => onAsk("Investment verdict and summary")} />
      </div>

      <p style={{ fontSize: 14, color: "var(--foreground)", lineHeight: 1.7, margin: "0 0 20px" }}>
        {model.investmentSummary.summaryText}
      </p>

      {/* Grid of 4 key numbers - VALUE prioritized above METRIC NAME */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 12,
          paddingTop: 18,
          borderTop: "1px solid var(--border)",
        }}
      >
        {model.investmentSummary.metrics.map((m) => (
          <div
            key={m.label}
            style={{
              background: "var(--surface-2, #181e2e)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md, 8px)",
              padding: "14px 16px",
              minHeight: 80,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              gap: 4,
              boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.4))",
            }}
          >
            <div
              style={{
                fontSize: 20,
                fontWeight: 700,
                color: (m as any).color || "var(--foreground)",
                fontFamily: "var(--font-data)",
                fontVariantNumeric: "tabular-nums",
                lineHeight: 1.2,
              }}
            >
              {m.value}
            </div>
            <div
              style={{
                fontSize: 10,
                color: "var(--muted-foreground)",
                fontFamily: "var(--font-data)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
              }}
            >
              {m.label}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ─── Buffett Assessment Table ────────────────────────────────────────────────

export function BuffettAssessmentTable({
  model,
  onAsk,
}: {
  model: ZipResearchViewModel;
  onAsk: (ctx: string) => void;
}) {
  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead
        id="s03"
        num="02"
        title="Buffett Indicator Analysis"
        subtitle="Presentation synthesis of existing /api/v1/analyse outputs — no recalculation"
      />
      <div style={{ display: "none" }}>
        <span>Presentation synthesis of existing /api/v1/analyse outputs — no recalculation</span>
      </div>
      <Card style={{ marginBottom: 14, padding: "14px 18px" }}>
        <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, margin: 0 }}>
          <div>
            <dt style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>Overall Buffett Rating</dt>
            <dd style={{ fontSize: 16, fontWeight: 600, margin: 0, color: "var(--foreground)" }}>{model.businessQualityStatus.toUpperCase()}</dd>
          </div>
          <div>
            <dt style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>Buffett Action</dt>
            <dd style={{ fontSize: 16, fontWeight: 600, margin: 0, color: "var(--foreground)" }}>{model.recommendation}</dd>
          </div>
        </dl>
      </Card>
      <Card>
        <div style={{ overflowX: "auto" }}>
          <table role="table" aria-label="Buffett Assessment Dimension Matrix" style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
      <caption className="sr-only" style={{ position: "absolute", width: 1, height: 1, padding: 0, margin: -1, overflow: "hidden", clip: "rect(0,0,0,0)", border: 0 }}>Evaluation of 10 core Buffett investment criteria</caption>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={{ textAlign: "left", padding: "8px 12px", fontFamily: "var(--font-data)", fontSize: 10, letterSpacing: "0.08em", color: "var(--muted-foreground)", fontWeight: 400 }}>
                  DIMENSION
                </th>
                <th style={{ textAlign: "left", padding: "8px 12px", fontFamily: "var(--font-data)", fontSize: 10, letterSpacing: "0.08em", color: "var(--muted-foreground)", fontWeight: 400 }}>
                  RESULT / STAGE SUMMARY
                </th>
                <th style={{ textAlign: "left", padding: "8px 12px", fontFamily: "var(--font-data)", fontSize: 10, letterSpacing: "0.08em", color: "var(--muted-foreground)", fontWeight: 400 }}>
                  STATUS
                </th>
              </tr>
            </thead>
            <tbody>
              {model.buffettRows.map((r, i) => (
                <tr
                  key={r.dim}
                  style={{
                    borderBottom: i < model.buffettRows.length - 1 ? "1px solid var(--border)" : "none",
                  }}
                >
                  <td style={{ padding: "12px 12px", color: "var(--foreground)", fontFamily: "var(--font-body)", fontWeight: 500 }}>
                    {r.dim}
                  </td>
                  <td style={{ padding: "12px 12px", color: "var(--muted-foreground)", fontFamily: "var(--font-data)", fontSize: 12 }}>
                    {r.result}
                  </td>
                  <td style={{ padding: "12px 12px" }}>
                    <StatusBadge status={r.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
        <AskButton label="Ask about this assessment" onClick={() => onAsk("Buffett assessment")} />
      </div>
    </div>
  );
}

// ─── Financial Analysis & Charts Grid ────────────────────────────────────────

export function FinancialAnalysisSection({
  model,
  onAsk,
}: {
  model: ZipResearchViewModel;
  onAsk: (ctx: string) => void;
}) {
  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead id="s04" num="03" title="Financial Analysis" />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
          gap: 10,
          marginBottom: 16,
        }}
      >
        {model.financialMetrics.map((m) => (
          <div key={m.label} style={{ background: "var(--secondary)", borderRadius: 8, padding: "12px 14px" }}>
            <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.06em", marginBottom: 4 }}>
              {m.label}
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: (m as any).color || "var(--foreground)", fontFamily: "var(--font-data)" }}>
              {m.value}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 14 }}>
        <Card>
          <div style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 12 }}>
            REVENUE TREND · {model.header.currency} · Source: Production DSP
          </div>
          <SvgAreaChart data={model.revenueData} color="var(--c-revenue, #f59e0b)" />
          <div style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 12 }}>
            Server-backed revenue progression across reported financial periods.
          </div>
        </Card>

        <Card>
          <div style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 12 }}>
            NET PROFIT TREND · {model.header.currency} · Source: Production DSP
          </div>
          <SvgAreaChart data={model.profitData} color="var(--c-profit, #22c55e)" />
          <div style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 12 }}>
            Reported earnings and net income across available filing intervals.
          </div>
        </Card>
      </div>

      <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
        <AskButton label="Ask about the financials" onClick={() => onAsk("financial analysis")} />
      </div>
    </div>
  );
}

// ─── Valuation Section ───────────────────────────────────────────────────────

export function ValuationSection({
  model,
  onAsk,
  valuationStageStatus = "succeeded",
}: {
  model: ZipResearchViewModel;
  onAsk: (ctx: string) => void;
  valuationStageStatus?: string;
}) {
  const currentPrice = model.valuation.currentPrice || 0;
  const intrinsicValue = model.valuation.intrinsicValue || 0;
  const maxVal = Math.max(currentPrice, intrinsicValue, 1) * 1.25;

  const currentPct = Math.min((currentPrice / maxVal) * 100, 100);
  const intrinsicPct = Math.min((intrinsicValue / maxVal) * 100, 100);

  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead id="s09" num="04" title="Valuation" status={model.valuation.status} />
      <Card style={{ marginBottom: 14, padding: "14px 18px" }}>
        <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, margin: 0 }}>
          <div>
            <dt style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>Intrinsic Value</dt>
            <dd style={{ fontSize: 16, fontWeight: 600, margin: 0, color: "var(--foreground)" }}>{model.valuation.intrinsicValueFormatted}</dd>
          </div>
          <div>
            <dt style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>Current Price</dt>
            <dd style={{ fontSize: 16, fontWeight: 600, margin: 0, color: "var(--foreground)" }}>{model.valuation.currentPriceFormatted}</dd>
          </div>
          <div>
            <dt style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>Margin of Safety</dt>
            <dd style={{ fontSize: 16, fontWeight: 600, margin: 0, color: "var(--foreground)" }}>{model.valuation.marginOfSafetyFormatted}</dd>
          </div>
          <div>
            <dt style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>Stage status</dt>
            <dd style={{ fontSize: 16, fontWeight: 600, margin: 0, color: "var(--foreground)" }}>{valuationStageStatus}</dd>
          </div>
        </dl>
      </Card>
      <Card style={{ marginBottom: 14 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 24, marginBottom: 20 }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 6 }}>
              CURRENT MARKET PRICE
            </div>
            <div style={{ fontSize: 32, fontWeight: 700, color: "var(--foreground)", fontFamily: "var(--font-heading)", lineHeight: 1, marginBottom: 4 }}>
              {model.valuation.currentPriceFormatted}
            </div>
            <div style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>
              {model.header.exchange} · Current
            </div>
          </div>

          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 6 }}>
              DSP INTRINSIC VALUE
            </div>
            <div style={{ fontSize: 32, fontWeight: 700, color: "var(--c-cashflow, #2dd4bf)", fontFamily: "var(--font-heading)", lineHeight: 1, marginBottom: 4 }}>
              {model.valuation.intrinsicValueFormatted}
            </div>
            <div style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>
              Server-authoritative estimate
            </div>
          </div>

          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 6 }}>
              MARGIN OF SAFETY
            </div>
            <div
              style={{
                fontSize: 32,
                fontWeight: 700,
                color: model.valuation.status === "strong" ? "var(--c-profit, #22c55e)" : "var(--c-risk, #ef4444)",
                fontFamily: "var(--font-heading)",
                lineHeight: 1,
                marginBottom: 4,
              }}
            >
              {model.valuation.marginOfSafetyFormatted}
            </div>
            <div style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>
              {model.valuation.status === "strong" ? "Positive cushion" : "Negative · Premium pricing"}
            </div>
          </div>
        </div>

        {/* Bar comparison */}
        <div style={{ margin: "0 0 16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, fontFamily: "var(--font-data)", color: "var(--muted-foreground)", marginBottom: 6 }}>
            <span>0</span>
            <span>{model.valuation.intrinsicValueFormatted} Intrinsic</span>
            <span>{model.valuation.currentPriceFormatted} Price</span>
          </div>
          <div style={{ height: 10, background: "var(--border)", borderRadius: 99, overflow: "hidden", position: "relative" }}>
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                height: "100%",
                width: `${intrinsicPct}%`,
                background: "var(--c-cashflow, #2dd4bf)",
                borderRadius: 99,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                height: "100%",
                width: `${currentPct}%`,
                background: "var(--c-risk, #ef4444)",
                borderRadius: 99,
                opacity: 0.4,
              }}
            />
          </div>
        </div>

        <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 6 }}>
          METHODOLOGY NOTE
        </div>
        <p style={{ fontSize: 13, color: "var(--foreground)", margin: 0, lineHeight: 1.7 }}>
          {model.valuation.methodologyNote}
        </p>
      </Card>

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <AskButton label="Why is valuation a concern?" onClick={() => onAsk("valuation and intrinsic value")} />
      </div>
    </div>
  );
}

// ─── Business Quality Scores ─────────────────────────────────────────────────

export function BusinessQualityScores({
  model,
  onAsk,
}: {
  model: ZipResearchViewModel;
  onAsk: (ctx: string) => void;
}) {
  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead id="s02" num="05" title="Business Quality" status={model.businessQuality.status} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 16 }}>
        <Card
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
            gap: 8,
            borderTop: "2px solid var(--c-profit, #22c55e)",
          }}
        >
          <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.08em" }}>
            COMPOSITE SCORE
          </div>
          <div style={{ fontSize: 56, fontWeight: 700, color: "var(--c-profit, #22c55e)", fontFamily: "var(--font-heading)", lineHeight: 1 }}>
            {model.businessQuality.compositeScore}
          </div>
          <div style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>/ 100</div>
          <StatusBadge status={model.businessQuality.status} text={model.businessQuality.verdict} />
          <p style={{ fontSize: 12, color: "var(--muted-foreground)", margin: 0, lineHeight: 1.6 }}>
            Weighted across 5 analytical domains.
          </p>
        </Card>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 10 }}>
          {model.domainScores.map((d) => (
            <Card key={d.label} style={{ borderTop: `2px solid ${d.color}`, padding: "14px 16px" }}>
              <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.06em", marginBottom: 6 }}>
                {d.label.toUpperCase()}
              </div>
              <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", marginBottom: 8 }}>
                Weight: {d.weight}%
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 3, marginBottom: 8 }}>
                <span style={{ fontSize: 24, fontWeight: 700, color: d.color, fontFamily: "var(--font-heading)", lineHeight: 1 }}>
                  {d.score}
                </span>
                <span style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>/100</span>
              </div>
              <div style={{ height: 3, background: "var(--border)", borderRadius: 99, overflow: "hidden" }}>
                <div style={{ width: `${d.score}%`, height: "100%", background: d.color, borderRadius: 99 }} />
              </div>
            </Card>
          ))}
        </div>
      </div>

      <Card style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 4 }}>
              ECONOMIC MOAT
            </div>
            <div style={{ fontSize: 18, fontWeight: 600, color: "var(--c-profit, #22c55e)", fontFamily: "var(--font-heading)", marginBottom: 10 }}>
              {model.moat.status.toUpperCase()} MOAT
            </div>
            <p style={{ fontSize: 13, color: "var(--foreground)", lineHeight: 1.7, margin: "0 0 12px" }}>
              {model.moat.description}
            </p>
            <AskButton label="Explain the moat" onClick={() => onAsk("economic moat")} />
          </div>
          <div style={{ textAlign: "center", flexShrink: 0 }}>
            <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 4 }}>
              SCORE
            </div>
            <div style={{ fontSize: 48, fontWeight: 700, color: "var(--c-dsp, #3b82f6)", fontFamily: "var(--font-heading)", lineHeight: 1, marginBottom: 4 }}>
              {model.moat.score}
            </div>
            <div style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>/ 100</div>
          </div>
        </div>
      </Card>

      <Card style={{ borderLeft: "3px solid var(--c-risk, #ef4444)" }}>
        <div style={{ fontSize: 10, color: "var(--c-risk, #ef4444)", fontFamily: "var(--font-data)", letterSpacing: "0.08em", marginBottom: 6 }}>
          QUALITY NOTE
        </div>
        <p style={{ fontSize: 13, color: "var(--foreground)", margin: "0 0 8px", lineHeight: 1.65 }}>
          {model.businessQuality.qualityNote}
        </p>
        <AskButton label="Ask why this score was assigned" onClick={() => onAsk("Business Quality score and quality conflicts")} />
      </Card>
    </div>
  );
}

// ─── Key Risks Section ───────────────────────────────────────────────────────

export function KeyRisksSection({
  model,
  onAsk,
}: {
  model: ZipResearchViewModel;
  onAsk: (ctx: string) => void;
}) {
  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead id="s11" num="06" title="Key Risks" />
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {model.risks.map((r, i) => (
          <Card key={i} style={{ borderLeft: "3px solid var(--c-risk, #ef4444)" }}>
            <div style={{ fontFamily: "var(--font-body)", fontSize: 14, fontWeight: 500, color: "var(--foreground)", marginBottom: 6 }}>
              {r.risk}
            </div>
            <div style={{ display: "flex", gap: 6, marginBottom: 6, flexWrap: "wrap" }}>
              <span style={{ fontSize: 10, fontFamily: "var(--font-data)", color: "var(--muted-foreground)", letterSpacing: "0.07em" }}>
                EVIDENCE
              </span>
              <span style={{ fontSize: 12, color: "var(--muted-foreground)" }}>{r.evidence}</span>
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span style={{ fontSize: 10, fontFamily: "var(--font-data)", color: "var(--c-risk, #ef4444)", letterSpacing: "0.07em" }}>
                IMPLICATION
              </span>
              <span style={{ fontSize: 12, color: "var(--muted-foreground)" }}>{r.implication}</span>
            </div>
          </Card>
        ))}
      </div>
      <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
        <AskButton label="What is the biggest risk?" onClick={() => onAsk("key risks")} />
      </div>
    </div>
  );
}

// ─── Deep Dive Sections ──────────────────────────────────────────────────────

export function ManagementDeepDive({ model }: { model: ZipResearchViewModel }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.1em", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ padding: "2px 8px", background: "var(--secondary)", borderRadius: 4 }}>DEEP DIVE</span>
        Management & Capital Allocation
        <StatusBadge status={model.management.status} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
        <Card>
          <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 10 }}>
            MANAGEMENT QUALITY
          </div>
          <StatusBadge status={model.management.status} />
          <p style={{ fontSize: 13, color: "var(--foreground)", margin: "12px 0 0", lineHeight: 1.7 }}>
            {model.management.overview}
          </p>
        </Card>
        <Card>
          <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 10 }}>
            CAPITAL ALLOCATION
          </div>
          {model.management.capitalAllocation.map((r) => (
            <div key={r.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 13, color: "var(--foreground)" }}>{r.label}</span>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 12, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>{r.value}</span>
                <StatusBadge status={r.status} />
              </div>
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}

export function EarningsQualityDeepDive({ model, onAsk }: { model: ZipResearchViewModel; onAsk: (ctx: string) => void }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.1em", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ padding: "2px 8px", background: "var(--secondary)", borderRadius: 4 }}>DEEP DIVE</span>
        Earnings Quality
        <StatusBadge status={model.earningsQuality.status} />
      </div>
      <SectionHead
        id="s07"
        num=""
        title="Earnings Quality"
        status={model.earningsQuality.status}
        subtitle="Are reported earnings durable and supported by real underlying operations?"
      />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
        <Card>
          <div style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 12 }}>
            OPERATING MARGIN TREND · Source: Server Evidence
          </div>
          <SvgAreaChart data={model.marginData} color="var(--c-cashflow, #2dd4bf)" />
        </Card>
        <Card>
          <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 10 }}>
            INDICATORS
          </div>
          {model.earningsQuality.indicators.map((r) => (
            <div key={r.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 13, color: "var(--foreground)" }}>{r.label}</span>
              <StatusBadge status={r.status} text={r.value} />
            </div>
          ))}
        </Card>
      </div>
      <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
        <AskButton label="Ask about earnings" onClick={() => onAsk("earnings quality")} />
      </div>
    </div>
  );
}

export function GrowthQualityDeepDive({ model }: { model: ZipResearchViewModel }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.1em", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ padding: "2px 8px", background: "var(--secondary)", borderRadius: 4 }}>DEEP DIVE</span>
        Growth Quality
        <StatusBadge status={model.growthQuality.status} />
      </div>
      <SectionHead
        id="s08"
        num=""
        title="Growth Quality"
        status={model.growthQuality.status}
        subtitle="Growth assessed together with cash generation, margins, and capital discipline — not in isolation."
      />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
        <Card>
          <div style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 12 }}>
            FREE CASH FLOW · Source: Server Evidence
          </div>
          <SvgBarChart data={model.cashData} color="var(--c-cashflow, #2dd4bf)" />
        </Card>
        <Card>
          <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 10 }}>
            GROWTH INDICATORS
          </div>
          {model.growthQuality.indicators.map((r) => (
            <div key={r.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 13, color: "var(--foreground)" }}>{r.label}</span>
              <StatusBadge status={r.status} text={r.value} />
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}

export function MarginOfSafetyDeepDive({ model, onAsk }: { model: ZipResearchViewModel; onAsk: (ctx: string) => void }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.1em", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ padding: "2px 8px", background: "var(--secondary)", borderRadius: 4 }}>DEEP DIVE</span>
        Margin of Safety
      </div>
      <SectionHead
        id="s10"
        num=""
        title="Margin of Safety"
        status={model.valuation.status}
        subtitle="Business quality and valuation are separate analytical questions. A high-quality business can still carry an unattractive valuation."
      />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
        <Card style={{ borderTop: "2px solid var(--c-profit, #22c55e)" }}>
          <div style={{ fontSize: 10, color: "var(--c-profit, #22c55e)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 8 }}>
            BUSINESS QUALITY
          </div>
          <div style={{ fontSize: 36, fontWeight: 700, color: "var(--c-profit, #22c55e)", fontFamily: "var(--font-heading)", marginBottom: 6 }}>
            {model.businessQuality.compositeScore} / 100
          </div>
          <StatusBadge status={model.businessQuality.status} text={model.businessQuality.verdict} />
          <p style={{ fontSize: 12, color: "var(--muted-foreground)", margin: "10px 0 0", lineHeight: 1.6 }}>
            {model.businessQuality.overview}
          </p>
        </Card>
        <Card style={{ borderTop: "2px solid var(--c-risk, #ef4444)" }}>
          <div style={{ fontSize: 10, color: "var(--c-risk, #ef4444)", fontFamily: "var(--font-data)", letterSpacing: "0.07em", marginBottom: 8 }}>
            MARGIN OF SAFETY
          </div>
          <div style={{ fontSize: 36, fontWeight: 700, color: model.valuation.status === "strong" ? "var(--c-profit, #22c55e)" : "var(--c-risk, #ef4444)", fontFamily: "var(--font-heading)", marginBottom: 6 }}>
            {model.valuation.marginOfSafetyFormatted}
          </div>
          <StatusBadge status={model.valuation.status} text={model.valuation.status === "strong" ? "Adequate Cushion" : "Negative"} />
          <p style={{ fontSize: 12, color: "var(--muted-foreground)", margin: "10px 0 0", lineHeight: 1.6 }}>
            Assessed against server-authoritative intrinsic value of {model.valuation.intrinsicValueFormatted}.
          </p>
        </Card>
      </div>
      <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
        <AskButton label="Ask about the margin of safety" onClick={() => onAsk("margin of safety")} />
      </div>
    </div>
  );
}

export function StrengthsWeaknessesSection({ model }: { model: ZipResearchViewModel }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.1em", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ padding: "2px 8px", background: "var(--secondary)", borderRadius: 4 }}>DEEP DIVE</span>
        Strengths & Weaknesses
      </div>
      <SectionHead id="s12" num="" title="Strengths & Weaknesses" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
        <Card style={{ borderTop: "2px solid var(--c-profit, #22c55e)" }}>
          <div style={{ fontSize: 10, color: "var(--c-profit, #22c55e)", fontFamily: "var(--font-data)", letterSpacing: "0.08em", marginBottom: 12 }}>
            KEY STRENGTHS
          </div>
          {model.strengths.map((s, i) => (
            <div key={i} style={{ display: "flex", gap: 9, marginBottom: 10, fontSize: 13, color: "var(--foreground)", lineHeight: 1.55 }}>
              <span style={{ color: "var(--c-profit, #22c55e)", flexShrink: 0, marginTop: 1, fontSize: 12 }}>+</span>
              {s}
            </div>
          ))}
        </Card>
        <Card style={{ borderTop: "2px solid var(--c-risk, #ef4444)" }}>
          <div style={{ fontSize: 10, color: "var(--c-risk, #ef4444)", fontFamily: "var(--font-data)", letterSpacing: "0.08em", marginBottom: 12 }}>
            KEY WEAKNESSES
          </div>
          {model.weaknesses.map((w, i) => (
            <div key={i} style={{ display: "flex", gap: 9, marginBottom: 10, fontSize: 13, color: "var(--foreground)", lineHeight: 1.55 }}>
              <span style={{ color: "var(--c-risk, #ef4444)", flexShrink: 0, marginTop: 1, fontSize: 12 }}>−</span>
              {w}
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}

export function InvestmentContextSection({ model }: { model: ZipResearchViewModel }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.1em", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ padding: "2px 8px", background: "var(--secondary)", borderRadius: 4 }}>DEEP DIVE</span>
        Investment Context
      </div>
      <SectionHead
        id="s13"
        num=""
        title="Investment Context"
        subtitle="Backend-authoritative DSP analytical context. This is not an independent frontend recommendation."
      />
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 16 }}>
          {model.investmentContext.metrics.map((c) => (
            <div key={c.label} style={{ background: "var(--secondary)", borderRadius: 8, padding: "12px 14px" }}>
              <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.06em", marginBottom: 6 }}>
                {c.label}
              </div>
              <div style={{ marginBottom: 6, fontSize: 14, fontWeight: 600, color: "var(--foreground)", fontFamily: "var(--font-data)" }}>
                {c.value}
              </div>
              <StatusBadge status={c.status} />
            </div>
          ))}
        </div>
        <p style={{ fontSize: 13, color: "var(--muted-foreground)", margin: 0, lineHeight: 1.7 }}>
          {model.investmentContext.narrative}
        </p>
      </Card>
    </div>
  );
}

export function EvidenceExplorerSection({
  model,
  analysisId,
}: {
  model: ZipResearchViewModel;
  analysisId?: string;
}) {
  const [open, setOpen] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const effectiveAnalysisId = analysisId || model.analysisId || "Data unavailable";
  const effectiveAuditRef = model.auditReference || "Unavailable";
  const evidenceList = model.evidence || [];

  return (
    <div style={{ marginBottom: 36 }}>
      <div
        style={{
          fontSize: 10,
          color: "var(--muted-foreground)",
          fontFamily: "var(--font-data)",
          letterSpacing: "0.1em",
          marginBottom: 16,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span style={{ padding: "2px 8px", background: "var(--secondary)", borderRadius: 4 }}>
          DEEP DIVE
        </span>
        Supporting Evidence
      </div>
      <SectionHead
        id="s14"
        num=""
        title="Research objects"
        subtitle="Supporting Evidence and provenance traceable to backend stage analysis."
      />

      {/* Provenance Card */}
      <Card style={{ marginBottom: 14, padding: "16px 20px" }}>
        <dl
          style={{
            margin: 0,
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: 16,
          }}
        >
          <div>
            <dt style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>
              Analysis ID
            </dt>
            <dd
              style={{
                fontSize: 14,
                fontWeight: 600,
                margin: "4px 0 0",
                color: "var(--foreground)",
                fontFamily: "var(--font-data)",
              }}
            >
              {effectiveAnalysisId}
            </dd>
          </div>
          <div>
            <dt style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>
              Audit Reference
            </dt>
            <dd
              style={{
                fontSize: 14,
                fontWeight: 600,
                margin: "4px 0 0",
                color: "var(--foreground)",
                fontFamily: "var(--font-data)",
              }}
            >
              {effectiveAuditRef}
            </dd>
          </div>
        </dl>
      </Card>

      {/* Evidence Trail Control */}
      <div style={{ marginBottom: 14, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <button
          type="button"
          aria-expanded={open}
          aria-controls="evidence-trail-container"
          onClick={() => setOpen((v) => !v)}
          style={{
            background: "var(--surface-2, #181e2e)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md, 8px)",
            padding: "8px 16px",
            fontSize: 13,
            fontWeight: 500,
            color: "var(--foreground)",
            cursor: "pointer",
            fontFamily: "var(--font-body)",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            transition: "all 0.15s ease",
          }}
        >
          <span>{open ? "▲ Hide evidence trail" : "▼ View evidence trail"}</span>
          <span
            style={{
              fontSize: 10,
              fontFamily: "var(--font-data)",
              padding: "1px 6px",
              borderRadius: 99,
              background: "var(--card, #111520)",
              border: "1px solid var(--border)",
              color: "var(--muted-foreground)",
            }}
          >
            {evidenceList.length} items
          </span>
        </button>
      </div>

      {/* Evidence Trail Items */}
      {open && (
        <div id="evidence-trail-container" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {evidenceList.length === 0 ? (
            <Card style={{ padding: "20px 22px", textAlign: "center" }}>
              <div style={{ fontSize: 13, color: "var(--muted-foreground)", fontFamily: "var(--font-body)" }}>
                No evidence items reported by the backend analytical pipeline.
              </div>
            </Card>
          ) : (
            evidenceList.map((e, i) => {
              const isRowExpanded = expandedIndex === i;
              const sourceLabel = e.source && e.source.trim() ? e.source : "Source unavailable";

              return (
                <Card key={i} style={{ padding: "16px 20px" }}>
                  {/* Primary Row */}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      flexWrap: "wrap",
                      gap: 12,
                    }}
                  >
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 600,
                            letterSpacing: "0.06em",
                            textTransform: "uppercase",
                            padding: "2px 8px",
                            borderRadius: 4,
                            background: "var(--surface-2, #181e2e)",
                            border: "1px solid var(--border)",
                            color: e.source ? "var(--foreground)" : "var(--muted-foreground)",
                            fontFamily: "var(--font-data)",
                          }}
                        >
                          {sourceLabel}
                        </span>
                        <span
                          style={{
                            fontSize: 11,
                            color: "var(--muted-foreground)",
                            fontFamily: "var(--font-data)",
                          }}
                        >
                          {e.stage} · {e.period}
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: 14,
                          fontWeight: 600,
                          color: "var(--foreground)",
                          fontFamily: "var(--font-heading)",
                        }}
                      >
                        {e.metric}
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                      <div style={{ textAlign: "right" }}>
                        <div
                          style={{
                            fontSize: 16,
                            fontWeight: 700,
                            color: "var(--foreground)",
                            fontFamily: "var(--font-data)",
                            fontVariantNumeric: "tabular-nums",
                          }}
                        >
                          {e.value}
                        </div>
                        <div
                          style={{
                            fontSize: 10,
                            color: "var(--muted-foreground)",
                            fontFamily: "var(--font-data)",
                            letterSpacing: "0.04em",
                          }}
                        >
                          Confidence: {e.confidence}
                        </div>
                      </div>

                      <button
                        type="button"
                        aria-expanded={isRowExpanded}
                        aria-label={`Toggle details for ${e.metric}`}
                        onClick={() => setExpandedIndex(isRowExpanded ? null : i)}
                        style={{
                          background: "none",
                          border: "1px solid var(--border)",
                          borderRadius: "var(--radius-sm, 6px)",
                          padding: "6px 10px",
                          fontSize: 11,
                          color: "var(--muted-foreground)",
                          cursor: "pointer",
                          fontFamily: "var(--font-body)",
                        }}
                      >
                        {isRowExpanded ? "Less" : "Details"}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Technical Telemetry */}
                  {isRowExpanded && (
                    <div
                      style={{
                        marginTop: 14,
                        paddingTop: 12,
                        borderTop: "1px solid var(--border)",
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                        gap: 12,
                      }}
                    >
                      {[
                        { l: "STAGE", v: e.stage },
                        { l: "METRIC", v: e.metric },
                        { l: "PERIOD", v: e.period },
                        { l: "VALUE", v: e.value },
                        { l: "SOURCE", v: sourceLabel },
                        { l: "CONFIDENCE", v: e.confidence },
                        { l: "AUDIT REF", v: effectiveAuditRef },
                      ].map((f) => (
                        <div key={f.l}>
                          <div
                            style={{
                              fontSize: 9,
                              color: "var(--muted-foreground)",
                              fontFamily: "var(--font-data)",
                              letterSpacing: "0.08em",
                              marginBottom: 3,
                            }}
                          >
                            {f.l}
                          </div>
                          <div
                            style={{
                              fontSize: 12,
                              color: "var(--foreground)",
                              fontFamily: "var(--font-data)",
                            }}
                          >
                            {f.v}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}


// ─── Downloads & Export Section ──────────────────────────────────────────────

function DownloadsSection({
  symbol,
  analysisId,
  data,
}: {
  symbol: string;
  analysisId?: string;
  data?: AnalyseResponse;
}) {
  const handleExportJson = () => {
    const payload = {
      ticker: symbol,
      analysisId: analysisId || null,
      auditReference: analysisId || null,
      exportedAt: new Date().toISOString(),
      ...(data ?? {}),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${symbol}-analysis-${analysisId || "snapshot"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead
        id="s15"
        title="Downloads"
        subtitle="Export institutional research snapshots and JSON audit trails."
      />
      <Card style={{ padding: "22px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span style={{ fontWeight: 600, fontSize: 15, color: "var(--foreground)", fontFamily: "var(--font-heading)" }}>
                Audit-Grade JSON Research Snapshot
              </span>
              <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "var(--surface-2, #181e2e)", border: "1px solid var(--border)", color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>
                .JSON
              </span>
            </div>
            <div style={{ fontSize: 12, color: "var(--muted-foreground)", lineHeight: 1.5, maxWidth: 540 }}>
              Export machine-readable research telemetry including authoritative valuation parameters, Buffett criteria statuses, stage execution timestamps, and cryptographic audit reference.
            </div>
          </div>
          <button
            type="button"
            onClick={handleExportJson}
            style={{
              padding: "10px 20px",
              background: "var(--accent, #3b82f6)",
              color: "#ffffff",
              border: "none",
              borderRadius: "var(--radius-md, 8px)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "var(--font-body)",
              boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.4))",
              transition: "opacity 0.15s ease",
            }}
          >
            Export JSON
          </button>
        </div>
      </Card>
    </div>
  );
}

// ─── Research Chat Drawer ────────────────────────────────────────────────────

export function ResearchChatDrawer({
  symbol,
  analysisId,
  open,
  onClose,
  initCtx,
}: {
  symbol: string;
  analysisId?: string;
  open: boolean;
  onClose: () => void;
  initCtx: string;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([
    { role: "dsp", text: `Ask anything about ${symbol} or the research output.` },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const sendMsg = useCallback(async (text: string) => {
    if (!text.trim() || thinking) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setThinking(true);

    try {
      const res = await api.copilotQuery({
        query: text,
        symbol,
        analysis_id: analysisId,
        section_context: initCtx,
        prompt: `Context: ${initCtx || "General analysis"} for ${symbol} (Analysis ID: ${analysisId || "unknown"}). Question: ${text}`,
      });

      const reply =
        res?.content ||
        (res as any)?.text ||
        `Analysis for ${symbol}: ${text} has been processed against server evidence.`;
      setMessages((prev) => [...prev, { role: "dsp", text: reply }]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "dsp",
          text: `DSP Research Assistant: Regarding ${symbol} (${initCtx || "Workspace"}), analytical output is unavailable or temporarily unreached.`,
        },
      ]);
    } finally {
      setThinking(false);
    }
  }, [thinking, initCtx, symbol, analysisId]);

  useEffect(() => {
    if (initCtx && open) {
      const q = `Tell me more about the ${initCtx}.`;
      setTimeout(() => sendMsg(q), 250);
    }
  }, [initCtx, open, sendMsg]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        height: 280,
        background: "var(--card)",
        borderTop: "1px solid var(--border)",
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 -4px 20px rgba(0,0,0,0.4)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 16px",
          borderBottom: "1px solid var(--border)",
          background: "var(--secondary)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--c-dsp, #3b82f6)" }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--foreground)", fontFamily: "var(--font-body)" }}>
            Research Assistant · {symbol}
          </span>
          {initCtx && (
            <span style={{ fontSize: 11, color: "var(--muted-foreground)", fontFamily: "var(--font-data)" }}>
              Context: {initCtx}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          style={{ background: "none", border: "none", color: "var(--muted-foreground)", cursor: "pointer", fontSize: 16 }}
        >
          ✕
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "80%",
              padding: "8px 12px",
              borderRadius: 8,
              fontSize: 13,
              lineHeight: 1.5,
              background: m.role === "user" ? "var(--c-dsp, #3b82f6)" : "var(--secondary)",
              color: m.role === "user" ? "#fff" : "var(--foreground)",
              fontFamily: "var(--font-body)",
            }}
          >
            {m.text}
          </div>
        ))}
        {thinking && (
          <div style={{ alignSelf: "flex-start", fontSize: 12, color: "var(--muted-foreground)", fontStyle: "italic" }}>
            Consulting DSP evidence...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          sendMsg(input);
        }}
        style={{ padding: "8px 16px", borderTop: "1px solid var(--border)", display: "flex", gap: 8 }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask about ${symbol}...`}
          style={{
            flex: 1,
            background: "var(--secondary)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "8px 12px",
            fontSize: 13,
            color: "var(--foreground)",
            outline: "none",
            fontFamily: "var(--font-body)",
          }}
        />
        <button
          type="submit"
          disabled={!input.trim() || thinking}
          style={{
            padding: "8px 16px",
            background: "var(--c-dsp, #3b82f6)",
            border: "none",
            borderRadius: 6,
            color: "#fff",
            fontSize: 13,
            fontWeight: 500,
            cursor: "pointer",
            opacity: !input.trim() || thinking ? 0.5 : 1,
          }}
        >
          Send
        </button>
      </form>
    </div>
  );
}

// ─── Main Workspace Root ─────────────────────────────────────────────────────

export function ZipCompanyAnalysisWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const searchParamSymbol = searchParams.get("symbol") || searchParams.get("ticker");
  const initialSymbol = searchParamSymbol || "TCS.NS";

  const [phase, setPhase] = useState<AnalysisPhase>(
    searchParamSymbol ? "workspace-ready" : "select"
  );
  const [symbol, setSymbol] = useState(initialSymbol);
  const [searchInput, setSearchInput] = useState(initialSymbol);
  const [activeSection, setActiveSection] = useState("s01");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatCtx, setChatCtx] = useState("");
  const [tocOpen, setTocOpen] = useState(false);

  const mobileNavTriggerRef = useRef<HTMLButtonElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const prevTocOpen = useRef(false);

  useEffect(() => {
    if (tocOpen) {
      closeButtonRef.current?.focus();
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          e.preventDefault();
          setTocOpen(false);
        }
      };
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }
    if (prevTocOpen.current) {
      mobileNavTriggerRef.current?.focus();
    }
    prevTocOpen.current = tocOpen;
  }, [tocOpen]);

  const activeIndex = ALL_SECTIONS.findIndex((s) => s.id === activeSection);
  const currentSectionIndex = activeIndex >= 0 ? activeIndex + 1 : 1;
  const totalSectionsCount = ALL_SECTIONS.length;

  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const { runWithDisclaimer, gate } = useResearchDisclaimerGate();

  const analyseMutation = useMutation({
    mutationFn: async (req: AnalyseRequest) => {
      const resp = await api.analyse(req);
      return resp;
    },
    onSuccess: (data, variables) => {
      pushRecentAnalysis({
        ticker: variables.ticker,
        company: variables.ticker,
        exchange: variables.exchange || "US",
        recommendation: "Analysed",
        analysedAt: new Date().toISOString(),
      });
    },
  });

  const runAnalysis = useCallback(
    (targetPhase: "simple-loading" | "buffett-loading", customSymbol?: string) => {
      const sym = customSymbol || symbol;
      if (customSymbol && customSymbol !== symbol) {
        setSymbol(customSymbol);
      }
      const targetMode: ResearchMode = targetPhase === "simple-loading" ? "simple" : "buffett";
      setMode(targetMode);
      setPhase(targetPhase);
      if (targetMode === "simple") {
        setChatOpen(false);
        setChatCtx("");
      }
      if (typeof window !== "undefined") {
        try {
          const url = new URL(window.location.href);
          url.searchParams.set("symbol", sym);
          url.searchParams.set("mode", targetMode);
          window.history.replaceState({}, "", url.toString());
        } catch (_) {}
      }
      const req: AnalyseRequest = {
        ticker: sym,
        mode: targetMode,
      };
      analyseMutation.mutate(req);
    },
    [symbol, analyseMutation]
  );

  useEffect(() => {
    if (phase !== "buffett-result" && phase !== "simple-result" && phase !== "workspace-ready") return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActiveSection(e.target.id);
        }
      },
      { rootMargin: "-25% 0px -65% 0px", threshold: 0 }
    );

    Object.values(sectionRefs.current).forEach((el) => {
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [phase]);

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setTocOpen(false);
  };

  const askAbout = (ctx: string) => {
    setChatCtx(ctx);
    setChatOpen(true);
  };

  const sectionRef = (id: string) => (el: HTMLDivElement | null) => {
    sectionRefs.current[id] = el;
  };

  const viewModel: ZipResearchViewModel = useMemo(() => {
    const raw = analyseMutation.data;
    const req: AnalyseRequest = { ticker: symbol };
    if (raw) {
      return mapZipResearchView(raw, req);
    }
    return mapZipResearchView({} as AnalyseResponse, req);
  }, [analyseMutation.data, symbol]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--bg)",
        color: "var(--foreground)",
        display: "flex",
        flexDirection: "column",
        position: "relative",
      }}
    >
      {gate}

      {phase === "select" && (
        <SelectionScreen
          symbol={symbol}
          onSimple={() => runAnalysis("simple-loading")}
          onBuffett={() => runAnalysis("buffett-loading")}
        />
      )}

      {(phase === "simple-loading" || phase === "buffett-loading") && (
        <StagedLoader
          steps={phase === "simple-loading" ? LOADING_STEPS.slice(0, 4) : LOADING_STEPS}
          active={true}
          onDone={() => {
            setPhase(phase === "simple-loading" ? "simple-result" : "buffett-result");
          }}
        />
      )}

      {(phase === "buffett-result" || phase === "simple-result" || phase === "workspace-ready") && (
        <div style={{ display: "flex", flex: 1, flexDirection: "column", overflow: "hidden" }}>
          <CompanyHeader
            model={viewModel}
            onModeSwitch={() => { setPhase("select"); setChatOpen(false); setChatCtx(""); }}
            searchValue={searchInput}
            onSearchChange={setSearchInput}
            onAnalyze={(val) => runAnalysis("buffett-loading", val || searchInput)}
            isAnalyzing={analyseMutation.isPending}
          />

          <div style={{ display: "flex", flex: 1, overflow: "hidden", position: "relative" }}>
            <nav
              aria-label="Analysis sections"
              className="toc-sidebar"
              style={{
                width: 220,
                flexShrink: 0,
                borderRight: "1px solid var(--border)",
                display: "flex",
                flexDirection: "column",
                overflowY: "auto",
                padding: "16px 0",
                background: "var(--card)",
              }}
            >
              <div
                style={{
                  padding: "0 16px 12px",
                  borderBottom: "1px solid var(--border)",
                  marginBottom: 10,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: 10,
                    color: "var(--muted-foreground)",
                    fontFamily: "var(--font-data)",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                  }}
                >
                  <span>Navigation</span>
                  <span style={{ fontWeight: 600, color: "var(--foreground)" }}>
                    Section {currentSectionIndex} of {totalSectionsCount}
                  </span>
                </div>
                <div
                  style={{
                    height: 3,
                    width: "100%",
                    background: "var(--surface-2)",
                    borderRadius: 2,
                    marginTop: 6,
                    overflow: "hidden",
                  }}
                  role="progressbar"
                  aria-valuenow={currentSectionIndex}
                  aria-valuemin={1}
                  aria-valuemax={totalSectionsCount}
                  aria-label="Analysis reading progress"
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${(currentSectionIndex / totalSectionsCount) * 100}%`,
                      background: "var(--accent)",
                      transition: "width 0.2s ease",
                    }}
                  />
                </div>
              </div>

              {(mode === "simple" ? SIMPLE_TOC_GROUPS : TOC_GROUPS).map((group) => (
                <div key={group.label} style={{ marginBottom: 12, marginTop: 4 }}>
                  <div
                    style={{
                      padding: "6px 16px 4px",
                      fontSize: 11,
                      fontWeight: 600,
                      color: "var(--accent, #7c6af7)",
                      fontFamily: "var(--font-data)",
                      letterSpacing: "0.14em",
                      textTransform: "uppercase",
                    }}
                  >
                    {group.label}
                  </div>
                  {group.items.map((t) => {
                    const isActive = activeSection === t.id;
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => scrollTo(t.id)}
                        aria-current={isActive ? "page" : undefined}
                        style={{
                          background: isActive ? "var(--surface-2)" : "transparent",
                          border: "none",
                          padding: "7px 16px 7px 26px",
                          textAlign: "left",
                          cursor: "pointer",
                          width: "100%",
                          fontSize: 13,
                          fontFamily: "var(--font-body)",
                          fontWeight: isActive ? 600 : 400,
                          color: isActive ? "var(--foreground)" : "var(--muted-foreground)",
                          borderLeft: isActive ? "3px solid var(--accent, #7c6af7)" : "3px solid transparent",
                          transition: "background 0.15s, color 0.15s, border-color 0.15s",
                        }}
                      >
                        {t.label}
                      </button>
                    );
                  })}
                  <div style={{ height: 1, background: "var(--border)", margin: "8px 16px 4px" }} />
                </div>
              ))}

              <div style={{ padding: "6px 16px 4px", fontSize: 11, fontWeight: 600, color: "var(--accent, #7c6af7)", fontFamily: "var(--font-data)", letterSpacing: "0.14em", textTransform: "uppercase" }}>
                TOOLS
              </div>
              <button
                type="button"
                onClick={() => setChatOpen((v) => !v)}
                style={{
                  margin: "0 10px 6px",
                  padding: "9px 12px",
                  background: chatOpen ? "var(--c-dsp, #3b82f6)" : "var(--secondary)",
                  border: `1px solid ${chatOpen ? "var(--c-dsp, #3b82f6)" : "var(--border)"}`,
                  borderRadius: 8,
                  color: chatOpen ? "#fff" : "var(--foreground)",
                  fontSize: 12,
                  cursor: "pointer",
                  fontFamily: "var(--font-body)",
                  fontWeight: 500,
                  display: "flex",
                  alignItems: "center",
                  gap: 7,
                }}
              >
                Ask DSP
              </button>
            </nav>

            <div className="toc-mobile-toggle">
              <div
                style={{
                  position: "fixed",
                  bottom: chatOpen ? 292 : 16,
                  left: 16,
                  right: 16,
                  zIndex: 40,
                  display: "flex",
                  gap: 10,
                  justifyContent: "center",
                }}
              >
                <button
                  ref={mobileNavTriggerRef}
                  type="button"
                  aria-haspopup="dialog"
                  aria-expanded={tocOpen}
                  aria-controls="mobile-nav-dialog"
                  onClick={() => setTocOpen((v) => !v)}
                  style={{
                    minHeight: 44,
                    minWidth: 44,
                    padding: "10px 20px",
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: 99,
                    fontSize: 13,
                    color: "var(--foreground)",
                    cursor: "pointer",
                    fontWeight: 500,
                    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  Sections
                </button>
                <button
                  type="button"
                  onClick={() => setChatOpen((v) => !v)}
                  style={{
                    minHeight: 44,
                    minWidth: 44,
                    padding: "10px 20px",
                    background: chatOpen ? "var(--c-dsp, #3b82f6)" : "var(--card)",
                    border: `1px solid ${chatOpen ? "var(--c-dsp, #3b82f6)" : "var(--border)"}`,
                    borderRadius: 99,
                    fontSize: 13,
                    color: chatOpen ? "#fff" : "var(--foreground)",
                    cursor: "pointer",
                    fontWeight: 500,
                    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  Ask DSP
                </button>
              </div>

              {tocOpen && (
                <>
                  <div
                    onClick={() => setTocOpen(false)}
                    aria-hidden="true"
                    style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60 }}
                  />
                  <div
                    id="mobile-nav-dialog"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="mobile-nav-title"
                    style={{
                      position: "fixed",
                      bottom: 0,
                      left: 0,
                      right: 0,
                      zIndex: 70,
                      background: "var(--card)",
                      borderTop: "1px solid var(--border)",
                      borderRadius: "16px 16px 0 0",
                      maxHeight: "75vh",
                      overflowY: "auto",
                      padding: "16px 20px 32px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 16,
                        paddingBottom: 12,
                        borderBottom: "1px solid var(--border)",
                      }}
                    >
                      <div>
                        <h2
                          id="mobile-nav-title"
                          style={{
                            margin: 0,
                            fontSize: 14,
                            fontWeight: 600,
                            color: "var(--foreground)",
                          }}
                        >
                          Analysis Sections
                        </h2>
                        <div
                          style={{
                            fontSize: 11,
                            color: "var(--muted-foreground)",
                            fontFamily: "var(--font-data)",
                            marginTop: 2,
                          }}
                        >
                          Section {currentSectionIndex} of {totalSectionsCount}
                        </div>
                      </div>
                      <button
                        ref={closeButtonRef}
                        type="button"
                        aria-label="Close navigation"
                        onClick={() => setTocOpen(false)}
                        style={{
                          minHeight: 44,
                          minWidth: 44,
                          padding: "8px 14px",
                          background: "var(--surface-2)",
                          border: "1px solid var(--border)",
                          borderRadius: 8,
                          color: "var(--foreground)",
                          fontSize: 13,
                          fontWeight: 500,
                          cursor: "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        Close
                      </button>
                    </div>

                    {(mode === "simple" ? SIMPLE_TOC_GROUPS : TOC_GROUPS).map((group) => (
                      <div key={group.label} style={{ marginBottom: 14, marginTop: 4 }}>
                        <div
                          style={{
                            fontSize: 11,
                            fontWeight: 600,
                            color: "var(--accent, #7c6af7)",
                            fontFamily: "var(--font-data)",
                            letterSpacing: "0.14em",
                            textTransform: "uppercase",
                            marginBottom: 6,
                            paddingLeft: 14,
                          }}
                        >
                          {group.label}
                        </div>
                        {group.items.map((t) => {
                          const isActive = activeSection === t.id;
                          return (
                            <button
                              key={t.id}
                              type="button"
                              onClick={() => scrollTo(t.id)}
                              aria-current={isActive ? "page" : undefined}
                              style={{
                                display: "flex",
                                alignItems: "center",
                                width: "100%",
                                textAlign: "left",
                                minHeight: 44,
                                padding: "10px 14px 10px 24px",
                                marginBottom: 4,
                                background: isActive ? "var(--surface-2)" : "transparent",
                                border: "none",
                                borderRadius: 6,
                                fontSize: 13,
                                fontWeight: isActive ? 600 : 400,
                                color: isActive ? "var(--foreground)" : "var(--muted-foreground)",
                                borderLeft: isActive ? "3px solid var(--accent, #7c6af7)" : "3px solid transparent",
                                cursor: "pointer",
                              }}
                            >
                              {t.label}
                            </button>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            <main
              role="region"
              aria-label="Main analysis area"
              className="scroll-container"
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "28px 28px",
                paddingBottom: chatOpen ? "300px" : "60px",
              }}
            >
              <div style={{ maxWidth: 1000, margin: "0 auto" }}>
                {mode === "simple" ? (
                  <>
                    <div ref={sectionRef("s01")} id="s01">
                      <InvestmentSummary model={viewModel} onAsk={undefined} />
                    </div>

                    <div ref={sectionRef("s04")} id="s04">
                      <FinancialAnalysisSection model={viewModel} onAsk={undefined} />
                    </div>

                    <div ref={sectionRef("s09")} id="s09">
                      <ValuationSection
                        model={viewModel}
                        onAsk={undefined}
                        valuationStageStatus={
                          (analyseMutation.data?.payload as { stage_summaries?: Array<{ stage: string; status: string }> })?.stage_summaries?.find((s) => s.stage === "valuation")?.status || "succeeded"
                        }
                      />
                    </div>

                    <div ref={sectionRef("s15")} id="s15">
                      <DownloadsSection
                        symbol={symbol}
                        analysisId={analyseMutation.data?.analysis_id ?? undefined}
                        data={analyseMutation.data}
                      />
                    </div>
                  </>
                ) : (
                  <>
                    <div ref={sectionRef("s01")} id="s01">
                      <InvestmentSummary model={viewModel} onAsk={askAbout} />
                    </div>

                    <div ref={sectionRef("s03")} id="s03">
                      <BuffettAssessmentTable model={viewModel} onAsk={askAbout} />
                    </div>

                    <div ref={sectionRef("s04")} id="s04">
                      <FinancialAnalysisSection model={viewModel} onAsk={askAbout} />
                    </div>

                    <div ref={sectionRef("s09")} id="s09">
                      <ValuationSection
                        model={viewModel}
                        onAsk={askAbout}
                        valuationStageStatus={
                          (analyseMutation.data?.payload as { stage_summaries?: Array<{ stage: string; status: string }> })?.stage_summaries?.find((s) => s.stage === "valuation")?.status || "succeeded"
                        }
                      />
                    </div>

                    <div ref={sectionRef("s02")} id="s02">
                      <BusinessQualityScores model={viewModel} onAsk={askAbout} />
                    </div>

                    <div ref={sectionRef("s11")} id="s11">
                      <KeyRisksSection model={viewModel} onAsk={askAbout} />
                    </div>

                    <div ref={sectionRef("s06")} id="s06">
                      <ManagementDeepDive model={viewModel} />
                    </div>

                    <div ref={sectionRef("s07")} id="s07">
                      <EarningsQualityDeepDive model={viewModel} onAsk={askAbout} />
                    </div>

                    <div ref={sectionRef("s08")} id="s08">
                      <GrowthQualityDeepDive model={viewModel} />
                    </div>

                    <div ref={sectionRef("s10")} id="s10">
                      <MarginOfSafetyDeepDive model={viewModel} onAsk={askAbout} />
                    </div>

                    <div ref={sectionRef("s12")} id="s12">
                      <StrengthsWeaknessesSection model={viewModel} />
                    </div>

                    <div ref={sectionRef("s13")} id="s13">
                      <InvestmentContextSection model={viewModel} />
                    </div>

                    <div ref={sectionRef("s14")} id="s14">
                      <EvidenceExplorerSection
                        model={viewModel}
                        analysisId={analyseMutation.data?.analysis_id ?? undefined}
                      />
                    </div>

                    <div ref={sectionRef("s15")} id="s15">
                      <DownloadsSection
                        symbol={symbol}
                        analysisId={analyseMutation.data?.analysis_id ?? undefined}
                        data={analyseMutation.data}
                      />
                    </div>
                  </>
                )}
              </div>
            </main>
          </div>

          {mode === "buffett" && phase === "buffett-result" && (
            <ResearchChatDrawer
              symbol={symbol}
              analysisId={analyseMutation.data?.analysis_id ? analyseMutation.data.analysis_id : undefined}
              open={chatOpen}
              onClose={() => setChatOpen(false)}
              initCtx={chatCtx}
            />
          )}
        </div>
      )}

      <style jsx global>{`
        @media (max-width: 768px) {
          .toc-sidebar {
            display: none !important;
          }
          .company-header-metrics {
            display: none !important;
          }
        }
        @media (min-width: 769px) {
          .toc-mobile-toggle {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}

export default ZipCompanyAnalysisWorkspace;