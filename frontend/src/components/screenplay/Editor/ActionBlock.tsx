"use client";

import { ActionBlock as ActionBlockType } from "@/lib/screenplay/types";

interface ActionBlockProps {
  block: ActionBlockType;
}

export function ActionBlock({ block }: ActionBlockProps) {
  return <div className="screenplay-action">{block.text}</div>;
}
