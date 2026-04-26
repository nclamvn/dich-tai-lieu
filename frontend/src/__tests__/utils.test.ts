import { describe, it, expect } from "vitest";
import { cn, formatCost, formatNumber, formatDate, statusVariant } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    const result = cn("foo", "bar");
    expect(result).toContain("foo");
    expect(result).toContain("bar");
  });

  it("handles undefined values", () => {
    const result = cn("foo", undefined, "bar");
    expect(result).toContain("foo");
    expect(result).toContain("bar");
  });

  it("handles conditional classes", () => {
    const result = cn("base", false && "hidden", true && "visible");
    expect(result).toContain("base");
    expect(result).toContain("visible");
    expect(result).not.toContain("hidden");
  });
});

describe("formatCost", () => {
  it("formats zero", () => {
    expect(formatCost(0)).toBe("$0.00");
  });

  it("formats very small amounts", () => {
    expect(formatCost(0.0001)).toBe("<$0.01");
  });

  it("formats small amounts with 3 decimals", () => {
    const result = formatCost(0.005);
    expect(result).toMatch(/^\$0\.00[0-9]$/);
  });

  it("formats normal amounts", () => {
    expect(formatCost(1.5)).toBe("$1.50");
  });
});

describe("formatNumber", () => {
  it("formats small numbers", () => {
    expect(formatNumber(42)).toBe("42");
  });

  it("formats large numbers with separators", () => {
    const result = formatNumber(1000000);
    // Result depends on locale but should have separators
    expect(result.length).toBeGreaterThan(6);
  });
});

describe("statusVariant", () => {
  it("returns success for completed", () => {
    expect(statusVariant("completed")).toBe("success");
  });

  it("returns info for processing", () => {
    expect(statusVariant("processing")).toBe("info");
  });

  it("returns warning for pending", () => {
    expect(statusVariant("pending")).toBe("warning");
  });

  it("returns error for failed", () => {
    expect(statusVariant("failed")).toBe("error");
  });

  it("returns default for unknown status", () => {
    expect(statusVariant("unknown")).toBe("default");
  });
});
