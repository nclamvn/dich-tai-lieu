"use client";

import { useEffect, useState } from "react";
import { Activity, Database, AlertTriangle, Cpu, HardDrive, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { admin } from "@/lib/api/client";

type DashboardData = {
  health: Record<string, unknown> | null;
  system: Record<string, unknown> | null;
  queue: Record<string, number> | null;
  costs: Record<string, unknown> | null;
  errors: Record<string, unknown> | null;
  recentErrors: Array<Record<string, unknown>> | null;
  cache: Record<string, unknown> | null;
};

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="text-center">
      <p className="text-2xl font-bold" style={{ color: "var(--fg-primary)" }}>{value}</p>
      <p className="text-xs" style={{ color: "var(--fg-tertiary)" }}>{label}</p>
      {sub && <p className="text-xs mt-0.5" style={{ color: "var(--fg-ghost)" }}>{sub}</p>}
    </div>
  );
}

export default function AdminDashboard() {
  const [data, setData] = useState<DashboardData>({
    health: null, system: null, queue: null, costs: null, errors: null, recentErrors: null, cache: null,
  });
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchAll = async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      admin.getHealth(),
      admin.getSystemInfo(),
      admin.getQueueStats(),
      admin.getCostMetrics(24),
      admin.getErrorStats(24),
      admin.getRecentErrors(10),
      admin.getCacheStats(),
    ]);
    setData({
      health: results[0].status === "fulfilled" ? results[0].value : null,
      system: results[1].status === "fulfilled" ? results[1].value : null,
      queue: results[2].status === "fulfilled" ? results[2].value : null,
      costs: results[3].status === "fulfilled" ? results[3].value : null,
      errors: results[4].status === "fulfilled" ? results[4].value : null,
      recentErrors: results[5].status === "fulfilled" ? results[5].value : null,
      cache: results[6].status === "fulfilled" ? results[6].value : null,
    });
    setLoading(false);
    setLastRefresh(new Date());
  };

  useEffect(() => { fetchAll(); }, []);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(fetchAll, 30_000);
    return () => clearInterval(interval);
  }, []);

  const sys = data.system as Record<string, unknown> | null;
  const queue = data.queue as Record<string, number> | null;
  const health = data.health as Record<string, unknown> | null;
  const costs = data.costs as Record<string, unknown> | null;
  const cache = data.cache as Record<string, unknown> | null;
  const recentErrors = data.recentErrors || [];

  const uptime = sys?.uptime_seconds
    ? `${Math.floor((sys.uptime_seconds as number) / 3600)}h ${Math.floor(((sys.uptime_seconds as number) % 3600) / 60)}m`
    : "—";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1>Admin Dashboard</h1>
          <p className="text-sm mt-1" style={{ color: "var(--fg-tertiary)" }}>
            Last updated: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <Button size="sm" variant="secondary" onClick={fetchAll} disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} strokeWidth={1.5} />
          Refresh
        </Button>
      </div>

      {loading && !data.system && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 skeleton" />)}
        </div>
      )}

      {/* System Health */}
      <Card>
        <CardHeader>
          <h3 className="text-[15px] font-semibold flex items-center gap-2">
            <Activity className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
            System Health
          </h3>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <StatCard
              label="Status"
              value={health?.status === "healthy" ? "Healthy" : (health?.status as string) || "—"}
            />
            <StatCard label="Uptime" value={uptime} />
            <StatCard
              label="Version"
              value={(sys?.version as string) || "—"}
            />
            <StatCard
              label="Processor"
              value={sys?.processor_running ? "Running" : "Stopped"}
              sub={sys?.current_jobs !== undefined ? `${sys.current_jobs} active jobs` : undefined}
            />
          </div>
          {health?.components ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {Object.entries(health.components as Record<string, Record<string, unknown>>).map(([name, comp]) => (
                <Badge
                  key={name}
                  variant={comp.status === "healthy" ? "success" : comp.status === "degraded" ? "warning" : "error"}
                >
                  {name}: {String(comp.status)}
                </Badge>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Job Queue Stats */}
      <Card>
        <CardHeader>
          <h3 className="text-[15px] font-semibold flex items-center gap-2">
            <Cpu className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
            Job Queue
          </h3>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
            <StatCard label="Total" value={queue?.total ?? "—"} />
            <StatCard label="Pending" value={queue?.pending ?? 0} />
            <StatCard label="Running" value={queue?.running ?? 0} />
            <StatCard label="Completed" value={queue?.completed ?? 0} />
            <StatCard label="Failed" value={queue?.failed ?? 0} />
            <StatCard label="Cancelled" value={queue?.cancelled ?? 0} />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Cost Metrics */}
        <Card>
          <CardHeader>
            <h3 className="text-[15px] font-semibold flex items-center gap-2">
              <Database className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
              Costs (24h)
            </h3>
          </CardHeader>
          <CardContent>
            {costs ? (
              <div className="grid grid-cols-2 gap-4">
                <StatCard
                  label="Total Cost"
                  value={`$${((costs.total_cost_usd as number) || 0).toFixed(4)}`}
                />
                <StatCard
                  label="Jobs Processed"
                  value={(costs.jobs_processed as number) || 0}
                />
                <StatCard
                  label="Tokens Used"
                  value={((costs.total_tokens_used as number) || 0).toLocaleString()}
                />
                <StatCard
                  label="Avg Cost/Job"
                  value={`$${((costs.average_cost_per_job as number) || 0).toFixed(4)}`}
                />
              </div>
            ) : (
              <p className="text-sm" style={{ color: "var(--fg-tertiary)" }}>No cost data available</p>
            )}
          </CardContent>
        </Card>

        {/* Cache Stats */}
        <Card>
          <CardHeader>
            <h3 className="text-[15px] font-semibold flex items-center gap-2">
              <HardDrive className="w-4 h-4" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
              Cache
            </h3>
          </CardHeader>
          <CardContent>
            {cache?.stats ? (
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(cache.stats as Record<string, unknown>).map(([key, val]) => (
                  <StatCard
                    key={key}
                    label={key.replace(/_/g, " ")}
                    value={typeof val === "number" ? val.toLocaleString() : String(val)}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm" style={{ color: "var(--fg-tertiary)" }}>No cache data</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Errors */}
      <Card>
        <CardHeader>
          <h3 className="text-[15px] font-semibold flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" style={{ color: "var(--color-notion-red)" }} strokeWidth={1.5} />
            Recent Errors
          </h3>
        </CardHeader>
        <CardContent>
          {recentErrors.length > 0 ? (
            <div className="space-y-2">
              {recentErrors.map((err, i) => (
                <div
                  key={(err.id as string) || i}
                  className="flex items-start gap-3 p-3 text-sm"
                  style={{
                    background: "var(--bg-secondary)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  <Badge
                    variant={
                      err.severity === "critical" || err.severity === "high"
                        ? "error"
                        : err.severity === "medium"
                          ? "warning"
                          : "default"
                    }
                  >
                    {err.severity as string}
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium truncate" style={{ color: "var(--fg-primary)" }}>
                      {err.error_type as string}
                    </p>
                    <p className="text-xs mt-0.5 truncate" style={{ color: "var(--fg-tertiary)" }}>
                      {err.error_message as string}
                    </p>
                    <p className="text-xs mt-1" style={{ color: "var(--fg-ghost)" }}>
                      {err.occurrence_count as number}x &middot;{" "}
                      {err.last_seen ? new Date((err.last_seen as number) * 1000).toLocaleString() : "—"}
                    </p>
                  </div>
                  {err.resolved ? (
                    <Badge variant="success">Resolved</Badge>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm py-4 text-center" style={{ color: "var(--fg-tertiary)" }}>
              No recent errors
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
