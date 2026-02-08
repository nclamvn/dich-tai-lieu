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

const CHART_COLORS = [
  "#3b82f6",
  "#8b5cf6",
  "#f59e0b",
  "#10b981",
  "#ef4444",
];

export default function DashboardPage() {
  const { data: overview } = useCostOverview();
  const { data: providers } = useProviderCosts();
  const { data: langPairs } = useLanguagePairCosts();

  const providerList = Array.isArray(providers) ? providers : [];
  const langPairData = langPairs
    ? Object.entries(langPairs).map(([pair, cost]) => ({
        language_pair: pair,
        cost_usd: cost as number,
      }))
    : [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Cost Dashboard</h1>

      {/* Overview Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Cost"
          value={formatCost(overview?.total_cost_usd || 0)}
          icon={DollarSign}
        />
        <StatCard
          label="Total Calls"
          value={formatNumber(overview?.total_calls || 0)}
          icon={Cpu}
        />
        <StatCard
          label="Avg Cost/Call"
          value={formatCost(overview?.avg_cost_per_call || 0)}
          icon={TrendingDown}
        />
        <StatCard
          label="Cost/1K Tokens"
          value={formatCost(overview?.avg_cost_per_1k_tokens || 0)}
          icon={Globe}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Provider Cost Chart */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold">Cost by Provider</h3>
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
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-slate-400 py-8">No data yet</p>
            )}
          </CardContent>
        </Card>

        {/* Language Pair Chart */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold">Cost by Language Pair</h3>
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
                  />
                  <Bar
                    dataKey="cost_usd"
                    fill="#3b82f6"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-slate-400 py-8">No data yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Provider Details Table */}
      {providerList.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="font-semibold">Provider Details</h3>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left px-5 py-3 font-medium">
                    Provider
                  </th>
                  <th className="text-right px-5 py-3 font-medium">Cost</th>
                  <th className="text-right px-5 py-3 font-medium">Calls</th>
                  <th className="text-right px-5 py-3 font-medium">
                    Tokens
                  </th>
                  <th className="text-right px-5 py-3 font-medium">
                    Avg Quality
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {providerList.map((p) => (
                  <tr key={p.provider} className="hover:bg-slate-50">
                    <td className="px-5 py-3 font-medium capitalize">
                      {p.provider}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {formatCost(p.cost_usd)}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {formatNumber(p.calls)}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {formatNumber(p.tokens)}
                    </td>
                    <td className="px-5 py-3 text-right">
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
