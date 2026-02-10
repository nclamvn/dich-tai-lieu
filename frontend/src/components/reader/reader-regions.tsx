"use client";

import type { ReaderRegion, ReaderFont } from "@/lib/api/types";

interface RegionProps {
  region: ReaderRegion;
  font: ReaderFont;
}

export function RegionRenderer({ region, font }: RegionProps) {
  switch (region.type) {
    case "heading":
      return <HeadingRegion region={region} font={font} />;
    case "text":
      return <TextRegion region={region} />;
    case "table":
      return <TableRegion region={region} />;
    case "formula":
      return <FormulaRegion region={region} />;
    case "list":
      return <ListRegion region={region} />;
    case "image":
      return <ImageRegion region={region} />;
    case "code":
      return <CodeRegion region={region} />;
    default:
      return <TextRegion region={region} />;
  }
}

function HeadingRegion({ region, font }: RegionProps) {
  const level = region.level || 2;

  const sizes: Record<number, string> = {
    1: "mt-[1.4em] mb-[0.35em]",
    2: "mt-[1.3em] mb-[0.3em]",
    3: "mt-[1.2em] mb-[0.25em]",
    4: "mt-[1em] mb-[0.2em]",
    5: "mt-[0.8em] mb-[0.15em]",
    6: "mt-[0.6em] mb-[0.1em]",
  };

  const fontSizes: Record<number, string> = {
    1: "1.875em",
    2: "1.5em",
    3: "1.25em",
    4: "1.1em",
    5: "1em",
    6: "0.9em",
  };

  const Tag = `h${Math.min(level, 6)}` as "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
  const cls = sizes[level] || sizes[3];

  return (
    <Tag
      className={`font-semibold leading-tight ${cls}`}
      style={{
        fontSize: fontSizes[level] || fontSizes[3],
        fontFamily:
          level <= 2 && font === "serif"
            ? "'Instrument Serif', Georgia, serif"
            : "inherit",
        letterSpacing: level <= 2 ? "-0.01em" : undefined,
      }}
    >
      {region.content}
    </Tag>
  );
}

function TextRegion({ region }: { region: ReaderRegion }) {
  const content = region.content || "";

  if (region.style === "quote") {
    return (
      <blockquote
        className="my-[0.8em] italic opacity-85"
        style={{
          borderLeft: "3px solid currentColor",
          borderLeftColor: "rgba(128,128,128,0.25)",
          paddingLeft: "1em",
        }}
      >
        {content.split("\n").map((line, i) => (
          <p key={i} className="my-[0.3em] leading-[1.75]">
            {line}
          </p>
        ))}
      </blockquote>
    );
  }

  if (region.style === "caption") {
    return (
      <p className="text-[0.85em] opacity-55 my-[0.5em] text-center italic">
        {content}
      </p>
    );
  }

  const paragraphs = content.split(/\n\n+/).filter(Boolean);

  return (
    <>
      {paragraphs.map((para, i) => (
        <p key={i} className="my-[0.6em] leading-[1.8]">
          {para}
        </p>
      ))}
    </>
  );
}

function TableRegion({ region }: { region: ReaderRegion }) {
  if (!region.html) return null;

  return (
    <figure className="my-[1.2em] overflow-x-auto">
      {region.caption && (
        <figcaption className="text-[0.85em] opacity-55 mb-2 font-medium">
          {region.caption}
        </figcaption>
      )}
      <div
        className="reader-table text-[0.9em] overflow-hidden"
        style={{
          borderRadius: "var(--radius-md)",
          border: "1px solid rgba(128,128,128,0.15)",
        }}
        dangerouslySetInnerHTML={{ __html: region.html }}
      />
    </figure>
  );
}

function FormulaRegion({ region }: { region: ReaderRegion }) {
  if (region.inline) {
    return (
      <code
        className="text-[0.9em] px-1 py-0.5 rounded"
        style={{
          fontFamily: "var(--font-mono)",
          background: "rgba(128,128,128,0.06)",
        }}
      >
        {region.display_text || region.latex || ""}
      </code>
    );
  }

  return (
    <figure className="my-[1em] text-center">
      <div
        className="inline-block px-6 py-3 rounded"
        style={{
          borderRadius: "var(--radius-md)",
          background: "rgba(128,128,128,0.04)",
        }}
      >
        <code
          className="text-[1.1em]"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {region.display_text || region.latex || ""}
        </code>
      </div>
    </figure>
  );
}

function ListRegion({ region }: { region: ReaderRegion }) {
  const items = region.items || [];
  const Tag = region.ordered ? "ol" : "ul";

  return (
    <Tag
      className="my-[0.8em] pl-[1.5em] space-y-[0.3em]"
      style={{ listStyleType: region.ordered ? "decimal" : "disc" }}
    >
      {items.map((item, i) => (
        <li key={i} className="leading-[1.7] pl-[0.3em]">
          {item}
        </li>
      ))}
    </Tag>
  );
}

function ImageRegion({ region }: { region: ReaderRegion }) {
  return (
    <figure className="my-[1.5em] text-center">
      <div
        className="inline-flex items-center justify-center w-full max-w-[400px] h-48"
        style={{
          borderRadius: "var(--radius-lg)",
          background: "rgba(128,128,128,0.05)",
          border: "1px solid rgba(128,128,128,0.12)",
        }}
      >
        <span className="text-[0.85em] opacity-30">
          {region.alt_text || "Image"}
        </span>
      </div>
      {region.alt_text && (
        <figcaption className="text-[0.8em] opacity-45 mt-2 italic">
          {region.alt_text}
        </figcaption>
      )}
    </figure>
  );
}

function CodeRegion({ region }: { region: ReaderRegion }) {
  return (
    <pre
      className="my-[1em] p-4 overflow-x-auto"
      style={{
        borderRadius: "var(--radius-md)",
        background: "rgba(128,128,128,0.05)",
        border: "1px solid rgba(128,128,128,0.1)",
      }}
    >
      <code
        className="text-[0.85em] leading-[1.6]"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {region.content}
      </code>
    </pre>
  );
}
