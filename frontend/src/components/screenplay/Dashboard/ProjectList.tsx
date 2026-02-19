"use client";

import { useState } from "react";
import Link from "next/link";
import { useProjects } from "@/hooks/screenplay/useProjects";
import { ProjectCard } from "./ProjectCard";

export function ProjectList() {
  const {
    projects,
    total,
    page,
    pageSize,
    loading,
    error,
    setPage,
    refresh,
    remove,
  } = useProjects({ autoRefresh: true, refreshInterval: 5000 });
  const [searchQuery, setSearchQuery] = useState("");

  const totalPages = Math.ceil(total / pageSize);

  if (loading && projects.length === 0) {
    return (
      <div className="screenplay-loading">
        <div className="screenplay-spinner-lg" />
        <p>Loading projects...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="screenplay-error">
        <p>{error}</p>
        <button className="screenplay-btn" onClick={refresh}>
          Retry
        </button>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="screenplay-empty">
        <h3>No projects yet</h3>
        <p>Create your first screenplay project to get started.</p>
        <Link href="/screenplay/new" className="screenplay-btn screenplay-btn-primary">
          Create Project
        </Link>
      </div>
    );
  }

  const filteredProjects = searchQuery.trim()
    ? projects.filter((p) =>
        (p.title || p.id).toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : projects;

  return (
    <div className="screenplay-project-list">
      <div className="screenplay-list-header">
        <h2>
          Projects <span className="screenplay-count">({total})</span>
        </h2>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {projects.length > 3 && (
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search projects..."
              className="screenplay-search-input"
              style={{
                padding: "6px 12px",
                fontSize: 14,
                borderRadius: 6,
                border: "1px solid var(--border-default, #ddd)",
                background: "var(--bg-primary, #fff)",
                color: "var(--fg-primary, #333)",
                width: 200,
              }}
            />
          )}
          <Link href="/screenplay/new" className="screenplay-btn screenplay-btn-primary">
            + New Project
          </Link>
        </div>
      </div>

      <div className="screenplay-grid">
        {filteredProjects.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            onDelete={remove}
          />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="screenplay-pagination">
          <button
            className="screenplay-btn screenplay-btn-sm"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </button>
          <span className="screenplay-page-info">
            Page {page} of {totalPages}
          </span>
          <button
            className="screenplay-btn screenplay-btn-sm"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
