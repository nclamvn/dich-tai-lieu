"use client";

import { FileText, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { useProfiles } from "@/lib/api/hooks";

export default function ProfilesPage() {
  const { data, isLoading } = useProfiles();
  const profileList = data?.profiles || [];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Publishing Profiles</h1>
      <p className="text-slate-500">
        Reusable settings for translation + output formatting
      </p>

      {isLoading ? (
        <div className="animate-pulse space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-slate-200 rounded-lg" />
          ))}
        </div>
      ) : profileList.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No profiles found"
          description="Profiles will appear here when available from the backend"
        />
      ) : (
        <div className="grid gap-4">
          {profileList.map((p) => (
            <Card key={p.id} className="hover:shadow-md transition-shadow">
              <CardContent className="py-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-purple-500" />
                      {p.name}
                    </h3>
                    <p className="text-sm text-slate-500 mt-1">
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
