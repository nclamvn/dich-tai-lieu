"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

/**
 * UX-24: Global keyboard shortcuts.
 *
 * Ctrl/Cmd + N → New translation
 * Ctrl/Cmd + J → Jobs list
 * Ctrl/Cmd + D → Dashboard
 * ? → Toggle shortcut cheat sheet
 */
export function useKeyboardShortcuts() {
  const router = useRouter();
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't intercept when typing in inputs/textareas
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.metaKey || e.ctrlKey) {
        switch (e.key.toLowerCase()) {
          case "n":
            e.preventDefault();
            router.push("/translate");
            break;
          case "j":
            e.preventDefault();
            router.push("/jobs");
            break;
          case "d":
            e.preventDefault();
            router.push("/dashboard");
            break;
        }
      }

      if (e.key === "?" && !e.metaKey && !e.ctrlKey) {
        setShowHelp((prev) => !prev);
      }
      if (e.key === "Escape") {
        setShowHelp(false);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [router]);

  return { showHelp, setShowHelp };
}
