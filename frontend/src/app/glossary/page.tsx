"use client";

import { useState } from "react";
import Link from "next/link";
import { BookOpen, Plus, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  useGlossaries,
  useCreateGlossary,
  useDeleteGlossary,
} from "@/lib/api/hooks";
import { SUPPORTED_LANGUAGES } from "@/lib/api/types";
import { useLocale } from "@/lib/i18n";

export default function GlossaryPage() {
  const { data, isLoading } = useGlossaries();
  const createGlossary = useCreateGlossary();
  const deleteGlossary = useDeleteGlossary();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSrc, setNewSrc] = useState("en");
  const [newTgt, setNewTgt] = useState("vi");
  const { t } = useLocale();

  const list = data?.glossaries || [];

  const handleCreate = async () => {
    if (!newName.trim()) return;
    await createGlossary.mutateAsync({
      name: newName.trim(),
      source_language: newSrc,
      target_language: newTgt,
    });
    setNewName("");
    setShowCreate(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1>{t.glossary.title}</h1>
        <Button onClick={() => setShowCreate(!showCreate)} size="sm">
          <Plus className="w-4 h-4 mr-1" /> {t.glossary.newGlossary}
        </Button>
      </div>

      {showCreate && (
        <Card
          style={{
            borderColor: "var(--color-notion-blue)",
            background: "var(--accent-blue-bg)",
          }}
        >
          <CardContent className="pt-4 space-y-3">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={t.glossary.glossaryName}
              className="w-full px-3 py-2 text-sm"
              style={{
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-default)",
                background: "var(--bg-primary)",
                color: "var(--fg-primary)",
              }}
              autoFocus
            />
            <div className="grid grid-cols-2 gap-3">
              <select
                value={newSrc}
                onChange={(e) => setNewSrc(e.target.value)}
                className="px-3 py-2 text-sm"
                style={{
                  borderRadius: "var(--radius-md)",
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
              <select
                value={newTgt}
                onChange={(e) => setNewTgt(e.target.value)}
                className="px-3 py-2 text-sm"
                style={{
                  borderRadius: "var(--radius-md)",
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
            <div className="flex gap-2">
              <Button
                onClick={handleCreate}
                loading={createGlossary.isPending}
                size="sm"
              >
                {t.glossary.create}
              </Button>
              <Button
                variant="ghost"
                onClick={() => setShowCreate(false)}
                size="sm"
              >
                {t.glossary.cancel}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 skeleton" />
          ))}
        </div>
      ) : list.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title={t.glossary.emptyTitle}
          description={t.glossary.emptyDesc}
        />
      ) : (
        <div className="space-y-2">
          {list.map((g) => (
            <Link
              key={g.id}
              href={`/glossary/${g.id}`}
              className="block no-underline"
            >
              <Card className="px-5 py-4 cursor-pointer transition-colors duration-100"
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "var(--bg-hover)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "var(--bg-primary)")
                }
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <BookOpen
                      className="w-5 h-5"
                      style={{ color: "var(--fg-icon)" }}
                      strokeWidth={1.5}
                    />
                    <div>
                      <p
                        className="font-medium text-sm"
                        style={{ color: "var(--fg-primary)" }}
                      >
                        {g.name}
                      </p>
                      <p
                        className="text-xs"
                        style={{ color: "var(--fg-secondary)" }}
                      >
                        {g.language_pair} &middot; {g.entry_count} {t.glossary.terms}
                        {g.project && ` \u00b7 ${g.project}`}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      if (confirm(t.glossary.deleteConfirm))
                        deleteGlossary.mutate(g.id);
                    }}
                    className="p-1.5 transition-colors duration-100"
                    style={{ color: "var(--fg-icon)" }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.color =
                        "var(--color-notion-red)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.color = "var(--fg-icon)")
                    }
                  >
                    <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                  </button>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
