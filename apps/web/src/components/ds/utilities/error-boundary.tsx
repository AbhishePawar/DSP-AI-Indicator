"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorState } from "../feedback/error-state";

export type DsErrorBoundaryProps = {
  children: ReactNode;
  fallback?: ReactNode;
  title?: string;
  description?: string;
  onError?: (error: Error, info: ErrorInfo) => void;
};

type DsErrorBoundaryState = {
  error: Error | null;
};

export class DsErrorBoundary extends Component<
  DsErrorBoundaryProps,
  DsErrorBoundaryState
> {
  state: DsErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): DsErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    this.props.onError?.(error, info);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    if (this.props.fallback) return this.props.fallback;

    return (
      <ErrorState
        title={this.props.title ?? "Something went wrong"}
        description={
          this.props.description ??
          "An unexpected UI error occurred. Try again or reload the page."
        }
        action={
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--danger-border)] bg-[var(--surface)] px-3 text-sm text-[var(--danger-fg)] transition hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Try again
          </button>
        }
      />
    );
  }
}
