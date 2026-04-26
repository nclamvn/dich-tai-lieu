import { describe, it, expect } from "vitest";
import { formatCost, formatDate, gradeColor, statusVariant } from "@/lib/utils";

describe("formatDate", () => {
  it("formats ISO date string", () => {
    const result = formatDate("2026-01-15T10:30:00Z");
    expect(result).toContain("Jan");
    expect(result).toContain("15");
  });

  it("formats unix timestamp", () => {
    // 2026-01-15 00:00:00 UTC = 1768435200
    const result = formatDate(1768435200);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });
});

describe("gradeColor", () => {
  it("returns green for A grade", () => {
    expect(gradeColor("A")).toBe("color-notion-green");
  });

  it("returns blue for B grade", () => {
    expect(gradeColor("B")).toBe("color-notion-blue");
  });

  it("returns yellow for C grade", () => {
    expect(gradeColor("C")).toBe("color-notion-yellow");
  });

  it("returns red for F grade", () => {
    expect(gradeColor("F")).toBe("color-notion-red");
  });

  it("returns fallback for unknown grade", () => {
    expect(gradeColor("X")).toBe("var(--fg-secondary)");
  });
});

describe("formatCost edge cases", () => {
  it("formats large cost with commas", () => {
    const result = formatCost(1500.99);
    expect(result).toContain("1");
    expect(result).toContain("500");
  });

  it("formats sub-cent cost", () => {
    const result = formatCost(0.005);
    expect(result).toMatch(/^\$/);
  });
});

describe("statusVariant edge cases", () => {
  it("returns default for cancelled", () => {
    expect(statusVariant("cancelled")).toBe("default");
  });

  it("returns default for empty string", () => {
    expect(statusVariant("")).toBe("default");
  });
});
