"use client";

import { DialogueBlock as DialogueBlockType } from "@/lib/screenplay/types";

interface DialogueBlockProps {
  block: DialogueBlockType;
}

export function DialogueBlock({ block }: DialogueBlockProps) {
  return (
    <div className="screenplay-dialogue">
      <div className="screenplay-dialogue-character">{block.character}</div>
      {block.parenthetical && (
        <div className="screenplay-dialogue-paren">
          ({block.parenthetical})
        </div>
      )}
      <div className="screenplay-dialogue-text">{block.dialogue}</div>
    </div>
  );
}
