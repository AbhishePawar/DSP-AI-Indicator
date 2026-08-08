// @vitest-environment jsdom
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  Button,
  COMPONENT_CATALOGUE,
  DESIGN_SYSTEM_VERSION,
  EmptyState,
  Skeleton,
  ThemeSwitcher,
  Typography,
} from "@/components/ds";
import { ThemeProvider } from "@/providers/ThemeProvider";

describe("EPIC-F001 design system", () => {
  it("reports design system version 0.2.0", () => {
    expect(DESIGN_SYSTEM_VERSION).toBe("0.2.0");
    expect(COMPONENT_CATALOGUE.forms).toContain("Button");
    expect(COMPONENT_CATALOGUE.navigation).toContain("CommandPalette");
  });

  it("renders Button and supports click", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("EmptyState defaults to Data unavailable.", () => {
    render(<EmptyState />);
    expect(screen.getByText("Data unavailable.")).toBeInTheDocument();
  });

  it("Typography and Skeleton render", () => {
    render(
      <>
        <Typography variant="h1">Heading</Typography>
        <Skeleton data-testid="sk" className="h-4 w-20" />
      </>,
    );
    expect(screen.getByText("Heading")).toBeInTheDocument();
    expect(screen.getByTestId("sk")).toBeInTheDocument();
  });

  it("ThemeSwitcher cycles theme modes", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => undefined,
        removeListener: () => undefined,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        dispatchEvent: () => false,
      }),
    });
    render(
      <ThemeProvider>
        <ThemeSwitcher />
      </ThemeProvider>,
    );
    const light = screen.getByRole("button", { name: "Light" });
    fireEvent.click(light);
    expect(light).toHaveAttribute("aria-pressed", "true");
  });
});
