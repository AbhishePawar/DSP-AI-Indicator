"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

import { RetryCard, GracefulDegradationCard } from "@/components/reliability/RetryCard";

type Props = {
  children: ReactNode;
  title?: string;
  fallback?: ReactNode;
  onError?: (error: Error, info: ErrorInfo) => void;
};

type State = { error: Error | null };

/** App-wide error boundary — Sprint 9 GlobalErrorBoundary. */
export class GlobalErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Avoid logging secrets — message + componentStack only
    console.error("[DSP GlobalErrorBoundary]", error.message, info.componentStack);
    this.props.onError?.(error, info);
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="mx-auto max-w-lg p-6">
          <GracefulDegradationCard
            title={this.props.title ?? "Something went wrong"}
            message="The UI hit an unexpected state. Research engines and APIs were not modified — retry the view."
          />
          <div className="mt-4">
            <RetryCard
              detail={this.state.error.message}
              onRetry={() => this.setState({ error: null })}
            />
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/** Section-scoped boundary so one panel can fail without collapsing the page. */
export class SectionErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[DSP SectionErrorBoundary]", error.message, info.componentStack);
    this.props.onError?.(error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-md border border-[var(--danger-border)] bg-[var(--danger-bg)] p-4 text-[var(--danger-fg)]">
          <p className="font-medium">{this.props.title ?? "Section unavailable"}</p>
          <p className="mt-1 text-sm opacity-90">{this.state.error.message}</p>
          <button
            type="button"
            className="mt-3 min-h-11 rounded-md border border-current px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            onClick={() => this.setState({ error: null })}
          >
            Retry section
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

/** @deprecated use GlobalErrorBoundary */
export class ErrorBoundary extends GlobalErrorBoundary {}
