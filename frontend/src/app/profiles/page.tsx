"use client";

import { FileText, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { useProfiles } from "@/lib/api/hooks";
import { useLocale } from "@/lib/i18n";

export default function ProfilesPage() {
  const { data, isLoading } = useProfiles();
  const profileList = data?.profiles || [];
  const { t } = useLocale();

  return (
    <div className="space-y-6">
      <div>
        <h1>{t.profiles.title}</h1>
        <p style={{ color: "var(--fg-secondary)" }}>
          {t.profiles.subtitle}
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 skeleton" />
          ))}
        </div>
      ) : profileList.length === 0 ? (
        <EmptyState
          icon={FileText}
          title={t.profiles.emptyTitle}
          description={t.profiles.emptyDesc}
        />
      ) : (
        <div className="grid gap-4">
          {profileList.map((p) => (
            <Card
              key={p.id}
              className="cursor-pointer transition-colors duration-100"
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "var(--bg-hover)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "var(--bg-primary)")
              }
            >
              <CardContent className="py-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold flex items-center gap-2 text-[15px]">
                      <Sparkles
                        className="w-4 h-4"
                        style={{ color: "var(--color-notion-purple)" }}
                        strokeWidth={1.5}
                      />
                      <span style={{ color: "var(--fg-primary)" }}>
                        {p.name}
                      </span>
                    </h3>
                    <p
                      className="text-sm mt-1"
                      style={{ color: "var(--fg-secondary)" }}
                    >
                      {p.description}
                    </p>
                    <div className="flex gap-2 mt-2">
                      <Badge>{p.language_pair}</Badge>
                      <Badge variant="info">{p.output.format}</Badge>
                      <Badge variant="info">
                        {p.translation.routing_mode.replace("_", " ")}
                      </Badge>
                      {p.translation.preferred_provider && (
                        <Badge>{p.translation.preferred_provider}</Badge>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
