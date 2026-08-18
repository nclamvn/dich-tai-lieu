"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface QueryErrorProps {
  error?: unknown;
  onRetry?: () => void;
  title?: string;
}

export function QueryError({
  error,
  onRetry,
  title = "Không tải được dữ liệu",
}: QueryErrorProps) {
  const message =
    error instanceof Error
      ? error.message
      : typeof error === "string"
        ? error
        : "";

  return (
    <Card>
      <CardContent>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center mb-5"
            style={{ background: "var(--bg-secondary)" }}
          >
            <AlertTriangle
              className="w-7 h-7"
              style={{ color: "var(--fg-tertiary)" }}
              strokeWidth={1.25}
            />
          </div>
          <h3
            className="font-medium text-base"
            style={{ color: "var(--fg-primary)" }}
          >
            {title}
          </h3>
          {message && (
            <p
              className="mt-1.5 text-sm max-w-[320px] leading-relaxed"
              style={{ color: "var(--fg-tertiary)" }}
            >
              {message}
            </p>
          )}
          {onRetry && (
            <div className="mt-5">
              <Button variant="secondary" size="md" onClick={onRetry}>
                <RotateCcw className="w-3.5 h-3.5 mr-1.5" strokeWidth={1.5} />
                Thử lại
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
