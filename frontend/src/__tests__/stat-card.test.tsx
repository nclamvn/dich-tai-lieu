import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatCard } from "@/components/ui/stat-card";
import { FileText } from "lucide-react";

describe("StatCard", () => {
  it("renders label and value", () => {
    render(<StatCard label="Total Jobs" value={42} />);
    expect(screen.getByText("Total Jobs")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders string value", () => {
    render(<StatCard label="Cost" value="$1.50" />);
    expect(screen.getByText("$1.50")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    const { container } = render(
      <StatCard label="Files" value={10} icon={FileText} />,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
  });

  it("renders trend when provided", () => {
    render(
      <StatCard
        label="Jobs"
        value={100}
        trend={{ value: 15, label: "vs last week" }}
      />,
    );
    expect(screen.getByText(/15%/)).toBeInTheDocument();
    expect(screen.getByText(/vs last week/)).toBeInTheDocument();
  });

  it("does not render trend when not provided", () => {
    const { container } = render(<StatCard label="Jobs" value={10} />);
    const trendEl = container.querySelector(".text-xs");
    expect(trendEl).toBeNull();
  });
});
