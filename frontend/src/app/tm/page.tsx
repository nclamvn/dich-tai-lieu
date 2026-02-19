"use client";

import { useState } from "react";
import Link from "next/link";
import { useLocale } from "@/lib/i18n";
import { useTMs, useCreateTM, useDeleteTM } from "@/lib/api/hooks";
import { Database, Plus, Trash2, Search, X } from "lucide-react";
import { SUPPORTED_LANGUAGES } from "@/lib/api/types";

export default function TMListPage() {
  const { t } = useLocale();
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newSrcLang, setNewSrcLang] = useState("en");
  const [newTgtLang, setNewTgtLang] = useState("vi");
  const [newDomain, setNewDomain] = useState("general");

  const { data, isLoading } = useTMs(search ? { search } : undefined);
  const createTM = useCreateTM();
  const deleteTM = useDeleteTM();

  const handleCreate = () => {
    if (!newName.trim()) return;
    createTM.mutate(
      {
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        source_language: newSrcLang,
        target_language: newTgtLang,
        domain: newDomain,
      },
      {
        onSuccess: () => {
          setShowCreate(false);
          setNewName("");
          setNewDesc("");
        },
      },
    );
  };

  const handleDelete = (tmId: string) => {
    if (!confirm(t.tm.deleteConfirm)) return;
    deleteTM.mutate(tmId);
  };

  const tms = data?.tms ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1>{t.tm.title}</h1>
          <p className="mt-1 text-sm" style={{ color: "var(--fg-secondary)" }}>
            {t.tm.emptyDesc}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white"
          style={{ borderRadius: "var(--radius-sm)", background: "var(--accent)" }}
        >
          <Plus className="w-4 h-4" />
          {t.tm.newTm}
        </button>
      </div>

      {/* Create dialog */}
      {showCreate && (
        <div
          className="p-4 space-y-3"
          style={{
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-default)",
            background: "var(--bg-secondary)",
          }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--fg-secondary)" }}>
                {t.tm.name}
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My TM"
                className="w-full px-3 py-1.5 text-sm"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--fg-secondary)" }}>
                {t.tm.description}
              </label>
              <input
                type="text"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Optional description"
                className="w-full px-3 py-1.5 text-sm"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--fg-secondary)" }}>
                {t.translate.sourceLang}
              </label>
              <select
                value={newSrcLang}
                onChange={(e) => setNewSrcLang(e.target.value)}
                className="w-full px-3 py-1.5 text-sm"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--fg-secondary)" }}>
                {t.translate.targetLang}
              </label>
              <select
                value={newTgtLang}
                onChange={(e) => setNewTgtLang(e.target.value)}
                className="w-full px-3 py-1.5 text-sm"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-primary)",
                  color: "var(--fg-primary)",
                }}
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setShowCreate(false)}
              className="px-3 py-1.5 text-sm"
              style={{
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                color: "var(--fg-secondary)",
              }}
            >
              {t.common.cancel}
            </button>
            <button
              onClick={handleCreate}
              disabled={!newName.trim() || createTM.isPending}
              className="px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              style={{ borderRadius: "var(--radius-sm)", background: "var(--accent)" }}
            >
              {t.common.create}
            </button>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4"
          style={{ color: "var(--fg-icon)" }}
        />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t.tm.searchSegments}
          className="w-full pl-9 pr-8 py-2 text-sm"
          style={{
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-default)",
            background: "var(--bg-primary)",
            color: "var(--fg-primary)",
          }}
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute right-2 top-1/2 -translate-y-1/2"
          >
            <X className="w-4 h-4" style={{ color: "var(--fg-icon)" }} />
          </button>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="py-12 text-center text-sm" style={{ color: "var(--fg-secondary)" }}>
          {t.common.loading}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && tms.length === 0 && (
        <div className="py-16 text-center">
          <Database
            className="w-12 h-12 mx-auto mb-3"
            style={{ color: "var(--fg-icon)" }}
            strokeWidth={1}
          />
          <p className="text-sm font-medium" style={{ color: "var(--fg-primary)" }}>
            {t.tm.emptyTitle}
          </p>
          <p className="text-sm mt-1" style={{ color: "var(--fg-secondary)" }}>
            {t.tm.emptyDesc}
          </p>
        </div>
      )}

      {/* TM cards */}
      {tms.length > 0 && (
        <div className="grid gap-3">
          {tms.map((item) => (
            <Link
              key={item.id}
              href={`/tm/${item.id}`}
              className="flex items-center justify-between p-4 no-underline transition-colors duration-100"
              style={{
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                background: "var(--bg-primary)",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "var(--bg-primary)")}
            >
              <div className="flex items-center gap-3 min-w-0">
                <Database
                  className="w-5 h-5 shrink-0"
                  style={{ color: "var(--fg-icon)" }}
                  strokeWidth={1.5}
                />
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: "var(--fg-primary)" }}>
                    {item.name}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--fg-secondary)" }}>
                    {item.source_language} → {item.target_language}
                    {" · "}
                    {item.segment_count} {t.tm.segments}
                    {" · "}
                    {item.total_words.toLocaleString()} {t.tm.words}
                    {item.domain !== "general" && ` · ${item.domain}`}
                  </p>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleDelete(item.id);
                }}
                className="p-1.5 shrink-0 transition-colors"
                style={{ borderRadius: "var(--radius-sm)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-active)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <Trash2 className="w-4 h-4" style={{ color: "var(--fg-icon)" }} />
              </button>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
