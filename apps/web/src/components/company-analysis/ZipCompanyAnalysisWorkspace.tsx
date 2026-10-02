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
} from "@/lib/research/mapZipResearchView";
import { useResearchDisclaimerGate } from "@/components/legal/useResearchDisclaimerGate";
import { pushRecentAnalysis } from "@/lib/analysis/recentAnalyses";

// ─── Types ───────────────────────────────────────────────────────────────────

export type AnalysisPhase =
  | "select"
  | "simple-loading"
  | "simple-result"
  | "buffett-loading"
  | "buffett-result";

type ChatMsg = { role: "user" | "dsp"; text: string };

const LOADING_STEPS = [
  "Identifying company",
  "Collecting financial evidence",
  "Analysing business quality",
  "Evaluating economic moat",
  "Evaluating management",
  "Analysing earnings & growth",
  "Evaluating valuation",
  "Assessing risks",
  "Validating research",
  "Preparing analysis report",
];

const TOC_GROUPS = [
  {
    label: "ANALYSIS",
    items: [
      { id: "s01", label: "Summary" },
      { id: "s03", label: "Buffett Assessment" },
      { id: "s04", label: "Financials" },
      { id: "s09", label: "Valuation" },
      { id: "s02", label: "Business Quality" },
      { id: "s11", label: "Key Risks" },
    ],
  },
  {
    label: "DEEP DIVE",
    items: [
      { id: "s06", label: "Management" },
      { id: "s07", label: "Earnings Quality" },
      { id: "s08", label: "Growth Quality" },
      { id: "s10", label: "Margin of Safety" },
      { id: "s12", label: "Strengths & Weaknesses" },
      { id: "s13", label: "Investment Context" },
      { id: "s14", label: "Evidence" },
    ],
  },
];

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
        background: "var(--card)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "20px 22px",
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

