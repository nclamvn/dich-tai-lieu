"use client";

import { DollarSign, Cpu, Globe, TrendingDown, FileText, Loader2, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat-card";
import {
  useCostOverview,
  useProviderCosts,
  useLanguagePairCosts,
  useJobs,
} from "@/lib/api/hooks";
import { formatCost, formatNumber, formatDate, statusVariant } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { useLocale } from "@/lib/i18n";

const CHART_COLORS = [
  "rgb(35,131,226)",
  "rgb(15,123,108)",
  "rgb(203,145,47)",
  "rgb(144,101,176)",
  "rgb(217,115,13)",
  "rgb(193,76,138)",
  "rgb(159,107,83)",
];

const TOOLTIP_STYLE: React.CSSProperties = {
  background: "var(--bg-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-md)",
  fontSize: "13px",
  color: "var(--fg-primary)",
};

export default function DashboardPage() {
  const { data: overview } = useCostOverview();
  const { data: providers } = useProviderCosts();
  const { data: langPairs } = useLanguagePairCosts();
  const { data: jobsData } = useJobs({ limit: 20 });
  const { t } = useLocale();

  const allJobs = jobsData?.jobs || [];
  const activeJobs = allJobs.filter((j) => j.status === "processing" || j.status === "pending");
  const recentCompleted = allJobs.filter((j) => j.status === "completed").slice(0, 5);

  const providerList = Array.isArray(providers) ? providers : [];
  const langPairData = langPairs
    ? Object.entries(langPairs).map(([pair, cost]) => ({
        language_pair: pair,
        cost_usd: cost as number,
      }))
    : [];

  return (
    <div className="space-y-6">
      <h1>{t.dashboard.title}</h1>

      {/* Overview Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label={t.dashboard.totalCost}
          value={formatCost(overview?.total_cost_usd || 0)}
          icon={DollarSign}
        />
        <StatCard
          label={t.dashboard.totalCalls}
          value={formatNumber(overview?.total_calls || 0)}
          icon={Cpu}
        />
        <StatCard
          label={t.dashboard.avgCostPerCall}
          value={formatCost(overview?.avg_cost_per_call || 0)}
          icon={TrendingDown}
        />
        <StatCard
          label={t.dashboard.costPer1kTokens}
          value={formatCost(overview?.avg_cost_per_1k_tokens || 0)}
          icon={Globe}
        />
      </div>

      {/* Active Jobs */}
      {activeJobs.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-[15px] font-semibold">{t.dashboard.activeJobs || "Active Jobs"}</h3>
              <Link href="/jobs?status=processing" className="text-xs no-underline" style={{ color: "var(--color-notion-blue)" }}>
                {t.dashboard.viewAll || "View all"} <ArrowRight className="w-3 h-3 inline" />
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {activeJobs.map((job) => (
              <Link key={job.id} href={`/jobs/${job.id}`} className="block no-underline">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-4 h-4 animate-spin shrink-0" style={{ color: "var(--color-notion-blue)" }} strokeWidth={1.5} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: "var(--fg-primary)" }}>
                      {job.source_filename || job.id}
                    </p>
                    <div className="mt-1 h-1.5 overflow-hidden" style={{ background: "var(--bg-secondary)", borderRadius: "var(--radius-sm)" }}>
                      <div className="h-full transition-all duration-500" style={{ width: `${job.progress || 0}%`, background: "var(--color-notion-blue)", borderRadius: "var(--radius-sm)" }} />
                    </div>
                  </div>
                  <span className="text-xs shrink-0" style={{ color: "var(--fg-tertiary)" }}>{job.progress || 0}%</span>
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Recent Completed */}
      {recentCompleted.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-[15px] font-semibold">{t.dashboard.recentJobs || "Recent Jobs"}</h3>
              <Link href="/jobs" className="text-xs no-underline" style={{ color: "var(--color-notion-blue)" }}>
                {t.dashboard.viewAll || "View all"} <ArrowRight className="w-3 h-3 inline" />
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {recentCompleted.map((job) => (
              <Link key={job.id} href={`/jobs/${job.id}`} className="block no-underline">
                <div className="flex items-center justify-between py-1.5 transition-colors duration-100" style={{ borderBottom: "1px solid var(--border-default)" }}>
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="w-4 h-4 shrink-0" style={{ color: "var(--fg-icon)" }} strokeWidth={1.5} />
                    <span className="text-sm truncate" style={{ color: "var(--fg-primary)" }}>{job.source_filename || job.id}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
                    <span className="text-xs" style={{ color: "var(--fg-tertiary)" }}>{formatDate(job.created_at)}</span>
                  </div>
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Provider Cost Chart */}
        <Card>
          <CardHeader>
            <h3 className="text-[15px] font-semibold">{t.dashboard.costByProvider}</h3>
          </CardHeader>
          <CardContent>
            {providerList.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={providerList.map((p) => ({
                      name: p.provider,
                      value: p.cost_usd,
                    }))}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    dataKey="value"
                    label={({ name, value }) =>
                      `${name ?? ""}: ${formatCost(value as number)}`
                    }
                  >
                    {providerList.map((_, i) => (
                      <Cell
                        key={i}
                        fill={CHART_COLORS[i % CHART_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v) => formatCost(v as number)}
                    contentStyle={TOOLTIP_STYLE}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p
                className="text-center py-8 text-sm"
                style={{ color: "var(--fg-tertiary)" }}
              >
                {t.dashboard.noData}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Language Pair Chart */}
        <Card>
          <CardHeader>
            <h3 className="text-[15px] font-semibold">
              {t.dashboard.costByLangPair}
            </h3>
          </CardHeader>
          <CardContent>
            {langPairData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={langPairData}>
                  <XAxis
                    dataKey="language_pair"
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis tickFormatter={(v) => formatCost(v)} />
                  <Tooltip
                    formatter={(v) => formatCost(v as number)}
                    contentStyle={TOOLTIP_STYLE}
                  />
                  <Bar
                    dataKey="cost_usd"
                    fill="rgb(35,131,226)"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p
                className="text-center py-8 text-sm"
                style={{ color: "var(--fg-tertiary)" }}
              >
                {t.dashboard.noData}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Provider Details Table */}
      {providerList.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-[15px] font-semibold">{t.dashboard.providerDetails}</h3>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: "var(--bg-secondary)" }}>
                  <th
                    className="text-left px-5 py-3 font-medium"
                    style={{ color: "var(--fg-secondary)" }}
                  >
                    {t.dashboard.provider}
                  </th>
                  <th
                    className="text-right px-5 py-3 font-medium"
                    style={{ color: "var(--fg-secondary)" }}
                  >
                    {t.dashboard.cost}
                  </th>
                  <th
                    className="text-right px-5 py-3 font-medium"
                    style={{ color: "var(--fg-secondary)" }}
                  >
                    {t.dashboard.calls}
                  </th>
                  <th
                    className="text-right px-5 py-3 font-medium"
                    style={{ color: "var(--fg-secondary)" }}
                  >
                    {t.dashboard.tokens}
                  </th>
                  <th
                    className="text-right px-5 py-3 font-medium"
                    style={{ color: "var(--fg-secondary)" }}
                  >
                    {t.dashboard.avgQuality}
                  </th>
                </tr>
              </thead>
              <tbody>
                {providerList.map((p) => (
                  <tr
                    key={p.provider}
                    className="transition-colors duration-100"
                    style={{
                      borderBottom: "1px solid var(--border-default)",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background =
                        "var(--bg-hover)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "transparent")
                    }
                  >
                    <td
                      className="px-5 py-3 font-medium capitalize"
                      style={{ color: "var(--fg-primary)" }}
                    >
                      {p.provider}
                    </td>
                    <td
                      className="px-5 py-3 text-right"
                      style={{ color: "var(--fg-primary)" }}
                    >
                      {formatCost(p.cost_usd)}
                    </td>
                    <td
                      className="px-5 py-3 text-right"
                      style={{ color: "var(--fg-primary)" }}
                    >
                      {formatNumber(p.calls)}
                    </td>
                    <td
                      className="px-5 py-3 text-right"
                      style={{ color: "var(--fg-primary)" }}
                    >
                      {formatNumber(p.tokens)}
                    </td>
                    <td
                      className="px-5 py-3 text-right"
                      style={{ color: "var(--fg-primary)" }}
                    >
                      {(p.avg_quality * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
