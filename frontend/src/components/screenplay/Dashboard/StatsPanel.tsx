"use client";

import { ScreenplayProject } from "@/lib/screenplay/types";

interface StatsPanelProps {
  projects: ScreenplayProject[];
}

export function StatsPanel({ projects }: StatsPanelProps) {
  const totalProjects = projects.length;
  const completed = projects.filter((p) => p.status === "completed").length;
  const inProgress = projects.filter((p) =>
    ["analyzing", "writing", "visualizing", "rendering"].includes(p.status)
  ).length;
  const totalCost = projects.reduce((sum, p) => sum + p.actual_cost_usd, 0);
  const totalPages = projects.reduce(
    (sum, p) => sum + (p.screenplay?.total_pages || 0),
    0
  );

  const stats = [
    { label: "Total Projects", value: totalProjects },
    { label: "Completed", value: completed },
    { label: "In Progress", value: inProgress },
    { label: "Pages Written", value: totalPages },
    { label: "Total Cost", value: `$${totalCost.toFixed(2)}` },
  ];

  return (
    <div className="screenplay-stats-panel">
      {stats.map((stat) => (
        <div key={stat.label} className="screenplay-stat-card">
          <div className="screenplay-stat-value">{stat.value}</div>
          <div className="screenplay-stat-label">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}
