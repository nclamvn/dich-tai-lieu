import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EmptyState } from "@/components/ui/empty-state";
import { FileText } from "lucide-react";

describe("EmptyState", () => {
  it("renders title", () => {
    render(<EmptyState icon={FileText} title="No items" />);
    expect(screen.getByText("No items")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(
      <EmptyState
        icon={FileText}
        title="No items"
        description="Upload a file to get started"
      />,
    );
    expect(screen.getByText("Upload a file to get started")).toBeInTheDocument();
  });

  it("does not render description paragraph when not provided", () => {
    const { container } = render(<EmptyState icon={FileText} title="No items" />);
    const paragraphs = container.querySelectorAll("p");
    expect(paragraphs.length).toBe(0);
  });

  it("renders action when provided", () => {
    render(
      <EmptyState
        icon={FileText}
        title="No items"
        action={<button>Upload</button>}
      />,
    );
    expect(screen.getByText("Upload")).toBeInTheDocument();
  });
});
