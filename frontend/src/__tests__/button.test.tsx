import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders children text", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("is disabled when loading", () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByText("Loading").closest("button")).toBeDisabled();
  });

  it("is disabled when disabled prop set", () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByText("Disabled").closest("button")).toBeDisabled();
  });

  it("shows spinner svg when loading", () => {
    const { container } = render(<Button loading>Save</Button>);
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
  });

  it("does not show spinner svg when not loading", () => {
    const { container } = render(<Button>Save</Button>);
    const svg = container.querySelector("svg");
    expect(svg).toBeFalsy();
  });
});
