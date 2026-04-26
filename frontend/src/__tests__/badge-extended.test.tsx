import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "@/components/ui/badge";

describe("Badge (extended)", () => {
  it("renders children text", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies default variant styles", () => {
    render(<Badge>Default</Badge>);
    const el = screen.getByText("Default");
    expect(el).toHaveStyle({ color: "var(--fg-secondary)" });
  });

  it("applies success variant", () => {
    render(<Badge variant="success">Done</Badge>);
    const el = screen.getByText("Done");
    expect(el).toHaveStyle({ color: "var(--color-notion-green)" });
  });

  it("applies error variant", () => {
    render(<Badge variant="error">Failed</Badge>);
    const el = screen.getByText("Failed");
    expect(el).toHaveStyle({ color: "var(--color-notion-red)" });
  });

  it("applies warning variant", () => {
    render(<Badge variant="warning">Pending</Badge>);
    const el = screen.getByText("Pending");
    expect(el).toHaveStyle({ color: "var(--color-notion-yellow)" });
  });

  it("applies info variant", () => {
    render(<Badge variant="info">Processing</Badge>);
    const el = screen.getByText("Processing");
    expect(el).toHaveStyle({ color: "var(--color-notion-blue)" });
  });

  it("applies custom className", () => {
    render(<Badge className="custom-badge">Test</Badge>);
    const el = screen.getByText("Test");
    expect(el).toHaveClass("custom-badge");
  });
});