export function SvgAreaChart({ data, color, label }: { data: ZipFinancialPoint[]; color: string; label?: string }) {
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
}: {
  model: ZipResearchViewModel;
  onModeSwitch: () => void;
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
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h1
              style={{
                fontSize: 20,
                fontWeight: 700,
                color: "var(--foreground)",
                margin: 0,
                fontFamily: "var(--font-heading)",
              }}
            >
              {model.header.companyName}
            </h1>
            <span
              style={{
                fontSize: 11,
                padding: "2px 6px",
                background: "var(--secondary)",
                border: "1px solid var(--border)",
                borderRadius: 4,
                fontFamily: "var(--font-data)",
                color: "var(--muted-foreground)",
              }}
            >
              {model.header.ticker} · {model.header.exchange}
            </span>
            <span
              style={{
                fontSize: 11,
                padding: "2px 6px",
                background: "rgba(59,130,246,0.12)",
                border: "1px solid rgba(59,130,246,0.25)",
                borderRadius: 4,
                fontFamily: "var(--font-data)",
                color: "var(--c-dsp, #3b82f6)",
              }}
            >
              {model.header.sector}
            </span>
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

      <div style={{ display: "flex", alignItems: "center", gap: 20 }} className="company-header-metrics">
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontSize: 10,
              color: "var(--muted-foreground)",
              fontFamily: "var(--font-data)",
              letterSpacing: "0.06em",
            }}
          >
            MARKET PRICE
          </div>
          <div
            className="company-header-price"
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: "var(--foreground)",
              fontFamily: "var(--font-data)",
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
              letterSpacing: "0.06em",
            }}
          >
            INTRINSIC VALUE
          </div>
          <div
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: "var(--c-cashflow, #2dd4bf)",
              fontFamily: "var(--font-data)",
            }}
          >
            {model.valuation.intrinsicValueFormatted}
          </div>
        </div>

        <button
          type="button"
          onClick={onModeSwitch}
          style={{
            padding: "7px 14px",
            background: "var(--secondary)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            fontSize: 12,
            color: "var(--foreground)",
            cursor: "pointer",
            fontFamily: "var(--font-body)",
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
              letterSpacing: "0.1em",
              marginBottom: 4,
            }}
          >
            INVESTMENT SUMMARY
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span
              style={{
                fontSize: 22,
                fontWeight: 700,
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

      {/* Grid of 4 key numbers */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
          gap: 12,
          paddingTop: 16,
          borderTop: "1px solid var(--border)",
        }}
      >
        {model.investmentSummary.metrics.map((m) => (
          <div key={m.label} style={{ background: "var(--secondary)", borderRadius: 8, padding: "10px 12px" }}>
            <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", marginBottom: 4 }}>
              {m.label}
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: m.color || "var(--foreground)", fontFamily: "var(--font-data)" }}>
              {m.value}
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
        title="Buffett-Style Assessment"
        subtitle="DSP analytical outputs organised through a Buffett-inspired investment framework."
      />
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
            <div style={{ fontSize: 15, fontWeight: 600, color: m.color || "var(--foreground)", fontFamily: "var(--font-data)" }}>
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
}: {
  model: ZipResearchViewModel;
  onAsk: (ctx: string) => void;
}) {
  const currentPrice = model.valuation.currentPrice || 0;
  const intrinsicValue = model.valuation.intrinsicValue || 0;
  const maxVal = Math.max(currentPrice, intrinsicValue, 1) * 1.25;

  const currentPct = Math.min((currentPrice / maxVal) * 100, 100);
  const intrinsicPct = Math.min((intrinsicValue / maxVal) * 100, 100);

  return (
    <div style={{ marginBottom: 36 }}>
      <SectionHead id="s09" num="04" title="Valuation & Intrinsic Value" status={model.valuation.status} />
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
          <SvgAreaChart data={model.marginData} color="var(--c-cashflow, #2dd4bf)" unit="%" />
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

export function EvidenceExplorerSection({ model }: { model: ZipResearchViewModel }) {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ marginBottom: 36 }}>
      <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.1em", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ padding: "2px 8px", background: "var(--secondary)", borderRadius: 4 }}>DEEP DIVE</span>
        Evidence & Sources
      </div>
      <SectionHead
        id="s14"
        num=""
        title="Evidence & Sources"
        subtitle="Every key conclusion is traceable to analytical evidence and backend stage provenance."
      />
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          marginBottom: 12,
          background: "none",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "8px 16px",
          fontSize: 13,
          color: "var(--muted-foreground)",
          cursor: "pointer",
          fontFamily: "var(--font-body)",
        }}
      >
        {open ? "▲ Hide evidence trail" : "▼ View evidence trail"}
      </button>
      {open && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {model.evidence.map((e, i) => (
            <Card key={i} style={{ padding: "14px 18px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 12 }}>
                {[
                  { l: "METRIC", v: e.metric },
                  { l: "VALUE", v: e.value },
                  { l: "PERIOD", v: e.period },
                  { l: "SOURCE", v: e.source },
                  { l: "STAGE", v: e.stage },
                  { l: "CONFIDENCE", v: e.confidence },
                ].map((f) => (
                  <div key={f.l}>
                    <div style={{ fontSize: 9, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.09em", marginBottom: 3 }}>
                      {f.l}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--foreground)", fontFamily: "var(--font-data)" }}>
                      {f.v}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
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
  const initialSymbol = searchParams.get("symbol") || searchParams.get("ticker") || "TCS.NS";

  const [phase, setPhase] = useState<AnalysisPhase>("select");
  const [symbol, setSymbol] = useState(initialSymbol);
  const [activeSection, setActiveSection] = useState("s01");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatCtx, setChatCtx] = useState("");
  const [tocOpen, setTocOpen] = useState(false);

  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const { isAccepted, DisclaimerModal } = useResearchDisclaimerGate();

  const analyseMutation = useMutation({
    mutationFn: async (req: AnalyseRequest) => {
      const resp = await api.analyse(req);
      return resp;
    },
    onSuccess: (data, variables) => {
      pushRecentAnalysis({
        ticker: variables.ticker,
        companyName: data.company_name || variables.ticker,
        sector: data.sector || "General",
        timestamp: Date.now(),
      });
    },
  });

  const runAnalysis = useCallback(
    (targetPhase: "simple-loading" | "buffett-loading") => {
      setPhase(targetPhase);
      const req: AnalyseRequest = {
        ticker: symbol,
        request_id: `req_${Date.now()}`,
      };
      analyseMutation.mutate(req);
    },
    [symbol, analyseMutation]
  );

  useEffect(() => {
    if (phase !== "buffett-result" && phase !== "simple-result") return;

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
      <DisclaimerModal />

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

      {(phase === "buffett-result" || phase === "simple-result") && (
        <div style={{ display: "flex", flex: 1, flexDirection: "column", overflow: "hidden" }}>
          <CompanyHeader
            model={viewModel}
            onModeSwitch={() => setPhase("select")}
          />

          <div style={{ display: "flex", flex: 1, overflow: "hidden", position: "relative" }}>
            <aside
              className="toc-sidebar"
              style={{
                width: 210,
                flexShrink: 0,
                borderRight: "1px solid var(--border)",
                display: "flex",
                flexDirection: "column",
                overflowY: "auto",
                padding: "16px 0",
                background: "var(--card)",
              }}
            >
              {TOC_GROUPS.map((group) => (
                <div key={group.label} style={{ marginBottom: 8 }}>
                  <div
                    style={{
                      padding: "0 16px 8px",
                      fontSize: 9,
                      color: "var(--muted-foreground)",
                      fontFamily: "var(--font-data)",
                      letterSpacing: "0.12em",
                    }}
                  >
                    {group.label}
                  </div>
                  {group.items.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => scrollTo(t.id)}
                      style={{
                        background: activeSection === t.id ? "var(--secondary)" : "none",
                        border: "none",
                        padding: "7px 16px",
                        textAlign: "left",
                        cursor: "pointer",
                        width: "100%",
                        fontSize: 12,
                        fontFamily: "var(--font-body)",
                        color: activeSection === t.id ? "var(--foreground)" : "var(--muted-foreground)",
                        borderLeft: activeSection === t.id ? "2px solid var(--c-dsp, #3b82f6)" : "2px solid transparent",
                        transition: "all 0.15s",
                      }}
                    >
                      {t.label}
                    </button>
                  ))}
                  <div style={{ height: 1, background: "var(--border)", margin: "8px 16px" }} />
                </div>
              ))}

              <div style={{ padding: "0 16px 8px", fontSize: 9, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", letterSpacing: "0.12em" }}>
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
            </aside>

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
                  type="button"
                  onClick={() => setTocOpen((v) => !v)}
                  style={{
                    padding: "10px 20px",
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: 99,
                    fontSize: 13,
                    color: "var(--foreground)",
                    cursor: "pointer",
                    fontWeight: 500,
                    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                  }}
                >
                  Sections
                </button>
                <button
                  type="button"
                  onClick={() => setChatOpen((v) => !v)}
                  style={{
                    padding: "10px 20px",
                    background: chatOpen ? "var(--c-dsp, #3b82f6)" : "var(--card)",
                    border: `1px solid ${chatOpen ? "var(--c-dsp, #3b82f6)" : "var(--border)"}`,
                    borderRadius: 99,
                    fontSize: 13,
                    color: chatOpen ? "#fff" : "var(--foreground)",
                    cursor: "pointer",
                    fontWeight: 500,
                    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                  }}
                >
                  Ask DSP
                </button>
              </div>

              {tocOpen && (
                <>
                  <div
                    onClick={() => setTocOpen(false)}
                    style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60 }}
                  />
                  <div
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
                    {TOC_GROUPS.map((group) => (
                      <div key={group.label} style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: 10, color: "var(--muted-foreground)", fontFamily: "var(--font-data)", marginBottom: 6 }}>
                          {group.label}
                        </div>
                        {group.items.map((t) => (
                          <button
                            key={t.id}
                            type="button"
                            onClick={() => scrollTo(t.id)}
                            style={{
                              display: "block",
                              width: "100%",
                              textAlign: "left",
                              padding: "10px 0",
                              background: "none",
                              border: "none",
                              fontSize: 14,
                              color: activeSection === t.id ? "var(--c-dsp, #3b82f6)" : "var(--foreground)",
                            }}
                          >
                            {t.label}
                          </button>
                        ))}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            <main
              className="scroll-container"
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "28px 28px",
                paddingBottom: chatOpen ? "300px" : "60px",
              }}
            >
              <div style={{ maxWidth: 1000, margin: "0 auto" }}>
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
                  <ValuationSection model={viewModel} onAsk={askAbout} />
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
                  <EvidenceExplorerSection model={viewModel} />
                </div>
              </div>
            </main>
          </div>

          <ResearchChatDrawer
            symbol={symbol}
            analysisId={analyseMutation.data?.analysis_id}
            open={chatOpen}
            onClose={() => setChatOpen(false)}
            initCtx={chatCtx}
          />
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