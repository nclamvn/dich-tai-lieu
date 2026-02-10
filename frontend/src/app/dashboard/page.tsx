"use client";

import { DollarSign, Cpu, Globe, TrendingDown } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import {
  useCostOverview,
  useProviderCosts,
  useLanguagePairCosts,
} from "@/lib/api/hooks";
import { formatCost, formatNumber } from "@/lib/utils";
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
  const { t } = useLocale();

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
